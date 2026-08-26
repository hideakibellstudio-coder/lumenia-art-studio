"""SecondaryToolBar — Floating contextual options bar for active tool."""

from __future__ import annotations

from typing import Optional, Dict
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.icons import get_icon

from .dynamic_stacked_widget import DynamicStackedWidget
from .toolbar_theme import apply_secondary_toolbar_theme
from .toolbar_handlers import SecondaryToolbarHandlersMixin
from .tool_options.eyedrop_options import build_eyedrop_panels
from .tool_options.bucket_options import build_bucket_panels
from .tool_options.wand_options import build_wand_panels
from .tool_options.geom_options import build_geom_panels
from .tool_options.lasso_options import build_lasso_panels
from .tool_options.transform_options import build_transform_panels
from .tool_options.smudge_options import build_smudge_panels
from .tool_options.shapes_options import build_shapes_panels
from .tool_options.text_options import build_text_panels


class SecondaryToolBar(QtWidgets.QDialog, SecondaryToolbarHandlersMixin):
    """Barra flutuante secundária com suporte a orientação horizontal e vertical responsiva."""

    settingsChanged = QtCore.Signal(str, dict)
    commitTextRequested = QtCore.Signal()
    cancelTextRequested = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("QDialog { background: transparent; border: none; }")

        self._orientation: QtCore.Qt.Orientation = QtCore.Qt.Horizontal
        self._active_tool_id: str = "shapes"
        self._current_color: QtGui.QColor = QtGui.QColor(0, 0, 0)
        self._shape_stroke_color: QtGui.QColor = QtGui.QColor(0, 0, 0, 255)
        self._shape_fill_color: QtGui.QColor = QtGui.QColor(0, 0, 0, 255)
        self._text_color: QtGui.QColor = QtGui.QColor(0, 0, 0, 255)

        self._settings_cache: Dict[str, dict] = {
            "eyedrop": {"sample_size": "1x1 Ponto Único", "sample_radius": 0, "sample_all": True, "show_loupe": True},
            "bucket": {"tolerance": 20, "expansion": 1, "contiguous": True, "sample_all": True},
            "wand": {"tolerance": 20, "contiguous": True, "sample_all": True, "mode": 0},
            "rect_select": {"feather": 0, "anti_alias": True, "mode": 0},
            "ellipse_select": {"feather": 0, "anti_alias": True, "mode": 0},
            "lasso": {"feather": 0, "anti_alias": True, "mode": 0},
            "transform": {"interp_mode": 2, "lock_aspect": False},
            "smudge": {"smudge_stretch": 80, "color_pickup": 70, "mix_ratio": 50},
            "shapes": {
                "shape_type": "shape_line", "draw_mode": "both", "stroke_width": 4,
                "stroke_color": self._shape_stroke_color, "fill_color": self._shape_fill_color,
                "fill_opacity": 1.0, "corner_radius": 0, "polygon_sides": 5, "star_points": 5,
            },
            "text": {
                "font_family": "Segoe UI", "font_size": 36, "bold": False, "italic": False,
                "underline": False, "align": "left", "color": self._text_color
            }
        }

        self._build_ui()
        self._apply_theme()
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(lambda _: self._apply_theme())

    def _build_ui(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 10)
        self.main_layout.setSpacing(0)
        self.main_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        self.container = QtWidgets.QWidget(self)
        self.container.setObjectName("SecondaryBarContainer")

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(shadow)

        self.main_layout.addWidget(self.container)

        self.box_layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight, self.container)
        self.box_layout.setContentsMargins(12, 0, 12, 0)
        self.box_layout.setSpacing(8)
        self.box_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.stacked_widget = DynamicStackedWidget(self.container)
        self.box_layout.addWidget(self.stacked_widget)

        self._panels_h: Dict[str, QtWidgets.QWidget] = {}
        self._panels_v: Dict[str, QtWidgets.QWidget] = {}

        build_eyedrop_panels(self)
        build_bucket_panels(self)
        build_wand_panels(self)
        build_geom_panels(self)
        build_lasso_panels(self)
        build_transform_panels(self)
        build_smudge_panels(self)
        build_shapes_panels(self)
        build_text_panels(self)

        self._apply_orientation_constraints()

    def set_orientation(self, orientation: QtCore.Qt.Orientation):
        if self._orientation == orientation:
            return
        self._orientation = orientation
        self._apply_orientation_constraints()
        self._sync_active_tool_view()
        self._apply_theme()
        self.adjustSize()
        parent = self.parent()
        if parent and hasattr(parent, "update_toolbar_position"):
            parent.update_toolbar_position()

    def _apply_orientation_constraints(self):
        is_vert = (self._orientation == QtCore.Qt.Vertical)
        if is_vert:
            self.container.setMinimumHeight(0)
            self.container.setMaximumHeight(16777215)
            self.container.setFixedWidth(206)
            self.box_layout.setContentsMargins(12, 12, 12, 14)
            self.box_layout.setSpacing(6)
            self.box_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        else:
            self.container.setMinimumWidth(0)
            self.container.setMaximumWidth(16777215)
            self.container.setFixedHeight(40)
            self.box_layout.setContentsMargins(12, 0, 12, 0)
            self.box_layout.setSpacing(8)
            self.box_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

    # ── EYEDROP HANDLERS ──
    def _on_eyedrop_sample_changed(self, idx: int, src: str):
        target = self.cbo_sample_v if src == "h" else self.cbo_sample_h
        target.blockSignals(True)
        target.setCurrentIndex(idx)
        target.blockSignals(False)
        self._emit_eyedrop_settings()

    def _on_eyedrop_merged_changed(self, val: bool, src: str):
        target = self.btn_eye_merged_v if src == "h" else self.btn_eye_merged_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_eyedrop_settings()

    def _emit_eyedrop_settings(self):
        radius_map = {0: 0, 1: 1, 2: 2, 3: 5}
        idx = self.cbo_sample_h.currentIndex()
        settings = {
            "sample_size": self.cbo_sample_h.currentText(),
            "sample_radius": radius_map.get(idx, 0),
            "sample_all": self.btn_eye_merged_h.isChecked(),
            "show_loupe": True,
        }
        self._settings_cache["eyedrop"] = settings
        self.settingsChanged.emit("eyedrop", settings)

    # ── BUCKET HANDLERS ──
    def _on_bucket_tol_changed(self, val: int, src: str):
        self.lbl_bkt_tol_val_h.setText(f"{val}%")
        self.lbl_bkt_tol_val_v.setText(f"{val}%")
        target = self.slider_bkt_tol_v if src == "h" else self.slider_bkt_tol_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_bucket_settings()

    def _on_bucket_exp_changed(self, val: int, src: str):
        t = f"{val:+d}px" if val != 0 else "0px"
        self.lbl_bkt_exp_val_h.setText(t)
        self.lbl_bkt_exp_val_v.setText(t)
        target = self.slider_bkt_exp_v if src == "h" else self.slider_bkt_exp_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_bucket_settings()

    def _on_bucket_contig_changed(self, val: bool, src: str):
        target = self.btn_bkt_contig_v if src == "h" else self.btn_bkt_contig_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_bucket_settings()

    def _on_bucket_merged_changed(self, val: bool, src: str):
        target = self.btn_bkt_merged_v if src == "h" else self.btn_bkt_merged_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_bucket_settings()

    def _emit_bucket_settings(self):
        settings = {
            "tolerance": self.slider_bkt_tol_h.value(),
            "expansion": self.slider_bkt_exp_h.value(),
            "contiguous": self.btn_bkt_contig_h.isChecked(),
            "sample_all": self.btn_bkt_merged_h.isChecked(),
        }
        self._settings_cache["bucket"] = settings
        self.settingsChanged.emit("bucket", settings)

    # ── WAND HANDLERS ──
    def _on_wand_tol_changed(self, val: int, src: str):
        self.lbl_wand_tol_val_h.setText(f"{val}%")
        self.lbl_wand_tol_val_v.setText(f"{val}%")
        target = self.slider_wand_tol_v if src == "h" else self.slider_wand_tol_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_wand_settings()

    def _on_wand_contig_changed(self, val: bool, src: str):
        target = self.btn_wand_contig_v if src == "h" else self.btn_wand_contig_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_wand_settings()

    def _on_wand_merged_changed(self, val: bool, src: str):
        target = self.btn_wand_merged_v if src == "h" else self.btn_wand_merged_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_wand_settings()

    def _on_wand_mode_changed(self, idx: int, src: str):
        target = self.cbo_wand_mode_v if src == "h" else self.cbo_wand_mode_h
        target.blockSignals(True)
        target.setCurrentIndex(idx)
        target.blockSignals(False)
        self._emit_wand_settings()

    def _emit_wand_settings(self):
        settings = {
            "tolerance": self.slider_wand_tol_h.value(),
            "contiguous": self.btn_wand_contig_h.isChecked(),
            "sample_all": self.btn_wand_merged_h.isChecked(),
            "mode": self.cbo_wand_mode_h.currentIndex(),
        }
        self._settings_cache["wand"] = settings
        self.settingsChanged.emit("wand", settings)

    # ── GEOM HANDLERS ──
    def _on_geom_feather_changed(self, val: int, src: str):
        self.lbl_geom_feather_val_h.setText(f"{val}px")
        self.lbl_geom_feather_val_v.setText(f"{val}px")
        target = self.slider_geom_feather_v if src == "h" else self.slider_geom_feather_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_geom_settings()

    def _on_geom_aa_changed(self, val: bool, src: str):
        target = self.btn_geom_aa_v if src == "h" else self.btn_geom_aa_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_geom_settings()

    def _on_geom_mode_changed(self, idx: int, src: str):
        target = self.cbo_geom_mode_v if src == "h" else self.cbo_geom_mode_h
        target.blockSignals(True)
        target.setCurrentIndex(idx)
        target.blockSignals(False)
        self._emit_geom_settings()

    def _emit_geom_settings(self):
        settings = {
            "feather": self.slider_geom_feather_h.value(),
            "anti_alias": self.btn_geom_aa_h.isChecked(),
            "mode": self.cbo_geom_mode_h.currentIndex(),
        }
        tool = "ellipse_select" if self._active_tool_id == "ellipse_select" else "rect_select"
        self._settings_cache[tool] = settings
        self.settingsChanged.emit(tool, settings)

    # ── LASSO HANDLERS ──
    def _on_lasso_feather_changed(self, val: int, src: str):
        self.lbl_lasso_feather_val_h.setText(f"{val}px")
        self.lbl_lasso_feather_val_v.setText(f"{val}px")
        target = self.slider_lasso_feather_v if src == "h" else self.slider_lasso_feather_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_lasso_settings()

    def _on_lasso_aa_changed(self, val: bool, src: str):
        target = self.btn_lasso_aa_v if src == "h" else self.btn_lasso_aa_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_lasso_settings()

    def _on_lasso_mode_changed(self, idx: int, src: str):
        target = self.cbo_lasso_mode_v if src == "h" else self.cbo_lasso_mode_h
        target.blockSignals(True)
        target.setCurrentIndex(idx)
        target.blockSignals(False)
        self._emit_lasso_settings()

    def _emit_lasso_settings(self):
        settings = {
            "feather": self.slider_lasso_feather_h.value(),
            "anti_alias": self.btn_lasso_aa_h.isChecked(),
            "mode": self.cbo_lasso_mode_h.currentIndex(),
        }
        self._settings_cache["lasso"] = settings
        self.settingsChanged.emit("lasso", settings)

    def _on_deselect_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            if backend and hasattr(backend, "clear_selection"):
                backend.clear_selection()
            parent.canvas_widget.update()

    # ── TRANSFORM HANDLERS ──
    def _on_trans_interp_changed(self, idx: int, src: str):
        target = self.cbo_trans_interp_v if src == "h" else self.cbo_trans_interp_h
        target.blockSignals(True)
        target.setCurrentIndex(idx)
        target.blockSignals(False)
        self._emit_transform_settings()

    def _on_trans_aspect_changed(self, val: bool, src: str):
        target = self.btn_trans_aspect_v if src == "h" else self.btn_trans_aspect_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_transform_settings()

    def _emit_transform_settings(self):
        settings = {
            "interp_mode": self.cbo_trans_interp_h.currentIndex(),
            "lock_aspect": self.btn_trans_aspect_h.isChecked(),
        }
        self._settings_cache["transform"] = settings
        self.settingsChanged.emit("transform", settings)

    def _on_transform_commit_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.commit_transform()

    def _on_transform_cancel_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.cancel_transform()

    def _on_transform_flip_h_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.transform_flip_h()

    def _on_transform_flip_v_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.transform_flip_v()

    def _on_transform_rot_90_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.transform_rotate_90()

    # ── SMUDGE HANDLERS ──
    def _on_smudge_preset_changed(self, idx: int, src: str):
        target = self.cbo_smudge_preset_v if src == "h" else self.cbo_smudge_preset_h
        target.blockSignals(True)
        target.setCurrentIndex(idx)
        target.blockSignals(False)

        presets = [(80, 70, 50), (90, 85, 70), (50, 50, 40)]
        if 0 <= idx < len(presets):
            st, pk, mx = presets[idx]
            self.slider_smudge_stretch_h.setValue(st)
            self.slider_smudge_pickup_h.setValue(pk)
            self.slider_smudge_mix_h.setValue(mx)
    # ── NAVEGAÇÃO E SINCRONIZAÇÃO ──
    def set_tool(self, tool_id: str):
        self._active_tool_id = tool_id
        if tool_id.startswith("shape_") and tool_id != "shapes":
            self.shape_dropdown_h.set_shape(tool_id)
            self.shape_dropdown_v.set_shape(tool_id)
            self._on_shape_type_changed(tool_id, self.shape_dropdown_h.shape_label(), "h")

        if tool_id in self._panels_h or tool_id.startswith("shape") or tool_id == "shapes":
            self._sync_active_tool_view()
            self.show()
            self.adjustSize()
            parent = self.parent()
            if parent and hasattr(parent, "update_toolbar_position"):
                parent.update_toolbar_position()
            if tool_id.startswith("shape") or tool_id == "shapes":
                self._emit_shapes_settings()
            elif tool_id == "text":
                self._emit_text_settings()
        else:
            self.hide()

    def _sync_active_tool_view(self):
        is_vert = (self._orientation == QtCore.Qt.Vertical)
        panel_map = self._panels_v if is_vert else self._panels_h
        target_widget = panel_map.get(self._active_tool_id)
        if not target_widget and (self._active_tool_id.startswith("shape") or self._active_tool_id == "shapes"):
            target_widget = panel_map.get("shapes")
        if target_widget:
            self.stacked_widget.setCurrentWidget(target_widget)

    def set_captured_color(self, color: QtGui.QColor):
        self._current_color = color
        hex_str = color.name().upper()
        for sw, lbl in [(self.swatch_h, self.lbl_hex_h), (self.swatch_v, self.lbl_hex_v)]:
            sw.setStyleSheet(f"background: {hex_str}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);")
            lbl.setText(hex_str)

        self._shape_stroke_color = QtGui.QColor(color)
        old_a = self._shape_fill_color.alpha()
        self._shape_fill_color = QtGui.QColor(color.red(), color.green(), color.blue(), old_a)

        st_s = f"background: {color.name()}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.4);"
        st_f = f"background: {self._shape_fill_color.name()}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.4);"
        for b_s, b_f in [(self.btn_shape_stroke_col_h, self.btn_shape_fill_col_h), (self.btn_shape_stroke_col_v, self.btn_shape_fill_col_v)]:
            b_s.setStyleSheet(st_s)
            b_f.setStyleSheet(st_f)

        self._emit_shapes_settings()

    def _apply_theme(self):
        apply_secondary_toolbar_theme(self.container)
