"""
Panel de Telemetría para ChefChat Pro

Observabilidad y Telemetría en Tiempo Real
- Tarjetas KPI: Gasto Total, Tokens, Peticiones
- Tabla de Datos: Registros recientes
"""

from typing import Dict
# pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QFrame, QSizePolicy, QHeaderView
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor

from data.db_manager import DatabaseManager


# =============================================================================
# DICCIONARIO DE PRECIOS (USD por 1M tokens)
# =============================================================================

PRICING = {
    "minimax-2.7b": {"input": 0.14, "output": 0.28},
    "openrouter/auto": {"input": 0.10, "output": 0.20},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-coder": {"input": 0.14, "output": 0.28},
    "gemini-pro": {"input": 0.50, "output": 1.50},
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.30},
    "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "big-pickle": {"input": 0.00, "output": 0.00},
    "open-code-v1": {"input": 0.00, "output": 0.00},
    "code-assistant": {"input": 0.00, "output": 0.00},
    "default": {"input": 1.00, "output": 3.00},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING.get(model) or PRICING["default"]
    input_cost = (input_tokens / 1_000_000.0) * pricing["input"]
    output_cost = (output_tokens / 1_000_000.0) * pricing["output"]
    return round(input_cost + output_cost, 6)


# =============================================================================
# TEMAS: colors for dark and light mode
# =============================================================================

DARK = {
    "bg": "#0f172a",
    "card": "#1e293b",
    "card_alt": "#1a2744",
    "text": "#f5f5f5",
    "text_sec": "#94a3b8",
    "accent": "#3B82F6",
    "accent_green": "#deff9a",
    "border": "#334155",
}

LIGHT = {
    "bg": "#F1F5F9",
    "card": "#FFFFFF",
    "card_alt": "#F1F5F9",
    "text": "#0F172A",
    "text_sec": "#475569",
    "accent": "#2563EB",
    "accent_green": "#16A34A",
    "border": "#CBD5E1",
}


class KPICard(QFrame):
    def __init__(self, title: str, value: str, icon: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(120)
        self.title_label = QLabel(f"{icon} {title}")
        self.value_label = QLabel(value)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def apply_theme(self, theme: Dict[str, str]) -> None:
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background-color: {theme["card"]};
                border-radius: 12px;
                padding: 16px;
                border: 1px solid {theme["border"]};
            }}
        """)
        self.title_label.setStyleSheet(f"""
            color: {theme["text_sec"]};
            font-size: 10pt;
            font-weight: 500;
        """)
        self.value_label.setStyleSheet(f"""
            color: {theme["accent"]};
            font-size: 24pt;
            font-weight: bold;
        """)


class TelemetryDashboard(QWidget):
    """Dashboard de telemetría con KPIs y tabla de registros recientes."""
    def __init__(self, db: DatabaseManager, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setObjectName("telemetryDashboard")
        self._is_dark = True

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.title = QLabel("📊 Telemetría y Observabilidad")
        main_layout.addWidget(self.title)

        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)
        self.kpi_costo = KPICard("Gasto Total (Mes)", "$0.00", "💰")
        self.kpi_tokens = KPICard("Tokens Totales", "0", "🔤")
        self.kpi_peticiones = KPICard("Peticiones API", "0", "📡")
        kpi_layout.addWidget(self.kpi_costo)
        kpi_layout.addWidget(self.kpi_tokens)
        kpi_layout.addWidget(self.kpi_peticiones)
        main_layout.addLayout(kpi_layout, stretch=1)

        # Table
        self.table_label = QLabel("📋 Registros Recientes")
        main_layout.addWidget(self.table_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Modelo", "Input Tokens", "Output Tokens",
            "Costo (USD)", "Operación"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        v_header = self.table.verticalHeader()
        if v_header is not None:
            v_header.setVisible(False)
        main_layout.addWidget(self.table, stretch=8)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_refresh = QLabel("🔄 Actualizar cada 30s")
        btn_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(btn_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(30000)

        self.apply_theme(True)
        self.refresh()

    def apply_theme(self, is_dark: bool) -> None:
        self._is_dark = is_dark
        theme = DARK if is_dark else LIGHT

        self.setStyleSheet(f"""
            QWidget#telemetryDashboard {{
                background-color: {theme["bg"]};
            }}
        """)

        self.title.setStyleSheet(f"""
            color: {theme["text"]};
            font-size: 18pt;
            font-weight: bold;
            padding: 8px 0;
        """)

        self.table_label.setStyleSheet(f"""
            color: {theme["text"]};
            font-size: 14pt;
            font-weight: bold;
            padding: 8px 0;
        """)

        self.btn_refresh.setStyleSheet(f"""
            color: {theme["text_sec"]};
            font-size: 9pt;
            padding: 4px 12px;
        """)

        if is_dark:
            table_qss = f"""
                QTableWidget {{
                    background-color: {theme["card"]};
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 8px;
                    gridline-color: {theme["border"]};
                    font-size: 10pt;
                }}
                QTableWidget::item {{
                    padding: 6px 8px;
                }}
                QTableWidget::item:alternate {{
                    background-color: #1a2744;
                }}
                QHeaderView::section {{
                    background-color: {DARK["bg"]};
                    color: {DARK["accent"]};
                    padding: 6px;
                    border: 1px solid {DARK["border"]};
                    font-weight: bold;
                }}
            """
        else:
            table_qss = f"""
                QTableWidget {{
                    background-color: {theme["card"]};
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 8px;
                    gridline-color: {theme["border"]};
                    font-size: 10pt;
                    selection-background-color: {theme["accent"]};
                    selection-color: #FFFFFF;
                }}
                QTableWidget::item {{
                    padding: 6px 8px;
                }}
                QTableWidget::item:alternate {{
                    background-color: {theme["card_alt"]};
                }}
                QHeaderView::section {{
                    background-color: #E2E8F0;
                    color: #0F172A;
                    font-weight: bold;
                    border: none;
                    border-right: 1px solid {theme["border"]};
                    border-bottom: 2px solid {theme["accent"]};
                    padding: 6px;
                }}
            """

        self.table.setStyleSheet(table_qss)
        if style := self.table.style():
            style.unpolish(self.table)
            style.polish(self.table)

        self.kpi_costo.apply_theme(theme)
        self.kpi_tokens.apply_theme(theme)
        self.kpi_peticiones.apply_theme(theme)

    def refresh(self) -> None:
        if not self.db:
            return
        try:
            gasto = self.db.obtener_gasto_total_mes()
            self.kpi_costo.value_label.setText(f"${gasto:.2f}")

            tokens = self.db.obtener_total_tokens()
            self.kpi_tokens.value_label.setText(f"{tokens['total']:,}")

            peticiones = self.db.obtener_total_peticiones()
            self.kpi_peticiones.value_label.setText(f"{peticiones:,}")

            registros = self.db.obtener_telemetria_reciente(50)
            self.table.setRowCount(len(registros))
            theme = DARK if self._is_dark else LIGHT
            for row_idx, reg in enumerate(registros):
                ts = str(reg.get("timestamp", ""))
                if len(ts) > 16:
                    ts = ts[:16].replace("T", " ")
                item_ts = QTableWidgetItem(ts)
                item_ts.setForeground(QColor(theme["text_sec"]))
                self.table.setItem(row_idx, 0, item_ts)

                modelo = str(reg.get("modelo_usado", ""))
                item_m = QTableWidgetItem(modelo)
                item_m.setForeground(QColor(theme["accent"]))
                self.table.setItem(row_idx, 1, item_m)

                inp = reg.get("input_tokens", 0)
                item_in = QTableWidgetItem(f"{inp:,}")
                item_in.setForeground(QColor(theme["text_sec"]))
                self.table.setItem(row_idx, 2, item_in)

                out = reg.get("output_tokens", 0)
                item_out = QTableWidgetItem(f"{out:,}")
                item_out.setForeground(QColor(theme["text_sec"]))
                self.table.setItem(row_idx, 3, item_out)

                costo = reg.get("costo_total_usd", 0.0)
                item_c = QTableWidgetItem(f"${costo:.4f}")
                item_c.setForeground(QColor(theme["accent_green"] if costo > 0 else theme["text_sec"]))
                self.table.setItem(row_idx, 4, item_c)

                op = str(reg.get("tipo_operacion", ""))
                item_op = QTableWidgetItem(op)
                item_op.setForeground(QColor(theme["text"]))
                self.table.setItem(row_idx, 5, item_op)

            self.table.resizeRowsToContents()
            if header := self.table.horizontalHeader():
                header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
                header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            print(f"TelemetryDashboard refresh error: {e}")
