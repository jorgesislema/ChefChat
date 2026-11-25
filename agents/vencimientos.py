"""Consultas de vencimiento por rango de fechas (sin IA, solo SQL).

Fuente unica de verdad: tablas Inventario y Catalogo de chefchat.db.
La fecha de vencimiento de un lote es fecha_caducidad_fija si existe;
si no, fecha_ingreso + vida_util_dias del catalogo.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")

_SQL = """
SELECT c.nombre AS producto, c.categoria AS categoria, c.tipo AS tipo,
       i.id_lote AS lote, i.cantidad_actual AS cantidad, i.unidad AS unidad,
       date(COALESCE(i.fecha_caducidad_fija,
            date(i.fecha_ingreso, '+' || c.vida_util_dias || ' days'))) AS vence
FROM Inventario i JOIN Catalogo c ON c.id = i.producto_id
WHERE i.cantidad_actual > 0
  AND vence IS NOT NULL
  AND vence BETWEEN ? AND ?
ORDER BY vence, producto
"""


def vencen_entre(desde: date, hasta: date, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Lotes con stock que vencen entre dos fechas (ambas incluidas). Trae tipo: alimento o limpieza."""
    from data.esquema import asegurar_esquema
    asegurar_esquema(db_path)  # idempotente: crea columna tipo si falta
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(_SQL, (desde.isoformat(), hasta.isoformat()))]
    finally:
        conn.close()


def vencen_en_semanas(semanas: int, hoy: Optional[date] = None, db_path: str = DB_PATH):
    hoy = hoy or date.today()
    return vencen_entre(hoy, hoy + timedelta(weeks=semanas), db_path)


def vencen_en_mes(anio: int, mes: int, db_path: str = DB_PATH):
    ini = date(anio, mes, 1)
    fin = (date(anio + (mes == 12), mes % 12 + 1, 1)) - timedelta(days=1)
    return vencen_entre(ini, fin, db_path)


def ya_vencidos(hoy: Optional[date] = None, db_path: str = DB_PATH):
    hoy = hoy or date.today()
    return vencen_entre(date(2000, 1, 1), hoy - timedelta(days=1), db_path)


def formatear(filas: List[Dict[str, Any]], titulo: str) -> str:
    """Texto para el chat. Dice claro cuando no hay datos."""
    if not filas:
        return f"{titulo}: no hay lotes en ese periodo."
    out = [f"{titulo} ({len(filas)} lotes):"]
    for f in filas:
        out.append(f"- {f['producto']} | lote {f['lote']} | {f['cantidad']:g} {f['unidad']} | vence {f['vence']}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Respuestas directas desde la base (sin IA). Devuelve None si no entiende.
# ---------------------------------------------------------------------------
import re
import unicodedata

_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
          "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def _n(t: str) -> str:
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _fetch(sql: str, args=(), db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def responder_datos(pregunta: str, hoy: Optional[date] = None, db_path: str = DB_PATH) -> Optional[str]:
    """Contesta preguntas de vencimiento, stock, mermas y personal usando solo la base."""
    hoy = hoy or date.today()
    t = _n(pregunta)
    productos = _fetch("SELECT nombre, categoria FROM Catalogo", db_path=db_path)
    # el nombre del producto debe aparecer como palabra completa ("pan" no cuenta dentro de "pantalla")
    prod = None if "categoria" in t else max((p for p in productos if re.search(rf"\b{re.escape(_n(p[0]))}\b", t)),
                                             key=lambda p: len(p[0]), default=None)
    pide_venc = bool(re.search(r"venc|caduc|botar", t)) and "merma" not in t

    if pide_venc:
        if prod:
            fut = [f for f in vencen_entre(hoy, date(2100, 1, 1), db_path) if f["producto"] == prod[0]]
            if not fut:
                return f"No hay lotes vigentes de {prod[0]} con fecha de vencimiento."
            return formatear(fut[:3], f"Lotes de {prod[0]} por vencer (el mas proximo primero)")
        if re.search(r"ya (esta|estan)|vencid|botar", t):
            return formatear(ya_vencidos(hoy, db_path), "Productos ya vencidos")
        filas = None
        titulo = ""
        for nombre, num in _MESES.items():
            if nombre in t:
                anio = hoy.year + (1 if num < hoy.month else 0)
                filas, titulo = vencen_en_mes(anio, num, db_path), f"Vencen en {nombre} {anio}"
        m = re.search(r"(\d+)\s*semana", t)
        if filas is None and (m or "semana" in t):
            s = int(m.group(1)) if m else 1
            filas, titulo = vencen_en_semanas(s, hoy, db_path), f"Vencen en las proximas {s} semanas"
        if filas is not None:
            cat = next((c for c in {p[1] for p in productos if p[1]} if _n(c) in t), None)
            if cat:
                filas = [f for f in filas if f["categoria"] == cat]
                titulo += f" (categoria {cat})"
            return formatear(filas, titulo)
        return None

    if prod and "merma" not in t and re.search(r"cuanto|stock|tengo|inventario|hay de", t):
        tot, uni = _fetch(
            "SELECT round(sum(i.cantidad_actual),1), min(i.unidad) FROM Inventario i JOIN Catalogo c "
            "ON c.id=i.producto_id WHERE c.nombre=? AND i.cantidad_actual>0", (prod[0],), db_path)[0]
        return f"Stock de {prod[0]}: {tot:g} {uni}." if tot else f"No hay stock de {prod[0]}."

    if "merma" in t:
        for motivo, total in _fetch("SELECT motivo, round(sum(costo_estimado),2) FROM Mermas GROUP BY motivo",
                                    db_path=db_path):
            if motivo and _n(motivo) in t:
                return f"Merma por {motivo}: costo total {total:g}."
        return None

    if re.search(r"cuantos|cuantas|personas", t):
        for cargo, n in _fetch("SELECT cargo, count(*) FROM Trabajadores GROUP BY cargo", db_path=db_path):
            if cargo and _n(cargo) in t:
                return f"Hay {n} {cargo}."
        for turno, n in _fetch("SELECT turno, count(*) FROM Trabajadores GROUP BY turno", db_path=db_path):
            if turno and re.search(rf"turno {re.escape(_n(turno))}", t):
                return f"En el turno {turno} trabajan {n} personas."
    return None
