"""Analisis para el dueno (etapa E). Todo son cuentas sobre la base: la IA no calcula nada.

Cada bloque dice de que periodo son los datos, porque las mermas y las ventas no cubren las mismas fechas.
Los "mensajes" son frases armadas por codigo con los numeros del bloque (una idea, un dato).
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.normalizar import clave
from data import recetas as rec
from data.esquema import asegurar_esquema, registrar_cambio
from data.proveedores import DatoInvalido

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
MIN_DIAS_COMPARAR = 20
DESTINOS = ("reutilizado", "desperdicio", "donacion")  # los valores que permite la tabla SobrantesReutilizables
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _rango(desde: Optional[str], hasta: Optional[str]) -> tuple[str, str]:
    try:
        d = date.fromisoformat(desde).isoformat() if desde else "0000-01-01"
        h = date.fromisoformat(hasta).isoformat() if hasta else "9999-12-31"
    except ValueError:
        raise DatoInvalido("Las fechas deben tener el formato año-mes-día.") from None
    if d > h:
        raise DatoInvalido("La fecha «desde» no puede ser después de «hasta».")
    return d, h


def _mes_texto(ym: str) -> str:
    anio, mes = ym.split("-")
    return f"{MESES[int(mes) - 1]} {anio}"


def _pct(parte: float, total: float) -> Optional[float]:
    return round(parte / total * 100, 1) if total else None


def _d(x: float) -> str:
    from core.formato import dinero
    return dinero(x)


# ---------------------------------------------------------------- mermas
def mermas(desde: Optional[str] = None, hasta: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    d, h = _rango(desde, hasta)
    conn = _conn(db_path)
    try:
        filas = conn.execute("SELECT fecha, producto, motivo, costo_estimado FROM Mermas WHERE fecha BETWEEN ? AND ?", (d, h)).fetchall()
    finally:
        conn.close()
    total = round(sum(f["costo_estimado"] or 0 for f in filas), 2)
    dias_mes: Dict[str, set] = defaultdict(set)
    por_mes: Dict[str, List[float]] = defaultdict(lambda: [0.0, 0])
    por_motivo: Dict[str, List[float]] = defaultdict(lambda: [0.0, 0])
    por_producto: Dict[str, List[float]] = defaultdict(lambda: [0.0, 0])
    etiqueta: Dict[str, str] = {}
    for f in filas:
        costo = f["costo_estimado"] or 0
        por_mes[f["fecha"][:7]][0] += costo
        por_mes[f["fecha"][:7]][1] += 1
        dias_mes[f["fecha"][:7]].add(f["fecha"][:10])
        for dic, nombre in ((por_motivo, f["motivo"]), (por_producto, f["producto"])):
            k = clave(nombre)
            etiqueta.setdefault(k, " ".join((nombre or "Sin dato").split()).capitalize())
            dic[k][0] += costo
            dic[k][1] += 1
    meses = [{"mes": m, "texto": _mes_texto(m), "costo": round(v[0], 2), "registros": int(v[1]), "dias_con_datos": len(dias_mes[m])}
             for m, v in sorted(por_mes.items())]
    motivos = [{"motivo": etiqueta[k], "costo": round(v[0], 2), "veces": int(v[1]), "pct": _pct(v[0], total)}
               for k, v in sorted(por_motivo.items(), key=lambda kv: -kv[1][0]) if v[0] > 0][:10]
    productos = [{"producto": etiqueta[k], "costo": round(v[0], 2), "veces": int(v[1]), "pct": _pct(v[0], total)}
                 for k, v in sorted(por_producto.items(), key=lambda kv: -kv[1][0]) if v[0] > 0][:10]
    mensajes: List[str] = []
    if not filas:
        mensajes.append("No hay mermas registradas en ese periodo.")
    else:
        if motivos:
            m0 = motivos[0]
            mensajes.append(f"El motivo que más dinero pierde es «{m0['motivo']}»: {_d(m0['costo'])} ({m0['pct']:g} % del total).")
        if productos:
            p0 = productos[0]
            mensajes.append(f"El producto que más se desperdicia es {p0['producto']}: {_d(p0['costo'])} en {p0['veces']} registros.")
        # solo se compara mes con mes si los dos meses tienen datos de al menos 20 dias; si no, la comparacion engaña
        if len(meses) >= 2:
            a, b = meses[-2], meses[-1]
            if a["dias_con_datos"] >= MIN_DIAS_COMPARAR and b["dias_con_datos"] >= MIN_DIAS_COMPARAR and a["costo"] > 0:
                cambio = (b["costo"] - a["costo"]) / a["costo"] * 100
                mensajes.append(f"De {a['texto']} a {b['texto']} la merma {'subió' if cambio > 0 else 'bajó'} {abs(cambio):.0f} % ({_d(a['costo'])} → {_d(b['costo'])}).")
            else:
                pocos = a if a["dias_con_datos"] < b["dias_con_datos"] else b
                mensajes.append(f"Aún no se puede comparar mes con mes: de {pocos['texto']} solo hay datos de {pocos['dias_con_datos']} días.")
    return {"periodo": {"desde": min((f["fecha"] for f in filas), default=None), "hasta": max((f["fecha"] for f in filas), default=None)},
            "total": total, "registros": len(filas), "por_mes": meses, "por_motivo": motivos, "por_producto": productos, "mensajes": mensajes}


# ---------------------------------------------------------------- merma recuperada
def recuperacion(desde: Optional[str] = None, hasta: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Sobrantes que se reutilizaron contra lo que se perdio. El dinero recuperado lo escribe el chef al marcar el sobrante."""
    d, h = _rango(desde, hasta)
    perdido = mermas(desde, hasta, db_path)["total"]
    conn = _conn(db_path)
    try:
        filas = conn.execute("SELECT destino_actual, count(*) AS n, round(sum(cantidad),1) AS cant, round(sum(coalesce(valor_estimado,0)),2) AS valor, "
                             "sum(valor_estimado IS NULL) AS sin_valor FROM SobrantesReutilizables WHERE fecha_registro BETWEEN ? AND ? GROUP BY destino_actual",
                             (d, h)).fetchall()
    finally:
        conn.close()
    por = {f["destino_actual"]: f for f in filas}
    get = lambda k, c: (por[k][c] if k in por else 0) or 0  # noqa: E731
    recuperado = round(get("reutilizado", "valor"), 2)
    mensajes: List[str] = []
    if not por:
        mensajes.append("Aún no hay sobrantes registrados en ese periodo.")
    else:
        if get("reutilizado", "n"):
            mensajes.append(f"Se reutilizaron {get('reutilizado', 'n')} sobrantes ({get('reutilizado', 'cant'):g} kg o litros), con un valor de {_d(recuperado)}.")
            if get("reutilizado", "sin_valor"):
                mensajes.append(f"A {get('reutilizado', 'sin_valor')} reutilizados les falta el valor estimado: anótalo para que el dinero recuperado sea real.")
            if recuperado + perdido:
                mensajes.append(f"De cada $100 en juego (perdido + recuperado) se recuperaron ${recuperado / (recuperado + perdido) * 100:.0f}.")
        else:
            mensajes.append("Ningún sobrante se ha marcado como reutilizado todavía.")
        if get("almacenado", "n"):
            mensajes.append(f"Hay {get('almacenado', 'n')} sobrantes guardados esperando destino: úsalos antes de que pase su plazo.")
    return {"recuperado": recuperado, "perdido": perdido, "reutilizados": int(get("reutilizado", "n")), "desperdiciados": int(get("desperdicio", "n")),
            "donados": int(get("donacion", "n")),
            "guardados": int(get("almacenado", "n")), "kg_reutilizados": get("reutilizado", "cant"), "kg_desperdiciados": get("desperdicio", "cant"),
            "pct_recuperado": _pct(recuperado, recuperado + perdido), "mensajes": mensajes}


def registrar_destino_sobrante(sobrante_id: int, destino: str, valor_estimado: Optional[float] = None, db_path: str = DB_PATH) -> None:
    if destino not in DESTINOS:
        raise DatoInvalido("El destino debe ser «reutilizado», «desperdicio» o «donacion».")
    if valor_estimado is not None and not 0 <= valor_estimado <= 100000:
        raise DatoInvalido("El valor estimado debe estar entre 0 y 100000.")
    conn = _conn(db_path)
    try:
        r = conn.execute("SELECT producto_sopro, cantidad, unidad, destino_actual FROM SobrantesReutilizables WHERE id_sobrante=?", (sobrante_id,)).fetchone()
        if not r:
            raise DatoInvalido("No encuentro ese sobrante.")
        if r["destino_actual"] != "almacenado":
            raise DatoInvalido(f"Este sobrante ya se marcó como {r['destino_actual']}.")
        conn.execute("UPDATE SobrantesReutilizables SET destino_actual=?, valor_estimado=?, fecha_destino=? WHERE id_sobrante=?",
                     (destino, valor_estimado, date.today().isoformat(), sobrante_id))
        registrar_cambio(conn, "sobrante", "cambiar", f"{r['producto_sopro']} ({r['cantidad']:g} {r['unidad']}): {destino}" +
                         (f", valor {valor_estimado:g}" if valor_estimado is not None else ""))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- producido, vendido y ganancia
def _costos_plato(db_path: str) -> Dict[str, float]:
    return {r["id_receta"]: r["costo_plato"] for r in rec.listar(db_path=db_path)}


def _ventas(desde: Optional[str], hasta: Optional[str], db_path: str) -> tuple[List[sqlite3.Row], Dict[str, float]]:
    d, h = _rango(desde, hasta)
    conn = _conn(db_path)
    try:
        filas = conn.execute("SELECT fecha, servicio, plato, receta_id, producido, vendido, precio_unitario, es_demo FROM Ventas WHERE fecha BETWEEN ? AND ?",
                             (d, h)).fetchall()
    finally:
        conn.close()
    return filas, _costos_plato(db_path)


def produccion(desde: Optional[str] = None, hasta: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    filas, costos = _ventas(desde, hasta, db_path)
    por_plato: Dict[str, Dict[str, Any]] = {}
    por_servicio: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    for f in filas:
        k = f["receta_id"] or f["plato"]
        p = por_plato.setdefault(k, {"plato": f["plato"], "receta_id": f["receta_id"], "producido": 0, "vendido": 0, "costo_plato": costos.get(f["receta_id"])})
        p["producido"] += f["producido"]
        p["vendido"] += f["vendido"]
        por_servicio[clave(f["servicio"])][0] += f["producido"]
        por_servicio[clave(f["servicio"])][1] += f["vendido"]
    platos = []
    for p in por_plato.values():
        sobra = p["producido"] - p["vendido"]
        platos.append({**p, "sobrante": sobra, "pct_sobrante": _pct(sobra, p["producido"]),
                       "costo_sobrante": round(sobra * p["costo_plato"], 2) if p["costo_plato"] is not None else None})
    platos.sort(key=lambda p: (-(p["costo_sobrante"] if p["costo_sobrante"] is not None else -1), -p["sobrante"]))
    prod, vend = sum(p["producido"] for p in platos), sum(p["vendido"] for p in platos)
    costo_sobra = round(sum(p["costo_sobrante"] or 0 for p in platos), 2)
    servicios = [{"servicio": s, "producido": v[0], "vendido": v[1], "pct_sobrante": _pct(v[0] - v[1], v[0])}
                 for s, v in sorted(por_servicio.items(), key=lambda kv: -(kv[1][0] - kv[1][1]))]
    mensajes: List[str] = []
    if not filas:
        mensajes.append("No hay ventas registradas en ese periodo.")
    else:
        mensajes.append(f"Se produjeron {prod:,} platos y se vendieron {vend:,}: sobró el {_pct(prod - vend, prod):g} % (unos {_d(costo_sobra)} de comida).")
        if platos and platos[0]["costo_sobrante"]:
            p0 = platos[0]
            mensajes.append(f"El plato que más sobra en dinero es «{p0['plato']}»: {p0['sobrante']} platos, {_d(p0['costo_sobrante'])}. Prepara menos cantidad.")
        if servicios and servicios[0]["pct_sobrante"] is not None:
            mensajes.append(f"El servicio con más sobrante es {servicios[0]['servicio']} ({servicios[0]['pct_sobrante']:g} % de lo producido).")
    return {"periodo": {"desde": min((f["fecha"] for f in filas), default=None), "hasta": max((f["fecha"] for f in filas), default=None)},
            "demo": bool(filas) and all(f["es_demo"] for f in filas), "producido": prod, "vendido": vend, "sobrante": prod - vend,
            "pct_sobrante": _pct(prod - vend, prod), "costo_sobrante": costo_sobra, "por_plato": platos[:15], "por_servicio": servicios, "mensajes": mensajes}


def platos_rentables(desde: Optional[str] = None, hasta: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Ganancia por plato = vendido x (precio de venta - costo por plato). Los platos sin costo conocido se avisan aparte."""
    filas, costos = _ventas(desde, hasta, db_path)
    acum: Dict[str, Dict[str, Any]] = {}
    for f in filas:
        k = f["receta_id"] or f["plato"]
        a = acum.setdefault(k, {"plato": f["plato"], "receta_id": f["receta_id"], "vendido": 0, "ingresos": 0.0, "costo_plato": costos.get(f["receta_id"])})
        a["vendido"] += f["vendido"]
        a["ingresos"] += f["vendido"] * f["precio_unitario"]
    platos, sin_costo = [], []
    for a in acum.values():
        if a["costo_plato"] is None:
            sin_costo.append(a["plato"])
            continue
        costo = a["vendido"] * a["costo_plato"]
        platos.append({"plato": a["plato"], "receta_id": a["receta_id"], "vendido": a["vendido"], "ingresos": round(a["ingresos"], 2), "costo": round(costo, 2),
                       "ganancia": round(a["ingresos"] - costo, 2), "margen_pct": _pct(a["ingresos"] - costo, a["ingresos"])})
    platos.sort(key=lambda p: -p["ganancia"])
    total_ing = round(sum(p["ingresos"] for p in platos), 2)
    total_gan = round(sum(p["ganancia"] for p in platos), 2)
    mensajes: List[str] = []
    if platos:
        mejor, peor = platos[0], platos[-1]
        mensajes.append(f"El plato que más deja es «{mejor['plato']}»: {_d(mejor['ganancia'])} de ganancia ({mejor['vendido']} vendidos).")
        if len(platos) > 1:
            mensajes.append(f"El que menos deja es «{peor['plato']}»: {_d(peor['ganancia'])} (margen {peor['margen_pct']:g} %). Revisa su precio o su receta.")
        mensajes.append(f"Ganancia total sobre ingredientes: {_d(total_gan)} de {_d(total_ing)} vendidos ({_pct(total_gan, total_ing):g} %). No incluye sueldos ni gastos fijos.")
    else:
        mensajes.append("No hay ventas con costo conocido en ese periodo.")
    return {"periodo": {"desde": min((f["fecha"] for f in filas), default=None), "hasta": max((f["fecha"] for f in filas), default=None)},
            "demo": bool(filas) and all(f["es_demo"] for f in filas), "ingresos": total_ing, "ganancia": total_gan,
            "mas_ganan": platos[:8], "menos_ganan": list(reversed(platos[-5:])) if len(platos) > 8 else [], "sin_costo": sin_costo, "mensajes": mensajes}


def resumen(desde: Optional[str] = None, hasta: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    from data import compras
    return {"mermas": mermas(desde, hasta, db_path), "recuperacion": recuperacion(desde, hasta, db_path),
            "produccion": produccion(desde, hasta, db_path), "rentables": platos_rentables(desde, hasta, db_path),
            "costo_real": compras.costo_real(desde, hasta, db_path)}
