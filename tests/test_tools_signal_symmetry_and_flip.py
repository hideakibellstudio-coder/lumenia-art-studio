"""Testes automatizados cobrindo a integridade dos subsistemas satélites (Rodada 9).

Cobre:
1. Flip de Câmera (Menu MainWindowImageActionsMixin + NavigatorPanel + CanvasCompatMixin).
2. Grade e Réguas (MainWindowImageActionsMixin + geometry_ctrl / geometry_controller).
3. Seleção e Marching Ants (select_all, invert_selection, clear_selection em MainWindowMenuActions, WorkspaceActions e SelectionToolController).
4. Guards de Fallback do AladynBackend (set_render_options e render).
5. Remoção do Shim Nível 2 em color_plugin (importação canônica de ColorWheelWidget).
6. Simetria de Ciclo de Vida de Sinais strokeStarted/strokeFinished (ShapeTool e TransformTool).
"""

from __future__ import annotations

import pytest
from PySide6 import QtCore, QtWidgets, QtGui

from ui.core.engine.registry import EngineRegistry
from ui.core.engine.backend import EngineBackend
from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
from plugins.system.workspace_core.workspace.canvas.viewport.camera_controller import CameraController
from plugins.ui.navigator_plugin.panel import NavigatorPanel
from plugins.ui.color_plugin.panel import ColorWheelPanel
from ui.boundary.orchestrator.main_window_image_actions import MainWindowImageActionsMixin
from ui.boundary.orchestrator.main_window_menu_actions import MainWindowMenuActionsMixin
from ui.engine_backends.aladyn import AladynBackend


class _MockBackend(EngineBackend):
    def __init__(self):
        super().__init__()
        self._selection_active = False
        self._sel_all_called = False
        self._invert_called = False
        self._clear_called = False

    def clear_canvas(self) -> None: pass
    def dispatch(self, cmd: str, *args, **kwargs): pass
    def end_stroke(self, *args, **kwargs): return []
    def init_renderer(self, *args, **kwargs): pass
    def paint_stroke(self, *args, **kwargs): return []
    def render(self, *args, **kwargs): pass
    def resize(self, *args, **kwargs): pass
    def set_brush_color(self, *args, **kwargs): pass
    def set_brush_size(self, *args, **kwargs): pass
    def start_stroke(self, *args, **kwargs): pass
    def to_canvas(self, *args, **kwargs): return None
    def update_view(self, *args, **kwargs): pass

    def has_selection(self) -> bool:
        return self._selection_active

    def select_all(self) -> None:
        self._selection_active = True
        self._sel_all_called = True

    def invert_selection(self) -> None:
        self._selection_active = not self._selection_active
        self._invert_called = True

    def clear_selection(self) -> None:
        self._selection_active = False
        self._clear_called = True


class _MockStatusBar:
    def __init__(self):
        self.last_msg = ""
    def showMessage(self, msg, timeout=0):
        self.last_msg = msg


class _MockImageActionsWindow(MainWindowImageActionsMixin):
    def __init__(self, workspace):
        self.workspace = workspace
        self.status_bar = _MockStatusBar()
        self.dm = None


class _MockMenuActionsWindow(MainWindowMenuActionsMixin):
    def __init__(self, workspace):
        self.workspace = workspace
        self.status_bar = _MockStatusBar()
        self.dm = None


@pytest.fixture
def app():
    qapp = QtWidgets.QApplication.instance()
    if qapp is None:
        qapp = QtWidgets.QApplication([])
    return qapp


@pytest.fixture
def clean_engine():
    prev = EngineRegistry.instance().get_backend()
    backend = _MockBackend()
    EngineRegistry.instance().set_backend(backend)
    yield backend
    # Teardown
    backend.clear_selection()
    EngineRegistry.instance().set_backend(prev)



# ── 1. Flip de Câmera & Navigator ─────────────────────────────────────────────

def test_camera_flip_properties(app):
    rw = RenderWidget()
    assert rw.flip_x is False
    assert rw.flip_y is False
    assert rw.camera.flip_horizontal is False
    assert rw.camera.flip_vertical is False

    rw.flip_x = True
    assert rw.flip_x is True
    assert rw.camera.flip_horizontal is True

    rw.flip_y = True
    assert rw.flip_y is True
    assert rw.camera.flip_vertical is True



def test_main_window_image_actions_flip(app):
    class MockWS:
        def __init__(self):
            self.canvas_widget = RenderWidget()

    ws = MockWS()
    win = _MockImageActionsWindow(ws)

    win.flip_horizontal()
    assert ws.canvas_widget.flip_x is True
    assert ws.canvas_widget.camera.flip_horizontal is True
    assert "espelhada horizontalmente" in win.status_bar.last_msg

    win.flip_horizontal()
    assert ws.canvas_widget.flip_x is False

    win.flip_vertical()
    assert ws.canvas_widget.flip_y is True
    assert ws.canvas_widget.camera.flip_vertical is True
    assert "espelhada verticalmente" in win.status_bar.last_msg


def test_navigator_flip_signal_emission(app):
    panel = NavigatorPanel()
    emitted = []
    panel.flip_changed_by_user.connect(lambda fx, fy: emitted.append((fx, fy)))

    panel.toggle_flip_h()
    assert len(emitted) == 1
    assert emitted[-1] == (True, False)

    panel.toggle_flip_v()
    assert len(emitted) == 2
    assert emitted[-1] == (True, True)

    panel.toggle_flip_h()
    assert len(emitted) == 3
    assert emitted[-1] == (False, True)


# ── 2. Grade & Réguas via Menu ────────────────────────────────────────────────

def test_main_window_toggle_grid_and_rulers(app):
    rw = RenderWidget()
    assert hasattr(rw, "geometry_ctrl")
    assert hasattr(rw, "geometry_controller")
    assert rw.geometry_ctrl is rw.geometry_controller

    class MockWS:
        def __init__(self):
            self.canvas_widget = rw

    ws = MockWS()
    win = _MockImageActionsWindow(ws)

    # Toggle grade
    initial_v = rw.geometry_ctrl.guide_state.get("show_v", True)
    win.toggle_grid()
    assert rw.geometry_ctrl.guide_state["show_v"] == (not initial_v)
    assert "Grade magnética" in win.status_bar.last_msg

    # Toggle réguas
    initial_type = rw.geometry_ctrl.guide_state.get("type", "none")
    win.toggle_rulers()
    expected_type = "straight" if initial_type == "none" else "none"
    assert rw.geometry_ctrl.guide_state["type"] == expected_type
    assert "Réguas" in win.status_bar.last_msg


# ── 3. Seleção e Marching Ants ────────────────────────────────────────────────

def test_selection_controller_timer_lifecycle(app, clean_engine):
    rw = RenderWidget()
    sel_ctrl = rw.selection_ctrl

    assert not sel_ctrl.selection_timer.isActive()

    # select_all deve ativar timer
    sel_ctrl.select_all()
    assert clean_engine._sel_all_called
    assert clean_engine.has_selection()
    assert sel_ctrl.selection_timer.isActive()

    # clear_selection deve desativar timer imediatamente
    sel_ctrl.clear_selection()
    assert clean_engine._clear_called
    assert not clean_engine.has_selection()
    assert not sel_ctrl.selection_timer.isActive()

    # invert_selection
    sel_ctrl.invert_selection()
    assert clean_engine.has_selection()
    assert sel_ctrl.selection_timer.isActive()

    sel_ctrl.invert_selection()
    assert not clean_engine.has_selection()
    assert not sel_ctrl.selection_timer.isActive()


def test_menu_actions_select_all_and_invert(app, clean_engine):
    rw = RenderWidget()
    class MockWS:
        def __init__(self):
            self.canvas_widget = rw

    ws = MockWS()
    win = _MockMenuActionsWindow(ws)

    win.select_all()
    assert clean_engine.has_selection()
    assert rw.selection_ctrl.selection_timer.isActive()
    assert "Tudo selecionado" in win.status_bar.last_msg

    win.invert_selection()
    assert not clean_engine.has_selection()
    assert not rw.selection_ctrl.selection_timer.isActive()
    assert "Seleção invertida" in win.status_bar.last_msg


def test_workspace_actions_clear_selection(app, clean_engine):
    rw = RenderWidget()
    rw.select_all()
    assert rw.selection_ctrl.selection_timer.isActive()

    from plugins.system.workspace_core.workspace.workspace_actions import WorkspaceActionsMixin

    wa = WorkspaceActionsMixin.__new__(WorkspaceActionsMixin)
    wa.canvas_widget = rw
    wa._on_status_notification = lambda msg: setattr(wa, "status_msg", msg)


    wa.clear_selection()
    assert not clean_engine.has_selection()
    assert not rw.selection_ctrl.selection_timer.isActive()
    assert wa.status_msg == "Seleção cancelada."


# ── 4. Guards do AladynBackend ────────────────────────────────────────────────

def test_aladyn_backend_guards():
    backend = AladynBackend()

    # Facade com métodos modernos
    class ModernFacade:
        def __init__(self):
            self.opts = {}
            self.refreshed = False
        def set_render_options(self, **kwargs):
            self.opts = kwargs
        def refresh_display(self):
            self.refreshed = True

    backend._facade = ModernFacade()
    backend.set_render_options(low_latency=True, linear_gamma=False, deep_color=False)
    assert backend._facade.opts.get("low_latency") is True
    backend.render(0, 0, 1.0, 0.0)
    assert backend._facade.refreshed is True

    # Facade legada sem set_render_options e sem refresh_display
    class LegacyFacade:
        def __init__(self):
            self.low_latency = False
            self.buf_called = False
        def set_low_latency(self, val):
            self.low_latency = val
        def get_display_pixel_buffer(self):
            self.buf_called = True

    backend._facade = LegacyFacade()
    backend.set_render_options(low_latency=True, linear_gamma=False, deep_color=False)
    assert backend._facade.low_latency is True

    backend.render(0, 0, 1.0, 0.0)
    assert backend._facade.buf_called is True



# ── 5. Desacoplamento do ColorPlugin ──────────────────────────────────────────

def test_color_plugin_panel_instantiation(app):
    panel = ColorWheelPanel()
    assert panel is not None
    assert panel.color_wheel is not None
    assert hasattr(panel.color_wheel, "set_color")


# ── 6. Simetria de strokeStarted / strokeFinished ─────────────────────────────

def test_transform_controller_signal_symmetry(app):
    rw = RenderWidget()
    started = []
    finished = []
    rw.strokeStarted.connect(lambda: started.append(True))
    rw.strokeFinished.connect(lambda: finished.append(True))

    ctrl = rw.transform_ctrl
    # Simula ativação
    ctrl.active = True
    rw.strokeStarted.emit()
    assert len(started) == 1
    assert len(finished) == 0

    ctrl.cancel()
    assert len(started) == 1
    assert len(finished) == 1
    assert not ctrl.active


def test_shape_controller_signal_symmetry(app):
    rw = RenderWidget()
    started = []
    finished = []
    rw.strokeStarted.connect(lambda: started.append(True))
    rw.strokeFinished.connect(lambda: finished.append(True))

    # Commit sem path (ex: clique isolado sem drag)
    rw.shape_ctrl.commit_to_layer()
    assert len(finished) == 1
