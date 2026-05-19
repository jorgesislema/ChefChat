"""
Módulo de Evaluación para ChefChat Pro

Este módulo proporciona herramientas de evaluación sin modificar el programa principal:
- Golden Tests y Regression Tests
- Evaluación RAG (RAGAS, TruLens compatible)
- Evaluación de Agentes (Tool Match, Argument Match)
- DSPy Optimization Toolbox
- OpenTelemetry/Phoenix Integration
- Seguridad (Inyección de código, Filtración de datos)
"""

from .rag_evaluator import RAGEvaluator
from .agent_evaluator import AgentEvaluator
from .golden_tests import GoldenTestRunner
from .security_scanner import SecurityScanner
from .telemetry_exporter import TelemetryExporter

__all__ = [
    "RAGEvaluator",
    "AgentEvaluator", 
    "GoldenTestRunner",
    "SecurityScanner",
    "TelemetryExporter",
]
