"""
Telemetry Exporter Module

Exporta datos de telemetría para integración con:
- Arize Phoenix
- OpenTelemetry
- LangSmith
- Otros sistemas de observabilidad
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os


@dataclass
class TelemetrySpan:
    """Span de telemetría para tracing."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation: str  # tool_call, llm_call, rag_retrieval, etc.
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "OK"  # OK, ERROR
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class TelemetryExporter:
    """Exportador de telemetría para sistemas de observabilidad."""
    
    def __init__(self, export_dir: str = "telemetry_exports"):
        self.export_dir = export_dir
        self.spans: List[TelemetrySpan] = []
        os.makedirs(export_dir, exist_ok=True)
    
    def record_span(
        self,
        operation: str,
        name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        latency_ms: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str = "",
        attributes: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> TelemetrySpan:
        """
        Registra un span de telemetría.
        
        Args:
            operation: Tipo de operación (tool_call, llm_call, etc.)
            name: Nombre descriptivo
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            latency_ms: Latencia en milisegundos
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            model: Modelo utilizado
            attributes: Atributos adicionales
            error_message: Mensaje de error si ocurrió
            parent_span_id: ID del span padre (para tracing jerárquico)
            
        Returns:
            TelemetrySpan creado
        """
        import uuid
        
        span = TelemetrySpan(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4())[:8],
            parent_span_id=parent_span_id,
            operation=operation,
            name=name,
            start_time=start_time,
            end_time=end_time or datetime.now(),
            status="ERROR" if error_message else "OK",
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            attributes=attributes or {},
            error_message=error_message,
        )
        
        self.spans.append(span)
        return span
    
    def export_for_phoenix(self, output_file: Optional[str] = None) -> str:
        """
        Exporta datos en formato compatible con Arize Phoenix.
        
        Phoenix espera formato JSONL con spans de trace.
        
        Args:
            output_file: Archivo de salida (opcional)
            
        Returns:
            Ruta del archivo exportado
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(
                self.export_dir,
                f"phoenix_export_{timestamp}.jsonl",
            )
        
        with open(output_file, "w", encoding="utf-8") as f:
            for span in self.spans:
                record = {
                    "trace_id": span.trace_id,
                    "span_id": span.span_id,
                    "parent_id": span.parent_span_id,
                    "operation": span.operation,
                    "name": span.name,
                    "start_time": span.start_time.isoformat(),
                    "end_time": span.end_time.isoformat() if span.end_time else None,
                    "latency_ms": span.latency_ms,
                    "status": span.status,
                    "attributes": {
                        **span.attributes,
                        "input_tokens": span.input_tokens,
                        "output_tokens": span.output_tokens,
                        "model": span.model,
                        "error_message": span.error_message,
                    },
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        return output_file
    
    def export_for_opentelemetry(self, output_file: Optional[str] = None) -> str:
        """
        Exporta datos en formato compatible con OpenTelemetry.
        
        Formato JSON compatible con OTLP (OpenTelemetry Protocol).
        
        Args:
            output_file: Archivo de salida (opcional)
            
        Returns:
            Ruta del archivo exportado
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(
                self.export_dir,
                f"otel_export_{timestamp}.json",
            )
        
        # Formato simplificado de OTLP
        resource_spans = []
        
        for span in self.spans:
            otel_span = {
                "traceId": span.trace_id,
                "spanId": span.span_id,
                "parentSpanId": span.parent_span_id or "",
                "name": span.name,
                "kind": "SPAN_KIND_INTERNAL",
                "startTimeUnixNano": int(span.start_time.timestamp() * 1_000_000_000),
                "endTimeUnixNano": int(
                    span.end_time.timestamp() * 1_000_000_000
                ) if span.end_time else 0,
                "attributes": [
                    {"key": "operation", "value": {"stringValue": span.operation}},
                    {"key": "latency.ms", "value": {"doubleValue": span.latency_ms}},
                    {"key": "tokens.input", "value": {"intValue": str(span.input_tokens)}},
                    {"key": "tokens.output", "value": {"intValue": str(span.output_tokens)}},
                    {"key": "model", "value": {"stringValue": span.model}},
                ],
                "status": {
                    "code": "STATUS_CODE_ERROR" if span.error_message else "STATUS_CODE_OK",
                    "message": span.error_message or "",
                },
            }
            
            # Agregar atributos custom
            for key, value in span.attributes.items():
                if isinstance(value, str):
                    attr = {"key": key, "value": {"stringValue": value}}
                elif isinstance(value, (int, float)):
                    attr = {"key": key, "value": {"doubleValue": value}}
                elif isinstance(value, bool):
                    attr = {"key": key, "value": {"boolValue": value}}
                else:
                    attr = {"key": key, "value": {"stringValue": json.dumps(value)}}
                otel_span["attributes"].append(attr)
            
            resource_spans.append(otel_span)
        
        export_data = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "ChefChat-Pro"}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "chefchat-evaluation"},
                            "spans": resource_spans,
                        }
                    ],
                }
            ]
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def export_for_langsmith(self, output_file: Optional[str] = None) -> str:
        """
        Exporta datos en formato compatible con LangSmith.
        
        Args:
            output_file: Archivo de salida (opcional)
            
        Returns:
            Ruta del archivo exportado
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(
                self.export_dir,
                f"langsmith_export_{timestamp}.jsonl",
            )
        
        with open(output_file, "w", encoding="utf-8") as f:
            for span in self.spans:
                record = {
                    "id": span.span_id,
                    "trace_id": span.trace_id,
                    "parent_run_id": span.parent_span_id,
                    "name": span.name,
                    "run_type": span.operation,
                    "start_time": span.start_time.isoformat(),
                    "end_time": span.end_time.isoformat() if span.end_time else None,
                    "status": span.status,
                    "inputs": span.attributes.get("input", {}),
                    "outputs": span.attributes.get("output", {}),
                    "events": [
                        {
                            "name": "start",
                            "time": span.start_time.isoformat(),
                        },
                        {
                            "name": "end",
                            "time": span.end_time.isoformat() if span.end_time else datetime.now().isoformat(),
                        },
                    ],
                    "tags": [span.operation, span.model] if span.model else [span.operation],
                    "extra": {
                        "metadata": {
                            "tokens": {
                                "input": span.input_tokens,
                                "output": span.output_tokens,
                            },
                            "latency_ms": span.latency_ms,
                        }
                    },
                }
                
                if span.error_message:
                    record["error"] = span.error_message
                
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        return output_file
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Obtiene estadísticas de latencia."""
        if not self.spans:
            return {
                "total_spans": 0,
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
            }
        
        latencies = sorted([s.latency_ms for s in self.spans])
        n = len(latencies)
        
        def percentile(p: float) -> float:
            if n == 0:
                return 0.0
            k = (n - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < n else f
            return latencies[f] + (k - f) * (latencies[c] - latencies[f]) if f != c else latencies[f]
        
        return {
            "total_spans": n,
            "avg_latency_ms": sum(latencies) / n,
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "p50_latency_ms": percentile(50),
            "p95_latency_ms": percentile(95),
            "p99_latency_ms": percentile(99),
        }
    
    def get_token_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de uso de tokens."""
        if not self.spans:
            return {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "by_model": {},
            }
        
        by_model: Dict[str, Dict[str, int]] = {}
        
        for span in self.spans:
            if span.model not in by_model:
                by_model[span.model] = {"input": 0, "output": 0}
            
            by_model[span.model]["input"] += span.input_tokens
            by_model[span.model]["output"] += span.output_tokens
        
        total_input = sum(m["input"] for m in by_model.values())
        total_output = sum(m["output"] for m in by_model.values())
        
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "by_model": by_model,
        }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de errores."""
        if not self.spans:
            return {
                "total_errors": 0,
                "error_rate": 0.0,
                "errors_by_operation": {},
            }
        
        errors = [s for s in self.spans if s.error_message]
        errors_by_op: Dict[str, int] = {}
        
        for error in errors:
            errors_by_op[error.operation] = errors_by_op.get(error.operation, 0) + 1
        
        return {
            "total_errors": len(errors),
            "error_rate": len(errors) / len(self.spans),
            "errors_by_operation": errors_by_op,
            "error_details": [
                {
                    "span_id": s.span_id,
                    "operation": s.operation,
                    "name": s.name,
                    "error_message": s.error_message,
                    "timestamp": s.start_time.isoformat(),
                }
                for s in errors
            ],
        }
    
    def clear(self) -> None:
        """Limpia todos los spans registrados."""
        self.spans = []
