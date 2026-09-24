"""ShapeTextToolbarHandlersMixin — Event handlers for Vector Shapes and Text/Typography tools.

Strictly decoupled in compliance with ARCcC v2 (< 180 LOC).
"""

from PySide6 import QtGui, QtWidgets
from ui.core.icons import get_icon
from ui.core.i18n import tr
from ui.core.tool_settings import normalize_tool_settings


class ShapeTextToolbarHandlersMixin:
    """Handlers for shape geometry options and typography settings."""

    # ── SHAPES HANDLERS ──
    def _on_shape_type_changed(self, shape_id: str, label: str, src: str):
        target = self.shape_dropdown_v if src == "h" else self.shape_dropdown_h
        target.blockSignals(True)
        target.set_shape(shape_id, label)
        target.blockSignals(False)

        pix = get_icon(shape_id).pixmap(14, 14)
        self.lbl_shape_icon_v.setPixmap(pix)

        if shape_id == "shape_rect":
            for lbl, sld, val in [(self.lbl_shape_extra_h, self.slider_shape_extra_h, self.lbl_shape_extra_val_h),
                                  (self.lbl_shape_extra_v, self.slider_shape_extra_v, self.lbl_shape_extra_val_v)]:
                lbl.setText(tr("tool_options.radius", "Raio:"))
                lbl.show(); sld.show(); val.show()
                sld.setRange(0, 100); sld.setValue(0); val.setText("0px")
        elif shape_id in ("shape_polygon", "shape_star"):
            for lbl, sld, val in [(self.lbl_shape_extra_h, self.slider_shape_extra_h, self.lbl_shape_extra_val_h),
                                  (self.lbl_shape_extra_v, self.slider_shape_extra_v, self.lbl_shape_extra_val_v)]:
                lbl.setText(tr("tool_options.sides", "Lados:") if shape_id == "shape_polygon" else tr("tool_options.points", "Pontas:"))
                lbl.show(); sld.show(); val.show()
                sld.setRange(3, 16); sld.setValue(5); val.setText("5")
        else:
            for lbl, sld, val in [(self.lbl_shape_extra_h, self.slider_shape_extra_h, self.lbl_shape_extra_val_h),
                                  (self.lbl_shape_extra_v, self.slider_shape_extra_v, self.lbl_shape_extra_val_v)]:
                lbl.hide(); sld.hide(); val.hide()

        self._emit_shapes_settings()
        self.adjustSize()
        parent = self.parent()
        if parent and hasattr(parent, "update_toolbar_position"):
            parent.update_toolbar_position()

    def _on_shape_mode_changed(self, idx: int, src: str):
        target = self.cbo_shape_mode_v if src == "h" else self.cbo_shape_mode_h
        target.blockSignals(True)
        target.setCurrentIndex(idx)
        target.blockSignals(False)
        self._emit_shapes_settings()

    def _on_shape_stroke_changed(self, val: int, src: str):
        if hasattr(self, "lbl_shape_stroke_val_h"):
            self.lbl_shape_stroke_val_h.setText(f"{val}px")
        if hasattr(self, "lbl_shape_stroke_val_v"):
            self.lbl_shape_stroke_val_v.setText(f"{val}px")
        for sld in (getattr(self, "slider_shape_stroke_h", None),
                    getattr(self, "slider_shape_stroke_v", None),
                    getattr(self, "slider_shape_width_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
        self._emit_shapes_settings()

    _on_shape_width_changed = _on_shape_stroke_changed

    def _on_shape_fill_opac_changed(self, val: int, src: str = "h"):
        if hasattr(self, "lbl_shape_fill_opac_val_h"):
            self.lbl_shape_fill_opac_val_h.setText(f"{val}%")
        if hasattr(self, "lbl_shape_fill_opac_val_v"):
            self.lbl_shape_fill_opac_val_v.setText(f"{val}%")
        for sld in (getattr(self, "slider_shape_fill_opac_h", None),
                    getattr(self, "slider_shape_fill_opac_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
        alpha = int(val * 255 / 100)
        self._shape_fill_color.setAlpha(alpha)
        self._emit_shapes_settings()

    def _on_shape_extra_changed(self, val: int, src: str):
        st = self.shape_dropdown_h.shape_id()
        suffix = "px" if st == "shape_rect" else ""
        if hasattr(self, "lbl_shape_extra_val_h"):
            self.lbl_shape_extra_val_h.setText(f"{val}{suffix}")
        if hasattr(self, "lbl_shape_extra_val_v"):
            self.lbl_shape_extra_val_v.setText(f"{val}{suffix}")
        for sld in (getattr(self, "slider_shape_extra_h", None),
                    getattr(self, "slider_shape_extra_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
        self._emit_shapes_settings()

    def _pick_shape_stroke_color(self):
        col = QtWidgets.QColorDialog.getColor(self._shape_stroke_color, self, "Cor de Contorno")
        if col.isValid():
            self._shape_stroke_color = col
            st = f"background: {col.name()}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.4);"
            self.btn_shape_stroke_col_h.setStyleSheet(st)
            self.btn_shape_stroke_col_v.setStyleSheet(st)
            self._emit_shapes_settings()

    def _pick_shape_fill_color(self):
        col = QtWidgets.QColorDialog.getColor(self._shape_fill_color, self, "Cor de Preenchimento", QtWidgets.QColorDialog.ShowAlphaChannel)
        if col.isValid():
            self._shape_fill_color = col
            st = f"background: {col.name()}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.4);"
            self.btn_shape_fill_col_h.setStyleSheet(st)
            self.btn_shape_fill_col_v.setStyleSheet(st)
            self._emit_shapes_settings()

    def _emit_shapes_settings(self):
        draw_modes = ["both", "stroke", "fill"]
        shape_type = self.shape_dropdown_h.shape_id()
        idx_mode = self.cbo_shape_mode_h.currentIndex()

        draw_mode = draw_modes[idx_mode] if 0 <= idx_mode < len(draw_modes) else "both"
        fill_opac = (self.slider_shape_fill_opac_h.value() / 100.0)

        settings = normalize_tool_settings("shapes", {
            "shape_type": shape_type,
            "draw_mode": draw_mode,
            "stroke_width": self.slider_shape_stroke_h.value(),
            "stroke_color": self._shape_stroke_color,
            "fill_color": self._shape_fill_color,
            "fill_opacity": fill_opac,
            "corner_radius": self.slider_shape_extra_h.value() if shape_type == "shape_rect" else 0,
            "polygon_sides": self.slider_shape_extra_h.value() if shape_type == "shape_polygon" else 5,
            "star_points": self.slider_shape_extra_h.value() if shape_type == "shape_star" else 5,
        })
        self._tool_state.update_options("shapes", settings)

    # ── TEXT HANDLERS ──
    def _on_text_font_changed(self, font: QtGui.QFont, src: str):
        for cbo in (getattr(self, "cbo_text_font_h", None), getattr(self, "cbo_text_font_v", None)):
            if cbo and hasattr(cbo, "setCurrentFont"):
                cbo.blockSignals(True)
                cbo.setCurrentFont(font)
                cbo.blockSignals(False)
        self._emit_text_settings()

    def _on_text_size_changed(self, val: int, src: str):
        for spn in (getattr(self, "spin_text_size_h", None), getattr(self, "spin_text_size_v", None)):
            if spn and hasattr(spn, "value") and spn.value() != val:
                spn.blockSignals(True)
                spn.setValue(val)
                spn.blockSignals(False)
        self._emit_text_settings()

    def _on_text_bold_toggled(self, val: bool, src: str):
        for btn in (getattr(self, "btn_text_bold_h", None), getattr(self, "btn_text_bold_v", None)):
            if btn and hasattr(btn, "setChecked"):
                btn.blockSignals(True)
                btn.setChecked(val)
                btn.blockSignals(False)
        self._emit_text_settings()

    def _on_text_italic_toggled(self, val: bool, src: str):
        for btn in (getattr(self, "btn_text_italic_h", None), getattr(self, "btn_text_italic_v", None)):
            if btn and hasattr(btn, "setChecked"):
                btn.blockSignals(True)
                btn.setChecked(val)
                btn.blockSignals(False)
        self._emit_text_settings()

    def _on_text_underline_toggled(self, val: bool, src: str):
        for btn in (getattr(self, "btn_text_underline_h", None), getattr(self, "btn_text_underline_v", None)):
            if btn and hasattr(btn, "setChecked"):
                btn.blockSignals(True)
                btn.setChecked(val)
                btn.blockSignals(False)
        self._emit_text_settings()

    def _on_text_align_changed(self, align: str, src: str):
        self.btn_text_align_l_h.setChecked(align == "left")
        self.btn_text_align_c_h.setChecked(align == "center")
        self.btn_text_align_r_h.setChecked(align == "right")

        self.btn_text_align_l_v.setChecked(align == "left")
        self.btn_text_align_c_v.setChecked(align == "center")
        self.btn_text_align_r_v.setChecked(align == "right")

        self._emit_text_settings()

    def _pick_text_color(self):
        col = QtWidgets.QColorDialog.getColor(self._text_color, self, "Cor do Texto", QtWidgets.QColorDialog.ShowAlphaChannel)
        if col.isValid():
            self._text_color = col
            st = f"background: {col.name()}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.4);"
            self.btn_text_color_h.setStyleSheet(st)
            self.btn_text_color_v.setStyleSheet(st)
            self._emit_text_settings()

    def _on_commit_text_clicked(self):
        self.commitTextRequested.emit()
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget") and hasattr(parent.canvas_widget, "commit_text_overlay"):
            parent.canvas_widget.commit_text_overlay()

    def _on_cancel_text_clicked(self):
        self.cancelTextRequested.emit()
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget") and hasattr(parent.canvas_widget, "cancel_text_overlay"):
            parent.canvas_widget.cancel_text_overlay()

    def _emit_text_settings(self):
        align = "left"
        if self.btn_text_align_c_h.isChecked():
            align = "center"
        elif self.btn_text_align_r_h.isChecked():
            align = "right"

        settings = normalize_tool_settings("text", {
            "font_family": self.cbo_text_font_h.currentFont().family(),
            "font_size": self.spin_text_size_h.value(),
            "bold": self.btn_text_bold_h.isChecked(),
            "italic": self.btn_text_italic_h.isChecked(),
            "underline": self.btn_text_underline_h.isChecked(),
            "align": align,
            "color": self._text_color,
        })
        self._tool_state.update_options("text", settings)

        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget") and hasattr(parent.canvas_widget, "set_text_settings"):
            parent.canvas_widget.set_text_settings(settings)
