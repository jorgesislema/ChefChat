"""Script de test para verificar conexión con proveedores de IA"""

from core.config import ConfigManager, AIProvider
from agents.orchestrator import Orchestrator


def test_provider(provider: AIProvider) -> None:
    print(f"\n{'='*50}")
    print(f"Probando {provider.value}...")
    print(f"{'='*50}")
    
    api_key = ConfigManager.get_api_key(provider)
    if not api_key:
        print(f"❌ No hay API Key configurada para {provider.value}")
        return
    
    print(f"✅ API Key encontrada (length: {len(api_key)})")
    
    try:
        orchestrator = Orchestrator(provider=provider)
        print(f"✅ Orchestrator creado con modelo: {orchestrator.model_name}")
        print(f"✅ Base URL: {orchestrator.base_url}")
        
        response = orchestrator.generar_respuesta([
            {"rol": "user", "contenido": "Responde solo 'OK' si puedes leer esto"}
        ])
        print(f"✅ Respuesta recibida: {response[:100] if len(response) > 100 else response}")
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")


def main() -> None:
    print("="*50)
    print("ChefChat Pro - Test de Proveedores IA")
    print("="*50)
    
    configured = ConfigManager.get_configured_provider()
    if configured:
        print(f"\nProveedor configurado: {configured.value}")
    
    for provider in ConfigManager.get_all_providers():
        test_provider(provider)
    
    print(f"\n{'='*50}")
    print("Test completado")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()