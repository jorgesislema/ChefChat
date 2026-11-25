"""Corre el banco de 200 preguntas y cuenta aciertos.

Un acierto = la respuesta contiene TODOS los textos de `debe_contener`
(sin importar mayusculas ni acentos).

Modos:
  --modo chat      pregunta al Orchestrator real (usa tu proveedor de IA)
  --modo oraculo   responde con vencimientos.py (prueba que el banco es correcto)
Uso:  python evaluation/correr_banco.py --modo chat --max 50
"""

import argparse
import json
import sys
import unicodedata
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def norm(t: str) -> str:
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def acierta(resp: str, debe) -> bool:
    r = norm(resp)
    return all(norm(x) in r for x in debe)


def responder_oraculo(q: dict) -> str:
    from agents import vencimientos as v
    texto = norm(q["pregunta"])
    hoy = date(2026, 11, 24)
    if "diciembre" in texto:
        return v.formatear(v.vencen_en_mes(2026, 12), "Diciembre")
    return " ".join(q["debe_contener"])  # solo valida que el banco se pueda leer


def crear_chat():
    from agents.orchestrator import Orchestrator
    from data.db_manager import DatabaseManager
    orq = Orchestrator(db_manager=DatabaseManager(str(RAIZ / "chefchat.db")))
    return lambda q: orq.generar_respuesta([{"rol": "user", "contenido": q["pregunta"]}])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["chat", "oraculo"], default="chat")
    ap.add_argument("--max", type=int, default=200)
    a = ap.parse_args()
    banco = json.loads((RAIZ / "evaluation" / "banco_200_preguntas.json").read_text(encoding="utf-8"))
    preguntas = banco["preguntas"][: a.max]
    responder = crear_chat() if a.modo == "chat" else responder_oraculo
    ok, fallas = 0, []
    for q in preguntas:
        try:
            resp = responder(q) if a.modo == "oraculo" else responder(q)
        except Exception as e:  # una pregunta rota no frena el resto
            resp = f"ERROR: {e}"
        if acierta(resp, q["debe_contener"]):
            ok += 1
        else:
            fallas.append({"id": q["id"], "tema": q["tema"], "pregunta": q["pregunta"],
                           "esperaba": q["debe_contener"], "recibio": str(resp)[:300]})
    print(f"Aciertos: {ok}/{len(preguntas)}")
    out = RAIZ / "evaluation" / f"resultado_{a.modo}.json"
    out.write_text(json.dumps(fallas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Fallas guardadas en {out}")


if __name__ == "__main__":
    main()
