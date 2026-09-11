"""BrushFillToolbarHandlersMixin — Event handlers for Smudge, Eyedropper, Bucket, and Transform tools.

Strictly decoupled in compliance with ARCcC v2 (< 160 LOC).
"""

from ui.core.tool_settings import normalize_tool_settings


class BrushFillToolbarHandlersMixin:
    """Handlers for smudge parameters, eyedrop sampling, bucket fill, and free transform."""

    # ── SMUDGE HANDLERS ──
    def _on_smudge_stretch_changed(self, val: int, src: str):
        if hasattr(self, "lbl_smudge_stretch_val_h"):
            self.lbl_smudge_stretch_val_h.setText(f"{val}%")
        if hasattr(self, "lbl_smudge_stretch_val_v"):
            self.lbl_smudge_stretch_val_v.setText(f"{val}%")
        for sld in (getattr(self, "slider_smudge_stretch_h", None), getattr(self, "slider_smudge_stretch_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
        self._emit_smudge_settings()

    def _on_smudge_pickup_changed(self, val: int, src: str):
        if hasattr(self, "lbl_smudge_pickup_val_h"):
            self.lbl_smudge_pickup_val_h.setText(f"{val}%")
        if hasattr(self, "lbl_smudge_pickup_val_v"):
            self.lbl_smudge_pickup_val_v.setText(f"{val}%")
        for sld in (getattr(self, "slider_smudge_pickup_h", None), getattr(self, "slider_smudge_pickup_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
        self._emit_smudge_settings()

    def _on_smudge_mix_changed(self, val: int, src: str):
        if hasattr(self, "lbl_smudge_mix_val_h"):
            self.lbl_smudge_mix_val_h.setText(f"{val}%")
        if hasattr(self, "lbl_smudge_mix_val_v"):
            self.lbl_smudge_mix_val_v.setText(f"{val}%")
        for sld in (getattr(self, "slider_smudge_mix_h", None), getattr(self, "slider_smudge_mix_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
        self._emit_smudge_settings()

    def _emit_smudge_settings(self):
        settings = normalize_tool_settings("smudge", {
            "smudge_stretch": self.slider_smudge_stretch_h.value() / 100.0,
            "color_pickup": self.slider_smudge_pickup_h.value() / 100.0,
            "mix_ratio": self.slider_smudge_mix_h.value() / 100.0,
        })
        self._settings_cache["smudge"] = settings
        self.settingsChanged.emit("smudge", settings)

        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            for parameter, value in settings.items():
                backend.set_brush_param("smudge", parameter, value)

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
        settings = normalize_tool_settings("eyedrop", {
            "sample_size": self.cbo_sample_h.currentText(),
            "sample_radius": radius_map.get(idx, 0),
            "sample_all": self.btn_eye_merged_h.isChecked(),
            "show_loupe": True,
        })
        self._settings_cache["eyedrop"] = settings
        self.settingsChanged.emit("eyedrop", settings)

    # ── BUCKET HANDLERS ──
    def _on_bucket_tol_changed(self, val: int, src: str):
        if hasattr(self, "lbl_bkt_tol_val_h"):
            self.lbl_bkt_tol_val_h.setText(f"{val}%")
        if hasattr(self, "lbl_bkt_tol_val_v"):
            self.lbl_bkt_tol_val_v.setText(f"{val}%")
        for sld in (getattr(self, "slider_bkt_tol_h", None), getattr(self, "slider_bkt_tol_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
        self._emit_bucket_settings()

    def _on_bucket_exp_changed(self, val: int, src: str):
        t = f"{val:+d}px" if val != 0 else "0px"
        if hasattr(self, "lbl_bkt_exp_val_h"):
            self.lbl_bkt_exp_val_h.setText(t)
        if hasattr(self, "lbl_bkt_exp_val_v"):
            self.lbl_bkt_exp_val_v.setText(t)
        for sld in (getattr(self, "slider_bkt_exp_h", None), getattr(self, "slider_bkt_exp_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
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
        settings = normalize_tool_settings("bucket", {
            "tolerance": self.slider_bkt_tol_h.value(),
            "expand_px": self.slider_bkt_exp_h.value(),
            "contiguous": self.btn_bkt_contig_h.isChecked(),
            "sample_all": self.btn_bkt_merged_h.isChecked(),
        })
        self._settings_cache["bucket"] = settings
        self.settingsChanged.emit("bucket", settings)

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
        settings = normalize_tool_settings("transform", {
            "interp_mode": self.cbo_trans_interp_h.currentIndex(),
            "lock_aspect": self.btn_trans_aspect_h.isChecked(),
        })
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
