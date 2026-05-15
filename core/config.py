import keyring
import os
from typing import Optional, Dict, List
from enum import Enum


class AIProvider(Enum):
    OPENROUTER = "openrouter"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"
    OPENCODE = "opencode"


class ConfigManager:
    SERVICE_NAME = "ChefChat"

    PROVIDER_KEY_IDS: Dict[AIProvider, str] = {
        AIProvider.OPENROUTER: "openrouter_key",
        AIProvider.DEEPSEEK: "deepseek_key",
        AIProvider.GEMINI: "gemini_key",
        AIProvider.CLAUDE: "claude_key",
        AIProvider.OPENAI: "openai_key",
        AIProvider.OPENCODE: "opencode_key",
    }

    PROVIDER_NAMES: Dict[AIProvider, str] = {
        AIProvider.OPENROUTER: "OpenRouter (MiniMax, GPT, etc)",
        AIProvider.DEEPSEEK: "DeepSeek",
        AIProvider.GEMINI: "Google Gemini",
        AIProvider.CLAUDE: "Claude (Anthropic)",
        AIProvider.OPENAI: "OpenAI (GPT-4, GPT-3.5)",
        AIProvider.OPENCODE: "OpenCode (Big Pickle 🆓)",
    }

    PROVIDER_MODELS: Dict[AIProvider, List[str]] = {
        AIProvider.OPENROUTER: ["minimax-2.7b", "openrouter/auto", "gpt-4o", "claude-3-5-sonnet"],
        AIProvider.DEEPSEEK: ["deepseek-chat", "deepseek-coder"],
        AIProvider.GEMINI: ["gemini-pro", "gemini-1.5-pro", "gemini-2.0-flash"],
        AIProvider.CLAUDE: ["claude-3-5-sonnet-20240620", "claude-3-opus", "claude-3-haiku"],
        AIProvider.OPENAI: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        AIProvider.OPENCODE: ["big-pickle", "open-code-v1", "code-assistant"],
    }

    @staticmethod
    def save_api_key(provider: AIProvider, api_key: str) -> None:
        if not api_key or len(api_key) < 10:
            raise ValueError(f"API Key para {provider.value} inválida")
        key_id = ConfigManager.PROVIDER_KEY_IDS[provider]
        keyring.set_password(ConfigManager.SERVICE_NAME, key_id, api_key)

    @staticmethod
    def get_api_key(provider: AIProvider) -> Optional[str]:
        key_id = ConfigManager.PROVIDER_KEY_IDS[provider]
        return keyring.get_password(ConfigManager.SERVICE_NAME, key_id)

    @staticmethod
    def delete_api_key(provider: AIProvider) -> None:
        try:
            key_id = ConfigManager.PROVIDER_KEY_IDS[provider]
            keyring.delete_password(ConfigManager.SERVICE_NAME, key_id)
        except keyring.errors.PasswordDeleteError:
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
        sandbox_base = r"C:\Temp\ChefChat_Sandbox"
        if not os.path.exists(sandbox_base):
            os.makedirs(sandbox_base, exist_ok=True)
        return sandbox_base

    @staticmethod
    def is_path_in_sandbox(file_path: str) -> bool:
        sandbox = ConfigManager.get_sandbox_path()
        abs_path = os.path.abspath(file_path)
        return abs_path.startswith(sandbox)

    @classmethod
    def get_configured_provider(cls) -> Optional[AIProvider]:
        for provider in cls.get_all_providers():
            if cls.get_api_key(provider):
                return provider
        return None

    @classmethod
    def has_any_api_key(cls) -> bool:
        return cls.get_configured_provider() is not None