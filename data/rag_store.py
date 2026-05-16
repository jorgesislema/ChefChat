"""
Almacén Persistente de Documentos RAG para ChefChat

Guarda y recupera documentos clasificados en SQLite:
- Recetas
- Catálogo de Inventario
- Lotes de Inventario
- Manuales/Procedimientos BPM
- Documentos Genéricos
"""

import sqlite3
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from core.rag_classifier import (
    procesar_documento_rag,
    DocumentoRAG,
    cargar_documentos_rag
)


class RAGStore:
    """
    Gestor de persistencia para documentos RAG.
    
    Almacena documentos clasificados en SQLite con metadata
    estructurada para búsqueda semántica.
    """

    def __init__(self, db_path: str = "chefchat.db") -> None:
        """
        Inicializa el almacén RAG.
        
        Args:
            db_path: Ruta a la base de datos SQLite.
        """
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones SQLite."""
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

    def _init_tables(self) -> None:
        """Inicializa tablas para documentos RAG."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS DocumentosRAG (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    path TEXT NOT NULL,
                    extension TEXT,
                    tamano_bytes INTEGER,
                    columnas TEXT,
                    filas INTEGER,
                    contenido_preview TEXT,
                    fecha_ingreso DATETIME DEFAULT CURRENT_TIMESTAMP,
                    estado TEXT DEFAULT 'activo'
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS RecetasRAG (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento_id INTEGER,
                    id_receta TEXT,
                    nombre TEXT NOT NULL,
                    categoria TEXT,
                    tiempo_prep INTEGER,
                    costo REAL,
                    ingredientes_json TEXT,
                    alergenos TEXT,
                    instrucciones TEXT,
                    FOREIGN KEY (documento_id) REFERENCES DocumentosRAG(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS DocumentosTexto (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento_id INTEGER,
                    contenido_completo TEXT,
                    palabras_clave TEXT,
                    FOREIGN KEY (documento_id) REFERENCES DocumentosRAG(id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documentos_tipo 
                ON DocumentosRAG(tipo)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documentos_estado 
                ON DocumentosRAG(estado)
            """)

    def guardar_documento(self, metadata: Dict[str, Any]) -> int:
        """
        Guarda un documento clasificado en la base de datos.
        
        Args:
            metadata: Metadata del documento desde procesar_documento_rag().
            
        Returns:
            int: ID del documento guardado.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO DocumentosRAG 
                (tipo, nombre, path, extension, tamano_bytes, columnas, filas, contenido_preview)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata["tipo"],
                metadata["nombre"],
                metadata["path"],
                metadata.get("extension", ""),
                metadata.get("tamano_bytes", 0),
                json.dumps(metadata.get("columnas", [])),
                metadata.get("filas", 0),
                metadata.get("contenido_preview", "")
            ))
            
            doc_id = cursor.lastrowid
            
            if metadata["tipo"] == DocumentoRAG.RECETA:
                self._guardar_recetas_csv(metadata, doc_id, conn)
            elif metadata["tipo"] in [DocumentoRAG.MANUAL_BPM, DocumentoRAG.GENERICO]:
                self._guardar_documento_texto(metadata, doc_id, conn)
            
            return doc_id

    def _guardar_recetas_csv(self, metadata: Dict[str, Any], doc_id: int, conn) -> None:
        """Guarda recetas desde CSV en tabla RecetasRAG."""
        path = metadata["path"]
        
        try:
            cursor = conn.cursor()
            recetas_guardadas = 0
            recetas_duplicadas = 0
            recetas_actualizadas = 0
            
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Soporte para múltiples nombres de columna
                    id_receta = (row.get('id_receta') or row.get('ID_Receta') or 
                                row.get('id') or row.get('ID') or '').strip()
                    nombre = (row.get('nombre') or row.get('Nombre_Plato') or 
                             row.get('nombre_plato') or '').strip()
                    categoria = (row.get('categoria') or row.get('Categoria') or 
                                row.get('Categoría') or '').strip()
                    tiempo_prep = (row.get('tiempo_prep') or row.get('Tiempo_Prep_Min') or 
                                  row.get('tiempo') or '0')
                    costo = (row.get('costo') or row.get('Costo_Estimado_USD') or 
                            row.get('costo_estimado') or '0')
                    ingredientes = (row.get('Ingredientes_Estructurados') or 
                                   row.get('ingredientes_json') or 
                                   row.get('ingredientes') or '')
                    alergenos = (row.get('alergenos') or row.get('Alergenos') or 
                                row.get('alérgenos') or 'ninguno')
                    instrucciones = (row.get('instrucciones') or row.get('Instrucciones') or 
                                    row.get('preparacion') or '')
                    
                    # Verificar si ya existe por id_receta o nombre
                    cursor.execute("""
                        SELECT id, nombre FROM RecetasRAG 
                        WHERE id_receta = ? OR nombre = ?
                    """, (id_receta, nombre))
                    
                    existente = cursor.fetchone()
                    
                    if existente:
                        recetas_duplicadas += 1
                        
                        # Verificar si hay cambios reales
                        cursor.execute("""
                            SELECT nombre, categoria, tiempo_prep, costo, 
                                   ingredientes_json, alergenos, instrucciones
                            FROM RecetasRAG WHERE id = ?
                        """, (existente[0],))
                        
                        receta_actual = cursor.fetchone()
                        
                        # Comparar si hay diferencias
                        hay_cambios = (
                            receta_actual[1] != categoria or
                            (receta_actual[2] != (int(tiempo_prep) if tiempo_prep else 0)) or
                            (receta_actual[3] != (float(costo) if costo else 0.0)) or
                            receta_actual[4] != ingredientes or
                            receta_actual[5] != alergenos or
                            receta_actual[6] != instrucciones
                        )
                        
                        if hay_cambios:
                            cursor.execute("""
                                UPDATE RecetasRAG 
                                SET documento_id = ?, categoria = ?, tiempo_prep = ?, 
                                    costo = ?, ingredientes_json = ?, alergenos = ?, 
                                    instrucciones = ?
                                WHERE id = ?
                            """, (
                                doc_id,
                                categoria,
                                int(tiempo_prep) if tiempo_prep else 0,
                                float(costo) if costo else 0.0,
                                ingredientes,
                                alergenos,
                                instrucciones,
                                existente[0]
                            ))
                            recetas_actualizadas += 1
                            print(f"  [ACT] Actualizada: {nombre}")
                        else:
                            print(f"  [DUP] Duplicada (sin cambios): {nombre}")
                    else:
                        # Insertar nueva
                        cursor.execute("""
                            INSERT INTO RecetasRAG 
                            (documento_id, id_receta, nombre, categoria, tiempo_prep, 
                             costo, ingredientes_json, alergenos, instrucciones)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            doc_id,
                            id_receta,
                            nombre,
                            categoria,
                            int(tiempo_prep) if tiempo_prep else 0,
                            float(costo) if costo else 0.0,
                            ingredientes,
                            alergenos,
                            instrucciones
                        ))
                        recetas_guardadas += 1
                        print(f"  [NEW] Nueva: {nombre}")
            
            print(f"\n  Resumen: {recetas_guardadas} nuevas, {recetas_actualizadas} actualizadas, {recetas_duplicadas} duplicadas")
            
        except Exception as e:
            print(f"Error guardando recetas: {e}")

    def _guardar_documento_texto(self, metadata: Dict[str, Any], doc_id: int, conn) -> None:
        """Guarda contenido completo de documentos de texto."""
        path = metadata["path"]
        
        try:
            cursor = conn.cursor()
            with open(path, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
                palabras_clave = self._extraer_palabras_clave(contenido)
                
                cursor.execute("""
                    INSERT INTO DocumentosTexto 
                    (documento_id, contenido_completo, palabras_clave)
                    VALUES (?, ?, ?)
                """, (doc_id, contenido, json.dumps(palabras_clave)))
        except Exception as e:
            print(f"Error guardando documento texto: {e}")

    def _extraer_palabras_clave(self, contenido: str, max_palabras: int = 20) -> List[str]:
        """Extrae palabras clave de un documento de texto."""
        palabras_comunes = {
            'el', 'la', 'los', 'las', 'de', 'del', 'al', 'con', 'para', 'por',
            'en', 'es', 'son', 'ser', 'esta', 'este', 'como', 'que', 'se', 'un',
            'una', 'unos', 'unas', 'y', 'o', 'pero', 'si', 'no', 'mas', 'menos'
        }
        
        palabras = contenido.lower().split()
        frecuencia = {}
        
        for palabra in palabras:
            palabra_limpia = ''.join(c for c in palabra if c.isalnum())
            if palabra_limpia and palabra_limpia not in palabras_comunes and len(palabra_limpia) > 3:
                frecuencia[palabra_limpia] = frecuencia.get(palabra_limpia, 0) + 1
        
        ordenadas = sorted(frecuencia.items(), key=lambda x: x[1], reverse=True)
        return [p[0] for p in ordenadas[:max_palabras]]

    def guardar_lotes_inventario(self, metadata: Dict[str, Any], db_manager) -> int:
        """
        Guarda lotes de inventario evitando duplicados.
        
        Args:
            metadata: Metadata del documento.
            db_manager: DatabaseManager para guardar en tablas existentes.
            
        Returns:
            int: ID del documento guardado.
        """
        doc_id = self.guardar_documento(metadata)
        path = metadata["path"]
        
        try:
            lotes_guardados = 0
            lotes_duplicados = 0
            lotes_actualizados = 0
            
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    id_lote = row.get('id_lote', '').strip()
                    producto_id = row.get('producto_id', '').strip()
                    fecha_ingreso = row.get('fecha_ingreso', datetime.now().strftime('%Y-%m-%d'))
                    cantidad = float(row.get('cantidad_actual', 0))
                    unidad = row.get('unidad', 'unidad')
                    fecha_caducidad = row.get('fecha_caducidad_fija', None)
                    if fecha_caducidad == '':
                        fecha_caducidad = None
                    
                    with db_manager._get_connection() as conn:
                        cursor = conn.cursor()
                        
                        # Verificar duplicado por id_lote
                        cursor.execute("""
                            SELECT id, cantidad_actual, fecha_caducidad_fija 
                            FROM Inventario WHERE id_lote = ?
                        """, (id_lote,))
                        
                        existente = cursor.fetchone()
                        
                        # Si no tiene id_lote, buscar por producto_id + fecha_ingreso
                        if existente is None and not id_lote:
                            cursor.execute("""
                                SELECT id, cantidad_actual FROM Inventario 
                                WHERE producto_id = ? AND fecha_ingreso = ?
                            """, (producto_id, fecha_ingreso))
                            existente = cursor.fetchone()
                        
                        if existente:
                            lotes_duplicados += 1
                            
                            # Actualizar cantidad si hay cambios
                            cursor.execute("""
                                UPDATE Inventario 
                                SET cantidad_actual = ?, fecha_caducidad_fija = ?
                                WHERE id = ?
                            """, (cantidad, fecha_caducidad, existente[0]))
                            lotes_actualizados += 1
                            print(f"  [ACT] Actualizado: {id_lote or producto_id}")
                        else:
                            cursor.execute("""
                                INSERT INTO Inventario 
                                (producto_id, fecha_ingreso, cantidad_actual, unidad, fecha_caducidad_fija)
                                VALUES (?, ?, ?, ?, ?)
                            """, (producto_id, fecha_ingreso, cantidad, unidad, fecha_caducidad))
                            lotes_guardados += 1
                            print(f"  [NEW] Nuevo: {id_lote or producto_id}")
            
            print(f"\n  Resumen: {lotes_guardados} nuevos, {lotes_actualizados} actualizados, {lotes_duplicados} duplicados")
                    
        except Exception as e:
            print(f"Error guardando lotes: {e}")
        
        return doc_id

    def guardar_catalogo(self, metadata: Dict[str, Any], db_manager) -> int:
        """
        Guarda catálogo de productos evitando duplicados.
        
        Args:
            metadata: Metadata del documento.
            db_manager: DatabaseManager para guardar en tablas existentes.
            
        Returns:
            int: ID del documento guardado.
        """
        doc_id = self.guardar_documento(metadata)
        path = metadata["path"]
        
        try:
            productos_guardados = 0
            productos_duplicados = 0
            productos_actualizados = 0
            
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    nombre = row.get('nombre', '').strip().title()
                    categoria = row.get('categoria', '').strip().title()
                    vida_util = int(row.get('vida_util_dias', 30))
                    
                    # Verificar duplicado por nombre
                    with db_manager._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT id, vida_util_dias, categoria 
                            FROM Catalogo WHERE nombre = ?
                        """, (nombre,))
                        
                        existente = cursor.fetchone()
                        
                        if existente:
                            productos_duplicados += 1
                            
                            # Verificar si hay cambios
                            hay_cambios = (
                                existente[1] != vida_util or
                                existente[2] != categoria
                            )
                            
                            if hay_cambios:
                                cursor.execute("""
                                    UPDATE Catalogo 
                                    SET vida_util_dias = ?, categoria = ?
                                    WHERE id = ?
                                """, (vida_util, categoria, existente[0]))
                                productos_actualizados += 1
                                print(f"  [ACT] Actualizado: {nombre}")
                            else:
                                print(f"  [DUP] Duplicado (sin cambios): {nombre}")
                        else:
                            db_manager.insertar_catalogo(nombre, categoria, vida_util)
                            productos_guardados += 1
                            print(f"  [NEW] Nuevo: {nombre}")
            
            print(f"\n  Resumen: {productos_guardados} nuevos, {productos_actualizados} actualizados, {productos_duplicados} duplicados")
            
        except Exception as e:
            print(f"Error guardando catálogo: {e}")
        
        return doc_id

    def guardar_documentos(self, file_paths: List[str], db_manager) -> Dict[str, Any]:
        """
        Guarda múltiples documentos en la base de datos.
        
        Args:
            file_paths: Lista de rutas de archivos.
            db_manager: DatabaseManager para operaciones CRUD.
            
        Returns:
            Dict: Resumen de documentos guardados.
        """
        resultados = {
            "total": len(file_paths),
            "guardados": 0,
            "recetas": 0,
            "catalogo": 0,
            "lotes": 0,
            "manuales": 0,
            "genericos": 0,
            "errores": [],
            "documentos_ids": []
        }
        
        for file_path in file_paths:
            try:
                metadata = procesar_documento_rag(file_path)
                doc_id = self.guardar_documento(metadata)
                resultados["documentos_ids"].append(doc_id)
                resultados["guardados"] += 1
                
                tipo = metadata["tipo"]
                
                if tipo == DocumentoRAG.RECETA:
                    resultados["recetas"] += 1
                elif tipo == DocumentoRAG.CATALOGO:
                    self.guardar_catalogo(metadata, db_manager)
                    resultados["catalogo"] += 1
                elif tipo == DocumentoRAG.LOTES:
                    self.guardar_lotes_inventario(metadata, db_manager)
                    resultados["lotes"] += 1
                elif tipo == DocumentoRAG.MANUAL_BPM:
                    resultados["manuales"] += 1
                else:
                    resultados["genericos"] += 1
                    
            except Exception as e:
                resultados["errores"].append(f"{Path(file_path).name}: {str(e)}")
        
        return resultados

    def obtener_documentos_por_tipo(self, tipo: str) -> List[Dict[str, Any]]:
        """
        Obtiene documentos por tipo.
        
        Args:
            tipo: Tipo de documento (receta, catalogo_inventario, etc.).
            
        Returns:
            List[Dict]: Lista de documentos.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM DocumentosRAG 
                WHERE tipo = ? AND estado = 'activo'
                ORDER BY fecha_ingreso DESC
            """, (tipo,))
            
            return [dict(row) for row in cursor.fetchall()]

    def obtener_recetas(self) -> List[Dict[str, Any]]:
        """Obtiene todas las recetas guardadas."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.*, d.nombre as documento_nombre
                FROM RecetasRAG r
                JOIN DocumentosRAG d ON r.documento_id = d.id
                WHERE d.estado = 'activo'
                ORDER BY r.nombre
            """)
            
            return [dict(row) for row in cursor.fetchall()]

    def buscar_documento(self, query: str) -> List[Dict[str, Any]]:
        """
        Busca documentos por palabras clave.
        
        Args:
            query: Término de búsqueda.
            
        Returns:
            List[Dict]: Documentos encontrados.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT d.*, t.palabras_clave
                FROM DocumentosRAG d
                LEFT JOIN DocumentosTexto t ON d.id = t.documento_id
                WHERE d.estado = 'activo'
                AND (
                    d.nombre LIKE ? OR
                    d.columnas LIKE ? OR
                    t.palabras_clave LIKE ?
                )
                ORDER BY d.fecha_ingreso DESC
            """, (f'%{query}%', f'%{query}%', f'%{query}%'))
            
            return [dict(row) for row in cursor.fetchall()]

    def eliminar_documento(self, doc_id: int) -> bool:
        """
        Elimina lógicamente un documento.
        
        Args:
            doc_id: ID del documento.
            
        Returns:
            bool: True si se eliminó correctamente.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE DocumentosRAG 
                SET estado = 'eliminado' 
                WHERE id = ?
            """, (doc_id,))
            
            return cursor.rowcount > 0

    def contar_documentos(self) -> Dict[str, int]:
        """
        Cuenta documentos por tipo.
        
        Returns:
            Dict: Conteo por tipo.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tipo, COUNT(*) as cantidad
                FROM DocumentosRAG
                WHERE estado = 'activo'
                GROUP BY tipo
            """)
            
            return {row["tipo"]: row["cantidad"] for row in cursor.fetchall()}
