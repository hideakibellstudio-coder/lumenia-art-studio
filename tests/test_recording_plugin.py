"""
Testes de Unidade e Contrato para o Plugin de Gravação & Timelapse (ARCcC).
===========================================================================
Valida o ciclo de vida do motor de gravação, captura assíncrona, exportação ZIP,
comportamento do painel de UI e registro no WorkspaceService.
"""

import os
import zipfile
from PySide6 import QtCore, QtWidgets, QtGui

from ui.plugins.panels.recording_plugin.engine.recording_engine import TimelapseRecordingEngine
from ui.plugins.panels.recording_plugin.engine.export_worker import TimelapseExportWorker
from ui.plugins.panels.recording_plugin.engine.frame_source import DocumentFrameSource, Frame
from ui.core.document.document import Document
from ui.plugins.panels.recording_plugin.panel import RecordingPanel
from ui.plugins.panels.recording_plugin import RecordingPlugin
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


def test_recording_panel_ui(qapp):
    """Valida que o RecordingPanel instancia todos os controles e responde a comandos."""
    panel = RecordingPanel(make_engine())
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

        # O plugin liga o fim do traço do canvas ao motor de gravação...
        engine = panel_info["widget"].engine
        engine.start_recording()
        canvas.strokeFinished.emit()
        assert engine.stroke_debounce_timer.isActive()
        engine.discard_recording()

        plugin.deactivate()
        assert "recording" not in mock_ws.panels
        # ...e desliga ao desativar.
        assert canvas.receivers(QtCore.SIGNAL("strokeFinished()")) == 0
        # A barra flutuante também solta o canvas (filtro de eventos e aviso de
        # destruição): o canvas continua vivo depois que o painel morre, e o
        # filtro de uma barra já destruída derrubava o processo (2026-09-25).
        assert canvas.receivers(QtCore.SIGNAL("destroyed(QObject*)")) == 0
    finally:
        reg._registry[WorkspaceService] = old_impls


def test_recording_fps_selection_and_duration_calculation(qapp):
    """Valida a seleção dinâmica de taxa de quadros (24, 30, 60 FPS) e o cálculo de duração."""
    panel = RecordingPanel(make_engine())

    assert panel.engine.fps == 30
    assert panel.combo_fps.currentText() == "30 FPS (Padrão)"

    # Simula 60 quadros capturados
    panel.engine.frame_count = 60
    panel.engine._emit_stats()
    assert "2.0s (a 30 FPS)" in panel.lbl_diag_dur.text()

    # Muda para 60 FPS
    panel.combo_fps.setCurrentIndex(1)
    assert panel.engine.fps == 60
    assert "1.0s (a 60 FPS)" in panel.lbl_diag_dur.text()

    # Muda para 24 FPS
    panel.combo_fps.setCurrentIndex(2)
    assert panel.engine.fps == 24
    assert "2.5s (a 24 FPS)" in panel.lbl_diag_dur.text()

    # Valida worker com FPS configurado
    worker = TimelapseExportWorker("dummy_dir", 60, fps=panel.engine.fps)
    assert worker.fps == 24
    worker.export("dummy.mp4", fps=60)
    assert worker.fps == 60

    panel.close()


def test_recording_floating_bar_lifecycle_and_anchoring(qapp):
    """Valida ciclo de vida, ancoragem no topo do viewport e sincronização da barra flutuante."""
    canvas = QtWidgets.QWidget()
    canvas.resize(800, 600)
    canvas.show()

    panel = RecordingPanel(make_engine(), anchor=canvas)
    panel.show()

    fbar = panel.floating_bar
    assert fbar is not None
    assert fbar.isHidden() is True

    # Inicia gravação -> barra flutuante deve se tornar visível e ancorada
    panel.btn_toggle.click()
    assert panel.engine.is_recording is True
    assert fbar.isVisible() is True
    assert fbar.lbl_status.text() == "REC"

    # Testa sincronização de estatísticas
    panel.engine.elapsed_seconds = 125
    panel.engine.frame_count = 42
    panel.engine._emit_stats()
    assert "00:02:05" in fbar.lbl_time.text()
    assert "42 f" in fbar.lbl_frames.text()

    # Pausa via botão da barra flutuante
    fbar.btn_pause_resume.click()
    assert panel.engine.is_paused is True
    assert fbar.lbl_status.text() == "PAUSA"

    # Retoma via botão da barra flutuante
    fbar.btn_pause_resume.click()
    assert panel.engine.is_paused is False
    assert fbar.lbl_status.text() == "REC"

    # Testa posicionamento na âncora do topo
    fbar.reposition_to_top_anchor()
    canvas_global = canvas.mapToGlobal(QtCore.QPoint(0, 0))
    assert abs(fbar.y() - (canvas_global.y() + 14)) <= 5

    # Encerra gravação -> barra flutuante deve desaparecer
    panel.engine.discard_recording()
    assert panel.engine.is_recording is False
    assert fbar.isHidden() is True

    panel.close()
    canvas.close()


def test_recording_stop_flow_dialog(qapp, monkeypatch):
    """Valida o fluxo de parada (Stop) com pergunta de salvar, descartar e cancelar."""
    canvas = QtWidgets.QWidget()
    canvas.resize(400, 300)
    panel = RecordingPanel(make_engine(), anchor=canvas)
    panel.show()
    stop = panel.actions.request_stop

    # 1. Parar sem gravação ativa retorna False
    assert stop() is False

    # 2. Inicia gravação com 0 quadros -> parar descarta direto e avisa
    panel.btn_toggle.click()
    panel.engine.frame_count = 0
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *args, **kwargs: None)
    stopped = stop()
    assert stopped is True
    assert panel.engine.is_recording is False

    # 3. Gravação com quadros -> Escolher "Cancelar" não interrompe
    panel.btn_toggle.click()
    panel.engine.frame_count = 15

    def mock_msgbox_choice(target_role):
        def fake_exec(self):
            for btn in self.buttons():
                if self.buttonRole(btn) == target_role:
                    self._mock_clicked = btn
                    break
        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", fake_exec)
        monkeypatch.setattr(QtWidgets.QMessageBox, "clickedButton", lambda self: getattr(self, "_mock_clicked", None))

    mock_msgbox_choice(QtWidgets.QMessageBox.ButtonRole.RejectRole)
    res = stop()
    assert res is False
    assert panel.engine.is_recording is True
    assert panel.engine.is_paused is False

    # 4. Gravação com quadros -> Escolher "Descartar"
    mock_msgbox_choice(QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
    res = stop()
    assert res is True
    assert panel.engine.is_recording is False

    # 5. Gravação com quadros -> Escolher "Salvar"
    panel.btn_toggle.click()
    panel.engine.frame_count = 20

    mock_msgbox_choice(QtWidgets.QMessageBox.ButtonRole.AcceptRole)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: ("dummy_save.mp4", "mp4"))
    monkeypatch.setattr(TimelapseExportWorker, "export", lambda self, path, fmt=None, fps=None: None)

    res = stop()
    assert res is True
    assert panel.engine.is_recording is False
    assert panel.floating_bar.isHidden() is True

    panel.close()
    canvas.close()


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


def test_recording_zero_cross_plugin_imports():
    """Garante conformidade estrita com a Lei Canônica de Zero Cross-Plugin Imports."""
    import ast
    import pathlib
    base_dir = pathlib.Path(__file__).parent.parent / "ui" / "plugins" / "panels" / "recording_plugin"
    py_files = list(base_dir.rglob("*.py"))
    assert py_files, f"pasta do plugin não encontrada: {base_dir}"
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("ui.plugins.") and "recording_plugin" not in node.module:
                    assert False, f"Cross-Plugin Import em {py_file}: {node.module}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("ui.plugins.") and "recording_plugin" not in alias.name:
                        assert False, f"Cross-Plugin Import em {py_file}: {alias.name}"
