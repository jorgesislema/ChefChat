"""Une cada ingrediente de las recetas con un producto del catalogo (RecetaIngredientes).

Se usa al cargar recetas nuevas y en scripts/etapa_b_datos.py. Es repetible: reconstruye todo lo derivado de las
recetas y nunca borra productos con stock ni con precios cargados por el dueno.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter

from core.normalizar import buscar_producto_id, clave, nombre_canonico

# --- ingredientes de receta que se escriben distinto al catalogo ---------------------------------
ALIAS = {
    "huevos": "Huevo", "limon": "Limon", "limones": "Limon", "aceite": "Aceite Vegetal",
    "mantequilla": "Mantequilla Sin Sal", "leche": "Leche Entera", "sal": "Sal Marina",
    "azucar": "Azúcar Refinada", "cilantro": "Cilantro Fresco", "arroz blanco": "Arroz",
    "harina": "Harina", "pollo": "Pollo", "papa": "Papa", "papas": "Papa", "tomates": "Tomate",
    "cebolla blanca": "Cebolla", "cebolla perla": "Cebolla", "cebollas": "Cebolla",
    "palta": "Palta", "aguacate": "Palta", "platano": "Platano Maduro", "banano": "Platano Maduro",
    "yuca": "Yuca Fresca", "camarones": "Camaron Jumbo", "camaron": "Camaron Jumbo",
    "pechuga de pollo": "Pollo Pechuga", "jabon": "Jabon Industrial", "champinones": "Champinon Portobello",
    "champinon": "Champinon Portobello", "pasta": "Pasta Seca", "fideos": "Pasta Seca",
    "salmon": "Salmón Noruego", "naranja": "Naranja", "limon sutil": "Limon",
}


GRATIS = {"agua", "hielo", "agua fria", "agua tibia", "agua caliente", "agua hirviendo"}


MIN_USOS_NUEVO = 1  # un ingrediente sin producto se agrega al catalogo si aparece al menos 3 veces


def _numero(txt: str) -> float | None:
    t = txt.strip().replace(",", ".")
    try:
        if "/" in t:
            a, b = t.split("/", 1)
            return float(a) / float(b)
        return float(t)
    except ValueError:
        return None


# "piña en cubos", "papa cocida", "cebolla picada" -> "piña", "papa", "cebolla" (la preparacion no es otro producto)
_PREPARACION = re.compile(
    r"\s+(en\s+(cubos|cubitos|rodajas|rebanadas|gajos|presas|tiras|juliana|trozos|mitades|laminas|láminas|polvo|rama|ramas)"
    r"|picad[oa]s?|rallad[oa]s?|cocid[oa]s?|pelad[oa]s?|molid[oa]s?|desmenuzad[oa]s?|trocead[oa]s?|cortad[oa]s?"
    r"|filetead[oa]s?|licuad[oa]s?|tostad[oa]s?|sancochad[oa]s?|desgranad[oa]s?|hervid[oa]s?|fritos?|fritas?)\b.*$",
    re.IGNORECASE)


def _base(nombre: str) -> str:
    return _PREPARACION.sub("", nombre.strip()) or nombre.strip()


# Categoria sugerida para un producto nuevo (la primera regla que coincide). El dueno puede corregirla.
_REGLAS_CATEGORIA = [
    ("Condimentos", r"^caldo|\bcaldo de"),  # "caldo de carne" no es carne
    ("Bebidas", r"\b(vino|pisco|cerveza|licor|ron|aguardiente|sidra|cafe|jugo|gaseosa|te)\b"),
    ("Aceites", r"\baceite"),
    ("Secos", r"(de coco|almendra|harina|arroz|fideo|pasta|avena|quinoa|quinua|lenteja|frijol|garbanzo|maiz|trigo|\bpan\b|galleta|polvo de hornear|cacao|chocolate|nuez|nueces|mani|semilla|granola|azucar|panela|papelon|miel|mermelada|gelatina|bizcocho)"),
    ("Lácteos", r"\b(queso|leche|crema|yogur|yogurt|mantequilla|manjar|nata)\b"),
    ("Proteinas", r"\b(huevo|huevos)\b"),
    ("Mariscos", r"(camaron|langostino|pulpo|calamar|concha|mejillon|marisco|cangrejo|almeja|ostion)"),
    ("Pescados", r"(pescado|corvina|salmon|atun|trucha|bacalao|tilapia|dorado|sardina)"),
    ("Carnes", r"\b(pollo|pechuga|res|cerdo|chivo|cordero|pavo|lomo|costilla|carne|chorizo|tocino|pato|jamon|cuy|conejo)\b"),
    ("Hierbas", r"(cilantro|perejil|albahaca|menta|romero|tomillo|oregano|hierbabuena|eneldo|epazote|culantro|laurel)"),
    ("Condimentos", r"\b(sal|pimienta|comino|canela|clavo|clavos|vinagre|salsa|mostaza|curry|paprika|pimenton|achiote|vainilla|esencia|colorante|colorantes|ajo en polvo|caldo)\b"),
    ("Frutas", r"(limon|naranja|mango|pina|manzana|pera|uva|fresa|mora|durazno|banano|platano|maracuya|lulo|papaya|sandia|melon|ciruela|higo|fruto|tomate de arbol|aguacate|palta|coco|guanabana|tuna|kiwi|cereza)"),
    ("Vegetales", r"(papa|yuca|zanahoria|cebolla|tomat|lechuga|pimiento|\baji\b|zapallo|coliflor|brocoli|espinaca|choclo|pepino|apio|alcachofa|berenjena|calabac|champi|hongo|\bajo\b|\bcol\b|rabano|nabo|remolacha|vainita|arveja|haba|camote|oca|mashua|pimenton|cebollin|rocoto|jicama|esparrago|lenteja)"),
]


def _categoria(nombre: str) -> str:
    k = clave(nombre)
    for cat, patron in _REGLAS_CATEGORIA:
        if re.search(patron, k):
            return cat
    return "Sin clasificar"


def _singular(t: str) -> str:
    return t[:-2] if t.endswith("es") and len(t) > 4 else t[:-1] if t.endswith("s") and len(t) > 3 else t


def _buscar_producto(conn: sqlite3.Connection, nombre: str, catalogo: dict[str, int], nombres_c: dict[str, int]):
    k = clave(nombre)
    for cand in (k, _singular(k), clave(ALIAS.get(k, "")), clave(ALIAS.get(_singular(k), ""))):
        if cand and cand in catalogo:
            return catalogo[cand]
    # "cebolla blanca" -> "cebolla" (solo si el nombre del catalogo es la primera palabra y no hay " de ")
    if " de " not in k:
        for cn, pid in nombres_c.items():
            if k.startswith(cn + " "):
                return pid
    return None


def paso_ingredientes(conn: sqlite3.Connection, limpiar_auto: bool = True) -> dict:
    # Se reconstruye todo lo derivado de las recetas: vinculos y productos que se crearon desde ellas.
    # Nunca se borra un producto con stock o con un precio cargado por el dueno.
    # limpiar_auto=False (al cargar recetas desde la pantalla): se conservan los productos ya creados, con sus precios.
    conn.execute("DELETE FROM RecetaIngredientes")
    # productos creados por una corrida anterior (antes de existir la marca `origen`)
    conn.execute("UPDATE Catalogo SET origen='auto_receta' WHERE origen IS NULL AND categoria='Sin clasificar' AND id NOT IN "
                 "(SELECT producto_id FROM Inventario WHERE producto_id IS NOT NULL) AND id NOT IN "
                 "(SELECT producto_id FROM ProveedorProductos WHERE es_demo=0)")
    if limpiar_auto:
        conn.execute("DELETE FROM Catalogo WHERE origen='auto_receta' AND id NOT IN "
                     "(SELECT producto_id FROM Inventario WHERE producto_id IS NOT NULL) AND id NOT IN "
                     "(SELECT producto_id FROM ProveedorProductos WHERE es_demo=0)")
    catalogo = {clave(n): i for i, n in conn.execute("SELECT id, nombre FROM Catalogo")}
    nombres_c = dict(sorted(catalogo.items(), key=lambda kv: -len(kv[0])))
    lineas = []
    for rid, texto in conn.execute("SELECT id_receta, ingredientes_json FROM RecetasRAG"):
        for parte in (texto or "").split(";"):
            p = [x.strip() for x in parte.split("|")]
            if len(p) == 3 and p[2]:
                lineas.append((rid, _numero(p[0]), p[1].lower(), p[2]))
    usos = Counter(clave(_base(n)) for _, _, _, n in lineas)
    nuevos = 0
    for _, _, _, original in lineas:
        nombre = _base(original)
        k = clave(nombre)
        if k in GRATIS or clave(original) in GRATIS or usos[k] < MIN_USOS_NUEVO:
            continue
        if _buscar_producto(conn, nombre, catalogo, nombres_c) is None and buscar_producto_id(conn, nombre) is None:
            cur = conn.execute(
                "INSERT INTO Catalogo (nombre, categoria, vida_util_dias, tipo, origen) VALUES (?,?,?,?,'auto_receta')",
                (nombre_canonico(nombre), _categoria(nombre), 30, "alimento"))
            catalogo[k] = cur.lastrowid
            nombres_c = dict(sorted(catalogo.items(), key=lambda kv: -len(kv[0])))
            nuevos += 1
    conn.execute("DELETE FROM RecetaIngredientes")
    vinculadas = 0
    for rid, cant, unidad, nombre in lineas:
        k = clave(nombre)
        pid = None if (k in GRATIS or clave(_base(nombre)) in GRATIS) else (
            _buscar_producto(conn, nombre, catalogo, nombres_c) or _buscar_producto(conn, _base(nombre), catalogo, nombres_c))
        vinculadas += pid is not None
        conn.execute("INSERT OR IGNORE INTO RecetaIngredientes (receta_id, producto_id, ingrediente, cantidad, unidad) "
                     "VALUES (?,?,?,?,?)", (rid, pid, nombre, cant, unidad))
    total = conn.execute("SELECT count(*) FROM RecetaIngredientes").fetchone()[0]
    return {"lineas": total, "vinculadas": conn.execute(
        "SELECT count(*) FROM RecetaIngredientes WHERE producto_id IS NOT NULL").fetchone()[0], "productos_nuevos": nuevos}
