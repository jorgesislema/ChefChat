"""
Test para simular el flujo de MainWindow al enviar un mensaje
"""

import logging
logging.basicConfig(level=logging.CRITICAL, format='%(levelname)s:%(message)s')

from core.config import ConfigManager, AIProvider
from data.db_manager import DatabaseManager
import os

print("="*60)
print(" SIMULANDO FLUJO DE MAINWINDOW")
print("="*60)

# 1. Simular _selected_provider
print("\n1. Simulando _selected_provider...")
_selected_provider = None  # Inicialmente es None como en MainWindow
print(f"   _selected_provider inicial: {_selected_provider}")

# 2. Simular línea 837 de main_window.py
print("\n2. Obteniendo provider (línea 837)...")
provider = _selected_provider or ConfigManager.get_configured_provider()
print(f"   provider = _selected_provider or ConfigManager.get_configured_provider()")
print(f"   provider result: {provider}")

# 3. Verificar API key (línea 843)
print("\n3. Verificando API key (línea 843)...")
api_key = ConfigManager.get_api_key(provider)
print(f"   api_key = ConfigManager.get_api_key({provider})")
print(f"   api_key found: {bool(api_key)}")
print(f"   api_key length: {len(api_key) if api_key else 0}")

# 4. Crear Orchestrator (línea 851)
print("\n4. Creando Orchestrator (línea 851)...")
db_path = os.path.join(os.path.dirname(__file__), "chefchat.db")
db = DatabaseManager(db_path=db_path)

try:
    from agents.orchestrator import Orchestrator
    orchestrator = Orchestrator(
        provider=provider,
        model=None,
        db_manager=db
    )
    print(f"   [OK] Orchestrator creado exitosamente!")
    print(f"   orchestrator.provider: {orchestrator.provider}")
    print(f"   orchestrator.api_key length: {len(orchestrator.api_key) if orchestrator.api_key else 0}")
except Exception as e:
    print(f"   [ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print(" TEST COMPLETADO")
print("="*60)
