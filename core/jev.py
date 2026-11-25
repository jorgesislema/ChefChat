"""Cliente de JEV (modelo juez, TypeSafe AI) via 100milionseek.top.

Se envia `state` (el contenido a juzgar) y `questions` (preguntas tipadas);
vuelve una respuesta por pregunta. `noul` = probabilidad de que algo sea cierto (0 a 1).
Es un consejo, no una verdad: el codigo decide con umbrales.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict

# Cargar .env si existe (core.config lo hace al importarse)
import core.config  # noqa: F401

BASE_URL = os.environ.get("CHEFCHAT_CUSTOM_BASE_URL", "https://100milionseek.top/v1")
MODELO = os.environ.get("CHEFCHAT_JEV_MODEL", "jev-1.13-free")


class JevError(RuntimeError):
    pass


def noul(instrucciones: str) -> Dict[str, str]:
    return {"type": "noul", "instructions": instrucciones}


def choice(instrucciones: str, opciones: Dict[str, str]) -> Dict[str, Any]:
    return {"type": "choice", "instructions": instrucciones, "options": opciones}


def juzgar(state: Any, questions: Dict[str, Dict[str, Any]], reintentos: int = 3, timeout: int = 60) -> Dict[str, Any]:
    """Devuelve {id_pregunta: respuesta}. Para noul: {'type':'noul','noul':0.93}."""
    clave = os.environ.get("CHEFCHAT_CUSTOM_API_KEY") or os.environ.get("HMS_API_KEY")
    if not clave:
        raise JevError("Falta HMS_API_KEY en .env")
    cuerpo = json.dumps({"model": MODELO, "state": state, "questions": questions}).encode()
    ultimo = ""
    for i in range(reintentos):
        req = urllib.request.Request(
            f"{BASE_URL}/systemone", data=cuerpo,
            headers={"Authorization": f"Bearer {clave}", "Content-Type": "application/json",
                     "User-Agent": "ChefChat/1.0", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())["answers"]
        except urllib.error.HTTPError as e:
            ultimo = f"HTTP {e.code}"
            if e.code in (429, 502, 503, 529):
                time.sleep(2 * (i + 1))
                continue
            raise JevError(f"JEV rechazo la peticion ({ultimo})") from e
        except (urllib.error.URLError, TimeoutError) as e:
            ultimo = str(e)
            time.sleep(2 * (i + 1))
    raise JevError(f"JEV no respondio: {ultimo}")


def probabilidad(respuesta: Dict[str, Any]) -> float:
    return float(respuesta.get("noul", 0.0))
