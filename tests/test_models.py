import pytest
from pydantic import ValidationError
from core.models import Receta, Evento, AccionOffice, Ingrediente


class TestIngrediente:
    def test_crear_ingrediente_valido(self) -> None:
        ing = Ingrediente(nombre="Pato", cantidad=1.0, unidad="unidad")
        assert ing.nombre == "pato"
        assert ing.cantidad == 1.0
        assert ing.unidad == "unidad"

    def test_unidad_invalida_rechaza(self) -> None:
        with pytest.raises(ValidationError):
            Ingrediente(nombre="Sal", cantidad=5.0, unidad="onzas")

    def test_to_dict(self) -> None:
        ing = Ingrediente(nombre="Pato", cantidad=1.0, unidad="unidad")
        d = ing.to_dict()
        assert d["nombre"] == "pato"


class TestReceta:
    def test_crear_receta_valida(self, sample_receta: Receta) -> None:
        assert sample_receta.nombre == "Pato a la Naranja"
        assert len(sample_receta.ingredientes) == 2
        assert "gluten" in sample_receta.alergenos

    def test_alergenos_son_trimmed(self) -> None:
        receta = Receta(
            id_receta="r001",
            nombre="Test",
            ingredientes=[Ingrediente(nombre="X", cantidad=1.0, unidad="unidad")],
            alergenos=["  gluten  ", " lactosa "],
            costo_estimado=10.0,
        )
        assert receta.alergenos == ["gluten", "lactosa"]

    def test_costo_negativo_rechaza(self) -> None:
        with pytest.raises(ValidationError):
            Receta(
                id_receta="r001",
                nombre="Test",
                ingredientes=[],
                costo_estimado=-5.0,
            )


class TestEvento:
    def test_crear_evento_valido(self, sample_evento: Evento) -> None:
        assert sample_evento.tipo_evento == "corporativo"
        assert sample_evento.presupuesto == 5000.0

    def test_estado_invalido_rechaza(self) -> None:
        with pytest.raises(ValidationError):
            Evento(
                id_evento="e001",
                tipo_evento="boda",
                fecha="2025-06-15",
                presupuesto=10000.0,
                estado_aprobacion="invalid_state",
            )

    def test_fecha_formato_incorrecto_rechaza(self) -> None:
        with pytest.raises(ValidationError):
            Evento(
                id_evento="e001",
                tipo_evento="boda",
                fecha="15-06-2025",
                presupuesto=10000.0,
            )


class TestAccionOffice:
    def test_herramienta_word_valida(self) -> None:
        accion = AccionOffice(
            herramienta="WORD",
            operacion="crear",
            ruta_archivo="C:\\Temp\\test.docx",
            payload={},
        )
        assert accion.herramienta == "word"

    def test_herramienta_invalida_rechaza(self) -> None:
        with pytest.raises(ValidationError):
            AccionOffice(
                herramienta="powerpoint",
                operacion="crear",
                ruta_archivo="test.pptx",
                payload={},
            )

    def test_operacion_invalida_rechaza(self) -> None:
        with pytest.raises(ValidationError):
            AccionOffice(
                herramienta="excel",
                operacion="modificar",
                ruta_archivo="test.xlsx",
                payload={},
            )

    def test_to_dict(self) -> None:
        accion = AccionOffice(
            herramienta="excel",
            operacion="leer",
            ruta_archivo="test.xlsx",
            payload={"hoja": "Hoja1"},
        )
        d = accion.to_dict()
        assert d["herramienta"] == "excel"
        assert d["operacion"] == "leer"