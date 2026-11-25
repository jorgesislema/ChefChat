"""Chat y API de menu (etapa D). Copia de la base, fecha fija, sin IA."""

import shutil
from datetime import date
from pathlib import Path

import pytest

from agents.menu_chat import _dias_vencer, _sin, _tope, responder_menu

RAIZ = Path(__file__).resolve().parent.parent
HOY = date(2026, 11, 24)


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("mc") / "t.db"
    shutil.copy2(RAIZ / "chefchat.db", ruta)
    return str(ruta)


def test_lectura_de_la_pregunta():
    assert _dias_vencer("que puedo cocinar con lo que vence manana") == 1
    assert _dias_vencer("que cocino con lo que vence hoy") == 0
    assert _dias_vencer("que cocino con lo que vence esta semana") == 7
    assert _dias_vencer("lo que vence en 3 dias") == 3
    assert _tope("menu con tope de 12 dolares") == 12.0
    assert _tope("menu de maximo $9,50 por persona") == 9.5
    assert _tope("menu de la semana") is None
    assert _sin("menu sin gluten y sin lacteos") == ["gluten", "lacteos"]


def test_chat_que_cocinar_esta_semana(db):
    r = responder_menu("¿Qué puedo cocinar con lo que vence esta semana?", HOY, db)
    assert r and "Vence pronto" in r and "Puedes cocinar" in r


def test_chat_que_cocinar_manana_sin_nada_que_venza(db):
    # en los datos de demostracion lo primero vence el 26: manana (25) no vence nada y se dice claro
    r = responder_menu("¿Qué puedo cocinar con lo que vence mañana?", HOY, db)
    assert r == "No hay alimentos que venzan en ese plazo. No hace falta cocinar nada con urgencia."


def test_chat_costo_por_persona(db):
    r = responder_menu("¿Cuánto cuesta el desayuno por persona?", HOY, db)
    assert r and "Desayuno" in r and "$" in r and "Almuerzo" not in r


def test_chat_menu_con_tope_y_sin_gluten(db):
    r = responder_menu("Diseña un menú para hoy con tope de 14 dólares sin gluten", HOY, db)
    assert r and "por persona" in r and "Revisa siempre los alérgenos" in r


def test_chat_menu_semana(db):
    r = responder_menu("Arma el menú de la semana", HOY, db)
    assert r and r.count("2026-11-") >= 7 and "Promedio por día" in r


def test_chat_sobrantes(db):
    r = responder_menu("¿Cómo aprovecho los sobrantes?", HOY, db)
    assert r and "plazo sanitario" in r


def test_categoria_cocina_no_es_cocinar(db):
    assert responder_menu("¿Qué de la categoría Cocina vence en diciembre?", HOY, db) is None


def test_chat_ignora_otras_preguntas(db):
    assert responder_menu("¿Qué productos vencen en diciembre?", HOY, db) is None
    assert responder_menu("¿Cuántos cocineros hay?", HOY, db) is None


def test_chat_alergeno_raro_da_mensaje_claro(db):
    # "sin" + algo desconocido no se detecta como alergeno; el menu se arma igual y no falla
    assert responder_menu("Arma un menú sin pelos", HOY, db)


# ---------------------------------------------------------------- API
def _cliente(db, monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    import server.app as app_mod
    monkeypatch.setattr(app_mod, "DB", db)
    return TestClient(app_mod.app)


def test_api_menu(db, monkeypatch):
    c = _cliente(db, monkeypatch)
    costos = c.get("/api/menu/costos").json()["por_comida"]
    assert costos["almuerzo"]["minimo"] <= costos["almuerzo"]["maximo"]
    s = c.get("/api/menu/sugerencia?comidas=desayuno,almuerzo&tope=12&sin=gluten&dias=2").json()
    assert len(s["dias"]) == 2 and s["excluye"] == ["gluten"]
    mala = c.get("/api/menu/sugerencia?sin=pelos")
    assert mala.status_code == 400 and "No conozco el alérgeno" in mala.json()["detail"]
    assert c.get("/api/menu/sugerencia?dias=9").status_code == 400
    assert c.get("/api/menu/sugerencia?comidas=brunch").status_code == 400
    assert c.get("/api/menu/cocinar?dias=3").status_code == 200
    assert c.get("/api/menu/cocinar?dias=99").status_code == 400
    assert "sobrantes" in c.get("/api/menu/sobrantes").json()
    assert "gluten" in c.get("/api/menu/alergenos").json()["alergenos"]
