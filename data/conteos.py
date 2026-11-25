"""Conteo fisico de inventario (fin de mes).

1. crear(): arma la hoja con el stock que dice el sistema por producto (pasado a kg, l o unidad) y su precio.
2. contar(): se anota lo que hay de verdad (se puede guardar de a poco).
3. cerrar(): fija los valores. Opcional: ajustar el inventario a lo contado (sale lo que falta empezando por lo que
   vence antes; lo que sobra entra como lote de ajuste).
4. con dos conteos cerrados, data.compras.costo_real() usa: inventario inicial + compras - inventario final.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.formato import dinero
from core.normalizar import clave
from core.unidades import convertir, familia
from data.esquema import asegurar_esquema, registrar_cambio
from data.proveedores import DatoInvalido

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
DIFERENCIA_ALERTA = 0.10  # avisa las lineas donde falta o sobra mas del 10 %


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _stock_por_producto(conn: sqlite3.Connection, incluye_limpieza: bool) -> Dict[int, Dict[str, Any]]:
    """{producto_id: {unidad, cantidad}} sumando lotes con stock, todo pasado a una sola unidad (kg, l o unidad)."""
    out: Dict[int, Dict[str, Any]] = {}
    for r in conn.execute("SELECT i.producto_id, i.cantidad_actual, i.unidad, c.tipo FROM Inventario i JOIN Catalogo c ON c.id=i.producto_id "
                          "WHERE i.cantidad_actual > 0"):
        if r["tipo"] == "limpieza" and not incluye_limpieza:
            continue
        fam = familia(r["unidad"])
        if fam is None:
            continue
        d = out.setdefault(r["producto_id"], {"unidad": fam, "cantidad": 0.0})
        if d["unidad"] != fam:  # un producto con lotes en kg y en litros: se cuenta en la primera unidad y se omite el resto
            continue
        d["cantidad"] += convertir(r["cantidad_actual"], r["unidad"], fam) or 0.0
    return out


def _precio_en(precio: Dict[str, Any] | None, unidad: str) -> Optional[float]:
    if not precio:
        return None
    factor = convertir(1, unidad, precio["unidad_precio"])
    return round(precio["precio"] * factor, 6) if factor is not None else None


def crear(fecha: Optional[str] = None, incluye_limpieza: bool = False, notas: str = "", db_path: str = DB_PATH) -> Dict[str, Any]:
    from data import proveedores as prov
    hoy = date.today().isoformat()
    try:
        f = date.fromisoformat(fecha).isoformat() if fecha else hoy
    except ValueError:
        raise DatoInvalido("La fecha no es válida (usa año-mes-día).") from None
    if f > hoy:
        raise DatoInvalido("No se puede contar un día que aún no llega.")
    conn = _conn(db_path)
    try:
        abierto = conn.execute("SELECT id, fecha FROM Conteos WHERE estado='abierto' AND es_demo=0").fetchone()
        if abierto:
            raise DatoInvalido(f"Ya hay un conteo abierto (del {abierto['fecha']}). Ciérralo antes de empezar otro.")
        if conn.execute("SELECT 1 FROM Conteos WHERE fecha=? AND es_demo=0", (f,)).fetchone():
            raise DatoInvalido("Ya hay un conteo de esa fecha.")
        stock = _stock_por_producto(conn, incluye_limpieza)
        mejores = prov.mejor_precio_por_producto(conn)
        cid = conn.execute("INSERT INTO Conteos (fecha, incluye_limpieza, notas) VALUES (?,?,?)",
                           (f, int(incluye_limpieza), " ".join((notas or "").split())[:300])).lastrowid
        for pid, s in stock.items():
            conn.execute("INSERT INTO ConteoLineas (conteo_id, producto_id, unidad, cantidad_sistema, precio) VALUES (?,?,?,?,?)",
                         (cid, pid, s["unidad"], round(s["cantidad"], 3), _precio_en(mejores.get(pid), s["unidad"])))
        registrar_cambio(conn, "conteo", "crear", f"Conteo de inventario del {f} ({len(stock)} productos)")
        conn.commit()
        return {"id": cid, "fecha": f, "lineas": len(stock)}
    finally:
        conn.close()


def _lineas(conn: sqlite3.Connection, conteo_id: int) -> List[Dict[str, Any]]:
    filas = []
    for r in conn.execute("SELECT l.*, c.nombre AS producto, c.categoria, c.tipo FROM ConteoLineas l JOIN Catalogo c ON c.id=l.producto_id "
                          "WHERE l.conteo_id=? ORDER BY c.categoria, c.nombre", (conteo_id,)):
        d = dict(r)
        p = d["precio"]
        d["valor_sistema"] = round(d["cantidad_sistema"] * p, 2) if p is not None else None
        d["valor_contado"] = round(d["cantidad_contada"] * p, 2) if p is not None and d["cantidad_contada"] is not None else None
        if d["cantidad_contada"] is None:
            d["diferencia"] = None
            d["diferencia_pct"] = None
        else:
            d["diferencia"] = round(d["cantidad_contada"] - d["cantidad_sistema"], 3)
            d["diferencia_pct"] = round(d["diferencia"] / d["cantidad_sistema"] * 100, 1) if d["cantidad_sistema"] else None
        d["valor_diferencia"] = (round(d["valor_contado"] - d["valor_sistema"], 2)
                                 if d["valor_contado"] is not None and d["valor_sistema"] is not None else None)
        filas.append(d)
    return filas


def detalle(conteo_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        c = conn.execute("SELECT * FROM Conteos WHERE id=?", (conteo_id,)).fetchone()
        if not c:
            return None
        lineas = _lineas(conn, conteo_id)
    finally:
        conn.close()
    contadas = [l for l in lineas if l["cantidad_contada"] is not None]
    v_sis = round(sum(l["valor_sistema"] or 0 for l in lineas), 2)
    v_cont = round(sum(l["valor_contado"] or 0 for l in contadas), 2)
    v_sis_contadas = round(sum(l["valor_sistema"] or 0 for l in contadas), 2)
    alertas = [l for l in contadas if l["diferencia"] and l["cantidad_sistema"] and abs(l["diferencia"]) / l["cantidad_sistema"] > DIFERENCIA_ALERTA]
    mensajes: List[str] = []
    if contadas:
        dif = v_cont - v_sis_contadas
        if abs(dif) >= 0.01:
            mensajes.append(f"En lo contado hasta ahora {'falta' if dif < 0 else 'sobra'} {dinero(abs(dif))} frente a lo que dice el sistema.")
        if alertas:
            peor = max(alertas, key=lambda l: abs(l["valor_diferencia"] or 0))
            mensajes.append(f"{len(alertas)} productos difieren más del {DIFERENCIA_ALERTA * 100:g} %. El que más pesa: {peor['producto']} "
                            f"({peor['diferencia']:+g} {peor['unidad']}, {dinero(peor['valor_diferencia'] or 0)}).")
    faltan = len(lineas) - len(contadas)
    if faltan:
        mensajes.append(f"Faltan {faltan} productos por contar.")
    sin_precio = sum(1 for l in lineas if l["precio"] is None)
    if sin_precio:
        mensajes.append(f"{sin_precio} productos no tienen precio de proveedor: no suman al valor del inventario.")
    return {**dict(c), "lineas": lineas, "n_lineas": len(lineas), "n_contadas": len(contadas), "valor_sistema_actual": v_sis,
            "valor_contado_actual": v_cont, "n_alertas": len(alertas), "mensajes": mensajes}


def listar(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        filas = conn.execute("SELECT c.*, (SELECT count(*) FROM ConteoLineas WHERE conteo_id=c.id) AS n_lineas, "
                             "(SELECT count(*) FROM ConteoLineas WHERE conteo_id=c.id AND cantidad_contada IS NOT NULL) AS n_contadas "
                             "FROM Conteos c ORDER BY c.fecha DESC, c.id DESC").fetchall()
        return [dict(r) for r in filas]
    finally:
        conn.close()


def contar(conteo_id: int, cantidades: Iterable[Dict[str, Any]], db_path: str = DB_PATH) -> Dict[str, Any]:
    """cantidades: [{producto_id, cantidad}] en la unidad de la linea. cantidad None = borrar lo contado."""
    conn = _conn(db_path)
    try:
        c = conn.execute("SELECT estado FROM Conteos WHERE id=?", (conteo_id,)).fetchone()
        if not c:
            raise DatoInvalido("No encuentro ese conteo.")
        if c["estado"] != "abierto":
            raise DatoInvalido("Este conteo ya está cerrado.")
        n = 0
        for x in cantidades:
            v = x.get("cantidad")
            if v is not None:
                try:
                    v = round(float(v), 3)
                except (TypeError, ValueError):
                    raise DatoInvalido("Las cantidades deben ser números.") from None
                if v < 0 or v > 1_000_000:
                    raise DatoInvalido("Las cantidades deben ser números entre 0 y 1000000.")
            cur = conn.execute("UPDATE ConteoLineas SET cantidad_contada=? WHERE conteo_id=? AND producto_id=?", (v, conteo_id, x.get("producto_id")))
            if not cur.rowcount:
                raise DatoInvalido("Ese producto no está en este conteo.")
            n += 1
        conn.commit()
        return {"guardadas": n}
    finally:
        conn.close()


def agregar_producto(conteo_id: int, producto: str, cantidad: float, unidad: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Algo que se encontro en el almacen y el sistema no tenia (stock 0)."""
    from core.normalizar import buscar_producto_id
    from data import proveedores as prov
    fam = familia(unidad)
    if fam is None:
        raise DatoInvalido("La unidad no es válida. Usa kg, g, l, ml, libra, qq o unidad.")
    try:
        cant = convertir(float(cantidad), unidad, fam)
    except (TypeError, ValueError):
        raise DatoInvalido("La cantidad debe ser un número.") from None
    if cant is None or cant < 0:
        raise DatoInvalido("La cantidad debe ser 0 o más.")
    conn = _conn(db_path)
    try:
        c = conn.execute("SELECT estado FROM Conteos WHERE id=?", (conteo_id,)).fetchone()
        if not c:
            raise DatoInvalido("No encuentro ese conteo.")
        if c["estado"] != "abierto":
            raise DatoInvalido("Este conteo ya está cerrado.")
        pid = buscar_producto_id(conn, producto)
        if pid is None:
            raise DatoInvalido("Ese producto no está en tu lista. Créalo primero en Inventario → Productos o con un lote.")
        if conn.execute("SELECT 1 FROM ConteoLineas WHERE conteo_id=? AND producto_id=?", (conteo_id, pid)).fetchone():
            raise DatoInvalido("Ese producto ya está en la hoja: anota la cantidad en su fila.")
        mejor = prov.mejor_precio_por_producto(conn).get(pid)
        conn.execute("INSERT INTO ConteoLineas (conteo_id, producto_id, unidad, cantidad_sistema, cantidad_contada, precio) VALUES (?,?,?,?,?,?)",
                     (conteo_id, pid, fam, 0, round(cant, 3), _precio_en(mejor, fam)))
        conn.commit()
        return {"producto_id": pid, "unidad": fam}
    finally:
        conn.close()


def _ajustar(conn: sqlite3.Connection, fecha: str, lineas: List[Dict[str, Any]]) -> int:
    """Deja el inventario igual a lo contado. Faltante: se descuenta de los lotes que vencen antes. Sobrante: lote de ajuste."""
    from data.inventario import entrada_ajuste, salida_fifo
    hechos = 0
    for l in lineas:
        dif = l["diferencia"]
        if dif is None or abs(dif) < 1e-9:
            continue
        hechos += 1
        if dif > 0:
            entrada_ajuste(conn, l["producto_id"], dif, l["unidad"], fecha, "AJ")
        else:
            salida_fifo(conn, l["producto_id"], -dif, l["unidad"])
    return hechos


def cerrar(conteo_id: int, cerrado_por: str, ajustar_inventario: bool = True, sin_contar_igual: bool = False,
           db_path: str = DB_PATH) -> Dict[str, Any]:
    """Cierra el conteo. sin_contar_igual=True: lo que no se conto se toma igual a lo que dice el sistema."""
    nombre = " ".join((cerrado_por or "").split())
    if len(nombre) < 2:
        raise DatoInvalido("Escribe el nombre de quien cierra el conteo.")
    conn = _conn(db_path)
    try:
        c = conn.execute("SELECT * FROM Conteos WHERE id=?", (conteo_id,)).fetchone()
        if not c:
            raise DatoInvalido("No encuentro ese conteo.")
        if c["estado"] != "abierto":
            raise DatoInvalido("Este conteo ya está cerrado.")
        faltan = conn.execute("SELECT count(*) FROM ConteoLineas WHERE conteo_id=? AND cantidad_contada IS NULL", (conteo_id,)).fetchone()[0]
        if faltan and not sin_contar_igual:
            raise DatoInvalido(f"Faltan {faltan} productos por contar. Cuéntalos o elige «tomar lo que dice el sistema» para esos.")
        if faltan:
            conn.execute("UPDATE ConteoLineas SET cantidad_contada=cantidad_sistema WHERE conteo_id=? AND cantidad_contada IS NULL", (conteo_id,))
        lineas = _lineas(conn, conteo_id)
        v_sis = round(sum(l["valor_sistema"] or 0 for l in lineas), 2)
        v_cont = round(sum(l["valor_contado"] or 0 for l in lineas), 2)
        ajustes = _ajustar(conn, c["fecha"], lineas) if ajustar_inventario else 0
        conn.execute("UPDATE Conteos SET estado='cerrado', cerrado_por=?, cerrado_en=?, valor_sistema=?, valor_contado=?, ajusto_inventario=? WHERE id=?",
                     (nombre, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), v_sis, v_cont, int(ajustar_inventario), conteo_id))
        registrar_cambio(conn, "conteo", "cambiar", f"Conteo del {c['fecha']} cerrado por {nombre}: sistema {dinero(v_sis)}, contado {dinero(v_cont)}"
                         + (f", {ajustes} productos ajustados en el inventario" if ajustar_inventario else ""))
        conn.commit()
        return {"valor_sistema": v_sis, "valor_contado": v_cont, "diferencia": round(v_cont - v_sis, 2), "ajustes": ajustes}
    finally:
        conn.close()


def anular(conteo_id: int, db_path: str = DB_PATH) -> None:
    """Borra un conteo ABIERTO (por ejemplo si se empezo con la fecha equivocada). Uno cerrado no se borra."""
    conn = _conn(db_path)
    try:
        c = conn.execute("SELECT estado, fecha FROM Conteos WHERE id=?", (conteo_id,)).fetchone()
        if not c:
            raise DatoInvalido("No encuentro ese conteo.")
        if c["estado"] != "abierto":
            raise DatoInvalido("Un conteo cerrado no se puede borrar: ya se usa para calcular el costo real.")
        conn.execute("DELETE FROM ConteoLineas WHERE conteo_id=?", (conteo_id,))
        conn.execute("DELETE FROM Conteos WHERE id=?", (conteo_id,))
        registrar_cambio(conn, "conteo", "quitar", f"Conteo abierto del {c['fecha']}")
        conn.commit()
    finally:
        conn.close()


def valor_alimentos(conn: sqlite3.Connection, conteo_id: int) -> float:
    """Valor de lo CONTADO, solo alimentos (lo que entra al costo de comida)."""
    v = conn.execute("SELECT coalesce(sum(l.cantidad_contada * l.precio), 0) FROM ConteoLineas l JOIN Catalogo c ON c.id=l.producto_id "
                     "WHERE l.conteo_id=? AND c.tipo != 'limpieza' AND l.precio IS NOT NULL AND l.cantidad_contada IS NOT NULL", (conteo_id,)).fetchone()[0]
    return round(v, 2)


def par_para_periodo(conn: sqlite3.Connection, desde: str, hasta: str) -> Optional[Dict[str, Any]]:
    """Los dos conteos cerrados que mejor encierran el periodo: el ultimo en o antes de «desde» (o el primero dentro)
    y el ultimo en o antes de «hasta», posterior al inicial."""
    cerrados = conn.execute("SELECT id, fecha, es_demo FROM Conteos WHERE estado='cerrado' ORDER BY fecha").fetchall()
    if len(cerrados) < 2:
        return None
    antes = [c for c in cerrados if c["fecha"] <= desde]
    ini = antes[-1] if antes else next((c for c in cerrados if c["fecha"] >= desde), None)
    if ini is None:
        return None
    fin_cands = [c for c in cerrados if ini["fecha"] < c["fecha"] <= hasta]
    if not fin_cands:
        return None
    fin = fin_cands[-1]
    return {"inicial": {"id": ini["id"], "fecha": ini["fecha"], "valor": valor_alimentos(conn, ini["id"])},
            "final": {"id": fin["id"], "fecha": fin["fecha"], "valor": valor_alimentos(conn, fin["id"])},
            "demo": bool(ini["es_demo"] and fin["es_demo"])}
