"""
Gestor de Base de Datos para ChefChat Pro - SQLite

Este módulo implementa la capa de persistencia usando SQLite con
context managers para manejo seguro de conexiones y transacciones.
"""

import sqlite3
import json
from datetime import date
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from core.models import (
    Catalogo, Inventario, VistaCaducidad, BitacoraDiaria
)


class DatabaseManager:
    """
    Gestor de base de datos SQLite para ChefChat Pro.
    
    Implementa todas las operaciones CRUD para las tablas del sistema,
    incluyendo la vista de caducidad y operaciones de reporting.
    
    Attributes:
        db_path: Ruta al archivo de base de datos.
    """

    def __init__(self, db_path: str = "chefchat.db") -> None:
        """
        Inicializa el DatabaseManager y crea las tablas si no existen.
        
        Args:
            db_path: Ruta al archivo SQLite. Por defecto 'chefchat.db'.
        """
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """
        Context manager para conexiones SQLite.
        
        Yields:
            sqlite3.Connection: Conexión con row_factory habilitado.
        
        Example:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM Catalogo")
        """
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

    def _init_db(self) -> None:
        """Inicializa todas las tablas y vistas de la base de datos."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Catalogo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    categoria TEXT NOT NULL,
                    vida_util_dias INTEGER NOT NULL CHECK(vida_util_dias > 0 AND vida_util_dias <= 365)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Bitacora_Diaria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    categoria TEXT NOT NULL,
                    descripcion TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Ventas_Historicas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receta_id INTEGER NOT NULL,
                    receta_nombre TEXT NOT NULL,
                    unidades_vendidas INTEGER NOT NULL CHECK(unidades_vendidas > 0),
                    precio_venta REAL NOT NULL CHECK(precio_venta > 0),
                    costo_produccion REAL NOT NULL CHECK(costo_produccion >= 0),
                    fecha_venta DATE DEFAULT CURRENT_DATE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Recetas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    ingredientes TEXT NOT NULL,
                    comensales INTEGER NOT NULL CHECK(comensales > 0),
                    costo_produccion REAL NOT NULL CHECK(costo_produccion >= 0)
                )
            """)
            
            # Telemetría y Observabilidad
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    modelo_usado TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    costo_total_usd REAL DEFAULT 0.0,
                    tipo_operacion TEXT NOT NULL,
                    duracion_segundos REAL DEFAULT 0.0,
                    exito INTEGER DEFAULT 1
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_telemetria_timestamp 
                ON telemetria(timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_telemetria_modelo 
                ON telemetria(modelo_usado)
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL,
                    id_lote TEXT,
                    fecha_ingreso DATE NOT NULL,
                    cantidad_actual REAL NOT NULL CHECK(cantidad_actual > 0),
                    unidad TEXT NOT NULL,
                    fecha_caducidad_fija DATE,
                    FOREIGN KEY (producto_id) REFERENCES Catalogo(id)
                )
            """)
            
            cursor.execute("""
                DROP VIEW IF EXISTS Vista_Caducidad
            """)
            
            cursor.execute("""
                CREATE VIEW Vista_Caducidad AS
                SELECT 
                    i.id as inventario_id,
                    c.nombre as producto_nombre,
                    c.categoria,
                    i.fecha_ingreso,
                    i.cantidad_actual,
                    i.unidad,
                    c.vida_util_dias,
                    COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days')) as fecha_caducidad_efectiva,
                    CAST(julianday(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) - julianday(date('now')) AS INTEGER) as dias_restantes
                FROM Inventario i
                JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad_actual > 0
            """)
            
            # Índices para Inventario (después de crear la tabla y vista)
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_inventario_lote 
                    ON Inventario(id_lote)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_inventario_producto_fecha 
                    ON Inventario(producto_id, fecha_ingreso)
                """)
            except DatabaseError as e:
                print(f"Nota: {e}")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Bitacora_Diaria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    categoria TEXT NOT NULL,
                    descripcion TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Ventas_Historicas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receta_id INTEGER NOT NULL,
                    receta_nombre TEXT NOT NULL,
                    unidades_vendidas INTEGER NOT NULL CHECK(unidades_vendidas > 0),
                    precio_venta REAL NOT NULL CHECK(precio_venta > 0),
                    costo_produccion REAL NOT NULL CHECK(costo_produccion >= 0),
                    fecha_venta DATE DEFAULT CURRENT_DATE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Recetas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    ingredientes TEXT NOT NULL,
                    comensales INTEGER NOT NULL CHECK(comensales > 0),
                    costo_produccion REAL NOT NULL CHECK(costo_produccion >= 0)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Mermas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATE DEFAULT CURRENT_DATE,
                    producto TEXT NOT NULL,
                    cantidad REAL NOT NULL CHECK(cantidad > 0),
                    unidad TEXT NOT NULL,
                    motivo TEXT NOT NULL,
                    costo_estimado REAL DEFAULT 0.0,
                    receta_asociada TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS OrdenesCompra (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_emision DATE DEFAULT CURRENT_DATE,
                    proveedor TEXT NOT NULL,
                    producto TEXT NOT NULL,
                    cantidad REAL NOT NULL CHECK(cantidad > 0),
                    unidad TEXT NOT NULL,
                    costo_unitario REAL DEFAULT 0.0,
                    estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'enviada', 'recibida', 'cancelada')),
                    receta_origen TEXT,
                    fecha_requerida DATE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS MenuSemanal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dia_semana TEXT NOT NULL CHECK(dia_semana IN ('Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo')),
                    tipo_comida TEXT NOT NULL CHECK(tipo_comida IN ('entrante','sopa','plato_fuerte','postre','bebida')),
                    receta_id TEXT NOT NULL,
                    receta_nombre TEXT NOT NULL,
                    activo INTEGER DEFAULT 1
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS TurnosCocina (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATE NOT NULL,
                    cocinero TEXT NOT NULL,
                    estacion TEXT NOT NULL CHECK(estacion IN ('entradas','sopas','platos_fuertes','postres','plancha','parrilla','vegetales','limpieza')),
                    hora_inicio TEXT NOT NULL,
                    hora_fin TEXT NOT NULL,
                    receta_asignada TEXT,
                    notas TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ProduccionDiaria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATE DEFAULT CURRENT_DATE,
                    tipo TEXT NOT NULL CHECK(tipo IN ('cocido', 'sobrante')),
                    receta_nombre TEXT,
                    producto TEXT NOT NULL,
                    cantidad REAL NOT NULL CHECK(cantidad >= 0),
                    unidad TEXT NOT NULL,
                    es_perecedero INTEGER DEFAULT 0,
                    destino TEXT DEFAULT 'reportado' CHECK(destino IN ('reportado', 'desperdicio', 'almacenado', 'donacion'))
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Trabajadores (
                    id_empleado TEXT PRIMARY KEY,
                    nombre_completo TEXT NOT NULL,
                    cargo TEXT NOT NULL,
                    turno TEXT NOT NULL CHECK(turno IN ('matutino', 'vespertino', 'nocturno', 'mixto')),
                    hora_entrada TEXT NOT NULL,
                    hora_salida TEXT NOT NULL,
                    dias_descanso TEXT
                )
            """)
            
            # Extension de columnas para gestion de personal (v2.0)
            nuevas_columnas_personal = [
                "ALTER TABLE Trabajadores ADD COLUMN tipo_contrato TEXT DEFAULT 'fijo'",
                "ALTER TABLE Trabajadores ADD COLUMN estado TEXT DEFAULT 'activo'",
                "ALTER TABLE Trabajadores ADD COLUMN fecha_inicio_contrato DATE",
                "ALTER TABLE Trabajadores ADD COLUMN fecha_fin_contrato DATE",
                "ALTER TABLE Trabajadores ADD COLUMN fecha_inicio_ausencia DATE",
                "ALTER TABLE Trabajadores ADD COLUMN fecha_fin_ausencia DATE",
                "ALTER TABLE Trabajadores ADD COLUMN motivo_ausencia TEXT",
            ]
            for col_sql in nuevas_columnas_personal:
                try:
                    cursor.execute(col_sql)
                except sqlite3.OperationalError:
                    pass  # Column already exists

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SobrantesReutilizables (
                    id_sobrante INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_registro DATE DEFAULT CURRENT_DATE,
                    producto_sopro TEXT NOT NULL,
                    cantidad REAL NOT NULL CHECK(cantidad > 0),
                    unidad TEXT NOT NULL,
                    id_empleado TEXT,
                    turno TEXT,
                    dias_reutilizacion_sanitaria INTEGER DEFAULT 1,
                    destino_actual TEXT DEFAULT 'almacenado' CHECK(destino_actual IN ('almacenado', 'reutilizado', 'desperdicio', 'donacion')),
                    FOREIGN KEY (id_empleado) REFERENCES Trabajadores(id_empleado)
                )
            """)

    def insertar_catalogo(self, nombre: str, categoria: str, vida_util_dias: int) -> int | None:
        """
        Inserta un nuevo producto en el catálogo.

        Args:
            nombre: Nombre del producto.
            categoria: Categoría (Fresco, Congelado, Seco, etc.).
            vida_util_dias: Días de vida útil (máx 365, se ajusta automáticamente).

        Returns:
            int: ID del producto insertado.

        Example:
            db.insertar_catalogo("Fresa", "Fresco", 8)
        """
        # Ajustar vida útil a máximo 365 días
        if vida_util_dias > 365:
            vida_util_dias = 365
        elif vida_util_dias <= 0:
            vida_util_dias = 30

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Catalogo (nombre, categoria, vida_util_dias) VALUES (?, ?, ?)",
                (nombre.strip().title(), categoria.strip().title(), vida_util_dias)
            )
            return cursor.lastrowid

    def registrar_merma(self, producto: str, cantidad: float, unidad: str, motivo: str, costo_estimado: float = 0.0, receta_asociada: str = "") -> int | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Mermas (producto, cantidad, unidad, motivo, costo_estimado, receta_asociada) VALUES (?, ?, ?, ?, ?, ?)", (producto.strip().title(), cantidad, unidad, motivo.strip(), costo_estimado, receta_asociada))
            return cursor.lastrowid

    def dar_de_baja_inventario(self, producto: str, cantidad: float, unidad: str, motivo: str, costo: float = 0.0) -> str:
        """Da de baja producto del inventario (rotura, dano, extravio)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, cantidad_actual FROM Inventario WHERE LOWER(producto_id) IN (SELECT id FROM Catalogo WHERE LOWER(nombre) = LOWER(?)) AND cantidad_actual > 0 ORDER BY fecha_ingreso ASC LIMIT 1", (producto,))
            inv = cursor.fetchone()
            if not inv:
                return f"Producto '{producto}' no encontrado en inventario activo."
            inv_id, actual = inv
            if cantidad > actual:
                return f"Cantidad a dar de baja ({cantidad}) excede stock actual ({actual})."
            nueva_cant = actual - cantidad
            if nueva_cant <= 0.001:
                cursor.execute("DELETE FROM Inventario WHERE id = ?", (inv_id,))
            else:
                cursor.execute("UPDATE Inventario SET cantidad_actual = ? WHERE id = ?", (round(nueva_cant, 3), inv_id))
            cursor.execute("INSERT INTO Mermas (producto, cantidad, unidad, motivo, costo_estimado) VALUES (?, ?, ?, ?, ?)",
                          (producto.strip().title(), cantidad, unidad, f"BAJA: {motivo}", costo))
            return f"BAJA registrada: {cantidad} {unidad} de {producto} - {motivo} (stock restante: {nueva_cant:.1f} {unidad})"

    def obtener_mermas(self, dias: int = 7) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Mermas WHERE fecha >= date('now', ? || ' days') ORDER BY fecha DESC", (f"-{dias}",))
            return [dict(row) for row in cursor.fetchall()]

    def total_mermas_periodo(self, dias: int = 30) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total_mermas, SUM(costo_estimado) as costo_total, SUM(cantidad) as cantidad_total FROM Mermas WHERE fecha >= date('now', ? || ' days')", (f"-{dias}",))
            row = cursor.fetchone()
            return dict(row) if row else {"total_mermas": 0, "costo_total": 0, "cantidad_total": 0}

    def generar_orden_compra(self, proveedor: str, producto: str, cantidad: float, unidad: str, costo_unitario: float = 0.0, receta_origen: str = "", fecha_requerida: str = "") -> int | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO OrdenesCompra (proveedor, producto, cantidad, unidad, costo_unitario, receta_origen, fecha_requerida) VALUES (?, ?, ?, ?, ?, ?, ?)", (proveedor.strip().title(), producto.strip().title(), cantidad, unidad, costo_unitario, receta_origen, fecha_requerida))
            return cursor.lastrowid

    def obtener_ordenes_compra(self, estado: str = "pendiente") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM OrdenesCompra WHERE estado = ? ORDER BY fecha_emision DESC", (estado,))
            return [dict(row) for row in cursor.fetchall()]

    def actualizar_estado_orden(self, orden_id: int, nuevo_estado: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE OrdenesCompra SET estado = ? WHERE id = ?", (nuevo_estado, orden_id))
            return cursor.rowcount > 0

    def configurar_menu_semanal(self, dia: str, tipo: str, receta_id: str, receta_nombre: str) -> int | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO MenuSemanal (dia_semana, tipo_comida, receta_id, receta_nombre) VALUES (?, ?, ?, ?)", (dia.strip().title(), tipo.strip().lower().replace(" ", "_"), receta_id, receta_nombre))
            return cursor.lastrowid

    def obtener_menu_semanal(self, dia: str = "") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if dia:
                cursor.execute("SELECT * FROM MenuSemanal WHERE dia_semana = ? AND activo = 1 ORDER BY tipo_comida", (dia.strip().title(),))
            else:
                cursor.execute("SELECT * FROM MenuSemanal WHERE activo = 1 ORDER BY dia_semana, tipo_comida")
            return [dict(row) for row in cursor.fetchall()]

    def limpiar_menu_semanal(self, dia: str = "") -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if dia:
                cursor.execute("UPDATE MenuSemanal SET activo = 0 WHERE dia_semana = ?", (dia.strip().title(),))
            else:
                cursor.execute("UPDATE MenuSemanal SET activo = 0")

    def costo_real_vs_teorico(self, dias: int = 30) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.receta_nombre, v.receta_id,
                       SUM(v.unidades_vendidas) as unidades,
                       AVG(v.costo_produccion) as costo_real_unitario,
                       AVG(v.precio_venta) as precio_venta,
                       SUM(v.unidades_vendidas * v.costo_produccion) as costo_real_total,
                       SUM(v.unidades_vendidas * v.precio_venta) as ingreso_total
                FROM Ventas_Historicas v
                WHERE v.fecha_venta >= date('now', ? || ' days')
                GROUP BY v.receta_nombre, v.receta_id
                ORDER BY ingreso_total DESC
            """, (f"-{dias}",))
            rows = cursor.fetchall()
            resultados = []
            for row in rows:
                item = dict(row)
                item["margen_real"] = round((item["ingreso_total"] - item["costo_real_total"]) / item["ingreso_total"] * 100, 2) if item["ingreso_total"] else 0
                resultados.append(item)
            return resultados

    def asignar_turno(self, fecha: str, cocinero: str, estacion: str, hora_inicio: str, hora_fin: str, receta_asignada: str = "", notas: str = "") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO TurnosCocina (fecha, cocinero, estacion, hora_inicio, hora_fin, receta_asignada, notas) VALUES (?, ?, ?, ?, ?, ?, ?)", (fecha, cocinero.strip().title(), estacion.strip().lower(), hora_inicio, hora_fin, receta_asignada, notas))
            return cursor.lastrowid

    def obtener_turnos(self, fecha: str = "") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if fecha:
                cursor.execute("SELECT * FROM TurnosCocina WHERE fecha = ? ORDER BY estacion, hora_inicio", (fecha,))
            else:
                cursor.execute("SELECT * FROM TurnosCocina WHERE fecha >= date('now') ORDER BY fecha, estacion, hora_inicio LIMIT 20")
            return [dict(row) for row in cursor.fetchall()]

    def obtener_ventas_dashboard(self, dias: int = 7) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.fecha_venta, v.receta_nombre,
                       SUM(v.unidades_vendidas) as unidades,
                       SUM(v.unidades_vendidas * v.precio_venta) as ingresos,
                       SUM(v.unidades_vendidas * v.costo_produccion) as costos
                FROM Ventas_Historicas v
                WHERE v.fecha_venta >= date('now', ? || ' days')
                GROUP BY v.fecha_venta, v.receta_nombre
                ORDER BY v.fecha_venta DESC, ingresos DESC
            """, (f"-{dias}",))
            ventas = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT v.fecha_venta,
                       SUM(v.unidades_vendidas * v.precio_venta) as ingresos,
                       SUM(v.unidades_vendidas * v.costo_produccion) as costos,
                       SUM(v.unidades_vendidas * (v.precio_venta - v.costo_produccion)) as ganancia
                FROM Ventas_Historicas v
                WHERE v.fecha_venta >= date('now', ? || ' days')
                GROUP BY v.fecha_venta
                ORDER BY v.fecha_venta ASC
            """, (f"-{dias}",))
            diario = [dict(row) for row in cursor.fetchall()]

            total_ingresos = sum(v["ingresos"] for v in ventas)
            total_costos = sum(v["costos"] for v in ventas)
            return {
                "ventas": ventas,
                "diario": diario,
                "total_ingresos": total_ingresos,
                "total_costos": total_costos,
                "total_ganancia": total_ingresos - total_costos,
                "margen_promedio": round((total_ingresos - total_costos) / total_ingresos * 100, 2) if total_ingresos else 0,
                "total_unidades": sum(v["unidades"] for v in ventas),
                "periodo_dias": dias
            }

    def alertas_stock_bajo(self, umbral: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.nombre, c.categoria, SUM(i.cantidad_actual) as stock_total, i.unidad
                FROM Inventario i
                JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad_actual > 0
                GROUP BY c.nombre, c.categoria, i.unidad
                HAVING stock_total < ?
                ORDER BY stock_total ASC
            """, (umbral,))
            return [dict(row) for row in cursor.fetchall()]

    def sugerir_menu_diario(self) -> Dict[str, Any]:
        hoy = date.today()
        dias_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
        dia_actual = dias_semana[hoy.weekday()]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM MenuSemanal WHERE dia_semana = ? AND activo = 1 ORDER BY tipo_comida", (dia_actual,))
            menu_config = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT c.nombre, c.categoria, SUM(i.cantidad_actual) as stock, i.unidad
                FROM Inventario i JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad_actual > 0 AND i.cantidad_actual < 20
                GROUP BY c.nombre, c.categoria, i.unidad
                ORDER BY stock ASC LIMIT 5
            """)
            stock_bajo = [dict(row) for row in cursor.fetchall()]

        return {"dia": dia_actual, "menu_configurado": menu_config, "stock_bajo_sugerencia": stock_bajo}

    CategoriasPerecederas = {"fresco", "lacteos", "carnes", "pescados", "mariscos", "verduras", "frutas", "huevos", "lácteos"}

    def registrar_produccion(self, fecha: str, items_cocidos: list, items_sobrantes: list) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            registros = {"cocidos": 0, "sobrantes": 0, "desperdicios": 0, "almacenados": 0}

            for item in items_cocidos:
                receta = item.get("receta", "")
                producto = item.get("producto", receta)
                cantidad = float(item.get("cantidad", 0))
                unidad = item.get("unidad", "porciones")
                cursor.execute("INSERT INTO ProduccionDiaria (fecha, tipo, receta_nombre, producto, cantidad, unidad, destino) VALUES (?, 'cocido', ?, ?, ?, ?, 'reportado')", (fecha, receta, producto, cantidad, unidad))
                registros["cocidos"] += 1

            for item in items_sobrantes:
                producto = item.get("producto", "")
                cantidad = float(item.get("cantidad", 0))
                unidad = item.get("unidad", "kg")
                es_perecedero = item.get("es_perecedero", 0)
                if es_perecedero:
                    destino = "desperdicio"
                    registros["desperdicios"] += 1
                else:
                    destino = "almacenado"
                    registros["almacenados"] += 1
                cursor.execute("INSERT INTO ProduccionDiaria (fecha, tipo, producto, cantidad, unidad, es_perecedero, destino) VALUES (?, 'sobrante', ?, ?, ?, ?, ?)", (fecha, producto, cantidad, unidad, es_perecedero, destino))
                registros["sobrantes"] += 1

        return registros

    def determinar_perecedero(self, producto: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT categoria FROM Catalogo WHERE LOWER(nombre) LIKE LOWER(?)", (f"%{producto.split()[0]}%",))
            row = cursor.fetchone()
            if row:
                return row[0].lower() in self.CategoriasPerecederas
        return False

    def obtener_produccion_dashboard(self, dias: int = 7) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tipo, COUNT(*) as total, SUM(cantidad) as cantidad_total, unidad
                FROM ProduccionDiaria
                WHERE fecha >= date('now', ? || ' days')
                GROUP BY tipo, unidad
            """, (f"-{dias}",))
            resumen = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT fecha, tipo, receta_nombre, producto, cantidad, unidad, destino
                FROM ProduccionDiaria
                WHERE fecha >= date('now', ? || ' days')
                ORDER BY fecha DESC, tipo
            """, (f"-{dias}",))
            detalle = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT COALESCE(SUM(cantidad), 0) as total_desperdicio
                FROM ProduccionDiaria
                WHERE destino = 'desperdicio' AND fecha >= date('now', ? || ' days')
            """, (f"-{dias}",))
            desperdicio = cursor.fetchone()

            cursor.execute("""
                SELECT COALESCE(SUM(cantidad), 0) as total_almacenado
                FROM ProduccionDiaria
                WHERE destino = 'almacenado' AND fecha >= date('now', ? || ' days')
            """, (f"-{dias}",))
            almacenado = cursor.fetchone()

            return {
                "resumen": resumen,
                "detalle": detalle,
                "total_desperdicio": desperdicio[0] if desperdicio else 0,
                "total_almacenado": almacenado[0] if almacenado else 0,
                "periodo_dias": dias
            }

    def crear_producto(
        self, nombre: str, categoria: str, 
        vida_util_dias: int
    ) -> int:
        """
        Crea un producto en el catálogo.
        
        Args:
            nombre: Nombre del producto.
            categoria: Categoría del producto.
            vida_util_dias: Días de vida útil.
            
        Returns:
            int: ID del producto creado.
            
        Raises:
            ValueError: Si la inserción falla.
        """
        result = self.insertar_catalogo(
            nombre, categoria, vida_util_dias
        )
        if result is None:
            raise ValueError(
                f"Error al crear producto: {nombre}"
            )
        return result

    def insertar_inventario(
        self, producto_id: int, cantidad: float, unidad: str, 
        fecha_ingreso: Optional[date] = None
    ) -> Optional[int]:
        """
        Registra una entrada de producto al inventario.
        
        Args:
            producto_id: ID del producto en Catálogo.
            cantidad: Cantidad del producto.
            unidad: Unidad de medida.
            fecha_ingreso: Fecha de ingreso (por defecto hoy).
            
        Returns:
            int: ID del registro insertado.
        """
        if fecha_ingreso is None:
            fecha_ingreso = date.today()
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO Inventario (producto_id, fecha_ingreso, cantidad, unidad) 
                   VALUES (?, ?, ?, ?)""",
                (producto_id, fecha_ingreso.isoformat(), cantidad, unidad.lower())
            )
            return cursor.lastrowid

    def obtener_ingredientes_por_caducar(self, dias_limite: int) -> List[VistaCaducidad]:
        """
        Obtiene productos que caducarán en los próximos días_limite.
        
        Implementa lógica FEFO (First Expired, First Out) ordenando
        por fecha de caducidad ascendente.
        
        Args:
            dias_limite: Número de días para la consulta.
            
        Returns:
            List[VistaCaducidad]: Lista de productos por caducar.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM Vista_Caducidad 
                   WHERE dias_restantes <= ? AND dias_restantes >= -1
                   ORDER BY dias_restantes ASC""",
                (dias_limite,)
            )
            rows = cursor.fetchall()
            return [VistaCaducidad(**dict(row)) for row in rows]

    def registrar_uso_inventario(self, nombre_item: str, cantidad_usada: float) -> str:
        """
        Registra el uso de inventario aplicando política FEFO.
        
        Descuenta la cantidad del lote más antiguo primero.
        
        Args:
            nombre_item: Nombre del producto.
            cantidad_usada: Cantidad a descontar.
            
        Returns:
            str: Mensaje de confirmación del uso registrado.
            
        Raises:
            ValueError: Si no hay suficiente inventario.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT i.id, i.cantidad, i.producto_id 
                   FROM Inventario i
                   JOIN Catalogo c ON i.producto_id = c.id
                   WHERE c.nombre = ? AND i.cantidad > 0
                   ORDER BY i.fecha_ingreso ASC""",
                (nombre_item.strip().title(),)
            )
            lotes = cursor.fetchall()
            
            if not lotes:
                raise ValueError(f"No hay inventario disponible de '{nombre_item}'")
            
            cantidad_restante = cantidad_usada
            lotes_actualizados = []
            
            for lote in lotes:
                if cantidad_restante <= 0:
                    break
                    
                lote_id, cantidad_lote, _ = lote
                
                if cantidad_lote <= cantidad_restante:
                    cursor.execute(
                        "UPDATE Inventario SET cantidad = 0 WHERE id = ?",
                        (lote_id,)
                    )
                    cantidad_restante -= cantidad_lote
                    lotes_actualizados.append(f"Lote {lote_id}: {cantidad_lote} usados (agotado)")
                else:
                    nueva_cantidad = cantidad_lote - cantidad_restante
                    cursor.execute(
                        "UPDATE Inventario SET cantidad = ? WHERE id = ?",
                        (nueva_cantidad, lote_id)
                    )
                    lotes_actualizados.append(f"Lote {lote_id}: {cantidad_restante} usados")
                    cantidad_restante = 0
            
            if cantidad_restante > 0:
                raise ValueError(
                    f"Insuficiente inventario. Faltan {cantidad_restante} unidades"
                )
            
            return f"Uso registrado: {', '.join(lotes_actualizados)}"

    def escalar_receta(self, receta_id: int, comensales: int) -> Dict[str, Any]:
        """
        Escala matemáticamente una receta para nuevo número de comensales.
        
        Args:
            receta_id: ID de la receta.
            comensales: Nuevo número de comensales.
            
        Returns:
            Dict[str, Any]: Receta escalada con ingredientes ajustados.
            
        Raises:
            ValueError: Si la receta no existe.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM Recetas WHERE id = ?", (receta_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"Receta ID {receta_id} no encontrada")
            
            receta = dict(row)
            factorescala = comensales / receta["comensales"]
            ingredientes = json.loads(receta["ingredientes"])
            
            ingredientes_escalados = []
            for ing in ingredientes:
                ing_escalado = ing.copy()
                ing_escalado["cantidad"] = round(ing["cantidad"] * factorescala, 2)
                ingredientes_escalados.append(ing_escalado)
            
            return {
                "id": receta["id"],
                "nombre": receta["nombre"],
                "comensales_originales": receta["comensales"],
                "comensales_nuevos": comensales,
                "factor_escala": round(factorescala, 2),
                "ingredientes": ingredientes_escalados,
                "costo_produccion_estimado": round(receta["costo_produccion"] * factorescala, 2)
            }

    def registrar_incidencia(self, categoria: str, descripcion: str) -> int | None:
        """
        Registra una incidencia en la bitácora diaria.
        
        Args:
            categoria: Categoría de la incidencia.
            descripcion: Descripción detallada.
            
        Returns:
            int | None: ID del registro insertado.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Bitacora_Diaria (categoria, descripcion) VALUES (?, ?)",
                (categoria.strip().title(), descripcion.strip())
            )
            return cursor.lastrowid

    def analizar_rentabilidad_menu(self) -> Dict[str, Any]:
        """
        Analiza la rentabilidad del menú usando matriz BCG.
        
        Clasifica las recetas en:
        - Estrellas: Alto margen (>40%), Alta venta (>10 unidades)
        - Vacas: Alto margen, Baja venta
        - Interrogantes: Bajo margen, Alta venta
        - Perros: Bajo margen, Baja venta
        
        Returns:
            Dict[str, Any]: Clasificación de recetas con resumen.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    receta_id,
                    receta_nombre,
                    SUM(unidades_vendidas) as total_vendidas,
                    AVG(precio_venta) as precio_promedio,
                    AVG(costo_produccion) as costo_promedio,
                    AVG((precio_venta - costo_produccion) / precio_venta * 100) as margen_promedio
                FROM Ventas_Historicas
                GROUP BY receta_id, receta_nombre
            """)
            rows = cursor.fetchall()
            
            resultado = {
                "estrellas": [],
                "vacas": [],
                "interrogantes": [],
                "perros": []
            }
            
            for row in rows:
                item = dict(row)
                es_alto_margen = item["margen_promedio"] > 40
                es_alta_venta = item["total_vendidas"] > 10
                
                dato = {
                    "receta_id": item["receta_id"],
                    "nombre": item["receta_nombre"],
                    "unidades_vendidas": int(item["total_vendidas"]),
                    "margen_promedio": round(item["margen_promedio"], 2)
                }
                
                if es_alto_margen and es_alta_venta:
                    resultado["estrellas"].append(dato)
                elif es_alto_margen and not es_alta_venta:
                    resultado["vacas"].append(dato)
                elif not es_alto_margen and es_alta_venta:
                    resultado["interrogantes"].append(dato)
                else:
                    resultado["perros"].append(dato)
            
            total = sum(len(v) for v in resultado.values())
            resultado["resumen"] = (
                f"Análisis completado: {total} recetas analizadas. "
                f"Estrellas: {len(resultado['estrellas'])}, "
                f"Vacas: {len(resultado['vacas'])}, "
                f"Interrogantes: {len(resultado['interrogantes'])}, "
                f"Perros: {len(resultado['perros'])}"
            )
            
            return resultado

    def registrar_venta(
        self, receta_id: int, receta_nombre: str,
        unidades: int, precio_venta: float, costo_produccion: float,
        fecha_venta: Optional[date] = None
    ) -> int:
        """
        Registra una venta en el histórico.
        
        Args:
            receta_id: ID de la receta vendida.
            receta_nombre: Nombre de la receta.
            unidades: Unidades vendidas.
            precio_venta: Precio de venta unitario.
            costo_produccion: Costo de producción unitario.
            fecha_venta: Fecha de venta (por defecto hoy).
            
        Returns:
            int: ID del registro insertado.
        """
        if fecha_venta is None:
            fecha_venta = date.today()
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO Ventas_Historicas 
                   (receta_id, receta_nombre, unidades_vendidas, precio_venta, costo_produccion, fecha_venta)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (receta_id, receta_nombre, unidades, precio_venta, costo_produccion, fecha_venta.isoformat())
            )
            return cursor.lastrowid or 0

    def insertar_receta(
        self, nombre: str, ingredientes: List[dict],
        comensales: int, costo_produccion: float
    ) -> int:
        """
        Inserta una nueva receta.
        
        Args:
            nombre: Nombre de la receta.
            ingredientes: Lista de ingredientes con cantidades.
            comensales: Número de comensales.
            costo_produccion: Costo total de producción.
            
        Returns:
            int: ID de la receta insertada.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO Recetas (nombre, ingredientes, comensales, costo_produccion)
                   VALUES (?, ?, ?, ?)""",
                (nombre.strip().title(), json.dumps(ingredientes), comensales, costo_produccion)
            )
            return cursor.lastrowid or 0

    def obtener_todos_los_productos(self) -> List[Catalogo]:
        """Obtiene todos los productos del catálogo."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Catalogo ORDER BY nombre")
            rows = cursor.fetchall()
            return [Catalogo(**dict(row)) for row in rows]

    def obtener_inventario_actual(self) -> List[Inventario]:
        """Obtiene el inventario actual con nombres de productos."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.*, c.nombre as producto_nombre 
                FROM Inventario i
                JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad > 0
                ORDER BY c.nombre
            """)
            rows = cursor.fetchall()
            return [Inventario(**dict(row)) for row in rows]

    def obtener_bitacora_reciente(self, limite: int = 50) -> List[BitacoraDiaria]:
        """Obtiene las últimas incidencias de la bitácora."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM Bitacora_Diaria ORDER BY timestamp DESC LIMIT ?",
                (limite,)
            )
            rows = cursor.fetchall()
            return [BitacoraDiaria(**dict(row)) for row in rows]

    # =========================================================================
    # TELEMETRÍA Y OBSERVABILIDAD
    # =========================================================================

    def registrar_telemetria(
        self, modelo: str, input_tokens: int, output_tokens: int,
        costo_usd: float, operacion: str, duracion: float = 0.0, exito: bool = True
    ) -> int:
        """Registra una llamada al LLM en la tabla de telemetría."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO telemetria 
                (modelo_usado, input_tokens, output_tokens, costo_total_usd, 
                 tipo_operacion, duracion_segundos, exito)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (modelo, input_tokens, output_tokens, costo_usd, 
                  operacion, duracion, 1 if exito else 0))
            return cursor.lastrowid

    def obtener_gasto_total_mes(self) -> float:
        """Obtiene el gasto total del mes actual en USD."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(costo_total_usd), 0.0) as total
                FROM telemetria
                WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
            """)
            row = cursor.fetchone()
            return float(row["total"]) if row else 0.0

    def obtener_total_tokens(self) -> Dict[str, int]:
        """Obtiene el total de tokens consumidos (input/output)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(input_tokens), 0) as input_total,
                    COALESCE(SUM(output_tokens), 0) as output_total
                FROM telemetria
                WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
            """)
            row = cursor.fetchone()
            return {
                "input": int(row["input_total"]) if row else 0,
                "output": int(row["output_total"]) if row else 0,
                "total": int(row["input_total"] + row["output_total"]) if row else 0
            }

    def obtener_total_peticiones(self) -> int:
        """Obtiene el total de peticiones (llamadas API) del mes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as total FROM telemetria
                WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
            """)
            row = cursor.fetchone()
            return int(row["total"]) if row else 0

    def obtener_gasto_ultimos_7_dias(self) -> List[Dict[str, Any]]:
        """Obtiene el gasto diario de los últimos 7 días."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    date(timestamp) as fecha,
                    SUM(costo_total_usd) as gasto_dia
                FROM telemetria
                WHERE date(timestamp) >= date('now', '-6 days')
                GROUP BY date(timestamp)
                ORDER BY fecha ASC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def obtener_telemetria_reciente(self, limite: int = 50) -> List[Dict[str, Any]]:
        """Obtiene los registros recientes de telemetría."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    timestamp, modelo_usado, input_tokens, output_tokens,
                    costo_total_usd, tipo_operacion, exito
                FROM telemetria
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limite,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def obtener_gasto_por_modelo(self) -> List[Dict[str, Any]]:
        """Obtiene el gasto acumulado por modelo."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    modelo_usado,
                    SUM(costo_total_usd) as gasto_total,
                    COUNT(*) as cantidad_usos,
                    SUM(input_tokens + output_tokens) as tokens_totales
                FROM telemetria
                WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
                GROUP BY modelo_usado
                ORDER BY gasto_total DESC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # TRABAJADORES
    # =========================================================================

    def registrar_trabajador(self, id_empleado: str, nombre: str, cargo: str,
                             turno: str, hora_entrada: str, hora_salida: str,
                             dias_descanso: str = "",
                             tipo_contrato: str = "fijo", estado: str = "activo",
                             fecha_inicio: str = "", fecha_fin: str = "") -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO Trabajadores
                (id_empleado, nombre_completo, cargo, turno, hora_entrada, hora_salida, dias_descanso,
                 tipo_contrato, estado, fecha_inicio_contrato, fecha_fin_contrato)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (id_empleado.upper(), nombre.strip().title(), cargo.strip().title(),
                  turno.strip().lower(), hora_entrada, hora_salida, dias_descanso,
                  tipo_contrato, estado, fecha_inicio, fecha_fin))
            return f"Trabajador {nombre} registrado (ID: {id_empleado.upper()})"

    def obtener_trabajadores(self, turno: str = "") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if turno:
                cursor.execute("SELECT * FROM Trabajadores WHERE turno = ? ORDER BY nombre_completo", (turno,))
            else:
                cursor.execute("SELECT * FROM Trabajadores ORDER BY turno, nombre_completo")
            return [dict(row) for row in cursor.fetchall()]

    def eliminar_trabajador(self, id_empleado: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Trabajadores WHERE id_empleado = ?", (id_empleado.upper(),))
            return cursor.rowcount > 0

    def registrar_ausencia(self, id_empleado: str, tipo: str,
                           fecha_inicio: str, fecha_fin: str, motivo: str = "") -> str:
        """Registra ausencia (reposo_medico, permiso_maternidad, vacaciones, etc.)."""
        tipos_validos = {'reposo_medico', 'permiso_maternidad', 'vacaciones',
                         'permiso_personal', 'suspendido'}
        tipo_normalizado = tipo.strip().lower().replace(' ', '_')
        if tipo_normalizado not in tipos_validos:
            tipo_normalizado = 'permiso_personal'
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Trabajadores
                SET estado = ?, fecha_inicio_ausencia = ?, fecha_fin_ausencia = ?,
                    motivo_ausencia = ?
                WHERE id_empleado = ?
            """, (tipo_normalizado, fecha_inicio, fecha_fin, motivo, id_empleado.upper()))
            if cursor.rowcount == 0:
                return f"Error: Trabajador {id_empleado} no encontrado"
            return f"Ausencia registrada: {id_empleado} - {tipo_normalizado} ({fecha_inicio} a {fecha_fin})"

    def reincorporar_trabajador(self, id_empleado: str) -> str:
        """Reincorpora a un trabajador tras una ausencia."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Trabajadores
                SET estado = 'activo', fecha_inicio_ausencia = NULL,
                    fecha_fin_ausencia = NULL, motivo_ausencia = NULL
                WHERE id_empleado = ?
            """, (id_empleado.upper(),))
            if cursor.rowcount == 0:
                return f"Error: Trabajador {id_empleado} no encontrado"
            return f"Trabajador {id_empleado} reincorporado"

    def obtener_personal_activo(self) -> List[Dict[str, Any]]:
        """Obtiene personal actualmente activo (no ausente)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM Trabajadores
                WHERE estado = 'activo'
                ORDER BY turno, nombre_completo
            """)
            return [dict(row) for row in cursor.fetchall()]

    def obtener_turno_hoy(self, turno: str = "") -> List[Dict[str, Any]]:
        """
        Obtiene personal que trabaja hoy en un turno especifico.
        Usa la fecha actual para determinar si el trabajador esta activo.
        """
        from datetime import date
        hoy = date.today().strftime('%Y-%m-%d')
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if turno:
                cursor.execute("""
                    SELECT * FROM Trabajadores
                    WHERE turno = ? AND estado = 'activo'
                      AND (fecha_inicio_ausencia IS NULL OR fecha_inicio_ausencia > ?)
                    ORDER BY nombre_completo
                """, (turno.strip().lower(), hoy))
            else:
                cursor.execute("""
                    SELECT * FROM Trabajadores
                    WHERE estado = 'activo'
                      AND (fecha_inicio_ausencia IS NULL OR fecha_inicio_ausencia > ?)
                    ORDER BY turno, nombre_completo
                """, (hoy,))
            return [dict(row) for row in cursor.fetchall()]

    def obtener_personal_con_ausencia(self) -> List[Dict[str, Any]]:
        """Obtiene personal actualmente ausente."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM Trabajadores
                WHERE estado != 'activo'
                ORDER BY fecha_inicio_ausencia DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def seed_mermas_realistas(self, dias: int = 30) -> str:
        """
        Genera datos realistas de mermas para un restaurante.
        Incluye desperdicio diario de vegetales, sobreproduccion,
        pan, aceite, y accidentes varios.
        """
        import random
        from datetime import date, timedelta

        productos_vegetales = [
            ("Cebolla", 0.3, 1.5, "kg", 1.20),
            ("Tomate", 0.5, 2.0, "kg", 1.80),
            ("Lechuga", 0.2, 1.0, "kg", 2.50),
            ("Zanahoria", 0.2, 0.8, "kg", 1.00),
            ("Pimiento", 0.2, 0.5, "kg", 2.00),
            ("Papa", 0.3, 2.0, "kg", 0.80),
            ("Aguacate", 0.1, 0.3, "kg", 3.50),
            ("Cilantro", 0.05, 0.15, "kg", 5.00),
            ("Ajo", 0.05, 0.1, "kg", 4.00),
            ("Espinaca", 0.2, 0.5, "kg", 3.00),
        ]
        productos_proteinas = [
            ("Pollo", 0.5, 2.0, "kg", 4.50),
            ("Cerdo", 0.3, 1.5, "kg", 5.00),
            ("Pescado", 0.2, 1.0, "kg", 7.00),
            ("Res", 0.3, 1.0, "kg", 8.00),
        ]
        productos_pan = [
            ("Pan bolillo", 1.0, 3.0, "kg", 1.50),
            ("Pan de caja", 0.5, 1.5, "kg", 2.00),
        ]
        sobreproduccion = [
            ("Sopa del dia", 1, 4, "porciones", 8.00),
            ("Arroz", 0.5, 2.0, "kg", 1.20),
            ("Frijoles", 0.3, 1.5, "kg", 1.50),
            ("Guarnicion", 1, 5, "porciones", 6.00),
            ("Postre del dia", 1, 3, "porciones", 10.00),
        ]
        motivos_vegetal = [
            "Se echo a perder", "Sobre-maduracion", "Golpeado",
            "No paso control de calidad", "Oxidacion"
        ]
        motivos_proteina = [
            "Caduco", "Cambio de color", "Mal olor",
            "Descongelacion inadecuada", "Excedio vida util"
        ]
        motivos_sobreprod = [
            "Sobreproduccion", "No se vendio", "Excedente de buffet",
            "Error de calculo en porciones"
        ]
        motivos_accidente = [
            "Se cayo al piso", "Se quemo en coccion",
            "Contaminacion cruzada", "Error de preparacion"
        ]

        registros = 0
        hoy = date.today()
        with self._get_connection() as conn:
            cursor = conn.cursor()

            for d in range(dias, -1, -1):
                fecha = hoy - timedelta(days=d)

                # 1. Desperdicio de vegetales (diario, 2-5 items)
                random.shuffle(productos_vegetales)
                for prod in productos_vegetales[:random.randint(2, 5)]:
                    cant = round(random.uniform(prod[1], prod[2]), 2)
                    motivo = random.choice(motivos_vegetal)
                    costo = round(cant * prod[4], 2)
                    cursor.execute(
                        "INSERT INTO Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado) VALUES (?,?,?,?,?,?)",
                        (fecha.strftime('%Y-%m-%d'), prod[0], cant, prod[3], motivo, costo))
                    registros += 1

                # 2. Desperdicio de proteinas (cada 2-3 dias)
                if d % random.randint(2, 3) == 0:
                    prod = random.choice(productos_proteinas)
                    cant = round(random.uniform(prod[1], prod[2]), 2)
                    motivo = random.choice(motivos_proteina)
                    costo = round(cant * prod[4], 2)
                    cursor.execute(
                        "INSERT INTO Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado) VALUES (?,?,?,?,?,?)",
                        (fecha.strftime('%Y-%m-%d'), prod[0], cant, prod[3], motivo, costo))
                    registros += 1

                # 3. Pan (diario, casi siempre)
                if random.random() > 0.2:
                    prod = random.choice(productos_pan)
                    cant = round(random.uniform(prod[1], prod[2]), 2)
                    costo = round(cant * prod[4], 2)
                    cursor.execute(
                        "INSERT INTO Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado) VALUES (?,?,?,?,?,?)",
                        (fecha.strftime('%Y-%m-%d'), prod[0], cant, prod[3],
                         "Sobrante del dia", costo))
                    registros += 1

                # 4. Sobreproduccion (cada 2-4 dias)
                if d % random.randint(2, 4) == 0:
                    prod = random.choice(sobreproduccion)
                    cant = round(random.uniform(prod[1], prod[2]), 2)
                    motivo = random.choice(motivos_sobreprod)
                    costo = round(cant * (prod[4] / max(prod[2], 1)), 2)
                    cursor.execute(
                        "INSERT INTO Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado) VALUES (?,?,?,?,?,?)",
                        (fecha.strftime('%Y-%m-%d'), prod[0], cant, prod[3], motivo, costo))
                    registros += 1

                # 5. Accidentes (ocasional, ~1 por semana)
                if d % 7 == random.randint(0, 6):
                    prods_acc = ["Salsa roja", "Crema", "Huevo", "Queso", "Arroz",
                                 "Pollo empanizado", "Filete de pescado"]
                    prod = random.choice(prods_acc)
                    cant = round(random.uniform(0.2, 1.5), 2)
                    motivo = random.choice(motivos_accidente)
                    costo = round(cant * random.uniform(2, 8), 2)
                    cursor.execute(
                        "INSERT INTO Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado) VALUES (?,?,?,?,?,?)",
                        (fecha.strftime('%Y-%m-%d'), prod, cant, "kg", motivo, costo))
                    registros += 1

        return f"Mermas generadas: {registros} registros en {dias + 1} dias (hasta {hoy.strftime('%Y-%m-%d')})"

    # =========================================================================
    # SOBRANTES REUTILIZABLES
    # =========================================================================

    def registrar_sobrante(self, producto: str, cantidad: float, unidad: str,
                           id_empleado: str = "", turno: str = "",
                           dias_reutilizacion: int = 1,
                           fecha: str = "") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if fecha:
                cursor.execute("""
                    INSERT INTO SobrantesReutilizables
                    (fecha_registro, producto_sopro, cantidad, unidad, id_empleado, turno, dias_reutilizacion_sanitaria)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (fecha, producto.strip().title(), cantidad, unidad.lower(),
                      id_empleado.upper() if id_empleado else None,
                      turno.lower() if turno else None, dias_reutilizacion))
            else:
                cursor.execute("""
                    INSERT INTO SobrantesReutilizables
                    (producto_sopro, cantidad, unidad, id_empleado, turno, dias_reutilizacion_sanitaria)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (producto.strip().title(), cantidad, unidad.lower(),
                      id_empleado.upper() if id_empleado else None,
                      turno.lower() if turno else None, dias_reutilizacion))
            return cursor.lastrowid

    def actualizar_destino_sobrante(self, id_sobrante: int, destino: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE SobrantesReutilizables SET destino_actual = ? WHERE id_sobrante = ?
            """, (destino, id_sobrante))
            return cursor.rowcount > 0

    def obtener_sobrantes(self, dias: int = 7, turno: str = "") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT s.*, t.nombre_completo
                FROM SobrantesReutilizables s
                LEFT JOIN Trabajadores t ON s.id_empleado = t.id_empleado
                WHERE s.fecha_registro >= date('now', ? || ' days')
            """
            params = [f"-{dias}"]
            if turno:
                query += " AND s.turno = ?"
                params.append(turno)
            query += " ORDER BY s.fecha_registro DESC, s.turno"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def dashboard_sobrantes(self, dias: int = 7) -> Dict[str, Any]:
        """Genera datos para dashboard de sobrantes por turno/día."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT fecha_registro, turno,
                       COUNT(*) as total_sobrantes,
                       SUM(cantidad) as cantidad_total,
                       GROUP_CONCAT(producto_sopro, ', ') as productos
                FROM SobrantesReutilizables
                WHERE fecha_registro >= date('now', ? || ' days')
                GROUP BY fecha_registro, turno
                ORDER BY fecha_registro DESC, turno
            """, (f"-{dias}",))
            sobrantes_por_turno = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT destino_actual, COUNT(*) as total, SUM(cantidad) as cantidad_total
                FROM SobrantesReutilizables
                WHERE fecha_registro >= date('now', ? || ' days')
                GROUP BY destino_actual
            """, (f"-{dias}",))
            destinos = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT producto_sopro, SUM(cantidad) as cantidad_total, unidad,
                       COUNT(*) as veces_registrado
                FROM SobrantesReutilizables
                WHERE fecha_registro >= date('now', ? || ' days')
                GROUP BY producto_sopro, unidad
                ORDER BY cantidad_total DESC
                LIMIT 20
            """, (f"-{dias}",))
            top_productos = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT fecha_registro,
                       SUM(cantidad) as total_kilos,
                       SUM(CASE WHEN destino_actual = 'desperdicio' THEN cantidad ELSE 0 END) as desperdicio_kilos,
                       COUNT(*) as total_registros
                FROM SobrantesReutilizables
                WHERE fecha_registro >= date('now', ? || ' days')
                GROUP BY fecha_registro
                ORDER BY fecha_registro ASC
            """, (f"-{dias}",))
            desperdicio_por_dia = [dict(row) for row in cursor.fetchall()]

            return {
                "sobrantes_por_turno": sobrantes_por_turno,
                "destinos": destinos,
                "top_productos": top_productos,
                "desperdicio_por_dia": desperdicio_por_dia,
                "periodo_dias": dias
            }

    def exportar_dashboard_sobrantes_excel(self, dias: int = 7) -> str:
        """Genera dashboard profesional en Excel con gráficos de sobrantes."""
        data = self.dashboard_sobrantes(dias)
        import os
        from datetime import datetime

        filename = f"dashboard_sobrantes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(os.path.dirname(self.db_path) or ".", filename)

        try:
            import win32com.client
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = True
            wb = excel.Workbooks.Add()
            ws_data = wb.Worksheets(1)
            ws_data.Name = "Datos"
            ws_chart = wb.Worksheets.Add()
            ws_chart.Name = "Dashboard"

            # ── DATA SHEET ──
            headers = ["Fecha", "Turno", "Producto", "Cantidad", "Unidad", "Destino", "Dias Reutilizacion", "Empleado"]
            for j, h in enumerate(headers, 1):
                ws_data.Cells(1, j).Value = h
                ws_data.Cells(1, j).Font.Bold = True
                ws_data.Cells(1, j).Interior.Color = 0x34495E
                ws_data.Cells(1, j).Font.Color = 0xFFFFFF

            conn2 = sqlite3.connect(self.db_path)
            conn2.row_factory = sqlite3.Row
            c2 = conn2.cursor()
            c2.execute("""
                SELECT s.*, t.nombre_completo
                FROM SobrantesReutilizables s
                LEFT JOIN Trabajadores t ON s.id_empleado = t.id_empleado
                WHERE s.fecha_registro >= date('now', ? || ' days')
                ORDER BY s.fecha_registro DESC, s.turno
            """, (f"-{dias}",))
            rows = c2.fetchall()
            for i, row in enumerate(rows, 2):
                ws_data.Cells(i, 1).Value = row["fecha_registro"]
                ws_data.Cells(i, 2).Value = row["turno"] or "No especificado"
                ws_data.Cells(i, 3).Value = row["producto_sopro"]
                ws_data.Cells(i, 4).Value = row["cantidad"]
                ws_data.Cells(i, 5).Value = row["unidad"]
                ws_data.Cells(i, 6).Value = row["destino_actual"]
                ws_data.Cells(i, 7).Value = row["dias_reutilizacion_sanitaria"]
                ws_data.Cells(i, 8).Value = row["nombre_completo"] or ""
            conn2.close()

            ws_data.Columns("A:H").AutoFit()

            # ── DASHBOARD SHEET ──
            # Title
            rng_title = ws_chart.Range("A1:H1")
            rng_title.Merge()
            ws_chart.Cells(1, 1).Value = f"DASHBOARD DE SOBRANTES REUTILIZABLES (últimos {dias} días)"
            ws_chart.Cells(1, 1).Font.Bold = True
            ws_chart.Cells(1, 1).Font.Size = 16
            ws_chart.Cells(1, 1).Font.Color = 0x34495E

            # KPI Row
            total_kilos = sum(r["cantidad"] for r in rows) if rows else 0
            total_registros = len(rows)
            desperdicio_kilos = sum(r["cantidad"] for r in rows if r["destino_actual"] == "desperdicio")
            reutilizado = sum(1 for r in rows if r["destino_actual"] == "reutilizado")

            for j, (label, val) in enumerate([
                ("Total Kilos", f"{total_kilos:.1f}"),
                ("Registros", str(total_registros)),
                ("Desperdicio (kg)", f"{desperdicio_kilos:.1f}"),
                ("Reutilizados", str(reutilizado)),
            ], 1):
                cell = ws_chart.Cells(3, j * 2 - 1)
                cell.Value = label
                cell.Font.Bold = True
                cell.Font.Size = 10
                cell.Font.Color = 0x7F8C8D
                val_cell = ws_chart.Cells(4, j * 2 - 1)
                val_cell.Value = val
                val_cell.Font.Bold = True
                val_cell.Font.Size = 24
                val_cell.Font.Color = 0x2C3E50

            # ── CHART 1: Desperdicio por día (bar chart) ──
            desperdicio_dia: dict[str, float] = {}
            for r in rows:
                dia = r["fecha_registro"]
                cant = r["cantidad"]
                desperdicio_dia[dia] = desperdicio_dia.get(dia, 0) + (cant if r["destino_actual"] == "desperdicio" else 0)

            if desperdicio_dia:
                start_row_desp = 7
                ws_chart.Cells(start_row_desp, 1).Value = "Desperdicio por Día (kg)"
                ws_chart.Cells(start_row_desp, 1).Font.Bold = True
                ws_chart.Cells(start_row_desp, 1).Font.Size = 12
                ws_chart.Cells(start_row_desp + 1, 1).Value = "Fecha"
                ws_chart.Cells(start_row_desp + 1, 2).Value = "Kilos"
                ws_chart.Cells(start_row_desp + 1, 1).Font.Bold = True
                ws_chart.Cells(start_row_desp + 1, 2).Font.Bold = True
                for i, (dia, kilos) in enumerate(sorted(desperdicio_dia.items()), start_row_desp + 2):
                    ws_chart.Cells(i, 1).Value = dia
                    ws_chart.Cells(i, 2).Value = round(kilos, 2)
                chart1 = ws_chart.ChartObjects().Add(350, 120, 400, 250)
                chart1.Chart.ChartType = 51  # xlColumnClustered
                chart1.Chart.SetSourceData(ws_chart.Range(
                    ws_chart.Cells(start_row_desp + 1, 1),
                    ws_chart.Cells(start_row_desp + 1 + len(desperdicio_dia), 2)
                ))
                chart1.Chart.HasLegend = False
                chart1.Chart.ChartTitle.Text = "Desperdicio por Día (kg)"
                chart1.Chart.ChartTitle.Font.Size = 10

            # ── CHART 2: Destino (pie chart) ──
            if data["destinos"]:
                start_row_dest = 7
                ws_chart.Cells(start_row_dest, 4).Value = "Distribución por Destino"
                ws_chart.Cells(start_row_dest, 4).Font.Bold = True
                ws_chart.Cells(start_row_dest, 4).Font.Size = 12
                ws_chart.Cells(start_row_dest + 1, 4).Value = "Destino"
                ws_chart.Cells(start_row_dest + 1, 5).Value = "Cantidad (kg)"
                ws_chart.Cells(start_row_dest + 1, 4).Font.Bold = True
                ws_chart.Cells(start_row_dest + 1, 5).Font.Bold = True
                for i, row in enumerate(data["destinos"], start_row_dest + 2):
                    ws_chart.Cells(i, 4).Value = row["destino_actual"]
                    ws_chart.Cells(i, 5).Value = round(row["cantidad_total"], 2)
                chart2 = ws_chart.ChartObjects().Add(780, 120, 400, 250)
                chart2.Chart.ChartType = 5  # xlPie
                chart2.Chart.SetSourceData(ws_chart.Range(
                    ws_chart.Cells(start_row_dest + 1, 4),
                    ws_chart.Cells(start_row_dest + 1 + len(data["destinos"]), 5)
                ))
                chart2.Chart.HasLegend = True
                chart2.Chart.ChartTitle.Text = "Distribución por Destino"
                chart2.Chart.ChartTitle.Font.Size = 10

            # ── CHART 3: Top productos sobrantes ──
            if data["top_productos"]:
                top = data["top_productos"][:10]
                start_row_top = 24
                ws_chart.Cells(start_row_top, 1).Value = "Top Productos Sobrantes"
                ws_chart.Cells(start_row_top, 1).Font.Bold = True
                ws_chart.Cells(start_row_top, 1).Font.Size = 12
                ws_chart.Cells(start_row_top + 1, 1).Value = "Producto"
                ws_chart.Cells(start_row_top + 1, 2).Value = "Cantidad (kg)"
                ws_chart.Cells(start_row_top + 1, 1).Font.Bold = True
                ws_chart.Cells(start_row_top + 1, 2).Font.Bold = True
                for i, row in enumerate(top, start_row_top + 2):
                    ws_chart.Cells(i, 1).Value = row["producto_sopro"]
                    ws_chart.Cells(i, 2).Value = round(row["cantidad_total"], 2)
                chart3 = ws_chart.ChartObjects().Add(350, 400, 400, 250)
                chart3.Chart.ChartType = 51  # xlColumnClustered
                chart3.Chart.SetSourceData(ws_chart.Range(
                    ws_chart.Cells(start_row_top + 1, 1),
                    ws_chart.Cells(start_row_top + 1 + len(top), 2)
                ))
                chart3.Chart.HasLegend = False
                chart3.Chart.ChartTitle.Text = "Top Productos Sobrantes (kg)"
                chart3.Chart.ChartTitle.Font.Size = 10

            # ── CHART 4: Días con mayor desperdicio ──
            if desperdicio_dia:
                sorted_desp = sorted(desperdicio_dia.items(), key=lambda x: x[1], reverse=True)[:5]
                start_row_desp_top = 24
                ws_chart.Cells(start_row_desp_top, 4).Value = "Días con Mayor Desperdicio"
                ws_chart.Cells(start_row_desp_top, 4).Font.Bold = True
                ws_chart.Cells(start_row_desp_top, 4).Font.Size = 12
                ws_chart.Cells(start_row_desp_top + 1, 4).Value = "Día"
                ws_chart.Cells(start_row_desp_top + 1, 5).Value = "Kilos"
                ws_chart.Cells(start_row_desp_top + 1, 4).Font.Bold = True
                ws_chart.Cells(start_row_desp_top + 1, 5).Font.Bold = True
                for i, (dia, kilos) in enumerate(sorted_desp, start_row_desp_top + 2):
                    ws_chart.Cells(i, 4).Value = dia
                    ws_chart.Cells(i, 5).Value = round(kilos, 2)
                chart4 = ws_chart.ChartObjects().Add(780, 400, 400, 250)
                chart4.Chart.ChartType = 51
                chart4.Chart.SetSourceData(ws_chart.Range(
                    ws_chart.Cells(start_row_desp_top + 1, 4),
                    ws_chart.Cells(start_row_desp_top + 1 + len(sorted_desp), 5)
                ))
                chart4.Chart.HasLegend = False
                chart4.Chart.ChartTitle.Text = "Días con Mayor Desperdicio (Top 5)"
                chart4.Chart.ChartTitle.Font.Size = 10

            ws_chart.Columns("A:E").AutoFit()

            # Save as .xlsx (save as CSV won't work with charts)
            xlsx_path = filepath.replace(".csv", ".xlsx")
            wb.SaveAs(xlsx_path)
            wb.Close()
            excel.Quit()
            return xlsx_path

        except (ImportError, OSError, AttributeError):
            # Fallback: CSV simple si no hay Excel
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["DASHBOARD DE SOBRANTES REUTILIZABLES"])
                writer.writerow([f"Periodo: últimos {dias} días"])
                writer.writerow([])
                writer.writerow(["SOBRANTES POR TURNO Y DÍA"])
                writer.writerow(["Fecha", "Turno", "Total", "Cantidad", "Productos"])
                for row in data["sobrantes_por_turno"]:
                    writer.writerow([
                        row.get("fecha_registro", ""),
                        row.get("turno", ""),
                        row.get("total_sobrantes", 0),
                        f"{row.get('cantidad_total', 0):.2f}",
                        row.get("productos", "")
                    ])
                writer.writerow([])
                writer.writerow(["DESTINO DE SOBRANTES"])
                writer.writerow(["Destino", "Registros", "Cantidad"])
                for row in data["destinos"]:
                    writer.writerow([
                        row.get("destino_actual", ""),
                        row.get("total", 0),
                        f"{row.get('cantidad_total', 0):.2f}"
                    ])
                writer.writerow([])
                writer.writerow(["TOP PRODUCTOS"])
                writer.writerow(["Producto", "Cantidad", "Unidad", "Veces"])
                for row in data["top_productos"]:
                    writer.writerow([
                        row.get("producto_sopro", ""),
                        f"{row.get('cantidad_total', 0):.2f}",
                        row.get("unidad", ""),
                        row.get("veces_registrado", 0)
                    ])
            return filepath
