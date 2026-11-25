"""Limpia duplicados existentes en chefchat.db (se puede repetir sin riesgo).

- Une productos del Catalogo con el mismo nombre (ignora mayusculas/acentos).
- Unifica categorias, unidades y motivos de merma.
- Crea un indice unico para que no vuelvan a nacer duplicados.
Copia de seguridad: chefchat.db.pre_unificar.bak (una sola vez).
"""

import shutil
import sqlite3
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from core.normalizar import clave, motivo_canonico, unidad_canonica  # noqa: E402

DB = RAIZ / "chefchat.db"


def mejor_variante(vals):
    """Prefiere la que tiene acentos; si empata, la mas frecuente."""
    cont = Counter(vals)
    return max(cont, key=lambda v: (sum(ord(c) > 127 for c in v), cont[v]))


def main() -> None:
    bak = RAIZ / "chefchat.db.pre_unificar.bak"
    if not bak.exists():
        shutil.copy2(DB, bak)
    c = sqlite3.connect(DB)
    tablas_ref = [t for (t,) in c.execute("select name from sqlite_master where type='table'")
                  if any(col[1] == "producto_id" for col in c.execute(f"pragma table_info([{t}])"))]

    # 1) Catalogo: unir repetidos (queda el id mas bajo)
    grupos = {}
    for pid, nombre in c.execute("select id, nombre from Catalogo order by id"):
        grupos.setdefault(clave(nombre), []).append(pid)
    unidos = 0
    for ids in grupos.values():
        if len(ids) > 1:
            keep = ids[0]
            for dup in ids[1:]:
                for t in tablas_ref:
                    c.execute(f"update [{t}] set producto_id=? where producto_id=?", (keep, dup))
                c.execute("delete from Catalogo where id=?", (dup,))
                unidos += 1

    # 2) Categorias: una sola forma por categoria
    cats = {}
    for (cat,) in c.execute("select categoria from Catalogo where categoria is not null"):
        cats.setdefault(clave(cat), []).append(cat)
    for vals in cats.values():
        buena = mejor_variante(vals)
        c.execute("update Catalogo set categoria=? where categoria in (%s)" % ",".join("?" * len(set(vals))),
                  (buena, *set(vals)))

    # 3) Unidades y motivos
    for t in ("Inventario", "Mermas"):
        for (u,) in c.execute(f"select distinct unidad from {t}").fetchall():
            c.execute(f"update {t} set unidad=? where unidad=?", (unidad_canonica(u), u))
    for (m,) in c.execute("select distinct motivo from Mermas").fetchall():
        c.execute("update Mermas set motivo=? where motivo=?", (motivo_canonico(m), m))

    # 3b) Documentos RAG repetidos o vacios -> inactivos (no se borran)
    c.execute("""update DocumentosRAG set estado='inactivo' where id not in
                 (select min(id) from DocumentosRAG group by nombre, tamano_bytes)""")
    c.execute("""update DocumentosRAG set estado='inactivo' where extension='.pdf' and id not in
                 (select documento_id from DocumentosTexto where length(coalesce(contenido_completo,''))>50)""")

    # 4) Indice unico (ignora mayusculas) para frenar duplicados nuevos
    c.execute("create unique index if not exists ux_catalogo_nombre on Catalogo(nombre collate nocase)")
    huerfanos = c.execute(
        "select count(*) from Inventario i left join Catalogo c on c.id=i.producto_id where c.id is null"
    ).fetchone()[0]
    c.commit()
    print(f"Productos unidos: {unidos}. Lotes sin producto en catalogo: {huerfanos} (no se tocaron).")
    c.close()


if __name__ == "__main__":
    main()
