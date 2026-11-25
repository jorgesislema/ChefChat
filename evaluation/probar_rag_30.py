"""Prueba el RAG de documentos con 30 preguntas del banco de examenes.

Pregunta al chat real y JEV juzga si la respuesta dice lo mismo que la correcta.
Tambien revisa que cite el documento de origen.
Uso:  python evaluation/probar_rag_30.py [cantidad]
"""

import json
import os
import random
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("CHEFCHAT_AI_PROVIDER", "custom")
from core import jev  # noqa: E402
from core.normalizar import clave  # noqa: E402


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    c = sqlite3.connect(RAIZ / "chefchat.db")
    filas = c.execute("SELECT enunciado, opciones, correcta, documento, seccion FROM PreguntasExamen "
                      "WHERE puntaje_jev>=0.9").fetchall()
    random.Random(11).shuffle(filas)
    from agents.orchestrator import Orchestrator
    from data.db_manager import DatabaseManager
    orq = Orchestrator(db_manager=DatabaseManager(str(RAIZ / "chefchat.db")))
    ok, cita, fallas = 0, 0, []
    for enun, ops, corr, doc, sec in filas[:n]:
        esperada = json.loads(ops)[corr]
        try:
            resp = orq.generar_respuesta([{"rol": "user", "contenido": enun}])
        except Exception as e:
            resp = f"ERROR {e}"
        r = jev.juzgar({"pregunta": enun, "respuesta_del_chat": resp, "respuesta_esperada": esperada},
                       {"igual": jev.noul("Does `respuesta_del_chat` give the same answer as `respuesta_esperada` to `pregunta`?")})
        p = jev.probabilidad(r["igual"])
        cita += int(clave(doc)[:20] in clave(resp))
        if p >= 0.7:
            ok += 1
        else:
            fallas.append({"pregunta": enun, "esperada": esperada, "recibio": resp[:300], "jev": p})
    print(f"Respuestas correctas segun JEV: {ok}/{n}. Citan el documento correcto: {cita}/{n}")
    (RAIZ / "evaluation" / "resultado_rag_30.json").write_text(json.dumps(fallas, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
