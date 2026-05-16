"""
Herramientas Operativas Multi-Agente para ChefChat Pro

Arquitectura de Agentes:
├── Agente Inventario: caducidad, stock, compras
├── Agente Recetas: búsqueda, escalado, sugerencias
├── Agente Menú: planificación, eventos, anti-desperdicio
└── Agente Incidencias: bitácora, problemas
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import Tool
from data.db_manager import DatabaseManager
import json

# Pricing dictionary for cost calculation (USD per 1M tokens)
# Source: OpenRouter, DeepSeek, official pricing pages
PRICING = {
    # OpenRouter models
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "o1-preview": {"input": 15.0, "output": 60.0},
    "o1-mini": {"input": 3.0, "output": 12.0},
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "gemini-2.0-flash": {"input": 0.1, "output": 0.4},
    "gemini-pro": {"input": 0.5, "output": 1.5},
    # DeepSeek models
    "deepseek-chat": {"input": 0.27, "output": 1.1},
    "deepseek-coder": {"input": 0.27, "output": 1.1},
    # OpenCode models (FREE)
    "big-pickle": {"input": 0.0, "output": 0.0},
    "open-code-v1": {"input": 0.0, "output": 0.0},
    "code-assistant": {"input": 0.0, "output": 0.0},
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculates USD cost for API call based on model pricing."""
    # Try exact match first
    if model in PRICING:
        pricing = PRICING[model]
        return (input_tokens / 1_000_000 * pricing["input"]) + (output_tokens / 1_000_000 * pricing["output"])
    
    # Fallback: check if model name contains known model
    model_lower = model.lower()
    for known_model, pricing in PRICING.items():
        if known_model in model_lower:
            return (input_tokens / 1_000_000 * pricing["input"]) + (output_tokens / 1_000_000 * pricing["output"])
    
    # Unknown model: return 0.0 (FREE)
    return 0.0


def _obtener_conexion(db: DatabaseManager):
    """Obtiene una conexión SQLite directa (sin context manager)."""
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    return conn

def crear_herramientas_operativas(db: DatabaseManager) -> List[Tool]:
    """Crea todas las herramientas operativas para LangChain."""
    
    # =========================================================================
    # AGENTE RECETAS
    # =========================================================================
    
    def _buscar_receta(nombre_o_id: str) -> str:
        """Busca receta por nombre o ID en SQLite."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            
            # Buscar en RecetasRAG (tabla correcta)
            cursor.execute("SELECT * FROM RecetasRAG WHERE id_receta = ?", (nombre_o_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("SELECT * FROM RecetasRAG WHERE LOWER(nombre) LIKE LOWER(?)", (f"%{nombre_o_id}%",))
                row = cursor.fetchone()
            if not row:
                conn.close()
                return f"Receta '{nombre_o_id}' no encontrada."
            
            receta = dict(row)
            ingredientes = json.loads(receta["ingredientes_json"])
            
            # Calcular comensales base (default 4 si no hay datos)
            comensales_base = 4
            
            lineas = [f"Receta: {receta['nombre']} (ID: {receta['id_receta']})",
                     f"Categoria: {receta['categoria']} | Tiempo: {receta['tiempo_prep']} min | Costo: ${receta['costo']:.2f}",
                     f"Comensales base: {comensales_base}",
                     "", "Ingredientes:"]
            for ing in ingredientes:
                # Parsear ingredientes estructurados: "cantidad|unidad|nombre"
                if isinstance(ing, str) and '|' in ing:
                    parts = ing.split('|')
                    if len(parts) >= 3:
                        cantidad, unidad, nombre = parts[0], parts[1], parts[2]
                        lineas.append(f"  - {cantidad} {unidad} {nombre}")
                elif isinstance(ing, dict):
                    lineas.append(f"  - {ing.get('cantidad', '')} {ing.get('unidad', '')} {ing.get('nombre', '')}")
            if receta.get("alergenos"):
                lineas.append(f"\nAlergenos: {receta['alergenos']}")
            if receta.get("instrucciones"):
                lineas.append(f"\nInstrucciones: {receta['instrucciones']}")
            conn.close()
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    def _escalar_receta(receta_id: str, comensales: int) -> str:
        """Escala receta para N comensales."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            
            # Buscar en RecetasRAG (tabla correcta)
            cursor.execute("SELECT * FROM RecetasRAG WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)",
                          (receta_id, f"%{receta_id}%"))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return f"Receta '{receta_id}' no encontrada"
            
            receta = dict(row)
            ingredientes_raw = receta["ingredientes_json"]
            
            # Parsear ingredientes (puede ser JSON o string estructurado)
            try:
                ingredientes = json.loads(ingredientes_raw) if isinstance(ingredientes_raw, str) else ingredientes_raw
            except:
                ingredientes = []
            
            # Comensales base = 4 por defecto (estándar para recetas)
            comensales_orig = 4
            factor = comensales / comensales_orig
            
            lineas = [f"🍽️ Receta: {receta['nombre']} - ESCALADA",
                     f"📊 Comensales: {comensales_orig} → {comensales} (factor: {factor:.2f}x)",
                     "", "📝 Ingredientes ajustados:"]
            
            for ing in ingredientes:
                if isinstance(ing, dict):
                    cantidad_orig = float(ing.get('cantidad', 0))
                    cantidad_nueva = round(cantidad_orig * factor, 2)
                    lineas.append(f"  - {cantidad_nueva} {ing.get('unidad', '')} {ing.get('nombre', '')}")
                elif isinstance(ing, str) and '|' in ing:
                    # Formato: "cantidad|unidad|nombre"
                    parts = ing.split('|')
                    if len(parts) >= 3:
                        cantidad_orig = float(parts[0])
                        cantidad_nueva = round(cantidad_orig * factor, 2)
                        lineas.append(f"  - {cantidad_nueva} {parts[1]} {parts[2]}")
            
            lineas.append(f"\n💰 Costo estimado: ${receta['costo'] * factor:.2f} (original: ${receta['costo']:.2f})")
            lineas.append(f"⏱️ Tiempo prep: {receta['tiempo_prep']} min (no cambia con escalado)")
            conn.close()
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    def _sugerir_recetas_con_ingrediente(ingrediente: str) -> str:
        """Busca recetas que contienen un ingrediente específico."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            
            # Buscar en RecetasRAG (tabla correcta)
            cursor.execute("""
                SELECT nombre, categoria, tiempo_prep, costo, ingredientes_json
                FROM RecetasRAG
                WHERE LOWER(ingredientes_json) LIKE LOWER(?)
                LIMIT 10
            """, (f"%{ingrediente}%",))
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return f"No hay recetas con '{ingrediente}'"
            
            lineas = [f"🍳 Recetas con '{ingrediente}':"]
            for row in rows:
                lineas.append(f"  - {row[0]} ({row[1]}) - {row[2]} min, ${row[3]:.2f}")
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # AGENTE INVENTARIO
    # =========================================================================
    
    def _productos_por_caducar(dias: int = 3) -> str:
        """Lista productos que caducan en N dias."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nombre_producto, cantidad_actual, unidad, dias_restantes, categoria
                FROM vista_caducidad_activa
                WHERE dias_restantes >= 0 AND dias_restantes <= ?
                ORDER BY dias_restantes ASC
            """, (dias,))
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return f"No hay productos por caducar en {dias} dias."
            
            lineas = [f"CADUCAN EN {dias} DIAS:"]
            for row in rows:
                prioridad = "[URGENTE]" if row[3] <= 1 else "[PRONTO]" if row[3] <= 3 else "[OK]"
                lineas.append(f"{prioridad} {row[0]}: {row[1]} {row[2]} ({row[3]} dias) - {row[4]}")
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    def _verificar_stock_bajo(umbral: float = 10.0) -> str:
        """Verifica productos con stock bajo."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.nombre, SUM(l.cantidad_actual) as total, l.unidad
                FROM lotes_inventario l
                JOIN catalogo_inventario c ON l.producto_id = c.id_producto
                GROUP BY c.nombre, l.unidad
                HAVING total < ?
                ORDER BY total ASC
            """, (umbral,))
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return f"Todo el inventario esta sobre {umbral} unidades."
            
            lineas = ["STOCK BAJO:"]
            for row in rows:
                lineas.append(f"  [ALERTA] {row[0]}: {row[1]} {row[2]} (umbral: {umbral})")
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    def _registrar_uso_inventario(nombre_item: str, cantidad: float) -> str:
        """Registra uso de inventario (FEFO)."""
        try:
            resultado = db.registrar_uso_inventario(nombre_item, cantidad)
            return f"OK: {resultado}"
        except ValueError as e:
            return f"Advertencia: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # AGENTE MENU
    # =========================================================================
    
    def _menu_anti_desperdicio() -> str:
        """Sugiere menu para usar productos por caducar."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nombre_producto, cantidad_actual, unidad, dias_restantes
                FROM vista_caducidad_activa
                WHERE dias_restantes >= 0 AND dias_restantes <= 5
                ORDER BY dias_restantes ASC
                LIMIT 10
            """)
            productos = cursor.fetchall()
            conn.close()
            if not productos:
                return "No hay productos criticos. Inventario en buen estado."
            
            lineas = ["MENU ANTI-DESPERDICIO", "=" * 40, "",
                     "Productos a usar urgente:"]
            for prod in productos:
                lineas.append(f"  - {prod[0]}: {prod[1]} {prod[2]} ({prod[3]} dias)")
            
            lineas.extend(["", "Recetas sugeridas:"])
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            for prod in productos[:5]:
                nombre_corto = prod[0].lower().split()[0]
                cursor.execute("""
                    SELECT nombre, categoria, tiempo_prep FROM recetas
                    WHERE LOWER(ingredientes_json) LIKE ? LIMIT 3
                """, (f"%{nombre_corto}%",))
                recetas = cursor.fetchall()
                if recetas:
                    lineas.append(f"\n  Para {prod[0]}:")
                    for r in recetas:
                        lineas.append(f"    - {r[0]} ({r[1]}) - {r[2]} min")
            conn.close()
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    def _generar_lista_compras(recetas_csv: str, comensales: int = 1) -> str:
        """Genera lista de compras para evento."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            ids = [r.strip() for r in recetas_csv.split(",")]
            ingredientes_totales = {}
            
            for receta_id in ids:
                cursor.execute("""
                    SELECT nombre, ingredientes_json, comensales FROM recetas
                    WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)
                """, (receta_id, f"%{receta_id}%"))
                row = cursor.fetchone()
                if not row:
                    continue
                
                nombre_receta, ingredientes_json, comensales_base = row
                ingredientes = json.loads(ingredientes_json)
                factor = comensales / comensales_base if comensales_base > 0 else 1
                
                for ing in ingredientes:
                    key = f"{ing['nombre']}_{ing['unidad']}"
                    if key not in ingredientes_totales:
                        ingredientes_totales[key] = {"nombre": ing["nombre"], "cantidad": 0,
                                                     "unidad": ing["unidad"], "recetas": []}
                    ingredientes_totales[key]["cantidad"] += ing["cantidad"] * factor
                    ingredientes_totales[key]["recetas"].append(nombre_receta)
            
            conn.close()
            if not ingredientes_totales:
                return f"No se encontraron recetas: {recetas_csv}"
            
            lineas = ["LISTA DE COMPRAS - EVENTO", "=" * 40,
                     f"Comensales: {comensales}", f"Recetas: {', '.join(ids)}",
                     "", "Ingredientes:"]
            for ing in sorted(ingredientes_totales.values(), key=lambda x: x["nombre"]):
                lineas.append(f"  [ ] {ing['cantidad']:.2f} {ing['unidad']} {ing['nombre']}")
                lineas.append(f"      Para: {', '.join(set(ing['recetas']))}")
            
            lineas.extend(["", "Tips:",
                          "  1. Verifica inventario antes de comprar",
                          "  2. Usa productos proximos a caducar",
                          "  3. Agrega 10% margen de seguridad"])
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # AGENTE INCIDENCIAS
    # =========================================================================
    
    def _registrar_incidencia(categoria: str, descripcion: str) -> str:
        """Registra incidencia en bitacora."""
        try:
            id_reg = db.registrar_incidencia(categoria, descripcion)
            return f"OK: Incidencia registrada (ID: {id_reg}) - {categoria}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _analizar_rentabilidad() -> str:
        """Analiza rentabilidad del menu (matriz BCG)."""
        try:
            resultado = db.analizar_rentabilidad_menu()
            lineas = ["RENTABILIDAD DEL MENU", "=" * 40]
            for categoria in ["estrellas", "vacas", "interrogantes", "perros"]:
                items = resultado.get(categoria, [])
                if items:
                    icono = {"estrellas": "[STAR]", "vacas": "[CASH]", "interrogantes": "[?]", "perros": "[LOW]"}[categoria]
                    lineas.append(f"\n{icono} {categoria.upper()}:")
                    for item in items[:5]:
                        lineas.append(f"  - {item['nombre']}: {item['unidades_vendidas']} ventas, {item['margen_promedio']}% margen")
            lineas.extend(["", "=" * 40, resultado.get("resumen", "")])
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # LISTA DE HERRAMIENTAS
    # =========================================================================
    
    return [
        # Agente Recetas
        Tool(name="buscar_receta", func=_buscar_receta,
             description="Busca receta por nombre o ID. Input: nombre_o_id (str). Ej: 'Pato' o 'REC001'"),
        Tool(name="escalar_receta", func=_escalar_receta,
             description="Escala receta para N comensales. Input: receta_id, comensales. Ej: 'REC001', 50"),
        Tool(name="buscar_recetas_con_ingrediente", func=_sugerir_recetas_con_ingrediente,
             description="Busca recetas con ingrediente. Input: ingrediente (str). Ej: 'pollo'"),
        
        # Agente Inventario
        Tool(name="productos_por_caducar", func=_productos_por_caducar,
             description="Productos que caducan en N días. Input: dias (int). Ej: 3"),
        Tool(name="verificar_stock_bajo", func=_verificar_stock_bajo,
             description="Productos con stock bajo. Input: umbral (float, opcional). Ej: 10"),
        Tool(name="registrar_uso_inventario", func=_registrar_uso_inventario,
             description="Registra uso de ingrediente. Input: nombre_item, cantidad. Ej: 'Fresa', 2.5"),
        
        # Agente Menú
        Tool(name="menu_anti_desperdicio", func=_menu_anti_desperdicio,
             description="Sugiere menú para usar productos por caducar. Sin input."),
        Tool(name="generar_lista_compras", func=_generar_lista_compras,
             description="Lista compras para evento. Input: recetas_csv, comensales. Ej: 'REC001,REC002', 50"),
        
        # Agente Incidencias
        Tool(name="registrar_incidencia", func=_registrar_incidencia,
             description="Registra incidencia. Input: categoria, descripcion. Ej: 'Inventario', 'Falta leche'"),
        Tool(name="analizar_rentabilidad", func=_analizar_rentabilidad,
             description="Analiza rentabilidad del menú. Sin input."),
    ]