"""Balance del turno (kilos y unidades). Siempre sobre una COPIA de la base. Ver docs/PLAN_BALANCE_TURNO.md."""

import shutil
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from data import balance as bal
from data import turnos as tur
from data.esquema import asegurar_esquema
from data.proveedores import DatoInvalido

RAIZ = Path(__file__).resolve().parent.parent
F, T = "2026-11-20", "nocturno"  # el turno de noche no tiene ventas: todo lo producido lo pone la prueba


def q(db, sql, args=()):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


@pytest.fixture()
def db(tmp_path):
    ruta = str(tmp_path / "t.db")
    shutil.copy2(RAIZ / "chefchat.db", ruta)
    asegurar_esquema(ruta)
    c = sqlite3.connect(ruta)
    for t in ("MovimientosTurno", "SalidasTurno", "EstandaresReceta"):
        c.execute(f"delete from {t}")
    c.execute("delete from InformesTurno")
    harina = c.execute("select id from Catalogo where nombre='Harina'").fetchone()[0]
    c.execute("insert into RecetasRAG (id_receta, nombre, categoria, costo, ingredientes_json, alergenos, instrucciones) "
              "values ('PAN-T', 'Pan de Prueba', 'panaderia', 0.2, '61.5|gramos|harina', 'Gluten', 'Amasar y hornear.')")
    c.execute("insert into RecetaIngredientes (receta_id, producto_id, ingrediente, cantidad, unidad) values ('PAN-T', ?, 'harina', 61.5, 'gramos')", (harina,))
    c.commit()
    c.close()
    return ruta


def panaderia(db, perdida=2.5, tolerancia=2.0, devuelto=5.0, panes=9350):
    """El ejemplo del plan: 600 kg entregados, 5 devueltos, 9 350 panes de 60 g, merma 10 kg, comida del personal 2 kg."""
    bal.guardar_estandar("PAN-T", 60, perdida, tolerancia, db_path=db)
    bal.anotar_movimiento(F, T, "entrega", "Harina", 600, "kg", "Bodega", "Chef", descontar_inventario=False, db_path=db)
    if devuelto:
        bal.anotar_movimiento(F, T, "devolucion", "Harina", devuelto, "kg", descontar_inventario=False, db_path=db)
    bal.anotar_merma(F, T, "Harina", 10, "kg", "Se pegó a la mesa", db_path=db)
    bal.anotar_salida(F, T, "comida_personal", 2, "Desayuno del equipo", db_path=db)
    tur.guardar(F, T, None, [], producido=[{"receta_id": "PAN-T", "producido": panes, "vendido": 9000, "recibido": panes - 50}], db_path=db)
    return tur.abrir(F, T, db)["datos"]["balance"]


# ---------------------------------------------------------------- el ejemplo del plan
def test_ejemplo_de_la_panaderia(db):
    b = panaderia(db)
    k = b["kg"]
    assert k["entregado"] == 600 and k["devuelto"] == 5 and k["entro"] == 595
    assert k["salio_bueno"] == pytest.approx(561)  # 9350 x 60 g
    assert k["perdida_normal"] == pytest.approx(561 / 0.975 - 561, abs=0.001)  # 14,38
    assert k["merma"] == 10 and k["comida_personal"] == 2 and k["anotado"] == 12
    assert k["sin_explicar"] == pytest.approx(595 - 561 - 14.3846 - 12, abs=0.002)  # +7,62: FALTA (entró más de lo que se explica)
    assert b["sin_explicar_pct"] == pytest.approx(1.28, abs=0.01)
    assert b["estado"] == "bien" and b["tolerancia_pct"] == 2.0  # 1,28 % < 1,5 % (75 % de la tolerancia)
    assert "faltan 7,6 kg" in b["mensajes"][0] and "1,3 %" in b["mensajes"][0]
    # el dinero sale del precio por kg de la harina; positivo = dinero perdido
    assert b["sin_explicar_dinero"] == pytest.approx(b["kg"]["sin_explicar"] * b["costo_kg"], abs=0.01) and b["sin_explicar_dinero"] > 0


def test_por_ingrediente_a_mano(db):
    b = panaderia(db)
    h = next(l for l in b["por_ingrediente"] if l["producto"] == "Harina")
    assert h["neto"] == 595 and h["uso_receta"] == pytest.approx(9350 * 0.0615) and h["merma"] == 10
    assert h["diferencia"] == pytest.approx(595 - 575.025 - 10, abs=0.001)  # faltan 9,98 kg de harina
    assert h["valor_diferencia"] > 0


def test_por_unidades_producido_contra_recibido(db):
    b = panaderia(db)
    p = b["por_plato"][0]
    assert (p["producido"], p["recibido"], p["vendido"], p["perdidas_unidades"]) == (9350, 9300, 9000, 50)
    assert b["unidades"] == {"producido": 9350, "vendido": 9000, "recibido": 9300, "perdidas": 50}


def test_alarma_fuera_de_tolerancia(db):
    b = panaderia(db, tolerancia=1.0)
    assert b["estado"] == "alarma" and any("ALARMA" in m for m in b["mensajes"])
    assert any("Harina" in m for m in b["mensajes"])  # dice donde esta la fuga


def test_cerca_de_la_tolerancia(db):
    assert panaderia(db, tolerancia=1.6)["estado"] == "cerca"  # 1,28 % > 75 % de 1,6 % (1,2 %)


def test_sobra_cuando_se_explica_mas_de_lo_que_entro(db):
    b = panaderia(db, perdida=0.0, devuelto=0, panes=10000)  # 600 - 600 - 12 = -12: sobra
    assert b["kg"]["sin_explicar"] == pytest.approx(-12) and b["sin_explicar_pct"] < 0
    assert "sobran 12,0 kg" in b["mensajes"][0]
    assert not any("ingrediente con más faltante" in m for m in b["mensajes"])


def test_alarma_por_sobra_pide_revisar_la_receta(db):
    b = panaderia(db, perdida=0.0, devuelto=0, panes=10000, tolerancia=1.0)
    assert b["estado"] == "alarma" and any("receta pide más" in m for m in b["mensajes"])


def test_sin_peso_por_unidad_usa_la_receta(db):
    bal.guardar_estandar("PAN-T", None, 2.5, 2.0, db_path=db)
    bal.anotar_movimiento(F, T, "entrega", "Harina", 600, "kg", descontar_inventario=False, db_path=db)
    tur.guardar(F, T, None, [], producido=[{"receta_id": "PAN-T", "producido": 9600, "vendido": 9600}], db_path=db)
    b = tur.abrir(F, T, db)["datos"]["balance"]
    assert b["kg"]["salio_bueno"] == pytest.approx(9600 * 0.0615 * 0.975, abs=0.01)
    assert b["por_plato"][0]["origen_peso"] == "peso de la receta"


def test_estandar_por_defecto_se_avisa(db):
    bal.anotar_movimiento(F, T, "entrega", "Harina", 100, "kg", descontar_inventario=False, db_path=db)
    tur.guardar(F, T, None, [], producido=[{"receta_id": "PAN-T", "producido": 1000, "vendido": 1000}], db_path=db)
    b = tur.abrir(F, T, db)["datos"]["balance"]
    assert b["por_plato"][0]["estandar_por_defecto"] is True and b["por_plato"][0]["perdida_normal_pct"] == 3.0
    assert any("estándar por defecto" in a for a in b["avisos"])


def test_sin_entregas_no_hay_balance(db):
    tur.guardar(F, T, None, [], producido=[{"receta_id": "PAN-T", "producido": 10, "vendido": 10}], db_path=db)
    b = tur.abrir(F, T, db)["datos"]["balance"]
    assert b["estado"] == "sin_entregas" and "Bodega no ha anotado entregas" in b["mensajes"][0]


# ---------------------------------------------------------------- conversiones
def test_a_kg():
    assert bal.a_kg(500, "gramos", None) == pytest.approx(0.5)
    assert bal.a_kg(2, "libras", None) == pytest.approx(0.90718474)
    assert bal.a_kg(1, "qq", None) == pytest.approx(45.359237)
    assert bal.a_kg(2, "litros", None) == pytest.approx(2.0)  # 1 kg por litro por defecto
    assert bal.a_kg(2, "litros", 0.92) == pytest.approx(1.84)  # aceite
    assert bal.a_kg(12, "unidades", 0.05) == pytest.approx(0.6)  # 12 huevos de 50 g
    assert bal.a_kg(12, "unidades", None) is None  # sin peso: no se inventa
    assert bal.a_kg(1, "pizca", None) is None


def test_unidades_sin_peso_se_avisan_y_con_peso_suman(db):
    bal.poner_kg_por_unidad("Huevo", None, db_path=db)  # la base de demostracion ya trae el peso del huevo
    bal.anotar_movimiento(F, T, "entrega", "Huevo", 30, "unidad", descontar_inventario=False, db_path=db)
    b = bal.calcular(F, T, [], db)
    assert b["kg"]["entro"] == 0 and any("Huevo" in a for a in b["avisos"])
    bal.poner_kg_por_unidad("Huevo", 0.06, db_path=db)
    assert bal.calcular(F, T, [], db)["kg"]["entro"] == pytest.approx(1.8)


# ---------------------------------------------------------------- inventario
def test_entrega_descuenta_y_devolucion_suma_inventario(db):
    p = q(db, "select id from Catalogo where nombre='Pollo'")[0][0]
    total = lambda: q(db, "select coalesce(sum(cantidad_actual),0) from Inventario where producto_id=? and unidad='kg'", (p,))[0][0]  # noqa: E731
    antes = total()
    r = bal.anotar_movimiento(F, T, "entrega", "Pollo", 2000, "g", db_path=db)
    assert r["aviso"] is None and total() == pytest.approx(antes - 2, abs=0.001)
    bal.anotar_movimiento(F, T, "devolucion", "Pollo", 0.5, "kg", db_path=db)
    assert total() == pytest.approx(antes - 1.5, abs=0.001)
    assert q(db, "select count(*) from Inventario where producto_id=? and id_lote like 'DEV%'", (p,))[0][0] == 1


def test_entrega_sin_stock_suficiente_avisa(db):
    r = bal.anotar_movimiento(F, T, "entrega", "Pollo", 100000, "kg", db_path=db)
    assert r["aviso"] and "no había suficiente" in r["aviso"]


def test_quitar_movimiento_deshace_el_inventario(db):
    p = q(db, "select id from Catalogo where nombre='Pollo'")[0][0]
    antes = q(db, "select coalesce(sum(cantidad_actual),0) from Inventario where producto_id=? and unidad='kg'", (p,))[0][0]
    r = bal.anotar_movimiento(F, T, "entrega", "Pollo", 3, "kg", db_path=db)
    bal.quitar_movimiento(r["id"], db)
    despues = q(db, "select coalesce(sum(cantidad_actual),0) from Inventario where producto_id=? and unidad='kg'", (p,))[0][0]
    assert despues == pytest.approx(antes, abs=0.001) and q(db, "select count(*) from MovimientosTurno")[0][0] == 0


# ---------------------------------------------------------------- mermas con turno
def test_merma_con_turno_entra_y_sin_turno_queda_aparte(db):
    bal.anotar_movimiento(F, T, "entrega", "Harina", 100, "kg", descontar_inventario=False, db_path=db)
    con = sqlite3.connect(db)
    con.execute("insert into Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado) values (?, 'Harina', 5, 'kg', 'Caduco', 6)", (F,))
    con.commit()
    con.close()
    b = bal.calcular(F, T, [], db)
    assert b["kg"]["merma"] == 0 and any("sin turno" in a for a in b["avisos"])
    r = bal.anotar_merma(F, T, "Harina", 4, "kg", "se cayó", db_path=db)
    assert r["costo"] and r["costo"] > 0  # costo calculado con el precio
    assert bal.calcular(F, T, [], db)["kg"]["merma"] == 4
    assert q(db, "select turno from Mermas where id=?", (r["id"],)) == [(T,)]


# ---------------------------------------------------------------- firma y reglas
def test_firmar_guarda_el_balance_y_bloquea_anotar(db):
    panaderia(db)
    tur.guardar(F, T, "EMP003", ["EMP008"], producido=[{"receta_id": "PAN-T", "producido": 9350, "vendido": 9000, "recibido": 9300}], db_path=db)
    tur.firmar(F, T, "Jefe de turno", db)
    foto = tur.abrir(F, T, db)["datos"]["balance"]
    assert foto["kg"]["entro"] == 595
    with pytest.raises(DatoInvalido, match="firmado"):
        bal.anotar_movimiento(F, T, "entrega", "Harina", 1, "kg", descontar_inventario=False, db_path=db)
    with pytest.raises(DatoInvalido, match="firmado"):
        bal.anotar_salida(F, T, "otro", 1, db_path=db)
    with pytest.raises(DatoInvalido, match="firmado"):
        bal.anotar_merma(F, T, "Harina", 1, "kg", "x", db_path=db)
    mov = q(db, "select id from MovimientosTurno limit 1")[0][0]
    with pytest.raises(DatoInvalido, match="firmado"):
        bal.quitar_movimiento(mov, db)
    # aunque cambie la base, el balance firmado no cambia
    con = sqlite3.connect(db)
    con.execute("update MovimientosTurno set cantidad=9999")
    con.commit()
    con.close()
    assert tur.abrir(F, T, db)["datos"]["balance"]["kg"]["entro"] == 595


@pytest.mark.parametrize("fn,args,texto", [
    (bal.anotar_movimiento, (F, T, "regalo", "Harina", 1, "kg"), "tipo"),
    (bal.anotar_movimiento, (F, T, "entrega", "Harina", 0, "kg"), "mayor que cero"),
    (bal.anotar_movimiento, (F, T, "entrega", "Harina", 1, "cajas"), "unidad"),
    (bal.anotar_movimiento, (F, T, "entrega", "No Existe", 1, "kg"), "no está en tu lista"),
    (bal.anotar_movimiento, (F, "madrugada", "entrega", "Harina", 1, "kg"), "turno"),
    (bal.anotar_movimiento, ((date.today() + timedelta(days=1)).isoformat(), T, "entrega", "Harina", 1, "kg"), "aún no llega"),
    (bal.anotar_salida, (F, T, "fiesta", 1), "Tipo"),
    (bal.anotar_salida, (F, T, "comida_personal", -1), "mayores que cero"),
    (bal.anotar_merma, (F, T, "Harina", 1, "kg", " "), "motivo"),
])
def test_datos_malos(db, fn, args, texto):
    with pytest.raises(DatoInvalido, match=texto):
        fn(*args, db_path=db)


@pytest.mark.parametrize("args,texto", [((-1, 3, 2), "peso"), ((60, 70, 2), "pérdida"), ((60, 3, 0), "tolerancia"), ((60, 3, 40), "tolerancia")])
def test_estandar_invalido(db, args, texto):
    with pytest.raises(DatoInvalido, match=texto):
        bal.guardar_estandar("PAN-T", *args, db_path=db)
    with pytest.raises(DatoInvalido, match="receta"):
        bal.guardar_estandar("NO-EXISTE", 60, 3, 2, db_path=db)


def test_recibido_mayor_que_producido(db):
    with pytest.raises(DatoInvalido, match="recibido"):
        tur.guardar(F, T, None, [], producido=[{"receta_id": "PAN-T", "producido": 10, "vendido": 5, "recibido": 11}], db_path=db)


# ---------------------------------------------------------------- tendencia
def test_tendencia_por_turno(db):
    panaderia(db, tolerancia=1.0)  # alarma
    t = bal.tendencia(db_path=db)
    assert t["turnos"][0]["estado"] == "alarma" and t["por_turno"][0]["turno"] == T
    assert "1 de 1 turnos pasaron su tolerancia" in t["mensajes"][0]
    assert any("turno de la noche es el que más pierde" in m for m in t["mensajes"])
    assert any(m.startswith("En total faltan unos $") for m in t["mensajes"])


# ---------------------------------------------------------------- API
def test_api_balance(db, monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    import server.app as app_mod
    monkeypatch.setattr(app_mod, "DB", db)
    c = TestClient(app_mod.app)
    assert c.put("/api/recetas/PAN-T/estandar", json={"peso_unidad_g": 60, "perdida_normal_pct": 2.5, "tolerancia_pct": 2}).status_code == 200
    assert c.get("/api/recetas/PAN-T/estandar").json()["peso_unidad_g"] == 60
    assert c.put("/api/recetas/PAN-T/estandar", json={"perdida_normal_pct": 90}).status_code == 400
    m = c.post("/api/balance/movimientos", json={"fecha": F, "turno": T, "tipo": "entrega", "producto": "Harina", "cantidad": 600, "unidad": "kg",
                                                "descontar_inventario": False})
    assert m.status_code == 200
    assert c.post("/api/balance/salidas", json={"fecha": F, "turno": T, "tipo": "comida_personal", "kg": 2}).status_code == 200
    assert c.post("/api/balance/mermas", json={"fecha": F, "turno": T, "producto": "Harina", "cantidad": 10, "unidad": "kg", "motivo": "x"}).status_code == 200
    assert c.put("/api/turnos/informe", json={"fecha": F, "turno": T, "personal": [], "incidencias": [], "observaciones": "",
                                             "producido": [{"receta_id": "PAN-T", "producido": 9600, "vendido": 9000, "recibido": 9550}]}).status_code == 200
    b = c.get(f"/api/balance?fecha={F}&turno={T}").json()
    assert b["kg"]["entro"] == 600 and b["unidades"]["perdidas"] == 50
    assert c.get(f"/api/balance?fecha={F}&turno=raro").status_code == 400
    assert c.get("/api/balance/tendencia").json()["turnos"]
    huevo = q(db, "select id from Catalogo where nombre='Huevo'")[0][0]
    assert c.put(f"/api/inventario/productos/{huevo}/peso", json={"kg_por_unidad": 0.06}).status_code == 200
    assert c.put(f"/api/inventario/productos/{huevo}/peso", json={"kg_por_unidad": -1}).status_code == 400
    assert c.delete(f"/api/balance/movimientos/{m.json()['id']}").status_code == 200
    assert c.delete("/api/balance/movimientos/99999").status_code == 400


def test_redondeo_igual_que_la_pantalla():
    assert bal._n(1.65) == "1,7" and bal._n(1.649) == "1,6" and bal._n(-0.05) == "-0,1" and bal._n(12.0) == "12,0"
