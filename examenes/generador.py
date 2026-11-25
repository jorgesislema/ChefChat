"""Genera preguntas desde los fragmentos del RAG y las puntua con JEV.

1. La IA (deepseek) propone preguntas SOLO con el texto del fragmento.
2. JEV puntua cada una (correcta y respondible con ese texto).
3. Entran como 'pendiente' para que el DUENO las apruebe. Nada se aprueba solo.
"""

from __future__ import annotations

import json
import os
import random
import re
import sqlite3
from typing import Any, Dict, List

import core.config  # noqa: F401  (carga .env)
from core import jev
from examenes import servicio

UMBRAL_BUENA = 0.80   # va a la bandeja del dueno
UMBRAL_DUDOSA = 0.50  # entre 0.50 y 0.80: marcada "revisar"; menos de 0.50: se descarta

_PROMPT = (
    "Eres instructor de un restaurante. Con SOLO el texto dado, escribe {n} preguntas de examen de opcion multiple "
    "en espanol. Cada pregunta debe poder responderse con el texto, sin saber nada mas. Evita 'segun el texto'. "
    "Las 3 respuestas incorrectas deben ser creibles pero claramente falsas segun el texto. "
    "Responde SOLO un arreglo JSON: "
    '[{{"enunciado": "...", "correcta": "...", "incorrectas": ["...", "...", "..."], "explicacion": "..."}}]\n\n'
    "TEXTO:\n{texto}"
)


def _llm(prompt: str) -> str:
    from openai import OpenAI
    cli = OpenAI(api_key=os.environ.get("CHEFCHAT_CUSTOM_API_KEY") or os.environ["HMS_API_KEY"],
                 base_url=jev.BASE_URL, default_headers={"User-Agent": "ChefChat/1.0"})
    r = cli.chat.completions.create(
        model=os.environ.get("CHEFCHAT_CUSTOM_MODEL", "deepseek-v4.1-flash-free"),
        messages=[{"role": "user", "content": prompt}], temperature=0.4)
    return r.choices[0].message.content or ""


def _parsear(texto: str) -> List[Dict[str, Any]]:
    m = re.search(r"\[.*\]", texto, flags=re.S)
    if not m:
        return []
    try:
        datos = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [d for d in datos if isinstance(d, dict) and d.get("enunciado") and d.get("correcta")
            and isinstance(d.get("incorrectas"), list) and len(d["incorrectas"]) == 3]


def puntuar(fragmento: str, enunciado: str, opciones: List[str], correcta: int) -> float:
    """Probabilidad de que la pregunta sea correcta y respondible con el fragmento (JEV)."""
    state = {"fragmento": fragmento, "pregunta": enunciado, "opciones": opciones,
             "opcion_marcada_como_correcta": opciones[correcta]}
    r = jev.juzgar(state, {
        "correcta": jev.noul("Is `opcion_marcada_como_correcta` the correct answer to `pregunta`, according only to `fragmento`?"),
        "unica": jev.noul("According to `fragmento`, are all the other options in `opciones` wrong or unsupported?"),
        "respondible": jev.noul("Can `pregunta` be answered using only `fragmento`?"),
    })
    return round(min(jev.probabilidad(v) for v in r.values()), 3)


def generar(tema: str, por_fragmento: int = 2, max_fragmentos: int = 0, db_path: str = servicio.DB_PATH,
            semilla: int = 7) -> Dict[str, int]:
    conn = sqlite3.connect(db_path)
    frags = conn.execute("SELECT documento, seccion, texto FROM ChunksDoc WHERE documento=? AND length(texto)>250 "
                         "ORDER BY id", (tema,)).fetchall()
    conn.close()
    if max_fragmentos:
        frags = frags[:max_fragmentos]
    rng = random.Random(semilla)
    res = {"fragmentos": len(frags), "propuestas": 0, "bandeja": 0, "revisar": 0, "descartadas": 0, "repetidas": 0}
    for doc, sec, texto in frags:
        try:
            propuestas = _parsear(_llm(_PROMPT.format(n=por_fragmento, texto=texto)))
        except Exception:
            continue
        for p in propuestas:
            ops = [p["correcta"], *p["incorrectas"]]
            orden = list(range(4))
            rng.shuffle(orden)
            ops_mezcladas = [ops[i] for i in orden]
            correcta = orden.index(0)
            res["propuestas"] += 1
            try:
                pj = puntuar(texto, p["enunciado"], ops_mezcladas, correcta)
            except jev.JevError:
                continue
            estado = "pendiente" if pj >= UMBRAL_BUENA else "revisar" if pj >= UMBRAL_DUDOSA else "retirada"
            try:
                nuevo = servicio.guardar_pregunta(doc, p["enunciado"], ops_mezcladas, correcta, p.get("explicacion", ""),
                                                  doc, sec, pj, estado, db_path)
            except servicio.ExamenError:
                continue
            if nuevo is None:
                res["repetidas"] += 1
            elif estado == "pendiente":
                res["bandeja"] += 1
            elif estado == "revisar":
                res["revisar"] += 1
            else:
                res["descartadas"] += 1
    return res
