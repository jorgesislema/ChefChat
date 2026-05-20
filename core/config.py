import keyring
from keyring import errors as keyring_errors
import os
from typing import Optional, Dict, List
from enum import Enum
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass


class AIProvider(Enum):
    OPENROUTER = "openrouter"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"
    OPENCODE = "opencode"
    OLLAMA = "ollama"


class ConfigManager:
    SERVICE_NAME = "ChefChat"

    PROVIDER_KEY_IDS: Dict[AIProvider, str] = {
        AIProvider.OPENROUTER: "openrouter_key",
        AIProvider.DEEPSEEK: "deepseek_key",
        AIProvider.GEMINI: "gemini_key",
        AIProvider.CLAUDE: "claude_key",
        AIProvider.OPENAI: "openai_key",
        AIProvider.OPENCODE: "opencode_key",
        AIProvider.OLLAMA: "ollama_key",
    }

    PROVIDER_NAMES: Dict[AIProvider, str] = {
        AIProvider.OPENROUTER: "OpenRouter (MiniMax, GPT, etc)",
        AIProvider.DEEPSEEK: "DeepSeek",
        AIProvider.GEMINI: "Google Gemini",
        AIProvider.CLAUDE: "Claude (Anthropic)",
        AIProvider.OPENAI: "OpenAI (GPT-4, GPT-3.5)",
        AIProvider.OPENCODE: "OpenCode (Big Pickle)",
        AIProvider.OLLAMA: "Ollama (Local)",
    }

    PROVIDER_MODELS: Dict[AIProvider, List[str]] = {
        AIProvider.OPENROUTER: ["minimax-2.7b", "openrouter/auto", "gpt-4o", "claude-3-5-sonnet"],
        AIProvider.DEEPSEEK: ["deepseek-chat", "deepseek-coder"],
        AIProvider.GEMINI: ["gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-1.5-pro"],
        AIProvider.CLAUDE: ["claude-3-5-sonnet-20240620", "claude-3-opus", "claude-3-haiku"],
        AIProvider.OPENAI: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        AIProvider.OPENCODE: ["big-pickle", "open-code-v1", "code-assistant"],
        AIProvider.OLLAMA: ["llama3.2", "llama3.1", "mistral", "codellama", "phi3", "gemma2"],
    }

    @staticmethod
    def save_api_key(provider: AIProvider, api_key: str) -> None:
        if not api_key or len(api_key) < 10:
            raise ValueError(f"API Key para {provider.value} invalida")
        key_id = ConfigManager.PROVIDER_KEY_IDS[provider]
        keyring.set_password(ConfigManager.SERVICE_NAME, key_id, api_key)

    @staticmethod
    def get_api_key(provider: AIProvider) -> Optional[str]:
        # First check environment variable
        env_var_map = {
            AIProvider.OPENROUTER: "CHEFCHAT_OPENROUTER_API_KEY",
            AIProvider.DEEPSEEK: "CHEFCHAT_DEEPSEEK_API_KEY",
            AIProvider.GEMINI: "CHEFCHAT_GEMINI_API_KEY",
            AIProvider.CLAUDE: "CHEFCHAT_CLAUDE_API_KEY",
            AIProvider.OPENAI: "CHEFCHAT_OPENAI_API_KEY",
            AIProvider.OPENCODE: "CHEFCHAT_OPENCODE_API_KEY",
            AIProvider.OLLAMA: "CHEFCHAT_OLLAMA_API_KEY",
        }
        env_var = env_var_map.get(provider)
        if env_var:
            env_key = os.environ.get(env_var)
            if env_key:
                return env_key
        
        # Fallback to keyring
        key_id = ConfigManager.PROVIDER_KEY_IDS[provider]
        return keyring.get_password(ConfigManager.SERVICE_NAME, key_id)

    @staticmethod
    def delete_api_key(provider: AIProvider) -> None:
        try:
            key_id = ConfigManager.PROVIDER_KEY_IDS[provider]
            keyring.delete_password(ConfigManager.SERVICE_NAME, key_id)
        except keyring_errors.PasswordDeleteError:
            pass

    @staticmethod
    def get_all_providers() -> List[AIProvider]:
        return list(AIProvider)

    @staticmethod
    def get_provider_display_name(provider: AIProvider) -> str:
        return ConfigManager.PROVIDER_NAMES[provider]

    @staticmethod
    def get_models_for_provider(provider: AIProvider) -> List[str]:
        return ConfigManager.PROVIDER_MODELS.get(provider, [])

    @staticmethod
    def get_sandbox_path() -> str:
        # Check environment variable first
        sandbox_path = os.environ.get("CHEFCHAT_SANDBOX_PATH", r"C:\Temp\ChefChat_Sandbox")
        if not os.path.exists(sandbox_path):
            os.makedirs(sandbox_path, exist_ok=True)
        return sandbox_path

    @staticmethod
    def is_path_in_sandbox(file_path: str) -> bool:
        sandbox = ConfigManager.get_sandbox_path()
        abs_path = os.path.abspath(file_path)
        return abs_path.startswith(sandbox)

    @classmethod
    def get_configured_provider(cls) -> Optional[AIProvider]:
        # Check environment variable first
        env_provider = os.environ.get("CHEFCHAT_AI_PROVIDER")
        if env_provider:
            try:
                return AIProvider(env_provider.lower())
            except ValueError:
                pass
        
        # Fallback to checking API keys
        for provider in cls.get_all_providers():
            if cls.get_api_key(provider):
                return provider
        return None

    @classmethod
    def has_any_api_key(cls) -> bool:
        return cls.get_configured_provider() is not None
    
    @staticmethod
    def get_db_path() -> str:
        """Get database path from environment or default."""
        return os.environ.get("CHEFCHAT_DB_PATH", "chefchat.db")
    
    @staticmethod
    def get_use_dspy() -> bool:
        """Check if DSPy optimization is enabled."""
        return os.environ.get("CHEFCHAT_USE_DSPY", "false").lower() == "true"
    
    @staticmethod
    def get_rag_only() -> bool:
        """Check if RAG-only mode is enabled."""
        return os.environ.get("CHEFCHAT_RAG_ONLY", "true").lower() == "true"
    
    @staticmethod
    def get_log_level() -> str:
        """Get logging level from environment."""
        return os.environ.get("CHEFCHAT_LOG_LEVEL", "INFO")