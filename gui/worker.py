import threading
import signal
from typing import Optional, Callable, Dict, Any, List
from PyQt6.QtCore import QThread, pyqtSignal, pyqtBoundValue, QObject
from core.models import AccionOffice
from agents.orchestrator import Orchestrator
from core.security import SecurityValidator


class TimeoutError(Exception):
    """Excepción para timeout de operaciones."""
    pass


def timeout_handler(signum, frame):
    """Manejador de señal para timeout."""
    raise TimeoutError("La operación tardó demasiado tiempo")


class Worker(QThread):
    chunk_recibido: pyqtBoundValue = pyqtSignal(str)
    requiere_aprobacion: pyqtBoundValue = pyqtSignal(AccionOffice)
    accion_completada: pyqtBoundValue = pyqtSignal(str)
    error_occurred: pyqtBoundValue = pyqtSignal(str)
    respuesta_completada: pyqtBoundValue = pyqtSignal(str)

    def __init__(
        self,
        orchestrator: Orchestrator,
        message: str,
        historial: Optional[List[Dict[str, str]]] = None,
        contexto_rag: Optional[str] = None,
        timeout_segundos: int = 60,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.orchestrator: Orchestrator = orchestrator
        self.message: str = message
        self.historial: List[Dict[str, str]] = historial or []
        self.contexto_rag: Optional[str] = contexto_rag
        self.timeout_segundos: int = timeout_segundos
        self.pause_condition: threading.Event = threading.Event()
        self.pause_condition.set()
        self.accion_pendiente: Optional[AccionOffice] = None
        self.pending_action_data: Optional[Dict[str, Any]] = None
        self.running: bool = True
        self._is_waiting: bool = False

    def run(self) -> None:
        try:
            import time
            start_time = time.time()
            
            historial_completo = self.historial + [{"rol": "user", "contenido": self.message}]
            
            # Ejecutar la llamada al LLM
            respuesta = self.orchestrator.generar_respuesta(
                historial=historial_completo,
                contexto_rag=self.contexto_rag
            )
            
            # Verificar si tomó demasiado tiempo
            elapsed = time.time() - start_time
            if elapsed > self.timeout_segundos:
                raise TimeoutError(
                    f"Timeout: La operación excedió {self.timeout_segundos}s. "
                    f"Intenta con un modelo más rápido o verifica tu conexión."
                )
            
            self.chunk_recibido.emit(respuesta)
            self.respuesta_completada.emit(respuesta)
                
        except TimeoutError as e:
            error_msg = f"⏱️ {str(e)}"
            self.error_occurred.emit(error_msg)
        except Exception as e:
            error_str = str(e)
            
            # Manejar errores específicos de proveedores
            if "langchain-google-genai" in error_str:
                error_msg = (
                    "❌ Error: Gemini requiere librería adicional.\n\n"
                    "✅ Soluciones:\n"
                    "1. pip install langchain-google-genai\n"
                    "2. O cambia a DeepSeek en Configuración → API Keys"
                )
            elif "langchain-anthropic" in error_str:
                error_msg = (
                    "❌ Error: Claude requiere librería adicional.\n\n"
                    "✅ Solución: pip install langchain-anthropic"
                )
            elif "connection" in error_str.lower() or "timeout" in error_str.lower() or "connect" in error_str.lower():
                error_msg = (
                    "🌐 Error de conexión.\n\n"
                    "Posibles causas:\n"
                    "• Sin conexión a internet\n"
                    "• API del proveedor caída\n"
                    "• Firewall bloqueando la conexión\n\n"
                    "💡 Intenta de nuevo o cambia de proveedor."
                )
            elif "API key" in error_str or "authentication" in error_str.lower() or "auth" in error_str.lower():
                error_msg = (
                    "🔑 Error de autenticación.\n\n"
                    "💡 Verifica tu API Key en:\n"
                    "Configuración → API Keys"
                )
            elif "deepseek" in error_str.lower():
                error_msg = (
                    "⚠️ Error con DeepSeek.\n\n"
                    "Posibles causas:\n"
                    "• Servidor sobrecargado (común)\n"
                    "• Timeout por respuesta larga\n"
                    "• Problemas temporales del servicio\n\n"
                    "💡 Intenta:\n"
                    "1. Esperar 30 segundos y重试\n"
                    "2. Usar OpenRouter como alternativa\n"
                    "3. Reducir longitud de la consulta"
                )
            else:
                error_msg = f"❌ Error: {error_str}"
            
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