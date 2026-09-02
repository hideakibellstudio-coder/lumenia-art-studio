"""SecondaryToolbarHandlersMixin — Event and signal handlers for SecondaryToolBar options."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.icons import get_icon

class SecondaryToolbarHandlersMixin:
    """Mixin com todos os manipuladores de eventos e emissões de configurações de ferramentas."""

    # ── SMUDGE HANDLERS ──
    def _on_smudge_stretch_changed(self, val: int, src: str):
        self.lbl_smudge_stretch_val_h.setText(f"{val}%")
        self.lbl_smudge_stretch_val_v.setText(f"{val}%")
        target = self.slider_smudge_stretch_v if src == "h" else self.slider_smudge_stretch_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_smudge_settings()

    def _on_smudge_pickup_changed(self, val: int, src: str):
        self.lbl_smudge_pickup_val_h.setText(f"{val}%")
        self.lbl_smudge_pickup_val_v.setText(f"{val}%")
        target = self.slider_smudge_pickup_v if src == "h" else self.slider_smudge_pickup_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_smudge_settings()

    def _on_smudge_mix_changed(self, val: int, src: str):
        self.lbl_smudge_mix_val_h.setText(f"{val}%")
        self.lbl_smudge_mix_val_v.setText(f"{val}%")
        target = self.slider_smudge_mix_v if src == "h" else self.slider_smudge_mix_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_smudge_settings()

    def _emit_smudge_settings(self):
        settings = {
            "smudge_stretch": self.slider_smudge_stretch_h.value() / 100.0,
            "color_pickup": self.slider_smudge_pickup_h.value() / 100.0,
            "mix_ratio": self.slider_smudge_mix_h.value() / 100.0,
        }
        self._settings_cache["smudge"] = settings
        self.settingsChanged.emit("smudge", settings)

        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_brush_profile"):
            prof = backend.get_brush_profile()
            if hasattr(prof, "smudge_params"):
                prof.smudge_params.smudge_stretch = settings["smudge_stretch"]
                prof.smudge_params.color_pickup = settings["color_pickup"]
                prof.smudge_params.mix_ratio = settings["mix_ratio"]

    # ── SHAPES HANDLERS ──
    def _on_shape_type_changed(self, shape_id: str, label: str, src: str):
        target = self.shape_dropdown_v if src == "h" else self.shape_dropdown_h
        target.blockSignals(True)
        target.set_shape(shape_id, label)
        target.blockSignals(False)

        pix = get_icon(shape_id).pixmap(14, 14)
        self.lbl_shape_icon_v.setPixmap(pix)

        from ui.core.i18n import tr
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
        self.lbl_shape_stroke_val_h.setText(f"{val}px")
        self.lbl_shape_stroke_val_v.setText(f"{val}px")
        target = self.slider_shape_stroke_v if src == "h" else self.slider_shape_stroke_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_shapes_settings()

    def _on_shape_fill_opac_changed(self, val: int, src: str = "h"):
        self.lbl_shape_fill_opac_val_h.setText(f"{val}%")
        self.lbl_shape_fill_opac_val_v.setText(f"{val}%")
        target = self.slider_shape_fill_opac_v if src == "h" else self.slider_shape_fill_opac_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        alpha = int(val * 255 / 100)
        self._shape_fill_color.setAlpha(alpha)
        self._emit_shapes_settings()

    def _on_shape_extra_changed(self, val: int, src: str):
        st = self.shape_dropdown_h.shape_id()
        suffix = "px" if st == "shape_rect" else ""
        self.lbl_shape_extra_val_h.setText(f"{val}{suffix}")
        self.lbl_shape_extra_val_v.setText(f"{val}{suffix}")
        target = self.slider_shape_extra_v if src == "h" else self.slider_shape_extra_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
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

        settings = {
            "shape_type": shape_type,
            "draw_mode": draw_mode,
            "stroke_width": self.slider_shape_stroke_h.value(),
            "stroke_color": self._shape_stroke_color,
            "fill_color": self._shape_fill_color,
            "fill_opacity": fill_opac,
            "corner_radius": self.slider_shape_extra_h.value() if shape_type == "shape_rect" else 0,
            "polygon_sides": self.slider_shape_extra_h.value() if shape_type == "shape_polygon" else 5,
            "star_points": self.slider_shape_extra_h.value() if shape_type == "shape_star" else 5,
        }
        self._settings_cache["shapes"] = settings
        self.settingsChanged.emit("shapes", settings)

        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget") and hasattr(parent.canvas_widget, "set_shape_settings"):
            parent.canvas_widget.set_shape_settings(settings)

    # ── TEXT HANDLERS ──
    def _on_text_font_changed(self, font: QtGui.QFont, src: str):
        target = self.cbo_text_font_v if src == "h" else self.cbo_text_font_h
        target.blockSignals(True)
        target.setCurrentFont(font)
        target.blockSignals(False)
        self._emit_text_settings()

    def _on_text_size_changed(self, val: int, src: str):
        target = self.spin_text_size_v if src == "h" else self.spin_text_size_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        self._emit_text_settings()

    def _on_text_bold_toggled(self, val: bool, src: str):
        target = self.btn_text_bold_v if src == "h" else self.btn_text_bold_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_text_settings()

    def _on_text_italic_toggled(self, val: bool, src: str):
        target = self.btn_text_italic_v if src == "h" else self.btn_text_italic_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        self._emit_text_settings()

    def _on_text_underline_toggled(self, val: bool, src: str):
        target = self.btn_text_underline_v if src == "h" else self.btn_text_underline_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
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

        settings = {
            "font_family": self.cbo_text_font_h.currentFont().family(),
            "font_size": self.spin_text_size_h.value(),
            "bold": self.btn_text_bold_h.isChecked(),
            "italic": self.btn_text_italic_h.isChecked(),
            "underline": self.btn_text_underline_h.isChecked(),
            "align": align,
            "color": self._text_color
        }
        self._settings_cache["text"] = settings
        self.settingsChanged.emit("text", settings)

        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget") and hasattr(parent.canvas_widget, "set_text_settings"):
            parent.canvas_widget.set_text_settings(settings)

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
        tool = "ellipse_select" if getattr(self, "_active_tool_id", "") == "ellipse_select" else "rect_select"
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

    # ── SMUDGE PRESET HANDLER ──
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

