import sys
# pylint: disable=no-name-in-module
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main() -> int:
    app = QGuiApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        raise RuntimeError("No available screen")
    geometry = screen.availableGeometry()
    window = MainWindow()
    window.resize(int(geometry.width() * 0.85), int(geometry.height() * 0.85))
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())