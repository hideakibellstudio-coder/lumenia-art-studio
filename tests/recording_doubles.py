"""Dublês compartilhados pelos testes do plugin de gravação.

Separados de `test_recording_plugin.py` em 2026-09-25, quando o arquivo chegou
a 434 linhas (parede dos 450) e foi dividido em motor (`test_recording_engine.py`)
e painel/plugin (`test_recording_plugin.py`).
"""

from PySide6 import QtCore, QtWidgets

from ui.plugins.panels.recording_plugin.engine.recording_engine import TimelapseRecordingEngine
from ui.plugins.panels.recording_plugin.engine.frame_source import Frame
from ui.core.plugins.workspace_contract import WorkspaceService


class DummyBackend:
    def __init__(self, w=100, h=100):
        self.w = w
        self.h = h

    def get_display_pixel_buffer(self) -> bytes:
        # Gera buffer RGBA (100x100x4 = 40000 bytes)
        return b"\xff\x00\x00\xff" * (self.w * self.h)


class DummyCanvas(QtWidgets.QWidget):
    """Canvas de teste. O contrato (`WorkspaceService.canvas`) é um QWidget: o
    plugin liga o fim do traço ao motor e ancora a barra flutuante no canvas.
    Até 2026-09-25 isto era um QObject; a barra chamava `isVisible()` nele
    dentro de um slot do Qt e o erro só aparecia com o pytest-qt instalado."""
    strokeFinished = QtCore.Signal()


def red_frames(include_guides: bool):
    """Fonte de quadros de teste: 100×100 vermelho, sem guias."""
    return Frame(b"\xff\x00\x00\xff" * (100 * 100), 100, 100, None)


def make_engine():
    return TimelapseRecordingEngine(red_frames)


class MockWorkspaceService(WorkspaceService):
    def __init__(self, canvas):
        self._canvas = canvas
        self.panels = {}

    def add_panel(self, panel_id, title, widget, area="right", icon_path=None):
        self.panels[panel_id] = {"title": title, "widget": widget, "area": area, "icon": icon_path}

    def remove_panel(self, panel_id):
        self.panels.pop(panel_id, None)

    def show_status(self, message, timeout_ms=3000):
        self.last_status = message

    @property
    def canvas(self):
        return self._canvas

    @property
    def workspace_container(self):
        return None
