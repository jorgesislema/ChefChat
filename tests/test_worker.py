import pytest
import threading
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QCoreApplication
from gui.worker import Worker


class TestWorkerHITL:
    def test_worker_se_crea_correctamente(
        self, mock_orchestrator: MagicMock, qapp: QCoreApplication
    ) -> None:
        worker = Worker(mock_orchestrator)
        assert worker.pause_condition is not None
        assert isinstance(worker.pause_condition, threading.Event)
        assert worker.accion_pendiente is None
        assert worker.running is True

    def test_worker_stop_sets_running_false(
        self, mock_orchestrator: MagicMock, qapp: QCoreApplication
    ) -> None:
        worker = Worker(mock_orchestrator)
        worker.start()
        assert worker.isRunning()
        worker.stop()
        assert worker.running is False

    def test_aprobar_accion_sets_event(
        self, mock_orchestrator: MagicMock, qapp: QCoreApplication
    ) -> None:
        worker = Worker(mock_orchestrator)
        worker.pause_condition.set()
        assert worker.pause_condition.is_set() is True
        worker.pause_condition.clear()
        assert worker.pause_condition.is_set() is False
        worker.aprobar_accion()
        assert worker.pause_condition.is_set() is True

    def test_rechazar_accion_sets_event_and_emits(
        self, mock_orchestrator: MagicMock, qapp: QCoreApplication
    ) -> None:
        worker = Worker(mock_orchestrator)
        result_message = []

        def capture(msg: str) -> None:
            result_message.append(msg)

        worker.accion_completada.connect(capture)
        worker.pause_condition.clear()
        worker.rechazar_accion()
        assert worker.pause_condition.is_set() is True
        assert len(result_message) > 0
        assert "rechazada" in result_message[0].lower()

    def test_worker_is_waiting_flag(
        self, mock_orchestrator: MagicMock, qapp: QCoreApplication
    ) -> None:
        worker = Worker(mock_orchestrator)
        assert worker.is_waiting_for_approval() is False
        worker._is_waiting = True
        worker.pause_condition.clear()
        assert worker.is_waiting_for_approval() is True