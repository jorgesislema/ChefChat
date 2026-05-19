"""
Módulo de Optimización de Prompts con DSPy para ChefChat Pro

Optimiza los system prompts y componentes de retrieval
de forma programática usando DSPy.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class OptimizedPrompt:
    """Prompt optimizado con metadata."""
    original: str
    optimized: str
    score: float
    examples_used: int
    optimization_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DSPyExample:
    """Ejemplo para optimización DSPy."""
    input_text: str
    expected_output: str
    context: Optional[str] = None


class PromptOptimizer:
    """Optimiza prompts usando técnicas de DSPy."""

    def __init__(self):
        self.examples: List[DSPyExample] = []
        self.optimized_prompts: Dict[str, OptimizedPrompt] = {}

    def add_example(self, input_text: str, expected_output: str, context: str = None):
        """Agrega un ejemplo para optimización."""
        self.examples.append(DSPyExample(
            input_text=input_text,
            expected_output=expected_output,
            context=context
        ))

    def load_examples_from_file(self, filepath: str):
        """Carga ejemplos desde un archivo JSON."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for ex in data:
                self.add_example(
                    input_text=ex['input'],
                    expected_output=ex['output'],
                    context=ex.get('context')
                )
            logging.info(f"DSPy: Loaded {len(data)} examples from {filepath}")
        except Exception as e:
            logging.error(f"DSPy: Error loading examples: {e}")

    def optimize_prompt(self, base_prompt: str, task_type: str = "general") -> OptimizedPrompt:
        """Optimiza un prompt basándose en los ejemplos disponibles."""
        if not self.examples:
            return OptimizedPrompt(
                original=base_prompt,
                optimized=base_prompt,
                score=0.0,
                examples_used=0,
                optimization_type="none"
            )

        optimized = self._apply_optimization(base_prompt, task_type)
        score = self._evaluate_prompt(optimized)

        result = OptimizedPrompt(
            original=base_prompt,
            optimized=optimized,
            score=score,
            examples_used=len(self.examples),
            optimization_type="few_shot",
            metadata={"task_type": task_type}
        )

        self.optimized_prompts[task_type] = result
        logging.info(f"DSPy: Optimized prompt for {task_type}, score={score:.2f}")
        return result

    def _apply_optimization(self, base_prompt: str, task_type: str) -> str:
        """Aplica optimización al prompt."""
        relevant_examples = self._select_examples(task_type, max_examples=3)

        if not relevant_examples:
            return base_prompt

        examples_section = "\n\nEJEMPLOS DE REFERENCIA:\n"
        for i, ex in enumerate(relevant_examples, 1):
            examples_section += f"\nEjemplo {i}:"
            examples_section += f"\n  Pregunta: {ex.input_text}"
            examples_section += f"\n  Respuesta esperada: {ex.expected_output}"
            if ex.context:
                examples_section += f"\n  Contexto: {ex.context}"
            examples_section += "\n"

        optimized = base_prompt + examples_section
        return optimized

    def _select_examples(self, task_type: str, max_examples: int = 3) -> List[DSPyExample]:
        """Selecciona los ejemplos más relevantes para la tarea."""
        if len(self.examples) <= max_examples:
            return self.examples

        scored = []
        for ex in self.examples:
            score = 0.0
            if task_type.lower() in ex.input_text.lower():
                score += 1.0
            if ex.context and task_type.lower() in ex.context.lower():
                score += 0.5
            scored.append((score, ex))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:max_examples]]

    def _evaluate_prompt(self, prompt: str) -> float:
        """Evalúa la calidad del prompt (heurística)."""
        score = 0.5

        if len(prompt) > 100:
            score += 0.1
        if len(prompt) > 300:
            score += 0.1
        if "EJEMPLOS" in prompt:
            score += 0.2
        if any(word in prompt.lower() for word in ["responde", "responda", "contesta"]):
            score += 0.1

        return min(score, 1.0)

    def get_optimized_prompt(self, task_type: str) -> Optional[OptimizedPrompt]:
        """Obtiene el prompt optimizado para un tipo de tarea."""
        return self.optimized_prompts.get(task_type)


class RetrievalOptimizer:
    """Optimiza componentes de retrieval."""

    def __init__(self):
        self.query_expansions: Dict[str, List[str]] = {}
        self.relevance_feedback: List[Dict[str, Any]] = []

    def add_query_expansion(self, original_query: str, expanded_terms: List[str]):
        """Agrega expansión de consulta."""
        self.query_expansions[original_query.lower()] = expanded_terms

    def expand_query(self, query: str) -> str:
        """Expande una consulta con términos relevantes."""
        query_lower = query.lower()
        expansions = self.query_expansions.get(query_lower, [])

        if expansions:
            expanded = query + " " + " ".join(expansions)
            logging.info(f"DSPy: Expanded query: {query} -> {expanded}")
            return expanded

        auto_expansion = self._auto_expand(query)
        return query + " " + " ".join(auto_expansion) if auto_expansion else query

    def _auto_expand(self, query: str) -> List[str]:
        """Genera expansión automática de consulta."""
        expansions = []

        food_synonyms = {
            "pollo": ["ave", "pechuga", "muslo"],
            "res": ["carne", "bistec", "lomo"],
            "cerdo": ["chuleta", "costilla"],
            "pescado": ["filete", "salmón", "atún"],
            "arroz": ["grano", "cereal"],
            "pasta": ["fideo", "espagueti"],
            "sopa": ["caldo", "crema"],
            "ensalada": ["verdura", "vegetal"],
        }

        query_lower = query.lower()
        for key, synonyms in food_synonyms.items():
            if key in query_lower:
                expansions.extend(synonyms[:2])
                break

        return expansions

    def add_relevance_feedback(self, query: str, doc_id: str, relevant: bool):
        """Agrega feedback de relevancia."""
        self.relevance_feedback.append({
            "query": query,
            "doc_id": doc_id,
            "relevant": relevant
        })

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de feedback."""
        total = len(self.relevance_feedback)
        relevant = sum(1 for f in self.relevance_feedback if f["relevant"])
        return {
            "total": total,
            "relevant": relevant,
            "irrelevant": total - relevant,
            "precision": relevant / total if total > 0 else 0.0
        }


class DSPyManager:
    """Gestor principal de DSPy para ChefChat Pro."""

    def __init__(self):
        self.prompt_optimizer = PromptOptimizer()
        self.retrieval_optimizer = RetrievalOptimizer()
        self._load_default_examples()

    def _load_default_examples(self):
        """Carga ejemplos por defecto para el dominio de restaurantes."""
        examples = [
            DSPyExample(
                input_text="¿Cuál es la receta de arroz con pollo?",
                expected_output="Receta PLF-018: Arroz con Pollo a la Chorrera. Ingredientes: pollo, arroz, cebolla, ajo, pimentón, culantro, achiote. Tiempo: 45 min. Porciones: 4.",
                context="recetas"
            ),
            DSPyExample(
                input_text="¿Qué productos están por caducar?",
                expected_output="Productos próximos a caducar: Leche (2 días), Queso fresco (1 día), Espinacas (hoy). Se recomienda usar estos productos primero.",
                context="inventario"
            ),
            DSPyExample(
                input_text="¿Cuál es el menú del lunes?",
                expected_output="Menú del Lunes: Desayuno - Pancakes con frutas. Almuerzo - Arroz con pollo, ensalada. Cena - Sopa de verduras, filete de pescado.",
                context="menu"
            ),
            DSPyExample(
                input_text="¿Cuánta merma hubo esta semana?",
                expected_output="Merma de la semana: 5.2 kg total. Principales productos: espinacas (1.5 kg), tomates (1.2 kg), leche (1 litro). Costo estimado: $15.40.",
                context="mermas"
            ),
        ]

        for ex in examples:
            self.prompt_optimizer.add_example(ex.input_text, ex.expected_output, ex.context)

        self.retrieval_optimizer.add_query_expansion(
            "receta con pollo",
            ["ave", "pechuga", "pollo entero"]
        )
        self.retrieval_optimizer.add_query_expansion(
            "productos por caducar",
            ["vencimiento", "fecha limite", "caducidad"]
        )

    def optimize_system_prompt(self, base_prompt: str, task_type: str = "general") -> str:
        """Optimiza el system prompt para un tipo de tarea."""
        result = self.prompt_optimizer.optimize_prompt(base_prompt, task_type)
        return result.optimized

    def expand_search_query(self, query: str) -> str:
        """Expande una consulta de búsqueda."""
        return self.retrieval_optimizer.expand_query(query)

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema DSPy."""
        return {
            "examples_loaded": len(self.prompt_optimizer.examples),
            "optimized_prompts": len(self.prompt_optimizer.optimized_prompts),
            "query_expansions": len(self.retrieval_optimizer.query_expansions),
            "feedback_stats": self.retrieval_optimizer.get_feedback_stats()
        }
