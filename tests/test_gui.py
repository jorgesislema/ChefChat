import pytest
from typing import Generator
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QTextEdit
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qapp: QApplication) -> MainWindow:
    window = MainWindow()
    yield window
    window.close()


@pytest.fixture
def window_with_mocked_api(qapp: QApplication) -> Generator[MagicMock, None, None]:
    with patch("gui.main_window.ConfigManager") as mock_config:
        mock_config.get_openrouter_key.return_value = "test_key_12345678901234567890"
        mock_config.get_sandbox_path.return_value = r"C:\Temp\ChefChat_Sandbox"
        window = MainWindow()
        yield mock_config
        window.close()


class TestGUISendButton:
    def test_send_button_clears_input_field(
        self, main_window: MainWindow, qtbot
    ) -> None:
        test_message = "Hola, esto es un mensaje de prueba"
        main_window.input_field.setPlainText(test_message)
        assert main_window.input_field.toPlainText() == test_message
        qtbot.mouseClick(main_window.btn_send, Qt.MouseButton.LeftButton)
        assert main_window.input_field.toPlainText() == ""

    def test_send_button_does_nothing_when_empty(
        self, main_window: MainWindow, qtbot
    ) -> None:
        main_window.input_field.setPlainText("")
        initial_chat_html = main_window.chat_area.toHtml()
        qtbot.mouseClick(main_window.btn_send, Qt.MouseButton.LeftButton)
        assert main_window.chat_area.toHtml() == initial_chat_html

    def test_chat_area_updates_on_send(
        self, main_window: MainWindow, qtbot
    ) -> None:
        with patch("gui.main_window.ConfigManager") as mock_config:
            mock_config.get_openrouter_key.return_value = "test_key_12345678901234567890"
            test_message = "Mensaje de prueba"
            main_window.input_field.setPlainText(test_message)
            qtbot.mouseClick(main_window.btn_send, Qt.MouseButton.LeftButton)
            assert "Usuario" in main_window.chat_area.toHtml() or test_message in main_window.chat_area.toPlainText()


class TestGUIHITLBar:
    def test_hitl_bar_is_hidden_by_default(self, main_window: MainWindow) -> None:
        assert main_window.hitl_bar.isVisible() is False

    def test_hitl_bar_shows_on_approval_required(
        self, main_window: MainWindow
    ) -> None:
        from core.models import AccionOffice
        mock_accion = AccionOffice(
            herramienta="excel",
            operacion="escribir",
            ruta_archivo=r"C:\Temp\ChefChat_Sandbox\test.xlsx",
            payload={"datos": []},
            requiere_hitl=True
        )
        main_window._on_requires_approval(mock_accion)
        assert main_window.hitl_bar.isVisible() is True

    def test_approve_button_is_green(self, main_window: MainWindow) -> None:
        approve_style = main_window.btn_approve.styleSheet()
        assert "22c55e" in approve_style or "green" in approve_style.lower()

    def test_reject_button_is_red(self, main_window: MainWindow) -> None:
        reject_style = main_window.btn_reject.styleSheet()
        assert "ef4444" in reject_style or "red" in reject_style.lower()


class TestGUIRAGIngest:
    def test_rag_button_exists(self, main_window: MainWindow) -> None:
        assert hasattr(main_window, "btn_rag")
        assert main_window.btn_rag is not None

    def test_rag_button_triggers_file_dialog(self, main_window: MainWindow, qtbot) -> None:
        with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileNames") as mock_dialog:
            mock_dialog.return_value = (["test.pdf"], "PDF Files (*.pdf)")
            qtbot.mouseClick(main_window.btn_rag, Qt.MouseButton.LeftButton)
            mock_dialog.assert_called_once()


class TestGUITheme:
    def test_dark_mode_applied(self, main_window: MainWindow) -> None:
        stylesheet = main_window.styleSheet()
        assert "#0f172a" in stylesheet
        assert "#1e293b" in stylesheet

    def test_send_button_has_accent_color(self, main_window: MainWindow) -> None:
        send_style = main_window.btn_send.styleSheet()
        assert "#deff9a" in send_style


class TestAPIKeyDialog:
    def test_dialog_has_key_field(self, main_window: MainWindow) -> None:
        from gui.main_window import APIKeyDialog
        dialog = APIKeyDialog(main_window)
        assert hasattr(dialog, "key_field")

    def test_dialog_save_requires_key(self, main_window: MainWindow, qtbot) -> None:
        from gui.main_window import APIKeyDialog
        dialog = APIKeyDialog(main_window)
        dialog.key_field.setText("")
        with patch("gui.main_window.ConfigManager") as mock_config:
            with patch("PyQt6.QtWidgets.QMessageBox.warning") as mock_warn:
                dialog._save_key()
                mock_warn.assert_called()