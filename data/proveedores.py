"""Proveedores, precios y comparacion de precios.

Un precio es una fila en ProveedorProductos con fecha: el historial se conserva
y "el precio actual" de un proveedor es su fila mas reciente.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.normalizar import buscar_producto_id, categoria_canonica, nombre_canonico
from data.esquema import asegurar_esquema, registrar_cambio, tipo_por_categoria

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
UNIDADES_PRECIO = ("kg", "l", "unidad")
ALERTA_SUBIDA = 10.0  # % de subida que dispara el aviso


class DatoInvalido(ValueError):
    """Error que se puede mostrar tal cual al usuario (HTTP 400)."""


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _historial(conn: sqlite3.Connection) -> Dict[tuple, List[sqlite3.Row]]:
    """{(proveedor_id, producto_id): [filas de la mas nueva a la mas vieja]} solo de proveedores activos."""
    filas: Dict[tuple, List[sqlite3.Row]] = {}
    for r in conn.execute(
        "SELECT pp.*, p.nombre AS proveedor FROM ProveedorProductos pp JOIN Proveedores p ON p.id=pp.proveedor_id "
        "WHERE p.activo=1 AND pp.quitado=0 ORDER BY pp.fecha DESC, pp.id DESC"
    ):
        filas.setdefault((r["proveedor_id"], r["producto_id"]), []).append(r)
    return filas


def mejor_precio_por_producto(conn: sqlite3.Connection) -> Dict[int, Dict[str, Any]]:
    """{producto_id: {precio, unidad_precio, proveedor, proveedor_id}} con el precio actual mas bajo."""
    mejores: Dict[int, Dict[str, Any]] = {}
    for (prov_id, prod_id), hist in _historial(conn).items():
        act = hist[0]
        actual = mejores.get(prod_id)
        if actual is None or (act["unidad_precio"] == actual["unidad_precio"] and act["precio"] < actual["precio"]):
            mejores[prod_id] = {"precio": act["precio"], "unidad_precio": act["unidad_precio"],
                                "proveedor": act["proveedor"], "proveedor_id": prov_id}
    return mejores


# ---------------------------------------------------------------- proveedores
def listar(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        return [dict(r) for r in conn.execute(
            "SELECT p.id, p.nombre, p.contacto, p.telefono, p.dias_entrega, p.notas, p.es_demo, "
            "(SELECT count(DISTINCT producto_id) FROM ProveedorProductos WHERE proveedor_id=p.id AND quitado=0) AS n_productos "
            "FROM Proveedores p WHERE p.activo=1 ORDER BY p.nombre")]
    finally:
        conn.close()


def crear(nombre: str, contacto: str = "", telefono: str = "", dias_entrega: str = "", notas: str = "",
          db_path: str = DB_PATH) -> int:
    nombre = " ".join((nombre or "").split())
    if len(nombre) < 2:
        raise DatoInvalido("Escribe el nombre del proveedor.")
    conn = _conn(db_path)
    try:
        try:
            cur = conn.execute("INSERT INTO Proveedores (nombre, contacto, telefono, dias_entrega, notas) VALUES (?,?,?,?,?)",
                               (nombre, contacto.strip(), telefono.strip(), dias_entrega.strip(), notas.strip()))
        except sqlite3.IntegrityError:
            raise DatoInvalido("Ya existe un proveedor con ese nombre.") from None
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def detalle(proveedor_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        prov = conn.execute("SELECT * FROM Proveedores WHERE id=? AND activo=1", (proveedor_id,)).fetchone()
        if not prov:
            return None
        hist = _historial(conn)
        mejores = mejor_precio_por_producto(conn)
        info = {r["id"]: r for r in conn.execute("SELECT id, nombre, categoria, tipo FROM Catalogo")}
        productos = []
        for (pv, prod_id), filas in hist.items():
            if pv != proveedor_id:
                continue
            act = filas[0]
            ant = filas[1]["precio"] if len(filas) > 1 else None
            mejor = mejores.get(prod_id)
            productos.append({
                "producto_id": prod_id, "producto": info[prod_id]["nombre"], "categoria": info[prod_id]["categoria"],
                "tipo": info[prod_id]["tipo"], "precio": act["precio"], "unidad_precio": act["unidad_precio"],
                "fecha": act["fecha"], "precio_anterior": ant,
                "cambio_pct": round((act["precio"] - ant) / ant * 100, 1) if ant else None,
                "es_mas_barato": bool(mejor and mejor["proveedor_id"] == proveedor_id),
                "mejor_precio": mejor["precio"] if mejor else None, "mejor_proveedor": mejor["proveedor"] if mejor else None,
            })
        productos.sort(key=lambda p: (p["categoria"] or "", p["producto"]))
        return {"proveedor": dict(prov), "productos": productos}
    finally:
        conn.close()


def poner_precio(proveedor_id: int, producto: str, precio: float, unidad_precio: str, categoria: Optional[str] = None,
                 fecha: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Registra el precio de HOY de un producto. Si el producto no existe, se crea (con categoria)."""
    if unidad_precio not in UNIDADES_PRECIO:
        raise DatoInvalido("La unidad del precio debe ser kg, l o unidad.")
    if not (precio > 0) or precio > 100000:
        raise DatoInvalido("El precio debe ser mayor que cero.")
    fecha = fecha or date.today().isoformat()
    try:
        date.fromisoformat(fecha)
    except ValueError:
        raise DatoInvalido("La fecha no es válida.") from None
    conn = _conn(db_path)
    try:
        if not conn.execute("SELECT 1 FROM Proveedores WHERE id=? AND activo=1", (proveedor_id,)).fetchone():
            raise DatoInvalido("No encuentro ese proveedor.")
        pid = buscar_producto_id(conn, producto)
        creado = False
        if pid is None:
            if not producto or len(producto.strip()) < 2:
                raise DatoInvalido("Escribe el nombre del producto.")
            cat = categoria_canonica(conn, categoria or "Sin clasificar")
            cur = conn.execute("INSERT INTO Catalogo (nombre, categoria, vida_util_dias, tipo) VALUES (?,?,?,?)",
                               (nombre_canonico(producto), cat, 30, tipo_por_categoria(cat)))
            pid, creado = cur.lastrowid, True
        anterior = conn.execute(
            "SELECT precio, unidad_precio, quitado FROM ProveedorProductos WHERE proveedor_id=? AND producto_id=? ORDER BY fecha DESC, id DESC LIMIT 1",
            (proveedor_id, pid)).fetchone()
        conn.execute("UPDATE ProveedorProductos SET quitado=0 WHERE proveedor_id=? AND producto_id=?", (proveedor_id, pid))  # vuelve a venderlo
        nombre_prov = conn.execute("SELECT nombre FROM Proveedores WHERE id=?", (proveedor_id,)).fetchone()[0]
        nombre_prod = conn.execute("SELECT nombre FROM Catalogo WHERE id=?", (pid,)).fetchone()[0]
        if anterior is None or anterior["quitado"]:
            registrar_cambio(conn, "precio", "crear", f"{nombre_prov} vende {nombre_prod} a {precio:g} por {unidad_precio}")
        else:
            registrar_cambio(conn, "precio", "cambiar", f"{nombre_prov}: {nombre_prod} de {anterior['precio']:g} a {precio:g} por {unidad_precio}")
        conn.execute(
            "INSERT INTO ProveedorProductos (proveedor_id, producto_id, precio, unidad_precio, fecha) VALUES (?,?,?,?,?) "
            "ON CONFLICT(proveedor_id, producto_id, fecha) DO UPDATE SET precio=excluded.precio, unidad_precio=excluded.unidad_precio, es_demo=0, quitado=0",
            (proveedor_id, pid, round(precio, 4), unidad_precio, fecha))
        conn.commit()
        return {"producto_id": pid, "producto_creado": creado}
    finally:
        conn.close()


def alertas_de_precio(umbral: float = ALERTA_SUBIDA, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Productos cuyo precio actual subio mas de `umbral` % contra el precio anterior del mismo proveedor."""
    conn = _conn(db_path)
    try:
        info = {r["id"]: r["nombre"] for r in conn.execute("SELECT id, nombre FROM Catalogo")}
        salida = []
        for (_pv, prod_id), filas in _historial(conn).items():
            if len(filas) < 2 or filas[1]["precio"] <= 0:
                continue
            cambio = (filas[0]["precio"] - filas[1]["precio"]) / filas[1]["precio"] * 100
            if cambio > umbral:
                salida.append({"producto": info[prod_id], "proveedor": filas[0]["proveedor"], "anterior": filas[1]["precio"],
                               "actual": filas[0]["precio"], "unidad_precio": filas[0]["unidad_precio"],
                               "cambio_pct": round(cambio, 1), "fecha": filas[0]["fecha"]})
        return sorted(salida, key=lambda a: -a["cambio_pct"])
    finally:
        conn.close()


def catalogo(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        return [dict(r) for r in conn.execute("SELECT id, nombre, categoria, tipo FROM Catalogo ORDER BY nombre")]
    finally:
        conn.close()


# ---------------------------------------------------------------- busquedas por texto (para el chat)
def _norm(t: str) -> str:
    from core.normalizar import clave
    return clave(t)


def producto_en_texto(texto: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """El producto del catalogo mencionado en el texto (palabra completa, gana el nombre mas largo)."""
    import re
    t = _norm(texto)
    conn = _conn(db_path)
    try:
        mejor = None
        for r in conn.execute("SELECT id, nombre, categoria, tipo FROM Catalogo"):
            n = _norm(r["nombre"])
            singular = n[:-1] if n.endswith("s") and len(n) > 4 else n
            if re.search(rf"\b({re.escape(n)}|{re.escape(singular)}|{re.escape(n)}s)\b", t) and (mejor is None or len(n) > len(_norm(mejor["nombre"]))):
                mejor = dict(r)
        return mejor
    finally:
        conn.close()


def proveedor_en_texto(texto: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """El proveedor mencionado: coincide por su nombre completo o por una palabra propia de su nombre (andina, valle...)."""
    import re
    t = _norm(texto)
    genericas = {"distribuidora", "mercado", "carnes", "lacteos", "mariscos", "limpieza", "total", "central", "mayorista", "del", "de", "la", "los", "las"}
    conn = _conn(db_path)
    try:
        mejor, mejor_k = None, (0, 0)
        for r in conn.execute("SELECT id, nombre FROM Proveedores WHERE activo=1"):
            n = _norm(r["nombre"])
            k = (2, len(n)) if n in t else (0, 0)
            if k == (0, 0):
                propias = [w for w in n.split() if len(w) > 3 and w not in genericas]
                if any(re.search(rf"\b{re.escape(w)}\b", t) for w in propias):
                    k = (1, len(n))
            if k > mejor_k:
                mejor, mejor_k = dict(r), k
        return mejor
    finally:
        conn.close()


def precios_de_producto(producto_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Precio actual de un producto en cada proveedor, del mas barato al mas caro (solo comparables entre si)."""
    conn = _conn(db_path)
    try:
        filas = []
        for (_pv, pid), hist in _historial(conn).items():
            if pid != producto_id:
                continue
            ant = hist[1]["precio"] if len(hist) > 1 else None
            filas.append({"proveedor_id": hist[0]["proveedor_id"], "proveedor": hist[0]["proveedor"], "precio": hist[0]["precio"], "unidad_precio": hist[0]["unidad_precio"],
                          "fecha": hist[0]["fecha"], "cambio_pct": round((hist[0]["precio"] - ant) / ant * 100, 1) if ant else None})
        filas.sort(key=lambda f: (f["unidad_precio"], f["precio"]))
        return filas
    finally:
        conn.close()


def productos_candidatos(texto: str, limite: int = 5, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Productos cuyo nombre contiene una palabra del texto (ej. 'mantequilla' -> 'Mantequilla Sin Sal').
    Sirve cuando nadie escribe el nombre completo del producto."""
    import re
    tokens = [t for t in re.findall(r"[a-z0-9]+", _norm(texto)) if len(t) >= 5]
    if not tokens:
        return []
    raices = {t for t in tokens} | {t[:-1] for t in tokens if t.endswith("s")} | {t[:-2] for t in tokens if t.endswith("es")}
    conn = _conn(db_path)
    try:
        puntuados = []
        for r in conn.execute("SELECT id, nombre, categoria, tipo FROM Catalogo"):
            partes = re.findall(r"[a-z0-9]+", _norm(r["nombre"]))
            aciertos = sum(1 for t in raices if any(p == t or (len(t) >= 5 and p.startswith(t)) for p in partes))
            if aciertos:
                puntuados.append((-aciertos, len(r["nombre"]), r["nombre"], dict(r)))
        puntuados.sort(key=lambda x: x[:3])
        return [x[3] for x in puntuados[:limite]]
    finally:
        conn.close()


def stock_de_producto(producto_id: int, db_path: str = DB_PATH) -> Dict[str, Any]:
    conn = _conn(db_path)
    try:
        cant, unidad = conn.execute("SELECT round(sum(cantidad_actual),1), min(unidad) FROM Inventario WHERE producto_id=? AND cantidad_actual>0",
                                    (producto_id,)).fetchone()
        return {"cantidad": cant or 0, "unidad": unidad or ""}
    finally:
        conn.close()


# ---------------------------------------------------------------- editar y quitar
def editar(proveedor_id: int, nombre: Optional[str] = None, contacto: Optional[str] = None, telefono: Optional[str] = None,
           dias_entrega: Optional[str] = None, notas: Optional[str] = None, db_path: str = DB_PATH) -> None:
    """Cambia los datos de un proveedor. Los campos que no se mandan (None) no se tocan."""
    conn = _conn(db_path)
    try:
        actual = conn.execute("SELECT * FROM Proveedores WHERE id=? AND activo=1", (proveedor_id,)).fetchone()
        if not actual:
            raise DatoInvalido("No encuentro ese proveedor.")
        nuevo = {"nombre": actual["nombre"], "contacto": actual["contacto"], "telefono": actual["telefono"],
                 "dias_entrega": actual["dias_entrega"], "notas": actual["notas"]}
        for k, v in (("nombre", nombre), ("contacto", contacto), ("telefono", telefono), ("dias_entrega", dias_entrega), ("notas", notas)):
            if v is not None:
                nuevo[k] = " ".join(v.split())
        if len(nuevo["nombre"]) < 2:
            raise DatoInvalido("Escribe el nombre del proveedor.")
        try:
            conn.execute("UPDATE Proveedores SET nombre=?, contacto=?, telefono=?, dias_entrega=?, notas=?, es_demo=0 WHERE id=?",
                         (nuevo["nombre"], nuevo["contacto"], nuevo["telefono"], nuevo["dias_entrega"], nuevo["notas"], proveedor_id))
        except sqlite3.IntegrityError:
            raise DatoInvalido("Ya existe un proveedor con ese nombre.") from None
        registrar_cambio(conn, "proveedor", "cambiar", f"{actual['nombre']} ? {nuevo['nombre']}" if nuevo["nombre"] != actual["nombre"] else nuevo["nombre"])
        conn.commit()
    finally:
        conn.close()


def quitar(proveedor_id: int, db_path: str = DB_PATH) -> None:
    """Deja de usar a un proveedor. No se borra: sus precios quedan guardados y se puede reactivar creando otro con el mismo nombre."""
    conn = _conn(db_path)
    try:
        r = conn.execute("SELECT nombre FROM Proveedores WHERE id=? AND activo=1", (proveedor_id,)).fetchone()
        if not r:
            raise DatoInvalido("No encuentro ese proveedor.")
        # al archivarlo se le cambia el nombre para liberar el original (el nombre es unico)
        conn.execute("UPDATE Proveedores SET activo=0, nombre=nombre || ' (archivado ' || id || ')' WHERE id=?", (proveedor_id,))
        registrar_cambio(conn, "proveedor", "quitar", r["nombre"])
        conn.commit()
    finally:
        conn.close()


def quitar_producto(proveedor_id: int, producto_id: int, db_path: str = DB_PATH) -> None:
    """El proveedor ya no vende este producto. El historial de precios se conserva (por si vuelve a venderlo)."""
    conn = _conn(db_path)
    try:
        r = conn.execute(
            "SELECT p.nombre AS prov, c.nombre AS prod FROM ProveedorProductos pp JOIN Proveedores p ON p.id=pp.proveedor_id "
            "JOIN Catalogo c ON c.id=pp.producto_id WHERE pp.proveedor_id=? AND pp.producto_id=? AND pp.quitado=0 LIMIT 1",
            (proveedor_id, producto_id)).fetchone()
        if not r:
            raise DatoInvalido("Ese proveedor no vende ese producto.")
        conn.execute("UPDATE ProveedorProductos SET quitado=1 WHERE proveedor_id=? AND producto_id=?", (proveedor_id, producto_id))
        registrar_cambio(conn, "precio", "quitar", f"{r['prov']} ya no vende {r['prod']}")
        conn.commit()
    finally:
        conn.close()
