"""Compras y costo real + informe del turno (etapa F). Siempre sobre una COPIA de la base."""

import shutil
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from data import compras as com
from data import turnos as tur
from data.proveedores import DatoInvalido

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import etapa_b_datos  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    ruta = tmp_path / "t.db"
    shutil.copy2(RAIZ / "chefchat.db", ruta)
    return str(ruta)


@pytest.fixture()
def db_demo(db):
    """Ventas y compras de demostracion SIN conteos: el costo real se calcula solo con compras."""
    etapa_b_datos.main(db, pasos=("ventas", "compras"))
    con = sqlite3.connect(db)
    con.execute("DELETE FROM ConteoLineas")
    con.execute("DELETE FROM Conteos")
    con.commit()
    con.close()
    return db


def q(db, sql, args=()):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def prov_id(db, nombre):
    return q(db, "select id from Proveedores where nombre=?", (nombre,))[0][0]


HOY = date.today().isoformat()


# ---------------------------------------------------------------- compras
def test_compra_suma_lote_y_actualiza_precio(db):
    a = prov_id(db, "Carnes del Valle")
    r = com.registrar(a, "Pollo", 2000, "g", 9.5, "kg", fecha=HOY, factura="F-001", db_path=db)
    assert r["total"] == pytest.approx(19.0)  # 2000 g = 2 kg x 9,50
    lote = q(db, "select cantidad_actual, unidad from Inventario where id_lote=?", (r["lote"],))
    assert lote == [(2000.0, "g")]
    from data import proveedores as prov
    hoy = next(f for f in prov.precios_de_producto(q(db, "select id from Catalogo where nombre='Pollo'")[0][0], db) if f["proveedor"] == "Carnes del Valle")
    assert hoy["precio"] == 9.5 and hoy["fecha"] == HOY
    assert any("Carnes del Valle: 2000 g de Pollo por $19,00" in c[0] for c in q(db, "select detalle from Cambios"))


def test_compra_de_producto_nuevo_lo_crea(db):
    r = com.registrar(prov_id(db, "Mercado Mayorista Central"), "Maracuyá Prueba", 3, "kg", 1.8, "kg", categoria="Frutas", db_path=db)
    assert r["producto_creado"] is True
    assert q(db, "select categoria, tipo from Catalogo where id=?", (r["producto_id"],)) == [("Frutas", "alimento")]


def test_compra_sin_lote_ni_precio(db):
    a = prov_id(db, "Carnes del Valle")
    antes = q(db, "select count(*) from Inventario")[0][0]
    precios = q(db, "select count(*) from ProveedorProductos")[0][0]
    com.registrar(a, "Pollo", 1, "kg", 1.0, "kg", crear_lote=False, actualizar_precio=False, db_path=db)
    assert q(db, "select count(*) from Inventario")[0][0] == antes
    assert q(db, "select count(*) from ProveedorProductos")[0][0] == precios
    with pytest.raises(DatoInvalido, match="no está en tu lista"):
        com.registrar(a, "Producto Que No Existe", 1, "kg", 1.0, "kg", crear_lote=False, db_path=db)


@pytest.mark.parametrize("args,texto", [
    (("Pollo", 0, "kg", 5, "kg"), "mayor que cero"),
    (("Pollo", 2, "kg", 0, "kg"), "mayor que cero"),
    (("Pollo", 2, "kg", 5, "caja"), "por kg"),
    (("Pollo", 2, "l", 5, "kg"), "No puedo pasar"),
    (("Pollo", "x", "kg", 5, "kg"), "números"),
])
def test_compras_invalidas(db, args, texto):
    with pytest.raises(DatoInvalido, match=texto):
        com.registrar(prov_id(db, "Carnes del Valle"), *args, db_path=db)


def test_compra_no_puede_ser_futura_ni_de_proveedor_quitado(db):
    manana = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(DatoInvalido, match="futura"):
        com.registrar(prov_id(db, "Carnes del Valle"), "Pollo", 1, "kg", 5, "kg", fecha=manana, db_path=db)
    with pytest.raises(DatoInvalido, match="No encuentro ese proveedor"):
        com.registrar(99999, "Pollo", 1, "kg", 5, "kg", db_path=db)


def test_si_la_compra_falla_no_queda_el_lote(db, monkeypatch):
    antes = q(db, "select count(*) from Inventario")[0][0]
    import data.compras as modulo
    original = modulo.registrar_cambio
    monkeypatch.setattr(modulo, "registrar_cambio", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("falla simulada")))
    with pytest.raises(RuntimeError):
        com.registrar(prov_id(db, "Carnes del Valle"), "Pollo", 1, "kg", 5, "kg", db_path=db)
    monkeypatch.setattr(modulo, "registrar_cambio", original)
    assert q(db, "select count(*) from Inventario")[0][0] == antes
    assert q(db, "select count(*) from Compras where es_demo=0")[0][0] == 0


def test_anular_compra_quita_el_lote_si_esta_intacto(db):
    a = prov_id(db, "Carnes del Valle")
    r = com.registrar(a, "Pollo", 4, "kg", 9, "kg", db_path=db)
    out = com.anular(r["id"], db)
    assert out["lote_quitado"] is True and q(db, "select count(*) from Inventario where id_lote=?", (r["lote"],))[0][0] == 0
    r2 = com.registrar(a, "Pollo", 4, "kg", 9, "kg", db_path=db)
    con = sqlite3.connect(db)
    con.execute("update Inventario set cantidad_actual=1 where id_lote=?", (r2["lote"],))
    con.commit()
    con.close()
    out2 = com.anular(r2["id"], db)
    assert out2["lote_quitado"] is False and "ya se usó en parte" in out2["aviso"]
    assert q(db, "select count(*) from Inventario where id_lote=?", (r2["lote"],))[0][0] == 1
    with pytest.raises(DatoInvalido, match="No encuentro esa compra"):
        com.anular(r2["id"], db)


def test_listar_compras_y_totales(db):
    a = prov_id(db, "Carnes del Valle")
    com.registrar(a, "Pollo", 1, "kg", 10, "kg", db_path=db)
    com.registrar(prov_id(db, "Limpieza Total"), "Cloro Granulado", 2, "kg", 3, "kg", db_path=db)
    r = com.listar(HOY, HOY, db_path=db)
    assert r["n"] == 2 and r["total"] == 16 and r["total_alimentos"] == 10 and r["total_limpieza"] == 6
    assert r["por_proveedor"][0] == {"proveedor": "Carnes del Valle", "total": 10.0}
    assert com.listar(HOY, HOY, proveedor_id=a, db_path=db)["n"] == 1
    with pytest.raises(DatoInvalido):
        com.listar("2026-12-01", "2026-01-01", db_path=db)


# ---------------------------------------------------------------- costo real contra teorico
def test_costo_real_sin_compras_lo_dice(db):
    con = sqlite3.connect(db)
    for t in ("Compras", "ConteoLineas", "Conteos"):  # sin compras y sin conteos
        con.execute(f"delete from {t}")
    con.commit()
    con.close()
    r = com.costo_real("2026-09-01", "2026-09-30", db)
    assert r["desglose"] is None and any("no hay compras" in m for m in r["mensajes"])


def test_costo_real_con_datos_demo(db_demo):
    r = com.costo_real(db_path=db_demo)
    assert r["demo"] is True and r["real"] > 0 and r["teorico"] > 0 and r["ingresos"] > r["real"]
    d = r["desglose"]
    # el desglose suma exactamente la diferencia: vendido + sobreproduccion + merma + sin explicar = real
    assert d["vendido"] + d["sobreproduccion"] + d["merma_registrada"] + d["sin_explicar"] == pytest.approx(r["real"], abs=0.05)
    assert d["sobreproduccion"] > 0
    # en la demo se compro entre 6 % y 14 % mas que lo producido
    assert 1.03 < r["real"] / r["teorico_producido"] < 1.17
    assert r["real_pct"] == pytest.approx(r["real"] / r["ingresos"] * 100, abs=0.1)
    assert "Gastaste" in r["mensajes"][0] and "$" in r["mensajes"][0]


def test_costo_real_es_repetible_y_no_toca_compras_reales(db_demo):
    com.registrar(prov_id(db_demo, "Carnes del Valle"), "Pollo", 1, "kg", 10, "kg", db_path=db_demo)
    n = q(db_demo, "select count(*) from Compras")[0][0]
    etapa_b_datos.main(db_demo, pasos=("compras",))
    assert q(db_demo, "select count(*) from Compras")[0][0] == n
    assert q(db_demo, "select count(*) from Compras where es_demo=0")[0][0] == 1


def test_periodo_corto_avisa(db_demo):
    hasta = q(db_demo, "select max(fecha) from Compras")[0][0]
    desde = (date.fromisoformat(hasta) - timedelta(days=6)).isoformat()
    r = com.costo_real(desde, hasta, db_demo)
    assert any("poco precisa" in m for m in r["mensajes"])


def test_analisis_trae_el_costo_real(db_demo):
    from data import analisis as ana
    assert "costo_real" in ana.resumen(db_path=db_demo)


# ---------------------------------------------------------------- informe del turno
def test_personal_del_turno_respeta_descanso_y_ausencias(db):
    # 2026-05-19 es martes: EMP001 (matutino) tiene permiso del 19 al 25; EMP004 descansa los martes
    p = tur.personal_del_turno("2026-05-19", "matutino", db)
    ids = lambda l: {x["id_empleado"] for x in l}  # noqa: E731
    assert "EMP001" in ids(p["ausentes"]) and "EMP004" in ids(p["descansan"])
    assert "EMP003" in ids(p["trabajan"]) and not ids(p["trabajan"]) & (ids(p["ausentes"]) | ids(p["descansan"]))
    assert all(x["cargo"] for x in p["trabajan"])


def test_abrir_informe_nuevo_trae_datos_de_la_base(db_demo):
    fecha = q(db_demo, "select max(fecha) from Ventas where servicio='almuerzo'")[0][0]
    r = tur.abrir(fecha, "matutino", db_demo)
    assert r["estado"] == "nuevo" and r["id"] is None and r["servicios"] == ["desayuno", "almuerzo"]
    assert r["producido"] and {p["servicio"] for p in r["producido"]} <= {"desayuno", "almuerzo"}
    assert r["totales"]["platos_producidos"] == sum(p["producido"] for p in r["producido"])
    assert r["personal"] == [p["id_empleado"] for p in r["datos"]["personal"]["trabajan"]]
    assert r["chefs"] and all("cocin" in c["cargo"].lower() or "paste" in c["cargo"].lower() or "repost" in c["cargo"].lower() for c in r["chefs"])


def test_dia_de_mermas_muestra_las_del_dia(db):
    r = tur.abrir("2026-05-19", "vespertino", db)
    assert r["datos"]["merma_total"] > 0 and "no se anotan por turno" in r["datos"]["nota_merma"]


def test_guardar_y_firmar_informe(db):
    f = "2026-05-19"
    tur.guardar(f, "matutino", "EMP003", ["EMP003", "EMP007"],
                producido=[{"receta_id": "PLF-018", "producido": 40, "vendido": 35}, {"plato": "Pan del día", "producido": 30, "vendido": 30}],
                incidencias=[{"tipo": "equipo", "descripcion": "La freidora 2 no calienta"}], observaciones="Faltó cilantro.", db_path=db)
    r = tur.abrir(f, "matutino", db)
    assert r["estado"] == "borrador" and r["chef_id"] == "EMP003" and r["personal"] == ["EMP003", "EMP007"] and r["producido_editado"]
    assert r["totales"]["platos_producidos"] == 70 and r["totales"]["platos_sobrantes"] == 5
    arroz = next(p for p in r["producido"] if p["receta_id"] == "PLF-018")
    assert arroz["plato"] == "Arroz con Pollo a la Chorrera" and arroz["costo_plato"] == 2.5
    assert r["totales"]["costo_sobrante"] == pytest.approx(5 * 2.5)
    firmado = tur.firmar(f, "matutino", "María García", db)
    assert firmado["estado"] == "firmado"
    assert q(db, "select categoria, descripcion from Bitacora_Diaria where descripcion like '%freidora%'") == [("equipo", "[Turno mañana] La freidora 2 no calienta")]
    # firmado: ya no cambia, aunque cambie la base
    con = sqlite3.connect(db)
    con.execute("insert into Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado) values (?, 'X', 1, 'kg', 'Caduco', 999)", (f,))
    con.commit()
    con.close()
    otra = tur.abrir(f, "matutino", db)
    assert otra["estado"] == "firmado" and otra["datos"]["merma_total"] == r["datos"]["merma_total"] and otra["firmado_por"] == "María García"
    with pytest.raises(DatoInvalido, match="firmado"):
        tur.guardar(f, "matutino", "EMP003", ["EMP003"], db_path=db)
    with pytest.raises(DatoInvalido, match="ya está firmado"):
        tur.firmar(f, "matutino", "Otro", db)
    lista = tur.listar(db_path=db)
    assert lista[0]["estado"] == "firmado" and lista[0]["chef"] == "Maria Garcia" and lista[0]["n_incidencias"] == 1 and lista[0]["totales"]["platos_producidos"] == 70


def test_firmar_exige_datos(db):
    with pytest.raises(DatoInvalido, match="Primero guarda"):
        tur.firmar("2026-05-18", "matutino", "Ana", db)
    tur.guardar("2026-05-18", "matutino", None, ["EMP003"], db_path=db)
    with pytest.raises(DatoInvalido, match="chef"):
        tur.firmar("2026-05-18", "matutino", "Ana", db)
    with pytest.raises(DatoInvalido, match="nombre de quien firma"):
        tur.firmar("2026-05-18", "matutino", " ", db)


@pytest.mark.parametrize("kwargs,texto", [
    ({"turno": "madrugada"}, "turno"),
    ({"fecha": "18/05/2026"}, "fecha"),
    ({"fecha": (date.today() + timedelta(days=2)).isoformat()}, "aún no llega"),
    ({"chef_id": "EMP999"}, "chef"),
    ({"personal": ["EMP003", "NADIE"]}, "NADIE"),
    ({"producido": [{"plato": "A", "producido": 3, "vendido": 5}]}, "más platos"),
    ({"producido": [{"plato": "A", "producido": -1, "vendido": 0}]}, "entre 0"),
    ({"producido": [{"plato": " ", "producido": 1, "vendido": 0}]}, "nombre"),
    ({"incidencias": [{"tipo": "ovni", "descripcion": "x"}]}, "Tipo"),
    ({"incidencias": [{"tipo": "otro", "descripcion": " "}]}, "descripción"),
    ({"observaciones": "x" * 1001}, "1000"),
])
def test_informe_con_datos_malos(db, kwargs, texto):
    base = {"fecha": "2026-05-18", "turno": "matutino", "chef_id": "EMP003", "personal": ["EMP003"]}
    base.update(kwargs)
    with pytest.raises(DatoInvalido, match=texto):
        tur.guardar(db_path=db, **base)


# ---------------------------------------------------------------- API
def test_api_compras_y_turnos(db, monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    import server.app as app_mod
    monkeypatch.setattr(app_mod, "DB", db)
    c = TestClient(app_mod.app)
    a = prov_id(db, "Carnes del Valle")
    r = c.post("/api/compras", json={"proveedor_id": a, "producto": "Pollo", "cantidad": 3, "unidad": "kg", "precio": 9, "unidad_precio": "kg"})
    assert r.status_code == 200 and r.json()["total"] == 27
    assert c.post("/api/compras", json={"proveedor_id": a, "producto": "Pollo", "cantidad": 0, "unidad": "kg", "precio": 9, "unidad_precio": "kg"}).status_code == 400
    lista = c.get(f"/api/compras?desde={HOY}&hasta={HOY}").json()
    assert lista["n"] == 1 and lista["total"] == 27
    assert c.delete(f"/api/compras/{r.json()['id']}").json()["lote_quitado"] is True
    assert c.get("/api/analisis/costo-real").status_code == 200
    assert "costo_real" in c.get("/api/analisis").json()
    inf = c.get("/api/turnos/informe?fecha=2026-05-19&turno=matutino")
    assert inf.status_code == 200 and inf.json()["estado"] == "nuevo"
    assert c.get("/api/turnos/informe?fecha=2026-05-19&turno=raro").status_code == 400
    g = c.put("/api/turnos/informe", json={"fecha": "2026-05-19", "turno": "matutino", "chef_id": "EMP003", "personal": ["EMP003"],
                                           "incidencias": [{"tipo": "higiene", "descripcion": "Faltó jabón"}], "observaciones": "ok"})
    assert g.status_code == 200
    assert c.post("/api/turnos/informe/firmar", json={"fecha": "2026-05-19", "turno": "matutino", "firmado_por": "María"}).status_code == 200
    assert c.post("/api/turnos/informe/firmar", json={"fecha": "2026-05-19", "turno": "matutino", "firmado_por": "María"}).status_code == 400
    assert c.get("/api/turnos").json()["informes"][0]["estado"] == "firmado"
