"""
Testes de Unidade e Contrato para o Plugin de Gravação & Timelapse (ARCcC).
===========================================================================
Valida o ciclo de vida do motor de gravação, captura assíncrona, exportação ZIP,
comportamento do painel de UI e registro no WorkspaceService.
"""

import os
import zipfile
import pytest
from PySide6 import QtCore, QtWidgets, QtGui

from plugins.ui.recording_plugin.engine.recording_engine import TimelapseRecordingEngine
from plugins.ui.recording_plugin.engine.export_worker import TimelapseExportWorker
from plugins.ui.recording_plugin.panel import RecordingPanel
from plugins.ui.recording_plugin import RecordingPlugin
from ui.core.plugins.workspace_contract import WorkspaceService


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class DummyBackend:
    def __init__(self, w=100, h=100):
        self.w = w
        self.h = h

    def get_display_pixel_buffer(self) -> bytes:
        # Gera buffer RGBA (100x100x4 = 40000 bytes)
        return b"\xff\x00\x00\xff" * (self.w * self.h)


class DummyCanvas(QtCore.QObject):
    strokeFinished = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.canvas_w = 100
        self.canvas_h = 100
        self.backend = DummyBackend(100, 100)
        self.engine_backend = self.backend


class MockWorkspaceService(WorkspaceService):
    def __init__(self, canvas):
        self._canvas = canvas
        self.panels = {}

    def add_panel(self, panel_id, title, widget, area="right", icon_path=None):
        self.panels[panel_id] = {"title": title, "widget": widget, "area": area, "icon": icon_path}

    def remove_panel(self, panel_id):
        self.panels.pop(panel_id, None)

    @property
    def canvas(self):
        return self._canvas

    @property
    def workspace_container(self):
        return None


def test_recording_engine_lifecycle(qapp):
    """Valida ciclo completo de sessão do motor de gravação (start, pause, resume, discard)."""
    canvas = DummyCanvas()
    engine = TimelapseRecordingEngine()
    engine.attach_canvas(canvas)

    assert not engine.is_recording
    assert not engine.is_paused

    # Inicia gravação
    ok = engine.start_recording()
    assert ok is True
    assert engine.is_recording is True
    assert engine.is_paused is False
    assert engine.frame_count == 1
    assert engine.temp_dir is not None
    assert os.path.isdir(engine.temp_dir)

    # Pausa
    engine.pause_recording()
    assert engine.is_paused is True

    # Retoma
    engine.resume_recording()
    assert engine.is_paused is False

    # Dispara strokeFinished
    canvas.strokeFinished.emit()
    engine.stroke_debounce_timer.timeout.emit()
    assert engine.frame_count == 2

    # Aguarda pool de threads processar tarefas de escrita de arquivo
    QtCore.QThreadPool.globalInstance().waitForDone(2000)

    # Verifica se os frames foram criados em disco
    files = os.listdir(engine.temp_dir)
    assert "frame_000001.jpg" in files

    # Descarta e verifica limpeza
    temp_dir = engine.temp_dir
    engine.discard_recording()
    assert engine.is_recording is False
    assert engine.temp_dir is None
    assert not os.path.exists(temp_dir)


def test_export_worker_zip(qapp, tmp_path):
    """Valida o empacotamento ZIP como exportação ou fallback."""
    # Cria pasta temporária com 3 frames falsos
    frames_dir = tmp_path / "fake_frames"
    frames_dir.mkdir()
    for i in range(1, 4):
        f = frames_dir / f"frame_{i:06d}.jpg"
        f.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # Header JPEG mínimo

    out_zip = str(tmp_path / "timelapse_output.zip")
    worker = TimelapseExportWorker(str(frames_dir), 3)

    results = []
    worker.finished.connect(lambda s, m, p: results.append((s, m, p)))

    worker.export(out_zip, format_type="zip")

    assert len(results) == 1
    success, msg, path = results[0]
    assert success is True
    assert os.path.exists(out_zip)

    # Inspeciona o conteúdo do ZIP
    with zipfile.ZipFile(out_zip, "r") as zf:
        names = zf.namelist()
        assert len(names) == 3
        assert "frame_000001.jpg" in names


def test_timelapse_watermark_applied(qapp):
    """Valida renderização e integridade da marca d'água oficial do Lumenia."""
    img = QtGui.QImage(400, 300, QtGui.QImage.Format.Format_RGBA8888)
    img.fill(QtCore.Qt.GlobalColor.white)

    # Aplica marca d'água
    TimelapseRecordingEngine.apply_watermark(img)

    # O canto inferior direito não deve ser mais branco puro (marca d'água foi pintada)
    pixel = img.pixelColor(350, 270)
    assert not (pixel.red() == 255 and pixel.green() == 255 and pixel.blue() == 255)


def test_recording_panel_ui(qapp):
    """Valida que o RecordingPanel instancia todos os controles e responde a comandos."""
    canvas = DummyCanvas()
    panel = RecordingPanel(canvas=canvas)
    panel.show()

    assert panel.engine.is_recording is False
    assert panel.btn_toggle.text() == "Iniciar Gravação"
    assert panel.row_extra.isHidden() is True

    # Inicia via clique
    panel.btn_toggle.click()
    assert panel.engine.is_recording is True
    assert panel.btn_toggle.text() == "Pausar Gravação"
    assert panel.row_extra.isHidden() is False

    # Descarta
    panel.engine.discard_recording()
    assert panel.engine.is_recording is False
    assert panel.btn_toggle.text() == "Iniciar Gravação"
    panel.close()


def test_recording_plugin_activation(qapp):
    """Valida registro e ciclo de vida do RecordingPlugin no ServiceRegistry."""
    from ui.core.plugins.registry import ServiceRegistry

    canvas = DummyCanvas()
    mock_ws = MockWorkspaceService(canvas)
    reg = ServiceRegistry.instance()

    old_impls = reg._registry.get(WorkspaceService, [])[:]
    reg._registry[WorkspaceService] = [mock_ws]

    try:
        class DummyContext:
            service_registry = reg

        plugin = RecordingPlugin()
        meta = plugin.get_metadata()
        assert meta.id == "lumenia.recording_ui"

        plugin.initialize(DummyContext())
        plugin.activate()

        assert "recording" in mock_ws.panels
        panel_info = mock_ws.panels["recording"]
        assert panel_info["title"] == "Timelapse"
        assert panel_info["area"] == "right"

        plugin.deactivate()
        assert "recording" not in mock_ws.panels
    finally:
        reg._registry[WorkspaceService] = old_impls
