"""Pruebas del RAG de documentos: debe encontrar la seccion correcta (sin IA)."""

import pytest

from data import rag_docs

CASOS = [
    ("¿Cómo debo lavarme las manos?", "Buenas Prácticas"),
    ("Un cliente dice que es alérgico al maní, ¿qué hago?", "Alérgenos"),
    ("¿Qué hago ante contaminación cruzada?", "Alérgenos"),
    ("¿Cuál es la zona de peligro de temperatura?", "Buenas Prácticas"),
    ("¿Cómo saludo a un cliente que llega a la mesa?", "Atención al Cliente"),
    ("¿Cómo manejo una queja de un cliente?", "Atención al Cliente"),
]


@pytest.mark.parametrize("pregunta,doc", CASOS)
def test_busca_documento_correcto(pregunta, doc):
    frags = rag_docs.buscar(pregunta, k=3)
    assert frags, "no encontro nada"
    assert any(doc in f["documento"] for f in frags), [(f["documento"], f["seccion"]) for f in frags]


def test_tema_inexistente_no_inventa():
    assert rag_docs.buscar("cambiar una llanta", k=3) == []

