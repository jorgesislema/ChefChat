"""
Interfaz Gráfica para ChefChat Pro - PyQt6

Implementa la GUI con pantalla dividida (QSplitter), soporte para temas
Claro/Oscuro, y barra HITL para aprobación de acciones críticas.
"""

from typing import Optional, List, Dict, Any
import logging
# pylint: disable=no-name-in-module
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
    QSizePolicy,
)  # pylint: disable=no-name-in-module
# pylint: disable=no-name-in-module
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
# pylint: disable=no-name-in-module
from PyQt6.QtGui import QTextCursor, QFont

from gui.worker import Worker
from agents.orchestrator import Orchestrator
from core.config import AIProvider, ConfigManager
from core.security import SecurityValidator
from gui.telemetry_view import TelemetryDashboard
from data.db_manager import DatabaseManager
from data.rag_store import RAGStore


DARK_THEME = {
    "bg_primary": "#0F172A",
    "bg_secondary": "#1E293B",
    "bg_tertiary": "#334155",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "border": "#334155",
    "success": "#22C55E",
    "error": "#EF4444",
    "warning": "#FBBF24",
    "info": "#3B82F6",
}

LIGHT_THEME = {
    "bg_primary": "#F1F5F9",
    "bg_secondary": "#FFFFFF",
    "bg_tertiary": "#CBD5E1",
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "border": "#CBD5E1",
    "success": "#16A34A",
    "error": "#DC2626",
    "warning": "#D97706",
    "info": "#2563EB",
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

    QPushButton#btn_rag:hover {{
        background-color: {theme['info']};
        opacity: 0.8;
    }}

    QPushButton#btn_selector_config {{
        background-color: {theme['bg_tertiary']};
        border: 1px solid {theme['border']};
        border-radius: 6px;
        font-size: 14pt;
        padding: 0;
    }}

    QPushButton#btn_selector_config:hover {{
        background-color: {theme['accent']};
    }}

    QPushButton#btn_office {{
        background-color: {theme['bg_tertiary']};
        color: {theme['text_primary']};
        border: 1px solid {theme['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 9pt;
    }}

    QPushButton#btn_office:hover {{
        background-color: {theme['border']};
        border-color: {theme['accent']};
    }}

    QPushButton#btn_office:disabled {{
        opacity: 0.4;
    }}

    QPushButton#btn_theme {{
        background-color: {theme['bg_secondary']};
        border: 1px solid {theme['border']};
        border-radius: 6px;
        padding: 8px;
        max-width: 50px;
    }}

    QComboBox {{
        background-color: {theme['bg_secondary']};
        border: 2px solid {theme['accent']};
        border-radius: 6px;
        padding: 4px 8px;
        color: {theme['text_primary']};
        font-weight: bold;
        min-height: 30px;
    }}

    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}

    QComboBox::down-arrow {{
        width: 12px;
        height: 12px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {theme['bg_secondary']};
        color: {theme['text_primary']};
        selection-background-color: {theme['accent']};
        selection-color: white;
    }}

    QLabel {{
        color: {theme['text_primary']};
        padding: 4px;
    }}

    #selector_bar {{
        background-color: {theme['bg_primary']};
        padding: 4px 0;
        border-bottom: 1px solid {theme['border']};
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

    #sidebar {{
        background-color: {theme['bg_secondary']};
        border-right: 1px solid {theme['border']};
    }}

    QPushButton#sidebar_btn {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
        padding: 8px;
        font-size: 18pt;
        min-width: 44px;
        max-width: 44px;
        min-height: 44px;
        max-height: 44px;
    }}

    QPushButton#sidebar_btn:hover {{
        background-color: {theme['bg_tertiary']};
    }}

    QPushButton#sidebar_btn:checked {{
        background-color: {theme['accent']};
        color: {theme['bg_primary']};
    }}
    """


class ChatBubble:
    """Clase utilitaria para generar burbujas de chat HTML."""

    @staticmethod
    def user_bubble(text: str, theme: Dict[str, str]) -> str:
        """Generate a user chat bubble with right-aligned styling."""
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
        self.setMinimumSize(1024, 680)
        
        import os
        self._db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chefchat.db")
        self.db = DatabaseManager(db_path=self._db_path)
        self.rag_store = RAGStore(db_path=self._db_path)
        self.theme_mode = "dark"
        self.current_theme = DARK_THEME
        
        self._current_session_id: str = "default_session"
        self.worker: Optional[Worker] = None
        self._rag_files: List[str] = []
        self._pending_action_data: Optional[Dict[str, Any]] = None
        self._selected_provider: Optional[AIProvider] = None
        self._selected_model: Optional[str] = None
        self._ultimo_id_receta: Optional[str] = None
        self._ultima_respuesta: str = ""
        self._chat_history: List[str] = []
        self.provider_selector: Optional[QComboBox] = None
        self.model_selector: Optional[QComboBox] = None
        self.chat_area: Optional[QTextEdit] = None
        self.input_field: Optional[QTextEdit] = None
        self.btn_send: Optional[QPushButton] = None
        self.btn_rag: Optional[QPushButton] = None
        self.btn_word: Optional[QPushButton] = None
        self.btn_excel: Optional[QPushButton] = None
        self.btn_ppt: Optional[QPushButton] = None
        self.btn_config: Optional[QPushButton] = None
        self._left_widget: Optional[QWidget] = None
        self.telemetry_dashboard: Optional[TelemetryDashboard] = None
        self._telemetry_visible: bool = False
        self.stacked_widget: Optional[QStackedWidget] = None
        self.right_title: Optional[QLabel] = None
        self.viewer_read: Optional[QTextEdit] = None
        self.viewer_office: Optional[QTextEdit] = None
        self.hitl_bar: Optional[QWidget] = None
        self.btn_approve: Optional[QPushButton] = None
        self.btn_reject: Optional[QPushButton] = None
        self._right_panel: Optional[QWidget] = None
        
        self._setup_ui()
        self._check_api_key_on_startup()

    def _check_api_key_on_startup(self) -> None:
        """Verifica si hay API Key configurada y muestra diálogo si no."""
        self._update_provider_selector()
        if not ConfigManager.has_any_api_key():
            QTimer.singleShot(500, self._show_keys_dialog)

    def _setup_ui(self) -> None:
        """Configura toda la interfaz de usuario."""
        self.setStyleSheet(generate_stylesheet(self.current_theme))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ── Sidebar (VS Code style, max 60px) ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(56)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(6, 8, 6, 8)
        sidebar_layout.setSpacing(4)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.sidebar_chat = QPushButton("💬")
        self.sidebar_chat.setObjectName("sidebar_btn")
        self.sidebar_chat.setToolTip("Chat")
        self.sidebar_chat.setCheckable(True)
        self.sidebar_chat.setChecked(True)
        sidebar_layout.addWidget(self.sidebar_chat)
        
        self.sidebar_telemetry = QPushButton("📊")
        self.sidebar_telemetry.setObjectName("sidebar_btn")
        self.sidebar_telemetry.setToolTip("Telemetría")
        self.sidebar_telemetry.setCheckable(True)
        self.sidebar_telemetry.clicked.connect(self._toggle_telemetry)
        sidebar_layout.addWidget(self.sidebar_telemetry)
        
        self.sidebar_config = QPushButton("⚙️")
        self.sidebar_config.setObjectName("sidebar_btn")
        self.sidebar_config.setToolTip("Configuración API Keys")
        self.sidebar_config.clicked.connect(self._show_keys_dialog)
        sidebar_layout.addWidget(self.sidebar_config)
        
        sidebar_layout.addStretch()
        
        self.sidebar_theme = QPushButton("🌙")
        self.sidebar_theme.setObjectName("sidebar_btn")
        self.sidebar_theme.setToolTip("Cambiar tema")
        self.sidebar_theme.clicked.connect(self._toggle_theme)
        sidebar_layout.addWidget(self.sidebar_theme)
        
        main_layout.addWidget(sidebar)
        
        # ── Main splitter ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, stretch=1)
        
        self._setup_left_panel(splitter)
        self._setup_right_panel(splitter)
        
        splitter.setSizes([560, 840])
        splitter.setStretchFactor(0, 40)
        splitter.setStretchFactor(1, 60)
        
        # Wire sidebar chat button to show chat (index 0)
        self.sidebar_chat.clicked.connect(lambda: self._show_panel(0))

    def _setup_left_panel(self, splitter: QSplitter) -> None:
        """Configura el panel izquierdo (Chat - 40%)."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 8, 8, 12)
        left_layout.setSpacing(8)
        
        left_layout.addWidget(self._build_selector_bar())
        left_layout.addWidget(self._build_chat_area(), stretch=1)
        left_layout.addWidget(self._build_input_widget())
        left_layout.addWidget(self._build_action_bar())
        
        splitter.addWidget(left_widget)
        self._left_widget = left_widget

    def _build_selector_bar(self) -> QWidget:
        selector_bar = QWidget()
        selector_bar.setObjectName("selector_bar")
        sel_layout = QHBoxLayout(selector_bar)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.setSpacing(6)
        
        self.provider_selector = QComboBox()
        self.provider_selector.setObjectName("provider_selector")
        self.provider_selector.currentIndexChanged.connect(self._on_provider_changed)
        sel_layout.addWidget(self.provider_selector, stretch=3)
        
        self.model_selector = QComboBox()
        self.model_selector.setObjectName("model_selector")
        self.model_selector.currentIndexChanged.connect(self._on_model_changed)
        sel_layout.addWidget(self.model_selector, stretch=2)
        
        self.btn_config = QPushButton("⚙️")
        self.btn_config.setObjectName("btn_selector_config")
        self.btn_config.setToolTip("Configurar API Keys")
        self.btn_config.setFixedSize(36, 36)
        self.btn_config.clicked.connect(self._show_keys_dialog)
        sel_layout.addWidget(self.btn_config)
        
        return selector_bar

    def _build_chat_area(self) -> QTextEdit:
        self.chat_area = QTextEdit()
        self.chat_area.setObjectName("chat_area")
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont("Segoe UI", 10))
        self.chat_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return self.chat_area

    def _build_input_widget(self) -> QWidget:
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(6)
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(80)
        self.input_field.setPlaceholderText("Escribe tu mensaje aquí...")
        self.input_field.setFont(QFont("Segoe UI", 10))
        self.input_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        input_layout.addWidget(self.input_field, stretch=5)
        
        self.btn_send = QPushButton("Enviar")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.setToolTip("Enviar mensaje")
        self.btn_send.clicked.connect(self._on_send_message)
        self.btn_send.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        input_layout.addWidget(self.btn_send)
        
        return input_widget

    def _create_office_button(self, label: str, tooltip: str, action: str) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("btn_office")
        button.setToolTip(tooltip)
        button.clicked.connect(lambda _, t=action: self._enviar_a_office(t))
        button.setEnabled(False)
        return button

    def _build_action_bar(self) -> QWidget:
        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(4)
        
        self.btn_rag = QPushButton("📂 +")
        self.btn_rag.setObjectName("btn_rag")
        self.btn_rag.setToolTip("Cargar documentos CSV/MD")
        self.btn_rag.setStyleSheet("max-width: 50px; font-size: 10pt;")
        self.btn_rag.clicked.connect(self._on_rag_ingest)
        action_layout.addWidget(self.btn_rag)

        self.btn_word = self._create_office_button("📄 Word", "Enviar a Word", "word")
        action_layout.addWidget(self.btn_word)

        self.btn_excel = self._create_office_button("📊 Excel", "Enviar a Excel", "excel")
        action_layout.addWidget(self.btn_excel)

        self.btn_ppt = self._create_office_button("📽️ PPT", "Enviar a PowerPoint", "powerpoint")
        action_layout.addWidget(self.btn_ppt)
        
        action_layout.addStretch()
        
        return action_bar

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
        self._telemetry_visible = False

    def _show_panel(self, index: int) -> None:
        """Muestra el panel indicado en el stacked widget."""
        self.sidebar_chat.setChecked(index == 0)
        self.sidebar_telemetry.setChecked(index == 2)
        if self.stacked_widget is not None:
            self.stacked_widget.setCurrentIndex(index)
        if index == 0:
            self._telemetry_visible = False

    def _toggle_theme(self) -> None:
        """Alterna entre tema Claro y Oscuro."""
        if self.theme_mode == "dark":
            self.theme_mode = "light"
            self.current_theme = LIGHT_THEME
            self.sidebar_theme.setText("☀️")
        else:
            self.theme_mode = "dark"
            self.current_theme = DARK_THEME
            self.sidebar_theme.setText("🌙")
        
        self.setStyleSheet(generate_stylesheet(self.current_theme))
        self._update_theme_dependent_elements()

    def _update_theme_dependent_elements(self) -> None:
        """Actualiza elementos que dependen del tema."""
        if self.right_title is not None:
            accent_color = self.current_theme['accent']
            right_title = self.right_title
            right_title.setStyleSheet(
                f"font-size: 14pt; font-weight: bold; "
                f"color: {accent_color}; padding: 8px;"
            )
        if self.viewer_read is not None:
            bg_color = self.current_theme['bg_primary']
            border_color = self.current_theme['border']
            self.viewer_read.setStyleSheet(
                f"background-color: {bg_color}; "
                f"border: 1px solid {border_color}; border-radius: 8px;"
            )
        if self.viewer_office is not None:
            bg_color = self.current_theme['bg_primary']
            border_color = self.current_theme['border']
            self.viewer_office.setStyleSheet(
                f"background-color: {bg_color}; "
                f"border: 1px solid {border_color}; border-radius: 8px;"
            )
        if self.telemetry_dashboard is not None:
            is_dark = self.theme_mode == "dark"
            self.telemetry_dashboard.apply_theme(is_dark)

    def _update_provider_selector(self) -> None:
        """Actualiza el selector de proveedores de IA."""
        if self.provider_selector is None:
            return
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
        provider = self.provider_selector.currentData()
        if provider:
            self._selected_provider = provider
        self._update_model_selector()

    def _on_provider_changed(self, index: int) -> None:
        if index < 0:
            return
        if self.provider_selector is None:
            return
        provider = self.provider_selector.currentData()
        if provider:
            self._selected_provider = provider
            self._update_model_selector()

    def _on_model_changed(self, index: int) -> None:
        if index < 0:
            return
        if self.model_selector:
            self._selected_model = self.model_selector.currentData()

    def _update_model_selector(self) -> None:
        if self.model_selector is None:
            return
        assert self.model_selector is not None
        self.model_selector.blockSignals(True)
        self.model_selector.clear()
        if self._selected_provider:
            models = ConfigManager.get_models_for_provider(self._selected_provider)
            for model in models:
                self.model_selector.addItem(model, model)
            self.model_selector.setCurrentIndex(0)
        self.model_selector.blockSignals(False)
        model = self.model_selector.currentData()
        if model:
            self._selected_model = model

    def _show_keys_dialog(self) -> None:
        """Show API key configuration dialog."""
        dialog = APIKeyDialog(self, self._selected_provider)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_provider_selector()
            # After saving, ensure _selected_provider is set
            if not self._selected_provider:
                configured = ConfigManager.get_configured_provider()
                if configured:
                    self._selected_provider = configured
                    logging.info("Set _selected_provider to %s", configured.value)
            QMessageBox.information(self, "Guardado", "API Key guardada en el sistema seguro")

    def _toggle_telemetry(self) -> None:
        """Muestra/oculta el dashboard de telemetría."""
        if self._telemetry_visible:
            self._show_panel(0)
        else:
            if not self.telemetry_dashboard and self.stacked_widget is not None:
                self.telemetry_dashboard = TelemetryDashboard(self.db, self)
                self.stacked_widget.addWidget(self.telemetry_dashboard)
            self._show_panel(2)
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
            
            # Mostrar en visor derecho (si está disponible)
            if self.viewer_read is not None:
                self.viewer_read.clear()
                self.viewer_read.append("<h3>📚 Documentos Guardados</h3>")

                for doc in resultados.get("documentos_ids", []):
                    self.viewer_read.append(f"✅ Documento ID: {doc}")

                self.viewer_read.append(f"\n<b>Total guardados: {resultados['guardados']}</b>")
                self.viewer_read.moveCursor(QTextCursor.MoveOperation.End)

    @pyqtSlot()
    def _on_send_message(self) -> None:
        input_field = self.input_field
        if input_field is None:
            return

        message = input_field.toPlainText().strip()
        if not message:
            return
        self._append_user_message(message)
        input_field.clear()
        
        provider = self._selected_provider or ConfigManager.get_configured_provider()
        if not provider:
            self._append_system_message("🔒 Configure API Key primero")
            self._show_keys_dialog()
            return
        
        # Debug: Verificar que la API key esté disponible
        api_key = ConfigManager.get_api_key(provider)
        logging.info("Send message - Provider: %s, API Key found: %s", provider, bool(api_key))
        
        if not api_key:
            self._append_system_message(f"🔒 API Key no encontrada para {provider.value}")
            self._append_system_message("💡 Verificando proveedores disponibles...")
            
            # Verificar todos los providers
            for p in ConfigManager.get_all_providers():
                key = ConfigManager.get_api_key(p)
                status = "[OK]" if key else "[NOT SET]"
                logging.info("  Provider %s: %s", p.value, status)
            
            self._show_keys_dialog()
            return
        
        try:
            self._append_system_message(f"⏳ Procesando con {provider.value}...")
            logging.info("Creating Orchestrator with provider=%s, model=%s", provider, self._selected_model)
            
            orchestrator = Orchestrator(
                provider=provider,
                model=self._selected_model,
                db_manager=self.db  # For telemetry
            )
            
            logging.info("Orchestrator created successfully")
            
            historial = [
                {"rol": "user", "contenido": "Hola"},
                {"rol": "assistant", "contenido": "¡Hola! Soy ChefChat, tu asistente para restaurantes."}
            ]
            
            self.worker = Worker(
                orchestrator=orchestrator,
                message=message,
                historial=historial,
                contexto_rag=None,
                timeout_segundos=90  # 90 segundos timeout
            )
            self.worker.chunk_recibido.connect(self._on_chunk_received)
            self.worker.respuesta_completada.connect(self._on_response_completed)
            self.worker.error_occurred.connect(self._on_error)
            self.worker.start()
        except (KeyError, ValueError, RuntimeError, TypeError, OSError) as e:
            # Capturar errores comunes (KeyError, ValueError, RuntimeError, TypeError, OSError)
            error_msg = str(e)
            
            # Si es error de API key, mostrar mensaje específico
            if "api_key" in error_msg.lower() or "credentials" in error_msg.lower() or "key" in error_msg.lower():
                self._append_system_message("🔒 Error: API Key no configurada o inválida")
                self._append_system_message("💡 Ve a Configuración (⚙️) y agrega tu API key")
                self._show_keys_dialog()
            else:
                self._append_system_message(f"❌ Error: {error_msg}")
            
            # Registrar error en log (sin mostrar al usuario)
            logging.error("Error en Orchestrator: %s", error_msg)

    def _append_user_message(self, message: str) -> None:
        chat_area = self.chat_area
        if chat_area is None:
            return
        chat_area.append(ChatBubble.user_bubble(
            SecurityValidator.sanitize_log_message(message), self.current_theme
        ))
        chat_area.moveCursor(QTextCursor.MoveOperation.End)

    def _append_assistant_message(self, message: str) -> None:
        chat_area = self.chat_area
        if chat_area is None:
            return
        chat_area.append(ChatBubble.assistant_bubble(message, self.current_theme))
        chat_area.moveCursor(QTextCursor.MoveOperation.End)

    def _append_system_message(self, message: str) -> None:
        chat_area = self.chat_area
        if chat_area is None:
            return
        chat_area.append(ChatBubble.system_bubble(message, self.current_theme))
        chat_area.moveCursor(QTextCursor.MoveOperation.End)

    @pyqtSlot(str)
    def _on_chunk_received(self, chunk: str) -> None:
        self._ultima_respuesta = chunk
        if chunk.strip():
            self._chat_history.append(chunk)
        import re
        match = re.search(r'\b((?:SPO|SOP|BEB|ENS|POS|ENT|PLF|EVT)[-_]\d{2,4})\b', chunk.upper())
        if match:
            self._ultimo_id_receta = match.group(1)
        if self.btn_word is not None:
            self.btn_word.setEnabled(True)
        if self.btn_excel is not None:
            self.btn_excel.setEnabled(True)
        if self.btn_ppt is not None:
            self.btn_ppt.setEnabled(True)

    @pyqtSlot(str)
    def _on_response_completed(self, respuesta: str) -> None:
        self._append_assistant_message(respuesta)
        self._ultima_respuesta = respuesta

    def _enviar_a_office(self, app: str) -> None:
        """Envía la última respuesta a la aplicación de Office."""
        from agents.mcp_client import MCPClient
        from core.models import AccionOffice

        contenido = self._ultima_respuesta or (self._chat_history[-1] if self._chat_history else "")
        contenido = contenido.strip()
        if not contenido:
            self._append_system_message("❌ No hay respuesta que enviar")
            return

        try:
            if self._ultimo_id_receta and app in ("word", "excel", "powerpoint"):
                self._append_system_message(
                    f"⏳ Enviando {self._ultimo_id_receta} a {app.title()}..."
                )
                from agents.tools import crear_herramientas_operativas
                tools = crear_herramientas_operativas(self.db)
                tool_map = {
                    "word": "enviar_receta_a_word",
                    "excel": "enviar_receta_a_excel",
                    "powerpoint": "enviar_menu_a_powerpoint"
                }
                tool_name = tool_map[app]
                tool = next((t for t in tools if t.name == tool_name), None)
                if tool is not None and tool.func is not None:
                    resultado = tool.func(self._ultimo_id_receta)
                    self._append_system_message(f"✅ {resultado}")
                    return

            titulo = contenido.split("\n")[0][:60] or "Reporte"
            if "RECETA:" in contenido.upper():
                titulo = "Receta"
            elif "PLANIFICACION" in contenido.upper():
                titulo = "Planificación de Evento"
            elif "LISTA DE COMPRAS" in contenido.upper():
                titulo = "Lista de Compras"
            elif "ORDEN DE COMPRA" in contenido.upper():
                titulo = "Orden de Compra"
            elif "MENU" in contenido.upper():
                titulo = "Menú"
            elif "DASHBOARD" in contenido.upper():
                titulo = "Dashboard"

            self._append_system_message(
                f"⏳ Enviando a {app.title()}..."
            )
            cliente = MCPClient()
            resultado_obj: str | dict = cliente.ejecutar_herramienta(AccionOffice(
                herramienta=app,
                operacion="enviar",
                ruta_archivo="",
                payload={
                    "contenido": contenido,
                    "formato": {"titulo": titulo}
                },
                requiere_hitl=False
            ))
            if isinstance(resultado_obj, dict):
                mensaje = resultado_obj.get("mensaje", "OK")
            else:
                mensaje = str(resultado_obj)
            self._append_system_message(
                f"✅ Enviado a {app.title()}: {mensaje}"
            )
        except (ValueError, KeyError, AttributeError) as e:
            self._append_system_message(
                f"❌ Error al enviar a {app.title()}: {str(e)}"
            )

    @pyqtSlot(str)
    def _on_error(self, error: str) -> None:
        self._append_system_message(f"❌ Error: {error}")

    @pyqtSlot()
    def _on_approve_action(self) -> None:
        if self.hitl_bar is not None:
            self.hitl_bar.setVisible(False)
        if self.worker and self._pending_action_data:
            self.worker.aprobar_accion(self._pending_action_data)
            self._pending_action_data = None

    @pyqtSlot()
    def _on_reject_action(self) -> None:
        if self.hitl_bar is not None:
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
        label_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #3B82F6;")
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
        provider_label.setStyleSheet("color: #94A3B8; font-weight: bold;")
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
        except (ValueError, OSError) as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.status_label.setStyleSheet("color: #ef4444;")