"""
Contratos do plugin de gravação depois de desfazer o espaguete (2026-09-24)
===========================================================================
- o quadro vem do documento ativo e do motor (`DocumentFrameSource`), não do
  canvas lido por `getattr`;
- a barra flutuante só emite sinais (não conhece o painel);
- exportar encerra a sessão (quadros temporários e contadores zerados).
"""
from PySide6 import QtCore, QtGui, QtWidgets

from ui.plugins.panels.recording_plugin.engine.export_worker import TimelapseExportWorker
from ui.plugins.panels.recording_plugin.engine.frame_source import DocumentFrameSource
from ui.plugins.panels.recording_plugin.panel import RecordingPanel
from tests.test_recording_plugin import DummyBackend, make_engine
from ui.core.document.document import Document


def test_frame_source_le_o_documento_e_o_motor(qapp):
    """Quadro = pixels do motor + tamanho, papel e guias do documento ativo."""
    doc = Document("rec-src", "Fonte", 100, 100)
    source = DocumentFrameSource(backend=lambda: DummyBackend(100, 100), document=lambda: doc)
    frame = source.grab(include_guides=True)
    assert (frame.width, frame.height, len(frame.pixels)) == (100, 100, 100 * 100 * 4)
    assert frame.guides is None  # nenhuma guia ativa

    class QImageOnlyBackend:
        """Motor sem buffer de exibição: compõe a imagem sobre o papel."""
        def get_display_pixel_buffer(self):
            return None

        def get_qimage(self):
            image = QtGui.QImage(10, 10, QtGui.QImage.Format.Format_RGBA8888)
            image.fill(QtCore.Qt.GlobalColor.transparent)
            return image

    doc.set_paper(color=QtGui.QColor(0, 0, 255))
    frame = DocumentFrameSource(backend=QImageOnlyBackend, document=lambda: doc).grab(False)
    assert frame.pixels[:4] == bytes([0, 0, 255, 255])  # papel azul por baixo
    assert DocumentFrameSource(backend=lambda: None, document=lambda: doc).grab(False) is None
    assert DocumentFrameSource(backend=QImageOnlyBackend, document=lambda: None).grab(False) is None


def test_barra_flutuante_so_emite_sinais(qapp):
    """A barra não conhece o painel: emite e o painel liga ao RecordingActions."""
    from ui.plugins.panels.recording_plugin.components.recording_floating_bar import RecordingFloatingBar
    bar = RecordingFloatingBar()
    fired = []
    bar.pauseResumeRequested.connect(lambda: fired.append("pause"))
    bar.stopRequested.connect(lambda: fired.append("stop"))
    bar.saveRequested.connect(lambda: fired.append("save"))
    bar.btn_pause_resume.click()
    bar.btn_stop.click()
    bar.btn_save.click()
    assert fired == ["pause", "stop", "save"]
    bar.update_state(True, True)
    assert bar.lbl_status.text() == "PAUSA"
    bar.close()


def test_exportar_encerra_a_sessao(qapp, monkeypatch):
    """Depois de exportar, quadros temporários e contadores zeram (o painel mostra 00:00:00)."""
    engine = make_engine()
    panel = RecordingPanel(engine)
    engine.start_recording()
    engine.elapsed_seconds = 42
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: ("x.zip", "zip"))

    def fake_export(worker, path, fmt=None, fps=None):
        worker.finished.emit(True, "ok", path)

    monkeypatch.setattr(TimelapseExportWorker, "export", fake_export)
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    assert panel.actions.save() is True
    assert engine.frame_count == 0 and engine.temp_dir is None
    assert panel.lbl_time.text() == "00:00:00"
    panel.close()
