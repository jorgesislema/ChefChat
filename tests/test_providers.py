"""Tests para verificar conexion con proveedores de IA"""

import pytest
from core.config import ConfigManager, AIProvider
from agents.orchestrator import Orchestrator


@pytest.fixture
def configured_provider() -> AIProvider:
    """Obtener el primer proveedor configurado o usar OpenRouter por defecto."""
    provider = ConfigManager.get_configured_provider()
    if provider:
        return provider
    return AIProvider.OPENROUTER


@pytest.mark.parametrize("provider", [p for p in AIProvider])
def test_provider_creation(provider: AIProvider) -> None:
    """Test que el Orchestrator se puede crear con cada proveedor."""
    api_key = ConfigManager.get_api_key(provider)
    if not api_key:
        pytest.skip(f"No hay API Key configurada para {provider.value}")
    
    try:
        orchestrator = Orchestrator(provider=provider)
        assert orchestrator.model_name is not None
        assert orchestrator.base_url is not None
    except Exception as e:
        pytest.fail(f"Error al crear Orchestrator con {provider.value}: {e}")


def test_configured_provider_exists() -> None:
    """Test que hay al menos un proveedor configurado."""
    provider = ConfigManager.get_configured_provider()
    assert provider is not None, "No hay ningun proveedor configurado con API Key"


def test_get_all_providers_returns_list() -> None:
    """Test que get_all_providers devuelve una lista no vacia."""
    providers = ConfigManager.get_all_providers()
    assert len(providers) > 0, "get_all_providers debe devolver al menos un proveedor"
