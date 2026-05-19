"""
Test del flujo completo de procesamiento de menús
"""

import logging
logging.basicConfig(level=logging.CRITICAL, format='%(levelname)s:%(message)s')

from core.config import ConfigManager, AIProvider
from data.db_manager import DatabaseManager
from agents.orchestrator import Orchestrator
import os

print("="*60)
print(" TEST: Flujo Completo de Menús")
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

# Simular mensajes de usuario
test_messages = [
    "elabora un menu para el almuerso",
    "crea un menu para el desayuno incluye cerdo",
    "elabora el menu para el dia de mañana desayuno almuerso y merienda que llebe fresas chocolate pollo",
]

print("\n3. Probando procesamiento...")

for message in test_messages:
    print(f"\n{'='*60}")
    print(f"Mensaje: '{message}'")
    print(f"{'='*60}")
    
    # Simular historial
    historial = [
        {"rol": "user", "contenido": message}
    ]
    
    # Crear messages para LLM (aunque no lo usaremos si detecta menú)
    from langchain_core.messages import HumanMessage
    messages = [HumanMessage(content=message)]
    
    # Llamar a generar_respuesta
    print("\n4. Llamando a generar_respuesta...")
    try:
        respuesta = orchestrator.generar_respuesta(historial, messages)
        print(f"\n   Respuesta ({len(respuesta)} chars):")
        print(f"   {respuesta[:300]}...")
    except Exception as e:
        print(f"\n   [ERROR] {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print(" TEST COMPLETADO")
print("="*60)
