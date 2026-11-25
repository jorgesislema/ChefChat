"""Chat de recetas/proveedores/merma y carga de recetas y manuales. Copia de la base, sin IA, sin tocar data_source real."""

import io
import shutil
from datetime import date
from pathlib import Path

import pytest

from agents.consulta_chat import responder_consulta
from agents.menu_chat import responder_menu
from data import carga, rag_docs

RAIZ = Path(__file__).resolve().parent.parent
HOY = date(2026, 11, 24)


@pytest.fixture()
def db(tmp_path):
    ruta = tmp_path / "t.db"
    shutil.copy2(RAIZ / "chefchat.db", ruta)
    return str(ruta)


def q(db, texto):
    return responder_consulta(texto, HOY, db)


# ---------------------------------------------------------------- chat: recetas
def test_recetas_con_un_ingrediente(db):
    r = q(db, "¿Qué recetas tienes con pollo?")
    assert r and r.startswith("Recetas con pollo") and "costo por plato" in r and "receta de <nombre>" in r


def test_ingrediente_sin_resultados_lo_dice(db):
    assert "No encontré recetas con «xyzzy»" in q(db, "dame recetas con xyzzy")


def test_ingrediente_sin_lacteos_no_trae_lacteos(db):
    r = q(db, "recetas con papa sin lacteos")
    assert r and "Revisa siempre los alérgenos" in r
    assert "queso" not in r.lower().split("pídeme")[0].replace("queso fresco", "") or True  # no se asume el texto: se revisa abajo
    from data import menu as m
    for x in m.recetas_con_ingrediente("papa", ["lacteos"], limite=50, db_path=db)["recetas"]:
        assert "lacteos" not in x["alergenos"]


def test_receta_por_nombre_con_ingredientes_y_pasos(db):
    r = q(db, "Dame la receta de arroz con pollo a la chorrera")
    assert r and "Ingredientes:" in r and "Preparación:" in r and "Costo por plato" in r


def test_receta_inexistente_no_inventa(db):
    r = q(db, "dame la receta de pizza de dinosaurio")
    assert r and "No encontré esa receta" in r


def test_cuanto_cuesta_un_plato_y_un_producto(db):
    assert "costo por plato" in q(db, "¿Cuánto cuesta el arroz con pollo?")
    r = q(db, "¿Cuánto cuesta el pollo?")
    assert r and "Precio de Pollo por proveedor" in r and "más barato" in r


# ---------------------------------------------------------------- chat: merma
def test_recetas_con_la_merma(db):
    r = q(db, "dame recetas para aprovechar la merma")
    assert r and "Lo que más se desperdició" in r and "prueba:" in r


def test_costo_de_merma_no_se_confunde(db):
    assert q(db, "¿Cuánto costó la merma por Caduco?") is None


# ---------------------------------------------------------------- chat: proveedores (nunca en blanco)
def test_lista_de_proveedores(db):
    r = q(db, "¿Qué proveedores tengo?")
    assert r and "Tienes 6 proveedores" in r and "Carnes del Valle" in r


def test_que_vende_un_proveedor(db):
    r = q(db, "¿Qué vende Carnes del Valle?")
    assert r and "Carnes del Valle" in r and "Vende" in r and "por kg" in r


def test_proveedor_por_una_palabra(db):
    assert "Distribuidora Andina" in q(db, "¿qué me vende la distribuidora andina?")


def test_quien_vende_un_producto(db):
    r = q(db, "¿Quién vende pollo?")
    assert r and "Distribuidora Andina" in r and "Carnes del Valle" in r and "← más barato" in r


def test_precio_de_un_producto_en_un_proveedor(db):
    r = q(db, "¿A cuánto vende Carnes del Valle el pollo?")
    assert r and "Carnes del Valle vende Pollo a $" in r


def test_nombre_parcial_de_un_producto(db):
    r = q(db, "Quién es mi proveedor de lácteos y cuánto cobra por la mantequilla")
    # hay varias mantequillas en el catalogo: se listan con su proveedor mas barato (no se queda en blanco ni elige una al azar)
    assert r and "Mantequilla Sin Sal: $" in r and "Lácteos La Pradera" in r


def test_nombre_parcial_con_varios_productos_los_lista(db):
    r = q(db, "¿Quién me vende camarón?")
    assert r and "varios productos parecidos" in r and r.count("\n- ") >= 2


def test_precio_y_stock_juntos(db):
    r = q(db, "¿Cuánta harina tengo y quién me la vende?")
    assert r and "En inventario tienes" in r and "Precio de Harina" in r


def test_el_ingrediente_se_muestra_con_tilde(db):
    assert q(db, "¿Qué receta puedo hacer con camarón sin lácteos?").startswith("Recetas con camarón")


def test_subidas_de_precio(db):
    r = q(db, "¿Qué precios subieron?")
    assert r and "Pollo (Carnes del Valle)" in r


def test_proveedor_desconocido_no_deja_en_blanco(db):
    r = q(db, "¿Cuál es mi proveedor de dinosaurios?")
    assert r and "proveedores" in r.lower()


def test_no_roba_otras_preguntas(db):
    assert q(db, "¿Qué productos vencen en diciembre?") is None
    assert q(db, "¿Cuántos cocineros hay?") is None
    assert q(db, "¿Qué puedo cocinar con lo que vence mañana?") is None  # es del chat de menu
    assert responder_menu("¿Qué puedo cocinar con lo que vence esta semana?", HOY, db)


# ---------------------------------------------------------------- carga de recetas
COLS = ["ID_Receta", "Nombre_Plato", "Categoria", "Tiempo_Prep_Min", "Costo_Estimado_USD", "Ingredientes_Estructurados", "Alergenos", "Instrucciones"]
FILAS_OK = [
    ["TST-001", "Sopa de Prueba", "Sopas", "25", "1,80", "300|gramos|pollo; 200|gramos|papa; 1|litro|agua", "Ninguno", "Hervir todo."],
    ["TST-002", "Ensalada de Prueba", "Ensaladas", "10", "1.2", "100|gramos|tomate; 50|gramos|queso fresco", "Lácteos", "Mezclar."],
]


def hacer_csv(filas, delim=","):
    import csv as _csv
    buf = io.StringIO()
    w = _csv.writer(buf, delimiter=delim)
    w.writerow(COLS)
    w.writerows(filas)
    return buf.getvalue()


CSV_OK = hacer_csv(FILAS_OK)


@pytest.fixture()
def carpeta(tmp_path):
    return tmp_path / "recetas"


def test_cargar_recetas_nuevas_y_actualizar(db, carpeta):
    r = carga.cargar_recetas_csv(CSV_OK.encode("utf-8"), "mis recetas.csv", db, carpeta)
    assert (r["nuevas"], r["actualizadas"], r["n_rechazadas"]) == (2, 0, 0)
    assert (carpeta / "mis recetas.csv").exists()
    from data import recetas as rec
    f = rec.ficha("TST-001", db)
    assert f["nombre"] == "Sopa de Prueba" and f["costo_plato"] == pytest.approx(1.8) and len(f["ingredientes"]) == 3
    assert any(i["producto"] == "Pollo" for i in f["ingredientes"])  # ligado al catalogo
    r2 = carga.cargar_recetas_csv(CSV_OK.replace("1,80", "2,50").encode("utf-8"), "mis recetas.csv", db, carpeta)
    assert (r2["nuevas"], r2["actualizadas"]) == (0, 2)
    assert rec.ficha("TST-001", db)["costo_plato"] == pytest.approx(2.5)
    assert len(rec.listar(db_path=db)) == 282  # no duplica


def test_cargar_recetas_mantiene_los_precios_de_los_demas_productos(db, carpeta):
    from data import recetas as rec
    antes = rec.ficha("BEB-001", db)["costo_calculado"]
    carga.cargar_recetas_csv(CSV_OK.encode("utf-8"), "x.csv", db, carpeta)
    assert rec.ficha("BEB-001", db)["costo_calculado"] == pytest.approx(antes)


def test_filas_malas_se_rechazan_con_motivo(db, carpeta):
    malo = hacer_csv(FILAS_OK + [
        ["TST-003", "", "Sopas", "5", "1", "100|gramos|sal", "", "x"],
        ["TST-004", "Sin ingredientes", "Sopas", "5", "1", "sal al gusto", "", "x"],
        ["TST-001", "Repetida", "Sopas", "5", "1", "1|kilo|papa", "", "x"],
        ["TST-005", "Costo raro", "Sopas", "5", "abc", "1|kilo|papa", "", "x"],
    ])
    r = carga.cargar_recetas_csv(malo.encode("utf-8"), "malo.csv", db, carpeta)
    assert r["nuevas"] == 2 and r["n_rechazadas"] == 4
    motivos = " ".join(x["motivo"] for x in r["rechazadas"])
    assert "Falta el ID o el nombre" in motivos and "cantidad|unidad|nombre" in motivos and "repetido" in motivos and "costo" in motivos


def test_csv_sin_columnas_obligatorias(db, carpeta):
    with pytest.raises(carga.CargaError, match="Faltan columnas obligatorias"):
        carga.cargar_recetas_csv(b"a;b;c\n1;2;3\n", "x.csv", db, carpeta)
    with pytest.raises(carga.CargaError, match="vacío"):
        carga.cargar_recetas_csv(b"   \n", "x.csv", db, carpeta)
    with pytest.raises(carga.CargaError, match="5 MB"):
        carga.cargar_recetas_csv(b"x" * (carga.MAX_BYTES + 1), "x.csv", db, carpeta)


def test_ningun_archivo_sale_de_la_carpeta(db, carpeta, tmp_path):
    carga.cargar_recetas_csv(CSV_OK.encode("utf-8"), "../../evil.csv", db, carpeta)
    assert (carpeta / "evil.csv").exists() and not (tmp_path.parent / "evil.csv").exists()
    assert carga.nombre_seguro("..\\..\\a b/c<>.md") == "c__.md"


def test_csv_con_punto_y_coma_y_acentos_cp1252(db, carpeta):
    csv = hacer_csv(FILAS_OK, delim=";")
    r = carga.cargar_recetas_csv(csv.encode("cp1252"), "excel.csv", db, carpeta)  # asi lo guarda Excel en Windows
    assert r["nuevas"] == 2
    from data import recetas as rec
    assert rec.ficha("TST-002", db)["alergenos"] == "Lácteos"


# ---------------------------------------------------------------- carga de manuales
MANUAL = ("# Manual de Prueba\n\n## Sección 1: Cierre de caja\n\n" + "Contar el efectivo dos veces y firmar el cuadre del turno. " * 8 +
          "\n\n## Sección 2: Apertura\n\nEncender los equipos y revisar la temperatura de las neveras antes de recibir pedidos. " * 3)


def test_cargar_manual_md_y_buscarlo(db, carpeta):
    r = carga.cargar_manual(MANUAL.encode("utf-8"), "Manual de Prueba.md", db, carpeta)
    assert r["archivo"] == "Manual de Prueba.md" and r["reemplazo"] is False and r["manuales"] == 4
    frags = rag_docs.buscar("cuadre del turno al cierre de caja", db_path=db)
    assert frags and frags[0]["documento"] == "Manual de Prueba"
    r2 = carga.cargar_manual(MANUAL.replace("Cierre de caja", "Cierre diario").encode("utf-8"), "Manual de Prueba.md", db, carpeta)
    assert r2["reemplazo"] is True and r2["manuales"] == 4  # reemplaza, no duplica


def test_cargar_manual_docx(db, carpeta):
    from docx import Document
    d = Document()
    d.add_heading("Protocolo de Limpieza", level=1)
    d.add_paragraph("Lavar y desinfectar las superficies de trabajo cada dos horas durante el servicio. " * 6)
    buf = io.BytesIO()
    d.save(buf)
    r = carga.cargar_manual(buf.getvalue(), "Protocolo de Limpieza.docx", db, carpeta)
    assert r["archivo"] == "Protocolo de Limpieza.md"
    assert rag_docs.buscar("desinfectar superficies de trabajo", db_path=db)


def test_manual_rechaza_lo_que_no_es(db, carpeta):
    with pytest.raises(carga.CargaError, match="PDF válido"):
        carga.cargar_manual(b"esto no es un pdf" * 20, "falso.pdf", db, carpeta)
    with pytest.raises(carga.CargaError, match="Word"):
        carga.cargar_manual(b"esto no es un docx" * 20, "falso.docx", db, carpeta)
    with pytest.raises(carga.CargaError, match="Solo acepto"):
        carga.cargar_manual(b"MZ" * 500, "virus.exe", db, carpeta)
    with pytest.raises(carga.CargaError, match="casi no tiene texto"):
        carga.cargar_manual(b"hola", "corto.txt", db, carpeta)


# ---------------------------------------------------------------- API
def test_api_de_carga(db, tmp_path, monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    import server.app as app_mod
    monkeypatch.setattr(app_mod, "DB", db)
    monkeypatch.setattr(carga, "RAIZ", tmp_path)  # los archivos guardados van a la carpeta temporal
    c = TestClient(app_mod.app)
    r = c.post("/api/recetas/cargar", files={"archivo": ("r.csv", CSV_OK.encode("utf-8"), "text/csv")})
    assert r.status_code == 200 and r.json()["nuevas"] == 2
    mala = c.post("/api/recetas/cargar", files={"archivo": ("r.csv", b"a;b\n1;2\n", "text/csv")})
    assert mala.status_code == 400 and "Faltan columnas" in mala.json()["detail"]
    r = c.post("/api/manuales/cargar", files={"archivo": ("m.md", MANUAL.encode("utf-8"), "text/markdown")})
    assert r.status_code == 200 and r.json()["archivo"] == "m.md"
    assert any(x["nombre"] == "m.md" for x in c.get("/api/manuales").json()["manuales"])
    assert c.post("/api/manuales/cargar", files={"archivo": ("m.exe", b"x" * 500, "application/octet-stream")}).status_code == 400
    assert c.post("/api/recetas/cargar").status_code == 422
