"""
Clasificador Automático de Documentos RAG para ChefChat

Detecta automáticamente el tipo de documento cargado:
- Recetas
- Catálogo de Inventario
- Lotes de Inventario
- Manuales/Procedimientos (BPM)
- Genérico
"""

from pathlib import Path
from typing import Dict, Any, List
import csv


class DocumentoRAG:
    """Enum de tipos de documento RAG."""
    RECETA = "receta"
    CATALOGO = "catalogo_inventario"
    LOTES = "lotes_inventario"
    MANUAL_BPM = "manual_bpm"
    GENERICO = "generico"


def detectar_tipo_documento(file_path: str) -> str:
    """
    Detecta automáticamente el tipo de documento basado en:
    1. Nombre del archivo
    2. Columnas (si es CSV)
    3. Contenido (si es TXT/MD)
    
    Args:
        file_path: Ruta completa al archivo.
        
    Returns:
        str: Tipo de documento detectado.
    """
    path = Path(file_path)
    nombre = path.name.lower()
    extension = path.suffix.lower()
    
    # 1. Detectar por patrón de nombre
    if "receta" in nombre or "recipe" in nombre:
        return DocumentoRAG.RECETA
    elif "catalogo" in nombre or "catalog" in nombre or "producto" in nombre:
        return DocumentoRAG.CATALOGO
    elif "lote" in nombre or "batch" in nombre or "inventario" in nombre:
        return DocumentoRAG.LOTES
    elif "manual" in nombre or "bpm" in nombre or "procedimiento" in nombre:
        return DocumentoRAG.MANUAL_BPM
    
    # 2. Detectar por contenido (CSV)
    if extension == ".csv":
        try:
            # Detectar delimitador
            with open(file_path, 'r', encoding='utf-8') as f:
                first = f.readline()
                tabs = first.count('\t')
                comas = first.count(',')
                delim = '\t' if tabs > comas else ','
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=delim)
                headers = next(reader, [])
                headers_lower = [h.lower().strip() for h in headers]
                headers_text = " ".join(headers_lower)
                
                # Patrones de columnas para recetas
                if any(col in headers_lower for col in ["ingredientes", "ingredientes_json", "ingredientes_estructurados"]):
                    return DocumentoRAG.RECETA
                if "id_receta" in headers_lower or "tiempo_prep" in headers_lower:
                    return DocumentoRAG.RECETA
                
                # Patrones para catálogo
                if "id_producto" in headers_lower or "tipo_caducidad" in headers_lower:
                    return DocumentoRAG.CATALOGO
                if "vida_util_dias" in headers_lower and "categoria" in headers_text:
                    return DocumentoRAG.CATALOGO
                
                # Patrones para lotes
                if "id_lote" in headers_lower or "fecha_caducidad_fija" in headers_lower:
                    return DocumentoRAG.LOTES
                if "fecha_ingreso" in headers_lower and "cantidad_actual" in headers_lower:
                    return DocumentoRAG.LOTES
                
        except (OSError, csv.Error, UnicodeDecodeError) as e:
            print(f"Error leyendo CSV: {e}")
    
    # 3. Detectar por contenido (TXT/MD)
    if extension in [".txt", ".md"]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                contenido = f.read(1000)  # Leer primeros 1000 caracteres
                contenido_lower = contenido.lower()
                
                # Palabras clave para manuales BPM
                bpm_keywords = ["procedimiento", "instrucción", "paso", "bpm", 
                               "manual", "operativo", "estándar", "norma"]
                bpm_count = sum(1 for kw in bpm_keywords if kw in contenido_lower)
                
                if bpm_count >= 2:
                    return DocumentoRAG.MANUAL_BPM
                
                # Palabras clave para recetas
                receta_keywords = ["ingrediente", "preparación", "receta", "cocinar",
                                  "tiempo de preparación", "comensales"]
                receta_count = sum(1 for kw in receta_keywords if kw in contenido_lower)
                
                if receta_count >= 2:
                    return DocumentoRAG.RECETA
                
        except (OSError, UnicodeDecodeError) as e:
            print(f"Error leyendo TXT/MD: {e}")
    
    # Default: genérico
    return DocumentoRAG.GENERICO


def procesar_documento_rag(file_path: str) -> Dict[str, Any]:
    """
    Procesa un documento RAG y devuelve metadata estructurada.
    
    Args:
        file_path: Ruta completa al archivo.
        
    Returns:
        Dict con: tipo, nombre, path, metadata, estado
    """
    path = Path(file_path)
    tipo = detectar_tipo_documento(file_path)
    
    metadata = {
        "tipo": tipo,
        "nombre": path.name,
        "path": str(path),
        "extension": path.suffix,
        "tamano_bytes": path.stat().st_size if path.exists() else 0,
        "columnas": [],
        "filas": 0,
        "contenido_preview": ""
    }
    
    # Extraer metadata específica por tipo
    if path.suffix.lower() == ".csv":
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if lines:
                tabs = lines[0].count('\t')
                comas = lines[0].count(',')
                delim = '\t' if tabs > comas else ','
                reader = csv.reader(lines, delimiter=delim)
                headers = next(reader, [])
                metadata["columnas"] = headers
                metadata["filas"] = len(lines) - 1
        except (OSError, csv.Error, UnicodeDecodeError) as e:
            metadata["error"] = str(e)
    
    elif path.suffix.lower() in [".txt", ".md"]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                contenido = f.read(500)
                metadata["contenido_preview"] = contenido[:200] + "..." if len(contenido) > 200 else contenido
                metadata["filas"] = contenido.count('\n') + 1
        except (OSError, UnicodeDecodeError) as e:
            metadata["error"] = str(e)
    
    # Mensaje descriptivo por tipo
    mensajes_tipo = {
        DocumentoRAG.RECETA: "📖 Receta detectada",
        DocumentoRAG.CATALOGO: "📦 Catálogo de inventario detectado",
        DocumentoRAG.LOTES: "📋 Lotes de inventario detectados",
        DocumentoRAG.MANUAL_BPM: "📘 Manual/Procedimiento BPM detectado",
        DocumentoRAG.GENERICO: "📄 Documento genérico detectado"
    }
    metadata["mensaje"] = mensajes_tipo.get(tipo, "Documento detectado")
    
    return metadata


def cargar_documentos_rag(file_paths: List[str]) -> Dict[str, Any]:
    """
    Procesa múltiples documentos y devuelve resumen de carga.
    
    Args:
        file_paths: Lista de rutas de archivos.
        
    Returns:
        Dict con resumen de documentos cargados por tipo.
    """
    recetas = 0
    catalogo = 0
    lotes = 0
    manuales = 0
    genericos = 0
    errores: List[str] = []
    documentos: List[Dict[str, Any]] = []
    
    for file_path in file_paths:
        try:
            metadata = procesar_documento_rag(file_path)
            documentos.append(metadata)
            
            tipo = metadata.get("tipo")
            if tipo == DocumentoRAG.RECETA:
                recetas += 1
            elif tipo == DocumentoRAG.CATALOGO:
                catalogo += 1
            elif tipo == DocumentoRAG.LOTES:
                lotes += 1
            elif tipo == DocumentoRAG.MANUAL_BPM:
                manuales += 1
            else:
                genericos += 1
        except (OSError, ValueError) as e:
            errores.append(f"{Path(file_path).name}: {e}")
    
    return {
        "total": len(file_paths),
        "recetas": recetas,
        "catalogo": catalogo,
        "lotes": lotes,
        "manuales": manuales,
        "genericos": genericos,
        "errores": errores,
        "documentos": documentos
    }


def generar_resumen_carga(resultados: Dict[str, Any]) -> str:
    """
    Genera mensaje de resumen para mostrar al usuario.
    
    Args:
        resultados: Dict de cargar_documentos_rag().
        
    Returns:
        str: Mensaje formateado para el usuario.
    """
    lineas = [f"📚 Documentos procesados: {resultados['total']}"]
    
    if resultados["recetas"] > 0:
        lineas.append(f"  📖 Recetas: {resultados['recetas']}")
    if resultados["catalogo"] > 0:
        lineas.append(f"  📦 Catálogo: {resultados['catalogo']}")
    if resultados["lotes"] > 0:
        lineas.append(f"  📋 Lotes: {resultados['lotes']}")
    if resultados["manuales"] > 0:
        lineas.append(f"  📘 Manuales BPM: {resultados['manuales']}")
    if resultados["genericos"] > 0:
        lineas.append(f"  📄 Genéricos: {resultados['genericos']}")
    
    if resultados["errores"]:
        lineas.append(f"\n⚠️ Errores: {len(resultados['errores'])}")
        for error in resultados["errores"][:3]:  # Mostrar máx 3 errores
            lineas.append(f"  - {error}")
    
    return "\n".join(lineas)