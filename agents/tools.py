"""
Herramientas Operativas Multi-Agente para ChefChat Pro

Arquitectura de Agentes:
├── Agente Inventario: caducidad, stock, compras
├── Agente Recetas: búsqueda, escalado, sugerencias
├── Agente Menú: planificación, eventos, anti-desperdicio
└── Agente Incidencias: bitácora, problemas
"""

from typing import List
from langchain_core.tools import Tool
from data.db_manager import DatabaseManager
import json
import sqlite3

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
    # Ollama models (FREE - local)
    "llama3.2": {"input": 0.0, "output": 0.0},
    "llama3.1": {"input": 0.0, "output": 0.0},
    "mistral": {"input": 0.0, "output": 0.0},
    "codellama": {"input": 0.0, "output": 0.0},
    "phi3": {"input": 0.0, "output": 0.0},
    "gemma2": {"input": 0.0, "output": 0.0},
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
    # Use the module-level sqlite3 import to avoid redefinition warnings
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    return conn

# ---- Funciones auxiliares para registro de compras ----

def _detectar_categoria(producto: str) -> str:
    """Detecta la categoria de un producto por su nombre."""
    p = producto.lower()
    if any(k in p for k in ['carne', 'pollo', 'cerdo', 'res', 'pescado', 'camaron', 'marisco', 'huevo']):
        return 'Proteina'
    if any(k in p for k in ['leche', 'queso', 'crema', 'mantequilla', 'yogur', 'helado']):
        return 'Lacteo'
    if any(k in p for k in ['pan', 'harina', 'tortilla', 'galleta', 'pastel', 'bolillo']):
        return 'Panaderia'
    if any(k in p for k in ['cebolla', 'tomate', 'lechuga', 'zanahoria', 'papa', 'ajo', 'pimiento',
                              'aguacate', 'cilantro', 'espinaca', 'brocoli', 'coliflor', 'apio',
                              'pepino', 'calabaza', 'chile', 'jitomate', 'elote', 'chayote']):
        return 'Vegetales'
    if any(k in p for k in ['manzana', 'naranja', 'platano', 'fresa', 'mango', 'pina', 'piña',
                              'sandia', 'melon', 'uva', 'limon', 'durazno', 'pera', 'guayaba']):
        return 'Frutas'
    if any(k in p for k in ['arroz', 'frijol', 'lenteja', 'garbanzo', 'maiz', 'maíz', 'avena',
                              'cereal', 'pasta', 'espagueti', 'fideo', 'sopa']):
        return 'Secos'
    if any(k in p for k in ['aceite', 'sal', 'azucar', 'azúcar', 'vinagre', 'salsa', 'condimento',
                              'especia', 'pimienta', 'oregano', 'comino', 'canela', 'clavo',
                              'caldo', 'consome', 'mayonesa', 'catsup', 'mostaza', 'soya']):
        return 'Condimentos'
    if any(k in p for k in ['jabon', 'jabón', 'detergente', 'cloro', 'desinfectante', 'papel',
                              'servilleta', 'bolsa', 'aluminio', 'plastico', 'plástico']):
        return 'Limpieza'
    if any(k in p for k in ['refresco', 'agua', 'jugo', 'cerveza', 'vino', 'licor', 'bebida']):
        return 'Bebidas'
    return 'General'


def _estimar_vida_util(producto: str) -> int:
    """Estima la vida util en dias segun el tipo de producto."""
    p = producto.lower()
    if any(k in p for k in ['carne', 'pollo', 'cerdo', 'res', 'pescado', 'camaron', 'marisco']):
        return 5
    if any(k in p for k in ['leche', 'crema', 'yogur']):
        return 7
    if any(k in p for k in ['queso', 'mantequilla']):
        return 30
    if any(k in p for k in ['pan', 'bolillo', 'tortilla']):
        return 3
    if any(k in p for k in ['harina', 'galleta']):
        return 90
    if any(k in p for k in ['cebolla', 'tomate', 'lechuga', 'espinaca', 'cilantro', 'aguacate']):
        return 7
    if any(k in p for k in ['papa', 'zanahoria', 'ajo', 'cebolla', 'calabaza']):
        return 30
    if any(k in p for k in ['arroz', 'frijol', 'lenteja', 'garbanzo', 'maiz', 'maíz', 'avena', 'pasta']):
        return 365
    if any(k in p for k in ['aceite', 'sal', 'azucar', 'azúcar', 'vinagre', 'condimento', 'especia']):
        return 365
    if any(k in p for k in ['huevo']):
        return 21
    return 30

def _parse_ingredientes(ingredientes_json):
    """Parsea ingredientes desde JSON o desde cadenas con formato delimitado por '|'."""
    if isinstance(ingredientes_json, str) and ingredientes_json.startswith("["):
        try:
            return json.loads(ingredientes_json)
        except (json.JSONDecodeError, TypeError):
            return []

    if isinstance(ingredientes_json, (list, tuple)):
        return list(ingredientes_json)

    ingredientes = []
    for item in str(ingredientes_json).split(";"):
        if "|" not in item:
            continue
        parts = item.split("|")
        if len(parts) < 3:
            continue
        try:
            cantidad = float(parts[0])
        except (ValueError, TypeError):
            continue
        ingredientes.append({
            "nombre": parts[2].strip(),
            "cantidad": cantidad,
            "unidad": parts[1].strip()
        })
    return ingredientes

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
            ingredientes_raw = receta.get("ingredientes_json")

            # Parsear ingredientes (JSON o cadena) usando helper robusto
            ingredientes = _parse_ingredientes(ingredientes_raw)

            # Comensales base (porciones del CSV) o 1 por defecto
            comensales_base = receta.get('porciones') or 1

            # Construir salida en líneas cortas para evitar long lines
            lineas = [
                f"Receta: {receta['nombre']}",
                f"(ID: {receta['id_receta']})",
                "Categoria: " + str(receta.get('categoria', '')),
                "Tiempo prep: " + str(receta.get('tiempo_prep', '')) + " min",
                "Costo: $" + f"{receta.get('costo', 0.0):.2f}",
                f"Porciones: {comensales_base}",
                "",
                "Ingredientes:",
            ]
            for ing in ingredientes:
                # Soportar dicts ya parseados o strings con formato
                if isinstance(ing, dict):
                    cantidad = ing.get('cantidad', '')
                    unidad = ing.get('unidad', '')
                    nombre = ing.get('nombre', '')
                    lineas.append(f"  - {cantidad} {unidad} {nombre}")
                elif isinstance(ing, str) and '|' in ing:
                    parts = ing.split('|')
                    if len(parts) >= 3:
                        lineas.append(f"  - {parts[0]} {parts[1]} {parts[2]}")
            if receta.get("alergenos"):
                lineas.append("")
                lineas.append("Alergenos: " + str(receta.get('alergenos')))
            if receta.get("instrucciones"):
                lineas.append("")
                lineas.append("Instrucciones: " + str(receta.get('instrucciones')))
            conn.close()
            return "\n".join(lineas)
        except (sqlite3.Error, json.JSONDecodeError) as e:
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
            ingredientes_raw = receta.get("ingredientes_json")

            # Usar helper para normalizar ingredientes
            ingredientes = _parse_ingredientes(ingredientes_raw)

            # Porciones originales y factor de escala
            comensales_orig = receta.get('porciones') or 1
            factor = comensales / comensales_orig

            lineas = [
                f"Receta: {receta['nombre']} - ESCALADA",
                f"Porciones: {comensales_orig} -> {comensales}",
                f"Factor: {factor:.2f}x",
                "",
                "Ingredientes ajustados:",
            ]
            
            for ing in ingredientes:
                if isinstance(ing, dict):
                    cantidad_orig = float(ing.get('cantidad', 0))
                    cantidad_nueva = round(cantidad_orig * factor, 2)
                    unidad = ing.get('unidad', '')
                    nombre = ing.get('nombre', '')
                    lineas.append(f"  - {cantidad_nueva} {unidad} {nombre}")
                elif isinstance(ing, str) and '|' in ing:
                    parts = ing.split('|')
                    if len(parts) >= 3:
                        cantidad_orig = float(parts[0])
                        cantidad_nueva = round(cantidad_orig * factor, 2)
                        lineas.append(f"  - {cantidad_nueva} {parts[1]} {parts[2]}")
            
            # Costo y tiempo en líneas separadas para evitar líneas largas
            lineas.append("")
            lineas.append("Costo estimado: $" + f"{receta.get('costo', 0.0) * factor:.2f}")
            lineas.append("(original: $" + f"{receta.get('costo', 0.0):.2f}" + ")")
            lineas.append("Tiempo prep: " + str(receta.get('tiempo_prep', '')) + " min")
            conn.close()
            return "\n".join(lineas)
        except (sqlite3.Error, json.JSONDecodeError, ValueError) as e:
            return f"Error: {str(e)}"

    def _sugerir_recetas_con_ingrediente(ingrediente: str) -> str:
        """Busca recetas que contienen un ingrediente específico."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            
            # Buscar en RecetasRAG (tabla correcta)
            cursor.execute(
                "SELECT nombre, categoria, tiempo_prep, costo, ingredientes_json "
                "FROM RecetasRAG "
                "WHERE LOWER(ingredientes_json) LIKE LOWER(?) "
                "LIMIT 10",
                (f"%{ingrediente}%",),
            )
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return f"No hay recetas con '{ingrediente}'"
            
            lineas = [f"🍳 Recetas con '{ingrediente}':"]
            for row in rows:
                lineas.append(f"  - {row[0]} ({row[1]}) - {row[2]} min, ${row[3]:.2f}")
            return "\n".join(lineas)
        except (sqlite3.Error, json.JSONDecodeError, ValueError) as e:
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
                SELECT c.nombre, c.categoria, i.cantidad_actual, i.unidad,
                       COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days')) as fecha_caducidad,
                       CAST(julianday(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) - julianday('now') AS INTEGER) as dias_restantes
                FROM Inventario i
                JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad_actual > 0 
                  AND (i.fecha_caducidad_fija IS NOT NULL OR c.vida_util_dias IS NOT NULL)
                  AND julianday(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) - julianday('now') <= ?
                  AND julianday(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) - julianday('now') >= 0
                ORDER BY COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days')) ASC
            """, (dias,))
            rows = cursor.fetchall()
            conn.close()
            
            # Guardar contexto para exportación
            from agents.orchestrator import guardar_contexto_exportacion
            datos = [[row[0], row[1], row[2], row[3], row[4], row[5]] for row in rows]
            columnas = ["Producto", "Categoría", "Cantidad", "Unidad", "Fecha Caducidad", "Días Restantes"]
            guardar_contexto_exportacion(datos=datos, columnas=columnas, titulo=f"Productos por Caducar ({dias} dias)")
            
            if not rows:
                return f"No hay productos por caducar en {dias} dias."
            
            lineas = [f"CADUCAN EN {dias} DIAS:", ""]
            urgentes = []
            for row in rows:
                prioridad = "[URGENTE]" if row[5] <= 1 else "[PRONTO]" if row[5] <= 3 else "[OK]"
                lineas.append(f"{prioridad} {row[0]}: {row[2]} {row[3]} ({row[5]} dias) - {row[1]}")
                if row[5] <= 3:
                    urgentes.append((row[0], row[5]))
            
            # Sugerir recetas para productos urgentes
            if urgentes:
                lineas.append("")
                lineas.append("RECETAS SUGERIDAS PARA APROVECHAR:")
                lineas.append("-" * 40)
                conn2 = _obtener_conexion(db)
                cursor2 = conn2.cursor()
                encontradas = 0
                for nombre_prod, dias_rest in urgentes[:5]:
                    palabra = nombre_prod.lower().split()[0]
                    try:
                        cursor2.execute("""
                            SELECT nombre, categoria, tiempo_prep FROM RecetasRAG
                            WHERE LOWER(ingredientes_json) LIKE ? LIMIT 2
                        """, (f"%{palabra}%",))
                        recetas = cursor2.fetchall()
                        if recetas:
                            lineas.append(f"  Para {nombre_prod} ({dias_rest} dias):")
                            for r in recetas:
                                lineas.append(f"    - {r[0]} ({r[1]}) - {r[2]} min")
                                encontradas += 1
                    except (sqlite3.Error, Exception):
                        pass
                conn2.close()
                if encontradas == 0:
                    lineas.append("  (No se encontraron recetas especificas. Usa [+] para cargar mas recetas)")
            
            return "\n".join(lineas)
        except sqlite3.Error as e:
            return f"Error de base de datos: {str(e)}"

    def _consultar_productos_por_caducar(dias: int = 7) -> str:
        """Consulta productos por caducar y guarda contexto para exportación."""
        return _productos_por_caducar(dias)

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
        except sqlite3.Error as e:
            return f"Error: {str(e)}"

    def _registrar_uso_inventario(nombre_item: str, cantidad: float) -> str:
        """Registra uso de inventario (FEFO)."""
        try:
            resultado = db.registrar_uso_inventario(nombre_item, cantidad)
            return f"OK: {resultado}"
        except (sqlite3.Error, json.JSONDecodeError) as e:
            return f"Error: {str(e)}"
        except ValueError as e:
            return f"Advertencia: {str(e)}"

    # =========================================================================
    # AGENTE MENU
    # =========================================================================
    
    def _menu_anti_desperdicio() -> str:
        """Sugiere menu para usar productos por caducar."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.nombre as nombre_producto, SUM(i.cantidad_actual) as cantidad_actual,
                       i.unidad,
                       CAST(MIN(julianday(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) - julianday('now')) AS INTEGER) as dias_restantes
                FROM Inventario i JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad_actual > 0
                GROUP BY c.nombre, i.unidad
                HAVING dias_restantes <= 5
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
                    SELECT nombre, categoria, tiempo_prep FROM RecetasRAG
                    WHERE LOWER(ingredientes_json) LIKE ? LIMIT 3
                """, (f"%{nombre_corto}%",))
                recetas = cursor.fetchall()
                if recetas:
                    lineas.append(f"\n  Para {prod[0]}:")
                    for r in recetas:
                        lineas.append(f"    - {r[0]} ({r[1]}) - {r[2]} min")
            conn.close()
            return "\n".join(lineas)
        except (sqlite3.Error, json.JSONDecodeError, ValueError) as e:
            return f"Error: {str(e)}"

    def _generar_lista_compras(recetas_csv: str, comensales: int = 1) -> str:
        """Genera lista de compras para evento."""
        def _procesar_ingredientes_receta(nombre_receta, ingredientes_json, porciones_base, comensales, ingredientes_totales):
            """Procesa ingredientes de una receta y los agrega al total."""
            try:
                if isinstance(ingredientes_json, str) and ingredientes_json.startswith("["):
                    ingredientes = json.loads(ingredientes_json)
                elif isinstance(ingredientes_json, (list, tuple)):
                    ingredientes = list(ingredientes_json)
                else:
                    ingredientes = []
                    for item in str(ingredientes_json).split(";"):
                        if "|" in item:
                            parts = item.split("|")
                            if len(parts) >= 3:
                                ingredientes.append({"nombre": parts[2].strip(), "cantidad": float(parts[0]), "unidad": parts[1].strip()})
            except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
                ingredientes = []
            
            factor = comensales / porciones_base if porciones_base > 0 else 1
            
            for ing in ingredientes:
                if not isinstance(ing, dict) or "nombre" not in ing:
                    continue
                key = f"{ing['nombre']}_{ing['unidad']}"
                if key not in ingredientes_totales:
                    ingredientes_totales[key] = {"nombre": ing["nombre"], "cantidad": 0,
                                                 "unidad": ing["unidad"], "recetas": []}
                try:
                    ingredientes_totales[key]["cantidad"] += float(ing["cantidad"]) * factor
                except (ValueError, TypeError):
                    pass
                ingredientes_totales[key]["recetas"].append(nombre_receta)
        
        def _verificar_stock(cursor2, ingredientes_totales):
            """Verifica stock disponible para ingredientes."""
            suficientes = []
            faltantes = []
            for _, ing in sorted(ingredientes_totales.items(), key=lambda x: x[1]["nombre"]):
                nombre_busq = ing["nombre"].split()[0] if " " in ing["nombre"] else ing["nombre"]
                cursor2.execute("""
                    SELECT i.cantidad_actual, i.unidad
                    FROM Inventario i JOIN Catalogo c ON i.producto_id = c.id
                    WHERE LOWER(c.nombre) LIKE LOWER(?) AND i.cantidad_actual > 0
                    ORDER BY i.fecha_ingreso ASC
                """, (f"%{nombre_busq}%",))
                stock_rows = cursor2.fetchall()
                stock_total = sum(r[0] for r in stock_rows) if stock_rows else 0
                if stock_total >= ing["cantidad"]:
                    suficientes.append(f"{ing['nombre']}: {ing['cantidad']:.1f} {ing['unidad']} (stock: {stock_total:.1f})")
                elif stock_total > 0:
                    faltan = ing["cantidad"] - stock_total
                    faltantes.append(f"{ing['nombre']}: necesitas {ing['cantidad']:.1f} {ing['unidad']}, tienes {stock_total:.1f}, faltan {faltan:.1f}")
                else:
                    faltantes.append(f"{ing['nombre']}: {ing['cantidad']:.1f} {ing['unidad']} (sin stock)")
            return suficientes, faltantes
        
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            ids = [r.strip() for r in recetas_csv.replace(",", ";").split(";") if r.strip()]
            ingredientes_totales: dict[str, dict] = {}
            
            for receta_id in ids:
                cursor.execute("""
                    SELECT nombre, ingredientes_json, COALESCE(porciones, 1) as porciones
                    FROM RecetasRAG
                    WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)
                """, (receta_id, f"%{receta_id}%"))
                row = cursor.fetchone()
                if not row:
                    continue
                
                nombre_receta, ingredientes_json, porciones_base = row
                _procesar_ingredientes_receta(nombre_receta, ingredientes_json, porciones_base, comensales, ingredientes_totales)
            
            conn2 = _obtener_conexion(db)
            cursor2 = conn2.cursor()
            suficientes, faltantes = _verificar_stock(cursor2, ingredientes_totales)
            conn2.close()
            
            lineas = ["LISTA DE COMPRAS", "=" * 40,
                     f"Recetas: {', '.join(ids)}"]
            
            if suficientes:
                lineas.extend(["", "✅ EN STOCK:"])
                lineas.extend(f"  {s}" for s in suficientes)
            
            if faltantes:
                lineas.extend(["", "❌ FALTA COMPRAR:"])
                lineas.extend(f"  {f}" for f in faltantes)
            
            return "\n".join(lineas)
        except (ValueError, TypeError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # AGENTE INCIDENCIAS
    # =========================================================================
    
    def _registrar_incidencia(categoria: str, descripcion: str) -> str:
        """Registra incidencia en bitacora."""
        try:
            id_reg = db.registrar_incidencia(categoria, descripcion)
            return f"OK: Incidencia registrada (ID: {id_reg}) - {categoria}"
        except (ValueError, TypeError, sqlite3.Error) as e:
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
        except (ValueError, TypeError, KeyError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # MENU POR INGREDIENTES
    # =========================================================================

    CATEGORIA_PREFIX = {
        "ENT": "Entrantes",
        "SOP": "Sopas",
        "ENS": "Ensaladas y Guarniciones",
        "PLF": "Platos Fuertes",
        "POS": "Postres",
        "BEB": "Bebidas",
        "EVT": "Eventos Especiales",
    }

    ORDEN_MENU = ["ENT", "SOP", "ENS", "PLF", "POS", "BEB"]

    def _crear_menu_por_comidas(comidas_dict: dict, ingredientes: list) -> str:
        """Crea menú separado por comidas (desayuno, almuerzo, merienda)."""
        try:
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            
            lineas = ["📅 MENÚ COMPLETO DEL DÍA", "=" * 50, ""]
            
            for tipo_comida, ingredientes_tipo in comidas_dict.items():
                # Buscar recetas para esta comida
                recetas_encontradas = []
                for ing in ingredientes_tipo:
                    cursor.execute("""
                        SELECT id_receta, nombre, categoria, tiempo_prep, costo, ingredientes_json
                        FROM RecetasRAG
                        WHERE LOWER(ingredientes_json) LIKE LOWER(?)
                        LIMIT 3
                    """, (f"%{ing}%",))
                    for row in cursor.fetchall():
                        if row[0] not in [r[0] for r in recetas_encontradas]:
                            recetas_encontradas.append(row)
                
                if recetas_encontradas:
                    lineas.append(f"🍽️ {tipo_comida.upper()}:")
                    lineas.append("-" * 40)
                    for r in recetas_encontradas[:2]:
                        lineas.append(f"  {r[0]} - {r[1]}")
                        lineas.append(f"    Tiempo: {r[3]} min | Costo: ${r[4]:.2f}")
                    lineas.append("")
                else:
                    lineas.append(f"⚠️ {tipo_comida.upper()}: No hay recetas con {', '.join(ingredientes_tipo)}")
                    lineas.append("")
            
            conn.close()
            
            if len(lineas) <= 4:
                return f"No se encontraron recetas para: {', '.join(ingredientes)}"
            
            lineas.extend([
                "=" * 50,
                "💡 RECOMENDACIONES:",
                "  - Usa 'buscar_receta ID' para ver detalles",
                "  - Usa 'escalar_receta ID, N' para ajustar porciones",
                "  - Usa 'generar_lista_compras' para lista de ingredientes"
            ])
            
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    def _sugerir_menu_por_ingredientes(ingredientes: str) -> str:
        """Sugiere menú completo con recetas que usen los ingredientes dados. Input: ingredientes separados por coma (str). Ej: 'pollo, queso, arroz'"""
        try:
            ingrediente_lista = [i.strip().lower() for i in ingredientes.replace(",", ";").split(";") if i.strip()]
            if not ingrediente_lista:
                return "Debes dar al menos un ingrediente"

            # Verificar si especifica comidas (desayuno, almuerzo, merienda)
            comidas_dict = {}
            ingredientes_lower = ingredientes.lower()
            
            if "desayuno" in ingredientes_lower or "almuerzo" in ingredientes_lower or "merienda" in ingredientes_lower or "cena" in ingredientes_lower:
                # Separar ingredientes por comida
                if "desayuno" in ingredientes_lower:
                    idx = ingredientes_lower.find("desayuno")
                    # Extraer ingredientes después de "desayuno" hasta la siguiente comida
                    resto = ingredientes[idx + len("desayuno"):]
                    for stop in ["almuerzo", "merienda", "cena"]:
                        if stop in resto:
                            resto = resto[:resto.find(stop)]
                    comidas_dict["Desayuno"] = [i.strip() for i in resto.replace(",", " ").split() if i.strip() and len(i) > 2]
                
                if "almuerzo" in ingredientes_lower or "almuerzo" in ingredientes_lower:
                    comida = "almuerzo" if "almuerzo" in ingredientes_lower else "almuerzo"
                    idx = ingredientes_lower.find(comida)
                    resto = ingredientes[idx + len(comida):]
                    for stop in ["merienda", "cena"]:
                        if stop in resto:
                            resto = resto[:resto.find(stop)]
                    comidas_dict["Almuerzo"] = [i.strip() for i in resto.replace(",", " ").split() if i.strip() and len(i) > 2]
                
                if "merienda" in ingredientes_lower:
                    idx = ingredientes_lower.find("merienda")
                    resto = ingredientes[idx + len("merienda"):]
                    if "cena" in resto:
                        resto = resto[:resto.find("cena")]
                    comidas_dict["Merienda"] = [i.strip() for i in resto.replace(",", " ").split() if i.strip() and len(i) > 2]
                
                if "cena" in ingredientes_lower:
                    idx = ingredientes_lower.find("cena")
                    resto = ingredientes[idx + len("cena"):]
                    comidas_dict["Cena"] = [i.strip() for i in resto.replace(",", " ").split() if i.strip() and len(i) > 2]
                
                # Si hay comidas definidas, usar función especializada
                if comidas_dict:
                    return _crear_menu_por_comidas(comidas_dict, ingrediente_lista)
            
            # Si no hay comidas específicas, usar método original por categorías
            conn = _obtener_conexion(db)
            cursor = conn.cursor()

            recetas_por_categoria: dict = {k: [] for k in CATEGORIA_PREFIX}
            recetas_vistas = set()

            for ing in ingrediente_lista:
                cursor.execute("""
                    SELECT id_receta, nombre, categoria, tiempo_prep, costo, ingredientes_json, alergenos
                    FROM RecetasRAG
                    WHERE LOWER(ingredientes_json) LIKE LOWER(?)
                """, (f"%{ing}%",))
                for row in cursor.fetchall():
                    rid = row[0]
                    if rid in recetas_vistas:
                        continue
                    recetas_vistas.add(rid)
                    prefijo = rid.split("-")[0] if "-" in rid else rid.split("_")[0]
                    if prefijo not in recetas_por_categoria:
                        continue
                    recetas_por_categoria[prefijo].append({
                        "id": rid, "nombre": row[1], "categoria": row[2],
                        "tiempo": row[3], "costo": row[4],
                        "ingredientes": row[5], "alergenos": row[6] or ""
                    })

            conn.close()

            total = sum(len(v) for v in recetas_por_categoria.values())
            if total == 0:
                return f"No se encontraron recetas con: {', '.join(ingrediente_lista)}"

            lineas = [
                "MENU SUGERIDO",
                "=" * 50,
                f"Basado en: {', '.join(ingrediente_lista)}",
                f"Recetas encontradas: {total}",
                "",
            ]

            for prefijo in ORDEN_MENU:
                recetas = recetas_por_categoria[prefijo]
                if not recetas:
                    continue
                nombre_cat = CATEGORIA_PREFIX[prefijo]
                lineas.append(f"── {nombre_cat} ──")
                for r in recetas[:3]:
                    costo = f"${r['costo']:.2f}" if r["costo"] else "N/A"
                    lineas.append(f"  {r['id']} - {r['nombre']}")
                    lineas.append(f"    Tiempo: {r['tiempo']} min | Costo: {costo}")
                    ing_texto = r["ingredientes"]
                    if ing_texto:
                        if ing_texto.startswith("["):
                            try:
                                parsed = json.loads(ing_texto)
                                nombres = [i.get("nombre", "") for i in parsed if isinstance(i, dict)]
                                ing_texto = ", ".join(nombres[:4])
                            except (json.JSONDecodeError, ValueError):
                                ing_texto = ing_texto[:80]
                        else:
                            parts = [p.split("|") for p in ing_texto.split(";") if "|" in p]
                            nombres = [p[2] for p in parts if len(p) >= 3]
                            ing_texto = ", ".join(nombres[:4])
                    lineas.append(f"    Ingredientes: {ing_texto}")
                    if r["alergenos"] and r["alergenos"] != "ninguno":
                        lineas.append(f"    Alergenos: {r['alergenos']}")
                    lineas.append("")
                lineas.append("")

            lineas.extend([
                "RECOMENDACIONES:",
                "  - Selecciona 1 de cada categoria para un menu equilibrado",
                "  - Usa 'buscar_receta ID' para ver la receta completa",
                "  - Usa 'escalar_receta ID, N' para ajustar comensales",
            ])

            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # FUNCIONES AUXILIARES PARA PLANIFICACION DE EVENTOS
    # =========================================================================

    def _obtener_recetas_evento(cursor, recetas_str: str, ingredientes_str: str):
        """Obtiene recetas para el evento por IDs o ingredientes."""
        recetas = []
        if recetas_str:
            ids = [r.strip() for r in recetas_str.replace(";", ",").split(",") if r.strip()]
            for rid in ids:
                cursor.execute("""
                    SELECT id_receta, nombre, ingredientes_json, COALESCE(porciones, 1) as porciones, costo
                    FROM RecetasRAG
                    WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)
                """, (rid, f"%{rid}%"))
                row = cursor.fetchone()
                if row:
                    recetas.append(dict(row))
        elif ingredientes_str:
            ing_list = [
                i.strip().lower()
                for i in ingredientes_str.replace(";", ",").split(",")
                if i.strip()
            ]
            for ing in ing_list[:3]:
                cursor.execute(
                    """
                    SELECT id_receta, nombre, ingredientes_json,
                           COALESCE(porciones, 1) as porciones, costo
                    FROM RecetasRAG
                    WHERE LOWER(ingredientes_json) LIKE LOWER(?)
                    LIMIT 1
                    """,
                    (f"%{ing}%",)
                )
                row = cursor.fetchone()
                if row:
                    recetas.append(dict(row))
        return recetas

    def _escalar_ingredientes(recetas_seleccionadas, comensales: int, comensales_base: int = 4):
        """Escala todos los ingredientes para N comensales."""
        ingredientes_totales = {}
        factor = comensales / comensales_base if comensales_base > 0 else 1
        
        for receta in recetas_seleccionadas:
            try:
                ing_json = receta.get("ingredientes_json", "[]")
                if isinstance(ing_json, str):
                    if ing_json.startswith("["):
                        ingredientes = json.loads(ing_json)
                    else:
                        ingredientes = [ing.strip() for ing in ing_json.split(";") if ing.strip()]
                else:
                    ingredientes = ing_json if isinstance(ing_json, list) else []
                
                for ing in ingredientes:
                    if isinstance(ing, dict):
                        nombre = ing.get("nombre", "")
                        unidad = ing.get("unidad", "")
                        cantidad = float(ing.get("cantidad", 0))
                    else:
                        parts = str(ing).split("|")
                        if len(parts) >= 3:
                            cantidad, unidad, nombre = float(parts[0]), parts[1].strip(), parts[2].strip()
                        else:
                            continue
                    
                    key = f"{nombre}_{unidad}"
                    if key not in ingredientes_totales:
                        ingredientes_totales[key] = {"nombre": nombre, "unidad": unidad, "cantidad": 0}
                    ingredientes_totales[key]["cantidad"] += cantidad * factor
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        
        return ingredientes_totales

    def _verificar_inventario(cursor, ingredientes_totales: dict):
        """Verifica si hay stock suficiente."""
        suficientes, parciales, faltantes = [], [], []
        
        for key, ing in ingredientes_totales.items():
            nombre_busq = ing["nombre"].split()[0] if " " in ing["nombre"] else ing["nombre"]
            cursor.execute("""
                SELECT i.cantidad_actual, i.unidad
                FROM Inventario i JOIN Catalogo c ON i.producto_id = c.id
                WHERE LOWER(c.nombre) LIKE LOWER(?) AND i.cantidad_actual > 0
                ORDER BY i.fecha_ingreso ASC
            """, (f"%{nombre_busq}%",))
            stock_rows = cursor.fetchall()
            stock_total = sum(float(r[0]) for r in stock_rows) if stock_rows else 0
            
            if stock_total >= ing["cantidad"]:
                suficientes.append(key)
            elif stock_total > 0:
                parciales.append(key)
            else:
                faltantes.append(key)
        
        return suficientes, parciales, faltantes

    def _obtener_alertas_caducidad(cursor, fecha_evento: str):
        """Obtiene alertas de caducidad para la fecha del evento."""
        alertas = []
        if fecha_evento:
            cursor.execute("""
                SELECT nombre_producto, dias_restantes
                FROM vista_caducidad_activa
                WHERE fecha_caducidad <= date(?)
                ORDER BY dias_restantes ASC
            """, (fecha_evento,))
            alertas = [dict(row) for row in cursor.fetchall()]
        return alertas

    def _generar_reporte_evento(fecha_evento: str, comensales: int, recetas_seleccionadas,
                                ing_keys: list, ingredientes_totales: dict, suficientes: list,
                                parciales: list, faltantes: list, alertas_caducidad: list):
        """Genera el reporte de planificación del evento."""
        lineas = [
            "PLANIFICACION DE EVENTO",
            "=" * 50,
            f"Fecha: {fecha_evento}",
            f"Comensales: {comensales}",
            ""
        ]
        
        if recetas_seleccionadas:
            lineas.append("RECETAS SELECCIONADAS:")
            for rec in recetas_seleccionadas:
                lineas.append(f"  - {rec.get('nombre', 'N/A')} (ID: {rec.get('id_receta', 'N/A')})")
        
        lineas.extend(["", "INGREDIENTES REQUERIDOS:"])
        for key in ing_keys:
            if key in ingredientes_totales:
                ing = ingredientes_totales[key]
                lineas.append(f"  - {ing['nombre']}: {ing['cantidad']:.1f} {ing['unidad']}")
        
        if suficientes:
            lineas.extend(["", "✅ EN STOCK:"])
            for key in suficientes:
                ing = ingredientes_totales[key]
                lineas.append(f"  - {ing['nombre']}: {ing['cantidad']:.1f} {ing['unidad']}")
        
        if parciales:
            lineas.extend(["", "⚠️ STOCK PARCIAL:"])
            for key in parciales:
                ing = ingredientes_totales[key]
                lineas.append(f"  - {ing['nombre']}: {ing['cantidad']:.1f} {ing['unidad']}")
        
        if faltantes:
            lineas.extend(["", "❌ FALTA COMPRAR:"])
            for key in faltantes:
                ing = ingredientes_totales[key]
                lineas.append(f"  - {ing['nombre']}: {ing['cantidad']:.1f} {ing['unidad']}")
        
        if alertas_caducidad:
            lineas.extend(["", "⚠️ ALERTA CADUCIDAD:"])
            for alerta in alertas_caducidad:
                lineas.append(f"  - {alerta.get('nombre_producto', 'N/A')}: {alerta.get('dias_restantes', 0)} días")
        
        return lineas

    # =========================================================================
    # PLANIFICACION DE EVENTOS
    # =========================================================================

    def _planificar_evento(parametros: str) -> str:
        """Planifica evento completo: sugiere menú, escala recetas, 
        verifica inventario y lista faltantes.
        Input: 'fecha=2025-06-15, comensales=50, ingredientes=pollo, arroz'
        O: 'fecha=2025-06-15, comensales=30, recetas=SOP-021,PLF-018,POS-006'"""
        try:
            # Parsear parámetros (usar | como separador, o coma respetando recetas=)
            params = {}
            sep = "|" if "|" in parametros else ","
            partes = parametros.split(sep)
            for par in partes:
                if "=" in par:
                    k, v = par.split("=", 1)
                    params[k.strip().lower()] = v.strip()

            fecha_evento = params.get("fecha", "")
            comensales = int(params.get("comensales", 10))
            ingredientes_str = params.get("ingredientes", "")
            recetas_str = params.get("recetas", "")

            conn = _obtener_conexion(db)
            cursor = conn.cursor()

            # 1. OBTENER RECETAS
            recetas_seleccionadas = _obtener_recetas_evento(
                cursor,
                recetas_str,
                ingredientes_str
            )

            if not recetas_seleccionadas:
                conn.close()
                msg = "No se encontraron recetas para planificar el evento."
                return msg

            # 2. ESCALAR Y AGRUPAR INGREDIENTES
            comensales_base = 4
            ingredientes_totales = _escalar_ingredientes(
                recetas_seleccionadas,
                comensales,
                comensales_base
            )

            # 3. VERIFICAR INVENTARIO
            suficientes, parciales, faltantes = _verificar_inventario(
                cursor,
                ingredientes_totales
            )

            # 4. ALERTAS DE CADUCIDAD
            alertas_caducidad = _obtener_alertas_caducidad(
                cursor,
                fecha_evento
            )

            conn.close()

            # 5. ARMAR REPORTE
            ing_keys = list(ingredientes_totales.keys())
            lineas = _generar_reporte_evento(
                fecha_evento,
                comensales,
                recetas_seleccionadas,
                ing_keys,
                ingredientes_totales,
                suficientes,
                parciales,
                faltantes,
                alertas_caducidad
            )

            return "\n".join(lineas)
        except ValueError as e:
            return f"Error en validación: {str(e)}"
        except sqlite3.Error as e:
            return f"Error en base de datos: {str(e)}"
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error inesperado: {str(e)}"

    # =========================================================================
    # HERRAMIENTAS OFFICE (COM)
    # =========================================================================

    def _enviar_a_word(receta_id: str) -> str:
        """Envía receta al documento activo de Word. Input: receta_id (str)."""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice

            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM RecetasRAG WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)",
                          (receta_id, f"%{receta_id}%"))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return f"Receta '{receta_id}' no encontrada"

            receta = dict(row)
            ingredientes_raw = receta["ingredientes_json"]
            ingredientes = []
            if isinstance(ingredientes_raw, str):
                if ingredientes_raw.startswith('['):
                    ingredientes = json.loads(ingredientes_raw)
                else:
                    ingredientes = [ing.strip() for ing in ingredientes_raw.split(';') if ing.strip()]
            else:
                ingredientes = ingredientes_raw

            lineas = [f"Receta: {receta['nombre']} (ID: {receta['id_receta']})",
                     f"Categoria: {receta['categoria']} | Tiempo: {receta['tiempo_prep']} min | Costo: ${receta['costo']:.2f}",
                     "", "Ingredientes:"]
            for ing in ingredientes:
                if isinstance(ing, str) and '|' in ing:
                    parts = ing.split('|')
                    if len(parts) >= 3:
                        lineas.append(f"  - {parts[0]} {parts[1]} {parts[2]}")
                elif isinstance(ing, dict):
                    lineas.append(f"  - {ing.get('cantidad', '')} {ing.get('unidad', '')} {ing.get('nombre', '')}")
            if receta.get("alergenos"):
                lineas.append(f"\nAlergenos: {receta['alergenos']}")
            if receta.get("instrucciones"):
                lineas.append(f"\nInstrucciones: {receta['instrucciones']}")

            contenido = "\n".join(lineas)
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="word",
                operacion="enviar",
                ruta_archivo="",
                payload={"contenido": contenido, "formato": {"titulo": receta["nombre"]}},
                requiere_hitl=False
            ))
            return f"Receta enviada a Word: {resultado.get('mensaje', 'OK')}"
        except (sqlite3.Error, json.JSONDecodeError, ValueError, TypeError) as e:
            return f"Error al enviar a Word: {str(e)}"

    def _enviar_a_excel(receta_id: str) -> str:
        """Envía receta como tabla al libro activo de Excel. Input: receta_id (str)."""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice

            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM RecetasRAG WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)",
                          (receta_id, f"%{receta_id}%"))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return f"Receta '{receta_id}' no encontrada"

            receta = dict(row)
            ingredientes_raw = receta["ingredientes_json"]
            ingredientes = []
            if isinstance(ingredientes_raw, str):
                if ingredientes_raw.startswith('['):
                    ingredientes = json.loads(ingredientes_raw)
                else:
                    ingredientes = [ing.strip() for ing in ingredientes_raw.split(';') if ing.strip()]
            else:
                ingredientes = ingredientes_raw

            datos = [["Ingrediente", "Cantidad", "Unidad"]]
            for ing in ingredientes:
                if isinstance(ing, str) and '|' in ing:
                    parts = ing.split('|')
                    if len(parts) >= 3:
                        datos.append([parts[2], parts[0], parts[1]])
                elif isinstance(ing, dict):
                    datos.append([ing.get('nombre', ''), str(ing.get('cantidad', '')), ing.get('unidad', '')])

            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="excel",
                operacion="enviar",
                ruta_archivo="",
                payload={"datos": datos, "insertar_en": "A1"},
                requiere_hitl=False
            ))
            return f"Receta '{receta['nombre']}' enviada a Excel: {resultado.get('mensaje', 'OK')}"
        except (sqlite3.Error, json.JSONDecodeError, ValueError, TypeError) as e:
            return f"Error al enviar a Excel: {str(e)}"

    def _enviar_menu_a_powerpoint(recetas: str) -> str:
        """Envía menú (recetas separadas por coma) a PowerPoint. Input: recetas (str). Ej: 'SOP-021,PLF-045'"""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice

            receta_ids = [r.strip() for r in recetas.replace(",", ";").split(";") if r.strip()]
            lineas_menu = ["MENU DEL DIA", "=" * 30, ""]

            conn = _obtener_conexion(db)
            for rid in receta_ids:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM RecetasRAG WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)",
                              (rid, f"%{rid}%"))
                row = cursor.fetchone()
                if row:
                    receta = dict(row)
                    lineas_menu.append(f"{receta['nombre']} (ID: {receta['id_receta']})")
                    lineas_menu.append(f"  Tiempo: {receta['tiempo_prep']} min | Costo: ${receta['costo']:.2f}")
                    lineas_menu.append("")
            conn.close()

            if len(lineas_menu) <= 3:
                return "No se encontraron recetas"

            contenido = "\n".join(lineas_menu)
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="powerpoint",
                operacion="enviar",
                ruta_archivo="",
                payload={"contenido": contenido, "formato": {"titulo": "Menú del Día"}},
                requiere_hitl=False
            ))
            return f"Menú enviado a PowerPoint: {resultado.get('mensaje', 'OK')}"
        except (sqlite3.Error, json.JSONDecodeError, ValueError, TypeError) as e:
            return f"Error al enviar menú a PowerPoint: {str(e)}"

    def _enviar_lista_compras_a_word(recetas: str, comensales: int = 1) -> str:
        """Envía lista de compras a Word. Input: recetas (str), comensales (int, opcional). Ej: 'SOP-021,PLF-045', 50"""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice

            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            ids = [r.strip() for r in recetas.replace(",", ";").split(";") if r.strip()]
            ingredientes_totales = {}
            
            for receta_id in ids:
                cursor.execute("""
                    SELECT nombre, ingredientes_json, COALESCE(porciones, 1) as porciones
                    FROM RecetasRAG
                    WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)
                """, (receta_id, f"%{receta_id}%"))
                row = cursor.fetchone()
                if not row:
                    continue
                
                nombre_receta, ingredientes_json, porciones_base = row
                ingredientes = _parse_ingredientes(ingredientes_json)

                factor = comensales / porciones_base if porciones_base > 0 else 1
                
                for ing in ingredientes:
                    if not isinstance(ing, dict) or "nombre" not in ing:
                        continue
                    key = f"{ing['nombre']}_{ing.get('unidad', '')}"
                    if key not in ingredientes_totales:
                        ingredientes_totales[key] = {"nombre": ing["nombre"], "cantidad": 0,
                                                     "unidad": ing.get("unidad", ""), "recetas": []}
                    try:
                        ingredientes_totales[key]["cantidad"] += float(ing.get("cantidad", 0)) * factor
                    except (ValueError, TypeError):
                        pass
                    ingredientes_totales[key]["recetas"].append(nombre_receta)
            
            conn2 = _obtener_conexion(db)
            cursor2 = conn2.cursor()
            suficientes = []
            faltantes = []
            for _, ing in sorted(ingredientes_totales.items(), key=lambda x: x[1]["nombre"]):
                nombre_busq = ing["nombre"].split()[0] if " " in ing["nombre"] else ing["nombre"]
                cursor2.execute("""
                    SELECT i.cantidad_actual, i.unidad
                    FROM Inventario i JOIN Catalogo c ON i.producto_id = c.id
                    WHERE LOWER(c.nombre) LIKE LOWER(?) AND i.cantidad_actual > 0
                    ORDER BY i.fecha_ingreso ASC
                """, (f"%{nombre_busq}%",))
                stock_rows = cursor2.fetchall()
                stock_total = sum(r[0] for r in stock_rows) if stock_rows else 0
                if stock_total >= ing["cantidad"]:
                    suficientes.append(f"{ing['nombre']}: {ing['cantidad']:.1f} {ing['unidad']} (stock: {stock_total:.1f})")
                elif stock_total > 0:
                    faltan = ing["cantidad"] - stock_total
                    faltantes.append(f"{ing['nombre']}: necesitas {ing['cantidad']:.1f} {ing['unidad']}, tienes {stock_total:.1f}, faltan {faltan:.1f}")
                else:
                    faltantes.append(f"{ing['nombre']}: {ing['cantidad']:.1f} {ing['unidad']} (sin stock)")
            conn2.close()
            
            lineas = ["LISTA DE COMPRAS", "=" * 40,
                     f"Recetas: {', '.join(ids)}", f"Comensales: {comensales}", ""]
            
            if suficientes:
                lineas.extend(["✅ EN STOCK:", ""])
                lineas.extend(f"  {s}" for s in suficientes)
            
            if faltantes:
                lineas.extend(["", "❌ FALTA COMPRAR:", ""])
                lineas.extend(f"  {f}" for f in faltantes)
            
            if not suficientes and not faltantes:
                lineas.append("No hay ingredientes para mostrar.")
            
            contenido = "\n".join(lineas)
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="word",
                operacion="enviar",
                ruta_archivo="",
                payload={"contenido": contenido, "formato": {"titulo": "Lista de Compras", "font_size": 12}},
                requiere_hitl=False
            ))
            return f"Lista de compras enviada a Word: {resultado.get('mensaje', 'OK')}"
        except (sqlite3.Error, json.JSONDecodeError, ValueError, TypeError) as e:
            return f"Error al enviar lista de compras a Word: {str(e)}"

    def _enviar_lista_compras_a_excel(recetas: str, comensales: int = 1) -> str:
        """Envía lista de compras a Excel. Input: recetas (str), comensales (int, opcional). Ej: 'SOP-021,PLF-045', 50"""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice

            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            ids = [r.strip() for r in recetas.replace(",", ";").split(";") if r.strip()]
            ingredientes_totales = {}
            
            for receta_id in ids:
                cursor.execute("""
                    SELECT nombre, ingredientes_json, COALESCE(porciones, 1) as porciones
                    FROM RecetasRAG
                    WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)
                """, (receta_id, f"%{receta_id}%"))
                row = cursor.fetchone()
                if not row:
                    continue
                
                nombre_receta, ingredientes_json, porciones_base = row
                ingredientes = _parse_ingredientes(ingredientes_json)

                factor = comensales / porciones_base if porciones_base > 0 else 1
                
                for ing in ingredientes:
                    if not isinstance(ing, dict) or "nombre" not in ing:
                        continue
                    key = f"{ing['nombre']}_{ing.get('unidad', '')}"
                    if key not in ingredientes_totales:
                        ingredientes_totales[key] = {"nombre": ing["nombre"], "cantidad": 0,
                                                     "unidad": ing.get("unidad", ""), "recetas": []}
                    try:
                        ingredientes_totales[key]["cantidad"] += float(ing.get("cantidad", 0)) * factor
                    except (ValueError, TypeError):
                        pass
                    ingredientes_totales[key]["recetas"].append(nombre_receta)
            
            conn2 = _obtener_conexion(db)
            cursor2 = conn2.cursor()
            datos = [["Ingrediente", "Cantidad", "Unidad", "Stock Disponible", "Estado", "Falta"]]
            for _, ing in sorted(ingredientes_totales.items(), key=lambda x: x[1]["nombre"]):
                nombre_busq = ing["nombre"].split()[0] if " " in ing["nombre"] else ing["nombre"]
                cursor2.execute("""
                    SELECT i.cantidad_actual, i.unidad
                    FROM Inventario i JOIN Catalogo c ON i.producto_id = c.id
                    WHERE LOWER(c.nombre) LIKE LOWER(?) AND i.cantidad_actual > 0
                    ORDER BY i.fecha_ingreso ASC
                """, (f"%{nombre_busq}%",))
                stock_rows = cursor2.fetchall()
                stock_total = sum(r[0] for r in stock_rows) if stock_rows else 0
                if stock_total >= ing["cantidad"]:
                    estado = "OK"
                    falta = 0
                elif stock_total > 0:
                    estado = "Parcial"
                    falta = ing["cantidad"] - stock_total
                else:
                    estado = "Sin Stock"
                    falta = ing["cantidad"]
                datos.append([
                    str(ing["nombre"]),
                    str(round(ing["cantidad"], 2)),
                    str(ing["unidad"]),
                    str(round(stock_total, 2)),
                    str(estado),
                    str(round(falta, 2))
                ])
            conn2.close()
            
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="excel",
                operacion="enviar",
                ruta_archivo="",
                payload={"datos": datos, "insertar_en": "A1"},
                requiere_hitl=False
            ))
            return f"Lista de compras enviada a Excel: {resultado.get('mensaje', 'OK')}"
        except (sqlite3.Error, json.JSONDecodeError, ValueError, TypeError) as e:
            return f"Error al enviar lista de compras a Excel: {str(e)}"

    def _enviar_reporte_mermas_a_word(dias: int = 7) -> str:
        """Envía reporte de mermas a Word. Input: dias (int, opcional, default 7). Ej: '30'"""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice
            from agents.orchestrator import guardar_contexto_exportacion

            mermas = db.obtener_mermas(dias)
            totales = db.total_mermas_periodo(dias)
            
            # Guardar contexto para exportación
            datos = [[m['fecha'], m['producto'], m['cantidad'], m['unidad'], m['motivo'], f"${m['costo_estimado']:.2f}" if m['costo_estimado'] else "$0.00"] for m in mermas]
            columnas = ["Fecha", "Producto", "Cantidad", "Unidad", "Motivo", "Costo"]
            guardar_contexto_exportacion(datos=datos, columnas=columnas, titulo=f"Reporte de Mermas ({dias} días)")
            
            lineas = ["REPORTE DE MERMAS", "=" * 40,
                     f"Período: últimos {dias} días", ""]
            
            if mermas:
                lineas.append("DETALLE DE MERMAS:")
                lineas.append("-" * 40)
                for m in mermas[:50]:
                    costo = f" | ${m['costo_estimado']:.2f}" if m['costo_estimado'] else ""
                    lineas.append(f"  {m['fecha']} - {m['producto']}: {m['cantidad']} {m['unidad']} ({m['motivo']}){costo}")
                
                lineas.extend(["", "=" * 40, "RESUMEN:"])
                lineas.append(f"  Total mermas: {totales['total_mermas']}")
                lineas.append(f"  Costo total: ${totales['costo_total']:.2f}")
            else:
                lineas.append(f"No hay mermas registradas en los últimos {dias} días.")
            
            contenido = "\n".join(lineas)
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="word",
                operacion="enviar",
                ruta_archivo="",
                payload={"contenido": contenido, "formato": {"titulo": f"Reporte de Mermas ({dias} días)", "font_size": 12}},
                requiere_hitl=False
            ))
            return f"Reporte de mermas enviado a Word: {resultado.get('mensaje', 'OK')}"
        except (sqlite3.Error, json.JSONDecodeError, ValueError, TypeError) as e:
            return f"Error al enviar reporte de mermas a Word: {str(e)}"

    def _enviar_reporte_mermas_a_excel(dias: int = 7) -> str:
        """Envía reporte de mermas a Excel. Input: dias (int, opcional, default 7). Ej: '30'"""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice
            from agents.orchestrator import guardar_contexto_exportacion

            mermas = db.obtener_mermas(dias)
            totales = db.total_mermas_periodo(dias)
            
            # Guardar contexto para exportación
            datos = [[m['fecha'], m['producto'], m['cantidad'], m['unidad'], m['motivo'], f"${m['costo_estimado']:.2f}" if m['costo_estimado'] else "$0.00"] for m in mermas]
            columnas = ["Fecha", "Producto", "Cantidad", "Unidad", "Motivo", "Costo"]
            guardar_contexto_exportacion(datos=datos, columnas=columnas, titulo=f"Reporte de Mermas ({dias} días)")
            
            datos = [["Fecha", "Producto", "Cantidad", "Unidad", "Motivo", "Costo Estimado"]]
            for m in mermas:
                datos.append([
                    m['fecha'],
                    m['producto'],
                    m['cantidad'],
                    m['unidad'],
                    m['motivo'],
                    m['costo_estimado'] if m['costo_estimado'] else 0.0
                ])
            
            datos.append([])
            # Manejar valores None en totales
            total_mermas = totales.get('total_mermas', 0) if totales else 0
            costo_total = totales.get('costo_total', 0.0) if totales else 0.0
            datos.append(["RESUMEN", "", "", "", "Total Mermas:", total_mermas])
            datos.append(["", "", "", "", "Costo Total:", f"${costo_total:.2f}" if costo_total else "$0.00"])
            
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="excel",
                operacion="enviar",
                ruta_archivo="",
                payload={"datos": datos, "insertar_en": "A1"},
                requiere_hitl=False
            ))
            return f"Reporte de mermas enviado a Excel: {resultado.get('mensaje', 'OK')}"
        except (sqlite3.Error, json.JSONDecodeError, ValueError, TypeError) as e:
            return f"Error al enviar reporte de mermas a Excel: {str(e)}"

    def _enviar_inventario_a_word() -> str:
        """Envía inventario actual a Word."""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice

            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.nombre, c.categoria, SUM(i.cantidad_actual) as total, i.unidad
                FROM Inventario i
                JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad_actual > 0
                GROUP BY c.nombre, c.categoria, i.unidad
                ORDER BY c.categoria, c.nombre
            """)
            rows = cursor.fetchall()
            conn.close()
            
            lineas = ["INVENTARIO ACTUAL", "=" * 40, ""]
            
            if rows:
                categoria_actual = ""
                for row in rows:
                    if row[1] != categoria_actual:
                        categoria_actual = row[1]
                        lineas.append(f"\n{categoria_actual.upper()}:")
                        lineas.append("-" * 30)
                    lineas.append(f"  {row[0]}: {row[2]:.2f} {row[3]}")
            else:
                lineas.append("No hay productos en inventario.")
            
            contenido = "\n".join(lineas)
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="word",
                operacion="enviar",
                ruta_archivo="",
                payload={"contenido": contenido, "formato": {"titulo": "Inventario Actual", "font_size": 12}},
                requiere_hitl=False
            ))
            return f"Inventario enviado a Word: {resultado.get('mensaje', 'OK')}"
        except (sqlite3.Error, json.JSONDecodeError, ValueError, TypeError) as e:
            return f"Error al enviar inventario a Word: {str(e)}"

    def _enviar_inventario_a_excel() -> str:
        """Envía inventario actual a Excel."""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice

            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.nombre, c.categoria, SUM(i.cantidad_actual) as total, i.unidad
                FROM Inventario i
                JOIN Catalogo c ON i.producto_id = c.id
                WHERE i.cantidad_actual > 0
                GROUP BY c.nombre, c.categoria, i.unidad
                ORDER BY c.categoria, c.nombre
            """)
            rows = cursor.fetchall()
            conn.close()
            
            datos = [["Producto", "Categoría", "Cantidad", "Unidad"]]
            for row in rows:
                datos.append([row[0], row[1], row[2], row[3]])
            
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="excel",
                operacion="enviar",
                ruta_archivo="",
                payload={"datos": datos, "insertar_en": "A1"},
                requiere_hitl=False
            ))
            return f"Inventario enviado a Excel: {resultado.get('mensaje', 'OK')}"
        except (ValueError, KeyError, OSError) as e:
            return f"Error al enviar inventario a Excel: {str(e)}"

    def _enviar_productos_por_caducar_a_excel() -> str:
        """Envía productos próximos a caducar a Excel usando el contexto guardado."""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice
            from agents.orchestrator import obtener_contexto_exportacion
            
            contexto = obtener_contexto_exportacion()
            
            # Si no hay datos en contexto, consultar directamente
            if not contexto.get("datos"):
                conn = _obtener_conexion(db)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.nombre, c.categoria, i.cantidad_actual, i.unidad,
                           COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days')) as fecha_caducidad,
                           CAST(julianday(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) - julianday('now') AS INTEGER) as dias_restantes
                    FROM Inventario i
                    JOIN Catalogo c ON i.producto_id = c.id
                    WHERE i.cantidad_actual > 0 
                      AND (i.fecha_caducidad_fija IS NOT NULL OR c.vida_util_dias IS NOT NULL)
                      AND julianday(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) - julianday('now') <= 7
                    ORDER BY COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days')) ASC
                """)
                rows = cursor.fetchall()
                conn.close()
                
                datos = [["Producto", "Categoría", "Cantidad", "Unidad", "Fecha Caducidad", "Días Restantes"]]
                for row in rows:
                    datos.append([row[0], row[1], row[2], row[3], row[4], row[5]])
            else:
                # Usar datos del contexto
                datos = [contexto["columnas"]] + contexto["datos"]
            
            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="excel",
                operacion="enviar",
                ruta_archivo="",
                payload={"datos": datos, "insertar_en": "A1"},
                requiere_hitl=False
            ))
            return f"Productos por caducar enviados a Excel: {resultado.get('mensaje', 'OK')}"
        except (ValueError, KeyError, OSError) as e:
            return f"Error al enviar productos por caducar a Excel: {str(e)}"

    # =========================================================================
    # HERRAMIENTAS PLANTILLAS
    # =========================================================================

    def _listar_plantillas() -> str:
        """Lista las plantillas disponibles en el directorio de plantillas."""
        try:
            import os
            from agents.mcp_client import PLANTILLAS_DIR
            if not os.path.exists(PLANTILLAS_DIR):
                return "No hay carpeta de plantillas. Crea la carpeta 'plantillas/' en la raiz del proyecto y guarda tus documentos .docx o .pptx alli."
            archivos = []
            for f in os.listdir(PLANTILLAS_DIR):
                if f.endswith((".docx", ".doc", ".pptx", ".ppt")):
                    archivos.append(f)
            if not archivos:
                return "No hay plantillas guardadas. Guarda archivos .docx o .pptx en la carpeta 'plantillas/' del proyecto."
            lineas = ["PLANTILLAS DISPONIBLES", "=" * 40]
            for a in archivos:
                ruta = os.path.join(PLANTILLAS_DIR, a)
                tam = os.path.getsize(ruta)
                lineas.append(f"  - {a} ({tam/1024:.0f} KB)")
            return "\n".join(lineas)
        except (OSError, IOError) as e:
            return f"Error: {str(e)}"

    def _usar_plantilla(parametros: str) -> str:
        """Aplica una plantilla de Word/PPT reemplazando sus placeholders {{...}} con datos.
        Input: 'nombre_plantilla.docx | clave1=valor1, clave2=valor2'
        Ej: 'invitacion.docx | nombre=Juan, fecha=15 Junio, lugar= SalonPrincipal'"""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice

            partes = parametros.split("|", 1)
            nombre = partes[0].strip()
            datos = {}
            if len(partes) > 1:
                for par in partes[1].split(","):
                    if "=" in par:
                        k, v = par.split("=", 1)
                        datos[k.strip()] = v.strip()

            if not nombre:
                return "Debes especificar el nombre de la plantilla"

            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(AccionOffice(
                herramienta="word" if nombre.endswith((".docx", ".doc")) else "powerpoint",
                operacion="plantilla",
                ruta_archivo="",
                payload={"plantilla": nombre, "datos": datos},
                requiere_hitl=False
            ))
            return resultado.get("mensaje", "Plantilla aplicada")
        except (ImportError, AttributeError, ValueError, KeyError) as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # NUEVAS FUNCIONES: Menú diario, Mermas, Órdenes, Costos, Turnos, Dashboard
    # =========================================================================

    def _menu_diario() -> str:
        """Muestra o sugiere el menú del día basado en configuración semanal e inventario."""
        try:
            info = db.sugerir_menu_diario()
            lineas = [f"MENU DEL {info['dia'].upper()}", "=" * 40]

            if info["menu_configurado"]:
                lineas.append("")
                for item in info["menu_configurado"]:
                    tipo = item["tipo_comida"].replace("_", " ").title()
                    lineas.append(f"  {tipo}: {item['receta_nombre']} ({item['receta_id']})")
            else:
                lineas.append("\n  No hay menú configurado para hoy.")
                lineas.append("  Usa 'configurar_menu_semanal' para asignar recetas a cada día.")

            if info["stock_bajo_sugerencia"]:
                lineas.extend(["", "⚠️ Productos con stock bajo (sugerencia para el menú):"])
                for p in info["stock_bajo_sugerencia"][:5]:
                    lineas.append(f"  - {p['nombre']}: {p['stock']:.1f} {p['unidad']}")

            return "\n".join(lineas)
        except (sqlite3.Error, KeyError, TypeError) as e:
            return f"Error: {str(e)}"

    def _configurar_menu_semanal(parametros: str) -> str:
        """Configura el menú semanal. Input: 'Lunes | entrante=REC001, sopa=REC002, plato_fuerte=REC003, postre=REC004, bebida=REC005'"""
        conn = None
        try:
            partes = parametros.split("|", 1)
            dia = partes[0].strip().title()
            if dia not in ["Lunes","Martes","Miercoles","Jueves","Viernes","Sabado","Domingo"]:
                return f"Día inválido: {dia}. Usa: Lunes, Martes, Miercoles, Jueves, Viernes, Sabado, Domingo"

            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            if len(partes) > 1:
                db.limpiar_menu_semanal(dia)
                asignaciones = partes[1].split(",")
                contador = 0
                for asig in asignaciones:
                    if "=" not in asig:
                        continue
                    tipo, receta_ref = asig.split("=", 1)
                    tipo = tipo.strip().lower().replace(" ", "_")
                    receta_ref = receta_ref.strip()
                    tipos_validos = {"entrante","sopa","plato_fuerte","postre","bebida"}
                    if tipo not in tipos_validos:
                        continue
                    cursor.execute("SELECT id_receta, nombre FROM RecetasRAG WHERE id_receta = ? OR LOWER(nombre) LIKE LOWER(?)", (receta_ref, f"%{receta_ref}%"))
                    row = cursor.fetchone()
                    if row:
                        db.configurar_menu_semanal(dia, tipo, row[0], row[1])
                        contador += 1
                return f"Menú del {dia} configurado con {contador} recetas"
            return "No se especificaron recetas. Formato: 'Lunes | entrante=SOP-021, plato_fuerte=PLF-018, postre=POS-006'"
        except (ValueError, sqlite3.Error) as e:
            return f"Error: {str(e)}"
        finally:
            if conn:
                conn.close()

    def _registrar_merma(parametros: str) -> str:
        """Registra merma/desperdicio. Input: 'producto, cantidad, unidad, motivo, costo' o lenguaje natural: '23 kilos de cerdo de merma'"""
        try:
            import re
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) >= 4:
                producto = partes[0]
                cantidad = float(partes[1])
                unidad = partes[2]
                motivo = partes[3]
                costo = float(partes[4]) if len(partes) > 4 and partes[4] else 0.0
            else:
                # Parseo de lenguaje natural: "23 kilos de cerdo de merma"
                match_nl = re.search(
                    r'(\d+(?:[.,]\d+)?)\s*(kilos?|kg|kgs?|litros?|lts?|l\b|'
                    r'unidades?|unds?|piezas?|pzas?|gramos?|grs?|g\b|'
                    r'libras?|lbs?|onzas?|oz|paquetes?|bolsas?|cajas?|galones?|'
                    r'porciones?)\s+(?:de\s+)?(.+?)(?:\s+(?:de|en|como|por)\s+merma|\s+(?:se\s+)?'
                    r'(?:echo|echó|echo a perder|dañ[oó]|pudri[oó]|caduc[oóad]+|venci[oó]|'
                    r'sobra|sobr[oó]|desperdici[oó]|mal\s+estado|contamin[oa]d[oa]|'
                    r'pas[oó]\s+de\s+fecha|expirad[oa]|malogrado|inservible))',
                    parametros, re.IGNORECASE
                )
                if match_nl:
                    cantidad = float(match_nl.group(1).replace(',', '.'))
                    unidad_raw = match_nl.group(2).lower()
                    producto = match_nl.group(3).strip().rstrip(',').rstrip('.')
                    unidad_map = {'kilos': 'kg', 'kilo': 'kg', 'kgs': 'kg', 'kg': 'kg',
                                  'litros': 'L', 'litro': 'L', 'lts': 'L', 'l': 'L',
                                  'unidades': 'und', 'unidad': 'und', 'unds': 'und',
                                  'piezas': 'pza', 'pieza': 'pza', 'pzas': 'pza',
                                  'gramos': 'g', 'gramo': 'g', 'grs': 'g', 'g': 'g',
                                  'libras': 'lb', 'libra': 'lb', 'lbs': 'lb',
                                  'onzas': 'oz', 'onza': 'oz', 'oz': 'oz',
                                  'porciones': 'porcion', 'porcion': 'porcion',
                                  'paquetes': 'pqt', 'paquete': 'pqt',
                                  'bolsas': 'bolsa', 'bolsa': 'bolsa',
                                  'cajas': 'caja', 'caja': 'caja',
                                  'galones': 'gal', 'galon': 'gal'}
                    unidad = unidad_map.get(unidad_raw, unidad_raw)
                    
                    # Extraer motivo del resto del texto
                    motivo_texto = re.sub(
                        r'\d+(?:[.,]\d+)?\s*(?:kilos?|kg|litros?|unidades?|'
                        r'piezas?|gramos?|libras?|onzas?|paquetes?|bolsas?|'
                        r'cajas?|galones?|porciones?).*?(?:de|en|como|por)\s+merma',
                        '', parametros, flags=re.IGNORECASE
                    ).strip()
                    motivo = motivo_texto if motivo_texto else "Reportado como merma"
                    costo = 0.0
                else:
                    return "Formato: 'producto, cantidad, unidad, motivo, costo' o '23 kilos de cerdo de merma'"
            
            id_merma = db.registrar_merma(producto, cantidad, unidad, motivo, costo)
            return f"Merma registrada (ID: {id_merma}): {cantidad} {unidad} de {producto} - {motivo}"
        except (ValueError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    def _dar_de_baja(parametros: str) -> str:
        """Da de baja producto del inventario por rotura/dano.
        Input: 'producto, cantidad, unidad, motivo, costo'
        Ej: 'plato sopero, 5, piezas, rotura, 25.00'
        Ej: 'mantel blanco, 2, piezas, quemado, 30.00'"""
        try:
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) < 4:
                return "Formato: producto, cantidad, unidad, motivo, costo(opcional)"
            producto = partes[0]
            cantidad = float(partes[1])
            unidad = partes[2]
            motivo = partes[3]
            costo = float(partes[4]) if len(partes) > 4 and partes[4] else 0.0
            return db.dar_de_baja_inventario(producto, cantidad, unidad, motivo, costo)
        except (ValueError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    def _reporte_mermas(dias: str = "7") -> str:
        """Reporte de mermas/desperdicio. Input: dias (int, opcional, default 7)"""
        try:
            d = int(dias) if dias else 7
            mermas = db.obtener_mermas(d)
            totales = db.total_mermas_periodo(d)
            
            # Guardar contexto para exportación
            from agents.orchestrator import guardar_contexto_exportacion
            datos = [[m['fecha'], m['producto'], m['cantidad'], m['unidad'], m['motivo'], f"${m['costo_estimado']:.2f}" if m['costo_estimado'] else "$0.00"] for m in mermas]
            columnas = ["Fecha", "Producto", "Cantidad", "Unidad", "Motivo", "Costo"]
            guardar_contexto_exportacion(datos=datos, columnas=columnas, titulo=f"Reporte de Mermas ({d} días)")
            
            if not mermas:
                return f"No hay mermas registradas en los últimos {d} días."
            lineas = [f"REPORTE DE MERMAS (últimos {d} días)", "=" * 40]
            for m in mermas[:20]:
                costo = f" | ${m['costo_estimado']:.2f}" if m["costo_estimado"] else ""
                lineas.append(f"  {m['fecha']} - {m['producto']}: {m['cantidad']} {m['unidad']} ({m['motivo']}){costo}")
            lineas.extend(["", f"Total mermas: {totales['total_mermas']}", f"Costo total: ${totales['costo_total']:.2f}"])
            return "\n".join(lineas)
        except (ValueError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    def _generar_orden_compra(parametros: str) -> str:
        """Genera orden de compra a proveedor. Input: 'proveedor, producto, cantidad, unidad, costo_unitario(opcional), fecha_requerida(opcional)' Ej: 'Distribuidora ABC, pollo, 50, kg, 3.50, 2025-06-20'"""
        try:
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) < 4:
                return "Formato: proveedor, producto, cantidad, unidad, costo_unitario(opcional), fecha_requerida(opcional)"
            proveedor = partes[0]
            producto = partes[1]
            cantidad = float(partes[2])
            unidad = partes[3]
            costo = float(partes[4]) if len(partes) > 4 and partes[4] else 0.0
            fecha_req = partes[5] if len(partes) > 5 and partes[5] else ""
            id_orden = db.generar_orden_compra(proveedor, producto, cantidad, unidad, costo, "", fecha_req)
            return f"Orden de compra generada (ID: {id_orden}): {cantidad} {unidad} de {producto} a {proveedor} - ${costo:.2f}/unidad"
        except (ValueError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    def _ordenes_compra_pendientes(estado: str = "pendiente") -> str:
        """Lista órdenes de compra. Input: estado (str, opcional: pendiente/enviada/recibida/cancelada, default pendiente)"""
        try:
            ordenes = db.obtener_ordenes_compra(estado)
            if not ordenes:
                return f"No hay órdenes de compra en estado '{estado}'."
            lineas = [f"ORDENES DE COMPRA - {estado.upper()}", "=" * 40]
            for o in ordenes:
                costo = f" | ${o['costo_unitario']:.2f}/u" if o["costo_unitario"] else ""
                req = f" | Requerida: {o['fecha_requerida']}" if o["fecha_requerida"] else ""
                lineas.append(f"  #{o['id']} - {o['producto']}: {o['cantidad']} {o['unidad']} a {o['proveedor']}{costo}{req}")
            return "\n".join(lineas)
        except (sqlite3.Error, KeyError, TypeError) as e:
            return f"Error: {str(e)}"

    def _costo_real_vs_teorico(dias: str = "30") -> str:
        """Compara costo real vs teórico de ventas. Input: dias (int, opcional, default 30)"""
        try:
            d = int(dias) if dias else 30
            datos = db.costo_real_vs_teorico(d)
            if not datos:
                return f"No hay ventas registradas en los últimos {d} días."
            lineas = [f"COSTO REAL vs TEORICO (últimos {d} días)", "=" * 50]
            for item in datos:
                lineas.append(f"\n  {item['receta_nombre']}:")
                lineas.append(f"    Unidades: {item['unidades']} | Precio: ${item['precio_venta']:.2f}")
                lineas.append(f"    Costo real: ${item['costo_real_unitario']:.2f}/u")
                lineas.append(f"    Ingreso: ${item['ingreso_total']:.2f} | Costo total: ${item['costo_real_total']:.2f}")
                lineas.append(f"    Margen real: {item['margen_real']}%")
            total_ingresos = sum(d["ingreso_total"] for d in datos)
            total_costos = sum(d["costo_real_total"] for d in datos)
            lineas.extend(["", "-" * 50, f"TOTAL: ${total_ingresos:.2f} ingresos, ${total_costos:.2f} costos"])
            return "\n".join(lineas)
        except (ValueError, KeyError, TypeError) as e:
            return f"Error: {str(e)}"

    def _dashboard_ventas(dias: str = "7") -> str:
        """Dashboard de producción diaria y ventas. Input: dias (int, opcional, default 7)"""
        try:
            d = int(dias) if dias else 7
            prod_data = db.obtener_produccion_dashboard(d)
            ventas_data = db.obtener_ventas_dashboard(d)

            lineas = [f"DASHBOARD DE PRODUCCION (últimos {d} días)", "=" * 40]

            if prod_data["resumen"]:
                for r in prod_data["resumen"]:
                    icono = "🍳" if r["tipo"] == "cocido" else "📦"
                    lineas.append(f"  {icono} {r['tipo'].title()}: {r['cantidad_total']:.1f} {r['unidad']} ({r['total']} registros)")

            if prod_data["total_desperdicio"] > 0 or prod_data["total_almacenado"] > 0:
                lineas.extend(["", "♻️ Destino de sobrantes:"])
                lineas.append(f"  🗑️ Desperdicio: {prod_data['total_desperdicio']:.1f}")
                lineas.append(f"  📦 Almacenado: {prod_data['total_almacenado']:.1f}")

            if ventas_data["total_unidades"] > 0:
                lineas.extend(["", "💰 Ventas:"])
                lineas.append(f"  📊 Ingresos: ${ventas_data['total_ingresos']:.2f}")
                lineas.append(f"  💰 Ganancia: ${ventas_data['total_ganancia']:.2f}")

            if prod_data["detalle"]:
                lineas.extend(["", "📋 Detalle de producción:"])
                for item in prod_data["detalle"][:15]:
                    destino = ""
                    if item["destino"] == "desperdicio":
                        destino = " 🗑️"
                    elif item["destino"] == "almacenado":
                        destino = " 📦"
                    receta = f" ({item['receta_nombre']})" if item["receta_nombre"] else ""
                    lineas.append(f"  {item['fecha']} - {item['producto']}: {item['cantidad']:.1f} {item['unidad']}{receta}{destino}")

            return "\n".join(lineas)
        except (ValueError, KeyError, TypeError) as e:
            return f"Error: {str(e)}"

    def _registrar_produccion(parametros: str) -> str:
        """Registra producción diaria y sobrantes. Input: 'fecha=2025-06-15, cocido: SOP-021=30, PLF-018=20, sobrante: arroz=4.5|kg|no, ensalada=2|kg|si, bebida=1|litro|no'
        Formato sobrante: 'producto=cantidad|unidad|es_perecedero(si/no)'"""
        try:
            def _parse_sobrante_item(clave: str, valor: str) -> dict:
                partes_valor = [v.strip() for v in valor.split("|")]
                cantidad = partes_valor[0] if len(partes_valor) > 0 else "0"
                unidad = partes_valor[1] if len(partes_valor) > 1 else "kg"
                es_pere = 1 if len(partes_valor) > 2 and partes_valor[2].lower() in ("si", "s", "1", "true") else 0
                if not es_pere and db.determinar_perecedero(clave):
                    es_pere = 1
                return {"producto": clave.strip(), "cantidad": cantidad, "unidad": unidad, "es_perecedero": es_pere}

            partes = [p.strip() for p in parametros.split(",")]
            fecha = ""
            items_cocidos = []
            items_sobrantes = []
            modo = ""

            for parte in partes:
                if parte.startswith("fecha="):
                    fecha = parte.split("=", 1)[1].strip()
                    continue

                if ":" in parte:
                    sub_modo, sub_valor = [s.strip() for s in parte.split(":", 1)]
                    if sub_modo in ("cocido", "cocina") and "=" in sub_valor:
                        clave, valor = [s.strip() for s in sub_valor.split("=", 1)]
                        items_cocidos.append({"receta": clave, "producto": clave, "cantidad": valor, "unidad": "porciones"})
                        modo = "cocido"
                    elif sub_modo == "sobrante" and "=" in sub_valor:
                        clave, valor = [s.strip() for s in sub_valor.split("=", 1)]
                        items_sobrantes.append(_parse_sobrante_item(clave, valor))
                        modo = "sobrante"
                    continue

                if "=" in parte and modo:
                    clave, valor = [s.strip() for s in parte.split("=", 1)]
                    if modo == "cocido":
                        items_cocidos.append({"receta": clave, "producto": clave, "cantidad": valor, "unidad": "porciones"})
                    else:
                        items_sobrantes.append(_parse_sobrante_item(clave, valor))

            if not fecha:
                from datetime import date
                fecha = date.today().isoformat()

            if not items_cocidos and not items_sobrantes:
                return "Formato: fecha=2025-06-15, cocido: SOP-021=30, PLF-018=20, sobrante: arroz=4.5|kg|no, ensalada=2|kg|si"

            resultado = db.registrar_produccion(fecha, items_cocidos, items_sobrantes)
            lineas = ["PRODUCCION REGISTRADA", "=" * 40, f"Fecha: {fecha}"]
            lineas.append(f"\n  🍳 Cocidos: {resultado['cocidos']} recetas/items")
            lineas.append(f"  📦 Sobrantes: {resultado['sobrantes']} items")
            if resultado["desperdicios"] > 0:
                lineas.append(f"  🗑️ Desperdicio (perecedero): {resultado['desperdicios']} items")
            if resultado["almacenados"] > 0:
                lineas.append(f"  📦 Almacenado (no perecedero): {resultado['almacenados']} items")
            return "\n".join(lineas)
        except (ValueError, KeyError, TypeError) as e:
            return f"Error: {str(e)}"

    def _generar_reporte_diario(fecha: str = "") -> str:
        """Genera reporte diario oficial en Word con producción y sobrantes. Input: fecha (str, opcional) Ej: '2025-06-15'"""
        try:
            from agents.mcp_client import MCPClient
            from core.models import AccionOffice
            from datetime import date

            if not fecha:
                fecha = date.today().isoformat()

            prod = db.obtener_produccion_dashboard(1)
            cocidos = [
                i
                for i in prod["detalle"]
                if i["tipo"] == "cocido" and i["fecha"] == fecha
            ]
            sobrantes = [
                i
                for i in prod["detalle"]
                if i["tipo"] == "sobrante" and i["fecha"] == fecha
            ]

            contenido = []
            contenido.append("REPORTE DIARIO DE PRODUCCION")
            contenido.append(f"Fecha: {fecha}")
            contenido.append("")

            if cocidos:
                contenido.append("PRODUCCION DEL DIA:")
                for c in cocidos:
                    receta = (
                        f" ({c['receta_nombre']})"
                        if c["receta_nombre"]
                        else ""
                    )
                    contenido.append(
                        "  - "
                        + c["producto"]
                        + receta
                        + ": "
                        + f"{c['cantidad']:.1f}"
                        + " "
                        + c["unidad"]
                    )
            else:
                contenido.append("No se registro produccion para esta fecha.")
                contenido.append("Usa 'registrar_produccion' primero.")

            if sobrantes:
                contenido.append("")
                contenido.append("SOBRANTES:")
                for s in sobrantes:
                    destino = (
                        "DESPERDICIO"
                        if s["destino"] == "desperdicio"
                        else "ALMACENADO"
                    )
                    contenido.append(
                        "  - "
                        + s["producto"]
                        + ": "
                        + f"{s['cantidad']:.1f}"
                        + " "
                        + s["unidad"]
                        + " -> "
                        + destino
                    )

            contenido.append("")
            contenido.append(
                "Total desperdicio: "
                + f"{prod['total_desperdicio']:.1f}"
            )
            contenido.append(
                "Total almacenado: "
                + f"{prod['total_almacenado']:.1f}"
            )
            contenido.append("")
            contenido.append("--- Documento generado por ChefChat Pro ---")

            contenido_texto = "\n".join(contenido)

            cliente = MCPClient()
            resultado = cliente.ejecutar_herramienta(
                AccionOffice(
                    herramienta="word",
                    operacion="enviar",
                    ruta_archivo="",
                    payload={
                        "contenido": contenido_texto,
                        "formato": {
                            "titulo": f"Reporte Diario {fecha}",
                            "font_size": 12,
                            "font_name": "Calibri",
                        },
                    },
                    requiere_hitl=False,
                )
            )
            return f"Reporte diario generado en Word: {resultado.get('mensaje', 'OK')}"
        except (
            ImportError,
            KeyError,
            TypeError,
            AttributeError,
            ValueError,
            RuntimeError,
        ) as e:
            return f"Error: {str(e)}"

    def _alertas_stock_bajo(umbral: str = "10") -> str:
        """Revisa stock bajo y emite alertas.
        Input: umbral (int, opcional, default 10)
        """
        try:
            u = int(umbral) if umbral else 10
            alertas = db.alertas_stock_bajo(u)
            if not alertas:
                return f"✅ Stock OK: No hay productos por debajo de {u} unidades."
            lineas = [
                f"⚠️ ALERTAS DE STOCK BAJO (umbral: {u} unidades)",
                "=" * 40,
            ]
            for a in alertas:
                icon = "🔴" if a["stock_total"] < u * 0.5 else "🟡"
                lineas.append(
                    f"  {icon} {a['nombre']}: "
                    f"{a['stock_total']:.1f} {a['unidad']} "
                    f"({a['categoria']})"
                )
            return "\n".join(lineas)
        except (TypeError, ValueError) as e:
            return f"Error: {str(e)}"

    def _asignar_turnos(parametros: str) -> str:
        """Asigna turnos de cocina.
        Input: 'fecha, cocinero, estacion, hora_inicio, hora_fin, receta(opcional)'
        Ej: '2025-06-15, Juan Perez, platos_fuertes, 08:00, 16:00, SOP-021'
        """
        try:
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) < 5:
                return (
                    "Formato: fecha, cocinero, estacion, hora_inicio, "
                    "hora_fin, receta(opcional)"
                )
            fecha = partes[0]
            cocinero = partes[1]
            estacion = (
                partes[2]
                .lower()
                .replace(" ", "_")
            )
            hora_ini = partes[3]
            hora_fin = partes[4]
            receta = partes[5] if len(partes) > 5 else ""
            estaciones_validas = {
                "entradas",
                "sopas",
                "platos_fuertes",
                "postres",
                "plancha",
                "parrilla",
                "vegetales",
                "limpieza",
            }
            if estacion not in estaciones_validas:
                return (
                    f"Estación inválida: {estacion}. "
                    f"Válidas: {', '.join(sorted(estaciones_validas))}"
                )
            id_turno = db.asignar_turno(
                fecha,
                cocinero,
                estacion,
                hora_ini,
                hora_fin,
                receta,
            )
            return (
                f"Turno asignado (ID: {id_turno}): {cocinero} "
                f"en {estacion} ({hora_ini}-{hora_fin})"
            )
        except (TypeError, ValueError) as e:
            return f"Error: {str(e)}"

    def _ver_turnos(fecha: str = "") -> str:
        """Ver turnos de cocina.
        Input: fecha (str, opcional, default hoy)
        Ej: '2025-06-15'"""
        try:
            turnos = db.obtener_turnos(fecha)
            if not turnos:
                return f"No hay turnos para {fecha or 'hoy'}."
            lineas = [
                f"TURNOS DE COCINA - {fecha or 'HOY'}",
                "=" * 40,
            ]
            for t in turnos:
                receta = (
                    f" | {t['receta_asignada']}"
                    if t["receta_asignada"]
                    else ""
                )
                notas = (
                    f" | {t['notas']}"
                    if t["notas"]
                    else ""
                )
                estacion = t["estacion"].replace("_", " ").title()
                lineas.append(
                    f"  {t['cocinero']} - {estacion}: "
                    f"{t['hora_inicio']}-{t['hora_fin']}"
                    f"{receta}{notas}"
                )
            return "\n".join(lineas)
        except sqlite3.Error as e:
            return f"Error: {str(e)}"

    def _registrar_compra(parametros: str) -> str:
        """Registra compra en lenguaje natural. Input: 'se compro 3 kintales de harina caduca 12-03-2027'."""
        try:
            import re
            p = parametros.lower()
            cantidad = 1.0
            unidad = ""
            producto = ""
            fecha_cad = ""
            # Buscar fecha de caducidad en todo el texto
            match_cad_global = re.search(
                r'(?:caducidad|caduc[oa]|vence|expira|vencimiento)\s*(?:el\s+)?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2})',
                p
            )
            if match_cad_global:
                fecha_cad = match_cad_global.group(1)
                # Limpiar el texto de la fecha
                p_clean = p[:match_cad_global.start()].strip()
                p_clean = re.sub(r'\s*(?:caducidad|caduc[oa]|vence|expira|vencimiento)\s*$', '', p_clean).strip()
            else:
                p_clean = p

            match_cant = re.search(r'(\d+(?:\.\d+)?)\s*(kintales|kintal|quintales|quintal|qq|kilos|kilo|kg|libras|libra|lbs|lb|gramos|gramo|gr|onzas|onza|oz|litros|litro|lts|galones|galon|unidades|unidad|unds|piezas|pieza|pzas|paquetes|paquete|bolsas|bolsa|cajas|caja)\b', p_clean)
            if match_cant:
                cantidad = float(match_cant.group(1))
                unidad = match_cant.group(2)
                idx = match_cant.end()
                resto = p_clean[idx:]
                match_prod = re.match(r'\s*(?:de\s+)?(.+)', resto)
                if match_prod:
                    producto = match_prod.group(1).strip()
            else:
                match_simple = re.search(r'(?:compr[oa]|compre)\s+(\d+(?:\.\d+)?)\s*(.+)', p_clean)
                if match_simple:
                    cantidad = float(match_simple.group(1))
                    resto = match_simple.group(2).strip()
                    match_prod = re.match(r'(kintales|kintal|quintales|quintal|qq|kilos|kilo|kg|libras|libra|lbs|lb|gramos|gramo|gr|onzas|onza|oz|litros|litro|lts|galones|galon|unidades|unidad|unds|piezas|pieza|pzas|paquetes|paquete|bolsas|bolsa|cajas|caja)\s+(?:de\s+)?(.+)', resto)
                    if match_prod:
                        unidad_match = re.match(r'(kintales|kintal|quintales|quintal|qq|kilos|kilo|kg|libras|libra|lbs|lb|gramos|gramo|gr|onzas|onza|oz|litros|litro|lts|galones|galon|unidades|unidad|unds|piezas|pieza|pzas|paquetes|paquete|bolsas|bolsa|cajas|caja)', resto)
                        if unidad_match:
                            unidad = unidad_match.group(1)
                        producto = match_prod.group(1).strip()
                    else:
                        producto = resto
                else:
                    producto = p_clean
            if not producto:
                return "No se pudo detectar el producto. Intenta: 'se compro 3 kintales de harina caduca 12-03-2027'"
            if not unidad:
                unidad = "unidad"
            # Limpiar sufijos de fecha del nombre del producto
            producto = re.sub(r'\s*(?:caduc[oa]|vence|expira)\s*$', '', producto).strip()
            producto = re.sub(r'\s*de\s*$', '', producto).strip()
            categoria = _detectar_categoria(producto)
            vida = _estimar_vida_util(producto)
            
            # Normalizar unidad
            unidad_map = {
                'kintal': 'qq', 'kintales': 'qq', 'quintal': 'qq', 'quintales': 'qq', 'qq': 'qq',
                'kilo': 'kg', 'kilos': 'kg', 'kg': 'kg',
                'libra': 'lb', 'libras': 'lb', 'lb': 'lb', 'lbs': 'lb',
                'gramo': 'g', 'gramos': 'g', 'g': 'g',
                'onza': 'oz', 'onzas': 'oz', 'oz': 'oz',
                'litro': 'L', 'litros': 'L', 'l': 'L',
                'galon': 'gal', 'galones': 'gal', 'gal': 'gal',
                'unidad': 'und', 'unidades': 'und', 'u': 'und', 'und': 'und',
            }
            unidad_norm = unidad_map.get(unidad.lower(), 'und')
            
            # Formatear fecha de caducidad (acepta DD-MM-YYYY, YYYY-MM-DD, DD/MM/YYYY)
            fecha_cad_fija = None
            if fecha_cad:
                partes_f = re.split(r'[-/]', fecha_cad)
                if len(partes_f) == 3:
                    if len(partes_f[0]) == 4:
                        fecha_cad_fija = f"{partes_f[0]}-{partes_f[1].zfill(2)}-{partes_f[2].zfill(2)}"
                    else:
                        d, m, a = partes_f
                        if len(a) == 2:
                            a = '20' + a
                        fecha_cad_fija = f"{a}-{m.zfill(2)}-{d.zfill(2)}"
            
            # Insertar en catalogo si no existe
            conn = _obtener_conexion(db)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Catalogo WHERE LOWER(nombre) = ?", (producto.lower(),))
            cat = cursor.fetchone()
            if cat:
                producto_id = cat[0]
                producto_nuevo = False
            else:
                cursor.execute("INSERT INTO Catalogo (nombre, categoria, vida_util_dias) VALUES (?, ?, ?)",
                             (producto.strip().title(), categoria, vida))
                producto_id = cursor.lastrowid
                producto_nuevo = True
            
            # Insertar en Inventario
            from datetime import date as dt_date
            fecha_ingreso = dt_date.today().strftime('%Y-%m-%d')
            id_lote = f"COMPRA-{dt_date.today().strftime('%Y%m%d')}-{producto[:3].upper()}"
            cursor.execute("""
                INSERT INTO Inventario 
                (producto_id, id_lote, fecha_ingreso, cantidad_actual, unidad, fecha_caducidad_fija)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (producto_id, id_lote, fecha_ingreso, cantidad, unidad_norm, fecha_cad_fija))
            id_inv = cursor.lastrowid
            conn.commit()
            conn.close()
            
            lineas = [f"COMPRA REGISTRADA (ID: {id_inv})", "=" * 40,
                      f"  Producto: {producto.strip().title()}", f"  Cantidad: {cantidad} {unidad_norm}",
                      f"  Categoria: {categoria}", f"  Vida util est: {vida} dias"]
            if fecha_cad_fija:
                lineas.append(f"  Caduca: {fecha_cad_fija}")
            if producto_nuevo:
                lineas.append(f"  [NUEVO] Producto agregado al catalogo")
            return "\n".join(lineas)
        except (ValueError, TypeError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    def _registrar_permiso_rapido(parametros: str) -> str:
        """Registra permiso/ausencia en lenguaje natural. Input: 'juan saco permiso por paternidad 6 dias'."""
        try:
            import re
            from datetime import date, datetime, timedelta
            p = parametros.lower()
            id_emp = ""
            nombre = ""
            tipo = "permiso_personal"
            dias_ausencia = 1
            match_id = re.search(r'\b(emp\d+)\b', p, re.IGNORECASE)
            if match_id:
                id_emp = match_id.group(1).upper()
            else:
                trabajadores = db.obtener_trabajadores("")
                for t in trabajadores:
                    if t['nombre_completo'].lower() in p:
                        id_emp = t['id_empleado']
                        nombre = t['nombre_completo']
                        break
                if not id_emp:
                    palabras = parametros.split()
                    conn = _obtener_conexion(db)
                    cursor = conn.cursor()
                    for palabra in palabras:
                        if len(palabra) > 2:
                            cursor.execute("SELECT id_empleado, nombre_completo FROM Trabajadores WHERE LOWER(nombre_completo) LIKE LOWER(?)", (f"%{palabra}%",))
                            row = cursor.fetchone()
                            if row:
                                id_emp = row[0]
                                nombre = row[1]
                                break
                    conn.close()
            if not id_emp:
                return "Empleado no encontrado. Usa ID (EMP001) o nombre 'Juan Perez'."
            match_dias = re.search(r'(\d+)\s*(?:dias|días|dia|día)', p)
            if match_dias:
                dias_ausencia = int(match_dias.group(1))
            tipos = {'reposo': 'reposo_medico', 'medico': 'reposo_medico', 'médico': 'reposo_medico',
                     'maternidad': 'permiso_maternidad', 'paternidad': 'permiso_personal',
                     'vacaciones': 'vacaciones', 'vacacion': 'vacaciones',
                     'personal': 'permiso_personal', 'permiso': 'permiso_personal',
                     'duelo': 'permiso_personal', 'luto': 'permiso_personal'}
            for k, v in tipos.items():
                if k in p:
                    tipo = v
                    break
            fecha_ini = date.today().isoformat()
            fecha_fin = (date.today() + timedelta(days=dias_ausencia)).isoformat()
            match_ini = re.search(r'(?:desde|del?)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', p)
            if match_ini:
                try:
                    fecha_ini = datetime.strptime(match_ini.group(1), '%d-%m-%Y').strftime('%Y-%m-%d')
                    fecha_fin = (datetime.strptime(fecha_ini, '%Y-%m-%d') + timedelta(days=dias_ausencia)).strftime('%Y-%m-%d')
                except ValueError:
                    pass
            match_fin = re.search(r'(?:hasta|al?)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', p)
            if match_fin:
                try:
                    fecha_fin = datetime.strptime(match_fin.group(1), '%d-%m-%Y').strftime('%Y-%m-%d')
                except ValueError:
                    pass
            motivo = ""
            match_motivo = re.search(r'por\s+(\w+(?:\s+\w+){0,3})', p)
            if match_motivo:
                motivo = match_motivo.group(1).strip()
            resultado = db.registrar_ausencia(id_emp, tipo, fecha_ini, fecha_fin, motivo)
            return f"Permiso registrado: {nombre or id_emp} ({tipo}) {fecha_ini} -> {fecha_fin} ({dias_ausencia} dias)"
        except (ValueError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    def _consultar_turno_hoy(turno: str = "") -> str:
        """Consulta personal que trabaja hoy. Input: turno (str, opcional). Ej: 'matutino'."""
        try:
            personal = db.obtener_turno_hoy(turno)
            if not personal:
                return f"No hay personal trabajando hoy{' en turno ' + turno if turno else ''}."
            filtro = f"TURNO {turno.upper()}" if turno else "TODOS LOS TURNOS"
            lineas = [f"PERSONAL DE HOY - {filtro}", "=" * 40]
            for t in personal:
                tipo = t.get('tipo_contrato', 'fijo')
                lineas.append(f"  {t['id_empleado']} - {t['nombre_completo']} ({t['cargo']})")
                lineas.append(f"    Turno: {t['turno']} | {t.get('hora_entrada', '')}-{t.get('hora_salida', '')} | Contrato: {tipo}")
            lineas.append(f"\nTotal: {len(personal)} trabajadores activos")
            return "\n".join(lineas)
        except (sqlite3.Error, KeyError, AttributeError) as e:
            return f"Error: {str(e)}"

    def _consultar_personal_activo() -> str:
        """Lista personal activo (no ausente). Sin input."""
        try:
            personal = db.obtener_personal_activo()
            if not personal:
                return "No hay personal activo registrado."
            lineas = ["PERSONAL ACTIVO", "=" * 40]
            for t in personal:
                tipo = t.get('tipo_contrato', 'fijo')
                lineas.append(f"  {t['id_empleado']} - {t['nombre_completo']} ({t['cargo']})")
                lineas.append(f"    Turno: {t['turno']} | {t.get('hora_entrada', '')}-{t.get('hora_salida', '')} | Contrato: {tipo}")
            lineas.append(f"\nTotal: {len(personal)} trabajadores activos")
            return "\n".join(lineas)
        except (sqlite3.Error, KeyError, AttributeError) as e:
            return f"Error: {str(e)}"

    def _consultar_personal_ausente() -> str:
        """Lista personal con ausencias (reposo, maternidad, etc.). Sin input."""
        try:
            ausentes = db.obtener_personal_con_ausencia()
            if not ausentes:
                return "No hay personal con ausencias registradas."
            lineas = ["PERSONAL CON AUSENCIAS", "=" * 40]
            for a in ausentes:
                estado = a.get('estado', 'desconocido')
                inicio = a.get('fecha_inicio_ausencia', 'N/A')
                fin = a.get('fecha_fin_ausencia', 'N/A')
                motivo = a.get('motivo_ausencia', '')
                lineas.append(f"  {a['id_empleado']} - {a.get('nombre_completo', '?')} ({a.get('cargo', '')})")
                lineas.append(f"    Estado: {estado} | {inicio} -> {fin}")
                if motivo:
                    lineas.append(f"    Motivo: {motivo}")
            lineas.append(f"\nTotal: {len(ausentes)} con ausencias")
            return "\n".join(lineas)
        except (sqlite3.Error, KeyError, AttributeError) as e:
            return f"Error: {str(e)}"

    def _registrar_ausencia(parametros: str) -> str:
        """Registra ausencia. Input: 'id_empleado, tipo, fecha_inicio, fecha_fin, motivo(opcional)'. Tipos: reposo_medico, permiso_maternidad, vacaciones, permiso_personal"""
        try:
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) < 4:
                return "Formato: id_empleado, tipo, fecha_inicio, fecha_fin, motivo(opcional)"
            id_emp = partes[0]
            tipo = partes[1].lower().replace(" ", "_")
            fecha_ini = partes[2]
            fecha_fin = partes[3]
            motivo = partes[4] if len(partes) > 4 else ""
            tipos_validos = ['reposo_medico', 'permiso_maternidad', 'vacaciones', 'permiso_personal']
            if tipo not in tipos_validos:
                return f"Tipo invalido: {tipo}. Validos: {', '.join(tipos_validos)}"
            resultado = db.registrar_ausencia(id_emp, tipo, fecha_ini, fecha_fin, motivo)
            return f"Ausencia registrada para {id_emp}: {tipo} ({fecha_ini} -> {fecha_fin})"
        except (sqlite3.Error, ValueError) as e:
            return f"Error: {str(e)}"

    def _reincorporar_trabajador(id_empleado: str) -> str:
        """Reincorpora trabajador tras ausencia. Input: id_empleado. Ej: 'EMP001'"""
        try:
            resultado = db.reincorporar_trabajador(id_empleado.strip())
            return resultado
        except (sqlite3.Error, ValueError) as e:
            return f"Error: {str(e)}"

    def _seed_mermas(dias: str = "30") -> str:
        """Genera datos realistas de mermas de restaurante. Input: dias (int, opcional, default 30). Ej: '30'"""
        try:
            d = int(dias) if dias else 30
            return db.seed_mermas_realistas(d)
            return f"Datos de mermas generados: {resultado}"
        except (ValueError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # TRABAJADORES Y SOBRANTES REUTILIZABLES
    # =========================================================================

    def _registrar_trabajador(parametros: str) -> str:
        """Registra un trabajador.
        Input: 'ID, nombre, cargo, turno,
        hora_entrada, hora_salida, dias_descanso(opcional)'
        Ej: 'EMP001, Juan Perez, Cocinero,
        matutino, 08:00, 16:00, Sabado-Domingo'"""
        try:
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) < 6:
                return (
                    "Formato: ID, nombre, cargo, turno, "
                    "hora_entrada, hora_salida, "
                    "dias_descanso(opcional)"
                )
            id_emp = partes[0]
            nombre = partes[1]
            cargo = partes[2]
            turno = partes[3]
            h_entrada = partes[4]
            h_salida = partes[5]
            descanso = partes[6] if len(partes) > 6 else ""
            tipo_contrato = partes[7] if len(partes) > 7 else ""
            estado = partes[8] if len(partes) > 8 else "activo"
            fecha_inicio = partes[9] if len(partes) > 9 else ""
            fecha_fin = partes[10] if len(partes) > 10 else ""
            return db.registrar_trabajador(
                id_emp,
                nombre,
                cargo,
                turno,
                h_entrada,
                h_salida,
                descanso,
                tipo_contrato,
                estado,
                fecha_inicio,
                fecha_fin,
            )
        except sqlite3.Error as e:
            return f"Error: {str(e)}"

    def _listar_trabajadores(turno: str = "") -> str:
        """Lista trabajadores. Input: turno (str, opcional). Ej: 'matutino'"""
        try:
            trabajadores = db.obtener_trabajadores(turno)
            if not trabajadores:
                return "No hay trabajadores registrados."
            from datetime import date
            hoy = date.today().isoformat()
            ausentes = db.obtener_personal_ausente(hoy)
            ids_ausentes = set(a['id_empleado'] for a in ausentes) if ausentes else set()
            lineas = [
                "TRABAJADORES",
                "=" * 40,
            ]
            for t in trabajadores:
                estado = t.get('estado', 'activo')
                ausente = " [AUSENTE]" if t['id_empleado'] in ids_ausentes else ""
                lineas.append(
                    f"  {t['id_empleado']} - "
                    f"{t['nombre_completo']} ({t['cargo']}){ausente}"
                )
                lineas.append(
                    f"    Turno: {t['turno']} | "
                    f"{t.get('hora_entrada', '')}-{t.get('hora_salida', '')} | "
                    f"Descanso: {t.get('dias_descanso') or 'N/A'} | "
                    f"Estado: {estado}"
                )
            return "\n".join(lineas)
        except sqlite3.Error as e:
            return f"Error: {str(e)}"

    def _registrar_sobrante(parametros: str) -> str:
        """Registra sobrante reutilizable.
        Input: 'producto, cantidad, unidad, id_empleado, turno,
        dias_reutilizacion_sanitaria'
        Ej: 'arroz cocido, 4.5, kg, EMP001, matutino, 2'"""
        try:
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) < 3:
                return (
                    "Formato: producto, cantidad, unidad, "
                    "id_empleado(opcional), turno(opcional), "
                    "dias_reutilizacion(opcional)"
                )
            producto = partes[0]
            cantidad = float(partes[1])
            unidad = partes[2]
            id_emp = partes[3] if len(partes) > 3 else ""
            turno = partes[4] if len(partes) > 4 else ""
            dias = int(partes[5]) if len(partes) > 5 and partes[5] else 1
            id_sob = db.registrar_sobrante(
                producto, cantidad, unidad, id_emp, turno, dias
            )
            return (
                f"Sobrante registrado (ID: {id_sob}): "
                f"{cantidad} {unidad} de {producto}"
            )
        except (ValueError, TypeError) as e:
            return f"Error: {str(e)}"

    def _dashboard_sobrantes(dias: str = "7") -> str:
        """Dashboard de sobrantes por turno y día. Input: dias (int, opcional, default 7)"""
        try:
            d = int(dias) if dias else 7
            data = db.dashboard_sobrantes(d)
            lineas = [f"DASHBOARD DE SOBRANTES (últimos {d} días)", "=" * 50]

            if data["sobrantes_por_turno"]:
                lineas.extend(["", "SOBRANTES POR TURNO Y DÍA:"])
                for row in data["sobrantes_por_turno"]:
                    lineas.append(f"  {row['fecha_registro']} | {row['turno'] or 'N/A'} | {row['total_sobrantes']} items | {row['cantidad_total']:.1f} total")
            else:
                lineas.append("\n  No hay sobrantes registrados en el período.")

            if data["destinos"]:
                lineas.extend(["", "DESTINO DE SOBRANTES:"])
                for row in data["destinos"]:
                    lineas.append(f"  {row['destino_actual']}: {row['total']} registros ({row['cantidad_total']:.1f} total)")

            if data.get("desperdicio_por_dia"):
                lineas.extend(["", "DESPERDICIO POR DÍA:"])
                for row in data["desperdicio_por_dia"]:
                    detalle = (
                        f"  {row['fecha_registro']}: "
                        f"{row['desperdicio_kilos']:.1f} kg desperdicio / "
                        f"{row['total_kilos']:.1f} kg total"
                    )
                    lineas.append(detalle)

            if data["top_productos"]:
                lineas.extend(["", "TOP 5 PRODUCTOS:"])
                for row in data["top_productos"][:5]:
                    detalle = (
                        f"  {row['producto_sopro']}: "
                        f"{row['cantidad_total']:.1f} {row['unidad']} "
                        f"({row['veces_registrado']} veces)"
                    )
                    lineas.append(detalle)

            maximos = data.get("desperdicio_por_dia", [])
            if maximos:
                peor_dia = max(maximos, key=lambda x: x["desperdicio_kilos"])
                detalle = (
                    f"⚠️ Peor día: {peor_dia['fecha_registro']} "
                    f"({peor_dia['desperdicio_kilos']:.1f} kg desperdicio)"
                )
                lineas.extend(["", detalle])

            lineas.extend(["", "Para exportar a Excel con gráficos usa: exportar_dashboard_sobrantes"])
            return "\n".join(lineas)
        except (ValueError, KeyError, TypeError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    def _exportar_dashboard_sobrantes(dias: str = "7") -> str:
        """Exporta dashboard de sobrantes a archivo CSV para Excel. Input: dias (int, opcional, default 7)"""
        try:
            d = int(dias) if dias else 7
            filepath = db.exportar_dashboard_sobrantes_excel(d)
            return f"Dashboard exportado a Excel: {filepath}"
        except (ValueError, sqlite3.Error) as e:
            return f"Error: {str(e)}"

    # =========================================================================
    # MENU SEMANAL
    # =========================================================================

    def _consultar_menu_semanal(pregunta: str = "") -> str:
        """Consulta el menu semanal. Input: pregunta (str, opcional). Ej: 'menu del lunes', 'precios', 'preparacion'"""
        try:
            from data.menu_semanal import MenuSemanalManager
            mgr = MenuSemanalManager()
            if not pregunta:
                return mgr.consultar_menu("menu completo")
            return mgr.consultar_menu(pregunta)
        except Exception as e:
            return f"Error: {str(e)}"

    def _agregar_plato_menu(parametros: str) -> str:
        """Agrega plato al menu semanal. Input: 'dia, servicio, nombre, precio, prep_previa'. Ej: 'Lunes, almuerzo, Arroz con Pollo, 8.50, No'"""
        try:
            from data.menu_semanal import MenuSemanalManager
            mgr = MenuSemanalManager()
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) < 3:
                return "Formato: dia, servicio, nombre, precio(opcional), prep_previa(Si/No)"
            dia = partes[0]
            servicio = partes[1]
            nombre = partes[2]
            precio = float(partes[3]) if len(partes) > 3 else 0.0
            prep = partes[4] if len(partes) > 4 else "No"
            id_plan = mgr.agregar_plato(dia, servicio, nombre, precio, prep)
            return f"Plato agregado al menu (ID: {id_plan}): {nombre} - {dia} {servicio}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _agregar_receta_al_menu(parametros: str) -> str:
        """Agrega receta existente de RAG al menu. Input: 'dia, servicio, receta_id, precio(opcional), prep_previa'. Ej: 'Lunes, almuerzo, PLF-018, 8.50, No'"""
        try:
            from data.menu_semanal import MenuSemanalManager
            mgr = MenuSemanalManager()
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) < 3:
                return "Formato: dia, servicio, receta_id, precio(opcional), prep_previa(Si/No)"
            dia = partes[0]
            servicio = partes[1]
            receta_id = partes[2]
            precio = float(partes[3]) if len(partes) > 3 else None
            prep = partes[4] if len(partes) > 4 else "No"
            id_plan = mgr.agregar_receta_al_menu(dia, servicio, receta_id, precio, prep)
            if id_plan:
                return f"Receta agregada al menu (ID: {id_plan}): {receta_id} - {dia} {servicio}"
            return f"Receta '{receta_id}' no encontrada en RAG."
        except Exception as e:
            return f"Error: {str(e)}"

    def _buscar_recetas_para_menu(query: str) -> str:
        """Busca recetas en RAG para agregar al menu. Input: termino de busqueda. Ej: 'pollo', 'sopa', 'postre'"""
        try:
            from data.menu_semanal import MenuSemanalManager
            mgr = MenuSemanalManager()
            recetas = mgr.buscar_recetas_rag(query)
            if not recetas:
                return f"No se encontraron recetas con: {query}"
            lineas = [f"RECETAS ENCONTRADAS ({len(recetas)}):", "=" * 40]
            for r in recetas[:15]:
                lineas.append(f"  {r['id_receta']}: {r['nombre']} ({r['categoria']}) - Costo: ${r['costo']:.2f}")
            return "\n".join(lineas)
        except Exception as e:
            return f"Error: {str(e)}"

    def _modificar_plato_menu(parametros: str) -> str:
        """Modifica plato del menu. Input: 'id_plan, campo=nuevo_valor'. Ej: '5, nombre=Arroz con Pollo Peruano, precio=9.50'"""
        try:
            from data.menu_semanal import MenuSemanalManager
            mgr = MenuSemanalManager()
            partes = [p.strip() for p in parametros.split(",")]
            if len(partes) < 2:
                return "Formato: id_plan, campo1=valor1, campo2=valor2"
            id_plan = int(partes[0])
            updates = {}
            for parte in partes[1:]:
                if "=" in parte:
                    k, v = parte.split("=", 1)
                    updates[k.strip().lower()] = v.strip()
            kwargs = {}
            if "dia" in updates or "dia_semana" in updates:
                kwargs["dia_semana"] = updates.get("dia", updates.get("dia_semana"))
            if "servicio" in updates or "tipo_servicio" in updates:
                kwargs["tipo_servicio"] = updates.get("servicio", updates.get("tipo_servicio"))
            if "nombre" in updates or "nombre_plato" in updates:
                kwargs["nombre_plato"] = updates.get("nombre", updates.get("nombre_plato"))
            if "precio" in updates:
                kwargs["precio"] = float(updates["precio"])
            if "prep" in updates or "prep_previa" in updates:
                kwargs["prep_previa"] = updates.get("prep", updates.get("prep_previa"))
            if mgr.modificar_plato(id_plan, **kwargs):
                return f"Plato {id_plan} modificado correctamente."
            return f"No se pudo modificar el plato {id_plan}."
        except Exception as e:
            return f"Error: {str(e)}"

    def _eliminar_plato_menu(id_plan: str) -> str:
        """Elimina plato del menu. Input: id_plan (int). Ej: 5"""
        try:
            from data.menu_semanal import MenuSemanalManager
            mgr = MenuSemanalManager()
            if mgr.eliminar_plato(int(id_plan)):
                return f"Plato {id_plan} eliminado del menu."
            return f"No se encontro el plato {id_plan}."
        except Exception as e:
            return f"Error: {str(e)}"

    def _reset_menu_semanal() -> str:
        """Resetea todo el menu semanal."""
        try:
            from data.menu_semanal import MenuSemanalManager
            mgr = MenuSemanalManager()
            count = mgr.reset_menu()
            return f"Menu semanal reseteado. {count} platos eliminados."
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
        Tool(name="sugerir_menu_por_ingredientes", func=_sugerir_menu_por_ingredientes,
             description="Sugiere menu completo basado en ingredientes. Input: ingredientes separados por coma (str). Ej: 'pollo, queso, arroz'"),
        Tool(name="planificar_evento", func=_planificar_evento,
             description="Planifica evento completo: menú, escalado, inventario y faltantes. Input: 'fecha=2025-06-15, comensales=50, ingredientes=pollo, arroz' o 'fecha=..., comensales=..., recetas=SOP-021,PLF-018'"),
        
        # Agente Inventario
        Tool(name="productos_por_caducar", func=_productos_por_caducar,
             description="Productos que caducan en N días. Input: dias (int). Ej: 3"),
        Tool(name="consultar_productos_por_caducar", func=_consultar_productos_por_caducar,
             description="Consulta productos por caducar (default 7 días). Sin input o input: dias (int). Ej: 7"),
        Tool(name="verificar_stock_bajo", func=_verificar_stock_bajo,
             description="Productos con stock bajo. Input: umbral (float, opcional). Ej: 10"),
        Tool(name="registrar_uso_inventario", func=_registrar_uso_inventario,
             description="Registra uso de ingrediente. Input: nombre_item, cantidad. Ej: 'Fresa', 2.5"),
        
        # Agente Menú
        Tool(name="menu_anti_desperdicio", func=_menu_anti_desperdicio,
             description="Sugiere menú para usar productos por caducar. Sin input."),
        Tool(name="generar_lista_compras", func=_generar_lista_compras,
             description="Lista compras para evento. Input: recetas_csv, comensales. Ej: 'REC001,REC002', 50"),
        
        # Menu Semanal
        Tool(name="consultar_menu_semanal", func=_consultar_menu_semanal,
             description="Consulta menu semanal. Input: pregunta (str, opcional). Ej: 'menu del lunes', 'precios', 'menu completo'"),
        Tool(name="agregar_plato_menu", func=_agregar_plato_menu,
             description="Agrega plato al menu semanal. Input: 'dia, servicio, nombre, precio, prep_previa'. Ej: 'Lunes, almuerzo, Arroz con Pollo, 8.50, No'"),
        Tool(name="agregar_receta_al_menu", func=_agregar_receta_al_menu,
             description="Agrega receta de RAG al menu. Input: 'dia, servicio, receta_id, precio, prep_previa'. Ej: 'Lunes, almuerzo, PLF-018, 8.50, No'"),
        Tool(name="buscar_recetas_para_menu", func=_buscar_recetas_para_menu,
             description="Busca recetas en RAG para menu. Input: termino. Ej: 'pollo', 'sopa', 'postre'"),
        Tool(name="modificar_plato_menu", func=_modificar_plato_menu,
             description="Modifica plato del menu. Input: 'id_plan, campo=valor'. Ej: '5, nombre=Arroz con Pollo Peruano, precio=9.50'"),
        Tool(name="eliminar_plato_menu", func=_eliminar_plato_menu,
             description="Elimina plato del menu. Input: id_plan (int). Ej: 5"),
        Tool(name="reset_menu_semanal", func=_reset_menu_semanal,
             description="Resetea todo el menu semanal. Sin input."),
        
        # Agente Incidencias
        Tool(name="registrar_incidencia", func=_registrar_incidencia,
             description="Registra incidencia. Input: categoria, descripcion. Ej: 'Inventario', 'Falta leche'"),
        Tool(name="analizar_rentabilidad", func=_analizar_rentabilidad,
             description="Analiza rentabilidad del menú. Sin input."),

        # Herramientas Office (COM)
        Tool(name="enviar_receta_a_word", func=_enviar_a_word,
             description="Envía receta al documento activo de Word. Input: receta_id o nombre (str)."),
        Tool(name="enviar_receta_a_excel", func=_enviar_a_excel,
             description="Envía receta como tabla a Excel activo. Input: receta_id o nombre (str)."),
        Tool(name="enviar_menu_a_powerpoint", func=_enviar_menu_a_powerpoint,
             description="Envía menú a PowerPoint como diapositiva. Input: recetas separadas por coma (str). Ej: 'SOP-021,PLF-045'"),
        Tool(name="enviar_lista_compras_a_word", func=_enviar_lista_compras_a_word,
             description="Envía lista de compras a Word. Input: recetas (str), comensales (int, opcional). Ej: 'SOP-021,PLF-045', 50"),
        Tool(name="enviar_lista_compras_a_excel", func=_enviar_lista_compras_a_excel,
             description="Envía lista de compras a Excel. Input: recetas (str), comensales (int, opcional). Ej: 'SOP-021,PLF-045', 50"),
        Tool(name="enviar_reporte_mermas_a_word", func=_enviar_reporte_mermas_a_word,
             description="Envía reporte de mermas a Word. Input: dias (int, opcional, default 7). Ej: '30'"),
        Tool(name="enviar_reporte_mermas_a_excel", func=_enviar_reporte_mermas_a_excel,
             description="Envía reporte de mermas a Excel. Input: dias (int, opcional, default 7). Ej: '30'"),
        Tool(name="enviar_inventario_a_word", func=_enviar_inventario_a_word,
             description="Envía inventario actual a Word. Sin input."),
        Tool(name="enviar_inventario_a_excel", func=_enviar_inventario_a_excel,
             description="Envía inventario actual a Excel. Sin input."),
        Tool(name="enviar_productos_por_caducar_a_excel", func=_enviar_productos_por_caducar_a_excel,
             description="Envía productos próximos a caducar a Excel. Sin input."),

        # Herramientas Plantillas
        Tool(name="listar_plantillas", func=_listar_plantillas,
             description="Lista las plantillas disponibles en el directorio de plantillas. Sin input."),
        Tool(name="usar_plantilla", func=_usar_plantilla,
             description="Aplica plantilla Word/PPT reemplazando placeholders {{...}} con datos. Input: 'plantilla.docx | nombre=Juan, fecha=15 Junio'"),

        # Nuevas Funciones
        Tool(name="menu_diario", func=_menu_diario,
             description="Muestra el menú del día según configuración semanal. Sin input."),
        Tool(name="configurar_menu_semanal", func=_configurar_menu_semanal,
             description="Configura el menú semanal. Input: 'Lunes | entrante=SOP-021, plato_fuerte=PLF-018, postre=POS-006'"),
        Tool(name="registrar_merma", func=_registrar_merma,
             description="Registra merma. Input: 'producto, cantidad, unidad, motivo, costo' o lenguaje natural: '23 kilos de cerdo de merma'"),
        Tool(name="dar_de_baja", func=_dar_de_baja,
             description="Da de baja producto del inventario por rotura/dano/extravio. Input: 'producto, cantidad, unidad, motivo, costo'. Ej: 'plato sopero, 5, piezas, rotura, 25.00'"),
        Tool(name="reporte_mermas", func=_reporte_mermas,
             description="Reporte de mermas. Input: dias (int, opcional). Ej: '30'"),
        Tool(name="generar_orden_compra", func=_generar_orden_compra,
             description="Genera orden de compra. Input: 'proveedor, producto, cantidad, unidad, costo_unitario, fecha_req'"),
        Tool(name="ordenes_compra", func=_ordenes_compra_pendientes,
             description="Lista órdenes de compra. Input: estado (str, opcional). Ej: 'pendiente'"),
        Tool(name="costo_real_vs_teorico", func=_costo_real_vs_teorico,
             description="Compara costo real vs teórico. Input: dias (int, opcional). Ej: '30'"),
        Tool(name="dashboard_ventas", func=_dashboard_ventas,
             description="Dashboard de producción y ventas. Input: dias (int, opcional). Ej: '7'"),
        Tool(name="registrar_produccion", func=_registrar_produccion,
             description="Registra producción diaria y sobrantes. Input: 'fecha=2025-06-15, cocido: SOP-021=30, sobrante: arroz=4.5|kg|no, ensalada=2|kg|si'"),
        Tool(name="generar_reporte_diario", func=_generar_reporte_diario,
             description="Genera reporte diario oficial en Word. Input: fecha (str, opcional). Ej: '2025-06-15'"),
        Tool(name="alertas_stock_bajo", func=_alertas_stock_bajo,
             description="Alertas de stock bajo. Input: umbral (int, opcional). Ej: '10'"),
        Tool(name="asignar_turnos", func=_asignar_turnos,
             description="Asigna turnos de cocina. Input: 'fecha, cocinero, estacion, hora_inicio, hora_fin, receta'"),
        Tool(name="ver_turnos", func=_ver_turnos,
             description="Ver turnos de cocina. Input: fecha (str, opcional). Ej: '2025-06-15'"),

        # Trabajadores y Sobrantes
        Tool(name="registrar_trabajador", func=_registrar_trabajador,
             description="Registra un trabajador. Input: 'ID, nombre, cargo, turno, hora_entrada, hora_salida, dias_descanso(opcional)'. Turnos: matutino, vespertino, nocturno, mixto"),
        Tool(name="listar_trabajadores", func=_listar_trabajadores,
             description="Lista trabajadores. Input: turno (str, opcional). Ej: 'matutino'"),
        Tool(name="consultar_turno_hoy", func=_consultar_turno_hoy,
             description="Consulta personal que trabaja hoy. Input: turno (str, opcional). Ej: 'matutino'"),
        Tool(name="consultar_personal_activo", func=_consultar_personal_activo,
             description="Lista personal activo (no ausente). Sin input."),
        Tool(name="consultar_personal_ausente", func=_consultar_personal_ausente,
             description="Lista personal con ausencias (reposo, maternidad, etc.). Sin input."),
        Tool(name="registrar_ausencia", func=_registrar_ausencia,
             description="Registra ausencia. Input: 'id_empleado, tipo, fecha_inicio, fecha_fin, motivo(opcional)'. Tipos: reposo_medico, permiso_maternidad, vacaciones, permiso_personal"),
        Tool(name="reincorporar_trabajador", func=_reincorporar_trabajador,
             description="Reincorpora trabajador tras ausencia. Input: id_empleado. Ej: 'EMP001'"),
        Tool(name="seed_mermas", func=_seed_mermas,
             description="Genera datos realistas de mermas de restaurante. Input: dias (int, opcional, default 30). Ej: '30'"),
        Tool(name="registrar_compra", func=_registrar_compra,
             description="Registra compra en lenguaje natural. Input: 'se compro 3 kintales de harina caduca 12-03-2027'. Detecta producto, cantidad, unidad, fecha caducidad."),
        Tool(name="registrar_permiso_rapido", func=_registrar_permiso_rapido,
             description="Registra permiso/ausencia en lenguaje natural. Input: 'juan saco permiso por paternidad 6 dias'. Calcula automaticamente la fecha de retorno."),
        Tool(name="registrar_sobrante", func=_registrar_sobrante,
             description="Registra sobrante reutilizable. Input: 'producto, cantidad, unidad, id_empleado(opcional), turno(opcional), dias_reutilizacion(opcional)'"),
        Tool(name="dashboard_sobrantes", func=_dashboard_sobrantes,
             description="Dashboard de sobrantes por turno y día. Input: dias (int, opcional, default 7)"),
        Tool(name="exportar_dashboard_sobrantes", func=_exportar_dashboard_sobrantes,
             description="Exporta dashboard de sobrantes a CSV para Excel. Input: dias (int, opcional, default 7)"),
    ]