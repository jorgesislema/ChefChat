"""
Sistema de Menu Semanal para ChefChat Pro

Gestiona el menu semanal con columnas:
- ID_Plan
- Dia_Semana
- Tipo_Servicio
- Nombre_Plato
- Precio_Venta_USD
- Requiere_Prep_Previa

Integrado con RAG para consultar y modificar con recetas existentes.
"""

import sqlite3
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


class MenuSemanalManager:
    """Gestor del menu semanal integrado con RAG."""

    def __init__(self, db_path: str = "chefchat.db"):
        self.db_path = db_path
        self._init_tablas()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_tablas(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS MenuSemanalPro (
                    ID_Plan INTEGER PRIMARY KEY AUTOINCREMENT,
                    Dia_Semana TEXT NOT NULL,
                    Tipo_Servicio TEXT NOT NULL,
                    Nombre_Plato TEXT NOT NULL,
                    Precio_Venta_USD REAL DEFAULT 0.0,
                    Requiere_Prep_Previa TEXT DEFAULT 'No',
                    receta_id TEXT,
                    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                    activo INTEGER DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_menu_dia 
                ON MenuSemanalPro(Dia_Semana, Tipo_Servicio, activo)
            """)

    def agregar_plato(
        self,
        dia_semana: str,
        tipo_servicio: str,
        nombre_plato: str,
        precio: float = 0.0,
        prep_previa: str = "No",
        receta_id: Optional[str] = None,
    ) -> Optional[int]:
        """Agrega un plato al menu semanal."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO MenuSemanalPro 
                (Dia_Semana, Tipo_Servicio, Nombre_Plato, Precio_Venta_USD, Requiere_Prep_Previa, receta_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dia_semana, tipo_servicio, nombre_plato, precio, prep_previa, receta_id))
            return cursor.lastrowid

    def obtener_menu_semanal(self, activo: bool = True) -> List[Dict[str, Any]]:
        """Obtiene todo el menu semanal."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM MenuSemanalPro"
            params: List[Any] = []
            if activo:
                query += " WHERE activo = 1"
            query += " ORDER BY CASE Dia_Semana WHEN 'Lunes' THEN 1 WHEN 'Martes' THEN 2 WHEN 'Miercoles' THEN 3 WHEN 'Jueves' THEN 4 WHEN 'Viernes' THEN 5 WHEN 'Sabado' THEN 6 WHEN 'Domingo' THEN 7 ELSE 8 END, Tipo_Servicio"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def obtener_menu_por_dia(self, dia: str) -> List[Dict[str, Any]]:
        """Obtiene el menu de un dia especifico."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM MenuSemanalPro 
                WHERE Dia_Semana = ? AND activo = 1
                ORDER BY Tipo_Servicio
            """, (dia,))
            return [dict(row) for row in cursor.fetchall()]

    def obtener_menu_por_servicio(self, dia: str, servicio: str) -> List[Dict[str, Any]]:
        """Obtiene el menu de un dia y servicio especifico."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM MenuSemanalPro 
                WHERE Dia_Semana = ? AND Tipo_Servicio = ? AND activo = 1
            """, (dia, servicio))
            return [dict(row) for row in cursor.fetchall()]

    def modificar_plato(
        self,
        id_plan: int,
        dia_semana: Optional[str] = None,
        tipo_servicio: Optional[str] = None,
        nombre_plato: Optional[str] = None,
        precio: Optional[float] = None,
        prep_previa: Optional[str] = None,
    ) -> bool:
        """Modifica un plato existente."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates: List[str] = []
            params: List[Any] = []
            if dia_semana is not None:
                updates.append("Dia_Semana = ?")
                params.append(dia_semana)
            if tipo_servicio is not None:
                updates.append("Tipo_Servicio = ?")
                params.append(tipo_servicio)
            if nombre_plato is not None:
                updates.append("Nombre_Plato = ?")
                params.append(nombre_plato)
            if precio is not None:
                updates.append("Precio_Venta_USD = ?")
                params.append(precio)
            if prep_previa is not None:
                updates.append("Requiere_Prep_Previa = ?")
                params.append(prep_previa)
            if not updates:
                return False
            params.append(id_plan)
            cursor.execute(f"""
                UPDATE MenuSemanalPro SET {', '.join(updates)}
                WHERE ID_Plan = ?
            """, params)
            return cursor.rowcount > 0

    def eliminar_plato(self, id_plan: int) -> bool:
        """Elimina logicamente un plato del menu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE MenuSemanalPro SET activo = 0 WHERE ID_Plan = ?
            """, (id_plan,))
            return cursor.rowcount > 0

    def reset_menu(self) -> int:
        """Resetea todo el menu semanal (elimina todos los platos activos)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE MenuSemanalPro SET activo = 0 WHERE activo = 1
            """)
            return cursor.rowcount

    def buscar_recetas_rag(self, query: str) -> List[Dict[str, Any]]:
        """Busca recetas en RAG para agregar al menu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_receta, nombre, categoria, tiempo_prep, costo, porciones
                FROM RecetasRAG
                WHERE LOWER(nombre) LIKE LOWER(?) OR LOWER(categoria) LIKE LOWER(?)
                LIMIT 20
            """, (f'%{query}%', f'%{query}%'))
            return [dict(row) for row in cursor.fetchall()]

    def agregar_receta_al_menu(
        self,
        dia_semana: str,
        tipo_servicio: str,
        receta_id: str,
        precio: Optional[float] = None,
        prep_previa: str = "No",
    ) -> Optional[int]:
        """Agrega una receta existente de RAG al menu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nombre, costo, porciones FROM RecetasRAG WHERE id_receta = ?
            """, (receta_id,))
            row = cursor.fetchone()
            if not row:
                return None
            nombre = row['nombre']
            costo = row['costo'] or 0
            precio_venta = precio if precio is not None else costo * 2.5
            cursor.execute("""
                INSERT INTO MenuSemanalPro 
                (Dia_Semana, Tipo_Servicio, Nombre_Plato, Precio_Venta_USD, Requiere_Prep_Previa, receta_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dia_semana, tipo_servicio, nombre, precio_venta, prep_previa, receta_id))
            return cursor.lastrowid

    def consultar_menu(self, pregunta: str) -> str:
        """Responde preguntas sobre el menu semanal."""
        pregunta_lower = pregunta.lower()
        
        # Obtener todo el menu
        menu = self.obtener_menu_semanal()
        if not menu:
            return "No hay menu semanal configurado. Usa 'crear menu' para comenzar."
        
        # Detectar tipo de consulta
        if "lunes" in pregunta_lower:
            return self._formatear_dia("Lunes", menu)
        elif "martes" in pregunta_lower:
            return self._formatear_dia("Martes", menu)
        elif "miercoles" in pregunta_lower or "miércoles" in pregunta_lower:
            return self._formatear_dia("Miercoles", menu)
        elif "jueves" in pregunta_lower:
            return self._formatear_dia("Jueves", menu)
        elif "viernes" in pregunta_lower:
            return self._formatear_dia("Viernes", menu)
        elif "sabado" in pregunta_lower or "sábado" in pregunta_lower:
            return self._formatear_dia("Sabado", menu)
        elif "domingo" in pregunta_lower:
            return self._formatear_dia("Domingo", menu)
        elif "precio" in pregunta_lower or "cuanto" in pregunta_lower or "cuánto" in pregunta_lower:
            return self._formatear_precios(menu)
        elif "preparacion" in pregunta_lower or "prep" in pregunta_lower:
            return self._formatear_preparacion(menu)
        else:
            return self._formatear_menu_completo(menu)

    def _formatear_dia(self, dia: str, menu: List[Dict]) -> str:
        platos_dia = [p for p in menu if p['Dia_Semana'] == dia]
        if not platos_dia:
            return f"No hay menu configurado para el {dia}."
        lineas = [f"📋 **MENU DEL {dia.upper()}**", "=" * 40]
        for p in platos_dia:
            prep = "⏳ Si" if p['Requiere_Prep_Previa'] == 'Si' else "✅ No"
            lineas.append(f"  {p['Tipo_Servicio']}: {p['Nombre_Plato']} - ${p['Precio_Venta_USD']:.2f} (Prep previa: {prep})")
        return "\n".join(lineas)

    def _formatear_precios(self, menu: List[Dict]) -> str:
        lineas = ["💰 **PRECIOS DEL MENU SEMANAL**", "=" * 40]
        for p in menu:
            lineas.append(f"  {p['Dia_Semana']} - {p['Tipo_Servicio']}: {p['Nombre_Plato']} - ${p['Precio_Venta_USD']:.2f}")
        return "\n".join(lineas)

    def _formatear_preparacion(self, menu: List[Dict]) -> str:
        platos_prep = [p for p in menu if p['Requiere_Prep_Previa'] == 'Si']
        if not platos_prep:
            return "No hay platos que requieran preparacion previa."
        lineas = ["⏳ **PLATOS QUE REQUIEREN PREPARACION PREVIA**", "=" * 40]
        for p in platos_prep:
            lineas.append(f"  {p['Dia_Semana']} - {p['Tipo_Servicio']}: {p['Nombre_Plato']}")
        return "\n".join(lineas)

    def _formatear_menu_completo(self, menu: List[Dict]) -> str:
        lineas = ["📋 **MENU SEMANAL COMPLETO**", "=" * 40]
        dia_actual = None
        for p in menu:
            if p['Dia_Semana'] != dia_actual:
                dia_actual = p['Dia_Semana']
                lineas.append(f"\n**{dia_actual.upper()}**")
                lineas.append("-" * 30)
            prep = "⏳" if p['Requiere_Prep_Previa'] == 'Si' else "✅"
            lineas.append(f"  {p['Tipo_Servicio']}: {p['Nombre_Plato']} - ${p['Precio_Venta_USD']:.2f} {prep}")
        return "\n".join(lineas)
