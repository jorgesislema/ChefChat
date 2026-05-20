"""Fallback dashboard export using openpyxl + matplotlib (no Excel COM required)."""
import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Tuple

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart.bar_chart import BarChart
    from openpyxl.chart.line_chart import LineChart
    from openpyxl.chart.pie_chart import PieChart
    from openpyxl.chart.reference import Reference
    from openpyxl.chart.series import DataPoint
    from openpyxl.chart.label import DataLabelList
    from openpyxl.drawing.image import Image
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ── Color Palette ──
COLORS = {
    "primary": "2C3E50",
    "secondary": "34495E",
    "accent": "3498DB",
    "success": "2ECC71",
    "warning": "F39C12",
    "danger": "E74C3C",
    "gray": "95A5A6",
    "light_gray": "ECF0F1",
    "white": "FFFFFF",
}

CHART_COLORS = ["3498DB", "2ECC71", "F39C12", "E74C3C", "9B59B6", "1ABC9C", "E67E22", "34495E"]


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _create_styled_cell(value, bold=False, size=11, color=COLORS["primary"], bg_color=None, alignment="left"):
    """Create a cell with styling."""
    cell = openpyxl.cell.Cell(worksheet=None, row=0, column=0, value=value)
    cell.font = Font(bold=bold, size=size, color=color)
    if bg_color:
        cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
    cell.alignment = Alignment(horizontal=alignment, vertical="center")
    return cell


def _add_chart_from_matplotlib(ws, fig, row: int, col: int, width: int = 10, height: int = 8) -> str:
    """Save matplotlib figure as image and add to worksheet. Returns image path."""
    if not HAS_MATPLOTLIB:
        return ""
    
    img_path = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    fig.savefig(img_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    
    if os.path.exists(img_path):
        img = Image(img_path)
        img.width = width * 10  # Approximate pixel width
        img.height = height * 10  # Approximate pixel height
        ws.add_image(img, ws.cell(row=row, column=col).coordinate)
        return img_path
    return ""


def _create_bar_chart_matplotlib(labels: List[str], values: List[float], title: str, color: str = COLORS["accent"]) -> plt.Figure:
    """Create a bar chart using matplotlib."""
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(labels, values, color=f"#{color}", edgecolor='white', linewidth=0.5)
    ax.set_title(title, fontsize=14, fontweight='bold', color=f"#{COLORS['primary']}")
    ax.set_ylabel("Cantidad", fontsize=11, color=f"#{COLORS['secondary']}")
    ax.grid(axis='y', alpha=0.3, color=f"#{COLORS['gray']}")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{val:.1f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    return fig


def _create_pie_chart_matplotlib(labels: List[str], values: List[float], title: str) -> plt.Figure:
    """Create a pie chart using matplotlib."""
    fig, ax = plt.subplots(figsize=(8, 8))
    colors = [f"#{c}" for c in CHART_COLORS[:len(labels)]]
    wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%',
                                       colors=colors, startangle=90,
                                       textprops={'fontsize': 10})
    ax.set_title(title, fontsize=14, fontweight='bold', color=f"#{COLORS['primary']}", pad=20)
    plt.tight_layout()
    return fig


def _create_line_chart_matplotlib(labels: List[str], values: List[float], title: str, color: str = COLORS["accent"]) -> plt.Figure:
    """Create a line chart using matplotlib."""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(labels, values, marker='o', linewidth=2, markersize=6, color=f"#{color}")
    ax.fill_between(range(len(labels)), values, alpha=0.1, color=f"#{color}")
    ax.set_title(title, fontsize=14, fontweight='bold', color=f"#{COLORS['primary']}")
    ax.set_ylabel("Cantidad", fontsize=11, color=f"#{COLORS['secondary']}")
    ax.grid(axis='both', alpha=0.3, color=f"#{COLORS['gray']}")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add value labels
    for i, val in enumerate(values):
        ax.annotate(f'{val:.1f}', (i, val), textcoords="offset points",
                    xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    return fig


def export_dashboard_fallback(db_path: str, dias: int = 7, tipo: str = "sobrantes") -> str:
    """Export dashboard using openpyxl + matplotlib fallback.
    
    Args:
        db_path: Path to SQLite database
        dias: Number of days to include
        tipo: Dashboard type ("sobrantes", "mermas", "personal")
    
    Returns:
        Path to generated Excel file
    """
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl is required for dashboard export fallback. Install with: pip install openpyxl")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # ── Create workbook ──
    wb = openpyxl.Workbook()
    ws_data = wb.active
    ws_data.title = "Datos"
    ws_chart = wb.create_sheet("Dashboard")
    
    # ── Styles ──
    header_font = Font(bold=True, size=11, color=COLORS["white"])
    header_fill = PatternFill(start_color=COLORS["secondary"], end_color=COLORS["secondary"], fill_type="solid")
    title_font = Font(bold=True, size=16, color=COLORS["primary"])
    kpi_label_font = Font(bold=True, size=10, color=COLORS["gray"])
    kpi_value_font = Font(bold=True, size=24, color=COLORS["primary"])
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    if tipo == "sobrantes":
        return _export_sobrantes_dashboard(conn, wb, ws_data, ws_chart, dias,
                                          header_font, header_fill, title_font,
                                          kpi_label_font, kpi_value_font, thin_border)
    elif tipo == "mermas":
        return _export_mermas_dashboard(conn, wb, ws_data, ws_chart, dias,
                                       header_font, header_fill, title_font,
                                       kpi_label_font, kpi_value_font, thin_border)
    elif tipo == "personal":
        return _export_personal_dashboard(conn, wb, ws_data, ws_chart,
                                         header_font, header_fill, title_font,
                                         kpi_label_font, kpi_value_font, thin_border)
    else:
        raise ValueError(f"Unknown dashboard type: {tipo}")


def _export_sobrantes_dashboard(conn, wb, ws_data, ws_chart, dias, header_font, header_fill, title_font, kpi_label_font, kpi_value_font, thin_border) -> str:
    """Export sobrantes dashboard."""
    # ── Query data ──
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, t.nombre_completo
        FROM SobrantesReutilizables s
        LEFT JOIN Trabajadores t ON s.id_empleado = t.id_empleado
        WHERE s.fecha_registro >= date('now', ? || ' days')
        ORDER BY s.fecha_registro DESC, s.turno
    """, (f"-{dias}",))
    rows = cursor.fetchall()
    
    # ── Data Sheet ──
    headers = ["Fecha", "Turno", "Producto", "Cantidad", "Unidad", "Destino", "Dias Reutilizacion", "Empleado"]
    for j, h in enumerate(headers, 1):
        cell = ws_data.cell(row=1, column=j, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    
    for i, row in enumerate(rows, 2):
        ws_data.cell(row=i, column=1, value=row["fecha_registro"]).border = thin_border
        ws_data.cell(row=i, column=2, value=row["turno"] or "No especificado").border = thin_border
        ws_data.cell(row=i, column=3, value=row["producto_sopro"]).border = thin_border
        ws_data.cell(row=i, column=4, value=row["cantidad"]).border = thin_border
        ws_data.cell(row=i, column=5, value=row["unidad"]).border = thin_border
        ws_data.cell(row=i, column=6, value=row["destino_actual"]).border = thin_border
        ws_data.cell(row=i, column=7, value=row["dias_reutilizacion_sanitaria"]).border = thin_border
        ws_data.cell(row=i, column=8, value=row["nombre_completo"] or "").border = thin_border
    
    # Auto-fit columns (approximate)
    for col in ws_data.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 30)
        ws_data.column_dimensions[column].width = adjusted_width
    
    # ── Dashboard Sheet ──
    # Title
    ws_chart.merge_cells('A1:H1')
    title_cell = ws_chart.cell(row=1, column=1, value=f"DASHBOARD DE SOBRANTES REUTILIZABLES (ultimos {dias} dias)")
    title_cell.font = title_font
    title_cell.alignment = Alignment(horizontal="center")
    
    # KPIs
    total_kilos = sum(r["cantidad"] for r in rows) if rows else 0
    total_registros = len(rows)
    desperdicio_kilos = sum(r["cantidad"] for r in rows if r["destino_actual"] == "desperdicio")
    reutilizado = sum(1 for r in rows if r["destino_actual"] == "reutilizado")
    
    kpis = [
        ("Total Kilos", f"{total_kilos:.1f}"),
        ("Registros", str(total_registros)),
        ("Desperdicio (kg)", f"{desperdicio_kilos:.1f}"),
        ("Reutilizados", str(reutilizado)),
    ]
    
    for j, (label, val) in enumerate(kpis, 1):
        col = j * 2 - 1
        ws_chart.cell(row=3, column=col, value=label).font = kpi_label_font
        ws_chart.cell(row=4, column=col, value=val).font = kpi_value_font
    
    # ── Charts ──
    image_paths = []
    if HAS_MATPLOTLIB and rows:
        # Chart 1: Desperdicio por dia
        desperdicio_dia: dict[str, float] = {}
        for r in rows:
            dia = r["fecha_registro"]
            cant = r["cantidad"]
            desperdicio_dia[dia] = desperdicio_dia.get(dia, 0) + (cant if r["destino_actual"] == "desperdicio" else 0)
        
        if desperdicio_dia:
            labels = sorted(desperdicio_dia.keys())
            values = [desperdicio_dia[d] for d in labels]
            fig = _create_bar_chart_matplotlib(labels, values, f"Desperdicio por Dia (kg) - Ultimos {dias} dias")
            img_path = _add_chart_from_matplotlib(ws_chart, fig, 6, 1, width=12, height=8)
            if img_path:
                image_paths.append(img_path)
        
        # Chart 2: Destino distribution (pie)
        destino_counts: dict[str, int] = {}
        for r in rows:
            dest = r["destino_actual"] or "otro"
            destino_counts[dest] = destino_counts.get(dest, 0) + 1
        
        if destino_counts:
            labels = list(destino_counts.keys())
            values = list(destino_counts.values())
            fig = _create_pie_chart_matplotlib(labels, values, "Distribucion por Destino")
            img_path = _add_chart_from_matplotlib(ws_chart, fig, 6, 10, width=10, height=8)
            if img_path:
                image_paths.append(img_path)
        
        # Chart 3: Por turno
        turno_kilos: dict[str, float] = {}
        for r in rows:
            turno = r["turno"] or "No especificado"
            turno_kilos[turno] = turno_kilos.get(turno, 0) + r["cantidad"]
        
        if turno_kilos:
            labels = list(turno_kilos.keys())
            values = list(turno_kilos.values())
            fig = _create_bar_chart_matplotlib(labels, values, "Kilos por Turno", color=COLORS["success"])
            img_path = _add_chart_from_matplotlib(ws_chart, fig, 16, 1, width=12, height=8)
            if img_path:
                image_paths.append(img_path)
    
    # ── Save ──
    filename = f"dashboard_sobrantes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(os.path.dirname(conn.execute("PRAGMA database_list").fetchone()[1]) or ".", filename)
    wb.save(filepath)
    
    # Clean up temp images
    for img_path in image_paths:
        try:
            os.remove(img_path)
        except OSError:
            pass
    
    conn.close()
    return filepath


def _export_mermas_dashboard(conn, wb, ws_data, ws_chart, dias, header_font, header_fill, title_font, kpi_label_font, kpi_value_font, thin_border) -> str:
    """Export mermas dashboard."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, c.nombre_producto, c.categoria
        FROM Mermas m
        LEFT JOIN Catalogo c ON m.id_producto = c.id_producto
        WHERE m.fecha_registro >= date('now', ? || ' days')
        ORDER BY m.fecha_registro DESC
    """, (f"-{dias}",))
    rows = cursor.fetchall()
    
    # ── Data Sheet ──
    headers = ["Fecha", "Producto", "Categoria", "Cantidad", "Unidad", "Motivo", "Costo Estimado"]
    for j, h in enumerate(headers, 1):
        cell = ws_data.cell(row=1, column=j, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    
    for i, row in enumerate(rows, 2):
        ws_data.cell(row=i, column=1, value=row["fecha_registro"]).border = thin_border
        ws_data.cell(row=i, column=2, value=row["nombre_producto"] or "N/A").border = thin_border
        ws_data.cell(row=i, column=3, value=row["categoria"] or "N/A").border = thin_border
        ws_data.cell(row=i, column=4, value=row["cantidad"]).border = thin_border
        ws_data.cell(row=i, column=5, value=row["unidad"]).border = thin_border
        ws_data.cell(row=i, column=6, value=row["motivo"] or "").border = thin_border
        ws_data.cell(row=i, column=7, value=row["costo_estimado"] or 0).border = thin_border
    
    for col in ws_data.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 30)
        ws_data.column_dimensions[column].width = adjusted_width
    
    # ── Dashboard Sheet ──
    ws_chart.merge_cells('A1:G1')
    title_cell = ws_chart.cell(row=1, column=1, value=f"DASHBOARD DE MERMAS (ultimos {dias} dias)")
    title_cell.font = title_font
    title_cell.alignment = Alignment(horizontal="center")
    
    # KPIs
    total_kilos = sum(r["cantidad"] for r in rows) if rows else 0
    total_costo = sum(r["costo_estimado"] or 0 for r in rows)
    total_registros = len(rows)
    
    kpis = [
        ("Total Kilos", f"{total_kilos:.1f}"),
        ("Costo Total", f"${total_costo:.2f}"),
        ("Registros", str(total_registros)),
    ]
    
    for j, (label, val) in enumerate(kpis, 1):
        col = j * 2 - 1
        ws_chart.cell(row=3, column=col, value=label).font = kpi_label_font
        ws_chart.cell(row=4, column=col, value=val).font = kpi_value_font
    
    # ── Charts ──
    image_paths = []
    if HAS_MATPLOTLIB and rows:
        # Chart 1: Mermas por dia
        merma_dia: dict[str, float] = {}
        for r in rows:
            dia = r["fecha_registro"]
            merma_dia[dia] = merma_dia.get(dia, 0) + r["cantidad"]
        
        if merma_dia:
            labels = sorted(merma_dia.keys())
            values = [merma_dia[d] for d in labels]
            fig = _create_line_chart_matplotlib(labels, values, f"Mermas por Dia (kg) - Ultimos {dias} dias", color=COLORS["danger"])
            img_path = _add_chart_from_matplotlib(ws_chart, fig, 6, 1, width=12, height=8)
            if img_path:
                image_paths.append(img_path)
        
        # Chart 2: Por motivo
        motivo_kilos: dict[str, float] = {}
        for r in rows:
            motivo = r["motivo"] or "No especificado"
            motivo_kilos[motivo] = motivo_kilos.get(motivo, 0) + r["cantidad"]
        
        if motivo_kilos:
            labels = list(motivo_kilos.keys())
            values = list(motivo_kilos.values())
            fig = _create_pie_chart_matplotlib(labels, values, "Distribucion por Motivo")
            img_path = _add_chart_from_matplotlib(ws_chart, fig, 6, 10, width=10, height=8)
            if img_path:
                image_paths.append(img_path)
    
    # ── Save ──
    filename = f"dashboard_mermas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(os.path.dirname(conn.execute("PRAGMA database_list").fetchone()[1]) or ".", filename)
    wb.save(filepath)
    
    # Clean up temp images
    for img_path in image_paths:
        try:
            os.remove(img_path)
        except OSError:
            pass
    
    conn.close()
    return filepath


def _export_personal_dashboard(conn, wb, ws_data, ws_chart, header_font, header_fill, title_font, kpi_label_font, kpi_value_font, thin_border) -> str:
    """Export personal dashboard."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Trabajadores ORDER BY nombre_completo")
    rows = cursor.fetchall()
    
    # ── Data Sheet ──
    headers = ["ID", "Nombre", "Cargo", "Turno", "Telefono", "Estado", "Tipo Contrato"]
    for j, h in enumerate(headers, 1):
        cell = ws_data.cell(row=1, column=j, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    
    for i, row in enumerate(rows, 2):
        ws_data.cell(row=i, column=1, value=row["id_trabajador"]).border = thin_border
        ws_data.cell(row=i, column=2, value=row["nombre_completo"]).border = thin_border
        ws_data.cell(row=i, column=3, value=row["cargo"] or "").border = thin_border
        ws_data.cell(row=i, column=4, value=row["turno"] or "").border = thin_border
        ws_data.cell(row=i, column=5, value=row["telefono"] or "").border = thin_border
        ws_data.cell(row=i, column=6, value=row.get("estado", "activo")).border = thin_border
        ws_data.cell(row=i, column=7, value=row.get("tipo_contrato", "fijo")).border = thin_border
    
    for col in ws_data.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 30)
        ws_data.column_dimensions[column].width = adjusted_width
    
    # ── Dashboard Sheet ──
    ws_chart.merge_cells('A1:G1')
    title_cell = ws_chart.cell(row=1, column=1, value="DASHBOARD DE PERSONAL")
    title_cell.font = title_font
    title_cell.alignment = Alignment(horizontal="center")
    
    # KPIs
    total_trabajadores = len(rows)
    activos = sum(1 for r in rows if r.get("estado", "activo") == "activo")
    reposo = total_trabajadores - activos
    fijos = sum(1 for r in rows if r.get("tipo_contrato", "fijo") == "fijo")
    temporales = total_trabajadores - fijos
    
    kpis = [
        ("Total Trabajadores", str(total_trabajadores)),
        ("Activos", str(activos)),
        ("En Reposo", str(reposo)),
        ("Fijos", str(fijos)),
        ("Temporales", str(temporales)),
    ]
    
    for j, (label, val) in enumerate(kpis, 1):
        col = j * 2 - 1
        ws_chart.cell(row=3, column=col, value=label).font = kpi_label_font
        ws_chart.cell(row=4, column=col, value=val).font = kpi_value_font
    
    # ── Charts ──
    image_paths = []
    if HAS_MATPLOTLIB and rows:
        # Chart 1: Por turno
        turno_counts: dict[str, int] = {}
        for r in rows:
            turno = r["turno"] or "No especificado"
            turno_counts[turno] = turno_counts.get(turno, 0) + 1
        
        if turno_counts:
            labels = list(turno_counts.keys())
            values = list(turno_counts.values())
            fig = _create_pie_chart_matplotlib(labels, values, "Distribucion por Turno")
            img_path = _add_chart_from_matplotlib(ws_chart, fig, 6, 1, width=10, height=8)
            if img_path:
                image_paths.append(img_path)
        
        # Chart 2: Por cargo
        cargo_counts: dict[str, int] = {}
        for r in rows:
            cargo = r["cargo"] or "No especificado"
            cargo_counts[cargo] = cargo_counts.get(cargo, 0) + 1
        
        if cargo_counts:
            labels = list(cargo_counts.keys())
            values = list(cargo_counts.values())
            fig = _create_bar_chart_matplotlib(labels, values, "Distribucion por Cargo", color=COLORS["warning"])
            img_path = _add_chart_from_matplotlib(ws_chart, fig, 6, 10, width=12, height=8)
            if img_path:
                image_paths.append(img_path)
        
        # Chart 3: Activo vs Reposo
        fig = _create_pie_chart_matplotlib(["Activos", "En Reposo"], [activos, reposo], "Estado del Personal")
        img_path = _add_chart_from_matplotlib(ws_chart, fig, 16, 1, width=10, height=8)
        if img_path:
            image_paths.append(img_path)
        
        # Chart 4: Fijo vs Temporal
        fig = _create_pie_chart_matplotlib(["Fijos", "Temporales"], [fijos, temporales], "Tipo de Contrato")
        img_path = _add_chart_from_matplotlib(ws_chart, fig, 16, 10, width=10, height=8)
        if img_path:
            image_paths.append(img_path)
    
    # ── Save ──
    filename = f"dashboard_personal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(os.path.dirname(conn.execute("PRAGMA database_list").fetchone()[1]) or ".", filename)
    wb.save(filepath)
    
    # Clean up temp images
    for img_path in image_paths:
        try:
            os.remove(img_path)
        except OSError:
            pass
    
    conn.close()
    return filepath
