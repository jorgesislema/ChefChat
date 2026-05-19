import pytest
import os
from core.models import AccionOffice
from agents.mcp_client import MCPClient


class TestMCPClient:
    def test_cliente_se_crea_con_sandbox_path(self) -> None:
        cliente = MCPClient()
        assert "ChefChat_Sandbox" in cliente.sandbox_path

    def test_ejecutar_herramienta_en_sandbox(self) -> None:
        cliente = MCPClient()
        sandbox_file = os.path.join(cliente.sandbox_path, "test.xlsx")
        accion = AccionOffice(
            herramienta="excel",
            operacion="crear",
            ruta_archivo=sandbox_file,
            payload={},
            requiere_hitl=False,
        )
        resultado = cliente.ejecutar_herramienta(accion)
        assert resultado["status"] == "ok"

    def test_validacion_ruta_fuera_sandbox_rechaza(self) -> None:
        """Verifica que una ruta fuera del sandbox sea rechazada."""
        cliente = MCPClient()
        accion = AccionOffice(
            herramienta="excel",
            operacion="crear",
            ruta_archivo=r"C:\Users\public\test.xlsx",
            payload={},
            requiere_hitl=False,
        )
        with pytest.raises(PermissionError):
            cliente.ejecutar_herramienta(accion)

    def test_ejecutar_herramienta_excel_leer_sin_hitl(self) -> None:
        cliente = MCPClient()
        accion = AccionOffice(
            herramienta="excel",
            operacion="leer",
            ruta_archivo=os.path.join(cliente.sandbox_path, "test.xlsx"),
            payload={},
            requiere_hitl=False,
        )
        resultado = cliente.ejecutar_herramienta(accion)
        assert resultado["status"] == "ok"

    def test_ejecutar_herramienta_word_crear_en_sandbox(self) -> None:
        cliente = MCPClient()
        sandbox_file = os.path.join(
            cliente.sandbox_path, "test_menu.txt"
        )
        accion = AccionOffice(
            herramienta="word",
            operacion="crear",
            ruta_archivo=sandbox_file,
            payload={"contenido": "Menu de prueba"},
            requiere_hitl=True,
        )
        resultado = cliente.ejecutar_herramienta(accion)
        assert resultado["status"] == "ok"
        assert os.path.exists(sandbox_file)

    def test_escritura_fuera_sandbox_lanza_excepcion(self) -> None:
        cliente = MCPClient()
        accion = AccionOffice(
            herramienta="excel",
            operacion="crear",
            ruta_archivo=r"C:\Temp\OtherFolder\test.xlsx",
            payload={},
            requiere_hitl=True,
        )
        with pytest.raises(PermissionError):
            cliente.ejecutar_herramienta(accion)