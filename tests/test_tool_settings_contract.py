"""Contract tests for canonical canvas-tool settings and their workspace route."""

from types import SimpleNamespace

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QApplication

from plugins.system.workspace_core.workspace.workspace_brush_adapter import WorkspaceBrushMixin
from plugins.system.workspace_core.workspace.canvas.tools.eyedrop_tool_controller import EyedropToolController
from plugins.system.workspace_core.workspace.canvas.tools.selection_tool_controller import SelectionToolController
from plugins.system.workspace_core.workspace.canvas.tools.tool_manager import ToolManager
from plugins.system.workspace_core.workspace.canvas.tools.transform_tool_controller import TransformToolController
from plugins.ui.brush_plugin.panel import BrushSettingsPanel
from ui.core.engine.registry import EngineRegistry
from ui.core.tool_settings import TOOL_SETTING_DEFAULTS, default_tool_settings, normalize_tool_settings
from ui.core.widgets.tool_options.bucket_wand_options import BucketOptionsWidget
from ui.core.widgets.tool_options.transform_selection_options import TransformOptionsWidget


app = QApplication.instance() or QApplication(["--platform", "offscreen"])


def test_tool_defaults_are_independent_and_cover_each_configurable_tool():
    expected = {
        "bucket", "eyedrop", "wand", "rect_select", "ellipse_select", "lasso", "transform", "smudge", "shapes", "text",
    }
    assert set(TOOL_SETTING_DEFAULTS) == expected

    first = default_tool_settings("bucket")
    first["tolerance"] = 90
    assert default_tool_settings("bucket")["tolerance"] == 20

    shape = default_tool_settings("shapes")
    shape["stroke_color"].setRed(200)
    assert default_tool_settings("shapes")["stroke_color"].red() == 0


def test_normalizer_accepts_legacy_events_but_returns_only_canonical_keys():
    bucket = normalize_tool_settings("bucket", {"expansion": -3, "tolerance": 60})
    assert bucket["expand_px"] == -3
    assert "expansion" not in bucket

    geometry = normalize_tool_settings("rect_select", {"feather": 12, "anti_alias": False})
    assert geometry["feather_px"] == 12
    assert geometry["aa"] is False
    assert "feather" not in geometry and "anti_alias" not in geometry


def test_normalizer_rejects_invalid_values_without_corrupting_current_state():
    current = {"tolerance": 42, "expand_px": 4}
    result = normalize_tool_settings("bucket", {"tolerance": True, "expand_px": 999, "unknown": "x"}, current)
    assert result["tolerance"] == 42
    assert result["expand_px"] == 4
    assert "unknown" not in result

    text = normalize_tool_settings("text", {"font_size": 72, "align": "right", "bold": True})
    assert text["font_size"] == 72 and text["align"] == "right" and text["bold"] is True
    assert normalize_tool_settings("shapes", {"stroke_width": 0})["stroke_width"] == 4


def test_workspace_routes_canonical_settings_to_the_controllers_that_consume_them():
    captured = {}
    canvas = SimpleNamespace(
        _bucket_settings=default_tool_settings("bucket"),
        _eyedrop_settings=default_tool_settings("eyedrop"),
        _wand_settings=default_tool_settings("wand"),
        _geom_select_settings=default_tool_settings("rect_select"),
        _lasso_settings=default_tool_settings("lasso"),
        _shape_settings=default_tool_settings("shapes"),
        _text_settings=default_tool_settings("text"),
        transform_ctrl=SimpleNamespace(interp_mode=2, lock_aspect=False),
    )
    canvas.set_shape_settings = lambda settings: captured.setdefault("shapes", settings)
    canvas.set_text_settings = lambda settings: captured.setdefault("text", settings)
    workspace = WorkspaceBrushMixin()
    workspace.canvas_widget = canvas

    workspace._on_tool_settings_changed("bucket", {"expansion": -2})
    workspace._on_tool_settings_changed("rect_select", {"feather": 9, "anti_alias": False})
    workspace._on_tool_settings_changed("transform", {"interp_mode": 1, "lock_aspect": True})
    workspace._on_tool_settings_changed("shapes", {"shape_type": "shape_star", "star_points": 7})
    workspace._on_tool_settings_changed("text", {"font_size": 48, "align": "center"})

    assert canvas._bucket_settings["expand_px"] == -2
    assert canvas._geom_select_settings["feather_px"] == 9
    assert canvas._geom_select_settings["aa"] is False
    assert canvas.transform_ctrl.interp_mode == 1
    assert canvas.transform_ctrl.lock_aspect is True
    assert captured["shapes"]["shape_type"] == "shape_star"
    assert captured["shapes"]["star_points"] == 7
    assert captured["text"]["font_size"] == 48 and captured["text"]["align"] == "center"


def test_core_option_widgets_emit_canonical_values():
    bucket = BucketOptionsWidget()
    bucket_events = []
    bucket.settingsChanged.connect(bucket_events.append)
    bucket.slider_exp.setValue(-5)
    assert bucket_events[-1]["expand_px"] == -5
    assert "expansion" not in bucket_events[-1]

    transform = TransformOptionsWidget()
    transform_events = []
    transform.settingsChanged.connect(transform_events.append)
    transform.combo_mode.setCurrentIndex(1)
    assert transform_events[-1]["lock_aspect"] is True
    transform.chk_bicubic.setChecked(False)
    assert transform_events[-1]["interp_mode"] == 1


def test_brush_panel_forwards_wand_transform_and_active_selection_settings():
    panel = BrushSettingsPanel()
    events = []
    panel.toolOptionsChanged.connect(lambda tool, settings: events.append((tool, settings)))

    panel.wand_options_widget.slider_tol.setValue(37)
    assert events[-1][0] == "wand"
    assert events[-1][1]["tolerance"] == 37

    panel.transform_options_widget.combo_mode.setCurrentIndex(1)
    assert events[-1][0] == "transform"
    assert events[-1][1]["lock_aspect"] is True

    panel.set_tool_active("ellipse_select")
    panel.selection_options_widget.chk_aa.setChecked(False)
    assert events[-1][0] == "ellipse_select"
    assert events[-1][1]["aa"] is False


class _Signal:
    def __init__(self):
        self.count = 0
        self.value = None

    def emit(self, value=None):
        self.count += 1
        self.value = value


class _BackendSpy:
    def __init__(self):
        self.calls = []

    def fill_area(self, **kwargs):
        self.calls.append(("fill", kwargs))
        return True

    def pick_color_merged(self, x, y, radius):
        self.calls.append(("pick_merged", (x, y, radius)))
        return (10, 20, 30, 255)

    def pick_color_layer(self, layer, x, y, radius):
        self.calls.append(("pick_layer", (layer, x, y, radius)))
        return (40, 50, 60, 255)

    def get_active_layer_index(self):
        return 3

    def magic_wand_select(self, **kwargs):
        self.calls.append(("wand", kwargs))
        return True

    def select_rect(self, *args, **kwargs):
        self.calls.append(("rect", (args, kwargs)))

    def select_polygon(self, *args, **kwargs):
        self.calls.append(("lasso", (args, kwargs)))

    def has_selection(self):
        return True

    def commit_transform(self, **kwargs):
        self.calls.append(("transform", kwargs))


def _with_backend(backend):
    registry = EngineRegistry.instance()
    previous = registry.get_backend()
    registry.set_backend(backend)
    return registry, previous


def test_bucket_and_eyedrop_controls_reach_the_backend_with_canonical_values():
    backend = _BackendSpy()
    registry, previous = _with_backend(backend)
    try:
        color = QtGui.QColor(12, 34, 56, 255)
        widget = SimpleNamespace(
            _active_draw_color=color,
            _bucket_settings=normalize_tool_settings("bucket", {"expansion": -3}),
            to_canvas=lambda *_: SimpleNamespace(x=12, y=18),
            strokeStarted=_Signal(),
            strokeFinished=_Signal(),
            update=lambda: None,
        )
        ToolManager.do_flood_fill(SimpleNamespace(widget=widget), 0, 0)
        kind, fill = backend.calls[-1]
        assert kind == "fill"
        assert fill["fill_color"] == color and fill["expand_px"] == -3
        assert widget.strokeStarted.count == widget.strokeFinished.count == 1

        widget.backend = backend
        widget.canvas_w, widget.canvas_h = 64, 64
        widget.colorPicked = _Signal()
        eyedrop = EyedropToolController(widget)
        eyedrop.settings = normalize_tool_settings("eyedrop", {"sample_all": False, "sample_radius": 2})
        assert eyedrop.do_sample(0, 0) == QtGui.QColor(40, 50, 60, 255)
        assert backend.calls[-1] == ("pick_layer", (3, 12, 18, 2))
    finally:
        registry.set_backend(previous)


def test_selection_and_transform_controllers_forward_the_normalized_options():
    backend = _BackendSpy()
    registry, previous = _with_backend(backend)
    canvas: QtWidgets.QWidget = QtWidgets.QWidget()
    canvas.canvas_w, canvas.canvas_h = 100, 100
    canvas.active_tool = "rect_select"
    canvas.to_canvas = lambda *_: SimpleNamespace(x=25, y=30)
    canvas.update = lambda: None
    canvas.strokeFinished = _Signal()
    try:
        selection: SelectionToolController = SelectionToolController(canvas)
        selection.wand_settings = normalize_tool_settings("wand", {"tolerance": 55, "mode": 2})
        selection.do_magic_wand_select(0, 0)
        assert backend.calls[-1] == ("wand", {
            "seed_x": 25, "seed_y": 30, "tolerance": 55, "contiguous": True,
            "expand_px": 0, "anti_aliasing": True, "mode": 2, "sample_all_layers": True,
        })

        selection.geom_select_settings = normalize_tool_settings("rect_select", {"feather_px": 7, "aa": False})
        selection.drag_start = QtCore.QPointF(10, 10)
        selection.drag_current = QtCore.QPointF(50, 30)
        selection.finish_geom_selection()
        kind, (_, rect) = backend.calls[-1]
        assert kind == "rect" and rect["feather_px"] == 7

        transform: TransformToolController = TransformToolController(canvas)
        transform.active = True
        transform.pivot = QtCore.QPointF(20, 20)
        transform.interp_mode, transform.lock_aspect = 1, True
        transform.commit()
        assert backend.calls[-1][0] == "transform"
        assert backend.calls[-1][1]["interp_mode"] == 1
    finally:
        registry.set_backend(previous)
        canvas.deleteLater()
