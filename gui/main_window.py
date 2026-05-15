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
    QSizePolicy,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QColor, QPalette, QTextCursor, QFont
from gui.worker import Worker
from agents.orchestrator import Orchestrator
from core.config import AIProvider, ConfigManager
from core.security import SecurityValidator


DARK_STYLESHEET = """
QWidget {
    background-color: #0f172a;
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
}

QMainWindow {
    background-color: #0f172a;
}

QSplitter::handle {
    background-color: #1e293b;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #334155;
}

QTextEdit, QTextEdit#chat_area {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px;
    color: #e2e8f0;
}

QTextEdit#chat_area {
    padding: 16px;
}

QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 16px;
    color: #e2e8f0;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #334155;
}

QPushButton:pressed {
    background-color: #475569;
}

QPushButton#btn_send {
    background-color: #deff9a;
    color: #0f172a;
    font-weight: bold;
    border: none;
}

QPushButton#btn_send:hover {
    background-color: #b8f29a;
}

QPushButton#btn_approve {
    background-color: #22c55e;
    color: white;
    font-weight: bold;
    border: none;
}

QPushButton#btn_approve:hover {
    background-color: #16a34a;
}

QPushButton#btn_reject {
    background-color: #ef4444;
    color: white;
    font-weight: bold;
    border: none;
}

QPushButton#btn_reject:hover {
    background-color: #dc2626;
}

QPushButton#btn_rag {
    background-color: #3b82f6;
    color: white;
    border: none;
    font-size: 14pt;
    max-width: 40px;
}

QPushButton#btn_rag:hover {
    background-color: #2563eb;
}

QLineEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px;
    color: #e2e8f0;
}

QComboBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px;
    color: #e2e8f0;
}

QComboBox:hover {
    border-color: #475569;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #e2e8f0;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #334155;
    selection-background-color: #334155;
    color: #e2e8f0;
}

QLabel {
    color: #e2e8f0;
    padding: 4px;
}

#right_panel {
    background-color: #0f172a;
    border-left: 1px solid #1e293b;
}

#hitl_bar {
    background-color: #1e293b;
    border-top: 2px solid #deff9a;
    padding: 12px;
    border-radius: 8px;
}

#hitl_label {
    color: #fbbf24;
    font-weight: bold;
    font-size: 10pt;
}

QDialog {
    background-color: #0f172a;
}

QMessageBox {
    background-color: #0f172a;
}
"""


class ChatBubble:
    @staticmethod
    def user_bubble(text: str) -> str:
        return f'''
        <div style="text-align: right; margin: 8px 0;">
            <span style="display: inline-block; background-color: #334155; 
                         color: #e2e8f0; padding: 10px 16px; border-radius: 16px 16px 4px 16px;
                         max-width: 70%; word-wrap: break-word;">
                {text}
            </span>
        </div>
        '''

    @staticmethod
    def assistant_bubble(text: str) -> str:
        return f'''
        <div style="text-align: left; margin: 8px 0;">
            <span style="display: inline-block; background-color: #1e293b; 
                         color: #e2e8f0; padding: 10px 16px; border-radius: 16px 16px 16px 4px;
                         max-width: 70%; word-wrap: break-word;">
                {text}
            </span>
        </div>
        '''

    @staticmethod
    def system_bubble(text: str) -> str:
        return f'''
        <div style="text-align: center; margin: 8px 0;">
            <span style="display: inline-block; background-color: #475569; 
                         color: #94a3b8; padding: 8px 16px; border-radius: 16px;
                         font-style: italic; font-size: 9pt;">
                {text}
            </span>
        </div>
        '''


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChefChat Pro - Asistente IA para Restaurantes")
        self.setMinimumSize(1400, 900)
        self._current_session_id: str = "default_session"
        self.worker: Optional[Worker] = None
        self._rag_files: List[str] = []
        self._pending_action_data: Optional[Dict[str, Any]] = None
        self._selected_provider: Optional[AIProvider] = None
        self._selected_model: Optional[str] = None
        self._setup_ui()
        self._check_api_key_on_startup()

    def _check_api_key_on_startup(self) -> None:
        if not ConfigManager.has_any_api_key():
            QTimer.singleShot(500, self._show_keys_dialog)
        else:
            self._update_provider_selector()

    def _setup_ui(self) -> None:
        self.setStyleSheet(DARK_STYLESHEET)
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
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 16, 8, 16)
        left_layout.setSpacing(12)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
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
        self.btn_rag.setToolTip("Ingesta RAG: Cargar documentos al sistema de conocimiento")
        self.btn_rag.clicked.connect(self._on_rag_ingest)
        input_layout.addWidget(self.btn_rag)
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        self.input_field.setPlaceholderText("Escribe tu mensaje aquí...")
        self.input_field.setFont(QFont("Segoe UI", 10))
        input_layout.addWidget(self.input_field, stretch=7)
        self.btn_send = QPushButton("Enviar")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.setToolTip("Enviar mensaje (Enter)")
        self.btn_send.clicked.connect(self._on_send_message)
        input_layout.addWidget(self.btn_send, stretch=1)
        left_layout.addWidget(input_widget)
        splitter.addWidget(left_widget)
        self._left_widget = left_widget

    def _setup_right_panel(self, splitter: QSplitter) -> None:
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 16, 16, 16)
        right_layout.setSpacing(12)
        right_widget.setObjectName("right_panel")
        self.right_title = QLabel("Bienvenido a ChefChat Pro")
        self.right_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #deff9a; padding: 8px;")
        right_layout.addWidget(self.right_title)
        self.stacked_widget = QStackedWidget()
        self.viewer_read = QTextEdit()
        self.viewer_read.setReadOnly(True)
        self.viewer_read.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px;")
        self.viewer_office = QTextEdit()
        self.viewer_office.setReadOnly(True)
        self.viewer_office.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px;")
        self.stacked_widget.addWidget(self.viewer_read)
        self.stacked_widget.addWidget(self.viewer_office)
        right_layout.addWidget(self.stacked_widget, stretch=9)
        self.hitl_bar = QWidget()
        self.hitl_bar.setObjectName("hitl_bar")
        self.hitl_bar.setVisible(False)
        hitl_layout = QHBoxLayout(self.hitl_bar)
        hitl_layout.setContentsMargins(8, 8, 8, 8)
        hitl_label = QLabel("⚠️ Aprobación requerida para acción en Office")
        hitl_label.setObjectName("hitl_label")
        hitl_layout.addWidget(hitl_label, stretch=3)
        self.btn_approve = QPushButton("✔ Aprobar Cambio")
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

    def _update_provider_selector(self) -> None:
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
            self._update_provider_key_status()

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

    def _update_provider_key_status(self) -> None:
        if self._selected_provider:
            has_key = ConfigManager.get_api_key(self._selected_provider) is not None
            index = self.provider_selector.currentIndex()
            display_text = self.provider_selector.currentText()
            if has_key:
                new_text = f"✅ {ConfigManager.get_provider_display_name(self._selected_provider)}"
            else:
                new_text = f"⚠️ {ConfigManager.get_provider_display_name(self._selected_provider)}"
            if display_text != new_text:
                self.provider_selector.setItemText(index, new_text)

    def _show_keys_dialog(self) -> None:
        dialog = APIKeyDialog(self, self._selected_provider)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_provider_selector()
            QMessageBox.information(self, "Guardado", "API Key guardada en el sistema seguro")

    @pyqtSlot()
    def _on_rag_ingest(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Ingesta RAG - Seleccionar Documentos",
            "",
            "Documentos (*.pdf *.txt *.docx *.md);;Todos los archivos (*.*)"
        )
        if file_paths:
            self._rag_files.extend(file_paths)
            files_list = ", ".join([path.split("/")[-1].split("\\")[-1] for path in file_paths])
            self._append_system_message(f"📚 Documentos cargados para RAG: {files_list}")
            self.viewer_read.append(f"<br>=== RAG CONTEXT LOADED ===<br>Files: {len(self._rag_files)}<br>")

    @pyqtSlot()
    def _on_send_message(self) -> None:
        message = self.input_field.toPlainText().strip()
        if not message:
            return
        self._append_user_message(message)
        self.input_field.clear()
        provider = self._selected_provider or ConfigManager.get_configured_provider()
        if not provider:
            self._append_system_message("🔒 Configure su API Key primero usando el botón de configuración")
            self._show_keys_dialog()
            return
        api_key = ConfigManager.get_api_key(provider)
        if not api_key:
            self._append_system_message(f"🔒 Configure la API Key para {provider.value} primero")
            self._show_keys_dialog()
            return
        try:
            self._append_system_message(f"⏳ Procesando con {provider.value}...")
            orchestrator = Orchestrator(
                provider=provider,
                model=self._selected_model
            )
            historial = [
                {"rol": "user", "contenido": "Hola"},
                {"rol": "assistant", "contenido": "¡Hola! Soy ChefChat, tu asistente IA para restaurantes. ¿En qué puedo ayudarte hoy?"}
            ]
            self.worker = Worker(
                orchestrator=orchestrator,
                message=message,
                historial=historial,
                contexto_rag=None
            )
            self.worker.chunk_recibido.connect(self._on_chunk_received)
            self.worker.requiere_aprobacion.connect(self._on_requires_approval)
            self.worker.accion_completada.connect(self._on_action_completed)
            self.worker.error_occurred.connect(self._on_error)
            self.worker.respuesta_completada.connect(self._on_respuesta_completada)
            self._pending_action_data = None
            self.worker.start()
        except Exception as e:
            self._append_system_message(f"❌ Error: {str(e)}")

    def _append_user_message(self, message: str) -> None:
        self.chat_area.append(ChatBubble.user_bubble(SecurityValidator.sanitize_log_message(message)))
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)

    def _append_assistant_message(self, message: str) -> None:
        self.chat_area.append(ChatBubble.assistant_bubble(message))
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)

    def _append_system_message(self, message: str) -> None:
        self.chat_area.append(ChatBubble.system_bubble(message))
        self.chat_area.moveCursor(QTextCursor.MoveOperation.End)

    @pyqtSlot(str)
    def _on_chunk_received(self, chunk: str) -> None:
        self._append_assistant_message(chunk)

    @pyqtSlot(str)
    def _on_respuesta_completada(self, respuesta: str) -> None:
        self._append_system_message("✅ Respuesta completada")

    @pyqtSlot(object)
    def _on_requires_approval(self, accion) -> None:
        self._pending_action_data = accion
        self.right_title.setText(f"⏸ Acción pendiente: {accion.herramienta.upper()}")
        self.right_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #fbbf24; padding: 8px;")
        self.stacked_widget.setCurrentIndex(1)
        self.viewer_office.clear()
        preview_text = f"""=== PREVIEW DE ACCIÓN OFFICE ===

🏷️ Herramienta: {accion.herramienta.upper()}
📝 Operación: {accion.operacion}
📁 Ruta: {accion.ruta_archivo}

📋 Payload:
"""
        for key, value in accion.payload.items():
            preview_text += f"   {key}: {value}\n"
        self.viewer_office.setPlainText(preview_text)
        self.hitl_bar.setVisible(True)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#FFF3E0"))
        self._right_panel.setPalette(palette)

    @pyqtSlot()
    def _on_approve_action(self) -> None:
        self.hitl_bar.setVisible(False)
        self._reset_right_panel()
        if self.worker and self._pending_action_data:
            self.worker.aprobar_accion(self._pending_action_data)
            self._pending_action_data = None

    @pyqtSlot()
    def _on_reject_action(self) -> None:
        self.hitl_bar.setVisible(False)
        self._reset_right_panel()
        if self.worker:
            self.worker.rechazar_accion()
        self._append_system_message("🚫 Acción rechazada por el usuario")

    def _reset_right_panel(self) -> None:
        self.right_title.setText("Bienvenido a ChefChat Pro")
        self.right_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #deff9a; padding: 8px;")
        palette = QPalette()
        self._right_panel.setPalette(palette)
        self.stacked_widget.setCurrentIndex(0)
        self.viewer_office.clear()
        self._pending_action_data = None

    @pyqtSlot(str)
    def _on_action_completed(self, mensaje: str) -> None:
        self._append_system_message(f"✅ {mensaje}")
        self._reset_right_panel()

    @pyqtSlot(str)
    def _on_error(self, error: str) -> None:
        self._append_system_message(f"❌ Error: {error}")
        self._reset_right_panel()


class APIKeyDialog(QDialog):
    def __init__(self, parent: Optional["QWidget"] = None, selected_provider: Optional[AIProvider] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🔐 Configuración de Bóveda - ChefChat Pro")
        self.setModal(True)
        self.resize(550, 320)
        self._provider = selected_provider or AIProvider.OPENROUTER
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        label_title = QLabel("Seguridad de Grado Industrial")
        label_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #deff9a;")
        label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_title)
        label = QLabel(
            "Las llaves se guardan en el administrador de credenciales seguro del sistema operativo (Windows Credential Manager / Keyring). "
            "NUNCA se almacenan en archivos .env o código fuente."
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
            display_name = ConfigManager.get_provider_display_name(provider)
            self.provider_combo.addItem(display_name, provider)
        self.provider_combo.setCurrentIndex(self.provider_combo.findData(self._provider))
        self.provider_combo.currentIndexChanged.connect(self._on_provider_combo_changed)
        layout.addWidget(self.provider_combo)
        self.key_field = QLineEdit()
        self.key_field.setPlaceholderText(f"Introduce tu API Key para {self._provider.value}")
        self.key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_field.setMinimumHeight(40)
        layout.addWidget(self.key_field)
        model_label = QLabel("Modelo:")
        model_label.setStyleSheet("color: #e2e8f0;")
        layout.addWidget(model_label)
        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(35)
        self._update_model_combo()
        layout.addWidget(self.model_combo)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        buttons = QWidget()
        btn_layout = QHBoxLayout(buttons)
        btn_layout.setSpacing(12)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setMaximumWidth(120)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_save = QPushButton("💾 Guardar en Bóveda")
        btn_save.setObjectName("btn_save")
        btn_save.setMaximumWidth(180)
        btn_save.clicked.connect(self._save_key)
        btn_layout.addWidget(btn_save)
        layout.addWidget(buttons)
        existing_key = ConfigManager.get_api_key(self._provider)
        if existing_key:
            self.key_field.setPlaceholderText(f"Nuevo key (dejar vacío para no cambiar)")

    def _on_provider_combo_changed(self, index: int) -> None:
        if index < 0:
            return
        self._provider = self.provider_combo.currentData()
        self.key_field.setPlaceholderText(f"Introduce tu API Key para {self._provider.value}")
        self._update_model_combo()

    def _update_model_combo(self) -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        if self._provider:
            models = ConfigManager.get_models_for_provider(self._provider)
            for model in models:
                self.model_combo.addItem(model, model)
        self.model_combo.blockSignals(False)

    def _save_key(self) -> None:
        api_key = self.key_field.text().strip()
        if not api_key:
            self.status_label.setText("⚠️ La API Key no puede estar vacía")
            self.status_label.setStyleSheet("color: #ef4444;")
            return
        if len(api_key) < 15:
            self.status_label.setText("⚠️ La API Key parece demasiado corta")
            self.status_label.setStyleSheet("color: #ef4444;")
            return
        try:
            ConfigManager.save_api_key(self._provider, api_key)
            self.status_label.setText("✅ Guardado correctamente")
            self.status_label.setStyleSheet("color: #22c55e;")
            QMessageBox.information(self, "Éxito", f"API Key para {self._provider.value} guardada de forma segura")
            self.accept()
        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.status_label.setStyleSheet("color: #ef4444;")