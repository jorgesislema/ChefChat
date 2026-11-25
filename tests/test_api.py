"""Pruebas de la API local (lecturas; no llama a la IA)."""

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from server.app import app  # noqa: E402

c = TestClient(app)


def test_salud():
    assert c.get("/api/salud").json() == {"ok": True}


def test_resumen_tiene_datos_reales():
    r = c.get("/api/resumen").json()
    assert {"vencen_7_dias", "vencen_diciembre", "ya_vencidos", "mermas_por_motivo", "personal"} <= set(r)


def test_inventario_y_trabajadores():
    assert c.get("/api/inventario").json()["productos"]
    assert c.get("/api/trabajadores").json()["trabajadores"]


def test_examen_con_tema_inexistente_da_mensaje_claro():
    t = c.get("/api/trabajadores").json()["trabajadores"][0]["id_empleado"]
    r = c.post("/api/examenes/iniciar", json={"id_empleado": t, "tema": "No existe", "modo": "practica"})
    assert r.status_code == 400 and "aprobadas" in r.json()["detail"]


def test_chat_no_vacio():
    assert c.post("/api/chat", json={"mensaje": ""}).status_code == 422
