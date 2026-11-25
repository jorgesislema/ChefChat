"""Edicion de precios, proveedores, lotes y productos + analisis del dueno (etapa E). Siempre sobre una COPIA de la base."""

import shutil
import sqlite3
from pathlib import Path

import pytest

from data import analisis as ana
from data import inventario as inv
from data import proveedores as prov
from data import recetas as rec

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture()
def db(tmp_path):
    ruta = tmp_path / "t.db"
    shutil.copy2(RAIZ / "chefchat.db", ruta)
    con = sqlite3.connect(ruta)  # las mermas FICTICIAS del balance del turno (noviembre) cambiarian los meses que se prueban
    con.execute("DELETE FROM Mermas WHERE es_demo=1")
    con.commit()
    con.close()
    return str(ruta)


def q(db, sql, args=()):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def pid(db, nombre):
    return q(db, "select id from Catalogo where nombre=?", (nombre,))[0][0]


def prov_id(db, nombre):
    return q(db, "select id from Proveedores where nombre=?", (nombre,))[0][0]


# ---------------------------------------------------------------- precios de proveedor
def test_cambiar_el_precio_cambia_el_costo_de_la_receta(db):
    antes = rec.ficha("BEB-001", db)
    arroz = next(i for i in antes["ingredientes"] if i["ingrediente"].lower() == "arroz blanco")
    p = prov.proveedor_en_texto(arroz["proveedor"], db)
    prov.poner_precio(p["id"], "Arroz", 50.0, "kg", db_path=db)  # carisimo: ahora es el unico precio de hoy
    despues = rec.ficha("BEB-001", db)
    nuevo = next(i for i in despues["ingredientes"] if i["ingrediente"].lower() == "arroz blanco")
    assert nuevo["precio"] <= 50.0
    # si ese proveedor era el mas barato, el costo sube; si no, la receta sigue con el mas barato: nunca baja
    assert despues["costo_calculado"] >= antes["costo_calculado"] - 1e-9


def test_quitar_un_producto_de_un_proveedor_y_volver_a_agregarlo(db):
    a = prov_id(db, "Carnes del Valle")
    pollo = pid(db, "Pollo")
    prov.quitar_producto(a, pollo, db)
    assert all(x["producto"] != "Pollo" for x in prov.detalle(a, db)["productos"])
    assert all(f["proveedor"] != "Carnes del Valle" for f in prov.precios_de_producto(pollo, db))
    assert prov.alertas_de_precio(db_path=db) == [x for x in prov.alertas_de_precio(db_path=db) if x["proveedor"] != "Carnes del Valle" or x["producto"] != "Pollo"]
    with pytest.raises(prov.DatoInvalido, match="no vende"):
        prov.quitar_producto(a, pollo, db)
    prov.poner_precio(a, "Pollo", 9.99, "kg", db_path=db)  # vuelve a venderlo, el historial reaparece
    d = next(x for x in prov.detalle(a, db)["productos"] if x["producto"] == "Pollo")
    assert d["precio"] == 9.99 and d["precio_anterior"] is not None


def test_el_precio_mas_barato_se_recalcula_al_quitar(db):
    pollo = pid(db, "Pollo")
    barato = prov.precios_de_producto(pollo, db)[0]["proveedor"]
    prov.quitar_producto(prov_id(db, barato), pollo, db)
    nuevo = prov.precios_de_producto(pollo, db)
    assert nuevo and nuevo[0]["proveedor"] != barato


def test_editar_proveedor(db):
    a = prov_id(db, "Limpieza Total")
    prov.editar(a, nombre="  Limpieza   Total SA ", telefono="0999", db_path=db)
    d = prov.detalle(a, db)["proveedor"]
    assert d["nombre"] == "Limpieza Total SA" and d["telefono"] == "0999" and d["es_demo"] == 0
    with pytest.raises(prov.DatoInvalido, match="Ya existe"):
        prov.editar(a, nombre="carnes del valle", db_path=db)
    with pytest.raises(prov.DatoInvalido):
        prov.editar(a, nombre=" ", db_path=db)
    with pytest.raises(prov.DatoInvalido, match="No encuentro"):
        prov.editar(99999, nombre="X", db_path=db)


def test_quitar_proveedor_lo_archiva_y_libera_el_nombre(db):
    a = prov_id(db, "Mariscos Pacífico")
    prov.quitar(a, db)
    assert all(p["id"] != a for p in prov.listar(db))
    assert prov.detalle(a, db) is None
    assert prov.crear("Mariscos Pacífico", db_path=db)  # el nombre se puede usar de nuevo
    assert q(db, "select count(*) from ProveedorProductos where proveedor_id=?", (a,))[0][0] > 0  # el historial no se borro
    with pytest.raises(prov.DatoInvalido):
        prov.quitar(a, db)


def test_los_cambios_quedan_anotados(db):
    a = prov_id(db, "Carnes del Valle")
    prov.poner_precio(a, "Pollo", 11.0, "kg", db_path=db)
    prov.quitar_producto(a, pid(db, "Pollo"), db)
    textos = [c["detalle"] for c in inv.cambios(db_path=db)]
    assert any("Carnes del Valle: Pollo de" in t for t in textos) and any("ya no vende Pollo" in t for t in textos)


# ---------------------------------------------------------------- lotes
def test_crear_lote_de_producto_existente_y_nuevo(db):
    r = inv.crear_lote("pollo", 5, "kg", "2026-11-20", "2026-12-05", db_path=db)
    assert r["producto_creado"] is False and r["lote"].startswith("M20261120-")
    n = inv.crear_lote("Quinua Roja", 3, "kg", categoria="Granos", db_path=db)
    assert n["producto_creado"] is True
    assert q(db, "select tipo, origen from Catalogo where id=?", (n["producto_id"],)) == [("alimento", "manual")]
    lote = next(x for x in inv.lotes("Quinua", db_path=db))
    assert lote["cantidad"] == 3 and lote["vence"]  # vence segun vida util (30 dias)


def test_lote_con_datos_malos(db):
    for args, texto in [(("Pollo", 0, "kg"), "mayor que cero"), (("Pollo", -3, "kg"), "mayor que cero"), (("Pollo", "abc", "kg"), "número"),
                        (("Pollo", 2, "cajas"), "unidad no es válida"), (("P", 2, "kg"), "nombre")]:
        with pytest.raises(inv.DatoInvalido, match=texto):
            inv.crear_lote(*args, db_path=db)
    with pytest.raises(inv.DatoInvalido, match="antes de la fecha de ingreso"):
        inv.crear_lote("Pollo", 2, "kg", "2026-11-20", "2026-11-01", db_path=db)
    with pytest.raises(inv.DatoInvalido, match="fecha no es válida"):
        inv.crear_lote("Pollo", 2, "kg", "20/11/2026", db_path=db)
    inv.crear_lote("Pollo", 2, "kg", id_lote="ABC-1", db_path=db)
    with pytest.raises(inv.DatoInvalido, match="Ya existe un lote"):
        inv.crear_lote("Pollo", 2, "kg", id_lote="ABC-1", db_path=db)


def test_editar_y_quitar_lote(db):
    lid = inv.crear_lote("Pollo", 5, "kg", "2026-11-20", "2026-12-05", db_path=db)["id"]
    inv.editar_lote(lid, cantidad=2.5, fecha_caducidad="2026-12-01", db_path=db)
    lote = next(x for x in inv.lotes("Pollo", db_path=db) if x["id"] == lid)
    assert lote["cantidad"] == 2.5 and lote["vence"] == "2026-12-01"
    inv.editar_lote(lid, quitar_caducidad=True, db_path=db)
    assert next(x for x in inv.lotes("Pollo", db_path=db) if x["id"] == lid)["fecha_caducidad_fija"] is None
    with pytest.raises(inv.DatoInvalido):
        inv.editar_lote(lid, cantidad=0, db_path=db)
    inv.quitar_lote(lid, db)
    assert all(x["id"] != lid for x in inv.lotes(db_path=db))
    with pytest.raises(inv.DatoInvalido, match="No encuentro"):
        inv.quitar_lote(lid, db)


def test_el_inventario_cambia_lo_que_ve_el_chat(db):
    from agents.vencimientos import responder_datos
    inv.crear_lote("Yuca Fresca", 100, "kg", "2026-11-24", "2026-11-25", db_path=db)
    r = responder_datos("¿Qué productos vencen en 1 semana?", __import__("datetime").date(2026, 11, 24), db)
    assert "Yuca Fresca" in r


# ---------------------------------------------------------------- productos (catalogo)
def test_editar_producto_y_clasificar(db):
    n = inv.crear_lote("Producto Raro", 1, "kg", db_path=db)["producto_id"]
    inv.editar_producto(n, nombre="producto  raro 2", categoria="vegetales", vida_util_dias=7, db_path=db)
    p = next(x for x in inv.productos(q="raro", db_path=db))
    assert (p["nombre"], p["categoria"], p["vida_util_dias"], p["tipo"], p["origen"]) == ("Producto Raro 2", "Vegetales", 7, "alimento", "manual")
    inv.editar_producto(n, categoria="Limpieza", db_path=db)  # al cambiar a limpieza, el tipo se deduce
    assert next(x for x in inv.productos(q="raro", db_path=db))["tipo"] == "limpieza"
    inv.editar_producto(n, tipo="alimento", db_path=db)
    assert next(x for x in inv.productos(q="raro", db_path=db))["tipo"] == "alimento"


def test_producto_con_datos_malos(db):
    p = pid(db, "Pollo")
    with pytest.raises(inv.DatoInvalido, match="Ya existe otro producto"):
        inv.editar_producto(p, nombre="  tomate ", db_path=db)
    with pytest.raises(inv.DatoInvalido, match="alimento o limpieza"):
        inv.editar_producto(p, tipo="comida", db_path=db)
    with pytest.raises(inv.DatoInvalido, match="vida útil"):
        inv.editar_producto(p, vida_util_dias=0, db_path=db)
    with pytest.raises(inv.DatoInvalido, match="No encuentro"):
        inv.editar_producto(99999, nombre="X", db_path=db)


def test_quitar_producto_solo_si_nadie_lo_usa(db):
    with pytest.raises(inv.DatoInvalido, match="No se puede quitar"):
        inv.quitar_producto(pid(db, "Pollo"), db)  # tiene lotes, precios y recetas
    libre = inv.crear_lote("Producto Sin Uso", 1, "kg", db_path=db)
    inv.quitar_lote(libre["id"], db)
    inv.quitar_producto(libre["producto_id"], db)
    assert all(x["nombre"] != "Producto Sin Uso" for x in inv.productos(db_path=db))


def test_lista_de_productos_trae_precio_y_stock(db):
    p = next(x for x in inv.productos(q="pollo", db_path=db) if x["nombre"] == "Pollo")
    assert p["stock"] > 0 and p["n_proveedores"] == 2 and p["mejor_proveedor"] == "Distribuidora Andina" and p["mejor_precio"] > 0
    assert all(x["tipo"] == "limpieza" for x in inv.productos(tipo="limpieza", db_path=db))


def test_la_clasificacion_manual_sobrevive_a_recargar_recetas(db):
    from data import vinculos
    n = q(db, "select id from Catalogo where origen='auto_receta' limit 1")[0][0]
    inv.editar_producto(n, categoria="Vegetales", db_path=db)
    con = sqlite3.connect(db)
    vinculos.paso_ingredientes(con)
    con.commit()
    con.close()
    assert q(db, "select categoria, origen from Catalogo where id=?", (n,)) == [("Vegetales", "manual")]


# ---------------------------------------------------------------- analisis
def test_mermas_por_mes_motivo_y_producto(db):
    m = ana.mermas(db_path=db)
    assert m["total"] == pytest.approx(sum(x["costo"] for x in m["por_mes"]), abs=0.05)
    assert [x["mes"] for x in m["por_mes"]] == ["2026-04", "2026-05"]
    assert m["por_motivo"][0]["motivo"] == "Sobrante del dia" and m["por_motivo"][0]["costo"] == pytest.approx(59.35)
    assert m["por_motivo"] == sorted(m["por_motivo"], key=lambda x: -x["costo"])
    assert len(m["mensajes"]) >= 2 and "Sobrante del dia" in m["mensajes"][0]
    # abril solo tiene datos de unos 12 dias: no se compara con mayo (engañaria)
    assert next(x for x in m["por_mes"] if x["mes"] == "2026-04")["dias_con_datos"] < 20
    assert not any("subió" in t or "bajó" in t for t in m["mensajes"])
    assert any("Aún no se puede comparar mes con mes" in t for t in m["mensajes"])


def test_mermas_compara_meses_completos(db):
    con = sqlite3.connect(db)
    for dia in range(1, 29):  # llena abril y mayo con un registro por dia para tener meses completos
        for mes in ("2026-04", "2026-05"):
            con.execute("insert into Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado) values (?,?,?,?,?,?)",
                        (f"{mes}-{dia:02d}", "Prueba", 1, "kg", "Caduco", 10.0 if mes == "2026-04" else 15.0))
    con.commit()
    con.close()
    t = " ".join(ana.mermas(db_path=db)["mensajes"])
    assert "la merma subió" in t


def test_mermas_con_rango_de_fechas(db):
    mayo = ana.mermas("2026-05-01", "2026-05-31", db)
    assert [x["mes"] for x in mayo["por_mes"]] == ["2026-05"]
    assert mayo["total"] < ana.mermas(db_path=db)["total"]
    vacio = ana.mermas("2030-01-01", "2030-12-31", db)
    assert vacio["total"] == 0 and vacio["mensajes"] == ["No hay mermas registradas en ese periodo."]
    with pytest.raises(inv.DatoInvalido, match="formato"):
        ana.mermas("ayer", None, db)
    with pytest.raises(inv.DatoInvalido, match="después"):
        ana.mermas("2026-06-01", "2026-05-01", db)


def test_recuperacion_de_sobrantes(db):
    antes = ana.recuperacion(db_path=db)
    assert antes["reutilizados"] == 0 and antes["guardados"] == 2 and "Ningún sobrante" in " ".join(antes["mensajes"])
    ana.registrar_destino_sobrante(1, "reutilizado", 12.5, db)
    ana.registrar_destino_sobrante(2, "desperdicio", db_path=db)
    r = ana.recuperacion(db_path=db)
    assert (r["reutilizados"], r["desperdiciados"], r["guardados"]) == (1, 1, 0) and r["recuperado"] == 12.5
    assert r["pct_recuperado"] == pytest.approx(12.5 / (12.5 + r["perdido"]) * 100, abs=0.1)
    with pytest.raises(inv.DatoInvalido, match="ya se marcó"):
        ana.registrar_destino_sobrante(1, "desperdicio", db_path=db)
    with pytest.raises(inv.DatoInvalido, match="destino"):
        ana.registrar_destino_sobrante(2, "regalado", db_path=db)
    with pytest.raises(inv.DatoInvalido, match="valor"):
        ana.registrar_destino_sobrante(2, "reutilizado", -1, db)
    with pytest.raises(inv.DatoInvalido, match="No encuentro"):
        ana.registrar_destino_sobrante(999, "reutilizado", db_path=db)


@pytest.fixture()
def db_ventas(db):
    """Copia con las ventas de demostracion regeneradas (platos con receta)."""
    import sys
    sys.path.insert(0, str(RAIZ / "scripts"))
    import etapa_b_datos
    etapa_b_datos.main(db, pasos=("ventas",))
    return db


def test_las_ventas_de_demo_solo_usan_platos_con_receta(db_ventas):
    sin = q(db_ventas, "select count(*) from Ventas v where not exists (select 1 from RecetasRAG r where r.id_receta=v.receta_id)")[0][0]
    assert sin == 0
    assert q(db_ventas, "select count(distinct receta_id) from Ventas")[0][0] >= 20
    # el precio de venta siempre es mayor que el costo por plato (si no, la demo mostraria perdidas absurdas)
    assert q(db_ventas, "select count(*) from Ventas v join RecetasRAG r on r.id_receta=v.receta_id where v.precio_unitario <= r.costo")[0][0] == 0
    assert q(db_ventas, "select count(*) from Ventas where vendido>producido")[0][0] == 0


def test_producido_contra_vendido_con_costos_reales(db_ventas):
    p = ana.produccion(db_path=db_ventas)
    assert p["demo"] is True and p["sobrante"] > 0 and p["costo_sobrante"] > 0
    assert all(x["costo_plato"] is not None for x in p["por_plato"])
    costos = [x["costo_sobrante"] for x in p["por_plato"]]
    assert costos == sorted(costos, reverse=True)


def test_platos_rentables_con_datos_completos(db_ventas):
    r = ana.platos_rentables(db_path=db_ventas)
    assert r["sin_costo"] == [] and len(r["mas_ganan"]) == 8 and len(r["menos_ganan"]) == 5
    assert all(x["ganancia"] > 0 for x in r["mas_ganan"])
    assert r["mas_ganan"][0]["ganancia"] >= r["mas_ganan"][-1]["ganancia"] >= r["menos_ganan"][0]["ganancia"]


def test_el_sobrante_en_dinero_se_calcula_a_mano(db_ventas):
    conn = sqlite3.connect(db_ventas)
    conn.row_factory = sqlite3.Row
    fila = conn.execute("select receta_id, sum(producido-vendido) s from Ventas group by receta_id order by s desc limit 1").fetchone()
    costo = conn.execute("select costo from RecetasRAG where id_receta=?", (fila["receta_id"],)).fetchone()[0]
    conn.close()
    encontrado = next(x for x in ana.produccion(db_path=db_ventas)["por_plato"] if x["receta_id"] == fila["receta_id"])
    assert encontrado["sobrante"] == fila["s"] and encontrado["costo_sobrante"] == round(fila["s"] * costo, 2)


def test_filtrar_por_fechas_en_produccion(db_ventas):
    todo = ana.produccion(db_path=db_ventas)
    semana = ana.produccion("2026-11-01", "2026-11-07", db_ventas)
    assert 0 < semana["producido"] < todo["producido"]
    assert semana["periodo"]["desde"] >= "2026-11-01" and semana["periodo"]["hasta"] <= "2026-11-07"
    assert ana.produccion("2030-01-01", "2030-01-31", db_ventas)["mensajes"] == ["No hay ventas registradas en ese periodo."]


def test_ganancia_por_plato_es_ingresos_menos_costo(db_ventas):
    for x in ana.platos_rentables(db_path=db_ventas)["mas_ganan"]:
        assert x["ganancia"] == pytest.approx(x["ingresos"] - x["costo"], abs=0.02)
        assert x["margen_pct"] == pytest.approx(x["ganancia"] / x["ingresos"] * 100, abs=0.1)
    assert "No incluye sueldos" in " ".join(ana.platos_rentables(db_path=db_ventas)["mensajes"])


def test_un_costo_mas_alto_baja_la_ganancia_del_plato(db_ventas):
    antes = {x["receta_id"]: x["ganancia"] for x in ana.platos_rentables(db_path=db_ventas)["mas_ganan"]}
    rid = next(iter(antes))
    con = sqlite3.connect(db_ventas)
    con.execute("update RecetasRAG set costo=costo*2 where id_receta=?", (rid,))
    con.commit()
    con.close()
    r = ana.platos_rentables(db_path=db_ventas)
    despues = {x["receta_id"]: x["ganancia"] for x in r["mas_ganan"] + r["menos_ganan"]}
    assert despues.get(rid, -1e9) < antes[rid]


# ---------------------------------------------------------------- API
def test_api_de_edicion_y_analisis(db, monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    import server.app as app_mod
    monkeypatch.setattr(app_mod, "DB", db)
    c = TestClient(app_mod.app)
    a = prov_id(db, "Carnes del Valle")
    assert c.put(f"/api/proveedores/{a}", json={"telefono": "0987"}).status_code == 200
    assert c.put(f"/api/proveedores/{a}", json={"nombre": "limpieza total"}).status_code == 400
    assert c.delete(f"/api/proveedores/{a}/productos/{pid(db, 'Pollo')}").status_code == 200
    assert c.delete(f"/api/proveedores/{a}/productos/{pid(db, 'Pollo')}").status_code == 400
    lote = c.post("/api/inventario/lotes", json={"producto": "Pollo", "cantidad": 4, "unidad": "kg"})
    assert lote.status_code == 200
    lid = lote.json()["id"]
    assert c.post("/api/inventario/lotes", json={"producto": "Pollo", "cantidad": 0, "unidad": "kg"}).status_code == 400
    assert c.post("/api/inventario/lotes", json={"producto": "Pollo", "cantidad": 1}).status_code == 422
    assert c.put(f"/api/inventario/lotes/{lid}", json={"cantidad": 9}).status_code == 200
    assert any(x["id"] == lid and x["cantidad"] == 9 for x in c.get("/api/inventario/lotes?q=pollo").json()["lotes"])
    assert c.delete(f"/api/inventario/lotes/{lid}").status_code == 200
    assert c.delete(f"/api/inventario/lotes/{lid}").status_code == 400
    prods = c.get("/api/inventario/productos?tipo=limpieza").json()
    assert prods["productos"] and prods["categorias"]
    assert c.put(f"/api/inventario/productos/{pid(db, 'Pollo')}", json={"tipo": "mal"}).status_code == 400
    assert c.delete(f"/api/inventario/productos/{pid(db, 'Pollo')}").status_code == 400
    precios = c.get(f"/api/inventario/productos/{pid(db, 'Pollo')}/precios").json()
    assert precios["stock"]["cantidad"] > 0 and all({"proveedor_id", "proveedor", "precio", "unidad_precio"} <= set(x) for x in precios["precios"])
    assert c.get("/api/inventario/productos/99999/precios").json()["precios"] == []
    assert c.get("/api/cambios").json()["cambios"]
    an = c.get("/api/analisis").json()
    assert set(an) == {"mermas", "recuperacion", "produccion", "rentables", "costo_real"}
    assert c.get("/api/analisis?desde=mal").status_code == 400
    assert c.post("/api/sobrantes/1/destino", json={"destino": "reutilizado", "valor_estimado": 5}).status_code == 200
    assert c.post("/api/sobrantes/1/destino", json={"destino": "reutilizado"}).status_code == 400
    assert c.get("/api/menu/sobrantes").json()["sobrantes"][0]["id"] == 2


def test_dinero_con_formato_de_ecuador():
    from core.formato import dinero
    assert dinero(59.35) == "$59,35"
    assert dinero(1234567.5) == "$1.234.567,50"
    assert dinero(0) == "$0,00"
    assert dinero(-3.2) == "-$3,20"


def test_mensajes_del_analisis_usan_coma_decimal(db):
    t = " ".join(ana.mermas(db_path=db)["mensajes"])
    assert "$59,35" in t and "$59.35" not in t
