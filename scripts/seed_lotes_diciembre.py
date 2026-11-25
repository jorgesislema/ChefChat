"""Agrega lotes DE PRUEBA (datos ficticios) con vencimientos en las proximas
semanas y en diciembre 2026. Es repetible: borra y recrea solo los lotes L26-*.

Uso:  python scripts/seed_lotes_diciembre.py
Copia de seguridad: chefchat.db.bak (se crea una sola vez).
"""

import random
import shutil
import sqlite3
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / "chefchat.db"
HOY = date(2026, 11, 24)  # fecha ancla de los datos de prueba


def main() -> None:
    bak = RAIZ / "chefchat.db.bak"
    if not bak.exists():
        shutil.copy2(DB, bak)
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM Inventario WHERE id_lote LIKE 'L26-%'")
    prods = conn.execute(
        "SELECT id, nombre, vida_util_dias FROM Catalogo WHERE vida_util_dias IS NOT NULL ORDER BY id"
    ).fetchall()
    rng = random.Random(2026)
    n = 0
    for pid, _nombre, vida in prods:
        # 1 a 2 lotes por producto, vencimiento entre hoy+2 y hoy+55 dias
        for _ in range(rng.choice([1, 1, 2])):
            n += 1
            vence = HOY + timedelta(days=rng.randint(2, 55))
            ingreso = vence - timedelta(days=min(int(vida), 20))
            cant = round(rng.uniform(1, 30), 1)
            unidad = conn.execute(
                "SELECT unidad FROM Inventario WHERE producto_id=? LIMIT 1", (pid,)
            ).fetchone()
            conn.execute(
                "INSERT INTO Inventario (producto_id, fecha_ingreso, cantidad_actual, unidad, id_lote, fecha_caducidad_fija)"
                " VALUES (?,?,?,?,?,?)",
                (pid, ingreso.isoformat(), cant, unidad[0] if unidad else "kg",
                 f"L26-{n:03d}", vence.isoformat()),
            )
    conn.commit()
    print(f"Lotes de prueba creados: {n}")
    conn.close()


if __name__ == "__main__":
    main()
