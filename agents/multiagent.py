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
"""

import logging
import re
from typing import List, Dict, Any, Optional, Callable
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

    def __init__(self, role: AgentRole, tools: List[Any] = None):
        self.role = role
        self.tools = tools or []
        self.reasoning: List[str] = []

    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """Determina si este agente puede manejar la consulta."""
        pass

    @abstractmethod
    def execute(self, task: AgentTask) -> AgentTask:
        """Ejecuta la tarea asignada."""
        pass

    def add_reasoning(self, reasoning: str):
        """Agrega paso de razonamiento."""
        self.reasoning.append(reasoning)
        logging.info(f"[{self.role.value}] {reasoning}")

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
                except Exception as e:
                    self.add_reasoning(f"Error calling {tool_name}: {e}")
                    return None
        return None


class RecipeAgent(BaseAgent):
    """Agente especializado en recetas."""

    def __init__(self, tools: List[Any] = None):
        super().__init__(AgentRole.RECIPE, tools)
        self.keywords = ["receta", "reseta", "cocinar", "preparar", "ingredientes", "plato"]

    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning(f"Procesando búsqueda de receta: {task.query[:50]}...")

        query_lower = task.query.lower()

        if any(kw in query_lower for kw in ["con ", "que tenga ", "ingredientes"]):
            self.add_reasoning("Detectada búsqueda por ingredientes")
            result = self._search_by_ingredients(task.query)
        else:
            self.add_reasoning("Detectada búsqueda por nombre")
            result = self._search_by_name(task.query)

        task.result = result
        task.success = result is not None and "no encontrada" not in result.lower()
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

    def __init__(self, tools: List[Any] = None):
        super().__init__(AgentRole.INVENTORY, tools)
        self.keywords = ["inventario", "stock", "producto", "caducar", "caducidad", "vencer", "comprar"]

    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning(f"Procesando consulta de inventario: {task.query[:50]}...")

        query_lower = task.query.lower()

        if any(kw in query_lower for kw in ["caducar", "caducidad", "vencer"]):
            self.add_reasoning("Detectada consulta de productos por caducar")
            dias = self._extract_days(task.query)
            result = self.call_tool("productos_por_caducar", dias)
        elif "stock bajo" in query_lower or "poco stock" in query_lower:
            self.add_reasoning("Detectada consulta de stock bajo")
            result = self.call_tool("verificar_stock_bajo")
        else:
            self.add_reasoning("Detectada consulta general de inventario")
            result = self.call_tool("consultar_productos_por_caducar", 7)

        task.result = result
        task.success = result is not None
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
    """Agente especializado en menús."""

    def __init__(self, tools: List[Any] = None):
        super().__init__(AgentRole.MENU, tools)
        self.keywords = ["menu", "menú", "planificar", "semanal", "dia", "desayuno", "almuerzo", "cena"]

    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning(f"Procesando consulta de menú: {task.query[:50]}...")

        query_lower = task.query.lower()

        if any(kw in query_lower for kw in ["semanal", "semana"]):
            self.add_reasoning("Detectada consulta de menú semanal")
            result = self.call_tool("consultar_menu_semanal", task.query)
        elif any(kw in query_lower for kw in ["desayuno", "almuerzo", "cena"]):
            self.add_reasoning("Detectada consulta de menú por comida")
            result = self.call_tool("consultar_menu_semanal", task.query)
        elif "sugerir" in query_lower or "sugiere" in query_lower:
            self.add_reasoning("Detectada solicitud de sugerencia de menú")
            result = self.call_tool("menu_anti_desperdicio")
        else:
            self.add_reasoning("Detectada consulta general de menú")
            result = self.call_tool("consultar_menu_semanal", task.query)

        task.result = result
        task.success = result is not None
        task.reasoning = self.reasoning.copy()
        return task


class WasteAgent(BaseAgent):
    """Agente especializado en mermas y desperdicio."""

    def __init__(self, tools: List[Any] = None):
        super().__init__(AgentRole.WASTE, tools)
        self.keywords = ["merma", "mermas", "desperdicio", "sobrante", "sobrantes", "perdida"]

    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning(f"Procesando consulta de mermas: {task.query[:50]}...")

        dias = self._extract_days(task.query)

        if "excel" in task.query.lower():
            self.add_reasoning("Detectada exportación a Excel")
            result = self.call_tool("enviar_reporte_mermas_a_excel", dias)
        elif "word" in task.query.lower():
            self.add_reasoning("Detectada exportación a Word")
            result = self.call_tool("enviar_reporte_mermas_a_word", dias)
        else:
            self.add_reasoning(f"Generando reporte de mermas ({dias} días)")
            result = self.call_tool("reporte_mermas", dias)

        task.result = result
        task.success = result is not None
        task.reasoning = self.reasoning.copy()
        return task

    def _extract_days(self, query: str) -> int:
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

    def __init__(self, tools: List[Any] = None):
        super().__init__(AgentRole.DOCUMENT, tools)
        self.keywords = ["documento", "documentos", "manual", "protocolo", "capacitacion", "bpm", "buenas practicas"]

    def can_handle(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)

    def execute(self, task: AgentTask) -> AgentTask:
        self.add_reasoning(f"Procesando búsqueda de documentos: {task.query[:50]}...")

        from data.rag_store import RAGStore
        rag = RAGStore()

        termino = task.query
        for prefix in ["busca documento", "buscar documento", "busca", "documento"]:
            idx = task.query.lower().find(prefix)
            if idx >= 0:
                termino = task.query[idx + len(prefix):].strip()
                break

        for word in ["el", "la", "los", "las", "un", "una", "de", "del"]:
            if termino.lower().startswith(word + " "):
                termino = termino[len(word) + 1:]

        self.add_reasoning(f"Buscando documentos con término: {termino}")
        docs = rag.buscar_documento(termino)

        if not docs:
            self.add_reasoning("No encontrado, intentando con palabras clave")
            for palabra in termino.split():
                if len(palabra) > 3:
                    docs = rag.buscar_documento(palabra)
                    if docs:
                        break

        if docs:
            lineas = [f"DOCUMENTOS ENCONTRADOS ({len(docs)}):"]
            for d in docs[:10]:
                lineas.append(f"  - {d.get('nombre')} (tipo: {d.get('tipo')})")
            task.result = "\n".join(lineas)
            task.success = True
        else:
            task.result = f"No se encontraron documentos con: {termino}"
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
            return result.result
        else:
            self.add_reasoning(f"Agente {task.role.value} no pudo completar la tarea")
            return result.result or f"No se pudo procesar la consulta"

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
                    return result.result
                else:
                    self.add_reasoning(f"Agente {task.role.value} falló, intentando siguiente")

        return "No se pudo procesar la consulta con ningún agente"

    def add_reasoning(self, reasoning: str):
        self.reasoning.append(reasoning)
        logging.info(f"[Executor] {reasoning}")


class MultiAgentSystem:
    """Sistema multiagente principal para ChefChat Pro."""

    def __init__(self, tools: List[Any] = None):
        self.tools = tools or []

        self.recipe_agent = RecipeAgent(self.tools)
        self.inventory_agent = InventoryAgent(self.tools)
        self.menu_agent = MenuAgent(self.tools)
        self.waste_agent = WasteAgent(self.tools)
        self.document_agent = DocumentAgent(self.tools)

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
