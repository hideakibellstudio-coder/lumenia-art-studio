"""SecondaryToolBar — Floating contextual options bar for active tool."""

from __future__ import annotations

from typing import Optional, Dict
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.icons import get_icon
from ui.core.tool_settings import default_tool_settings

from .dynamic_stacked_widget import DynamicStackedWidget
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
            **{tool: default_tool_settings(tool) for tool in (
                "eyedrop", "bucket", "wand", "rect_select", "ellipse_select", "lasso", "transform", "smudge"
            )},
            "shapes": default_tool_settings("shapes"),
            "text": default_tool_settings("text"),
        }

        self._build_ui()
        self._apply_theme()
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(lambda _: self._apply_theme())

        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

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
        pass

    def retranslate_ui(self) -> None:
        """Atualiza dinamicamente rótulos, comboboxes e tooltips da barra secundária."""
        from ui.core.i18n import tr
        # Eyedrop
        if hasattr(self, "cbo_sample_h"):
            for cbo in (self.cbo_sample_h, self.cbo_sample_v):
                idx = max(0, cbo.currentIndex())
                cbo.blockSignals(True)
                cbo.clear()
                cbo.addItems([
                    tr("tool_options.sample_1x1", "1x1 Ponto"),
                    tr("tool_options.sample_3x3", "3x3 Média"),
                    tr("tool_options.sample_5x5", "5x5 Média"),
                    "11x11 " + tr("tool_options.sample_3x3", "Média").split()[-1]
                ])
                cbo.setCurrentIndex(idx)
                cbo.blockSignals(False)
            self.btn_eye_merged_h.setText(tr("tool_options.sample_all_layers", "Todas Camadas"))
            self.btn_eye_merged_v.setText(tr("tool_options.sample_all_layers", "Todas Camadas"))

        # Bucket & Wand
        if hasattr(self, "btn_bkt_contig_h"):
            self.btn_bkt_contig_h.setText(tr("tool_options.contiguous", "Contíguo"))
            self.btn_bkt_contig_v.setText(tr("tool_options.contiguous", "Contíguo"))
            self.btn_bkt_merged_h.setText(tr("tool_options.sample_all_layers", "Todas Camadas"))
            self.btn_bkt_merged_v.setText(tr("tool_options.sample_all_layers", "Todas Camadas"))

        if hasattr(self, "btn_wand_contig_h"):
            self.btn_wand_contig_h.setText(tr("tool_options.contiguous", "Contíguo"))
            self.btn_wand_contig_v.setText(tr("tool_options.contiguous", "Contíguo"))
            self.btn_wand_merged_h.setText(tr("tool_options.sample_all_layers", "Todas Camadas"))
            self.btn_wand_merged_v.setText(tr("tool_options.sample_all_layers", "Todas Camadas"))

        # Transform & Text
        if hasattr(self, "btn_trans_commit_h"):
            self.btn_trans_commit_h.setText(f"✔ {tr('common.apply', 'Aplicar')}")
            self.btn_trans_commit_v.setText(f"✔ {tr('common.apply', 'Aplicar')}")
            self.btn_trans_cancel_h.setText(f"✖ {tr('common.cancel', 'Cancelar')}")
            self.btn_trans_cancel_v.setText(f"✖ {tr('common.cancel', 'Cancelar')}")
            self.btn_trans_flip_h_h.setText(tr("transform.flip_h", "Espelhar H"))
            self.btn_trans_flip_h_v.setText(tr("transform.flip_h", "Espelhar H"))
            self.btn_trans_flip_v_h.setText(tr("transform.flip_v", "Espelhar V"))
            self.btn_trans_flip_v_v.setText(tr("transform.flip_v", "Espelhar V"))
            self.btn_trans_rot_90_h.setText(tr("transform.rotate_90", "Girar 90°"))
            self.btn_trans_rot_90_v.setText(tr("transform.rotate_90", "Girar 90°"))
            self.btn_trans_aspect_h.setText(tr("transform.lock_aspect", "Travar Proporção"))
            self.btn_trans_commit_h.setToolTip(tr("tool_options.commit_text", "Confirmar"))
            self.btn_trans_cancel_h.setToolTip(tr("tool_options.cancel_text", "Cancelar"))
            self.btn_trans_aspect_h.setToolTip(tr("tool_options.lock_aspect", "Travar Proporções"))
            if hasattr(self, "lbl_trans_title_v"):
                self.lbl_trans_title_v.setText(tr("transform.title", "TRANSFORMAÇÃO"))
            if hasattr(self, "lbl_trans_interp_h"):
                self.lbl_trans_interp_h.setText(tr("transform.interp", "Interp:"))
            if hasattr(self, "cbo_trans_interp_h"):
                idx = max(0, self.cbo_trans_interp_h.currentIndex())
                self.cbo_trans_interp_h.blockSignals(True)
                self.cbo_trans_interp_h.clear()
                self.cbo_trans_interp_h.addItems([
                    tr("transform.interp_nearest", "Mais Próximo"),
                    tr("transform.interp_bilinear", "Bilinear"),
                    tr("transform.interp_bicubic", "Bicúbica")
                ])
                self.cbo_trans_interp_h.setCurrentIndex(idx)
                self.cbo_trans_interp_h.blockSignals(False)

        if hasattr(self, "btn_commit_text_h"):
            self.btn_commit_text_h.setToolTip(tr("tool_options.commit_text", "Confirmar"))
            self.btn_cancel_text_h.setToolTip(tr("tool_options.cancel_text", "Cancelar"))
        if hasattr(self, "btn_text_commit_h"):
            self.btn_text_commit_h.setText(tr("tool_options.insert_text", "Inserir"))
            self.btn_text_align_l_h.setText(tr("tool_options.align_left", "Esq"))
            self.btn_text_align_c_h.setText(tr("tool_options.align_center", "Cen"))
            self.btn_text_align_r_h.setText(tr("tool_options.align_right", "Dir"))

        # Shapes (Primitivas)
        if hasattr(self, "shape_dropdown_h"):
            self.shape_dropdown_h.retranslate_ui()
        if hasattr(self, "shape_dropdown_v"):
            self.shape_dropdown_v.retranslate_ui()
        if hasattr(self, "cbo_shape_mode_h"):
            modes = [
                tr("tool_options.shapes_stroke_and_fill", "Contorno & Preenchimento"),
                tr("tool_options.shapes_stroke_only", "Apenas Contorno"),
                tr("tool_options.shapes_fill_only", "Apenas Preenchimento")
            ]
            for cbo in (self.cbo_shape_mode_h, self.cbo_shape_mode_v):
                idx = max(0, cbo.currentIndex())
                cbo.blockSignals(True)
                cbo.clear()
                cbo.addItems(modes)
                cbo.setCurrentIndex(idx)
                cbo.blockSignals(False)

        if hasattr(self, "lbl_shape_stroke_h"):
            self.lbl_shape_stroke_h.setText(tr("tool_options.stroke", "Traço:"))
        if hasattr(self, "lbl_shape_border_h"):
            self.lbl_shape_border_h.setText(tr("tool_options.border", "Borda:"))
        if hasattr(self, "lbl_shape_border_v"):
            self.lbl_shape_border_v.setText(tr("tool_options.border", "Borda:"))
        if hasattr(self, "lbl_shape_fill_h"):
            self.lbl_shape_fill_h.setText(tr("tool_options.fill", "Fundo:"))
        if hasattr(self, "lbl_shape_fill_v"):
            self.lbl_shape_fill_v.setText(tr("tool_options.fill", "Fundo:"))
        if hasattr(self, "lbl_shape_opac_h"):
            self.lbl_shape_opac_h.setText(tr("tool_options.opacity", "Opac:"))
        if hasattr(self, "slider_shape_width_v"):
            self.slider_shape_width_v.setPrefix(tr("tool_options.stroke", "Traço:"))
        if hasattr(self, "slider_shape_fill_opac_v"):
            self.slider_shape_fill_opac_v.setPrefix(tr("tool_options.fill_opacity", "Opac. Fundo:"))
        if hasattr(self, "lbl_shape_title_v"):
            self.lbl_shape_title_v.setText(tr("tool_options.shapes_title", "FORMAS VETORIAIS"))

        if hasattr(self, "lbl_shape_extra_h"):
            if self._active_tool_id == "shape_rect":
                self.lbl_shape_extra_h.setText(tr("tool_options.radius", "Raio:"))
                self.lbl_shape_extra_v.setText(tr("tool_options.radius", "Raio:"))
            elif self._active_tool_id in ("shape_polygon", "shape_star"):
                txt = tr("tool_options.sides", "Lados:") if self._active_tool_id == "shape_polygon" else tr("tool_options.points", "Pontas:")
                self.lbl_shape_extra_h.setText(txt)
                self.lbl_shape_extra_v.setText(txt)

        # Geom & Lasso
        if hasattr(self, "cbo_geom_mode_h"):
            modes = [
                tr("selection.new", "Nova Seleção"),
                tr("selection.add", "Adicionar (+)"),
                tr("selection.subtract", "Subtrair (-)"),
                tr("selection.intersect", "Interseção")
            ]
            for cbo in (self.cbo_geom_mode_h, self.cbo_geom_mode_v):
                idx = max(0, cbo.currentIndex())
                cbo.blockSignals(True)
                cbo.clear()
                cbo.addItems(modes)
                cbo.setCurrentIndex(idx)
                cbo.blockSignals(False)
            self.btn_geom_deselect_h.setText(f" {tr('selection.deselect', 'Desmarcar')}")
            self.btn_geom_deselect_v.setText(f" {tr('selection.deselect', 'Desmarcar')}")
            self.btn_geom_aa_h.setText(tr("selection.anti_alias", "Anti-Alias"))
            self.btn_geom_aa_v.setText(tr("selection.anti_alias", "Anti-Alias"))

        if hasattr(self, "cbo_lasso_mode_h"):
            modes = [
                tr("selection.new", "Nova Seleção"),
                tr("selection.add", "Adicionar (+)"),
                tr("selection.subtract", "Subtrair (-)"),
                tr("selection.intersect", "Interseção")
            ]
            for cbo in (self.cbo_lasso_mode_h, self.cbo_lasso_mode_v):
                idx = max(0, cbo.currentIndex())
                cbo.blockSignals(True)
                cbo.clear()
                cbo.addItems(modes)
                cbo.setCurrentIndex(idx)
                cbo.blockSignals(False)
            self.btn_lasso_deselect_h.setText(f" {tr('selection.deselect', 'Desmarcar')}")
            self.btn_lasso_deselect_v.setText(f" {tr('selection.deselect', 'Desmarcar')}")
            self.btn_lasso_aa_h.setText(tr("selection.anti_alias", "Anti-Alias"))
            self.btn_lasso_aa_v.setText(tr("selection.anti_alias", "Anti-Alias"))
