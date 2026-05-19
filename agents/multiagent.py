"""
Sistema Multiagente para ChefChat Pro

Arquitectura:
├── Planner: Decide qué agentes usar
├── Executor: Coordina la ejecución
├── RecipeAgent: Maneja búsquedas de recetas
├── InventoryAgent: Maneja inventario y stock
├── MenuAgent: Maneja menús y planificación
├── WasteAgent: Maneja mermas y desperdicio
└── DocumentAgent: Maneja documentos RAG

Cada agente tiene su propio system prompt y usa el LLM seleccionado por el usuario.
Todos limitados a responder solo con datos del RAG/base de datos.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class AgentRole(Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    RECIPE = "recipe"
    INVENTORY = "inventory"
    MENU = "menu"
    WASTE = "waste"
    DOCUMENT = "document"


@dataclass
class AgentTask:
    """Tarea asignada a un agente."""
    role: AgentRole
    query: str
    priority: int = 1
    context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    success: bool = False
    reasoning: List[str] = field(default_factory=list)


@dataclass
class PlanResult:
    """Resultado del planner."""
    tasks: List[AgentTask]
    strategy: str
    confidence: float
    reasoning: List[str]


class BaseAgent(ABC):
    """Clase base para todos los agentes."""

    def __init__(self, role: AgentRole, tools: Optional[List[Any]] = None, llm: Any = None):
        self.role = role
        self.tools = tools or []
        self.llm = llm
        self.reasoning: List[str] = []
        self.keywords: List[str] = []

    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """Determina si este agente puede manejar la consulta."""

    @abstractmethod
    def execute(self, task: AgentTask) -> AgentTask:
        """Ejecuta la tarea asignada."""

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Prompt de sistema especializado para este agente."""

    def add_reasoning(self, reasoning: str):
        """Agrega paso de razonamiento."""
        self.reasoning.append(reasoning)
        logging.info("[%s] %s", self.role.value, reasoning)

    def get_tool(self, tool_name: str) -> Optional[Any]:
        """Obtiene una herramienta por nombre."""
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
        return None

    def call_tool(self, tool_name: str, *args) -> Optional[str]:
        """Llama a una herramienta y retorna el resultado."""
        tool = self.get_tool(tool_name)
        if tool:
            func = getattr(tool, 'func', None)
            if callable(func):
                try:
                    result = func(*args)
                    return str(result) if result else None
                except (AttributeError, TypeError, ValueError, RuntimeError) as e:
                    self.add_reasoning(f"Error calling {tool_name}: {e}")
                    return None
        return None

    def _ask_llm(self, query: str, tool_results: str = "") -> Optional[str]:
        """
        Consulta al LLM con el prompt del agente, limitado a datos RAG.
        Combina resultados de tools con el query del usuario.
        """
        if not self.llm:
            return None
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            context = f"DATOS DEL SISTEMA:\n{tool_results}" if tool_results else ""
            mensaje = f"{context}\n\nCONSULTA DEL USUARIO: {query}" if context else query

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=mensaje)
            ]
            response = self.llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except (ImportError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            self.add_reasoning(f"LLM error: {e}")
            return None


class RecipeAgent(BaseAgent):
    """Agente especializado en recetas."""

    def __init__(self, tools: Optional[List[Any]] = None, llm: Any = None):
        super().__init__(AgentRole.RECIPE, tools, llm)
        self.keywords = ["receta", "reseta", "cocinar", "preparar", "ingredientes", "plato"]

    @property
    def system_prompt(self) -> str:
        return """You are the Executive Chef of ChefChat Pro, specializing in recipes.

ABSOLUTE RULES:
1. ONLY respond with recipes that exist in the system's RAG database.
2. NEVER invent recipes. If not in RAG, say "Recipe not found in the system."
3. Always mention the recipe ID when referencing it.
4. Show ingredients, prep time, and servings when available.
5. For ingredient-based searches, find recipes containing those ingredients.
6. To scale recipes, use the escalar_receta tool.
7. ALWAYS respond in Spanish, with clear and professional formatting.
8. If data is insufficient, suggest loading more recipes via the [+] button."""


    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning("Procesando busqueda de receta: %s..." % task.query[:50])

        query_lower = task.query.lower()

        # Paso 1: intentar tools deterministas
        tool_result = None
        if any(kw in query_lower for kw in ["con ", "que tenga ", "ingredientes"]):
            self.add_reasoning("Detectada busqueda por ingredientes")
            tool_result = self._search_by_ingredients(task.query)
        else:
            self.add_reasoning("Detectada busqueda por nombre")
            tool_result = self._search_by_name(task.query)

        # Paso 2: si tools fallaron o respuesta es pobre, usar LLM con RAG
        if not tool_result or "no encontrada" in tool_result.lower() or "no encontro" in tool_result.lower():
            self.add_reasoning("Tools no encontraron suficiente, consultando LLM con RAG...")
            llm_response = self._ask_llm(task.query, tool_result or "")
            if llm_response:
                task.result = llm_response
                task.success = True
            else:
                task.result = tool_result or "No se encontro informacion de recetas en el sistema."
                task.success = False
        else:
            task.result = tool_result
            task.success = True

        task.reasoning = self.reasoning.copy()
        return task

    def _search_by_name(self, query: str) -> Optional[str]:
        for prefix in ["receta", "reseta", "busca", "dame", "buscar"]:
            idx = query.lower().find(prefix)
            if idx >= 0:
                name = query[idx + len(prefix):].strip()
                for word in ["la", "el", "un", "una", "de", "del"]:
                    if name.lower().startswith(word + " "):
                        name = name[len(word) + 1:]
                if name:
                    return self.call_tool("buscar_receta", name)
        return self.call_tool("buscar_receta", query)

    def _search_by_ingredients(self, query: str) -> Optional[str]:
        ingredients = []
        for prefix in ["con", "que tenga", "que lleve"]:
            idx = query.lower().find(prefix)
            if idx >= 0:
                text = query[idx + len(prefix):].strip()
                ingredients = [i.strip() for i in text.replace(",", " ").split() if len(i.strip()) > 2]
                break

        if not ingredients:
            return None

        results = []
        for ing in ingredients[:3]:
            result = self.call_tool("buscar_recetas_con_ingrediente", ing)
            if result and "no encontraron" not in result.lower():
                results.append(result)

        return "\n\n".join(results) if results else None


class InventoryAgent(BaseAgent):
    """Agente especializado en inventario."""

    def __init__(self, tools: Optional[List[Any]] = None, llm: Any = None):
        super().__init__(AgentRole.INVENTORY, tools, llm)
        self.keywords = ["inventario", "stock", "producto", "caducar", "caducidad",
                         "vencer", "comprar", "compra", "caduca", "vence"]

    @property
    def system_prompt(self) -> str:
        return """You are the Inventory Manager of ChefChat Pro.

ABSOLUTE RULES:
1. ONLY respond with data from the system's registered inventory.
2. NEVER invent quantities, products, or dates.
3. Always alert about expiring products or low stock.
4. Suggest recipes to use urgent products when relevant.
5. For purchase lists, use generar_lista_compras.
6. To register purchases, use natural language: 'se compro X de Y caduca Z'.
7. ALWAYS respond in Spanish, with professional report formatting.
8. If no data exists, state it clearly and suggest loading inventory."""


    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning("Procesando consulta de inventario: %s..." % task.query[:50])

        query_lower = task.query.lower()
        tool_result = None

        if any(kw in query_lower for kw in ["caducar", "caducidad", "vencer", "caduca", "vence"]):
            self.add_reasoning("Detectada consulta de productos por caducar")
            dias = self._extract_days(task.query)
            tool_result = self.call_tool("productos_por_caducar", dias)
        elif "stock bajo" in query_lower or "poco stock" in query_lower:
            self.add_reasoning("Detectada consulta de stock bajo")
            tool_result = self.call_tool("verificar_stock_bajo")
        elif any(kw in query_lower for kw in ["compr", "se compro", "ingresa", "agrega"]):
            self.add_reasoning("Detectado registro de compra")
            tool_result = self.call_tool("registrar_compra", task.query)
        else:
            self.add_reasoning("Detectada consulta general de inventario")
            tool_result = self.call_tool("consultar_productos_por_caducar", 7)

        if not tool_result or "error" in tool_result.lower():
            self.add_reasoning("Tools insuficientes, consultando LLM con datos RAG...")
            llm_response = self._ask_llm(task.query, tool_result or "")
            if llm_response:
                task.result = llm_response
                task.success = True
            else:
                task.result = tool_result or "No se encontro informacion de inventario."
                task.success = False
        else:
            task.result = tool_result
            task.success = True

        task.reasoning = self.reasoning.copy()
        return task

    def _extract_days(self, query: str) -> int:
        match = re.search(r'(\d+)\s*(?:dias?|días?|days?)', query)
        if match:
            return int(match.group(1))
        if "semana" in query.lower():
            return 7
        if "hoy" in query.lower():
            return 1
        return 7


class MenuAgent(BaseAgent):
    """Agente especializado en menus."""

    def __init__(self, tools: Optional[List[Any]] = None, llm: Any = None):
        super().__init__(AgentRole.MENU, tools, llm)
        self.keywords = ["menu", "menú", "planificar", "semanal", "dia", "desayuno",
                         "almuerzo", "cena", "merienda", "plato", "precio"]

    @property
    def system_prompt(self) -> str:
        return """You are the Planning Chef of ChefChat Pro.

ABSOLUTE RULES:
1. ONLY create menus using recipes that EXIST in the system's RAG.
2. NEVER invent dishes, names, or prices. Everything must come from RAG.
3. To create a new menu: search recipes in RAG, select suitable ones, use agregar_plato_menu or agregar_receta_al_menu.
4. Each menu must include: starter/soup, main course, dessert, beverage. Real prices from RAG.
5. When creating a menu, show available recipes first, then suggest combinations.
6. Query menu by day (Monday-Sunday) or by service (breakfast, lunch, snack).
7. ALWAYS respond in Spanish, with professional restaurant menu formatting and prices in USD.
8. If insufficient recipes in RAG, state it and suggest loading more via the [+] button.
9. ALL created menus must be exportable to Word, Excel, or PowerPoint."""


    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning("Procesando consulta de menu: %s..." % task.query[:50])

        query_lower = task.query.lower()

        if any(kw in query_lower for kw in ["crear", "elabora", "elaborar", "arma", "armar",
                                              "haz", "hacer", "genera", "generar", "nuevo"]):
            self.add_reasoning("Detectada solicitud de CREACION de menu - buscando recetas en RAG")
            # Primero buscar productos por caducar para menu anti-desperdicio
            productos_caducar = self.call_tool("productos_por_caducar", 5) or ""
            menu_anti = self.call_tool("menu_anti_desperdicio") or ""
            recetas_disponibles = self.call_tool("buscar_recetas_para_menu",
                                                  query_lower.replace("crear", "").replace("elabora", "")
                                                  .replace("menu", "").strip() or "general") or ""
            # Combinar todo para el LLM
            tool_result = (f"PRODUCTOS POR CADUCAR (para aprovechar):\n{productos_caducar}\n\n"
                          f"MENU ANTI-DESPERDICIO:\n{menu_anti}\n\n"
                          f"RECETAS DISPONIBLES:\n{recetas_disponibles}")
        elif any(kw in query_lower for kw in ["semanal", "semana", "completo"]):
            self.add_reasoning("Detectada consulta de menu completo")
            tool_result = self.call_tool("consultar_menu_semanal", "menu completo")
        elif any(kw in query_lower for kw in ["agregar", "añadir", "configurar"]):
            self.add_reasoning("Detectada solicitud de configuracion de menu")
            tool_result = self.call_tool("consultar_menu_semanal", task.query)
        elif "sugerir" in query_lower or "sugiere" in query_lower or "anti" in query_lower:
            self.add_reasoning("Detectada solicitud de menu anti-desperdicio")
            tool_result = self.call_tool("menu_anti_desperdicio")
        else:
            self.add_reasoning("Detectada consulta de menu por dia/servicio")
            tool_result = self.call_tool("consultar_menu_semanal", task.query)

        if not tool_result or "no hay" in tool_result.lower() or "error" in tool_result.lower():
            self.add_reasoning("Consultando LLM con datos del menu RAG...")
            llm_response = self._ask_llm(task.query, tool_result or "")
            if llm_response:
                task.result = llm_response
                task.success = True
            else:
                task.result = tool_result or "No se encontro menu configurado. Para crear uno, di 'crea un menu para...'"
                task.success = False
        else:
            task.result = tool_result
            task.success = True

        task.reasoning = self.reasoning.copy()
        return task


class WasteAgent(BaseAgent):
    """Agente especializado en mermas y desperdicio."""

    def __init__(self, tools: Optional[List[Any]] = None, llm: Any = None):
        super().__init__(AgentRole.WASTE, tools, llm)
        self.keywords = ["merma", "mermas", "desperdicio", "sobrante", "sobrantes",
                         "perdida", "sobra", "echo a perder", "caduco", "caducado"]

    @property
    def system_prompt(self) -> str:
        return """You are the Waste Controller of ChefChat Pro.

ABSOLUTE RULES:
1. ONLY report waste registered in the system. NEVER invent quantities.
2. To register waste: 'X kilos of Y as waste' or 'producto, cantidad, unidad, motivo'.
3. Generate professional dashboard reports with: total waste, total cost, top products, daily trend.
4. Classify waste by type: vegetables, proteins, bakery, overproduction, accidents.
5. Suggest actions to reduce waste based on detected patterns.
6. ALL reports must be exportable to Word (executive report), Excel (tabular data), or PowerPoint (visual dashboard).
7. ALWAYS respond in Spanish, with quality control report formatting.
8. If no waste in the period, state it clearly and suggest using 'seed_mermas' for test data."""


    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning("Procesando consulta de mermas: %s..." % task.query[:50])

        dias = self._extract_days(task.query)
        query_lower = task.query.lower()

        if any(kw in query_lower for kw in ["dashboard", "informe", "reporte completo",
                                              "analisis", "analisis de mermas"]):
            self.add_reasoning("Detectada solicitud de DASHBOARD de mermas")
            reporte = self.call_tool("reporte_mermas", dias) or ""
            sobrantes = self.call_tool("dashboard_sobrantes", dias) or ""
            tool_result = reporte + "\n\n" + sobrantes if sobrantes else reporte
        elif any(kw in query_lower for kw in ["registrar", "registra", "reporto", "anotar",
                                              "de merma", "echo a perder", "sobra",
                                              "caduco", "caducado"]):
            self.add_reasoning("Detectado registro de merma")
            tool_result = self.call_tool("registrar_merma", task.query)
        elif "excel" in task.query.lower() or "exportar" in query_lower:
            self.add_reasoning("Detectada exportacion")
            tool_result = self.call_tool("reporte_mermas", dias)
        elif "word" in task.query.lower():
            self.add_reasoning("Detectada exportacion a Word")
            tool_result = self.call_tool("reporte_mermas", dias)
        else:
            self.add_reasoning("Generando reporte de mermas (%s dias)" % dias)
            tool_result = self.call_tool("reporte_mermas", dias)

        if tool_result and "error" not in tool_result.lower():
            task.result = tool_result
            task.success = True
        else:
            self.add_reasoning("Consultando LLM...")
            llm_response = self._ask_llm(task.query, tool_result or "")
            if llm_response:
                task.result = llm_response
                task.success = True
            else:
                task.result = tool_result or "No hay mermas registradas en el periodo consultado."
                task.success = False

        # Guardar contexto para exportacion a Office (completo, sin truncar)
        try:
            from agents.orchestrator import guardar_contexto_exportacion
            titulo = "Dashboard de Mermas - ChefChat Pro"
            lineas_reporte = (task.result or "").split("\n")
            datos_export = [[l] for l in lineas_reporte if l.strip()]
            guardar_contexto_exportacion(
                datos=datos_export,
                columnas=["Informe de Mermas"],
                titulo=titulo
            )
        except Exception:
            pass

        task.reasoning = self.reasoning.copy()
        return task

    def _extract_days(self, query: str) -> int:
        """Extrae el numero de dias de una consulta de mermas."""
        match = re.search(r'(\d+)\s*(?:dias?|días?|days?|semana)', query)
        if match:
            return int(match.group(1))
        meses = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
                 "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
        match_fecha = re.search(r'(\d{1,2})\s*(?:de\s+)?(' + '|'.join(meses.keys()) + ')', query)
        if match_fecha:
            from datetime import datetime
            dia = int(match_fecha.group(1))
            mes = meses[match_fecha.group(2)]
            hoy = datetime.now()
            fecha = datetime(hoy.year, mes, dia)
            if fecha > hoy:
                fecha = fecha.replace(year=hoy.year - 1)
            return (hoy - fecha).days + 1
        if "hoy" in query.lower():
            return 1
        if "semana" in query.lower():
            return 7
        return 30


class DocumentAgent(BaseAgent):
    """Agente especializado en documentos RAG."""

    def __init__(self, tools: Optional[List[Any]] = None, llm: Any = None):
        super().__init__(AgentRole.DOCUMENT, tools, llm)
        self.keywords = ["documento", "documentos", "manual", "protocolo", "capacitacion",
                         "bpm", "buenas practicas", "busca documento", "buscar documento"]

    @property
    def system_prompt(self) -> str:
        return """You are the Compliance, Documentation and Personnel Officer of ChefChat Pro.

ABSOLUTE RULES - DOCUMENTS:
1. ONLY respond with information from documents loaded in the RAG system.
2. NEVER invent procedures, protocols, or manuals.
3. Always cite the source document name.
4. For BPM, emergency protocols, allergens, search documents by type.

ABSOLUTE RULES - PERSONNEL:
5. You are responsible for managing restaurant staff.
6. You can query: active staff, today's shift, staff on leave.
7. Leave types: reposo_medico, permiso_maternidad, permiso_personal (paternity), vacaciones, suspendido.
8. To register leave: 'juan took paternity leave 6 days'.
9. To reinstate: 'reinstate juan' or 'EMP001 returns'.
10. Always show: name, position, shift, contract type (fixed/temporary), return date.
11. ALL personnel reports must be exportable to Word or Excel.
12. ALWAYS respond in Spanish."""


    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        keywords_all = self.keywords + ["personal", "empleado", "trabajador", "turno",
                                         "ausencia", "permiso", "reposo", "maternidad",
                                         "paternidad", "vacaciones", "reincorpora",
                                         "quien trabaja", "quien esta", "staff"]
        return any(kw in query_lower for kw in keywords_all)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning("Procesando consulta: %s..." % task.query[:50])

        query_lower = task.query.lower()

        # Detectar si es consulta de personal
        es_personal = any(kw in query_lower for kw in
                          ["personal", "empleado", "trabajador", "turno",
                           "ausencia", "permiso", "reposo", "maternidad",
                           "paternidad", "vacaciones", "staff", "equipo",
                           "quien trabaja", "quien esta", "reincorpora",
                           "saco permiso", "pidio permiso", "de baja"])

        if es_personal:
            self.add_reasoning("Detectada consulta de PERSONAL")

            if any(kw in query_lower for kw in ["ausente", "permiso", "reposo", "maternidad",
                                                  "paternidad", "vacaciones", "falta", "baja"]):
                if any(kw in query_lower for kw in ["saco", "sacó", "pidio", "pidió", "registra",
                                                      "anota", "reporta"]):
                    tool_result = self.call_tool("registrar_permiso_rapido", task.query)
                else:
                    tool_result = self.call_tool("consultar_personal_ausente")
            elif any(kw in query_lower for kw in ["reincorpora", "vuelve", "regresa", "alta"]):
                # Extraer nombre o ID
                import re
                match_id = re.search(r'\b(EMP\d+)\b', task.query, re.IGNORECASE)
                id_emp = match_id.group(1) if match_id else task.query
                tool_result = self.call_tool("reincorporar_trabajador", id_emp)
            elif any(kw in query_lower for kw in ["turno", "hoy", "quien trabaja", "quien esta"]):
                turno = ""
                for t in ["matutino", "vespertino", "nocturno", "mixto"]:
                    if t in query_lower:
                        turno = t
                        break
                tool_result = self.call_tool("consultar_turno_hoy", turno)
            elif "activo" in query_lower:
                tool_result = self.call_tool("consultar_personal_activo")
            else:
                tool_result = self.call_tool("consultar_personal_activo")
        else:
            # Busqueda normal de documentos RAG
            from data.rag_store import RAGStore
            rag = RAGStore()

            termino = task.query
            for prefix in ["busca documento", "buscar documento", "busca", "documento",
                           "capacitacion", "capacitación", "manual", "protocolo", "bpm",
                           "personal", "empleado"]:
                idx = task.query.lower().find(prefix)
                if idx >= 0:
                    termino = task.query[idx + len(prefix):].strip()
                    break

            for word in ["el", "la", "los", "las", "un", "una", "de", "del", "con", "que", "sea"]:
                if termino.lower().startswith(word + " "):
                    termino = termino[len(word) + 1:]

            self.add_reasoning("Buscando documentos con termino: %s" % termino)
            docs = rag.buscar_documento(termino)

            if not docs:
                self.add_reasoning("No encontrado, intentando con palabras clave individuales")
                for palabra in termino.split():
                    if len(palabra) > 3:
                        docs = rag.buscar_documento(palabra)
                        if docs:
                            break

            if docs:
                contenidos = []
                lineas = ["DOCUMENTOS ENCONTRADOS (%s):" % len(docs), "=" * 40]
                for d in docs[:10]:
                    nombre = d.get('nombre', 'Sin nombre')
                    tipo = d.get('tipo', 'general')
                    contenido = d.get('contenido_completo') or d.get('contenido_preview') or ''
                    lineas.append("")
                    lineas.append("--- %s (tipo: %s) ---" % (nombre, tipo))
                    if contenido:
                        lineas.append(contenido[:3000])
                        contenidos.append("# %s\n\n%s" % (nombre, contenido))
                tool_result = "\n".join(lineas)
            else:
                tool_result = None

        if tool_result and "error" not in tool_result.lower():
            task.result = tool_result
            task.success = True
        else:
            self.add_reasoning("Consultando LLM...")
            llm_response = self._ask_llm(task.query, tool_result or "")
            if llm_response:
                task.result = llm_response
                task.success = True
            else:
                task.result = tool_result or "No se encontro informacion en el sistema RAG."
                task.success = False

        task.reasoning = self.reasoning.copy()
        return task


class Planner:
    """Agente planificador que decide qué agentes usar."""

    def __init__(self, agents: List[BaseAgent]):
        self.agents = agents
        self.reasoning: List[str] = []

    def plan(self, query: str) -> PlanResult:
        """Genera un plan de ejecución para la consulta."""
        self.reasoning = []
        self.add_reasoning(f"Analizando consulta: {query[:80]}...")

        tasks = []
        for agent in self.agents:
            if agent.can_handle(query):
                task = AgentTask(
                    role=agent.role,
                    query=query,
                    priority=self._calculate_priority(agent, query)
                )
                tasks.append(task)
                self.add_reasoning(f"Agente {agent.role.value} asignado (prioridad: {task.priority})")

        if not tasks:
            self.add_reasoning("No se encontró agente específico, usando agente general")
            tasks.append(AgentTask(role=AgentRole.EXECUTOR, query=query))

        tasks.sort(key=lambda t: t.priority, reverse=True)

        strategy = self._determine_strategy(tasks)
        self.add_reasoning(f"Estrategia seleccionada: {strategy}")

        return PlanResult(
            tasks=tasks,
            strategy=strategy,
            confidence=self._calculate_confidence(tasks),
            reasoning=self.reasoning.copy()
        )

    def _calculate_priority(self, agent: BaseAgent, query: str) -> int:
        """Calcula la prioridad de un agente para una consulta."""
        priority = 1
        query_lower = query.lower()

        keyword_matches = sum(1 for kw in agent.keywords if kw in query_lower)
        priority += keyword_matches * 2

        if agent.role == AgentRole.DOCUMENT and "documento" in query_lower:
            priority += 5

        return priority

    def _determine_strategy(self, tasks: List[AgentTask]) -> str:
        """Determina la estrategia de ejecución."""
        if len(tasks) == 1:
            return "single_agent"
        elif len(tasks) == 2:
            return "parallel"
        else:
            return "sequential"

    def _calculate_confidence(self, tasks: List[AgentTask]) -> float:
        """Calcula la confianza del plan."""
        if not tasks:
            return 0.0
        max_priority = max(t.priority for t in tasks)
        return min(max_priority / 10.0, 1.0)

    def add_reasoning(self, reasoning: str):
        self.reasoning.append(reasoning)
        logging.info(f"[Planner] {reasoning}")


class Executor:
    """Agente ejecutor que coordina la ejecución de tareas."""

    def __init__(self, agents: Dict[AgentRole, BaseAgent]):
        self.agents = agents
        self.reasoning: List[str] = []

    def execute(self, plan: PlanResult) -> str:
        """Ejecuta el plan generado por el planner."""
        self.reasoning = []
        self.add_reasoning(f"Ejecutando plan con {len(plan.tasks)} tareas, estrategia: {plan.strategy}")

        if plan.strategy == "single_agent":
            return self._execute_single(plan.tasks[0])
        elif plan.strategy == "parallel":
            return self._execute_parallel(plan.tasks)
        else:
            return self._execute_sequential(plan.tasks)

    def _execute_single(self, task: AgentTask) -> str:
        """Ejecuta una sola tarea."""
        agent = self.agents.get(task.role)
        if not agent:
            self.add_reasoning(f"Error: No se encontró agente para {task.role.value}")
            return f"Error: No se encontró agente para manejar esta consulta"

        self.add_reasoning(f"Ejecutando agente {task.role.value}")
        result = agent.execute(task)

        if result.success:
            self.add_reasoning(f"Agente {task.role.value} completado exitosamente")
            return result.result or ""

        self.add_reasoning(f"Agente {task.role.value} no pudo completar la tarea")
        return result.result or "No se pudo procesar la consulta"

    def _execute_parallel(self, tasks: List[AgentTask]) -> str:
        """Ejecuta tareas en paralelo y combina resultados."""
        results = []

        for task in tasks:
            agent = self.agents.get(task.role)
            if agent:
                self.add_reasoning(f"Ejecutando agente {task.role.value} en paralelo")
                result = agent.execute(task)
                if result.success and result.result:
                    results.append(result.result)

        if results:
            self.add_reasoning(f"Combinando {len(results)} resultados")
            return "\n\n---\n\n".join(results)
        else:
            return "No se encontraron resultados"

    def _execute_sequential(self, tasks: List[AgentTask]) -> str:
        """Ejecuta tareas secuencialmente con fallback."""
        for task in tasks:
            agent = self.agents.get(task.role)
            if agent:
                self.add_reasoning(f"Ejecutando agente {task.role.value} (secuencial)")
                result = agent.execute(task)
                if result.success:
                    self.add_reasoning(f"Agente {task.role.value} completado")
                    return result.result or ""
                self.add_reasoning(f"Agente {task.role.value} falló, intentando siguiente")

        return "No se pudo procesar la consulta con ningún agente"

    def add_reasoning(self, reasoning: str):
        self.reasoning.append(reasoning)
        logging.info(f"[Executor] {reasoning}")


class MultiAgentSystem:
    """Sistema multiagente principal para ChefChat Pro."""

    def __init__(self, tools: Optional[List[Any]] = None, llm: Any = None):
        self.tools = tools or []
        self.llm = llm

        self.recipe_agent = RecipeAgent(self.tools, self.llm)
        self.inventory_agent = InventoryAgent(self.tools, self.llm)
        self.menu_agent = MenuAgent(self.tools, self.llm)
        self.waste_agent = WasteAgent(self.tools, self.llm)
        self.document_agent = DocumentAgent(self.tools, self.llm)

        self.agents: Dict[AgentRole, BaseAgent] = {
            AgentRole.RECIPE: self.recipe_agent,
            AgentRole.INVENTORY: self.inventory_agent,
            AgentRole.MENU: self.menu_agent,
            AgentRole.WASTE: self.waste_agent,
            AgentRole.DOCUMENT: self.document_agent,
        }

        self.planner = Planner(list(self.agents.values()))
        self.executor = Executor(self.agents)

        self.last_reasoning: List[str] = []

    def process(self, query: str) -> str:
        """Procesa una consulta usando el sistema multiagente."""
        logging.info(f"[MultiAgent] Processing: {query[:80]}...")

        plan = self.planner.plan(query)

        result = self.executor.execute(plan)

        self.last_reasoning = plan.reasoning + self.executor.reasoning

        return result

    def get_reasoning(self) -> List[str]:
        """Obtiene la cadena de razonamiento de la última ejecución."""
        return self.last_reasoning

    def update_tools(self, tools: List[Any]):
        """Actualiza las herramientas de todos los agentes."""
        self.tools = tools
        for agent in self.agents.values():
            agent.tools = tools
