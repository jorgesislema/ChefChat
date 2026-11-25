"""Pruebas de la etapa B (en una COPIA de la base; no tocan chefchat.db)."""

import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import etapa_b_datos  # noqa: E402
from data.esquema import asegurar_esquema, tipo_por_categoria  # noqa: E402


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("b") / "t.db"
    shutil.copy2(RAIZ / "chefchat.db", ruta)
    etapa_b_datos.main(str(ruta))
    return str(ruta)


def q(db, sql, args=()):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def test_tipo_limpieza_y_alimento():
    assert tipo_por_categoria("Limpieza") == "limpieza"
    assert tipo_por_categoria("lácteos") == "alimento"
    assert tipo_por_categoria(None) == "alimento"


def test_catalogo_separa_limpieza(db):
    assert {r[0] for r in q(db, "select distinct tipo from Catalogo")} <= {"alimento", "limpieza"}
    assert q(db, "select count(*) from Catalogo where categoria='Limpieza' and tipo!='limpieza'")[0][0] == 0
    assert q(db, "select count(*) from Catalogo where tipo='limpieza' and categoria!='Limpieza'")[0][0] == 0


def test_es_repetible(db):
    antes = [q(db, f"select count(*) from {t}")[0][0] for t in ("RecetaIngredientes", "ProveedorProductos", "Ventas", "Catalogo")]
    etapa_b_datos.main(db)
    asegurar_esquema(db)
    despues = [q(db, f"select count(*) from {t}")[0][0] for t in ("RecetaIngredientes", "ProveedorProductos", "Ventas", "Catalogo")]
    assert antes == despues


def test_ingredientes_bien_ligados(db):
    total, lig = q(db, "select count(*), count(producto_id) from RecetaIngredientes")[0]
    assert total > 1500 and lig / total >= 0.65
    # el agua y el hielo no se compran: nunca llevan producto
    assert q(db, "select count(*) from RecetaIngredientes where lower(ingrediente) in ('agua','hielo') and producto_id is not null")[0][0] == 0
    # "leche de coco" no debe confundirse con leche entera
    assert q(db, "select count(*) from RecetaIngredientes r join Catalogo c on c.id=r.producto_id "
                 "where lower(r.ingrediente)='leche de coco' and c.nombre='Leche Entera'")[0][0] == 0


def test_no_hay_productos_duplicados(db):
    nombres = [r[0] for r in q(db, "select nombre from Catalogo")]
    from core.normalizar import clave
    claves = [clave(n) for n in nombres]
    assert len(claves) == len(set(claves))


def test_proveedores_y_precios(db):
    assert q(db, "select count(*) from Proveedores")[0][0] >= 5
    assert q(db, "select count(*) from Proveedores where nombre like '%Ã%'")[0][0] == 0  # sin caracteres rotos
    assert q(db, "select count(*) from ProveedorProductos where precio<=0")[0][0] == 0
    sin = q(db, "select count(*) from Catalogo c where tipo='alimento' and not exists "
                "(select 1 from ProveedorProductos where producto_id=c.id)")[0][0]
    total = q(db, "select count(*) from Catalogo where tipo='alimento'")[0][0]
    assert sin / total < 0.10
    assert q(db, "select count(*) from ProveedorProductos where es_demo!=1")[0][0] == 0


def test_subida_de_precio_para_la_alerta(db):
    pre = dict(q(db, "select pp.fecha, pp.precio from ProveedorProductos pp join Proveedores p on p.id=pp.proveedor_id "
                     "join Catalogo c on c.id=pp.producto_id where c.nombre='Pollo' and p.nombre='Carnes del Valle'"))
    assert pre["2026-11-01"] > pre["2026-10-01"] * 1.10


def test_ventas_coherentes(db):
    assert q(db, "select count(*) from Ventas where vendido>producido")[0][0] == 0
    n, ini, fin = q(db, "select count(*), min(fecha), max(fecha) from Ventas")[0]
    assert n > 300 and fin < "2026-11-24" and ini >= "2026-08-20"
    assert q(db, "select count(*) from Ventas where es_demo!=1")[0][0] == 0
