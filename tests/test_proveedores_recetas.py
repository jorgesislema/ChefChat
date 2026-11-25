"""Pruebas de proveedores, precios y recetas (siempre en una COPIA de la base)."""

import shutil
import sqlite3
from pathlib import Path

import pytest

from core.unidades import convertir, familia
from data import proveedores as prov
from data import recetas as rec

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture()
def db(tmp_path):
    ruta = tmp_path / "t.db"
    shutil.copy2(RAIZ / "chefchat.db", ruta)
    return str(ruta)


# ---------------------------------------------------------------- unidades
@pytest.mark.parametrize("cant,u,dest,esperado", [
    (500, "gramos", "kg", 0.5), (2, "kilos", "kg", 2), (250, "mililitros", "l", 0.25), (1.5, "litro", "l", 1.5),
    (3, "unidades", "unidad", 3), (100, "gr", "kg", 0.1),
])
def test_conversiones_seguras(cant, u, dest, esperado):
    assert convertir(cant, u, dest) == pytest.approx(esperado)


@pytest.mark.parametrize("u,dest", [("gramos", "l"), ("mililitros", "kg"), ("pizca", "kg"), ("unidad", "kg"), (None, "kg")])
def test_no_adivina_conversiones_dudosas(u, dest):
    assert convertir(10, u, dest) is None


def test_familia():
    assert familia("Gramos") == "kg" and familia("litros") == "l" and familia("rama") is None


# ---------------------------------------------------------------- proveedores
def test_crear_proveedor_y_rechazar_duplicado(db):
    pid = prov.crear("  Frutas   del Sol ", contacto="Ana", db_path=db)
    assert any(p["id"] == pid and p["nombre"] == "Frutas del Sol" for p in prov.listar(db))
    with pytest.raises(prov.DatoInvalido, match="Ya existe"):
        prov.crear("frutas del sol", db_path=db)  # ignora mayusculas
    with pytest.raises(prov.DatoInvalido):
        prov.crear(" ", db_path=db)


def test_poner_precio_producto_existente_y_nuevo(db):
    pid = prov.crear("Proveedor Prueba", db_path=db)
    r = prov.poner_precio(pid, "pollo", 7.5, "kg", fecha="2026-11-20", db_path=db)  # ignora mayusculas
    assert r["producto_creado"] is False
    r = prov.poner_precio(pid, "Quinua Real", 5.2, "kg", categoria="Granos", db_path=db)
    assert r["producto_creado"] is True
    d = prov.detalle(pid, db)
    assert {p["producto"] for p in d["productos"]} == {"Pollo", "Quinua Real"}
    quinua = next(p for p in d["productos"] if p["producto"] == "Quinua Real")
    assert quinua["tipo"] == "alimento" and quinua["es_mas_barato"] is True


def test_mismo_dia_actualiza_y_no_duplica(db):
    pid = prov.crear("Proveedor Prueba", db_path=db)
    prov.poner_precio(pid, "Pollo", 7.5, "kg", fecha="2026-11-20", db_path=db)
    prov.poner_precio(pid, "Pollo", 8.0, "kg", fecha="2026-11-20", db_path=db)
    n = sqlite3.connect(db).execute("select count(*) from ProveedorProductos where proveedor_id=?", (pid,)).fetchone()[0]
    assert n == 1
    assert prov.detalle(pid, db)["productos"][0]["precio"] == 8.0


def test_limpieza_se_crea_como_limpieza(db):
    pid = prov.crear("Proveedor Prueba", db_path=db)
    prov.poner_precio(pid, "Cloro Nuevo", 2.0, "l", categoria="Limpieza", db_path=db)
    assert next(p for p in prov.detalle(pid, db)["productos"])["tipo"] == "limpieza"


@pytest.mark.parametrize("precio,unidad", [(0, "kg"), (-1, "kg"), (5, "libra"), (1e9, "kg")])
def test_precios_invalidos(db, precio, unidad):
    pid = prov.crear("Proveedor Prueba", db_path=db)
    with pytest.raises(prov.DatoInvalido):
        prov.poner_precio(pid, "Pollo", precio, unidad, db_path=db)


def test_mas_barato_es_consistente(db):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    mejores = prov.mejor_precio_por_producto(con)
    pollo = sqlite3.connect(db).execute("select id from Catalogo where nombre='Pollo'").fetchone()[0]
    assert mejores[pollo]["proveedor"] == "Distribuidora Andina"  # 8,78 contra 12,15 en los datos de demostracion
    d = prov.detalle(next(p["id"] for p in prov.listar(db) if p["nombre"] == "Carnes del Valle"), db)
    fila = next(p for p in d["productos"] if p["producto"] == "Pollo")
    assert fila["es_mas_barato"] is False and fila["mejor_proveedor"] == "Distribuidora Andina"


def test_alerta_de_subida_de_precio(db):
    alertas = prov.alertas_de_precio(db_path=db)
    pollo = [a for a in alertas if a["producto"] == "Pollo" and a["proveedor"] == "Carnes del Valle"]
    assert pollo and pollo[0]["cambio_pct"] > 10
    assert all(a["cambio_pct"] > prov.ALERTA_SUBIDA for a in alertas)


# ---------------------------------------------------------------- recetas
def test_lista_de_recetas(db):
    lista = rec.listar(db_path=db)
    assert len(lista) == 280
    assert len(rec.listar("horchata", db_path=db)) >= 1
    cats = rec.categorias(db)
    assert len(cats) == len({c.lower() for c in cats})


def test_costo_es_suma_de_las_lineas(db):
    f = rec.ficha("BEB-001", db)
    assert f["nombre"] == "Horchata de Arroz"
    assert f["costo_calculado"] == pytest.approx(sum(i["costo"] or 0 for i in f["ingredientes"]), abs=0.01)
    assert 0 <= f["cobertura"] <= 1
    # el agua no se cobra y se dice
    agua = next(i for i in f["ingredientes"] if i["ingrediente"].lower() == "agua")
    assert agua["costo"] is None and agua["nota"] == "No se cobra"


def test_costo_a_mano_de_un_ingrediente(db):
    f = rec.ficha("BEB-001", db)
    arroz = next(i for i in f["ingredientes"] if i["ingrediente"].lower() == "arroz blanco")
    assert arroz["unidad_precio"] == "kg"
    assert arroz["costo"] == pytest.approx(0.1 * arroz["precio"], abs=0.001)  # 100 g = 0,1 kg


def test_porciones_cambian_el_costo_por_porcion(db):
    antes = rec.ficha("BEB-001", db)
    assert antes["porciones_supuestas"] is True
    rec.poner_porciones("BEB-001", 4, db)
    despues = rec.ficha("BEB-001", db)
    assert despues["porciones_supuestas"] is False
    assert despues["costo_porcion"] == pytest.approx(antes["costo_calculado"] / 4, abs=0.01)


@pytest.mark.parametrize("p", [0, -2, 501])
def test_porciones_invalidas(db, p):
    with pytest.raises(prov.DatoInvalido):
        rec.poner_porciones("BEB-001", p, db)


def test_margen_con_precio_de_venta(db):
    f = rec.ficha("PLF-018", db)  # Arroz con Pollo: esta en el menu a 8,50
    assert f["precio_venta"] == pytest.approx(8.5)
    assert f["margen_pct"] == pytest.approx((8.5 - f["costo_plato"]) / 8.5 * 100, abs=0.1)


def test_receta_inexistente(db):
    assert rec.ficha("NO-EXISTE", db) is None


# ---------------------------------------------------------------- API (sobre la copia)
def test_api_de_punta_a_punta(db, monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    import server.app as app_mod
    monkeypatch.setattr(app_mod, "DB", db)
    c = TestClient(app_mod.app)
    r = c.post("/api/proveedores", json={"nombre": "Prueba API"})
    assert r.status_code == 200
    pid = r.json()["id"]
    assert c.post("/api/proveedores", json={"nombre": "prueba api"}).status_code == 400
    assert c.post(f"/api/proveedores/{pid}/precios", json={"producto": "Pollo", "precio": 6, "unidad_precio": "kg"}).status_code == 200
    mala = c.post(f"/api/proveedores/{pid}/precios", json={"producto": "Pollo", "precio": 0, "unidad_precio": "kg"})
    assert mala.status_code == 400 and "mayor que cero" in mala.json()["detail"]
    det = c.get(f"/api/proveedores/{pid}").json()
    assert det["productos"][0]["es_mas_barato"] is True
    assert c.get("/api/proveedores/99999").status_code == 404
    assert c.get("/api/precios/alertas").json()["alertas"]
    assert len(c.get("/api/recetas?q=horchata").json()["recetas"]) >= 1
    assert c.get("/api/recetas/BEB-001").json()["ingredientes"]
    assert c.get("/api/recetas/NO").status_code == 404
    assert c.put("/api/recetas/BEB-001/porciones", json={"porciones": 0}).status_code == 400
    assert c.put("/api/recetas/BEB-001/porciones", json={"porciones": 6}).status_code == 200
    assert c.get("/api/catalogo").json()["productos"]

