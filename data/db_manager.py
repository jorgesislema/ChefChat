"""
Gestor de Base de Datos para ChefChat Pro - SQLite

Este módulo implementa la capa de persistencia usando SQLite con
context managers para manejo seguro de conexiones y transacciones.
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager
from pathlib import Path

from core.models import (
    Catalogo, Inventario, VistaCaducidad, BitacoraDiaria,
    VentasHistoricas, Receta
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
        """
        Inicializa todas las tablas y vistas de la base de datos.
        
        Crea las siguientes estructuras:
        - Catalogo: Productos del restaurante
        - Inventario: Registro de entradas de productos
        - Vista_Caducidad: Vista SQL para cálculo de caducidad
        - Bitacora_Diaria: Registro de incidencias
        - Ventas_Historicas: Histórico de ventas
        - Recetas: Recetario del restaurante
        """
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
                CREATE TABLE IF NOT EXISTS Inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL,
                    fecha_ingreso DATE NOT NULL,
                    cantidad REAL NOT NULL CHECK(cantidad > 0),
                    unidad TEXT NOT NULL,
                    FOREIGN KEY (producto_id) REFERENCES Catalogo(id)
                )
            """)
            
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS Vista_Caducidad AS
                SELECT 
                    i.id as inventario_id,
                    c.nombre as producto_nombre,
                    c.categoria,
                    i.fecha_ingreso,
                    i.cantidad,
                    i.unidad,
                    c.vida_util_dias,
                    date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days') as fecha_caducidad_efectiva,
                    CAST(julianday(date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days')) - julianday(date('now')) AS INTEGER) as dias_restantes
                FROM Inventario i
                JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad > 0
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

    def insertar_catalogo(self, nombre: str, categoria: str, vida_util_dias: int) -> int:
        """
        Inserta un nuevo producto en el catálogo.
        
        Args:
            nombre: Nombre del producto.
            categoria: Categoría (Fresco, Congelado, Seco, etc.).
            vida_util_dias: Días de vida útil.
            
        Returns:
            int: ID del producto insertado.
            
        Example:
            db.insertar_catalogo("Fresa", "Fresco", 8)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Catalogo (nombre, categoria, vida_util_dias) VALUES (?, ?, ?)",
                (nombre.strip().title(), categoria.strip().title(), vida_util_dias)
            )
            return cursor.lastrowid

    def insertar_inventario(
        self, producto_id: int, cantidad: float, unidad: str, 
        fecha_ingreso: Optional[date] = None
    ) -> int:
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
                    
                lote_id, cantidad_lote, producto_id = lote
                
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

    def registrar_incidencia(self, categoria: str, descripcion: str) -> int:
        """
        Registra una incidencia en la bitácora diaria.
        
        Args:
            categoria: Categoría de la incidencia.
            descripcion: Descripción detallada.
            
        Returns:
            int: ID del registro insertado.
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
            return cursor.lastrowid

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
            return cursor.lastrowid

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