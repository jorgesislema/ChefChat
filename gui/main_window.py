"""
Interfaz Gráfica para ChefChat Pro - PyQt6

Implementa la GUI con pantalla dividida (QSplitter), soporte para temas
Claro/Oscuro, y barra HITL para aprobación de acciones críticas.
"""

from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QTextEdit,
    QPushButton,
    QLabel,
    QLineEdit,
    QDialog,
    QMessageBox,
    QFileDialog,
    QStackedWidget,
    QComboBox,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QThread
from PyQt6.QtGui import QColor, QPalette, QTextCursor, QFont, QIcon

from gui.worker import Worker
from agents.orchestrator import Orchestrator
from agents.tools import crear_herramientas_operativas
from core.config import AIProvider, ConfigManager
from core.security import SecurityValidator
from core.rag_classifier import cargar_documentos_rag, generar_resumen_carga
from gui.telemetry_view import TelemetryDashboard
from data.db_manager import DatabaseManager
from data.rag_store import RAGStore


DARK_THEME = {
    "bg_primary": "#0f172a",
    "bg_secondary": "#1e293b",
    "bg_tertiary": "#334155",
    "text_primary": "#f5f5f5",
    "text_secondary": "#94a3b8",
    "accent": "#deff9a",
    "accent_hover": "#b8f29a",
    "border": "#475569",
    "success": "#22c55e",
    "error": "#ef4444",
    "warning": "#fbbf24",
    "info": "#3b82f6",
}

LIGHT_THEME = {
    "bg_primary": "#ffffff",
    "bg_secondary": "#f8fafc",
    "bg_tertiary": "#e2e8f0",
    "text_primary": "#1e293b",
    "text_secondary": "#64748b",
    "accent": "#16a34a",
    "accent_hover": "#15803d",
    "border": "#cbd5e1",
    "success": "#22c55e",
    "error": "#ef4444",
    "warning": "#f59e0b",
    "info": "#2563eb",
}


def generate_stylesheet(theme: Dict[str, str]) -> str:
    """
    Genera el stylesheet completo para un tema dado.
    
    Args:
        theme: Diccionario con colores del tema.
        
    Returns:
        str: Stylesheet en formato QSS.
    """
    return f"""
    QWidget {{
        background-color: {theme['bg_primary']};
        color: {theme['text_primary']};
        font-family: 'Segoe UI', sans-serif;
        font-size: 10pt;
    }}

    QMainWindow {{
        background-color: {theme['bg_primary']};
    }}

    QSplitter::handle {{
        background-color: {theme['border']};
        width: 2px;
    }}

    QSplitter::handle:hover {{
        background-color: {theme['bg_tertiary']};
    }}

    QTextEdit, QTextEdit#chat_area {{
        background-color: {theme['bg_secondary']};
        border: 1px solid {theme['border']};
        border-radius: 8px;
        padding: 12px;
        color: {theme['text_primary']};
    }}

    QTextEdit#chat_area {{
        padding: 16px;
    }}

    QPushButton {{
        background-color: {theme['bg_secondary']};
        border: 1px solid {theme['border']};
        border-radius: 6px;
        padding: 8px 16px;
        color: {theme['text_primary']};
        min-width: 80px;
    }}

    QPushButton:hover {{
        background-color: {theme['bg_tertiary']};
    }}

    QPushButton:pressed {{
        background-color: {theme['border']};
    }}

    QPushButton#btn_send {{
        background-color: {theme['accent']};
        color: {theme['bg_primary']};
        font-weight: bold;
        border: none;
    }}

    QPushButton#btn_send:hover {{
        background-color: {theme['accent_hover']};
    }}

    QPushButton#btn_approve {{
        background-color: {theme['success']};
        color: white;
        font-weight: bold;
        border: none;
        min-width: 120px;
    }}

    QPushButton#btn_reject {{
        background-color: {theme['error']};
        color: white;
        font-weight: bold;
        border: none;
        min-width: 120px;
    }}

    QPushButton#btn_rag {{
        background-color: {theme['info']};
        color: white;
        border: none;
        font-size: 14pt;
        max-width: 40px;
    }}

    QPushButton#btn_theme {{
        background-color: {theme['bg_secondary']};
        border: 1px solid {theme['border']};
        border-radius: 6px;
        padding: 8px;
        max-width: 50px;
    }}

    QLineEdit, QComboBox {{
        background-color: {theme['bg_secondary']};
        border: 1px solid {theme['border']};
        border-radius: 6px;
        padding: 8px;
        color: {theme['text_primary']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {theme['text_primary']};
        margin-right: 8px;
    }}

    QLabel {{
        color: {theme['text_primary']};
        padding: 4px;
    }}

    #right_panel {{
        background-color: {theme['bg_primary']};
        border-left: 1px solid {theme['border']};
    }}

    #hitl_bar {{
        background-color: {theme['bg_secondary']};
        border-top: 2px solid {theme['accent']};
        padding: 12px;
        border-radius: 8px;
    }}

    #hitl_label {{
        color: {theme['warning']};
        font-weight: bold;
        font-size: 10pt;
    }}

    QDialog {{
        background-color: {theme['bg_primary']};
    }}

    QMessageBox {{
        background-color: {theme['bg_primary']};
    }}
    """


class ChatBubble:
    """Clase utilitaria para generar burbujas de chat HTML."""

    @staticmethod
    def user_bubble(text: str, theme: Dict[str, str]) -> str:
        return f'''
        <div style="text-align: right; margin: 8px 0;">
            <span style="display: inline-block; background-color: {theme['bg_tertiary']}; 
                         color: {theme['text_primary']}; padding: 10px 16px; 
                         border-radius: 16px 16px 4px 16px; max-width: 70%; 
                         word-wrap: break-word;">
                {text}
            </span>
        </div>
        '''

    @staticmethod
    def assistant_bubble(text: str, theme: Dict[str, str]) -> str:
        return f'''
        <div style="text-align: left; margin: 8px 0;">
            <span style="display: inline-block; background-color: {theme['bg_secondary']}; 
                         color: {theme['text_primary']}; padding: 10px 16px; 
                         border-radius: 16px 16px 16px 4px; max-width: 70%; 
                         word-wrap: break-word;">
                {text}
            </span>
        </div>
        '''

    @staticmethod
    def system_bubble(text: str, theme: Dict[str, str]) -> str:
        return f'''
        <div style="text-align: center; margin: 8px 0;">
            <span style="display: inline-block; background-color: {theme['bg_tertiary']}; 
                         color: {theme['text_secondary']}; padding: 8px 16px; 
                         border-radius: 16px; font-style: italic; font-size: 9pt;">
                {text}
            </span>
        </div>
        '''


class MainWindow(QMainWindow):
    """
    Ventana principal de ChefChat Pro.
    
    Implementa interfaz de pantalla dividida con chat a la izquierda (40%)
    y visor de datos/aprobación a la derecha (60%). Incluye toggle de tema
    Claro/Oscuro y barra HITL para aprobación de acciones.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChefChat Pro - Sistema Operativo para Restaurantes")
        self.setMinimumSize(1400, 900)
        
        self.db = DatabaseManager()
        self.rag_store = RAGStore(db_path="chefchat.db")
        self.theme_mode = "dark"
        self.current_theme = DARK_THEME
        
        self._current_session_id: str = "default_session"
        self.worker: Optional[Worker] = None
        self._rag_files: List[str] = []
        self._pending_action_data: Optional[Dict[str, Any]] = None
        self._selected_provider: Optional[AIProvider] = None
        self._selected_model: Optional[str] = None
        
        self._setup_ui()
        self._check_api_key_on_startup()

    def _check_api_key_on_startup(self) -> None:
        """Verifica si hay API Key configurada y muestra diálogo si no."""
        if not ConfigManager.has_any_api_key():
            QTimer.singleShot(500, self._show_keys_dialog)
        else:
            self._update_provider_selector()

    def _setup_ui(self) -> None:
        """Configura toda la interfaz de usuario."""
        self.setStyleSheet(generate_stylesheet(self.current_theme))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        self._setup_left_panel(splitter)
        self._setup_right_panel(splitter)
        
        splitter.setSizes([560, 840])
        splitter.setStretchFactor(0, 40)
        splitter.setStretchFactor(1, 60)

    def _setup_left_panel(self, splitter: QSplitter) -> None:
        """Configura el panel izquierdo (Chat - 40%)."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 16, 8, 16)
        left_layout.setSpacing(12)
        
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        self.btn_theme = QPushButton("🌙")
        self.btn_theme.setObjectName("btn_theme")
        self.btn_theme.setToolTip("Cambiar tema Claro/Oscuro")
        self.btn_theme.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.btn_theme)
        
        self.provider_selector = QComboBox()
        self.provider_selector.setObjectName("provider_selector")
        self.provider_selector.setMinimumWidth(200)
        self.provider_selector.currentIndexChanged.connect(self._on_provider_changed)
        header_layout.addWidget(self.provider_selector, stretch=3)
        
        self.model_selector = QComboBox()
        self.model_selector.setObjectName("model_selector")
        self.model_selector.setMinimumWidth(180)
        self.model_selector.currentIndexChanged.connect(self._on_model_changed)
        header_layout.addWidget(self.model_selector, stretch=2)
        
        self.btn_keys = QPushButton("⚙")
        self.btn_keys.setObjectName("btn_keys")
        self.btn_keys.setStyleSheet("max-width: 40px; font-size: 12pt;")
        self.btn_keys.setToolTip("Configuración de Bóveda")
        self.btn_keys.clicked.connect(self._show_keys_dialog)
        header_layout.addWidget(self.btn_keys, stretch=1)
        
        self.btn_telemetry = QPushButton("📊")
        self.btn_telemetry.setObjectName("btn_telemetry")
        self.btn_telemetry.setStyleSheet("max-width: 40px; font-size: 12pt;")
        self.btn_telemetry.setToolTip("Ver Telemetría")
        self.btn_telemetry.clicked.connect(self._toggle_telemetry)
        header_layout.addWidget(self.btn_telemetry, stretch=1)
        
        left_layout.addWidget(header)
        
        self.chat_area = QTextEdit()
        self.chat_area.setObjectName("chat_area")
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont("Segoe UI", 10))
        left_layout.addWidget(self.chat_area)
        
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)
        
        self.btn_rag = QPushButton("+")
        self.btn_rag.setObjectName("btn_rag")
        self.btn_rag.setToolTip("Ingesta RAG: Cargar documentos CSV/MD")
        self.btn_rag.clicked.connect(self._on_rag_ingest)
        input_layout.addWidget(self.btn_rag)
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        self.input_field.setPlaceholderText("Escribe tu mensaje aquí...")
        self.input_field.setFont(QFont("Segoe UI", 10))
        input_layout.addWidget(self.input_field, stretch=7)
        
        self.btn_send = QPushButton("Enviar")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.setToolTip("Enviar mensaje")
        self.btn_send.clicked.connect(self._on_send_message)
        input_layout.addWidget(self.btn_send, stretch=1)
        
        left_layout.addWidget(input_widget)
        splitter.addWidget(left_widget)
        self._left_widget = left_widget

    def _setup_right_panel(self, splitter: QSplitter) -> None:
        """Configura el panel derecho (Visor/Aprobación - 60%)."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 16, 16, 16)
        right_layout.setSpacing(12)
        right_widget.setObjectName("right_panel")
        
        self.right_title = QLabel("ChefChat Pro Dashboard")
        self.right_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_title.setStyleSheet(
            f"font-size: 14pt; font-weight: bold; color: {self.current_theme['accent']}; padding: 8px;"
        )
        right_layout.addWidget(self.right_title)
        
        self.stacked_widget = QStackedWidget()
        self.viewer_read = QTextEdit()
        self.viewer_read.setReadOnly(True)
        self.viewer_read.setStyleSheet(
            f"background-color: {self.current_theme['bg_primary']}; "
            f"border: 1px solid {self.current_theme['border']}; border-radius: 8px;"
        )
        self.viewer_office = QTextEdit()
        self.viewer_office.setReadOnly(True)
        self.viewer_office.setStyleSheet(
            f"background-color: {self.current_theme['bg_primary']}; "
            f"border: 1px solid {self.current_theme['border']}; border-radius: 8px;"
        )
        self.stacked_widget.addWidget(self.viewer_read)
        self.stacked_widget.addWidget(self.viewer_office)
        right_layout.addWidget(self.stacked_widget, stretch=9)
        
        self.hitl_bar = QWidget()
        self.hitl_bar.setObjectName("hitl_bar")
        self.hitl_bar.setVisible(False)
        hitl_layout = QHBoxLayout(self.hitl_bar)
        hitl_layout.setContentsMargins(8, 8, 8, 8)
        
        hitl_label = QLabel("⚠️ Aprobación requerida para acción")
        hitl_label.setObjectName("hitl_label")
        hitl_layout.addWidget(hitl_label, stretch=3)
        
        self.btn_approve = QPushButton("✔ Aprobar")
        self.btn_approve.setObjectName("btn_approve")
        self.btn_approve.setToolTip("Aprobar la acción propuesta")
        self.btn_approve.clicked.connect(self._on_approve_action)
        hitl_layout.addWidget(self.btn_approve, stretch=1)
        
        self.btn_reject = QPushButton("✖ Rechazar")
        self.btn_reject.setObjectName("btn_reject")
        self.btn_reject.setToolTip("Rechazar la acción propuesta")
        self.btn_reject.clicked.connect(self._on_reject_action)
        hitl_layout.addWidget(self.btn_reject, stretch=1)
        
        right_layout.addWidget(self.hitl_bar, stretch=1)
        splitter.addWidget(right_widget)
        self._right_panel = right_widget
        
        # Telemetry Dashboard (hidden by default)
        self.telemetry_dashboard: Optional[TelemetryDashboard] = None
        self._telemetry_visible = False

    def _toggle_theme(self) -> None:
        """Alterna entre tema Claro y Oscuro."""
        if self.theme_mode == "dark":
            self.theme_mode = "light"
            self.current_theme = LIGHT_THEME
            self.btn_theme.setText("☀️")
        else:
            self.theme_mode = "dark"
            self.current_theme = DARK_THEME
            self.btn_theme.setText("🌙")
        
        self.setStyleSheet(generate_stylesheet(self.current_theme))
        self._update_theme_dependent_elements()

    def _update_theme_dependent_elements(self) -> None:
        """Actualiza elementos que dependen del tema."""
        self.right_title.setStyleSheet(
            f"font-size: 14pt; font-weight: bold; color: {self.current_theme['accent']}; padding: 8px;"
        )
        self.viewer_read.setStyleSheet(
            f"background-color: {self.current_theme['bg_primary']}; "
            f"border: 1px solid {self.current_theme['border']}; border-radius: 8px;"
        )
        self.viewer_office.setStyleSheet(
            f"background-color: {self.current_theme['bg_primary']}; "
            f"border: 1px solid {self.current_theme['border']}; border-radius: 8px;"
        )

    def _update_provider_selector(self) -> None:
        """Actualiza el selector de proveedores de IA."""
        self.provider_selector.blockSignals(True)
        self.provider_selector.clear()
        for provider in ConfigManager.get_all_providers():
            display_name = ConfigManager.get_provider_display_name(provider)
            has_key = ConfigManager.get_api_key(provider) is not None
            if has_key:
                self.provider_selector.addItem(f"✅ {display_name}", provider)
            else:
                self.provider_selector.addItem(f"⚠️ {display_name}", provider)
        configured = ConfigManager.get_configured_provider()
        if configured:
            index = self.provider_selector.findData(configured)
            if index >= 0:
                self.provider_selector.setCurrentIndex(index)
        self.provider_selector.blockSignals(False)
        self._update_model_selector()

    def _on_provider_changed(self, index: int) -> None:
        if index < 0:
            return
        provider = self.provider_selector.currentData()
        if provider:
            self._selected_provider = provider
            self._update_model_selector()

    def _on_model_changed(self, index: int) -> None:
        if index < 0:
            return
        self._selected_model = self.model_selector.currentData()

    def _update_model_selector(self) -> None:
        self.model_selector.blockSignals(True)
        self.model_selector.clear()
        if self._selected_provider:
            models = ConfigManager.get_models_for_provider(self._selected_provider)
            for model in models:
                self.model_selector.addItem(model, model)
        self.model_selector.blockSignals(False)

    def _show_keys_dialog(self) -> None:
        dialog = APIKeyDialog(self, self._selected_provider)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_provider_selector()
            QMessageBox.information(self, "Guardado", "API Key guardada en el sistema seguro")

    def _toggle_telemetry(self) -> None:
        """Muestra/oculta el dashboard de telemetría."""
        if self._telemetry_visible:
            self.stacked_widget.setCurrentIndex(0)
            self._telemetry_visible = False
        else:
            if not self.telemetry_dashboard:
                self.telemetry_dashboard = TelemetryDashboard(self.db, self)
                self.stacked_widget.addWidget(self.telemetry_dashboard)
            self.stacked_widget.setCurrentIndex(2)
            self._telemetry_visible = True

    def _generar_resumen_guardado(self, resultados: Dict[str, Any]) -> str:
        """
        Genera mensaje de resumen después de guardar documentos.
        
        Args:
            resultados: Dict de rag_store.guardar_documentos().
            
        Returns:
            str: Mensaje formateado para el usuario.
        """
        lineas = [f"✅ Documentos guardados: {resultados['guardados']}/{resultados['total']}"]
        
        if resultados["recetas"] > 0:
            lineas.append(f"  📖 Recetas: {resultados['recetas']}")
        if resultados["catalogo"] > 0:
            lineas.append(f"  📦 Catálogo: {resultados['catalogo']}")
        if resultados["lotes"] > 0:
            lineas.append(f"  📋 Lotes: {resultados['lotes']}")
        if resultados["manuales"] > 0:
            lineas.append(f"  📘 Manuales BPM: {resultados['manuales']}")
        if resultados["genericos"] > 0:
            lineas.append(f"  📄 Genéricos: {resultados['genericos']}")
        
        if resultados["errores"]:
            lineas.append(f"\n⚠️ Errores: {len(resultados['errores'])}")
            for error in resultados["errores"][:3]:
                lineas.append(f"  - {error}")
        
        return "\n".join(lineas)

    @pyqtSlot()
    def _on_rag_ingest(self) -> None:
        """
        Abre diálogo para seleccionar documentos, los clasifica y guarda en BD.
        
        Tipos detectados:
        - Recetas (CSV con columna Ingredientes)
        - Catálogo de Inventario (CSV con id_producto, vida_util_dias)
        - Lotes de Inventario (CSV con id_lote, fecha_ingreso)
        - Manuales BPM (TXT/MD con palabras clave: procedimiento, paso, bpm)
        - Genéricos (otros documentos)
        """
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Ingesta RAG - Seleccionar Documentos", "",
            "Documentos (*.csv *.md *.txt);;Todos los archivos (*.*)"
        )
        if file_paths:
            self._append_system_message("⏳ Procesando documentos...")
            
            # Guardar documentos en base de datos
            resultados = self.rag_store.guardar_documentos(file_paths, self.db)
            self._rag_files.extend(file_paths)
            
            # Mostrar resumen detallado
            resumen = self._generar_resumen_guardado(resultados)
            self._append_system_message(resumen)
            
            # Mostrar en visor derecho
            self.viewer_read.clear()
            self.viewer_read.append("<h3>📚 Documentos Guardados</h3>")
            
            for doc in resultados.get("documentos_ids", []):
                self.viewer_read.append(f"✅ Documento ID: {doc}")
            
            self.viewer_read.append(f"\n<b>Total guardados: {resultados['guardados']}</b>")
            self.viewer_read.moveCursor(QTextCursor.MoveOperation.End)

    @pyqtSlot()
    def _on_send_message(self) -> None:
        message = self.input_field.toPlainText().strip()
        if not message:
            return
        self._append_user_message(message)
        self.input_field.clear()
        
        provider = self._selected_provider or ConfigManager.get_configured_provider()
        if not provider:
            self._append_system_message("🔒 Configure API Key primero")
            self._show_keys_dialog()
            return
        
        api_key = ConfigManager.get_api_key(provider)
        if not api_key:
            self._append_system_message(f"🔒 Configure API Key para {provider.value}")
            self._show_keys_dialog()
            return
        
        try:
            self._append_system_message(f"⏳ Procesando con {provider.value}...")
            orchestrator = Orchestrator(
                provider=provider,
                model=self._selected_model,
                db_manager=self.db  # For telemetry
            )
            tools = crear_herramientas_operativas(self.db)
            orchestrator.tools = tools
            
            historial = [
                {"rol": "user", "contenido": "Hola"},
                {"rol": "assistant", "contenido": "¡Hola! Soy ChefChat, tu asistente para restaurantes."}
            ]
            
            self.worker = Worker(
                orchestrator=orchestrator,
                message=message,
                historial=historial,
                contexto_rag=None
            )
            self.worker.chunk_recibido.connect(self._on_chunk_received)
            self.worker.error_occurred.connect(self._on_error)
            self.worker.start()
        except Exception as e:
            self._append_system_message(f"❌ Error: {str(e)}")

    def _append_user_message(self, message: str) -> None:
        self.chat_area.append(ChatBubble.user_bubble(
            SecurityValidator.sanitize_log_message(message), self.current_theme
        ))
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)

    def _append_assistant_message(self, message: str) -> None:
        self.chat_area.append(ChatBubble.assistant_bubble(message, self.current_theme))
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)

    def _append_system_message(self, message: str) -> None:
        self.chat_area.append(ChatBubble.system_bubble(message, self.current_theme))
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)

    @pyqtSlot(str)
    def _on_chunk_received(self, chunk: str) -> None:
        self._append_assistant_message(chunk)

    @pyqtSlot(str)
    def _on_error(self, error: str) -> None:
        self._append_system_message(f"❌ Error: {error}")

    @pyqtSlot()
    def _on_approve_action(self) -> None:
        self.hitl_bar.setVisible(False)
        if self.worker and self._pending_action_data:
            self.worker.aprobar_accion(self._pending_action_data)
            self._pending_action_data = None

    @pyqtSlot()
    def _on_reject_action(self) -> None:
        self.hitl_bar.setVisible(False)
        if self.worker:
            self.worker.rechazar_accion()
        self._append_system_message("🚫 Acción rechazada")


class APIKeyDialog(QDialog):
    """Diálogo para configuración de API Keys."""

    def __init__(self, parent: Optional[QWidget] = None, selected_provider: Optional[AIProvider] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🔐 Configuración - ChefChat Pro")
        self.setModal(True)
        self.resize(550, 320)
        self._provider = selected_provider or AIProvider.OPENAI
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        label_title = QLabel("Seguridad de Grado Industrial")
        label_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #deff9a;")
        label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_title)
        
        label = QLabel(
            "Las llaves se guardan en Windows Credential Manager (keyring). "
            "NUNCA en archivos .env o código."
        )
        label.setWordWrap(True)
        label.setStyleSheet("color: #94a3b8; padding: 8px;")
        layout.addWidget(label)
        
        provider_label = QLabel("Proveedor de IA:")
        provider_label.setStyleSheet("color: #e2e8f0; font-weight: bold;")
        layout.addWidget(provider_label)
        
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumHeight(40)
        for provider in ConfigManager.get_all_providers():
            self.provider_combo.addItem(
                ConfigManager.get_provider_display_name(provider), provider
            )
        self.provider_combo.setCurrentIndex(self.provider_combo.findData(self._provider))
        self.provider_combo.currentIndexChanged.connect(self._on_provider_combo_changed)
        layout.addWidget(self.provider_combo)
        
        self.key_field = QLineEdit()
        self.key_field.setPlaceholderText(f"API Key para {self._provider.value}")
        self.key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_field.setMinimumHeight(40)
        layout.addWidget(self.key_field)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        buttons = QWidget()
        btn_layout = QHBoxLayout(buttons)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setMaximumWidth(120)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_save = QPushButton("💾 Guardar")
        btn_save.setObjectName("btn_save")
        btn_save.setMaximumWidth(180)
        btn_save.clicked.connect(self._save_key)
        btn_layout.addWidget(btn_save)
        layout.addWidget(buttons)

    def _on_provider_combo_changed(self, index: int) -> None:
        if index < 0:
            return
        self._provider = self.provider_combo.currentData()
        self.key_field.setPlaceholderText(f"API Key para {self._provider.value}")

    def _save_key(self) -> None:
        api_key = self.key_field.text().strip()
        if not api_key:
            self.status_label.setText("⚠️ La API Key no puede estar vacía")
            self.status_label.setStyleSheet("color: #ef4444;")
            return
        if len(api_key) < 15:
            self.status_label.setText("⚠️ API Key demasiado corta")
            self.status_label.setStyleSheet("color: #ef4444;")
            return
        try:
            ConfigManager.save_api_key(self._provider, api_key)
            self.status_label.setText("✅ Guardado correctamente")
            self.status_label.setStyleSheet("color: #22c55e;")
            QMessageBox.information(self, "Éxito", "API Key guardada")
            self.accept()
        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.status_label.setStyleSheet("color: #ef4444;")