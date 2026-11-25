"""Pruebas de menu y costos (etapa D). Siempre sobre una COPIA de la base y con fecha fija."""

import shutil
from datetime import date
from pathlib import Path

import pytest

from data import menu as m
from data import recetas as rec

RAIZ = Path(__file__).resolve().parent.parent
HOY = date(2026, 11, 24)


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("menu") / "t.db"
    shutil.copy2(RAIZ / "chefchat.db", ruta)
    return str(ruta)


# ---------------------------------------------------------------- costo por plato (archivo del dueno)
def test_el_costo_por_plato_es_el_del_archivo(db):
    f = rec.ficha("PLF-018", db)  # Arroz con Pollo: el archivo dice 2,50 por plato y el menu lo vende a 8,50
    assert f["fuente_costo"] == "archivo" and f["costo_plato"] == pytest.approx(2.5)
    assert f["margen_pct"] == pytest.approx((8.5 - 2.5) / 8.5 * 100, abs=0.1)


def test_todas_las_recetas_tienen_costo_por_plato(db):
    assert all(r["costo_plato"] for r in rec.listar(db_path=db))


# ---------------------------------------------------------------- alergenos
@pytest.mark.parametrize("texto,esperado", [("lácteos", "lacteos"), ("Sin gluten", "gluten"), ("huevos", "huevo"),
                                            ("frutos secos", "frutos secos"), ("maní", "mani"), ("mariscos", "mariscos")])
def test_alergeno_canonico(texto, esperado):
    assert m.alergeno_canonico(texto.replace("Sin ", "")) == esperado


def test_alergeno_desconocido_da_error_claro(db):
    with pytest.raises(m.MenuError, match="No conozco el alérgeno"):
        m.armar_menu(excluir=["pelos de unicornio"], hoy=HOY, db_path=db)


def test_se_detecta_alergeno_aunque_la_receta_diga_ninguno():
    assert "lacteos" in m._alergenos_de("Ninguno", ["leche entera", "azucar"])
    assert "gluten" in m._alergenos_de("", ["harina de trigo"])
    assert "gluten" not in m._alergenos_de("", ["harina de maiz"])


# ---------------------------------------------------------------- costo por persona
def test_costo_por_persona_ordenado(db):
    r = m.costo_por_persona(db)["por_comida"]
    for comida, d in r.items():
        assert d is not None, comida
        assert 0 < d["minimo"] <= d["tipico"] <= d["maximo"]


def test_eventos_especiales_no_entran_al_menu(db):
    assert all(r["cat"] != "eventos especiales" for r in m.cargar_recetas(db))


# ---------------------------------------------------------------- armar menu
def test_menu_respeta_el_tope(db):
    r = m.armar_menu(tope_dia=12.0, hoy=HOY, db_path=db)
    assert r["cumple_tope"] is True
    d = r["dias"][0]
    assert d["costo_persona"] <= 12.0 + 1e-9
    assert d["costo_persona"] == pytest.approx(sum(c["costo_persona"] for c in d["comidas"]), abs=0.01)
    for c in d["comidas"]:
        assert c["costo_persona"] == pytest.approx(sum(p["costo_plato"] for p in c["platos"]), abs=0.01)


def test_tope_imposible_se_dice_claro(db):
    r = m.armar_menu(tope_dia=0.5, hoy=HOY, db_path=db)
    assert r["cumple_tope"] is False
    assert any(c["nota"] and "supera el tope" in c["nota"] for c in r["dias"][0]["comidas"])


@pytest.mark.parametrize("alergeno", ["gluten", "lacteos", "huevo"])
def test_menu_sin_alergeno(db, alergeno):
    r = m.armar_menu(servicios=["desayuno", "almuerzo", "merienda"], excluir=[alergeno], dias=3, hoy=HOY, db_path=db)
    for d in r["dias"]:
        for c in d["comidas"]:
            for p in c["platos"]:
                assert alergeno not in p["alergenos"], p
    assert r["aviso"]


def test_semana_sin_platos_repetidos(db):
    r = m.armar_menu(dias=7, hoy=HOY, db_path=db)
    ids = [p["id_receta"] for d in r["dias"] for c in d["comidas"] for p in c["platos"]]
    assert len(ids) == len(set(ids))
    assert len(r["dias"]) == 7


def test_mismo_resultado_con_la_misma_semilla(db):
    a = m.armar_menu(tope_dia=14, hoy=HOY, semilla=3, db_path=db)
    b = m.armar_menu(tope_dia=14, hoy=HOY, semilla=3, db_path=db)
    assert a == b


def test_pide_comida_inexistente_o_dias_malos(db):
    with pytest.raises(m.MenuError):
        m.armar_menu(servicios=["brunch"], hoy=HOY, db_path=db)
    with pytest.raises(m.MenuError):
        m.armar_menu(dias=9, hoy=HOY, db_path=db)
    with pytest.raises(m.MenuError):
        m.armar_menu(tope_dia=-1, hoy=HOY, db_path=db)


# ---------------------------------------------------------------- que cocinar con lo que vence
def test_que_cocinar_usa_solo_lo_que_vence(db):
    r = m.que_cocinar(dias=3, hoy=HOY, db_path=db)
    pv = {p["producto"] for p in r["por_vencer"]}
    assert pv, "con los datos de demostracion algo vence en 3 dias"
    for rc in r["recetas"]:
        assert rc["usa"], rc
        assert {u["producto"] for u in rc["usa"]} <= pv
        assert rc["porciones_posibles"] == min(u["alcanza_para"] for u in rc["usa"]) >= 1
        assert all(u["dias"] <= 3 for u in rc["usa"])


def test_que_cocinar_no_incluye_limpieza(db):
    r = m.que_cocinar(dias=60, hoy=HOY, db_path=db)
    assert not any("Cloro" in p["producto"] or "Jabon" in p["producto"] for p in r["por_vencer"])


def test_que_cocinar_sin_alergeno(db):
    r = m.que_cocinar(dias=14, hoy=HOY, excluir=["lacteos"], limite=50, db_path=db)
    assert all("lacteos" not in rc["alergenos"] for rc in r["recetas"])


def test_menu_prefiere_lo_que_vence(db):
    con = m.armar_menu(dias=1, hoy=HOY, dias_vencer=30, db_path=db)
    sin = m.armar_menu(dias=1, hoy=HOY, preferir_por_vencer=False, db_path=db)
    n = lambda r: sum(len(p["usa_por_vencer"]) for c in r["dias"][0]["comidas"] for p in c["platos"])
    assert n(con) >= n(sin)


# ---------------------------------------------------------------- sobrantes
def test_sobrante_fuera_de_plazo_no_se_reutiliza(db):
    r = m.aprovechar_sobrantes(hoy=HOY, db_path=db)["sobrantes"]
    assert r and all(s["vigente"] is False and s["recetas"] == [] and "plazo" in s["mensaje"] for s in r)


def test_sobrante_dentro_de_plazo_da_ideas(db):
    r = m.aprovechar_sobrantes(hoy=date(2026, 5, 18), db_path=db)["sobrantes"]
    arroz = next(s for s in r if "Arroz" in s["producto"])
    assert arroz["vigente"] is True and arroz["recetas"]
