"""Genera preguntas de examen para todos los manuales indexados.

Uso:  python scripts/generar_preguntas.py [max_fragmentos_por_manual]
Las preguntas quedan 'pendiente' (o 'revisar'): el dueno las aprueba despues.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from examenes import generador, servicio  # noqa: E402


def main() -> None:
    tope = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    temas = [r[0] for r in sqlite3.connect(servicio.DB_PATH).execute("SELECT DISTINCT documento FROM ChunksDoc")]
    for t in temas:
        print(t, generador.generar(t, max_fragmentos=tope), flush=True)


if __name__ == "__main__":
    main()
