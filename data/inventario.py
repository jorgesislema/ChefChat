"""Inventario editable: lotes (agregar, cambiar, quitar) y productos del catalogo (nombre, categoria, tipo, vida util).

Cada cambio queda anotado en la tabla Cambios. Los errores se dicen en palabras simples (DatoInvalido -> HTTP 400).
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.normalizar import buscar_producto_id, categoria_canonica, clave, nombre_canonico, unidad_canonica
from core.unidades import familia
from data.esquema import asegurar_esquema, registrar_cambio, tipo_por_categoria
from data.proveedores import DatoInvalido

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
CANTIDAD_MAX = 1_000_000
VIDA_UTIL_MAX = 3650
TIPOS = ("alimento", "limpieza")

_SQL_LOTES = """
SELECT i.id, i.producto_id, c.nombre AS producto, c.categoria, c.tipo, i.id_lote AS lote, i.cantidad_actual AS cantidad,
       i.unidad, i.fecha_ingreso, i.fecha_caducidad_fija,
       date(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) AS vence
FROM Inventario i JOIN Catalogo c ON c.id = i.producto_id
"""


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _fecha(txt: Optional[str], campo: str) -> Optional[str]:
    if txt is None or str(txt).strip() == "":
        return None
    try:
        return date.fromisoformat(str(txt).strip()).isoformat()
    except ValueError:
        raise DatoInvalido(f"{campo}: la fecha no es válida (usa año-mes-día).") from None


def _cantidad(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise DatoInvalido("La cantidad debe ser un número.") from None
    if not v > 0:
        raise DatoInvalido("La cantidad debe ser mayor que cero. Para sacar un lote usa «Quitar».")
    if v > CANTIDAD_MAX:
        raise DatoInvalido("La cantidad es demasiado grande.")
    return round(v, 3)


def _unidad(txt: Optional[str]) -> str:
    u = unidad_canonica(txt)
    if not u or familia(u) is None:
        raise DatoInvalido("La unidad no es válida. Usa kg, g, l, ml, libra, qq o unidad.")
    return u


# ---------------------------------------------------------------- lotes
def lotes(q: str = "", tipo: str = "", limite: int = 500, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        filas = [dict(r) for r in conn.execute(_SQL_LOTES + " WHERE i.cantidad_actual > 0 ORDER BY vence, c.nombre")]
    finally:
        conn.close()
    if q:
        k = clave(q)
        filas = [f for f in filas if k in clave(f["producto"]) or k in clave(f["lote"] or "")]
    if tipo in TIPOS:
        filas = [f for f in filas if f["tipo"] == tipo]
    return filas[:limite]


def crear_lote(producto: str, cantidad: float, unidad: str, fecha_ingreso: Optional[str] = None, fecha_caducidad: Optional[str] = None,
               id_lote: Optional[str] = None, categoria: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Agrega un lote. Si el producto no existe se crea (con la categoria que indiques)."""
    nombre = " ".join((producto or "").split())
    if len(nombre) < 2:
        raise DatoInvalido("Escribe el nombre del producto.")
    cant, uni = _cantidad(cantidad), _unidad(unidad)
    ingreso = _fecha(fecha_ingreso, "Fecha de ingreso") or date.today().isoformat()
    caduca = _fecha(fecha_caducidad, "Fecha de vencimiento")
    if caduca and caduca < ingreso:
        raise DatoInvalido("El vencimiento no puede ser antes de la fecha de ingreso.")
    conn = _conn(db_path)
    try:
        pid = buscar_producto_id(conn, nombre)
        creado = False
        if pid is None:
            cat = categoria_canonica(conn, categoria or "Sin clasificar")
            pid = conn.execute("INSERT INTO Catalogo (nombre, categoria, vida_util_dias, tipo, origen) VALUES (?,?,?,?,'manual')",
                               (nombre_canonico(nombre), cat, 30, tipo_por_categoria(cat))).lastrowid
            creado = True
        lote = " ".join((id_lote or "").split())
        if lote:
            if conn.execute("SELECT 1 FROM Inventario WHERE id_lote=?", (lote,)).fetchone():
                raise DatoInvalido(f"Ya existe un lote con el código {lote}.")
        else:
            n = conn.execute("SELECT count(*) FROM Inventario WHERE id_lote LIKE ?", (f"M{ingreso.replace('-', '')}-%",)).fetchone()[0]
            lote = f"M{ingreso.replace('-', '')}-{n + 1:03d}"
        nuevo = conn.execute(
            "INSERT INTO Inventario (producto_id, fecha_ingreso, cantidad_actual, unidad, id_lote, fecha_caducidad_fija) VALUES (?,?,?,?,?,?)",
            (pid, ingreso, cant, uni, lote, caduca)).lastrowid
        nom = conn.execute("SELECT nombre FROM Catalogo WHERE id=?", (pid,)).fetchone()[0]
        registrar_cambio(conn, "lote", "crear", f"{nom}: {cant:g} {uni}, lote {lote}")
        conn.commit()
        return {"id": nuevo, "lote": lote, "producto_id": pid, "producto_creado": creado}
    finally:
        conn.close()


def editar_lote(lote_id: int, cantidad: Optional[float] = None, unidad: Optional[str] = None, fecha_ingreso: Optional[str] = None,
                fecha_caducidad: Optional[str] = None, quitar_caducidad: bool = False, db_path: str = DB_PATH) -> None:
    conn = _conn(db_path)
    try:
        r = conn.execute(_SQL_LOTES + " WHERE i.id=?", (lote_id,)).fetchone()
        if not r:
            raise DatoInvalido("No encuentro ese lote.")
        cant = _cantidad(cantidad) if cantidad is not None else r["cantidad"]
        uni = _unidad(unidad) if unidad is not None else r["unidad"]
        ingreso = _fecha(fecha_ingreso, "Fecha de ingreso") or r["fecha_ingreso"]
        caduca = None if quitar_caducidad else (_fecha(fecha_caducidad, "Fecha de vencimiento") or r["fecha_caducidad_fija"])
        if caduca and caduca < ingreso:
            raise DatoInvalido("El vencimiento no puede ser antes de la fecha de ingreso.")
        conn.execute("UPDATE Inventario SET cantidad_actual=?, unidad=?, fecha_ingreso=?, fecha_caducidad_fija=? WHERE id=?",
                     (cant, uni, ingreso, caduca, lote_id))
        registrar_cambio(conn, "lote", "cambiar",
                         f"{r['producto']} lote {r['lote']}: {r['cantidad']:g} {r['unidad']} → {cant:g} {uni}; vence {r['vence']} → {caduca or 'según vida útil'}")
        conn.commit()
    finally:
        conn.close()


def quitar_lote(lote_id: int, db_path: str = DB_PATH) -> None:
    """Saca el lote del inventario (se usa, se botó o fue un error de registro). Queda anotado en Cambios."""
    conn = _conn(db_path)
    try:
        r = conn.execute(_SQL_LOTES + " WHERE i.id=?", (lote_id,)).fetchone()
        if not r:
            raise DatoInvalido("No encuentro ese lote.")
        conn.execute("DELETE FROM Inventario WHERE id=?", (lote_id,))
        registrar_cambio(conn, "lote", "quitar", f"{r['producto']} lote {r['lote']} ({r['cantidad']:g} {r['unidad']})")
        conn.commit()
    finally:
        conn.close()


def salida_fifo(conn: sqlite3.Connection, producto_id: int, cantidad: float, unidad: str) -> float:
    """Descuenta `cantidad` (en `unidad`) de los lotes del producto, empezando por el que vence antes.
    Un lote que llega a cero se quita. Devuelve lo que NO se pudo descontar (0 si alcanzo). No hace commit."""
    from core.unidades import convertir
    falta = float(cantidad)
    for lote in conn.execute(
            "SELECT i.id, i.cantidad_actual, i.unidad FROM Inventario i JOIN Catalogo c ON c.id=i.producto_id WHERE i.producto_id=? "
            "AND i.cantidad_actual>0 ORDER BY date(COALESCE(i.fecha_caducidad_fija, date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))), i.id",
            (producto_id,)).fetchall():
        if falta <= 1e-9:
            break
        en_unidad = convertir(lote["cantidad_actual"], lote["unidad"], unidad)
        if en_unidad is None:
            continue
        quita = min(falta, en_unidad)
        queda = round(max(convertir(en_unidad - quita, unidad, lote["unidad"]) or 0.0, 0), 3)
        if queda <= 0:  # la tabla no admite lotes en cero
            conn.execute("DELETE FROM Inventario WHERE id=?", (lote["id"],))
        else:
            conn.execute("UPDATE Inventario SET cantidad_actual=? WHERE id=?", (queda, lote["id"]))
        falta -= quita
    return max(round(falta, 6), 0.0)


def entrada_ajuste(conn: sqlite3.Connection, producto_id: int, cantidad: float, unidad: str, fecha: str, prefijo: str) -> str:
    """Suma stock como un lote nuevo (devolucion o sobrante de conteo). Vence segun la vida util del producto. No hace commit."""
    n = conn.execute("SELECT count(*) FROM Inventario WHERE id_lote LIKE ?", (f"{prefijo}{fecha.replace('-', '')}-%",)).fetchone()[0]
    lote = f"{prefijo}{fecha.replace('-', '')}-{n + 1:03d}"
    conn.execute("INSERT INTO Inventario (producto_id, fecha_ingreso, cantidad_actual, unidad, id_lote) VALUES (?,?,?,?,?)",
                 (producto_id, fecha, round(cantidad, 3), unidad, lote))
    return lote


# ---------------------------------------------------------------- productos (catalogo)
def productos(q: str = "", categoria: str = "", tipo: str = "", db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Catalogo con stock, proveedores y mejor precio, para la pantalla de ingredientes y precios."""
    from data import proveedores as prov
    conn = _conn(db_path)
    try:
        mejores = prov.mejor_precio_por_producto(conn)
        n_prov: Dict[int, int] = {}
        for (_pv, prod_id) in prov._historial(conn):
            n_prov[prod_id] = n_prov.get(prod_id, 0) + 1
        stock = {r["producto_id"]: (r["cant"], r["uni"]) for r in conn.execute(
            "SELECT producto_id, round(sum(cantidad_actual),2) AS cant, min(unidad) AS uni FROM Inventario WHERE cantidad_actual>0 GROUP BY producto_id")}
        salida = []
        for r in conn.execute("SELECT id, nombre, categoria, tipo, vida_util_dias, origen, kg_por_unidad FROM Catalogo ORDER BY nombre"):
            if q and clave(q) not in clave(r["nombre"]):
                continue
            if categoria and clave(categoria) != clave(r["categoria"]):
                continue
            if tipo in TIPOS and r["tipo"] != tipo:
                continue
            m = mejores.get(r["id"])
            s = stock.get(r["id"])
            salida.append({**dict(r), "stock": s[0] if s else 0, "unidad_stock": s[1] if s else None, "n_proveedores": n_prov.get(r["id"], 0),
                           "mejor_precio": m["precio"] if m else None, "mejor_unidad": m["unidad_precio"] if m else None,
                           "mejor_proveedor": m["proveedor"] if m else None})
        return salida
    finally:
        conn.close()


def categorias(db_path: str = DB_PATH) -> List[str]:
    conn = _conn(db_path)
    try:
        vistos: Dict[str, str] = {}
        for (c,) in conn.execute("SELECT DISTINCT categoria FROM Catalogo WHERE categoria IS NOT NULL"):
            vistos.setdefault(clave(c), c)
        return sorted(vistos.values(), key=clave)
    finally:
        conn.close()


def editar_producto(producto_id: int, nombre: Optional[str] = None, categoria: Optional[str] = None, tipo: Optional[str] = None,
                    vida_util_dias: Optional[int] = None, db_path: str = DB_PATH) -> None:
    conn = _conn(db_path)
    try:
        r = conn.execute("SELECT * FROM Catalogo WHERE id=?", (producto_id,)).fetchone()
        if not r:
            raise DatoInvalido("No encuentro ese producto.")
        nom = nombre_canonico(nombre) if nombre is not None else r["nombre"]
        if len(nom) < 2:
            raise DatoInvalido("Escribe el nombre del producto.")
        otro = buscar_producto_id(conn, nom)
        if otro is not None and otro != producto_id:
            raise DatoInvalido("Ya existe otro producto con ese nombre.")
        cat = categoria_canonica(conn, categoria) if categoria is not None and categoria.strip() else r["categoria"]
        if tipo is not None and tipo not in TIPOS:
            raise DatoInvalido("El tipo debe ser alimento o limpieza.")
        # si cambia la categoria y no se indica el tipo, se vuelve a deducir; si se indica, manda lo indicado
        nuevo_tipo = tipo if tipo is not None else (tipo_por_categoria(cat) if cat != r["categoria"] else r["tipo"])
        vida = r["vida_util_dias"]
        if vida_util_dias is not None:
            if not isinstance(vida_util_dias, int) or not 1 <= vida_util_dias <= VIDA_UTIL_MAX:
                raise DatoInvalido(f"La vida útil debe ser entre 1 y {VIDA_UTIL_MAX} días.")
            vida = vida_util_dias
        conn.execute("UPDATE Catalogo SET nombre=?, categoria=?, tipo=?, vida_util_dias=?, origen='manual' WHERE id=?",
                     (nom, cat, nuevo_tipo, vida, producto_id))
        cambios = [f"{a}: {x} → {y}" for a, x, y in (("nombre", r["nombre"], nom), ("categoría", r["categoria"], cat), ("tipo", r["tipo"], nuevo_tipo),
                                                      ("vida útil", r["vida_util_dias"], vida)) if x != y]
        registrar_cambio(conn, "producto", "cambiar", f"{r['nombre']}: " + ("; ".join(cambios) or "sin cambios"))
        conn.commit()
    finally:
        conn.close()


def quitar_producto(producto_id: int, db_path: str = DB_PATH) -> None:
    """Borra un producto del catalogo SOLO si nada lo usa (sin lotes, sin precios, sin recetas)."""
    conn = _conn(db_path)
    try:
        r = conn.execute("SELECT nombre FROM Catalogo WHERE id=?", (producto_id,)).fetchone()
        if not r:
            raise DatoInvalido("No encuentro ese producto.")
        usos = []
        for tabla, texto in (("Inventario", "tiene lotes en el inventario"), ("ProveedorProductos", "tiene precios de proveedores"),
                             ("RecetaIngredientes", "se usa en recetas")):
            if conn.execute(f"SELECT 1 FROM {tabla} WHERE producto_id=? LIMIT 1", (producto_id,)).fetchone():
                usos.append(texto)
        if usos:
            raise DatoInvalido(f"No se puede quitar «{r['nombre']}»: " + ", ".join(usos) + ".")
        conn.execute("DELETE FROM Catalogo WHERE id=?", (producto_id,))
        registrar_cambio(conn, "producto", "quitar", r["nombre"])
        conn.commit()
    finally:
        conn.close()


def cambios(limite: int = 50, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        return [dict(r) for r in conn.execute("SELECT id, fecha, entidad, accion, detalle FROM Cambios ORDER BY id DESC LIMIT ?", (max(1, min(limite, 500)),))]
    finally:
        conn.close()
