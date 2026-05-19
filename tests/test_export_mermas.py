"""
Test específico para exportar reporte de mermas a Excel
"""

import logging
logging.basicConfig(level=logging.CRITICAL)

from core.config import ConfigManager, AIProvider
from data.db_manager import DatabaseManager
from agents.orchestrator import Orchestrator
import os

print("="*60)
print(" TEST: Exportar Mermas a Excel")
print("="*60)

# Configurar
db_path = os.path.join(os.path.dirname(__file__), "chefchat.db")
db = DatabaseManager(db_path=db_path)

provider = ConfigManager.get_configured_provider()
print(f"\n1. Provider: {provider}")

# Crear orchestrator
print("\n2. Creando Orchestrator...")
orchestrator = Orchestrator(
    provider=provider,
    model=None,
    db_manager=db
)
print(f"   [OK] Orchestrator creado")

# Simular mensaje de usuario
test_messages = [
    "envia el informe de la merma a excel",
    "dashboard de merma últimos 7 días a excel",
    "exporta reporte de mermas a word",
    "manda las mermas de la semana a excel",
]

print("\n3. Probando detección de comandos...")

for message in test_messages:
    print(f"\n   Mensaje: '{message}'")
    
    # Verificar si detecta mermas + excel
    tiene_merma = any(p in message for p in ["merma", "mermas", "desperdicio"])
    tiene_excel = "excel" in message
    tiene_word = "word" in message
    
    print(f"      - Detecta merma: {tiene_merma}")
    print(f"      - Detecta excel: {tiene_excel}")
    print(f"      - Detecta word: {tiene_word}")
    
    if tiene_merma and tiene_excel:
        print(f"      - [OK] Debería ejecutar: enviar_reporte_mermas_a_excel")
    elif tiene_merma and tiene_word:
        print(f"      - [OK] Debería ejecutar: enviar_reporte_mermas_a_word")

print("\n4. Ejecutando herramienta directamente...")

from agents.tools import crear_herramientas_operativas
tools = crear_herramientas_operativas(db)

# Buscar herramienta de exportar mermas a excel
tool = next((t for t in tools if t.name == "enviar_reporte_mermas_a_excel"), None)

if tool:
    print(f"   [OK] Herramienta encontrada: {tool.name}")
    print(f"   Descripción: {tool.description}")
    
    # Ejecutar
    print(f"\n5. Ejecutando herramienta (7 días)...")
    try:
        resultado = tool.func(7)
        print(f"   Resultado: {resultado[:200]}...")
    except Exception as e:
        print(f"   [ERROR] {e}")
else:
    print(f"   [ERROR] Herramienta no encontrada")

print("\n" + "="*60)
print(" TEST COMPLETADO")
print("="*60)
