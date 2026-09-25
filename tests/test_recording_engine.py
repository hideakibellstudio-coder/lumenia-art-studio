"""
Plugin de Gravação & Timelapse: o motor de gravação (ARCcC).
=============================================================
Ciclo de vida da sessão, captura assíncrona, exportação ZIP, marca d'água e
guias na captura. Painel e plugin: `test_recording_plugin.py`.
"""

import os
import zipfile
from PySide6 import QtCore, QtGui

from ui.plugins.panels.recording_plugin.engine.recording_engine import TimelapseRecordingEngine
from ui.plugins.panels.recording_plugin.engine.export_worker import TimelapseExportWorker
from ui.plugins.panels.recording_plugin.engine.frame_source import DocumentFrameSource
from ui.core.document.document import Document
from ui.plugins.panels.recording_plugin.panel import RecordingPanel
from tests.recording_doubles import DummyBackend, DummyCanvas, make_engine


def test_recording_engine_lifecycle(qapp):
    """Valida ciclo completo de sessão do motor de gravação (start, pause, resume, discard)."""
    canvas = DummyCanvas()
    engine = make_engine()
    canvas.strokeFinished.connect(engine.on_stroke_finished)

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



def test_recording_include_guides_option(qapp, tmp_path):
    """Valida a opção de incluir guias ativas (simetria e perspectiva) na captura de timelapse."""
    from ui.plugins.panels.recording_plugin.engine.recording_engine import FrameSaveTask

    # Guias e simetria vêm do documento ativo (fonte única), não do canvas.
    doc = Document("rec-guides", "Guias", 400, 300)
    doc.sym_state = {"mode": "mirror", "cx": 200.0, "cy": 150.0, "angle": 90.0}
    doc.guide_state = {"type": "straight", "p0": QtCore.QPointF(0, 150), "p1": QtCore.QPointF(400, 150), "hidden": False}
    source = DocumentFrameSource(backend=lambda: DummyBackend(400, 300), document=lambda: doc)
    panel = RecordingPanel(TimelapseRecordingEngine(source))
    panel.show()

    assert panel.engine.include_guides is False
    assert panel.chk_guides.isChecked() is False

    # Marca o checkbox de guias
    panel.chk_guides.setChecked(True)
    assert panel.engine.include_guides is True

    # Inicia gravação e captura um frame
    panel.engine.start_recording()
    QtCore.QThreadPool.globalInstance().waitForDone(2000)

    # FrameSaveTask com guides_data deve ter gravado o frame com sucesso
    assert panel.engine.frame_count >= 1
    files = os.listdir(panel.engine.temp_dir)
    assert "frame_000001.jpg" in files

    # Valida execução direta do FrameSaveTask com guias e callback injetado
    called_render = []
    def dummy_renderer(painter, sym, guide, zoom=1.0):
        called_render.append((sym, guide))

    out_file = str(tmp_path / "frame_with_guides.jpg")
    raw = b"\xff\xff\xff\xff" * (400 * 300)
    guides_data = source.grab(include_guides=True).guides
    assert guides_data["sym"]["mode"] == "mirror" and guides_data["guide"]["type"] == "straight"
    assert source.grab(include_guides=False).guides is None
    task = FrameSaveTask(raw, 400, 300, 400, 300, out_file, guides_data=guides_data, guides_renderer=dummy_renderer)
    task.run()
    assert os.path.exists(out_file)
    assert len(called_render) == 1
    assert called_render[0][0]["mode"] == "mirror"

    panel.engine.discard_recording()
    panel.close()
