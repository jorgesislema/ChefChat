"""Simple dependency injection container for ChefChat."""
from typing import Dict, Any, Type, Callable, Optional
import logging


class DIContainer:
    """Simple dependency injection container."""
    
    def __init__(self):
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._instances: Dict[str, Any] = {}
    
    def register_singleton(self, name: str, instance: Any) -> None:
        """Register a singleton instance."""
        self._singletons[name] = instance
    
    def register_factory(self, name: str, factory: Callable) -> None:
        """Register a factory function."""
        self._factories[name] = factory
    
    def resolve(self, name: str) -> Any:
        """Resolve a dependency by name."""
        # Check singletons first
        if name in self._singletons:
            return self._singletons[name]
        
        # Check cached instances
        if name in self._instances:
            return self._instances[name]
        
        # Try factory
        if name in self._factories:
            instance = self._factories[name]()
            self._instances[name] = instance
            return instance
        
        raise ValueError(f"Dependency '{name}' not registered")
    
    def resolve_optional(self, name: str, default: Any = None) -> Any:
        """Resolve a dependency, returning default if not found."""
        try:
            return self.resolve(name)
        except ValueError:
            return default
    
    def clear(self) -> None:
        """Clear all cached instances."""
        self._instances.clear()


# Global container instance
container = DIContainer()


def setup_default_container(db_manager=None, config_manager=None, rag_store=None):
    """Set up the default container with common dependencies."""
    if db_manager:
        container.register_singleton("db_manager", db_manager)
    
    if config_manager:
        container.register_singleton("config_manager", config_manager)
    
    if rag_store:
        container.register_singleton("rag_store", rag_store)
    
    # Register factories for components that should be created per-use
    def create_orchestrator():
        from agents.orchestrator import Orchestrator
        from core.config import ConfigManager
        
        db = container.resolve_optional("db_manager")
        use_dspy = ConfigManager.get_use_dspy()
        rag_only = ConfigManager.get_rag_only()
        
        return Orchestrator(
            db_manager=db,
            use_dspy=use_dspy,
            rag_only=rag_only,
        )
    
    container.register_factory("orchestrator", create_orchestrator)
    
    logging.info("DI container initialized with default dependencies")
