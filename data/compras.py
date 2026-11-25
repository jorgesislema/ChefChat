"""Compras recibidas y costo REAL de alimentos (frente al costo TEORICO de lo que se vendio).

- registrar(): guarda la compra, puede sumar el lote al inventario y actualizar el precio del proveedor.
- anular(): quita una compra mal anotada (y su lote, si nadie lo toco).
- costo_real(): compara lo que se gasto en alimentos con lo que debio costar lo producido y lo vendido.

Limite honesto: sin conteos de inventario al inicio y al final del periodo se supone que lo comprado se uso
en el mismo periodo. Con periodos de un mes o mas, ese error es pequeño; con una semana puede ser grande.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.formato import dinero
from core.normalizar import buscar_producto_id, clave
from core.unidades import convertir, familia
from data.esquema import asegurar_esquema, registrar_cambio
from data.proveedores import UNIDADES_PRECIO, DatoInvalido

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
MIN_DIAS_CONFIABLE = 28
OBJETIVO_COSTO_PCT = 35.0  # referencia comun en restaurantes: el costo de alimentos suele ir entre 28 % y 35 % de las ventas


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _fecha(txt: Optional[str], campo: str, defecto: Optional[str] = None) -> Optional[str]:
    if txt is None or str(txt).strip() == "":
        return defecto
    try:
        return date.fromisoformat(str(txt).strip()).isoformat()
    except ValueError:
        raise DatoInvalido(f"{campo}: la fecha no es válida (usa año-mes-día).") from None


def _rango(desde: Optional[str], hasta: Optional[str]) -> tuple[str, str]:
    d = _fecha(desde, "Desde", "0000-01-01")
    h = _fecha(hasta, "Hasta", "9999-12-31")
    if d > h:
        raise DatoInvalido("La fecha «desde» no puede ser después de «hasta».")
    return d, h


# ---------------------------------------------------------------- registrar y anular
def registrar(proveedor_id: int, producto: str, cantidad: float, unidad: str, precio: float, unidad_precio: str,
              fecha: Optional[str] = None, vence: Optional[str] = None, factura: str = "", notas: str = "",
              crear_lote: bool = True, actualizar_precio: bool = True, categoria: Optional[str] = None,
              db_path: str = DB_PATH) -> Dict[str, Any]:
    """Anota una compra. total = cantidad (pasada a la unidad del precio) x precio."""
    from data import inventario as inv
    from data import proveedores as prov
    hoy = date.today().isoformat()
    f = _fecha(fecha, "Fecha de la compra", hoy)
    if f > hoy:
        raise DatoInvalido("La fecha de la compra no puede ser futura.")
    if unidad_precio not in UNIDADES_PRECIO:
        raise DatoInvalido("El precio debe ser por kg, por litro o por unidad.")
    try:
        cant, pre = float(cantidad), float(precio)
    except (TypeError, ValueError):
        raise DatoInvalido("La cantidad y el precio deben ser números.") from None
    if not cant > 0:
        raise DatoInvalido("La cantidad debe ser mayor que cero.")
    if not pre > 0 or pre > 100000:
        raise DatoInvalido("El precio debe ser mayor que cero.")
    equivalente = convertir(cant, unidad, unidad_precio)
    if equivalente is None:
        raise DatoInvalido(f"No puedo pasar «{unidad}» a «{unidad_precio}». Usa una unidad del mismo tipo (peso, volumen o unidades).")
    total = round(equivalente * pre, 2)
    conn = _conn(db_path)
    try:
        if not conn.execute("SELECT 1 FROM Proveedores WHERE id=? AND activo=1", (proveedor_id,)).fetchone():
            raise DatoInvalido("No encuentro ese proveedor.")
        pid_existente = buscar_producto_id(conn, producto)
    finally:
        conn.close()
    lote = None
    if crear_lote:  # crea el producto si no existia y suma el stock
        lote = inv.crear_lote(producto, cant, unidad, f, vence, None, categoria, db_path)
        pid = lote["producto_id"]
    elif pid_existente is None:
        raise DatoInvalido("Ese producto no está en tu lista. Marca «Sumar al inventario» para crearlo.")
    else:
        pid = pid_existente
    conn = _conn(db_path)
    try:
        nombre_prov = conn.execute("SELECT nombre FROM Proveedores WHERE id=?", (proveedor_id,)).fetchone()[0]
        nombre_prod = conn.execute("SELECT nombre FROM Catalogo WHERE id=?", (pid,)).fetchone()[0]
        cid = conn.execute(
            "INSERT INTO Compras (fecha, proveedor_id, producto_id, cantidad, unidad, precio, unidad_precio, total, lote_id, cantidad_lote, factura, notas) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (f, proveedor_id, pid, cant, unidad, pre, unidad_precio, total, lote["id"] if lote else None, cant if lote else None,
             " ".join(factura.split())[:60], " ".join(notas.split())[:300])).lastrowid
        registrar_cambio(conn, "compra", "crear", f"{nombre_prov}: {cant:g} {unidad} de {nombre_prod} por {dinero(total)}")
        conn.commit()
    except Exception:
        conn.close()
        if lote:  # si la compra no se pudo guardar, el lote tampoco debe quedar
            inv.quitar_lote(lote["id"], db_path)
        raise
    conn.close()
    if actualizar_precio:
        prov.poner_precio(proveedor_id, nombre_prod, pre, unidad_precio, fecha=f, db_path=db_path)
    return {"id": cid, "total": total, "producto_id": pid, "lote": lote["lote"] if lote else None, "producto_creado": bool(lote and lote["producto_creado"])}


def anular(compra_id: int, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Quita una compra mal anotada. Su lote se quita solo si aun tiene la cantidad con la que nacio."""
    conn = _conn(db_path)
    try:
        c = conn.execute("SELECT c.*, p.nombre AS proveedor, k.nombre AS producto FROM Compras c JOIN Proveedores p ON p.id=c.proveedor_id "
                         "JOIN Catalogo k ON k.id=c.producto_id WHERE c.id=?", (compra_id,)).fetchone()
        if not c:
            raise DatoInvalido("No encuentro esa compra.")
        lote_quitado, aviso = False, None
        if c["lote_id"]:
            l = conn.execute("SELECT cantidad_actual FROM Inventario WHERE id=?", (c["lote_id"],)).fetchone()
            if l and abs(l["cantidad_actual"] - (c["cantidad_lote"] or 0)) < 1e-9:
                conn.execute("DELETE FROM Inventario WHERE id=?", (c["lote_id"],))
                lote_quitado = True
            elif l:
                aviso = "El lote de esta compra ya se usó en parte: lo dejé en el inventario. Ajústalo en Inventario → Lotes si hace falta."
        conn.execute("DELETE FROM Compras WHERE id=?", (compra_id,))
        registrar_cambio(conn, "compra", "quitar", f"{c['proveedor']}: {c['cantidad']:g} {c['unidad']} de {c['producto']} ({dinero(c['total'])})"
                         + (" y su lote" if lote_quitado else ""))
        conn.commit()
        return {"lote_quitado": lote_quitado, "aviso": aviso}
    finally:
        conn.close()


def listar(desde: Optional[str] = None, hasta: Optional[str] = None, proveedor_id: Optional[int] = None, limite: int = 500,
           db_path: str = DB_PATH) -> Dict[str, Any]:
    d, h = _rango(desde, hasta)
    conn = _conn(db_path)
    try:
        sql = ("SELECT c.id, c.fecha, c.proveedor_id, p.nombre AS proveedor, c.producto_id, k.nombre AS producto, k.categoria, k.tipo, "
               "c.cantidad, c.unidad, c.precio, c.unidad_precio, c.total, c.factura, c.notas, c.es_demo, (c.lote_id IS NOT NULL) AS sumo_lote "
               "FROM Compras c JOIN Proveedores p ON p.id=c.proveedor_id JOIN Catalogo k ON k.id=c.producto_id WHERE c.fecha BETWEEN ? AND ?")
        args: list = [d, h]
        if proveedor_id:
            sql += " AND c.proveedor_id=?"
            args.append(proveedor_id)
        filas = [dict(r) for r in conn.execute(sql + " ORDER BY c.fecha DESC, c.id DESC", args)]
    finally:
        conn.close()
    total = round(sum(f["total"] for f in filas), 2)
    alimentos = round(sum(f["total"] for f in filas if f["tipo"] != "limpieza"), 2)
    por_prov: Dict[str, float] = {}
    for f in filas:
        por_prov[f["proveedor"]] = por_prov.get(f["proveedor"], 0) + f["total"]
    return {"compras": filas[:limite], "n": len(filas), "total": total, "total_alimentos": alimentos, "total_limpieza": round(total - alimentos, 2),
            "por_proveedor": [{"proveedor": k, "total": round(v, 2)} for k, v in sorted(por_prov.items(), key=lambda kv: -kv[1])],
            "demo": bool(filas) and all(f["es_demo"] for f in filas)}


# ---------------------------------------------------------------- costo real contra teorico
def _pct(a: float, b: float) -> Optional[float]:
    return round(a / b * 100, 1) if b else None


def _p(x: Optional[float]) -> str:
    """30.5 -> '30,5' (como en la pantalla)."""
    return f"{x:g}".replace(".", ",") if x is not None else "?"


def costo_real(desde: Optional[str] = None, hasta: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Real = lo que se uso en alimentos. Con dos conteos cerrados: inventario inicial + compras - inventario final (exacto).
    Sin conteos: solo las compras (aproximado). Teorico = lo vendido x costo por plato. La diferencia se reparte en:
    sobreproduccion, merma registrada y «sin explicar» (porciones grandes, errores de registro o perdidas)."""
    from data import recetas as rec
    from data import conteos
    d, h = _rango(desde, hasta)
    costos = {r["id_receta"]: r["costo_plato"] for r in rec.listar(db_path=db_path)}
    conn = _conn(db_path)
    try:
        par = conteos.par_para_periodo(conn, d, h)
        if par:  # con conteos: el periodo va del dia siguiente al conteo inicial hasta el dia del conteo final
            d_q, h_q, op = par["inicial"]["fecha"], par["final"]["fecha"], ">"
        else:
            d_q, h_q, op = d, h, ">="
        filtro = f"fecha {op} ? AND fecha <= ?"
        ventas = conn.execute(f"SELECT fecha, receta_id, producido, vendido, precio_unitario, es_demo FROM Ventas WHERE {filtro}", (d_q, h_q)).fetchall()
        compras = conn.execute(f"SELECT c.fecha, c.total, c.es_demo, k.tipo FROM Compras c JOIN Catalogo k ON k.id=c.producto_id "
                               f"WHERE c.{filtro}", (d_q, h_q)).fetchall()
        merma = conn.execute(f"SELECT round(coalesce(sum(costo_estimado),0),2) FROM Mermas WHERE {filtro}", (d_q, h_q)).fetchone()[0]
    finally:
        conn.close()
    compras_alim = [c for c in compras if c["tipo"] != "limpieza"]
    sin_costo = {v["receta_id"] for v in ventas if v["receta_id"] not in costos}
    ingresos = round(sum(v["vendido"] * v["precio_unitario"] for v in ventas), 2)
    teorico = round(sum(v["vendido"] * costos[v["receta_id"]] for v in ventas if v["receta_id"] in costos), 2)
    producido = round(sum(v["producido"] * costos[v["receta_id"]] for v in ventas if v["receta_id"] in costos), 2)
    comprado = round(sum(c["total"] for c in compras_alim), 2)
    if par:  # costo de lo que se uso = lo que habia + lo que entro - lo que queda
        real = round(par["inicial"]["valor"] + comprado - par["final"]["valor"], 2)
    else:
        real = comprado
    dias_v = {v["fecha"] for v in ventas}
    dias_c = {c["fecha"] for c in compras_alim}
    periodo = {"desde": min(dias_v | dias_c) if dias_v | dias_c else None, "hasta": max(dias_v | dias_c) if dias_v | dias_c else None,
               "dias_con_ventas": len(dias_v), "dias_con_compras": len(dias_c)}
    if par:
        periodo["desde"], periodo["hasta"] = par["inicial"]["fecha"], par["final"]["fecha"]
    base = {"periodo": periodo, "metodo": "conteo" if par else "compras", "comprado": comprado,
            "inventario_inicial": par["inicial"] if par else None, "inventario_final": par["final"] if par else None,
            "demo": bool(ventas or compras) and all(x["es_demo"] for x in list(ventas) + list(compras)),
            "ingresos": ingresos, "teorico": teorico, "teorico_producido": producido, "real": real, "merma_registrada": merma,
            "teorico_pct": _pct(teorico, ingresos), "real_pct": _pct(real, ingresos), "objetivo_pct": OBJETIVO_COSTO_PCT,
            "diferencia": round(real - teorico, 2), "diferencia_pct": _pct(real - teorico, teorico),
            "desglose": None, "platos_sin_costo": len(sin_costo), "mensajes": []}
    m = base["mensajes"]
    if not ventas and not compras_alim:
        m.append("No hay ventas ni compras registradas en ese periodo.")
        return base
    if not compras_alim and not par:  # con conteos, un periodo sin compras es valido: se uso lo que habia
        m.append("Hay ventas pero no hay compras registradas en ese periodo: anota las compras para ver el costo real.")
        return base
    if not ventas:
        m.append("Hay compras pero no hay ventas registradas en ese periodo: no se puede comparar.")
        return base
    sobreprod = round(producido - teorico, 2)
    sin_explicar = round(real - producido - merma, 2)
    base["desglose"] = {"vendido": teorico, "sobreproduccion": sobreprod, "merma_registrada": merma, "sin_explicar": sin_explicar}
    if par:
        m.append(f"Con los conteos del {par['inicial']['fecha']} y del {par['final']['fecha']}: había {dinero(par['inicial']['valor'])}, "
                 f"compraste {dinero(comprado)} y quedan {dinero(par['final']['valor'])}. Usaste {dinero(real)} en alimentos y vendiste "
                 f"{dinero(ingresos)}: el costo real es el {_p(base['real_pct'])} % de las ventas.")
    else:
        m.append(f"Gastaste {dinero(real)} en alimentos y vendiste {dinero(ingresos)}: el costo real es el {_p(base['real_pct'])} % de las ventas.")
    m.append(f"Según las recetas, lo vendido debió costar {dinero(teorico)} ({_p(base['teorico_pct'])} %).")
    if real > teorico:
        m.append(f"Diferencia: {dinero(real - teorico)} ({_p(base['diferencia_pct'])} % más de lo esperado). "
                 f"Se explica así: sobreproducción {dinero(sobreprod)}, merma anotada {dinero(merma)}"
                 + (f" y {dinero(sin_explicar)} sin explicar (porciones grandes, robos o errores de registro"
                    + ("" if par else ", o compras que aún no se usan") + ")." if sin_explicar > 0 else "."))
    else:
        m.append(f"Gastaste {dinero(teorico - real)} menos de lo esperado: puede haber compras sin anotar o stock que se compró antes del periodo.")
    if base["real_pct"] is not None and base["real_pct"] > OBJETIVO_COSTO_PCT:
        m.append(f"El costo real supera el {_p(OBJETIVO_COSTO_PCT)} % de las ventas, una referencia común en restaurantes: revisa porciones y precios.")
    dias = len(dias_v | dias_c)
    # con conteos al inicio y al final el resultado es exacto aunque el periodo sea corto: los avisos son solo sin conteo
    if not par:
        m.append("Este cálculo supone que lo comprado se usó en el mismo periodo. Haz un conteo de inventario a fin de mes para que sea exacto.")
    if not par and dias < MIN_DIAS_CONFIABLE:
        m.append(f"Solo hay {dias} días con datos: con menos de {MIN_DIAS_CONFIABLE} días, lo que compraste puede no haberse usado aún y la comparación es poco precisa.")
    if sin_costo:
        m.append(f"{len(sin_costo)} platos vendidos no tienen costo por plato y no cuentan en el costo esperado.")
    return base
