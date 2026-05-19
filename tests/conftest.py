import pytest
import tempfile
import os
from typing import Generator
from unittest.mock import MagicMock
# pylint: disable=no-name-in-module, redefined-outer-name
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication
from core.models import Receta, Evento, AccionOffice, Ingrediente
from data.db_manager import DatabaseManager


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication | QCoreApplication, None, None]:
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def tmp_db_path() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def db_manager(tmp_db_path: str) -> Generator[DatabaseManager, None, None]:
    """Create a DatabaseManager instance with a temporary database."""
    yield DatabaseManager(db_path=tmp_db_path)


# No changes needed - temp_db is a valid fixture parameter name


@pytest.fixture
def sample_receta() -> Receta:
    return Receta(
        id_receta="rec001",
        nombre="Pato a la Naranja",
        ingredientes=[
            Ingrediente(nombre="Pato", cantidad=1.0, unidad="unidad"),
            Ingrediente(nombre="Naranja", cantidad=200.0, unidad="g"),
        ],
        alergenos=["gluten", "citricos"],
        costo_estimado=45.50,
    )


@pytest.fixture
def sample_evento() -> Evento:
    return Evento(
        id_evento="evt001",
        tipo_evento="corporativo",
        fecha="2025-06-15",
        presupuesto=5000.0,
        estado_aprobacion="pendiente",
    )


@pytest.fixture
def sample_accion_office() -> AccionOffice:
    return AccionOffice(
        herramienta="excel",
        operacion="escribir",
        ruta_archivo=r"C:\Temp\ChefChat_Sandbox\test.xlsx",
        payload={"datos": [["Item", "Cantidad", "Costo"], ["Pato", "1", "45.50"]]},
        requiere_hitl=True,
    )


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    mock = MagicMock()
    mock.generar_respuesta.return_value = "Respuesta de prueba del LLM"
    mock.clasificar_intencion.return_value = "rag"
    return mock