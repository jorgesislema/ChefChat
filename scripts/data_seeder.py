"""
Data Seeder para ChefChat Pro - ETL de Inicialización

Este script ejecuta la ingesta de datos desde archivos CSV/JSON hacia
la base de datos SQLite local. Se ejecuta de forma independiente a la GUI.

Uso:
    python data_seeder.py

Estructura de datos esperada:
    data_source/
    ├── 1_recetas/
    │   └── *.csv (recetas con ingredientes estructurados)
    └── 3_inventario/
        ├── catalogo/
        │   └── *.csv (productos del catálogo)
        └── lotes/
            └── *.csv (lotes de inventario con fechas)
"""

import sqlite3
import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


# =============================================================================
# CONFIGURACIÓN DE RUTAS
# =============================================================================

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "test_restaurante.db"
DATA_SOURCE_DIR = BASE_DIR / "data_source"

RECETAS_DIR = DATA_SOURCE_DIR / "1_recetas"
CATALOGO_DIR = DATA_SOURCE_DIR / "3_inventario" / "catalogo"
LOTES_DIR = DATA_SOURCE_DIR / "3_inventario" / "lotes"


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def parsear_ingredientes_estructurados(texto: str) -> List[Dict[str, Any]]:
    """
    Parsea el string de ingredientes estructurados a lista de diccionarios JSON.
    
    Formato de entrada: "cantidad|unidad|ingrediente;cantidad|unidad|ingrediente;..."
    Ejemplo: "2|gr|sal;100|ml|agua;3|unidad|huevo"
    
    Args:
        texto: String con ingredientes en formato estructurado.
        
    Returns:
        List[Dict]: Lista de diccionarios con claves: cantidad, unidad, nombre.
        
    Example:
        >>> parsear_ingredientes_estructurados("2|gr|sal;100|ml|agua")
        [{"cantidad": 2.0, "unidad": "gr", "nombre": "sal"}, 
         {"cantidad": 100.0, "unidad": "ml", "nombre": "agua"}]
    """
    if not texto or pd.isna(texto):
        return []
    
    ingredientes = []
    texto = str(texto).strip()
    
    if not texto:
        return []
    
    partes = texto.split(";")
    
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
            
        elementos = parte.split("|")
        
        if len(elementos) >= 3:
            try:
                cantidad_str = elementos[0].strip().replace(",", ".")
                cantidad = float(cantidad_str)
                unidad = elementos[1].strip().lower()
                nombre = elementos[2].strip().title()
                
                ingredientes.append({
                    "cantidad": cantidad,
                    "unidad": unidad,
                    "nombre": nombre
                })
            except (ValueError, IndexError) as e:
                print(f"⚠️ Warning: No se pudo parsear '{parte}': {e}")
                continue
    
    return ingredientes


def crear_conexion(db_path: Path) -> sqlite3.Connection:
    """
    Crea conexión SQLite con configuración optimizada.
    
    Args:
        db_path: Ruta al archivo de base de datos.
        
    Returns:
        sqlite3.Connection: Conexión configurada con row_factory.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def limpiar_tabla(conn: sqlite3.Connection, nombre_tabla: str) -> None:
    """
    Limpia todos los registros de una tabla.
    
    Args:
        conn: Conexión SQLite.
        nombre_tabla: Nombre de la tabla a limpiar.
    """
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {nombre_tabla}")
    conn.commit()


# =============================================================================
# PASO 1: CREACIÓN DE ESQUEMAS
# =============================================================================

def crear_esquemas(conn: sqlite3.Connection) -> None:
    """
    Crea todas las tablas y vistas si no existen.
    
    Tablas creadas:
    - recetas: Catálogo completo de recetas del restaurante.
    - catalogo_inventario: Productos base del inventario.
    - lotes_inventario: Lotes específicos con fechas y cantidades.
    
    Vistas creadas:
    - vista_caducidad_activa: Une lotes con catálogo, calcula caducidad.
    
    Args:
        conn: Conexión SQLite.
    """
    cursor = conn.cursor()
    
    print("\n[PASO 1] Creacion de esquemas...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recetas (
            id_receta TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            categoria TEXT,
            tiempo_prep INTEGER CHECK(tiempo_prep > 0),
            costo REAL CHECK(costo >= 0),
            ingredientes_json TEXT NOT NULL,
            alergenos TEXT,
            instrucciones TEXT
        )
    """)
    print("  [OK] Tabla 'recetas' creada")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS catalogo_inventario (
            id_producto TEXT PRIMARY KEY,
            nombre TEXT NOT NULL UNIQUE,
            categoria TEXT NOT NULL,
            tipo_caducidad TEXT CHECK(tipo_caducidad IN ('Dinamica', 'Fija')),
            vida_util_dias INTEGER CHECK(vida_util_dias > 0 AND vida_util_dias <= 365)
        )
    """)
    print("  [OK] Tabla 'catalogo_inventario' creada")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes_inventario (
            id_lote TEXT PRIMARY KEY,
            producto_id TEXT NOT NULL,
            fecha_ingreso DATE NOT NULL,
            cantidad_actual REAL NOT NULL CHECK(cantidad_actual >= 0),
            unidad TEXT NOT NULL,
            fecha_caducidad_fija DATE,
            FOREIGN KEY (producto_id) REFERENCES catalogo_inventario(id_producto)
        )
    """)
    print("  [OK] Tabla 'lotes_inventario' creada")
    
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS vista_caducidad_activa AS
        SELECT 
            l.id_lote,
            l.producto_id,
            c.nombre as nombre_producto,
            c.categoria,
            c.tipo_caducidad,
            c.vida_util_dias,
            l.fecha_ingreso,
            l.cantidad_actual,
            l.unidad,
            CASE 
                WHEN c.tipo_caducidad = 'Dinamica' 
                THEN date(l.fecha_ingreso, '+' || c.vida_util_dias || ' days')
                WHEN c.tipo_caducidad = 'Fija' 
                THEN l.fecha_caducidad_fija
                ELSE NULL
            END as fecha_caducidad_calculada,
            CAST(
                julianday(
                    CASE 
                        WHEN c.tipo_caducidad = 'Dinamica' 
                        THEN date(l.fecha_ingreso, '+' || c.vida_util_dias || ' days')
                        WHEN c.tipo_caducidad = 'Fija' 
                        THEN l.fecha_caducidad_fija
                        ELSE date('now')
                    END
                ) - julianday(date('now')) 
            AS INTEGER) as dias_restantes
        FROM lotes_inventario l
        JOIN catalogo_inventario c ON l.producto_id = c.id_producto
        WHERE l.cantidad_actual > 0
        ORDER BY dias_restantes ASC
    """)
    print("  [OK] Vista 'vista_caducidad_activa' creada")
    
    conn.commit()
    print("  [EXITO] Esquemas creados exitosamente")


# =============================================================================
# PASO 2: INGESTA DE RECETAS
# =============================================================================

def ingerir_recetas(conn: sqlite3.Connection) -> int:
    """
    Ingresa recetas desde archivos CSV en la carpeta 1_recetas/.
    
    Procesa la columna 'Ingredientes_Estructurados' convirtiéndola
    de formato "cantidad|unidad|ingrediente;..." a JSON array.
    
    Args:
        conn: Conexión SQLite.
        
    Returns:
        int: Número de recetas insertadas exitosamente.
    """
    print("\n[PASO 2] Ingesta de recetas...")
    
    if not RECETAS_DIR.exists():
        print(f"  [WARN] Directorio no encontrado: {RECETAS_DIR}")
        return 0
    
    archivos_csv = list(RECETAS_DIR.glob("*.csv"))
    
    if not archivos_csv:
        print(f"  [WARN] No se encontraron archivos CSV en {RECETAS_DIR}")
        return 0
    
    print(f"  [INFO] Encontrados {len(archivos_csv)} archivo(s) CSV")
    
    total_insertadas = 0
    
    for archivo in archivos_csv:
        try:
            print(f"  [FILE] Procesando: {archivo.name}")
            
            df = pd.read_csv(archivo, encoding="utf-8")
            
            columnas_requeridas = ["id_receta", "nombre", "Ingredientes_Estructurados"]
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if columnas_faltantes:
                raise ValueError(f"Columnas faltantes: {columnas_faltantes}")
            
            cursor = conn.cursor()
            
            for idx, row in df.iterrows():
                id_receta = str(row["id_receta"]).strip()
                nombre = str(row["nombre"]).strip()
                categoria = str(row.get("categoria", "General")).strip()
                tiempo_prep = int(row.get("tiempo_prep", 0)) if pd.notna(row.get("tiempo_prep")) else None
                costo = float(row.get("costo", 0)) if pd.notna(row.get("costo")) else 0.0
                alergenos = str(row.get("alergenos", "")).strip() if pd.notna(row.get("alergenos")) else ""
                instrucciones = str(row.get("instrucciones", "")).strip() if pd.notna(row.get("instrucciones")) else ""
                
                ingredientes_texto = str(row["Ingredientes_Estructurados"])
                ingredientes_json = parsear_ingredientes_estructurados(ingredientes_texto)
                ingredientes_json_str = json.dumps(ingredientes_json, ensure_ascii=False)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO recetas 
                    (id_receta, nombre, categoria, tiempo_prep, costo, 
                     ingredientes_json, alergenos, instrucciones)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (id_receta, nombre, categoria, tiempo_prep, costo,
                      ingredientes_json_str, alergenos, instrucciones))
                
                total_insertadas += 1
            
            conn.commit()
            print(f"    [OK] {len(df)} recetas insertadas")
            
        except Exception as e:
            print(f"    [ERROR] procesando {archivo.name}: {e}")
            continue
    
    print(f"  [EXITO] Total recetas insertadas: {total_insertadas}")
    return total_insertadas


# =============================================================================
# PASO 3: INGESTA DE INVENTARIO
# =============================================================================

def ingerir_catalogo_inventario(conn: sqlite3.Connection) -> int:
    """
    Ingresa productos del catálogo desde archivos CSV en 3_inventario/catalogo/.
    
    Args:
        conn: Conexión SQLite.
        
    Returns:
        int: Número de productos insertados exitosamente.
    """
    print("\n[PASO 3a] Ingesta de catalogo de inventario...")
    
    if not CATALOGO_DIR.exists():
        print(f"  [WARN] Directorio no encontrado: {CATALOGO_DIR}")
        return 0
    
    archivos_csv = list(CATALOGO_DIR.glob("*.csv"))
    
    if not archivos_csv:
        print(f"  [WARN] No se encontraron archivos CSV en {CATALOGO_DIR}")
        return 0
    
    print(f"  [INFO] Encontrados {len(archivos_csv)} archivo(s) CSV")
    
    total_insertados = 0
    
    for archivo in archivos_csv:
        try:
            print(f"  [FILE] Procesando: {archivo.name}")
            
            df = pd.read_csv(archivo, encoding="utf-8")
            
            columnas_requeridas = ["id_producto", "nombre", "categoria", "tipo_caducidad"]
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if columnas_faltantes:
                raise ValueError(f"Columnas faltantes: {columnas_faltantes}")
            
            cursor = conn.cursor()
            
            for idx, row in df.iterrows():
                id_producto = str(row["id_producto"]).strip()
                nombre = str(row["nombre"]).strip()
                categoria = str(row["categoria"]).strip()
                tipo_caducidad = str(row["tipo_caducidad"]).strip()
                
                if tipo_caducidad not in ["Dinamica", "Fija"]:
                    tipo_caducidad = "Dinamica"
                
                vida_util_dias = int(row.get("vida_util_dias", 7)) if pd.notna(row.get("vida_util_dias")) else 7
                
                cursor.execute("""
                    INSERT OR REPLACE INTO catalogo_inventario 
                    (id_producto, nombre, categoria, tipo_caducidad, vida_util_dias)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_producto, nombre, categoria, tipo_caducidad, vida_util_dias))
                
                total_insertados += 1
            
            conn.commit()
            print(f"    [OK] {len(df)} productos insertados")
            
        except Exception as e:
            print(f"    [ERROR] procesando {archivo.name}: {e}")
            continue
    
    print(f"  [EXITO] Total productos en catalogo: {total_insertados}")
    return total_insertados


def ingerir_lotes_inventario(conn: sqlite3.Connection) -> int:
    """
    Ingresa lotes de inventario desde archivos CSV en 3_inventario/lotes/.
    
    Args:
        conn: Conexión SQLite.
        
    Returns:
        int: Número de lotes insertados exitosamente.
    """
    print("\n[PASO 3b] Ingesta de lotes de inventario...")
    
    if not LOTES_DIR.exists():
        print(f"  [WARN] Directorio no encontrado: {LOTES_DIR}")
        return 0
    
    archivos_csv = list(LOTES_DIR.glob("*.csv"))
    
    if not archivos_csv:
        print(f"  [WARN] No se encontraron archivos CSV en {LOTES_DIR}")
        return 0
    
    print(f"  [INFO] Encontrados {len(archivos_csv)} archivo(s) CSV")
    
    total_insertados = 0
    
    for archivo in archivos_csv:
        try:
            print(f"  [FILE] Procesando: {archivo.name}")
            
            df = pd.read_csv(archivo, encoding="utf-8")
            
            columnas_requeridas = ["id_lote", "producto_id", "fecha_ingreso", "cantidad_actual", "unidad"]
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if columnas_faltantes:
                raise ValueError(f"Columnas faltantes: {columnas_faltantes}")
            
            cursor = conn.cursor()
            
            for idx, row in df.iterrows():
                id_lote = str(row["id_lote"]).strip()
                producto_id = str(row["producto_id"]).strip()
                fecha_ingreso = str(row["fecha_ingreso"]).strip()
                cantidad_actual = float(row["cantidad_actual"]) if pd.notna(row["cantidad_actual"]) else 0.0
                unidad = str(row["unidad"]).strip().lower()
                fecha_caducidad_fija = str(row.get("fecha_caducidad_fija", "")).strip() if pd.notna(row.get("fecha_caducidad_fija")) else None
                
                if fecha_caducidad_fija == "" or fecha_caducidad_fija == "NaT":
                    fecha_caducidad_fija = None
                
                cursor.execute("""
                    INSERT OR REPLACE INTO lotes_inventario 
                    (id_lote, producto_id, fecha_ingreso, cantidad_actual, unidad, fecha_caducidad_fija)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_lote, producto_id, fecha_ingreso, cantidad_actual, unidad, fecha_caducidad_fija))
                
                total_insertados += 1
            
            conn.commit()
            print(f"    [OK] {len(df)} lotes insertados")
            
        except Exception as e:
            print(f"    [ERROR] procesando {archivo.name}: {e}")
            continue
    
    print(f"  [EXITO] Total lotes insertados: {total_insertados}")
    return total_insertados


# =============================================================================
# FUNCIONES DE VERIFICACIÓN
# =============================================================================

def verificar_datos(conn: sqlite3.Connection) -> None:
    """
    Verifica y muestra resumen de datos cargados.
    
    Args:
        conn: Conexión SQLite.
    """
    print("\n[VERIFICACION] Datos cargados...")
    
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM recetas")
    print(f"  Recetas: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM catalogo_inventario")
    print(f"  Productos en catalogo: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM lotes_inventario")
    print(f"  Lotes en inventario: {cursor.fetchone()[0]}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM vista_caducidad_activa 
        WHERE dias_restantes <= 7 AND dias_restantes >= 0
    """)
    print(f"  [ALERTA] Productos por caducar (7 dias): {cursor.fetchone()[0]}")
    
    cursor.execute("""
        SELECT nombre_producto, cantidad_actual, dias_restantes 
        FROM vista_caducidad_activa 
        WHERE dias_restantes <= 7 AND dias_restantes >= 0
        ORDER BY dias_restantes ASC
        LIMIT 5
    """)
    
    print("\n  Top 5 productos por caducar:")
    for row in cursor.fetchall():
        print(f"    - {row[0]}: {row[1]} unidades ({row[2]} dias)")
    
    conn.commit()


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main() -> None:
    """
    Función principal que ejecuta todo el proceso ETL.
    
    Flujo:
    1. Crea esquemas de base de datos
    2. Ingresa recetas desde CSV
    3. Ingresa catálogo de inventario
    4. Ingresa lotes de inventario
    5. Verifica datos cargados
    """
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    print("=" * 60)
    print("ChefChat Pro - Data Seeder (ETL)")
    print("=" * 60)
    print(f"Base de datos: {DB_PATH}")
    print(f"Directorio datos: {DATA_SOURCE_DIR}")
    print("=" * 60)
    
    conn = None
    
    try:
        conn = crear_conexion(DB_PATH)
        print(f"✅ Conexión establecida: {DB_PATH}")
        
        crear_esquemas(conn)
        
        total_recetas = ingerir_recetas(conn)
        total_catalogo = ingerir_catalogo_inventario(conn)
        total_lotes = ingerir_lotes_inventario(conn)
        
        verificar_datos(conn)
        
        print("\n" + "=" * 60)
        print("ETL COMPLETADO EXITOSAMENTE")
        print("=" * 60)
        print(f"  [OK] Recetas: {total_recetas}")
        print(f"  [OK] Productos catalogo: {total_catalogo}")
        print(f"  [OK] Lotes inventario: {total_lotes}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR CRITICO] {e}")
        raise
    
    finally:
        if conn:
            conn.close()
            print("\n[INFO] Conexion cerrada")


if __name__ == "__main__":
    main()