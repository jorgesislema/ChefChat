"""Genera evaluation/banco_200_preguntas.json.

Cada pregunta trae la respuesta correcta calculada DESDE la base de datos
(no escrita a mano). El campo `debe_contener` son textos que la respuesta
del chat tiene que incluir. Fecha ancla: 2026-11-24.

Uso:  python evaluation/generar_banco_preguntas.py
"""

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from agents import vencimientos as v  # noqa: E402

HOY = date(2026, 11, 24)
DB = str(RAIZ / "chefchat.db")


def nombres(filas):
    return sorted({f["producto"] for f in filas})


def main() -> None:
    conn = sqlite3.connect(DB)
    qs = []

    def add(tema, pregunta, contiene, variantes=()):
        for p in (pregunta, *variantes):
            qs.append({"tema": tema, "pregunta": p, "debe_contener": contiene})

    # 1) Vencimientos por periodo
    dic = v.vencen_en_mes(2026, 12)
    add("vence_diciembre", "¿Qué productos vencen en diciembre?", nombres(dic),
        ["Dime los productos que caducan en diciembre", "¿Qué se me vence en diciembre?"])
    for s in range(1, 9):
        filas = v.vencen_en_semanas(s, HOY)
        add("vence_semanas", f"¿Qué productos vencen en {s} semana{'s' if s > 1 else ''}?",
            nombres(filas), [f"Qué se vence de hoy a {s} semanas"])
    add("ya_vencidos", "¿Qué productos ya están vencidos?",
        nombres(v.ya_vencidos(HOY))[:10], ["¿Qué tengo que botar por vencido?"])

    # 2) Por producto: primera fecha futura de vencimiento
    prods = conn.execute("SELECT id, nombre, categoria FROM Catalogo ORDER BY id").fetchall()
    futuros = v.vencen_entre(HOY, date(2100, 1, 1))
    for _id, nombre, _cat in prods:
        fs = [f for f in futuros if f["producto"] == nombre]
        if fs:
            add("fecha_producto", f"¿Cuándo vence el lote más próximo de {nombre}?", [fs[0]["vence"]],
                [f"¿Qué día caduca {nombre}?"])
        else:
            add("fecha_producto", f"¿Cuándo vence {nombre}?", ["no"])

    # 3) Stock total por producto (solo lotes con stock)
    for _id, nombre, _cat in prods:
        fila = conn.execute(
            "SELECT round(sum(i.cantidad_actual),1), min(i.unidad) FROM Inventario i "
            "JOIN Catalogo c ON c.id=i.producto_id WHERE c.nombre=? AND i.cantidad_actual>0", (nombre,)
        ).fetchone()
        if fila[0]:
            add("stock_producto", f"¿Cuánto {nombre} tengo en inventario?", [f"{fila[0]:g}"])

    # 4) Por categoría en diciembre
    for cat in sorted({c for _, _, c in prods if c}):
        n = nombres([f for f in dic if f["categoria"] == cat])
        add("categoria_diciembre", f"¿Qué de la categoría {cat} vence en diciembre?", n or ["no"])

    # 5) Mermas por motivo y trabajadores
    for motivo, total in conn.execute(
        "SELECT motivo, round(sum(costo_estimado),2) FROM Mermas GROUP BY motivo ORDER BY 2 DESC"
    ):
        add("mermas_motivo", f"¿Cuánto costó la merma por {motivo}?", [f"{total:g}"])
    for cargo, n in conn.execute("SELECT cargo, count(*) FROM Trabajadores GROUP BY cargo"):
        add("personal_cargo", f"¿Cuántos {cargo} hay?", [str(n)])
    for turno, n in conn.execute("SELECT turno, count(*) FROM Trabajadores GROUP BY turno"):
        add("personal_turno", f"¿Cuántas personas trabajan en el turno {turno}?", [str(n)])

    # Recortar a 200 manteniendo variedad (orden estable por tema)
    por_tema = {}
    for q in qs:
        por_tema.setdefault(q["tema"], []).append(q)
    final = []
    while len(final) < 200 and any(por_tema.values()):
        for t in list(por_tema):
            if por_tema[t] and len(final) < 200:
                final.append(por_tema[t].pop(0))
    for i, q in enumerate(final, 1):
        q["id"] = f"P{i:03d}"
    out = RAIZ / "evaluation" / "banco_200_preguntas.json"
    out.write_text(json.dumps({"fecha_ancla": HOY.isoformat(), "preguntas": final},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Preguntas: {len(final)} (generadas {len(qs)}) -> {out}")
    from collections import Counter
    print(Counter(q["tema"] for q in final))


if __name__ == "__main__":
    main()
