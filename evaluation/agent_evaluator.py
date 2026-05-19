"""
Agent Evaluation Module

Evaluación de agentes y herramientas:
- Tool Match (¿seleccionó la herramienta correcta?)
- Argument Match (¿los argumentos son correctos?)
- Success Rate (tasa de éxito)
- Latency (tiempo de respuesta)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class ToolCallRecord:
    """Registro de llamada a herramienta."""
    tool_name: str
    arguments: Dict[str, Any]
    expected_tool: Optional[str] = None
    expected_arguments: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentEvaluationResult:
    """Resultado de evaluación de agente."""
    tool_match_accuracy: float  # 0-1, % de veces que seleccionó herramienta correcta
    argument_match_accuracy: float  # 0-1, % de argumentos correctos
    success_rate: float  # 0-1, % de llamadas exitosas
    avg_latency_ms: float  # Latencia promedio en ms
    total_calls: int
    overall_score: float


class AgentEvaluator:
    """Evaluador de agentes y herramientas."""
    
    def __init__(self):
        self.tool_calls: List[ToolCallRecord] = []
        
    def record_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        expected_tool: Optional[str] = None,
        expected_arguments: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        latency_ms: float = 0.0,
    ) -> None:
        """
        Registra una llamada a herramienta para evaluación.
        
        Args:
            tool_name: Nombre de la herramienta llamada
            arguments: Argumentos pasados a la herramienta
            expected_tool: Herramienta esperada (para evaluación supervisada)
            expected_arguments: Argumentos esperados (para evaluación supervisada)
            success: Si la llamada fue exitosa
            error_message: Mensaje de error si falló
            latency_ms: Latencia en milisegundos
        """
        record = ToolCallRecord(
            tool_name=tool_name,
            arguments=arguments,
            expected_tool=expected_tool,
            expected_arguments=expected_arguments,
            success=success,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        self.tool_calls.append(record)
    
    def evaluate(self) -> AgentEvaluationResult:
        """
        Evalúa el desempeño del agente.
        
        Returns:
            AgentEvaluationResult con métricas de desempeño
        """
        if not self.tool_calls:
            return AgentEvaluationResult(
                tool_match_accuracy=0.0,
                argument_match_accuracy=0.0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                total_calls=0,
                overall_score=0.0,
            )
        
        # Tool Match Accuracy
        tool_match_scores = []
        for call in self.tool_calls:
            if call.expected_tool is not None:
                score = 1.0 if call.tool_name == call.expected_tool else 0.0
                tool_match_scores.append(score)
        
        tool_match_accuracy = (
            sum(tool_match_scores) / len(tool_match_scores)
            if tool_match_scores else 0.0
        )
        
        # Argument Match Accuracy
        argument_match_scores = []
        for call in self.tool_calls:
            if call.expected_arguments is not None:
                score = self._calculate_argument_similarity(
                    call.arguments, call.expected_arguments
                )
                argument_match_scores.append(score)
        
        argument_match_accuracy = (
            sum(argument_match_scores) / len(argument_match_scores)
            if argument_match_scores else 0.0
        )
        
        # Success Rate
        successful_calls = sum(1 for c in self.tool_calls if c.success)
        success_rate = successful_calls / len(self.tool_calls)
        
        # Average Latency
        avg_latency_ms = sum(c.latency_ms for c in self.tool_calls) / len(self.tool_calls)
        
        # Overall Score (weighted average)
        # Latency score: 100ms = 1.0, 1000ms = 0.5, 2000ms = 0.0
        latency_score = max(0.0, min(1.0, 1.0 - (avg_latency_ms / 2000)))
        
        overall_score = (
            tool_match_accuracy * 0.30 +
            argument_match_accuracy * 0.25 +
            success_rate * 0.30 +
            latency_score * 0.15
        )
        
        return AgentEvaluationResult(
            tool_match_accuracy=tool_match_accuracy,
            argument_match_accuracy=argument_match_accuracy,
            success_rate=success_rate,
            avg_latency_ms=avg_latency_ms,
            total_calls=len(self.tool_calls),
            overall_score=overall_score,
        )
    
    def _calculate_argument_similarity(
        self,
        actual: Dict[str, Any],
        expected: Dict[str, Any],
    ) -> float:
        """
        Calcula similitud entre argumentos reales y esperados.
        
        Usa matching exacto para valores simples y overlap para strings.
        """
        if not expected:
            return 1.0
        
        if not actual:
            return 0.0
        
        matching_args = 0
        total_args = len(expected)
        
        for key, expected_value in expected.items():
            if key not in actual:
                continue
            
            actual_value = actual[key]
            
            # Matching exacto para tipos simples
            if isinstance(expected_value, (int, float, bool)):
                if actual_value == expected_value:
                    matching_args += 1
            elif isinstance(expected_value, str):
                # String matching con tolerancia
                if self._string_similarity(actual_value, expected_value) > 0.7:
                    matching_args += 1
            else:
                # Para otros tipos, intentar comparación JSON
                try:
                    if json.dumps(actual_value, sort_keys=True) == json.dumps(expected_value, sort_keys=True):
                        matching_args += 1
                except (TypeError, ValueError):
                    pass
        
        return matching_args / total_args if total_args > 0 else 0.0
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calcula similitud entre dos strings (Jaccard similarity)."""
        set1 = set(s1.lower().split())
        set2 = set(s2.lower().split())
        
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def get_tool_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene estadísticas de uso por herramienta."""
        stats: Dict[str, Dict[str, Any]] = {}
        
        for call in self.tool_calls:
            if call.tool_name not in stats:
                stats[call.tool_name] = {
                    "total_calls": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_latency_ms": 0.0,
                    "total_latency_ms": 0.0,
                }
            
            stats[call.tool_name]["total_calls"] += 1
            if call.success:
                stats[call.tool_name]["successful"] += 1
            else:
                stats[call.tool_name]["failed"] += 1
            stats[call.tool_name]["total_latency_ms"] += call.latency_ms
        
        # Calcular promedios
        for tool_name, tool_stats in stats.items():
            tool_stats["avg_latency_ms"] = (
                tool_stats["total_latency_ms"] / tool_stats["total_calls"]
                if tool_stats["total_calls"] > 0 else 0.0
            )
            del tool_stats["total_latency_ms"]
        
        return stats
    
    def get_error_analysis(self) -> List[Dict[str, Any]]:
        """Obtiene análisis de errores."""
        errors = []
        
        for call in self.tool_calls:
            if not call.success and call.error_message:
                errors.append({
                    "tool_name": call.tool_name,
                    "arguments": call.arguments,
                    "error_message": call.error_message,
                    "timestamp": call.timestamp.isoformat(),
                })
        
        return errors
    
    def export_for_phoenix(self) -> List[Dict[str, Any]]:
        """
        Exporta datos en formato compatible con Arize Phoenix.
        
        Formato para tracing y evaluación en Phoenix UI.
        """
        traces = []
        
        for call in self.tool_calls:
            trace = {
                "trace_id": f"{call.tool_name}_{call.timestamp.timestamp()}",
                "span_id": f"span_{call.timestamp.timestamp()}",
                "parent_id": None,
                "operation": "tool_call",
                "name": call.tool_name,
                "start_time": call.timestamp.isoformat(),
                "end_time": call.timestamp.isoformat(),
                "latency_ms": call.latency_ms,
                "status": "SUCCESS" if call.success else "ERROR",
                "attributes": {
                    "tool_name": call.tool_name,
                    "arguments": json.dumps(call.arguments),
                    "expected_tool": call.expected_tool,
                    "expected_arguments": json.dumps(call.expected_arguments) if call.expected_arguments else None,
                    "error_message": call.error_message,
                },
            }
            traces.append(trace)
        
        return traces
