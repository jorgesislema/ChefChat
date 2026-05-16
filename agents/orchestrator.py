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
        "default_model": "gemini-1.5-flash",
    },
    AIProvider.CLAUDE: {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20240620",
    },
    AIProvider.OPENAI: {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
    },
    AIProvider.OPENCODE: {
        "base_url": "https://opencode.ai/zen/v1",
        "default_model": "big-pickle",
    },
}


class Orchestrator:
    """
    Orchestrator for ChefChat Pro with Telemetry Support.
    
    Handles LLM communication with automatic usage tracking and cost calculation.
    """
    
    RAG_ONLY_SYSTEM_PROMPT = """
You are ChefChat Pro, a professional restaurant assistant.

CRITICAL RULES:
1. ONLY use local SQLite database for recipes.
2. NEVER invent recipes. If not in DB, say "Not found in system".
3. For recipes, ALWAYS use 'buscar_receta_por_nombre' tool.
4. For inventory, use 'obtener_ingredientes_por_caducar' or 'registrar_uso_inventario'.
5. For scaling recipes, use 'escalar_receta'.
6. For reporting issues, use 'registrar_incidencia'.
7. For business analysis, use 'analizar_rentabilidad_menu'.

If user requests a recipe not found, suggest using [+] button to load new documents.
"""

    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None,
        streaming_callback: Optional[Callable[[str], None]] = None,
        rag_only: bool = True,
        db_manager=None,  # For telemetry logging
    ) -> None:
        self.provider = provider or ConfigManager.get_configured_provider() or AIProvider.OPENAI
        self.api_key = ConfigManager.get_api_key(self.provider)
        if not self.api_key:
            raise ValueError(f"No API Key found for {self.provider.value}")
        api_config = PROVIDER_API_CONFIGS[self.provider]
        self.model_name = model or api_config["default_model"]
        self.base_url = api_config["base_url"]
        self.streaming_callback = streaming_callback
        self.rag_only = rag_only
        self.db_manager = db_manager  # For telemetry
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
        import time
        start_time = time.time()
        
        messages = []
        
        # Add RAG-only system prompt if enabled
        if self.rag_only:
            messages.append(SystemMessage(content=self.RAG_ONLY_SYSTEM_PROMPT))
        
        if contexto_rag:
            messages.append(
                SystemMessage(content=f"Reference context:\n{contexto_rag}")
            )
        for msg in historial:
            if msg["rol"] == "user":
                messages.append(HumanMessage(content=msg["contenido"]))
            elif msg["rol"] == "assistant":
                messages.append(AIMessage(content=msg["contenido"]))
        
        input_tokens = 0
        output_tokens = 0
        success = True
        respuesta = ""
        
        try:
            if self.tools and self.provider not in [AIProvider.GEMINI, AIProvider.OPENCODE]:
                try:
                    from langchain.agents import AgentExecutor, create_openai_functions_agent
                    prompt = create_openai_functions_agent(self.llm, self.tools)
                    agent_executor = AgentExecutor(agent=prompt, tools=self.tools)
                    result = agent_executor.invoke({"input": historial[-1]["contenido"]})
                    respuesta = result.get("output", "")
                    
                    # Try to extract usage from agent result if available
                    if hasattr(result, "intermediate_steps"):
                        for step in result.intermediate_steps:
                            if hasattr(step[1], "response_metadata"):
                                metadata = step[1].response_metadata
                                if "token_usage" in metadata:
                                    usage = metadata["token_usage"]
                                    input_tokens = usage.get("prompt_tokens", 0)
                                    output_tokens = usage.get("completion_tokens", 0)
                except Exception:
                    pass
            
            if not respuesta:
                respuesta = self.llm.invoke(messages)
                
                # Extract usage from response
                if hasattr(respuesta, "response_metadata"):
                    metadata = respuesta.response_metadata
                    if "token_usage" in metadata:
                        usage = metadata["token_usage"]
                        input_tokens = usage.get("prompt_tokens", 0)
                        output_tokens = usage.get("completion_tokens", 0)
                    elif "usage" in metadata:
                        usage = metadata["usage"]
                        input_tokens = usage.get("prompt_tokens", 0)
                        output_tokens = usage.get("completion_tokens", 0)
                
                respuesta = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
            
        except Exception as e:
            success = False
            respuesta = f"Error: {str(e)}"
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Calculate cost
        from agents.tools import calculate_cost
        costo_usd = calculate_cost(self.model_name, input_tokens, output_tokens)
        
        # Log to telemetry (async/silent)
        if self.db_manager and success:
            try:
                self.db_manager.registrar_telemetria(
                    modelo=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    costo_usd=costo_usd,
                    operacion="chat_completion",
                    duracion=duration,
                    exito=success
                )
            except Exception:
                pass  # Silent fail - telemetry is non-critical
        
        return respuesta

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