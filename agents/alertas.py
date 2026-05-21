"""
Sistema de Alertas Cruzadas para ChefChat Pro.

Genera alertas proactivas entre agentes:
- Al consultar recetas → alerta de ingredientes por caducar
- Al consultar inventario → alerta de stock bajo + sugerencia lista compras
- Siempre → alerta de personal ausente (reposo, maternidad, etc.)
"""

import logging
from typing import List
from datetime import date, datetime


class AlertManager:
    """Gestor de alertas cruzadas entre agentes del sistema."""

    def __init__(self, db_manager):
        self.db = db_manager

    def get_all_alerts(self, query: str = "", query_type: str = "general") -> str:
        """
        Obtiene todas las alertas relevantes para una consulta.
        
        Args:
            query: Texto de la consulta del usuario.
            query_type: Tipo de consulta (general, receta, inventario, menu, mermas).
            
        Returns:
            str: Alertas formateadas, o "" si no hay alertas.
        """
        alertas = []
        alertas.extend(self._personnel_alerts())
        alertas.extend(self._expiration_alerts(query, query_type))
        alertas.extend(self._low_stock_alerts(query, query_type))
        
        if not alertas:
            return ""
        
        return "\n".join(["", "=" * 50, "ALERTAS DEL SISTEMA", "=" * 50, ""] + alertas)

    def _personnel_alerts(self) -> List[str]:
        """Genera alertas de personal ausente."""
        try:
            ausentes = self.db.obtener_personal_con_ausencia()
            if not ausentes:
                return []
            
            lineas = ["PERSONAL AUSENTE:"]
            hoy = date.today()
            
            for t in ausentes:
                estado = t.get('estado', 'desconocido')
                nombre = t.get('nombre_completo', t.get('id_empleado', '?'))
                cargo = t.get('cargo', '')
                fin_str = t.get('fecha_fin_ausencia', '')
                motivo = t.get('motivo_ausencia', '')
                
                estado_label = {
                    'reposo_medico': 'Reposo medico',
                    'permiso_maternidad': 'Permiso maternidad',
                    'vacaciones': 'Vacaciones',
                    'permiso_personal': 'Permiso personal',
                    'suspendido': 'Suspendido',
                }.get(estado, estado.replace('_', ' ').title())
                
                if fin_str:
                    try:
                        fin_date = datetime.strptime(fin_str, '%Y-%m-%d').date()
                        dias = (fin_date - hoy).days
                        if dias > 0:
                            retorno = f" | Se reincorpora en {dias} dias ({fin_str})"
                        elif dias == 0:
                            retorno = f" | Se reincorpora HOY ({fin_str})"
                        else:
                            retorno = f" | Debio reincorporarse el {fin_str}"
                    except ValueError:
                        retorno = f" | Hasta: {fin_str}"
                else:
                    retorno = ""
                
                motivo_str = f" - {motivo}" if motivo else ""
                lineas.append(f"  {nombre} ({cargo}): {estado_label}{motivo_str}{retorno}")
            
            return lineas
        except (AttributeError, TypeError, ValueError) as e:
            logging.warning("Personnel alerts error: %s", e)
            return []

    def _expiration_alerts(self, _query: str, _query_type: str) -> List[str]:
        """Genera alertas de productos por caducar, con sugerencias de recetas."""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.nombre, c.categoria, i.cantidad_actual, i.unidad,
                       COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days')) as fecha_cad,
                       CAST(julianday(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) - julianday('now') AS INTEGER) as dias
                FROM Inventario i
                JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad_actual > 0
                  AND (i.fecha_caducidad_fija IS NOT NULL OR c.vida_util_dias IS NOT NULL)
                  AND julianday(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) - julianday('now') <= 3
                ORDER BY dias ASC
                LIMIT 5
            """)
            urgentes = cursor.fetchall()
            conn.close()
            
            if not urgentes:
                return []
            
            lineas = ["PRODUCTOS POR CADUCAR (proximos 3 dias):"]
            
            for p in urgentes:
                dias = p['dias']
                etiqueta = "HOY" if dias <= 0 else f"en {dias} dias"
                lineas.append(f"  {p['nombre']}: {p['cantidad_actual']} {p['unidad']} caduca {etiqueta} ({p['fecha_cad']})")
                
                # Buscar recetas que usen este producto
                palabra = p['nombre'].lower().split()[0] if p['nombre'] else ""
                if len(palabra) > 2:
                    try:
                        conn2 = sqlite3.connect(self.db.db_path)
                        cursor2 = conn2.cursor()
                        cursor2.execute("""
                            SELECT nombre, tiempo_prep FROM RecetasRAG
                            WHERE LOWER(ingredientes_json) LIKE ? LIMIT 2
                        """, (f"%{palabra}%",))
                        recetas = cursor2.fetchall()
                        conn2.close()
                        if recetas:
                            for r in recetas:
                                lineas.append(f"    Sugerencia: {r[0]} ({r[1]} min)")
                    except sqlite3.Error:
                        pass
            
            return lineas
        except sqlite3.Error as e:
            logging.warning("Expiration alerts error: %s", e)
            return []

    def _low_stock_alerts(self, _query: str, _query_type: str) -> List[str]:
        """Genera alertas de stock bajo con sugerencia de lista de compras."""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.nombre, SUM(i.cantidad_actual) as total, i.unidad, c.categoria
                FROM Inventario i
                JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad_actual > 0
                GROUP BY c.nombre, i.unidad
                HAVING total < 5
                ORDER BY total ASC
                LIMIT 5
            """)
            bajos = cursor.fetchall()
            conn.close()
            
            if not bajos:
                return []
            
            lineas = ["STOCK BAJO (menos de 5 unidades):"]
            
            for p in bajos:
                aviso = "AGOTADO" if p['total'] <= 1 else "bajo"
                lineas.append(f"  {p['nombre']}: {p['total']:.1f} {p['unidad']} ({aviso}) - {p['categoria']}")
            
            lineas.append("")
            lineas.append("  Deseas generar una lista de compras? Escribe 'lista de compras'")
            
            return lineas
        except sqlite3.Error as e:
            logging.warning("Low stock alerts error: %s", e)
            return []
