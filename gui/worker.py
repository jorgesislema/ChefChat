import threading
from typing import Optional, Callable, Dict, Any, List
from PyQt6.QtCore import QThread, pyqtSignal, pyqtBoundSignal
from core.models import AccionOffice
from agents.orchestrator import Orchestrator
from core.security import SecurityValidator


class Worker(QThread):
    chunk_recibido: pyqtBoundSignal = pyqtSignal(str)
    requiere_aprobacion: pyqtBoundSignal = pyqtSignal(AccionOffice)
    accion_completada: pyqtBoundSignal = pyqtSignal(str)
    error_occurred: pyqtBoundSignal = pyqtSignal(str)
    respuesta_completada: pyqtBoundSignal = pyqtSignal(str)

    def __init__(
        self,
        orchestrator: Orchestrator,
        message: str,
        historial: Optional[List[Dict[str, str]]] = None,
        contexto_rag: Optional[str] = None,
        parent: Optional["QObject"] = None,
    ) -> None:
        super().__init__(parent)
        self.orchestrator: Orchestrator = orchestrator
        self.message: str = message
        self.historial: List[Dict[str, str]] = historial or []
        self.contexto_rag: Optional[str] = contexto_rag
        self.pause_condition: threading.Event = threading.Event()
        self.pause_condition.set()
        self.accion_pendiente: Optional[AccionOffice] = None
        self.pending_action_data: Optional[Dict[str, Any]] = None
        self.running: bool = True
        self._is_waiting: bool = False

    def run(self) -> None:
        try:
            historial_completo = self.historial + [{"rol": "user", "contenido": self.message}]
            respuesta = self.orchestrator.generar_respuesta(
                historial=historial_completo,
                contexto_rag=self.contexto_rag
            )
            self.chunk_recibido.emit(respuesta)
            self.respuesta_completada.emit(respuesta)
        except Exception as e:
            error_msg = f"Error en LLM: {str(e)}"
            self.error_occurred.emit(error_msg)

    def solicitud_accion(self, accion: AccionOffice) -> None:
        self.accion_pendiente = accion
        self._is_waiting = True
        self.pause_condition.clear()
        self.requiere_aprobacion.emit(accion)
        self.pause_condition.wait()
        self._is_waiting = False
        if self.accion_pendiente is None:
            return
        accion = self.accion_pendiente
        self.accion_pendiente = None
        self.pending_action_data = None
        try:
            from agents.mcp_client import MCPClient
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(accion)
            log_msg = SecurityValidator.sanitize_log_message(
                f"Acción MCP completada: {resultado}"
            )
            self.accion_completada.emit(log_msg)
        except Exception as e:
            error_msg = f"Error en acción MCP: {str(e)}"
            self.error_occurred.emit(error_msg)
        finally:
            self.pause_condition.set()

    def aprobar_accion(self, accion_data: Optional[Dict[str, Any]] = None) -> None:
        if accion_data:
            self.pending_action_data = accion_data
        self.accion_pendiente = None
        self.pause_condition.set()

    def rechazar_accion(self) -> None:
        self.accion_pendiente = None
        self.pending_action_data = None
        self.pause_condition.set()
        self.accion_completada.emit("Acción rechazada por el usuario")

    def stop(self) -> None:
        self.running = False
        if not self.pause_condition.is_set():
            self.pause_condition.set()
        self.quit()
        self.wait(3000)

    def is_waiting_for_approval(self) -> bool:
        return self._is_waiting and not self.pause_condition.is_set()