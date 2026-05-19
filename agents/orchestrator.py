"""Orchestrator module for ChefChat Pro with telemetry support."""

from typing import List, Dict, Any, Optional, Callable
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.tools import Tool
from core.config import AIProvider, ConfigManager
from core.models import AccionOffice
from langchain_anthropic import ChatAnthropic

# Contexto global para exportar datos a Office
_ultimo_contexto_exportacion: Dict[str, Any] = {
    "datos": None,  # Lista de listas con los datos
    "columnas": None,  # Lista con nombres de columnas
    "titulo": "",  # Título del reporte
}

def obtener_contexto_exportacion() -> Dict[str, Any]:
    """Obtiene el contexto actual de exportación."""
    return _ultimo_contexto_exportacion

def guardar_contexto_exportacion(datos: List[List], columnas: Optional[List[str]] = None, titulo: str = "") -> None:
    """Guarda datos en el contexto para posterior exportación."""
    global _ultimo_contexto_exportacion
    _ultimo_contexto_exportacion = {
        "datos": datos,
        "columnas": columnas,
        "titulo": titulo,
    }


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
    AIProvider.OLLAMA: {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
    },
}

HERRAMIENTAS_DETECTABLES = {
    "registrar_merma": {
        "patrones": ["registrar_merma", "registra merma", "registre merma"],
        "descripcion": "Input: 'producto, cantidad, unidad, motivo, costo(opcional)'"
    },
    "reporte_mermas": {
        "patrones": ["reporte_mermas", "reporte de mermas", "reporte mermas", "mermas"],
        "descripcion": "Input: dias (int, opcional)"
    },
    "registrar_incidencia": {
        "patrones": ["registrar_incidencia", "registra incidencia", "reportar problema", "reporta problema"],
        "descripcion": "Input: 'categoria, descripcion'"
    },
    "analizar_rentabilidad": {
        "patrones": ["analizar_rentabilidad", "analiza rentabilidad", "rentabilidad del menú", "rentabilidad del menu"],
        "descripcion": "Sin input"
    },
    "productos_por_caducar": {
        "patrones": ["productos_por_caducar", "productos por caducar", "por caducar", "próximos a caducar", "proximos a caducar"],
        "descripcion": "Input: dias (int, opcional)"
    },
    "verificar_stock_bajo": {
        "patrones": ["verificar_stock_bajo", "stock bajo", "verifica stock", "verificar stock"],
        "descripcion": "Input: umbral (float, opcional)"
    },
    "menu_diario": {
        "patrones": ["menu_diario", "menú del día", "menu del dia", "menú diario", "menu diario"],
        "descripcion": "Sin input"
    },
    "configurar_menu_semanal": {
        "patrones": ["configurar_menu_semanal", "configura menú semanal", "configura menu semanal", "menú semanal", "menu semanal"],
        "descripcion": "Input: 'Lunes | entrante=SOP-021, plato_fuerte=PLF-018'"
    },
    "generar_orden_compra": {
        "patrones": ["generar_orden_compra", "genera orden compra", "orden de compra", "crear orden compra", "crea orden de compra"],
        "descripcion": "Input: 'proveedor, producto, cantidad, unidad, costo_unitario(opcional), fecha_req(opcional)'"
    },
    "ordenes_compra": {
        "patrones": ["ordenes_compra", "órdenes de compra", "ordenes de compra", "ver ordenes", "listar ordenes"],
        "descripcion": "Input: estado (str, opcional)"
    },
    "costo_real_vs_teorico": {
        "patrones": ["costo_real_vs_teorico", "costo real vs teórico", "costo real teorico", "comparar costo"],
        "descripcion": "Input: dias (int, opcional)"
    },
    "dashboard_ventas": {
        "patrones": ["dashboard_ventas", "dashboard de ventas", "tablero ventas", "ventas"],
        "descripcion": "Input: dias (int, opcional)"
    },
    "alertas_stock_bajo": {
        "patrones": ["alertas_stock_bajo", "alerta stock", "alertas inventario"],
        "descripcion": "Input: umbral (int, opcional)"
    },
    "asignar_turnos": {
        "patrones": ["asignar_turnos", "asigna turno", "asignar turno", "crear turno"],
        "descripcion": "Input: 'fecha, cocinero, estacion, hora_inicio, hora_fin, receta'"
    },
    "ver_turnos": {
        "patrones": ["ver_turnos", "consulta turnos", "turnos cocina", "turno"],
        "descripcion": "Input: fecha (str, opcional)"
    },
    "registrar_produccion": {
        "patrones": ["registrar_produccion", "registra producción", "registra produccion", "registrar producción", "produccion diaria", "producción diaria", "reportar producción", "reportar produccion"],
        "descripcion": "Input: 'fecha=..., cocido: SOP-021=30, sobrante: arroz=4.5|kg|no'"
    },
    "generar_reporte_diario": {
        "patrones": ["generar_reporte_diario", "reporte diario", "reporte oficial", "genera reporte diario"],
        "descripcion": "Input: fecha (str, opcional)"
    },
    "listar_plantillas": {
        "patrones": ["listar_plantillas", "lista plantillas", "plantillas disponibles", "que plantillas"],
        "descripcion": "Sin input"
    },
    "usar_plantilla": {
        "patrones": ["usar_plantilla", "aplica plantilla", "usa plantilla", "aplicar plantilla"],
        "descripcion": "Input: 'plantilla.docx | nombre=Juan, fecha=15 Junio'"
    },
    "registrar_trabajador": {
        "patrones": ["registrar_trabajador", "registra trabajador", "registrar empleado", "registra empleado", "nuevo trabajador", "nuevo empleado"],
        "descripcion": "Input: 'ID, nombre, cargo, turno, hora_entrada, hora_salida, dias_descanso(opcional)'"
    },
    "listar_trabajadores": {
        "patrones": ["listar_trabajadores", "lista trabajadores", "lista empleados", "listar empleados", "ver trabajadores", "ver empleados"],
        "descripcion": "Input: turno (str, opcional)"
    },
    "registrar_sobrante": {
        "patrones": ["registrar_sobrante", "registra sobrante", "registrar sobrante reutilizable"],
        "descripcion": "Input: 'producto, cantidad, unidad, id_empleado(opcional), turno(opcional), dias_reutilizacion(opcional)'"
    },
    "dashboard_sobrantes": {
        "patrones": ["dashboard_sobrantes", "dashboard sobrantes", "tablero sobrantes", "sobrantes"],
        "descripcion": "Input: dias (int, opcional, default 7)"
    },
    "exportar_dashboard_sobrantes": {
        "patrones": ["exportar_dashboard_sobrantes", "exporta dashboard sobrantes", "exportar sobrantes a csv", "exportar sobrantes a excel"],
        "descripcion": "Input: dias (int, opcional, default 7)"
    },
    "buscar_recetas_con_ingrediente": {
        "patrones": ["buscar_recetas_con_ingrediente", "recetas con", "receta con", "buscar recetas con ingrediente", "busca recetas con"],
        "descripcion": "Input: ingrediente (str)"
    },
}


class Orchestrator:
    """
    Orquestador para ChefChat Pro con Soporte de Telemetría.

    Maneja la comunicación con LLM con seguimiento automático de uso y cálculo de costos.
    """

    RAG_ONLY_SYSTEM_PROMPT = """
Eres ChefChat Pro, un asistente profesional de restaurantes.

REGLAS CRÍTICAS:
1. SOLO utiliza la base de datos SQLite local para recetas.
2. NUNCA inventes recetas. Si no está en la BD, di "No encontrado en el sistema".
3. Para buscar recetas, usa buscar_receta(nombre_o_id).
4. Para buscar recetas por ingrediente, usa buscar_recetas_con_ingrediente(ingrediente).
5. Para inventario, usa productos_por_caducar(dias) o verificar_stock_bajo().
6. Para escalar recetas, usa escalar_receta(receta_id, comensales).
7. Para reportar problemas, usa registrar_incidencia(categoria, descripcion).
8. Para menu semanal, usa consultar_menu_semanal(pregunta).
9. Para agregar plato al menu, usa agregar_plato_menu(dia, servicio, nombre, precio, prep).
10. Para agregar receta de RAG al menu, usa agregar_receta_al_menu(dia, servicio, receta_id, precio).
11. Para buscar documentos, usa buscar_documento(termino).
12. Para mermas, usa reporte_mermas(dias).
13. Para exportar a Word/Excel/PowerPoint, di "a excel", "a word", "a powerpoint".
14. Para menu anti-desperdicio, usa menu_anti_desperdicio().
15. Para lista de compras, usa generar_lista_compras(recetas_csv, comensales).

FLUJO DE DETECCIÓN:
- "menu semanal", "menu del dia" → consultar_menu_semanal()
- "busca documento", "capacitacion", "protocolo" → buscar_documento()
- "receta PLF-018" → buscar_receta("PLF-018")
- "receta con pollo" → buscar_recetas_con_ingrediente("pollo")
- "merma" → reporte_mermas(dias)
- "sugiere menu con pollo, arroz" → sugerir_menu_por_ingredientes("pollo, arroz")
- "a excel" / "a word" / "a powerpoint" → exportar ultimo contexto

Si el usuario solicita una receta no encontrada, sugiere usar el botón [+] para cargar nuevos documentos.
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
        
        # CRITICAL DEBUG LOG
        import logging
        logging.critical(f"ORCHESTRATOR INIT - provider param: {provider}, ConfigManager.get_configured_provider: {ConfigManager.get_configured_provider()}, final self.provider: {self.provider}")
        
        self.api_key = ConfigManager.get_api_key(self.provider)
        
        # Ollama no necesita API key
        if self.provider == AIProvider.OLLAMA:
            self.api_key = self.api_key or "ollama"
        
        # Debug logging
        logging.info(f"Orchestrator init - Provider: {self.provider}, API Key found: {bool(self.api_key)}")
        
        if not self.api_key:
            # Try to get all providers to see what's available
            all_providers = ConfigManager.get_all_providers()
            logging.critical(f"NO API KEY FOR {self.provider}! Available providers:")
            for p in all_providers:
                key = ConfigManager.get_api_key(p)
                logging.critical(f"  - {p.value}: {'[SET]' if key else '[NOT SET]'} - Key length: {len(key) if key else 0}")
            
            raise ValueError(f"No API Key found for {self.provider.value}. Please configure it in Settings.")
        
        api_config = PROVIDER_API_CONFIGS[self.provider]
        self.model_name = model or api_config["default_model"]
        self.base_url = api_config["base_url"]
        self.streaming_callback = streaming_callback
        self.rag_only = rag_only
        self.db_manager = db_manager  # For telemetry
        self.multiagent = None  # Se inicializa después con las herramientas
        logging.info(f"Initializing LLM with provider={self.provider.value}, model={self.model_name}")
        self._setup_llm()
        self.tools: List[Tool] = []
        self._setup_tools()
        self._setup_multiagent()

    def _setup_llm(self) -> None:
        from pydantic import SecretStr
        import logging

        if self.provider == AIProvider.GEMINI:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.llm: Any = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    streaming=bool(self.streaming_callback),
                )
            except ImportError as exc:
                raise ImportError(
                    "langchain-google-genai required for Gemini provider. "
                    "Run: pip install langchain-google-genai"
                ) from exc
        elif self.provider == AIProvider.CLAUDE:
            self.llm = ChatAnthropic(
                model_name=self.model_name,
                api_key=SecretStr(
                    self.api_key
                ) if self.api_key else SecretStr(""),
                timeout=60.0,
                stop=None,
            )
        else:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ImportError(
                    "openai package required for OpenAI-compatible providers. "
                    "Run: pip install openai"
                ) from exc
            
            # CRITICAL DEBUG: Log api_key and base_url before creating client
            logging.critical(f"Creating OpenAI client - api_key length: {len(self.api_key) if self.api_key else 0}, base_url: {self.base_url}")
            
            client_kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                # Cast to AnyUrl for type-checkers while keeping a str at runtime
                from typing import cast
                try:
                    from pydantic import AnyUrl
                    client_kwargs["base_url"] = cast(AnyUrl, self.base_url)
                except ImportError:
                    client_kwargs["base_url"] = self.base_url
            
            logging.critical(f"client_kwargs: api_key={len(self.api_key) if self.api_key else 0} chars, base_url={client_kwargs.get('base_url')}")
            
            client = OpenAI(**client_kwargs)
            
            logging.critical(f"Client created: {client}")
            logging.critical(f"Client base_url: {client.base_url}")

            self.llm = ChatOpenAI(
                model_name=self.model_name,
                api_key=self.api_key,  # Pass api_key directly to ChatOpenAI
                base_url=self.base_url if self.base_url else None,  # Pass base_url directly
                temperature=0.7,
            )
            
            logging.critical(f"ChatOpenAI created successfully: {self.llm}")

    def _setup_tools(self) -> None:
        from agents.tools import crear_herramientas_operativas
        
        def mcp_tool_wrapper(accion_dict: Dict[str, Any]) -> Dict[str, Any]:
            from agents.mcp_client import MCPClient
            cliente = MCPClient()
            return cliente.ejecutar_herramienta(AccionOffice(**accion_dict))

        self.tools = crear_herramientas_operativas(self.db_manager) if self.db_manager else []
        self.tools.append(
            Tool(
                name="mcp_office",
                func=mcp_tool_wrapper,
                description="Ejecuta acciones en Microsoft Office (Word/Excel). Entrada: JSON con herramienta, operacion, ruta_archivo, payload",
            )
        )

    def _setup_multiagent(self) -> None:
        """Inicializa el sistema multiagente."""
        import logging
        try:
            from agents.multiagent import MultiAgentSystem
            self.multiagent = MultiAgentSystem(self.tools)
            logging.info("MultiAgent system initialized successfully")
        except Exception as e:
            logging.warning(f"Could not initialize MultiAgent system: {e}")
            self.multiagent = None

    def generar_respuesta(
        self, historial: List[Dict[str, str]], contexto_rag: Optional[str] = None
    ) -> str:
        import time
        import re
        start_time = time.time()
        
        messages: List[BaseMessage] = []
        
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
            # Intentar usar herramientas manualmente para búsquedas de recetas
            ultimo_mensaje = historial[-1]["contenido"].lower() if historial else ""
            
            # Detectar si es búsqueda de receta por ID (ej: SOP-021, PLF-003, BEB-010, SPO-036)
            match_id = re.search(r'\b((?:SPO|SOP|BEB|ENS|POS|ENT|PLF|EVT)[-_]\d{2,4})\b', ultimo_mensaje.upper())
            ids_encontrados = re.findall(r'\b((?:SPO|SOP|BEB|ENS|POS|ENT|PLF|EVT)[-_]\d{2,4})\b', ultimo_mensaje.upper())
            
            import logging
            logging.critical(f"ULTIMO_MENSAJE: {ultimo_mensaje[:100]}")
            logging.critical(f"MATCH_ID: {match_id}")
            
            # ============================================================
            # PRIORIDAD 1: EXPORTACIÓN GENÉRICA (a excel/word/powerpoint)
            # ============================================================
            if any(p in ultimo_mensaje for p in ["a excel", "a word", "a powerpoint", "al excel", "al word", "a la hoja", "al documento"]):
                from agents.orchestrator import obtener_contexto_exportacion
                from agents.mcp_client import MCPClient
                from core.models import AccionOffice
                
                contexto = obtener_contexto_exportacion()
                if contexto.get("datos"):
                    titulo = contexto.get("titulo", "Datos")
                    columnas = contexto.get("columnas", [])
                    datos = contexto.get("datos", [])
                    
                    if "excel" in ultimo_mensaje:
                        datos_completos = [columnas] + datos if columnas else datos
                        cliente = MCPClient()
                        resultado = cliente.ejecutar_herramienta(AccionOffice(
                            herramienta="excel",
                            operacion="enviar",
                            ruta_archivo="",
                            payload={"datos": datos_completos, "insertar_en": "A1"},
                            requiere_hitl=False
                        ))
                        return f"✅ Datos enviados a Excel: {resultado.get('mensaje', 'OK')}"
                    elif "word" in ultimo_mensaje:
                        contenido = f"# {titulo}\n\n"
                        if columnas:
                            contenido += "| " + " | ".join(columnas) + " |\n"
                            contenido += "| " + " | ".join(["---"] * len(columnas)) + " |\n"
                            for fila in datos:
                                contenido += "| " + " | ".join(str(c) for c in fila) + " |\n"
                        cliente = MCPClient()
                        resultado = cliente.ejecutar_herramienta(AccionOffice(
                            herramienta="word",
                            operacion="enviar",
                            ruta_archivo="",
                            payload={"contenido": contenido, "formato": {"titulo": titulo, "font_size": 12}},
                            requiere_hitl=False
                        ))
                        return f"✅ Datos enviados a Word: {resultado.get('mensaje', 'OK')}"
                    elif "powerpoint" in ultimo_mensaje:
                        contenido = f"{titulo}\n\n"
                        if columnas and datos:
                            contenido += " | ".join(columnas) + "\n"
                            for fila in datos[:10]:
                                contenido += " | ".join(str(c) for c in fila) + "\n"
                        cliente = MCPClient()
                        resultado = cliente.ejecutar_herramienta(AccionOffice(
                            herramienta="powerpoint",
                            operacion="enviar",
                            ruta_archivo="",
                            payload={"contenido": contenido, "titulo": titulo},
                            requiere_hitl=False
                        ))
                        return f"✅ Datos enviados a PowerPoint: {resultado.get('mensaje', 'OK')}"

            # ============================================================
            # PRIORIDAD 2: MENU SEMANAL (ANTES de menu por ingredientes)
            # ============================================================
            if not respuesta and self.db_manager and any(p in ultimo_mensaje for p in ["menu semanal", "menu de la semana", "menu del dia", "menu de hoy", "agregar plato", "agregar receta al menu", "modificar plato", "eliminar plato", "reset menu", "resetear menu", "consultar menu", "ver menu"]):
                from agents.tools import crear_herramientas_operativas
                tools = crear_herramientas_operativas(self.db_manager)
                
                tool = next((t for t in tools if t.name == "consultar_menu_semanal"), None)
                func = getattr(tool, "func", None) if tool else None
                if callable(func):
                    respuesta = func(ultimo_mensaje)
                    logging.critical(f"MENU_SEMANAL: {respuesta[:100]}")

            # ============================================================
            # PRIORIDAD 3: BUSCAR DOCUMENTOS (ANTES de buscar recetas)
            # ============================================================
            if not respuesta and self.db_manager and any(p in ultimo_mensaje for p in ["busca documento", "buscar documento", "documento", "capacitacion", "capacitación", "buenas practicas", "buenas prácticas", "protocolo", "protocolos", "manual"]):
                from data.rag_store import RAGStore
                rag = RAGStore()
                
                # Extraer termino de busqueda
                termino = ultimo_mensaje
                for prefix in ["busca documento", "buscar documento", "busca", "buscar", "documento", "capacitacion", "capacitación"]:
                    idx = ultimo_mensaje.find(prefix)
                    if idx >= 0:
                        termino = ultimo_mensaje[idx + len(prefix):].strip()
                        break
                
                # Limpiar articulos y preposiciones
                for word in ["el", "la", "los", "las", "un", "una", "de", "del", "con", "que", "sea"]:
                    if termino.lower().startswith(word + " "):
                        termino = termino[len(word):].strip()
                
                # Buscar por multiple terminos
                docs = rag.buscar_documento(termino)
                
                # Si no encontro, intentar con palabras clave mas cortas
                if not docs and len(termino.split()) > 2:
                    palabras = termino.split()
                    for palabra in palabras:
                        if len(palabra) > 3:
                            docs = rag.buscar_documento(palabra)
                            if docs:
                                break
                
                # Si no encontro, buscar por tipo de documento
                if not docs:
                    if any(p in ultimo_mensaje for p in ["protocolo", "protocolos", "manual", "bpm", "buenas practicas"]):
                        docs = rag.buscar_documento("manual_bpm")
                    elif any(p in ultimo_mensaje for p in ["capacitacion", "capacitación"]):
                        docs = rag.buscar_documento("generico")
                
                if docs:
                    lineas = [f"DOCUMENTOS ENCONTRADOS ({len(docs)}):"]
                    for d in docs[:10]:
                        lineas.append(f"  - {d.get('nombre')} (tipo: {d.get('tipo')})")
                    respuesta = "\n".join(lineas)
                    logging.critical(f"DOCUMENTOS: {respuesta[:100]}")
                else:
                    respuesta = f"No se encontraron documentos con: {termino}. Usa el boton [+] para cargar documentos."

            # ============================================================
            # PRIORIDAD 4: RECETA POR ID (PLF-018, SOP-021, etc.)
            # ============================================================
            if not respuesta and match_id and self.db_manager:
                from agents.tools import crear_herramientas_operativas
                tools = crear_herramientas_operativas(self.db_manager)
                receta_id = match_id.group(1)
                respuesta = self._procesar_mensaje_con_id(ultimo_mensaje, ids_encontrados, receta_id, tools)

            # ============================================================
            # PRIORIDAD 5: MENU POR INGREDIENTES (solo si NO es menu semanal)
            # ============================================================
            es_menu = any(p in ultimo_mensaje for p in ["menú", "menu", "sugiere", "sugerir", "elabora", "elaborar", "crea", "crear", "haz", "hacer", "arma", "armar", "planifica", "planificar"])
            es_reporte = any(p in ultimo_mensaje for p in ["merma", "mermas", "informe", "reporte", "dashboard", "inventario", "caducar", "caducidad", "stock", "semanal", "semana", "documento", "capacitacion"])
            es_menu = es_menu and not es_reporte and not any(p in ultimo_mensaje for p in ["menu semanal", "menu de la semana", "menu del dia"])
            
            logging.critical(f"ES_MENU: {es_menu}")
            
            if not respuesta and es_menu and self.db_manager:
                from agents.tools import crear_herramientas_operativas
                tools = crear_herramientas_operativas(self.db_manager)
                respuesta = self._procesar_menu_por_ingredientes(ultimo_mensaje, tools)

            # ============================================================
            # PRIORIDAD 6: MERMAS (con extraccion de fecha especifica)
            # ============================================================
            if not respuesta and self.db_manager and any(p in ultimo_mensaje for p in ["merma", "mermas", "desperdicio", "desperdicios"]):
                from agents.tools import crear_herramientas_operativas
                tools = crear_herramientas_operativas(self.db_manager)
                
                # Extraer dias (default 30 para consultas amplias)
                dias = 30
                match_dias = re.search(r"(\d+)\s*(?:dias?|días?|days?|semana)", ultimo_mensaje)
                if match_dias:
                    dias = int(match_dias.group(1))
                elif "semana" in ultimo_mensaje:
                    dias = 7
                elif "hoy" in ultimo_mensaje:
                    dias = 1
                else:
                    # Intentar extraer fecha especifica (ej: "sabado 16 de mayo", "16 mayo", "16/05")
                    from datetime import datetime, timedelta
                    meses = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
                             "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
                    
                    # Buscar patron "dia de mes" o "dia mes"
                    match_fecha = re.search(r'(\d{1,2})\s*(?:de\s+)?(' + '|'.join(meses.keys()) + ')', ultimo_mensaje)
                    if match_fecha:
                        dia = int(match_fecha.group(1))
                        mes = meses[match_fecha.group(2)]
                        hoy = datetime.now()
                        fecha_objetivo = datetime(hoy.year, mes, dia)
                        if fecha_objetivo > hoy:
                            fecha_objetivo = fecha_objetivo.replace(year=hoy.year - 1)
                        dias = (hoy - fecha_objetivo).days + 1
                    else:
                        # Buscar patron dd/mm o dd-mm
                        match_fecha2 = re.search(r'(\d{1,2})[/\-](\d{1,2})', ultimo_mensaje)
                        if match_fecha2:
                            dia = int(match_fecha2.group(1))
                            mes = int(match_fecha2.group(2))
                            hoy = datetime.now()
                            fecha_objetivo = datetime(hoy.year, mes, dia)
                            if fecha_objetivo > hoy:
                                fecha_objetivo = fecha_objetivo.replace(year=hoy.year - 1)
                            dias = (hoy - fecha_objetivo).days + 1
                
                logging.critical(f"MERMAS_DETECT: dias={dias}")
                
                if "excel" in ultimo_mensaje:
                    tool = next((t for t in tools if t.name == "enviar_reporte_mermas_a_excel"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        respuesta = func(dias)
                elif "word" in ultimo_mensaje:
                    tool = next((t for t in tools if t.name == "enviar_reporte_mermas_a_word"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        respuesta = func(dias)
                else:
                    tool = next((t for t in tools if t.name == "reporte_mermas"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        respuesta = func(dias)

            # ============================================================
            # PRIORIDAD 7: BUSCAR RECETA POR NOMBRE/INGREDIENTES
            # ============================================================
            busca_keywords = ["receta", "busca", "buscar", "encuentra", "dame", "encuentra", "reseta"]
            if not respuesta and self.db_manager and any(k in ultimo_mensaje for k in busca_keywords):
                from agents.tools import crear_herramientas_operativas
                tools = crear_herramientas_operativas(self.db_manager)
                
                # Detectar si es busqueda por ingredientes (contiene "con")
                if any(p in ultimo_mensaje for p in ["con ", "que tenga ", "que lleve "]):
                    # Extraer ingredientes
                    ingredientes = []
                    for prefix in ["con", "que tenga", "que lleve", "que incluya"]:
                        idx = ultimo_mensaje.find(prefix)
                        if idx >= 0:
                            texto = ultimo_mensaje[idx + len(prefix):].strip()
                            # Limpiar palabras de comando
                            for stop in ["para", "menu", "sugerir", "sugiere", "elabora", "crea", "haz"]:
                                sidx = texto.find(stop)
                                if sidx >= 0:
                                    texto = texto[:sidx]
                            # Limpiar articulos
                            palabras = texto.replace(",", " ").replace(" y ", " ").split()
                            ingredientes = [p.strip() for p in palabras if len(p.strip()) > 2 and p.lower() not in ["el", "la", "los", "las", "un", "una", "de", "del", "con", "que", "para", "menu"]]
                            break
                    
                    if ingredientes:
                        tool = next((t for t in tools if t.name == "buscar_recetas_con_ingrediente"), None)
                        func = getattr(tool, "func", None) if tool else None
                        if callable(func):
                            resultados = []
                            for ing in ingredientes[:3]:
                                res = func(ing)
                                if res and "no encontraron" not in res.lower():
                                    resultados.append(res)
                            if resultados:
                                respuesta = "\n\n".join(resultados)
                            else:
                                # Intentar buscar por nombre directo
                                resultado_busqueda = self._buscar_receta_por_nombre(ultimo_mensaje, tools, messages)
                                respuesta = resultado_busqueda if resultado_busqueda else f"No se encontraron recetas con: {', '.join(ingredientes)}"
                        else:
                            respuesta = self._buscar_receta_por_nombre(ultimo_mensaje, tools, messages)
                    else:
                        respuesta = self._buscar_receta_por_nombre(ultimo_mensaje, tools, messages)
                else:
                    # Buscar por nombre directo
                    respuesta = self._buscar_receta_por_nombre(ultimo_mensaje, tools, messages)

            # ============================================================
            # PRIORIDAD 8: EJECUTAR HERRAMIENTA DETECTADA
            # ============================================================
            if not respuesta and self.db_manager:
                respuesta = self._ejecutar_herramienta_detectada(historial)
            
            # ============================================================
            # PRIORIDAD 9: LLM DIRECTO
            # ============================================================
            if not respuesta:
                respuesta = self.llm.invoke(messages)
                
                logging.critical(f"LLM RESPONSE TYPE: {type(respuesta)}")
                
                if hasattr(respuesta, "response_metadata"):
                    metadata = respuesta.response_metadata
                    logging.critical(f"META KEYS: {metadata.keys() if hasattr(metadata, 'keys') else 'N/A'}")
                    logging.critical(f"META: {str(metadata)[:500]}")
                    
                    if "token_usage" in metadata:
                        usage = metadata["token_usage"]
                        input_tokens = usage.get("prompt_tokens", 0)
                        output_tokens = usage.get("completion_tokens", 0)
                        logging.critical(f"TOKENS (token_usage): input={input_tokens}, output={output_tokens}")
                    elif "usage" in metadata:
                        usage = metadata["usage"]
                        input_tokens = usage.get("prompt_tokens", 0)
                        output_tokens = usage.get("completion_tokens", 0)
                        logging.critical(f"TOKENS (usage): input={input_tokens}, output={output_tokens}")
                    elif "usage_metadata" in metadata:
                        usage = metadata["usage_metadata"]
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        logging.critical(f"TOKENS (usage_metadata): input={input_tokens}, output={output_tokens}")
                    else:
                        logging.critical(f"NO TOKEN USAGE FOUND IN METADATA")
                elif hasattr(respuesta, "usage_metadata"):
                    usage = respuesta.usage_metadata
                    if usage:
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        logging.critical(f"TOKENS (usage_metadata attr): input={input_tokens}, output={output_tokens}")
                else:
                    logging.critical(f"NO response_metadata ATTRIBUTE")
                
                respuesta = str(respuesta.content) if hasattr(respuesta, "content") else str(respuesta)
            
            # ============================================================
            # GUARDAR CONTEXTO PARA EXPORTACIÓN
            # ============================================================
            if respuesta:
                from agents.orchestrator import guardar_contexto_exportacion
                guardar_contexto_exportacion(
                    datos=[[respuesta]],
                    columnas=["Respuesta"],
                    titulo="Respuesta ChefChat"
                )
            
            # DETECCIÓN DE MENU SEMANAL
            if not respuesta and self.db_manager and any(p in ultimo_mensaje for p in ["menu semanal", "menu de la semana", "menu del", "agregar plato", "agregar receta al menu", "buscar receta para menu", "modificar plato", "eliminar plato", "reset menu", "resetear menu"]):
                from agents.tools import crear_herramientas_operativas
                tools = crear_herramientas_operativas(self.db_manager)
                
                # Consultar menu
                if any(p in ultimo_mensaje for p in ["menu semanal", "menu de la semana", "menu del", "que hay", "precios", "preparacion"]):
                    tool = next((t for t in tools if t.name == "consultar_menu_semanal"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        respuesta = func(ultimo_mensaje)
                # Agregar plato
                elif "agregar plato" in ultimo_mensaje:
                    tool = next((t for t in tools if t.name == "agregar_plato_menu"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        for prefix in ["agregar plato", "agrega plato"]:
                            idx = ultimo_mensaje.find(prefix)
                            if idx >= 0:
                                params = ultimo_mensaje[idx + len(prefix):].strip()
                                respuesta = func(params)
                                break
                # Agregar receta
                elif "agregar receta" in ultimo_mensaje:
                    tool = next((t for t in tools if t.name == "agregar_receta_al_menu"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        for prefix in ["agregar receta al menu", "agrega receta"]:
                            idx = ultimo_mensaje.find(prefix)
                            if idx >= 0:
                                params = ultimo_mensaje[idx + len(prefix):].strip()
                                respuesta = func(params)
                                break
                # Buscar recetas
                elif "buscar receta" in ultimo_mensaje and "menu" in ultimo_mensaje:
                    tool = next((t for t in tools if t.name == "buscar_recetas_para_menu"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        for prefix in ["buscar receta para menu", "busca receta"]:
                            idx = ultimo_mensaje.find(prefix)
                            if idx >= 0:
                                params = ultimo_mensaje[idx + len(prefix):].strip()
                                respuesta = func(params)
                                break
                # Modificar
                elif "modificar" in ultimo_mensaje:
                    tool = next((t for t in tools if t.name == "modificar_plato_menu"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        for prefix in ["modificar plato", "modifica"]:
                            idx = ultimo_mensaje.find(prefix)
                            if idx >= 0:
                                params = ultimo_mensaje[idx + len(prefix):].strip()
                                respuesta = func(params)
                                break
                # Eliminar
                elif "eliminar" in ultimo_mensaje or "quitar" in ultimo_mensaje:
                    tool = next((t for t in tools if t.name == "eliminar_plato_menu"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        import re
                        match = re.search(r'(\d+)', ultimo_mensaje)
                        if match:
                            respuesta = func(match.group(1))
                # Reset
                elif "reset" in ultimo_mensaje or "resetear" in ultimo_mensaje:
                    tool = next((t for t in tools if t.name == "reset_menu_semanal"), None)
                    func = getattr(tool, "func", None) if tool else None
                    if callable(func):
                        respuesta = func()
            
            if not respuesta and self.db_manager:
                respuesta = self._ejecutar_herramienta_detectada(historial)
            
            # Si no hay respuesta de herramienta, usar LLM directo
            if not respuesta:
                respuesta = self.llm.invoke(messages)
                
                # Extract usage from response - CRITICAL DEBUG
                logging.critical(f"LLM RESPONSE TYPE: {type(respuesta)}")
                
                if hasattr(respuesta, "response_metadata"):
                    metadata = respuesta.response_metadata
                    logging.critical(f"META KEYS: {metadata.keys() if hasattr(metadata, 'keys') else 'N/A'}")
                    logging.critical(f"META: {str(metadata)[:500]}")
                    
                    if "token_usage" in metadata:
                        usage = metadata["token_usage"]
                        input_tokens = usage.get("prompt_tokens", 0)
                        output_tokens = usage.get("completion_tokens", 0)
                        logging.critical(f"TOKENS (token_usage): input={input_tokens}, output={output_tokens}")
                    elif "usage" in metadata:
                        usage = metadata["usage"]
                        input_tokens = usage.get("prompt_tokens", 0)
                        output_tokens = usage.get("completion_tokens", 0)
                        logging.critical(f"TOKENS (usage): input={input_tokens}, output={output_tokens}")
                    elif "usage_metadata" in metadata:
                        usage = metadata["usage_metadata"]
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        logging.critical(f"TOKENS (usage_metadata): input={input_tokens}, output={output_tokens}")
                    else:
                        logging.critical(f"NO TOKEN USAGE FOUND IN METADATA")
                elif hasattr(respuesta, "usage_metadata"):
                    usage = respuesta.usage_metadata
                    if usage:
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        logging.critical(f"TOKENS (usage_metadata attr): input={input_tokens}, output={output_tokens}")
                else:
                    logging.critical(f"NO response_metadata ATTRIBUTE")
                
                respuesta = str(respuesta.content) if hasattr(respuesta, "content") else str(respuesta)
            
        except (AttributeError, ImportError, ValueError, RuntimeError, TypeError, OSError, KeyError) as e:
            # Capture common, expected exception types while avoiding a broad
            # catch-all. Telemetry will record the failure below.
            success = False
            respuesta = f"Error: {str(e)}"
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Calculate cost
        from agents.tools import calculate_cost
        costo_usd = calculate_cost(self.model_name, input_tokens, output_tokens)
        
        # Log to telemetry (async/silent)
        logging.critical(f"TELEMETRY: model={self.model_name}, input_tokens={input_tokens}, output_tokens={output_tokens}, cost={costo_usd}")
        
        if self.db_manager:
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
                logging.critical(f"TELEMETRY REGISTERED SUCCESSFULLY")
            except Exception as e:
                # Silent fail - telemetry is non-critical. Catching specific
                # exceptions likely to be raised by telemetry/database ops.
                logging.critical(f"TELEMETRY ERROR: {e}")
                pass
        
        return respuesta

    def _procesar_mensaje_con_id(
        self,
        ultimo_mensaje: str,
        ids_encontrados: List[str],
        receta_id: str,
        tools: List[Tool],
    ) -> str:
        import re

        def _ejecutar_tool(tool, *args) -> Optional[str]:
            """Ejecuta la función de la tool y devuelve str o None."""
            if tool is None:
                return None
            func = getattr(tool, "func", None)
            if callable(func):
                try:
                    res = func(*args)
                except (AttributeError, RuntimeError, ValueError, OSError):
                    return None
                return None if res is None else str(res)
            return None

        def _call_func(func, *args) -> Optional[str]:
            """Llama directamente a una función (posiblemente obtenida por getattr)
            y devuelve su resultado como str o None."""
            if not callable(func):
                return None
            try:
                res = func(*args)
            except (AttributeError, RuntimeError, ValueError, OSError):
                return None
            return None if res is None else str(res)

        respuesta = ""
        
        # PRIORIDAD 1: Verificar si quiere exportar algo (mermas, inventario, lista compras)
        # Esto debe verificarse ANTES de procesar IDs de receta
        es_export = any(
            p in ultimo_mensaje
            for p in ["word", "excel", "powerpoint", "envía", "manda", "envia"]
        )
        
        if es_export:
            # Lista de compras - PRIORIDAD ALTA
            if any(
                p in ultimo_mensaje
                for p in [
                    "lista compra",
                    "lista de compra",
                    "lista compras",
                    "lista de compras",
                ]
            ):
                if "word" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_lista_compras_a_word"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    if ids_encontrados:
                        res = _call_func(func, ";".join(ids_encontrados), 1)
                        if res is not None:
                            return res
                if "excel" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_lista_compras_a_excel"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    if ids_encontrados:
                        res = _call_func(func, ";".join(ids_encontrados), 1)
                        if res is not None:
                            return res
            
            # Reporte de mermas - PRIORIDAD ALTA
            if any(
                p in ultimo_mensaje
                for p in ["merma", "mermas", "desperdicio", "desperdicios", "informe merma", "reporte merma", "dashboard merma"]
            ):
                dias = 7
                match_dias = re.search(
                    r"(\d+)\s*(?:dias?|días?|days?|semana|ultima|última)",
                    ultimo_mensaje,
                )
                if match_dias:
                    dias = int(match_dias.group(1))
                if "semana" in ultimo_mensaje or "ultima" in ultimo_mensaje or "última" in ultimo_mensaje:
                    dias = 7
                if "word" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_reporte_mermas_a_word"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    res = _call_func(func, dias)
                    if res is not None:
                        return res
                if "excel" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_reporte_mermas_a_excel"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    res = _call_func(func, dias)
                    if res is not None:
                        return res
            
            # Inventario/Bodega - PRIORIDAD ALTA
            if any(p in ultimo_mensaje for p in ["inventario", "bodega", "stock"]):
                if "word" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_inventario_a_word"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    res = _call_func(func)
                    if res is not None:
                        return res
                if "excel" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_inventario_a_excel"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    res = _call_func(func)
                    if res is not None:
                        return res
        
        # PRIORIDAD 2: Verificar inventario (sin export)
        inventario_keywords = [
            "elaborar",
            "ingrediente",
            "ingredientes",
            "nesecita",
            "nesecitamos",
        ]
        if any(p in ultimo_mensaje for p in inventario_keywords):
            recetas_str = ";".join(ids_encontrados)
            if len(ids_encontrados) >= 2:
                plan_tool = next(
                    (t for t in tools if t.name == "planificar_evento"),
                    None,
                )
                resultado = _ejecutar_tool(
                    plan_tool,
                    f"recetas={recetas_str} | comensales=1",
                )
                if resultado is not None:
                    resultado_str = str(resultado)
                    respuesta = (
                        resultado_str
                        if "error" not in resultado_str.lower()
                        else f"❌ {resultado_str}"
                    )
            elif len(ids_encontrados) == 1:
                lista_tool = next(
                    (t for t in tools if t.name == "generar_lista_compras"),
                    None,
                )
                resultado = _ejecutar_tool(lista_tool, recetas_str, 1)
                if resultado is not None:
                    resultado_str = str(resultado)
                    respuesta = (
                        resultado_str
                        if "error" not in resultado_str.lower()
                        else f"❌ {resultado_str}"
                    )
            if respuesta:
                return respuesta

        if any(
            p in ultimo_mensaje
            for p in ["word", "excel", "powerpoint", "envía", "manda", "envia"]
        ):
            # Lista de compras
            if any(
                p in ultimo_mensaje
                for p in [
                    "lista compra",
                    "lista de compra",
                    "lista compras",
                    "lista de compras",
                ]
            ):
                if "word" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_lista_compras_a_word"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    if ids_encontrados:
                        res = _call_func(func, ";".join(ids_encontrados), 1)
                        if res is not None:
                            return res
                elif "excel" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_lista_compras_a_excel"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    if ids_encontrados:
                        res = _call_func(func, ";".join(ids_encontrados), 1)
                        if res is not None:
                            return res
            # Reporte de mermas
            elif any(
                p in ultimo_mensaje
                for p in ["merma", "mermas", "desperdicio", "desperdicios"]
            ):
                dias = 7
                match_dias = re.search(
                    r"(\d+)\s*(?:dias?|días?|days?)",
                    ultimo_mensaje,
                )
                if match_dias:
                    dias = int(match_dias.group(1))
                if "word" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_reporte_mermas_a_word"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    res = _call_func(func, dias)
                    if res is not None:
                        return res
                elif "excel" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_reporte_mermas_a_excel"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    res = _call_func(func, dias)
                    if res is not None:
                        return res
            # Inventario/Bodega
            elif any(p in ultimo_mensaje for p in ["inventario", "bodega", "stock"]):
                # Productos por caducar
                if any(p in ultimo_mensaje for p in ["caducar", "caducidad", "vencer", "vencimiento"]):
                    if "excel" in ultimo_mensaje or "word" in ultimo_mensaje or "powerpoint" in ultimo_mensaje:
                        # Exportar directamente
                        if "excel" in ultimo_mensaje:
                            tool = next(
                                (t for t in tools if t.name == "enviar_productos_por_caducar_a_excel"),
                                None,
                            )
                            func = getattr(tool, "func", None)
                            res = _call_func(func)
                            if res is not None:
                                return res
                        else:
                            # Primero consultar (guarda contexto), luego el usuario puede decir "a word/powerpoint"
                            tool = next(
                                (t for t in tools if t.name == "consultar_productos_por_caducar"),
                                None,
                            )
                            func = getattr(tool, "func", None)
                            res = _call_func(func, 7)
                            if res is not None:
                                return res
                    else:
                        # Solo consultar
                        tool = next(
                            (t for t in tools if t.name == "consultar_productos_por_caducar"),
                            None,
                        )
                        func = getattr(tool, "func", None)
                        res = _call_func(func, 7)
                        if res is not None:
                            return res
                # Inventario general
                elif "word" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_inventario_a_word"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    res = _call_func(func)
                    if res is not None:
                        return res
                elif "excel" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_inventario_a_excel"),
                        None,
                    )
                    func = getattr(tool, "func", None)
                    res = _call_func(func)
                    if res is not None:
                        return res
            # Recetas (default)
            else:
                if "word" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_receta_a_word"),
                        None,
                    )
                elif "excel" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_receta_a_excel"),
                        None,
                    )
                elif "powerpoint" in ultimo_mensaje:
                    tool = next(
                        (t for t in tools if t.name == "enviar_menu_a_powerpoint"),
                        None,
                    )
                else:
                    tool = None
                func = getattr(tool, "func", None)
                res = _call_func(func, receta_id)
                if res is not None:
                    return res

        match_escala = re.search(
            r"(?:para|a|escala\s*(?:a|para)?)\s*(\d+)\s*(?:personas?|comensales?|pax|porciones?)?",
            ultimo_mensaje,
        )
        if match_escala:
            comensales = int(match_escala.group(1))
            escala_tool = next(
                (t for t in tools if t.name == "escalar_receta"),
                None,
            )
            resultado = _ejecutar_tool(
                escala_tool,
                receta_id,
                comensales,
            )
            if resultado is not None:
                resultado_str = str(resultado)
                if "no encontrada" not in resultado_str.lower() and "error" not in resultado_str.lower():
                    return (
                        f"Aquí tienes la receta {receta_id} escalada a {comensales} "
                        f"personas:\n\n{resultado_str}"
                    )
                return f"❌ {resultado_str}"

        buscar_tool = next(
            (t for t in tools if t.name == "buscar_receta"),
            None,
        )
        resultado = _ejecutar_tool(buscar_tool, receta_id)
        if resultado is not None:
            resultado_str = str(resultado)
            if "no encontrada" not in resultado_str.lower() and "error" not in resultado_str.lower():
                return f"Aquí tienes la receta {receta_id}:\n\n{resultado_str}"
            return f"❌ {resultado_str}"

        return ""

    def _procesar_menu_por_ingredientes(self, ultimo_mensaje: str, tools: List[Tool]) -> str:
        import logging
        logging.critical(f"_PROCESAR_MENU: ultimo_mensaje={ultimo_mensaje[:100]}")
        
        es_anti_desperdicio = any(p in ultimo_mensaje for p in ["sobrante", "caducar", "desperdicio", "sobro"])
        if es_anti_desperdicio:
            anti_tool = next((t for t in tools if t.name == "menu_anti_desperdicio"), None)
            if anti_tool:
                func = getattr(anti_tool, "func", None)
                if callable(func):
                    resultado = func()
                    if resultado:
                        return str(resultado)

        menu_tool = next((t for t in tools if t.name == "sugerir_menu_por_ingredientes"), None)
        logging.critical(f"MENU_TOOL: {menu_tool}")
        if not menu_tool:
            return ""

        ingredientes_texto = ""
        
        # Palabras que NO son ingredientes (son genéricas o tipos de platos)
        generic_words = {"platos", "plato", "comida", "comidas", "algo", "todo", "cualquier", 
                        "lo", "que", "haya", "disponible", "menu", "menú", "dia", "día"}
        # Tipos de platos/categorías que NO son ingredientes específicos (incluye errores comunes)
        tipo_plato_words = {"postre", "postres", "pstre", "pstres",  # postre con typos
                           "bebida", "bebidas", "bebida", "trago", "tragos",
                           "entrante", "entrantes", "entrada", "entradas",
                           "sopa", "sopas", "crema", "caldos", "caldo",
                           "fuerte", "principal", "principales",
                           "plato", "platos", "plato", "plta", "pltos", "plats",  # platos con typos
                           "guarnición", "guarnicion", "guarniciones", "acompañante", "acompanante",
                           "ensalada", "ensaladas", "ensalada", "ensalada",
                           "carne", "carnes", "pollo", "pollos", "res", "cerdo", "pescado", "pescados",
                           "mariscos", "marisco", "aves", "ave"}
        
        # Estrategia 1: Buscar después de prefijos como "con", "que tenga", etc.
        for prefix in ["que tenga ", "que lleve ", "que llebe ", "con ", "que incluya "]:
            idx = ultimo_mensaje.find(prefix)
            if idx >= 0:
                ingredientes_texto = ultimo_mensaje[idx + len(prefix):].strip()
                # Cortar en la próxima comida o palabra clave
                for stop in [" para ", " el dia ", " día ", " desayuno ", " almuerzo ", " merienda ", " cena "]:
                    sidx = ingredientes_texto.find(stop)
                    if sidx >= 0:
                        ingredientes_texto = ingredientes_texto[:sidx]
                break
        
        # Estrategia 2: Si hay palabras de comida, extraer todo después de "menu"
        if not ingredientes_texto and any(c in ultimo_mensaje for c in ["desayuno", "almuerzo", "merienda", "cena"]):
            for keyword in ["menú", "menu"]:
                idx = ultimo_mensaje.find(keyword)
                if idx >= 0:
                    ingredientes_texto = ultimo_mensaje[idx + len(keyword):].strip()
                    break
        
        # Estrategia 3: Buscar después de "menu" o "menú"
        if not ingredientes_texto:
            for keyword in ["menú", "menu"]:
                idx = ultimo_mensaje.find(keyword)
                if idx >= 0:
                    ingredientes_texto = ultimo_mensaje[idx + len(keyword):].strip()
                    break
        
        # Filtrar stop words y palabras genéricas
        if ingredientes_texto:
            stop_words = {"para", "el", "la", "los", "las", "un", "una", "del", "de", "por", 
                         "dia", "día", "mañana", "hoy", "comida", "menu", "menú", "incluye", 
                         "incluya", "que", "tenga", "lleve", "llebe", "sea", "tengan", "4", 
                         "cuatro", "hacer", "haz", "crea", "crear", "elabora", "elaborar", 
                         "armar", "arma", "sugiere", "sugerir", "debe", "tener", "tiene", 
                         "3", "tres", "dos", "cinco", "6", "7", "8", "9", "10"}
            comida_words = {"almuerso", "almuerzo", "desayuno", "merienda", "cena"}
            
            palabras = ingredientes_texto.replace(",", " ").replace(".", "").split()
            # Filtrar: stop words + tipos de plato + palabras de comida
            ingredientes_filtrados = [p for p in palabras if p.lower() not in stop_words and p.lower() not in tipo_plato_words and p.lower() not in comida_words and len(p) > 2]
            
            ingredientes_texto = " ".join(ingredientes_filtrados)
        
        # Si aún está vacío o solo tiene palabras genéricas, intentar con regex
        if not ingredientes_texto or len(ingredientes_texto.split()) == 0:
            import re
            match = re.search(r'(?:con|que tenga|que lleve|que incluya)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ,\s]+?)(?:\s*(?:para|el dia|día|desayuno|almuerzo|merienda|cena|$))', ultimo_mensaje, re.IGNORECASE)
            if match:
                ingredientes_texto = match.group(1).strip()
                # Filtrar genéricas del regex también
                palabras = ingredientes_texto.replace(",", " ").split()
                ingredientes_filtrados = [p for p in palabras if p.lower() not in generic_words and len(p) > 2]
                ingredientes_texto = " ".join(ingredientes_filtrados)
        
        # Logging para debug
        logging.critical(f"INGREDIENTES_EXTRAIDOS: '{ingredientes_texto}' (genérico={all(p.lower() in generic_words for p in ingredientes_texto.split()) if ingredientes_texto else True})")

        if ingredientes_texto:
            func = getattr(menu_tool, "func", None)
            if not callable(func):
                return ""
            
            # Si los ingredientes son muy genéricos o solo tipos de plato, usar menú anti-desperdicio
            ingredientes_lista = ingredientes_texto.replace(",", " ").split()
            generic_words = {"platos", "comida", "comidas", "algo", "todo", "cualquier", "lo", "que", "haya", "disponible"}
            # Combinar palabras genéricas + tipos de plato para la verificación
            todas_genericas = generic_words.union(tipo_plato_words)
            es_generico = len(ingredientes_lista) == 0 or all(p.lower() in todas_genericas for p in ingredientes_lista)
            
            logging.critical(f"GENÉRICO_CHECK: ingredientes='{ingredientes_texto}', lista={ingredientes_lista}, es_generico={es_generico}")
            
            if es_generico:
                # Usar menú anti-desperdicio
                logging.critical("GENÉRICO_DETECTADO: Activando menú anti-desperdicio")
                anti_tool = next((t for t in tools if t.name == "menu_anti_desperdicio"), None)
                if anti_tool:
                    anti_func = getattr(anti_tool, "func", None)
                    if callable(anti_func):
                        resultado = anti_func()
                        logging.critical(f"ANTI_DESPERDICIO_RESULT: {resultado[:100] if resultado else 'None'}")
                        return f"📋 **Menú Sugerido (basado en inventario):**\n\n{resultado}"
                else:
                    logging.critical("ANTI_DESPERDICIO_TOOL: No encontrada")
            
            resultado = func(ingredientes_texto)
            if resultado is None:
                return ""
            resultado_str = str(resultado)
            if "error" not in resultado_str.lower() and "no encontraron" not in resultado_str.lower():
                return resultado_str
            # Si no hay recetas, sugerir usar botón para cargar
            return f"❌ No se encontraron recetas con: {ingredientes_texto}. 💡 Usa el botón [+] para cargar recetas con estos ingredientes: {', '.join(ingredientes_lista[:5])}"
        
        return ""

    def _buscar_receta_por_nombre(
        self,
        ultimo_mensaje: str,
        tools: List[Tool],
        messages: List[BaseMessage],
    ) -> str:
        buscar_tool = next((t for t in tools if t.name == "buscar_receta"), None)
        if not buscar_tool:
            return ""
        func = getattr(buscar_tool, "func", None)
        if not callable(func):
            return ""

        # Extraer el nombre de la receta limpiando palabras de comando
        consulta = ultimo_mensaje
        for prefix in [
            "dame la receta",
            "dame la reseta",
            "dame receta",
            "busca la receta",
            "buscar la receta",
            "encuentra la receta",
            "busca receta",
            "buscar receta",
            "dame",
            "busca",
            "buscar",
            "receta",
            "reseta",
            "la receta",
            "encuentra",
        ]:
            idx = ultimo_mensaje.find(prefix)
            if idx >= 0:
                consulta = ultimo_mensaje[idx + len(prefix):].strip()
                break
        
        # Limpiar artículos y preposiciones del inicio
        for word in ["el", "la", "los", "las", "un", "una", "de", "del", "con", "que", "sea"]:
            if consulta.lower().startswith(word + " "):
                consulta = consulta[len(word):].strip()
        
        # Si la consulta está vacía o es muy corta, no buscar
        if not consulta or len(consulta) < 3:
            return ""

        resultado = func(consulta)
        if resultado is None:
            return ""
        resultado_str = str(resultado)
        if "no encontrada" not in resultado_str.lower():
            messages.append(SystemMessage(content=f"Resultado:\n{resultado_str}"))
            return f"Aquí tienes:\n\n{resultado_str}"
        return f"❌ {resultado_str}"

    def _ejecutar_herramienta_detectada(self, historial: List[Dict[str, str]]) -> str:
        ultimo_mensaje = historial[-1]["contenido"].lower() if historial else ""
        if not self.db_manager or not ultimo_mensaje:
            return ""

        from agents.tools import crear_herramientas_operativas
        tools = crear_herramientas_operativas(self.db_manager)

        for nombre, info in HERRAMIENTAS_DETECTABLES.items():
            for patron in info["patrones"]:
                idx = ultimo_mensaje.find(patron)
                if idx < 0:
                    continue

                tool = next((t for t in tools if t.name == nombre), None)
                if not tool:
                    continue
                func = getattr(tool, "func", None)
                if not callable(func):
                    continue

                parametros = ultimo_mensaje[idx + len(patron):].strip()
                # Ejecutar la herramienta y asegurar que devolvemos un str
                try:
                    if parametros:
                        resultado = func(parametros)
                    else:
                        resultado = func()
                except (TypeError, ValueError, RuntimeError) as exc:
                    return f"❌ Error al ejecutar {nombre}: {exc}"

                if resultado is None:
                    return ""
                if isinstance(resultado, str):
                    return resultado
                # Coerción segura a str
                return str(resultado)

        return ""

    def clasificar_intencion(self, texto_usuario: str) -> str:
        texto_lower = texto_usuario.lower()
        palabras_rag = ["receta", "ingredientes", "alergenos", "bpm", "manual", "procedimiento"]
        palabras_mcp = ["word", "excel", "powerpoint", "documento", "menu", "costo", "inventario", "crear", "escribir", "envia", "manda", "evento", "planificar", "comensales"]
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
        # Compatibilidad con Pydantic v2 (model_json_schema) y v1 (schema)
        schema_dict = None
        try:
            if hasattr(schema_class, "model_json_schema"):
                schema_dict = schema_class.model_json_schema()
            elif hasattr(schema_class, "schema"):
                # pydantic v1
                try:
                    schema_dict = schema_class.schema()
                except TypeError:
                    # schema may be a property or already a dict
                    schema_dict = schema_class.schema
            elif isinstance(schema_class, dict):
                schema_dict = schema_class
            else:
                # If an instance of a BaseModel was passed
                try:
                    from pydantic import BaseModel

                    if isinstance(schema_class, BaseModel):
                        cls = schema_class.__class__
                        if hasattr(cls, "model_json_schema"):
                            schema_dict = cls.model_json_schema()
                        else:
                            schema_dict = cls.schema()
                except (ImportError, AttributeError, TypeError):
                    # pydantic not available or schema introspection failed
                    schema_dict = None

            if schema_dict is None:
                schema_dict = {"schema": str(schema_class)}

        except (AttributeError, TypeError):
            # Fallback when schema extraction raises common attribute/type errors
            schema_dict = {"schema": str(schema_class)}

        instruction = f"Extrae la siguiente informacion en JSON segun este esquema: {schema_dict}"
        messages = [
            SystemMessage(content=instruction),
            HumanMessage(content=prompt),
        ]
        respuesta = self.llm.invoke(messages)
        import json

        text = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": "No se pudo parsear la respuesta como JSON", "raw": text}

    def get_provider_display_name(self) -> str:
        return ConfigManager.get_provider_display_name(self.provider)

    def get_available_models(self) -> List[str]:
        return ConfigManager.get_models_for_provider(self.provider)