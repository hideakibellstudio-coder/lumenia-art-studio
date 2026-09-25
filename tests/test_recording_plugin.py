"""
Plugin de Gravação & Timelapse: painel, barra flutuante e registro (ARCcC).
==========================================================================
Painel de UI, ativação no WorkspaceService, FPS, barra flutuante, fluxo de
parada e zero imports entre plugins. O motor: `test_recording_engine.py`.
"""

from PySide6 import QtCore, QtWidgets

from ui.plugins.panels.recording_plugin.engine.export_worker import TimelapseExportWorker
from ui.plugins.panels.recording_plugin.panel import RecordingPanel
from ui.plugins.panels.recording_plugin import RecordingPlugin
from ui.core.plugins.workspace_contract import WorkspaceService
from ui.infrastructure.i18n import I18nManager
from tests.recording_doubles import DummyCanvas, MockWorkspaceService, make_engine


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



def test_recording_panel_follows_the_interface_language(qapp):
    """Textos seguem o idioma; o dado dos combos (resolução, formato) não muda com a tradução."""
    i18n = I18nManager.instance()
    panel = RecordingPanel(make_engine())
    panel.combo_res.setCurrentIndex(1)
    panel.combo_format.setCurrentIndex(1)
    try:
        i18n.set_locale("en_US", is_auto=False)
        assert panel.btn_toggle.text() == "Start Recording"
        assert panel.combo_fps.currentText() == "30 FPS (Default)"
        assert panel.floating_bar.btn_save.toolTip() == "Save Video..."
        assert panel.engine.target_resolution == "1080p"
        assert panel.combo_format.currentData() == "zip"
    finally:
        i18n.set_locale("pt_BR", is_auto=False)
        panel.shutdown()
        panel.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    i18n.set_locale("en_US", is_auto=False)  # painel já destruído: o sinal não pode chegar nele
    i18n.set_locale("pt_BR", is_auto=False)

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
