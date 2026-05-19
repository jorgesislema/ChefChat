"""
Script de Diagnóstico para API Keys

Verifica el estado de las API keys guardadas en keyring
"""

import sys
import os

print("="*60)
print(" DIAGNOSTICO DE API KEYS - ChefChat Pro")
print("="*60)

# 1. Verificar keyring
print("\n1. Verificando keyring...")
try:
    import keyring
    print(f"   [OK] keyring instalado")
    
    # Verificar backend
    backend = keyring.get_keyring()
    print(f"   [OK] Backend: {backend}")
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

# 2. Verificar ConfigManager
print("\n2. Verificando ConfigManager...")
try:
    from core.config import ConfigManager, AIProvider
    print(f"   [OK] ConfigManager importado")
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

# 3. Listar todos los providers
print("\n3. Providers disponibles:")
SERVICE_NAME = "ChefChat"

for provider in AIProvider:
    key_id = ConfigManager.PROVIDER_KEY_IDS[provider]
    display_name = ConfigManager.PROVIDER_NAMES[provider]
    
    # Intentar obtener la key
    try:
        api_key = keyring.get_password(SERVICE_NAME, key_id)
        if api_key:
            key_preview = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
            print(f"   [OK] {provider.value:15} - {display_name:35} - Key: {key_preview}")
        else:
            print(f"   [  ] {provider.value:15} - {display_name:35} - Sin key")
    except Exception as e:
        print(f"   [ERROR] {provider.value:15} - {e}")

# 4. Verificar configured provider
print("\n4. Provider configurado por defecto:")
configured = ConfigManager.get_configured_provider()
if configured:
    print(f"   [OK] {configured.value}")
else:
    print(f"   [  ] Ninguno")

# 5. Verificar has_any_api_key
print("\n5. Verificar si hay alguna API key:")
has_any = ConfigManager.has_any_api_key()
print(f"   [{'OK' if has_any else '  '}] Hay API keys: {has_any}")

# 6. Prueba directa con keyring
print("\n6. Prueba directa de lectura con keyring:")
for provider in [AIProvider.OPENROUTER, AIProvider.DEEPSEEK, AIProvider.GEMINI]:
    key_id = ConfigManager.PROVIDER_KEY_IDS[provider]
    try:
        api_key = keyring.get_password(SERVICE_NAME, key_id)
        if api_key:
            print(f"   [OK] {provider.value}: Key encontrada ({len(api_key)} chars)")
        else:
            print(f"   [  ] {provider.value}: Key NO encontrada")
    except Exception as e:
        print(f"   [ERROR] {provider.value}: {e}")

print("\n" + "="*60)
print(" Diagnostico completado")
print("="*60)
