"""
Script para cargar documentos de capacitaciÃ³n en ChefChat RAG

Busca archivos .md en carpetas comunes y los guarda en la base de datos.
"""

from pathlib import Path
from data.rag_store import RAGStore
from data.db_manager import DatabaseManager
from core.rag_classifier import generar_resumen_carga

def buscar_documentos_capacitacion():
    """Busca archivos MD en el proyecto."""
    paths_busqueda = [
        Path("documents"),
        Path("docs"),
        Path("uploads"),
        Path("data_source/capacitacion"),
        Path("data_source/manuales"),
        Path("data_source/md"),
    ]
    
    archivos_encontrados = []
    
    for path_base in paths_busqueda:
        if path_base.exists():
            archivos = list(path_base.glob("**/*.md"))
            archivos_encontrados.extend(archivos)
            print(f"ðŸ“‚ {path_base}: {len(archivos)} archivos encontrados")
    
    if not archivos_encontrados:
        print("\nâš  No se encontraron carpetas de documentos")
        print("\nÂ¿En quÃ© carpeta guardaste los archivos MD de capacitaciÃ³n?")
        print("Ejemplos:")
        print("  - documents/")
        print("  - capacitacion/")
        print("  - manuales/")
        print("  - uploads/")
    
    return archivos_encontrados

def cargar_capacitacion():
    """Carga documentos de capacitaciÃ³n en RAG."""
    print("ðŸ“š Buscando documentos de capacitaciÃ³n...\n")
    
    archivos = buscar_documentos_capacitacion()
    
    if not archivos:
        return
    
    print(f"\nâœ… Total archivos encontrados: {len(archivos)}")
    
    db = DatabaseManager("chefchat.db")
    store = RAGStore("chefchat.db")
    
    file_paths = [str(f) for f in archivos]
    
    print("\nðŸ“¥ Guardando documentos en base de datos...")
    resultados = store.guardar_documentos(file_paths, db)
    
    print("\n" + "="*50)
    print(generar_resumen_carga(resultados))
    print("="*50)
    
    print(f"\nâœ… Documentos guardados: {resultados['guardados']}/{resultados['total']}")
    
    if resultados["manuales"] > 0:
        print(f"   ðŸ“˜ Manuales BPM: {resultados['manuales']}")
    if resultados["genericos"] > 0:
        print(f"   ðŸ“„ GenÃ©ricos: {resultados['genericos']}")
    
    if resultados["errores"]:
        print(f"\nâš  Errores: {len(resultados['errores'])}")
        for error in resultados["errores"][:5]:
            print(f"   - {error}")

if __name__ == "__main__":
    cargar_capacitacion()
