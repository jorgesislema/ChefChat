"""Respuestas del chat sobre menu, costos y que cocinar. Todo sale de data/menu.py (codigo), sin IA.

responder_menu(pregunta) devuelve el texto o None si la pregunta no es de este tema.
"""

from __future__ import annotations

import re
from datetime import date
from typing import List, Optional

from core.normalizar import clave
from data import menu as m

COMIDAS = ("desayuno", "almuerzo", "merienda", "cena")


def _dinero(x: float) -> str:
    from core.formato import dinero
    return dinero(x)


def _comidas(t: str) -> List[str]:
    return [c for c in COMIDAS if c in t]


def _dias_vencer(t: str) -> int:
    n = re.search(r"(\d+)\s*dias?", t)
    if n:
        return min(int(n.group(1)), 30)
    if "semana" in t:
        return 7
    if "pasado manana" in t:
        return 2
    if "manana" in t:
        return 1
    if "hoy" in t:
        return 0
    return 1


def _sin(t: str) -> List[str]:
    return re.findall(r"sin\s+(gluten|lacteos?|huevos?|frutos secos|mani|soya|pescado|mariscos?)", t)


def _tope(t: str) -> Optional[float]:
    for patron in (r"(?:tope|maximo|maxima|hasta|no (?:mas|pase) de|menos de)\s*(?:de\s*)?\$?\s*(\d+(?:[.,]\d+)?)",
                   r"\$\s*(\d+(?:[.,]\d+)?)", r"(\d+(?:[.,]\d+)?)\s*(?:dolares|usd)"):
        mt = re.search(patron, t)
        if mt:
            return float(mt.group(1).replace(",", "."))
    return None


def _fmt_cocinar(r: dict) -> str:
    if not r["por_vencer"]:
        return "No hay alimentos que venzan en ese plazo. No hace falta cocinar nada con urgencia."
    nombres = ", ".join(f"{p['producto']} ({'hoy' if p['dias'] == 0 else 'mañana' if p['dias'] == 1 else 'en ' + str(p['dias']) + ' días'})"
                        for p in r["por_vencer"][:10])
    out = [f"💡 Vence pronto: {nombres}."]
    if not r["recetas"]:
        out.append("Ninguna receta alcanza a usar bien ese stock.")
        return "\n".join(out)
    out.append("Puedes cocinar:")
    for rc in r["recetas"]:
        usa = "; ".join(f"{u['producto']} (alcanza para {u['alcanza_para']})" for u in rc["usa"])
        out.append(f"- {rc['nombre']} | costo por plato {_dinero(rc['costo_plato'])} | hasta {rc['porciones_posibles']} platos | usa {usa}")
    if r.get("aviso"):
        out.append(r["aviso"])
    return "\n".join(out)


def _fmt_costos(r: dict, comidas: List[str]) -> str:
    out = ["Costo por persona (suma del costo por plato de cada puesto):"]
    for c, d in r["por_comida"].items():
        if comidas and c not in comidas:
            continue
        if d is None:
            out.append(f"- {c.capitalize()}: no hay recetas suficientes.")
        else:
            out.append(f"- {c.capitalize()}: típico {_dinero(d['tipico'])} (desde {_dinero(d['minimo'])} hasta {_dinero(d['maximo'])})")
    return "\n".join(out)


def _fmt_menu(r: dict) -> str:
    out = []
    for d in r["dias"]:
        if len(r["dias"]) > 1:
            out.append(f"**{d['fecha']}**")
        for c in d["comidas"]:
            if not c["platos"]:
                out.append(f"- {c['servicio'].capitalize()}: {c['nota']}")
                continue
            platos = " + ".join(f"{p['nombre']} ({_dinero(p['costo_plato'])})" for p in c["platos"])
            luz = " 💡" if any(p["usa_por_vencer"] for p in c["platos"]) else ""
            out.append(f"- {c['servicio'].capitalize()}: {platos} = {_dinero(c['costo_persona'])} por persona{luz}")
            if c.get("nota"):
                out.append(f"  ⚠️ {c['nota']}")
        if d["costo_persona"] is not None:
            out.append(f"Total del día: {_dinero(d['costo_persona'])} por persona")
    if len(r["dias"]) > 1 and r["costo_promedio_dia"] is not None:
        out.append(f"Promedio por día: {_dinero(r['costo_promedio_dia'])} por persona")
    if r["tope_dia"] and not r["cumple_tope"]:
        out.append(f"No pude cumplir el tope de {_dinero(r['tope_dia'])} por persona con estas condiciones.")
    if r["usa_por_vencer"] and any(p["usa_por_vencer"] for d in r["dias"] for c in d["comidas"] for p in c["platos"]):
        out.append("💡 = usa productos que vencen pronto.")
    if r.get("aviso"):
        out.append(r["aviso"])
    return "\n".join(out)


def _fmt_sobrantes(r: dict) -> str:
    if not r["sobrantes"]:
        return "No hay sobrantes registrados para reutilizar."
    out = ["Sobrantes registrados:"]
    for s in r["sobrantes"]:
        linea = f"- {s['producto']} ({s['cantidad']:g} {s['unidad']}), usar hasta {s['usar_hasta']}"
        if not s["vigente"]:
            out.append(f"{linea}. {s['mensaje']}")
        elif s["recetas"]:
            out.append(f"{linea}. Ideas: " + ", ".join(f"{x['nombre']} ({_dinero(x['costo_plato'])})" for x in s["recetas"]))
        else:
            out.append(f"{linea}. No encontré recetas que lo usen.")
    return "\n".join(out)


def responder_menu(pregunta: str, hoy: Optional[date] = None, db_path: str = m.DB_PATH) -> Optional[str]:
    t = clave(pregunta)
    hoy = hoy or date.today()
    try:
        if re.search(r"sobrante|aprovech\w+ (la )?merma|reutiliz", t) and not re.search(r"cost|cuanto|merma por", t):
            return _fmt_sobrantes(m.aprovechar_sobrantes(hoy, db_path))
        # "categoria Cocina" es una categoria de productos, no "cocinar"
        if "categoria" not in t and re.search(r"(que|cual).*(cocin|prepar|hac)\w*.*(venc|caduc|por vencer)|(venc|caduc).*(cocin|prepar|menu)", t):
            return _fmt_cocinar(m.que_cocinar(_dias_vencer(t), hoy, excluir=_sin(t), db_path=db_path))
        if re.search(r"\b(sugier|dise[nñ]|arma|armar|propon|crea|haz|genera)\w*.*\bmenu\b|\bmenu\b.*\b(sugier|dise[nñ]|arma)", t):
            comidas = _comidas(t) or ["desayuno", "almuerzo", "merienda"]
            dias = 7 if "semana" in t else 1
            return _fmt_menu(m.armar_menu(comidas, _tope(t), _sin(t), dias, hoy=hoy, db_path=db_path))
        if re.search(r"costo|cuesta|cuanto", t) and re.search(r"persona|comensal|cubierto", t):
            return _fmt_costos(m.costo_por_persona(db_path), _comidas(t))
    except m.MenuError as e:
        return str(e)
    return None
