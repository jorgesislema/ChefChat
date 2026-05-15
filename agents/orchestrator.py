import os
from typing import List, Dict, Any, Optional, Callable
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import Tool
from core.config import AIProvider, ConfigManager
from core.models import AccionOffice


PROVIDER_API_CONFIGS: Dict[AIProvider, Dict[str, str]] = {
    AIProvider.OPENROUTER: {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "minimax-2.7b",
    },
    AIProvider.DEEPSEEK: {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
    AIProvider.GEMINI: {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-pro",
    },
    AIProvider.CLAUDE: {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20240620",
    },
    AIProvider.OPENAI: {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
    },
}


class Orchestrator:
    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.provider = provider or ConfigManager.get_configured_provider() or AIProvider.OPENROUTER
        self.api_key = ConfigManager.get_api_key(self.provider)
        if not self.api_key:
            raise ValueError(f"No se encontró API Key para {self.provider.value}")
        api_config = PROVIDER_API_CONFIGS[self.provider]
        self.model_name = model or api_config["default_model"]
        self.base_url = api_config["base_url"]
        self.streaming_callback = streaming_callback
        self._setup_llm()
        self.tools: List[Tool] = []
        self._setup_tools()

    def _setup_llm(self) -> None:
        if self.provider == AIProvider.GEMINI:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    streaming=self.streaming_callback is not None,
                )
            except ImportError:
                raise ImportError("langchain-google-genai required for Gemini provider. Run: pip install langchain-google-genai")
        elif self.provider == AIProvider.CLAUDE:
            try:
                from langchain_anthropic import ChatAnthropic
                self.llm = ChatAnthropic(
                    model=self.model_name,
                    anthropic_api_key=self.api_key,
                )
            except ImportError:
                raise ImportError("langchain-anthropic required for Claude provider. Run: pip install langchain-anthropic")
        else:
            self.llm = ChatOpenAI(
                model=self.model_name,
                base_url=self.base_url,
                api_key=self.api_key,
                streaming=True if self.streaming_callback else False,
                temperature=0.7,
            )

    def _setup_tools(self) -> None:
        def mcp_tool_wrapper(accion_dict: Dict[str, Any]) -> str:
            from agents.mcp_client import MCPClient
            cliente = MCPClient()
            return cliente.ejecutar_herramienta(AccionOffice(**accion_dict))

        self.tools = [
            Tool(
                name="mcp_office",
                func=mcp_tool_wrapper,
                description="Ejecuta acciones en Microsoft Office (Word/Excel). Entrada: JSON con herramienta, operacion, ruta_archivo, payload",
            )
        ]

    def generar_respuesta(
        self, historial: List[Dict[str, str]], contexto_rag: Optional[str] = None
    ) -> str:
        messages = []
        if contexto_rag:
            messages.append(
                SystemMessage(content=f"Contexto de referencia:\n{contexto_rag}")
            )
        for msg in historial:
            if msg["rol"] == "user":
                messages.append(HumanMessage(content=msg["contenido"]))
            elif msg["rol"] == "assistant":
                messages.append(AIMessage(content=msg["contenido"]))
        if self.tools and self.provider != AIProvider.GEMINI:
            try:
                from langchain.agents import AgentExecutor, create_openai_functions_agent
                prompt = create_openai_functions_agent(self.llm, self.tools)
                agent_executor = AgentExecutor(agent=prompt, tools=self.tools)
                respuesta = agent_executor.invoke({"input": historial[-1]["contenido"]})
                return respuesta["output"]
            except Exception:
                pass
        respuesta = self.llm.invoke(messages)
        return respuesta.content if hasattr(respuesta, "content") else str(respuesta)

    def clasificar_intencion(self, texto_usuario: str) -> str:
        texto_lower = texto_usuario.lower()
        palabras_rag = ["receta", "ingredientes", "alergenos", "bpm", "manual", "procedimiento"]
        palabras_mcp = ["word", "excel", "documento", "menu", "costo", "inventario", "crear", "escribir"]
        score_rag = sum(1 for p in palabras_rag if p in texto_lower)
        score_mcp = sum(1 for p in palabras_mcp if p in texto_lower)
        if score_rag > score_mcp:
            return "rag"
        elif score_mcp > score_rag:
            return "mcp"
        return "general"

    def extraer_json_estructurado(
        self, prompt: str, schema_class: type
    ) -> Dict[str, Any]:
        schema_dict = schema_class.model_json_schema()
        instruction = f"Extrae la siguiente informacion en JSON segun este esquema: {schema_dict}"
        messages = [
            SystemMessage(content=instruction),
            HumanMessage(content=prompt),
        ]
        respuesta = self.llm.invoke(messages)
        import json

        try:
            return json.loads(respuesta.content)
        except json.JSONDecodeError:
            return {"error": "No se pudo parsear la respuesta como JSON"}

    def get_provider_display_name(self) -> str:
        return ConfigManager.get_provider_display_name(self.provider)

    def get_available_models(self) -> List[str]:
        return ConfigManager.get_models_for_provider(self.provider)