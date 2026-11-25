"""Conteo de inventario de fin de mes y costo real exacto. Siempre sobre una COPIA de la base."""

import shutil
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from data import compras as com
from data import conteos as cnt
from data.proveedores import DatoInvalido

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import etapa_b_datos  # noqa: E402


def q(db, sql, args=()):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


@pytest.fixture()
def db(tmp_path):
    ruta = tmp_path / "t.db"
    shutil.copy2(RAIZ / "chefchat.db", ruta)
    con = sqlite3.connect(ruta)
    from data.esquema import asegurar_esquema
    asegurar_esquema(str(ruta))
    con.execute("DELETE FROM ConteoLineas")
    con.execute("DELETE FROM Conteos")  # cada prueba empieza sin conteos
    con.commit()
    con.close()
    return str(ruta)


def pid(db, nombre):
    return q(db, "select id from Catalogo where nombre=?", (nombre,))[0][0]


def linea(det, nombre):
    return next(l for l in det["lineas"] if l["producto"] == nombre)


# ---------------------------------------------------------------- crear y contar
def test_crear_arma_la_hoja_con_el_stock_del_sistema(db):
    r = cnt.crear(db_path=db)
    det = cnt.detalle(r["id"], db)
    assert det["estado"] == "abierto" and det["n_lineas"] == r["lineas"] > 10 and det["n_contadas"] == 0
    assert all(l["tipo"] != "limpieza" for l in det["lineas"])  # por defecto no se cuenta limpieza
    pollo = linea(det, "Pollo")
    esperado = q(db, "select sum(cantidad_actual) from Inventario where producto_id=? and cantidad_actual>0 and unidad='kg'", (pid(db, "Pollo"),))[0][0]
    assert pollo["unidad"] == "kg" and pollo["cantidad_sistema"] == pytest.approx(esperado, abs=0.01)
    assert pollo["precio"] > 0 and pollo["valor_sistema"] == pytest.approx(pollo["cantidad_sistema"] * pollo["precio"], abs=0.01)
    assert any("Faltan" in m for m in det["mensajes"])


def test_gramos_y_libras_se_suman_en_kg(db):
    con = sqlite3.connect(db)
    p = pid(db, "Pollo")
    con.execute("delete from Inventario where producto_id=?", (p,))
    con.execute("insert into Inventario (producto_id, fecha_ingreso, cantidad_actual, unidad, id_lote) values (?, '2026-11-20', 1500, 'g', 'T1')", (p,))
    con.execute("insert into Inventario (producto_id, fecha_ingreso, cantidad_actual, unidad, id_lote) values (?, '2026-11-20', 2, 'libra', 'T2')", (p,))
    con.commit()
    con.close()
    det = cnt.detalle(cnt.crear(db_path=db)["id"], db)
    assert linea(det, "Pollo")["cantidad_sistema"] == pytest.approx(1.5 + 2 * 0.45359237, abs=0.001)


def test_con_limpieza(db):
    det = cnt.detalle(cnt.crear(incluye_limpieza=True, db_path=db)["id"], db)
    assert any(l["tipo"] == "limpieza" for l in det["lineas"])


def test_reglas_al_crear(db):
    cnt.crear(db_path=db)
    with pytest.raises(DatoInvalido, match="Ya hay un conteo abierto"):
        cnt.crear((date.today() - timedelta(days=1)).isoformat(), db_path=db)
    with pytest.raises(DatoInvalido, match="aún no llega"):
        cnt.crear((date.today() + timedelta(days=1)).isoformat(), db_path=db)
    with pytest.raises(DatoInvalido, match="fecha"):
        cnt.crear("31/10/2026", db_path=db)


def test_contar_de_a_poco_y_diferencias(db):
    c = cnt.crear(db_path=db)["id"]
    det = cnt.detalle(c, db)
    pollo = linea(det, "Pollo")
    cnt.contar(c, [{"producto_id": pollo["producto_id"], "cantidad": pollo["cantidad_sistema"] - 1}], db)
    det = cnt.detalle(c, db)
    p = linea(det, "Pollo")
    assert det["n_contadas"] == 1 and p["diferencia"] == pytest.approx(-1) and p["valor_diferencia"] == pytest.approx(-p["precio"], abs=0.01)
    assert any("falta" in m for m in det["mensajes"])
    cnt.contar(c, [{"producto_id": pollo["producto_id"], "cantidad": None}], db)  # borrar lo contado
    assert cnt.detalle(c, db)["n_contadas"] == 0


@pytest.mark.parametrize("valor,texto", [(-1, "entre 0"), ("abc", "números"), (2_000_000, "entre 0")])
def test_cantidades_invalidas(db, valor, texto):
    c = cnt.crear(db_path=db)["id"]
    p = cnt.detalle(c, db)["lineas"][0]["producto_id"]
    with pytest.raises(DatoInvalido, match=texto):
        cnt.contar(c, [{"producto_id": p, "cantidad": valor}], db)
    with pytest.raises(DatoInvalido, match="no está en este conteo"):
        cnt.contar(c, [{"producto_id": 999999, "cantidad": 1}], db)


def test_agregar_algo_que_el_sistema_no_tenia(db):
    c = cnt.crear(db_path=db)["id"]
    sin_stock = q(db, "select c.nombre from Catalogo c where c.tipo='alimento' and not exists (select 1 from Inventario i where i.producto_id=c.id and i.cantidad_actual>0) "
                      "and exists (select 1 from ProveedorProductos pp where pp.producto_id=c.id) limit 1")[0][0]
    r = cnt.agregar_producto(c, sin_stock, 500, "g", db)
    l = linea(cnt.detalle(c, db), sin_stock)
    assert r["unidad"] == "kg" and l["cantidad_sistema"] == 0 and l["cantidad_contada"] == 0.5
    with pytest.raises(DatoInvalido, match="ya está en la hoja"):
        cnt.agregar_producto(c, sin_stock, 1, "kg", db)
    with pytest.raises(DatoInvalido, match="no está en tu lista"):
        cnt.agregar_producto(c, "Producto Inexistente", 1, "kg", db)
    with pytest.raises(DatoInvalido, match="unidad"):
        cnt.agregar_producto(c, "Pollo", 1, "cajas", db)


# ---------------------------------------------------------------- cerrar y ajustar
def test_no_cierra_si_falta_contar(db):
    c = cnt.crear(db_path=db)["id"]
    with pytest.raises(DatoInvalido, match="Faltan"):
        cnt.cerrar(c, "Ana", db_path=db)
    with pytest.raises(DatoInvalido, match="nombre"):
        cnt.cerrar(c, " ", db_path=db)


def test_cerrar_ajusta_el_inventario_a_lo_contado(db):
    c = cnt.crear(db_path=db)["id"]
    det = cnt.detalle(c, db)
    pollo, otro = linea(det, "Pollo"), next(l for l in det["lineas"] if l["producto"] != "Pollo" and l["cantidad_sistema"] > 0)
    cnt.contar(c, [{"producto_id": pollo["producto_id"], "cantidad": round(pollo["cantidad_sistema"] - 2, 3)},
                   {"producto_id": otro["producto_id"], "cantidad": round(otro["cantidad_sistema"] + 3, 3)}], db)
    r = cnt.cerrar(c, "María García", ajustar_inventario=True, sin_contar_igual=True, db_path=db)
    assert r["ajustes"] == 2
    det = cnt.detalle(c, db)
    assert det["estado"] == "cerrado" and det["n_contadas"] == det["n_lineas"] and det["cerrado_por"] == "María García"
    assert r["diferencia"] == pytest.approx(det["valor_contado"] - det["valor_sistema"], abs=0.01)
    # el inventario ahora dice lo mismo que el conteo
    p = pollo["producto_id"]
    total_pollo = q(db, "select sum(cantidad_actual) from Inventario where producto_id=? and unidad='kg'", (p,))[0][0]
    assert total_pollo == pytest.approx(pollo["cantidad_sistema"] - 2, abs=0.01)
    assert q(db, "select count(*) from Inventario where producto_id=? and id_lote like 'AJ%'", (otro["producto_id"],))[0][0] == 1
    assert any("cerrado por María García" in x[0] for x in q(db, "select detalle from Cambios"))
    with pytest.raises(DatoInvalido, match="ya está cerrado"):
        cnt.contar(c, [{"producto_id": p, "cantidad": 1}], db)
    with pytest.raises(DatoInvalido, match="no se puede borrar"):
        cnt.anular(c, db)


def test_el_faltante_sale_primero_de_lo_que_vence_antes(db):
    con = sqlite3.connect(db)
    p = pid(db, "Pollo")
    con.execute("delete from Inventario where producto_id=?", (p,))
    con.execute("insert into Inventario (producto_id, fecha_ingreso, cantidad_actual, unidad, id_lote, fecha_caducidad_fija) values (?, '2026-11-20', 3, 'kg', 'PRONTO', '2026-11-28')", (p,))
    con.execute("insert into Inventario (producto_id, fecha_ingreso, cantidad_actual, unidad, id_lote, fecha_caducidad_fija) values (?, '2026-11-20', 3, 'kg', 'TARDE', '2026-12-20')", (p,))
    con.commit()
    con.close()
    c = cnt.crear(db_path=db)["id"]
    cnt.contar(c, [{"producto_id": p, "cantidad": 4}], db)
    cnt.cerrar(c, "Ana", sin_contar_igual=True, db_path=db)
    assert dict(q(db, "select id_lote, cantidad_actual from Inventario where producto_id=?", (p,))) == {"PRONTO": 1.0, "TARDE": 3.0}


def test_si_se_conto_cero_el_lote_se_quita(db):
    p = pid(db, "Pollo")
    c = cnt.crear(db_path=db)["id"]
    cnt.contar(c, [{"producto_id": p, "cantidad": 0}], db)
    cnt.cerrar(c, "Ana", sin_contar_igual=True, db_path=db)
    assert q(db, "select count(*) from Inventario where producto_id=? and unidad='kg'", (p,))[0][0] == 0


def test_cerrar_sin_ajustar_no_toca_el_inventario(db):
    antes = q(db, "select sum(cantidad_actual) from Inventario")[0][0]
    c = cnt.crear(db_path=db)["id"]
    l = cnt.detalle(c, db)["lineas"][0]
    cnt.contar(c, [{"producto_id": l["producto_id"], "cantidad": 0}], db)
    cnt.cerrar(c, "Ana", ajustar_inventario=False, sin_contar_igual=True, db_path=db)
    assert q(db, "select sum(cantidad_actual) from Inventario")[0][0] == pytest.approx(antes)


def test_anular_conteo_abierto(db):
    c = cnt.crear(db_path=db)["id"]
    cnt.anular(c, db)
    assert cnt.detalle(c, db) is None and q(db, "select count(*) from ConteoLineas where conteo_id=?", (c,))[0][0] == 0


# ---------------------------------------------------------------- costo real exacto
def _conteo_cerrado(db, fecha, valor_por_linea):
    """Conteo cerrado con UNA linea de un producto alimento cuyo valor contado es exacto."""
    con = sqlite3.connect(db)
    p = pid(db, "Pollo")
    cid = con.execute("insert into Conteos (fecha, estado, cerrado_por) values (?, 'cerrado', 'Prueba')", (fecha,)).lastrowid
    con.execute("insert into ConteoLineas (conteo_id, producto_id, unidad, cantidad_sistema, cantidad_contada, precio) values (?,?,'kg',?,?,10)",
                (cid, p, valor_por_linea / 10, valor_por_linea / 10))
    con.commit()
    con.close()
    return cid


def test_costo_real_con_conteos_es_inicial_mas_compras_menos_final(db):
    _conteo_cerrado(db, "2026-09-30", 1000)
    _conteo_cerrado(db, "2026-10-31", 1500)
    comprado = q(db, "select round(sum(c.total),2) from Compras c join Catalogo k on k.id=c.producto_id where k.tipo!='limpieza' "
                     "and c.fecha > '2026-09-30' and c.fecha <= '2026-10-31'")[0][0]
    r = com.costo_real("2026-10-01", "2026-10-31", db)
    assert r["metodo"] == "conteo" and r["comprado"] == pytest.approx(comprado)
    assert r["real"] == pytest.approx(1000 + comprado - 1500, abs=0.01)
    assert r["inventario_inicial"]["valor"] == 1000 and r["inventario_final"]["valor"] == 1500
    assert (r["periodo"]["desde"], r["periodo"]["hasta"]) == ("2026-09-30", "2026-10-31")
    assert "Con los conteos del 2026-09-30 y del 2026-10-31" in r["mensajes"][0]
    assert not any("supone" in m for m in r["mensajes"])
    # el desglose sigue cuadrando
    d = r["desglose"]
    assert d["vendido"] + d["sobreproduccion"] + d["merma_registrada"] + d["sin_explicar"] == pytest.approx(r["real"], abs=0.05)


def test_sin_dos_conteos_usa_compras_y_lo_dice(db):
    _conteo_cerrado(db, "2026-09-30", 1000)
    r = com.costo_real("2026-10-01", "2026-10-31", db)
    assert r["metodo"] == "compras" and r["real"] == r["comprado"] and any("conteo de inventario" in m for m in r["mensajes"])


def test_un_conteo_abierto_no_cuenta(db):
    _conteo_cerrado(db, "2026-09-30", 1000)
    cnt.crear("2026-10-31", db_path=db)  # abierto
    assert com.costo_real("2026-10-01", "2026-10-31", db)["metodo"] == "compras"


def test_conteos_de_demostracion(db):
    etapa_b_datos.main(db, pasos=("conteos",))
    lista = cnt.listar(db)
    assert len(lista) >= 2 and all(c["es_demo"] == 1 and c["estado"] == "cerrado" for c in lista)
    assert all(c["fecha"].endswith(("-30", "-31", "-28", "-29")) for c in lista)
    r = com.costo_real(db_path=db)
    assert r["metodo"] == "conteo" and r["real"] > 0
    assert r["inventario_inicial"]["fecha"] < r["inventario_final"]["fecha"]
    n = len(lista)
    etapa_b_datos.main(db, pasos=("conteos",))
    assert len(cnt.listar(db)) == n  # repetible
    # un conteo real abierto no se bloquea por los de demostracion
    assert cnt.crear(db_path=db)["id"]


# ---------------------------------------------------------------- API
def test_api_conteos(db, monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    import server.app as app_mod
    monkeypatch.setattr(app_mod, "DB", db)
    c = TestClient(app_mod.app)
    r = c.post("/api/conteos", json={})
    assert r.status_code == 200
    cid = r.json()["id"]
    assert c.post("/api/conteos", json={}).status_code == 400
    det = c.get(f"/api/conteos/{cid}").json()
    p = det["lineas"][0]["producto_id"]
    assert c.put(f"/api/conteos/{cid}/cantidades", json={"cantidades": [{"producto_id": p, "cantidad": 1.5}]}).json()["guardadas"] == 1
    assert c.put(f"/api/conteos/{cid}/cantidades", json={"cantidades": [{"producto_id": p, "cantidad": -1}]}).status_code == 400
    assert c.post(f"/api/conteos/{cid}/cerrar", json={"cerrado_por": "Ana"}).status_code == 400  # faltan productos
    assert c.post(f"/api/conteos/{cid}/cerrar", json={"cerrado_por": "Ana", "sin_contar_igual": True}).status_code == 200
    assert c.get("/api/conteos").json()["conteos"][0]["estado"] == "cerrado"
    assert c.delete(f"/api/conteos/{cid}").status_code == 400
    assert c.get("/api/conteos/99999").status_code == 404
