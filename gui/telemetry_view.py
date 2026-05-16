"""
Telemetry Dashboard for ChefChat Pro - Dark Aesthetic UI

Observabilidad y Telemetría en Tiempo Real
- KPI Cards: Gasto Total, Tokens, Peticiones
- Gráfico de Barras: Gasto últimos 7 días
- Tabla de Datos: Registros recientes
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen


# =============================================================================
# PRICING DICTIONARY (USD per 1M tokens)
# =============================================================================

PRICING = {
    # OpenRouter Models
    "minimax-2.7b": {"input": 0.14, "output": 0.28},
    "openrouter/auto": {"input": 0.10, "output": 0.20},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-coder": {"input": 0.14, "output": 0.28},
    
    # Google Gemini
    "gemini-pro": {"input": 0.50, "output": 1.50},
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.30},
    
    # Anthropic (Direct)
    "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    
    # OpenAI (Direct)
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    
    # OpenCode
    "big-pickle": {"input": 0.00, "output": 0.00},  # FREE
    "open-code-v1": {"input": 0.00, "output": 0.00},  # FREE
    "code-assistant": {"input": 0.00, "output": 0.00},  # FREE
    
    # Default fallback
    "default": {"input": 1.00, "output": 3.00},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculates the cost for a given model and token usage.
    
    Args:
        model: Model name identifier.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
    
    Returns:
        float: Cost in USD.
    """
    # Find pricing (try exact match, then partial)
    pricing = PRICING.get(model, PRICING.get("default"))
    
    # Calculate cost
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    
    return round(input_cost + output_cost, 6)


# =============================================================================
# DARK THEME STYLES
# =============================================================================

DARK_BG = "#0f172a"
CARD_BG = "#1e293b"
TEXT_PRIMARY = "#f5f5f5"
TEXT_SECONDARY = "#94a3b8"
ACCENT_GREEN = "#deff9a"
ACCENT_RED = "#ff4757"
ACCENT_BLUE = "#3b82f6"
BORDER_COLOR = "#334155"


class KPICard(QFrame):
    """KPI Card with rounded corners and accent number."""

    def __init__(self, title: str, value: str, icon: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background-color: {CARD_BG};
                border-radius: 12px;
                padding: 16px;
                border: 1px solid {BORDER_COLOR};
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: 10pt;
            font-weight: 500;
        """)
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            color: {ACCENT_GREEN};
            font-size: 24pt;
            font-weight: bold;
        """)
        layout.addWidget(value_label)


class BarChartWidget(QWidget):
    """Simple bar chart for spending visualization using QPainter."""

    def __init__(self, data: List[Dict[str, Any]], parent=None) -> None:
        super().__init__(parent)
        self.data = data
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """Updates chart data and refreshes."""
        self.data = data
        self.update()

    def paintEvent(self, event) -> None:
        """Draws the bar chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.setBrush(QBrush(QColor(CARD_BG)))
        painter.setPen(QPen(QColor(BORDER_COLOR), 1))
        painter.drawRoundedRect(self.rect(), 12, 12)
        
        if not self.data:
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sin datos")
            return
        
        # Chart dimensions
        margin = 50
        chart_width = self.width() - 2 * margin
        chart_height = self.height() - 2 * margin
        
        # Max value for scaling
        max_value = max((float(d.get("gasto_dia", 0)) for d in self.data), default=1)
        if max_value == 0:
            max_value = 1
        
        # Draw bars
        bar_width = chart_width / len(self.data) * 0.7
        spacing = chart_width / len(self.data) * 0.3
        
        for i, item in enumerate(self.data):
            x = margin + i * (bar_width + spacing) + spacing / 2
            value = float(item.get("gasto_dia", 0))
            bar_height = (value / max_value) * chart_height if max_value > 0 else 0
            
            # Bar gradient color based on value
            if value > 1.0:
                color = ACCENT_RED
            elif value > 0.5:
                color = ACCENT_BLUE
            else:
                color = ACCENT_GREEN
            
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.PenStyle.NoPen)
            
            y = self.height() - margin - bar_height
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_height), 4, 4)
            
            # Date label
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.setFont(QFont("Segoe UI", 8))
            fecha = item.get("fecha", "")
            if fecha and len(fecha) >= 5:
                fecha_corta = fecha[5:]  # MM-DD
                painter.drawText(int(x), int(self.height() - margin + 20), 
                               int(bar_width), 20, Qt.AlignmentFlag.AlignCenter, fecha_corta)
            
            # Value label
            painter.setPen(QColor(ACCENT_GREEN))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(int(x), int(y - 10), int(bar_width), 20, 
                           Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                           f"${value:.2f}")


class TelemetryDashboard(QWidget):
    """
    Dashboard de Telemetría con diseño Dark Aesthetic.
    
    Muestra:
    - KPI Cards: Gasto Total, Tokens, Peticiones
    - Gráfico de Barras: Gasto últimos 7 días
    - Tabla: Registros recientes
    """

    def __init__(self, db_manager, parent=None) -> None:
        super().__init__(parent)
        self.db = db_manager
        self.setStyleSheet(f"background-color: {DARK_BG};")
        
        self._setup_ui()
        self._refresh_data()
        
        # Auto-refresh every 30 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_data)
        self.timer.start(30000)

    def _setup_ui(self) -> None:
        """Configura la interfaz del dashboard."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Title
        title = QLabel("📊 Telemetría y Observabilidad")
        title.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: 18pt;
            font-weight: bold;
            padding: 8px;
        """)
        main_layout.addWidget(title)
        
        # KPI Cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)
        
        self.card_gasto = KPICard("Gasto Total (Mes)", "$0.00", "💵")
        self.card_tokens = KPICard("Tokens Consumidos", "0", "🔢")
        self.card_peticiones = KPICard("Peticiones API", "0", "📡")
        
        kpi_layout.addWidget(self.card_gasto)
        kpi_layout.addWidget(self.card_tokens)
        kpi_layout.addWidget(self.card_peticiones)
        
        main_layout.addLayout(kpi_layout)
        
        # Bar Chart
        chart_label = QLabel("📈 Gasto Últimos 7 Días")
        chart_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11pt; padding: 8px;")
        main_layout.addWidget(chart_label)
        
        self.chart_widget = BarChartWidget([])
        main_layout.addWidget(self.chart_widget)
        
        # Data Table
        table_label = QLabel("📋 Registros Recientes")
        table_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11pt; padding: 8px;")
        main_layout.addWidget(table_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Fecha/Hora", "Operación", "Modelo", "Input", "Output", "Costo USD"
        ])
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                gridline-color: {BORDER_COLOR};
            }}
            QTableWidget::item {{
                padding: 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {BORDER_COLOR};
            }}
            QHeaderView::section {{
                background-color: {CARD_BG};
                color: {TEXT_PRIMARY};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
        """)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        main_layout.addWidget(self.table, stretch=1)

    def _refresh_data(self) -> None:
        """Actualiza todos los datos del dashboard."""
        if not self.db:
            return
        
        # KPI Cards
        gasto_total = self.db.obtener_gasto_total_mes()
        self.card_gasto.findChild(QLabel, "", Qt.FindChildOption.FindDirectChildrenOnly)\
            .setText(f"${gasto_total:.2f}")
        
        tokens = self.db.obtener_total_tokens()
        self.card_tokens.findChild(QLabel, "", Qt.FindChildOption.FindDirectChildrenOnly)\
            .setText(f"{tokens['total']:,}")
        
        peticiones = self.db.obtener_total_peticiones()
        self.card_peticiones.findChild(QLabel, "", Qt.FindChildOption.FindDirectChildrenOnly)\
            .setText(str(peticiones))
        
        # Bar Chart
        gasto_7dias = self.db.obtener_gasto_ultimos_7_dias()
        self.chart_widget.set_data(gasto_7dias)
        
        # Data Table
        self._update_table()

    def _update_table(self) -> None:
        """Actualiza la tabla de registros recientes."""
        registros = self.db.obtener_telemetria_reciente(20)
        
        self.table.setRowCount(len(registros))
        
        for i, row in enumerate(registros):
            # Fecha
            timestamp = row.get("timestamp", "")
            if timestamp and len(timestamp) > 16:
                timestamp = timestamp[:16].replace("T", " ")
            item = QTableWidgetItem(timestamp)
            item.setForeground(QColor(TEXT_SECONDARY))
            self.table.setItem(i, 0, item)
            
            # Operación
            operacion = row.get("tipo_operacion", "N/A")
            item = QTableWidgetItem(operacion)
            item.setForeground(QColor(TEXT_PRIMARY))
            self.table.setItem(i, 1, item)
            
            # Modelo
            modelo = row.get("modelo_usado", "N/A")
            item = QTableWidgetItem(modelo)
            item.setForeground(QColor(ACCENT_BLUE))
            self.table.setItem(i, 2, item)
            
            # Input Tokens
            input_tokens = row.get("input_tokens", 0)
            item = QTableWidgetItem(f"{input_tokens:,}")
            item.setForeground(QColor(TEXT_SECONDARY))
            self.table.setItem(i, 3, item)
            
            # Output Tokens
            output_tokens = row.get("output_tokens", 0)
            item = QTableWidgetItem(f"{output_tokens:,}")
            item.setForeground(QColor(TEXT_SECONDARY))
            self.table.setItem(i, 4, item)
            
            # Costo
            costo = row.get("costo_total_usd", 0.0)
            item = QTableWidgetItem(f"${costo:.4f}")
            item.setForeground(QColor(ACCENT_GREEN if costo > 0 else TEXT_SECONDARY))
            self.table.setItem(i, 5, item)
        
        # Adjust column widths
        self.table.resizeColumnsToContents()