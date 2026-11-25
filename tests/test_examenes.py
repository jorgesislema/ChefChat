"""Pruebas del modulo de examenes (sin IA, con base temporal y datos ficticios)."""

import sqlite3

import pytest

from examenes import servicio as s


@pytest.fixture()
def db(tmp_path):
    ruta = str(tmp_path / "t.db")
    c = sqlite3.connect(ruta)
    c.execute("CREATE TABLE Trabajadores (id_empleado TEXT, nombre_completo TEXT)")
    c.executemany("INSERT INTO Trabajadores VALUES (?,?)", [("E1", "Ana Prueba"), ("E2", "Luis Prueba")])
    c.commit()
    c.close()
    for i in range(5):
        s.guardar_pregunta("Manual X", f"Pregunta {i}", [f"a{i}", f"b{i}", f"c{i}", f"d{i}"], i % 4,
                           "porque si", "Manual X", "Sección 1", 0.9, "aprobada", ruta)
    return ruta


def _responder_todo(db, intento, acertar):
    corr = {p["id"]: p for p in s.listar_preguntas(db_path=db)}
    for p in intento["preguntas"]:
        ok = corr[p["id"]]["correcta"]
        s.responder(intento["intento_id"], p["id"], ok if acertar else (ok + 1) % 4, db)


def test_no_repite_pregunta(db):
    assert s.guardar_pregunta("Manual X", "pregunta 0", ["z1", "z2", "z3", "z4"], 0, db_path=db) is None


def test_pregunta_necesita_4_opciones_distintas(db):
    with pytest.raises(s.ExamenError):
        s.guardar_pregunta("M", "q", ["a", "A", "c", "d"], 0, db_path=db)


def test_publico_no_filtra_la_respuesta(db):
    it = s.iniciar_intento("E1", "Manual X", "evaluacion", 5, db)
    assert "correcta" not in str(it["preguntas"][0]) and "explicacion" not in str(it["preguntas"][0])


@pytest.mark.parametrize("acertar,nota,aprobado", [(True, 100.0, True), (False, 0.0, False)])
def test_nota_exacta(db, acertar, nota, aprobado):
    it = s.iniciar_intento("E1", "Manual X", "evaluacion", 5, db)
    _responder_todo(db, it, acertar)
    r = s.cerrar_intento(it["intento_id"], db)
    assert (r["nota"], r["aprobado"]) == (nota, aprobado)
    assert len(r["falladas"]) == (0 if acertar else 5)


def test_nota_parcial_y_sin_responder_cuenta_mal(db):
    it = s.iniciar_intento("E1", "Manual X", "evaluacion", 5, db)
    corr = {p["id"]: p for p in s.listar_preguntas(db_path=db)}
    for p in it["preguntas"][:4]:
        s.responder(it["intento_id"], p["id"], corr[p["id"]]["correcta"], db)
    r = s.cerrar_intento(it["intento_id"], db)
    assert r["nota"] == 80.0 and r["aprobado"] is True and len(r["falladas"]) == 1


def test_limite_de_intentos(db):
    for _ in range(s.INTENTOS_EVALUACION):
        it = s.iniciar_intento("E1", "Manual X", "evaluacion", 5, db)
        s.cerrar_intento(it["intento_id"], db)
    with pytest.raises(s.ExamenError, match="intentos"):
        s.iniciar_intento("E1", "Manual X", "evaluacion", 5, db)
    s.iniciar_intento("E2", "Manual X", "evaluacion", 5, db)  # otra persona sí puede


def test_practica_da_feedback_y_no_cuenta_en_reporte(db):
    it = s.iniciar_intento("E1", "Manual X", "practica", 5, db)
    p = it["preguntas"][0]
    r = s.responder(it["intento_id"], p["id"], 0, db)
    assert "explicacion" in r and "Manual X" in r["fuente"]
    s.cerrar_intento(it["intento_id"], db)
    assert s.reporte(db)["por_persona"] == []


def test_evaluacion_no_da_feedback(db):
    it = s.iniciar_intento("E1", "Manual X", "evaluacion", 5, db)
    assert s.responder(it["intento_id"], it["preguntas"][0]["id"], 0, db) == {"guardada": True}


def test_tema_sin_preguntas_aprobadas(db):
    with pytest.raises(s.ExamenError, match="aprobadas"):
        s.iniciar_intento("E1", "Otro tema", "practica", 5, db)


def test_no_se_responde_dos_veces_tras_cerrar(db):
    it = s.iniciar_intento("E1", "Manual X", "practica", 5, db)
    s.cerrar_intento(it["intento_id"], db)
    with pytest.raises(s.ExamenError):
        s.responder(it["intento_id"], it["preguntas"][0]["id"], 0, db)
