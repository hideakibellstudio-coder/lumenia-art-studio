"""SelectionToolbarHandlersMixin — Event handlers for Magic Wand, Geometric Selection, and Lasso tools.

Strictly decoupled in compliance with ARCcC v2 (< 140 LOC).
"""

from ui.core.tool_settings import normalize_tool_settings


class SelectionToolbarHandlersMixin:
    """Handlers for magic wand, rect/ellipse selection, and lasso options."""

    # ── WAND HANDLERS ──
    def _on_wand_tol_changed(self, val: int, src: str):
        if hasattr(self, "lbl_wand_tol_val_h"):
            self.lbl_wand_tol_val_h.setText(f"{val}%")
        if hasattr(self, "lbl_wand_tol_val_v"):
            self.lbl_wand_tol_val_v.setText(f"{val}%")
        for sld in (getattr(self, "slider_wand_tol_h", None), getattr(self, "slider_wand_tol_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
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
        settings = normalize_tool_settings("wand", {
            "tolerance": self.slider_wand_tol_h.value(),
            "contiguous": self.btn_wand_contig_h.isChecked(),
            "sample_all": self.btn_wand_merged_h.isChecked(),
            "mode": self.cbo_wand_mode_h.currentIndex(),
        })
        self._settings_cache["wand"] = settings
        self.settingsChanged.emit("wand", settings)

    # ── GEOM HANDLERS ──
    def _on_geom_feather_changed(self, val: int, src: str):
        if hasattr(self, "lbl_geom_feather_val_h"):
            self.lbl_geom_feather_val_h.setText(f"{val}px")
        if hasattr(self, "lbl_geom_feather_val_v"):
            self.lbl_geom_feather_val_v.setText(f"{val}px")
        for sld in (getattr(self, "slider_geom_feather_h", None), getattr(self, "slider_geom_feather_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
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
        tool = "ellipse_select" if getattr(self, "_active_tool_id", "") == "ellipse_select" else "rect_select"
        settings = normalize_tool_settings(tool, {
            "feather_px": self.slider_geom_feather_h.value(),
            "aa": self.btn_geom_aa_h.isChecked(),
            "mode": self.cbo_geom_mode_h.currentIndex(),
        })
        self._settings_cache[tool] = settings
        self.settingsChanged.emit(tool, settings)

    # ── LASSO HANDLERS ──
    def _on_lasso_feather_changed(self, val: int, src: str):
        if hasattr(self, "lbl_lasso_feather_val_h"):
            self.lbl_lasso_feather_val_h.setText(f"{val}px")
        if hasattr(self, "lbl_lasso_feather_val_v"):
            self.lbl_lasso_feather_val_v.setText(f"{val}px")
        for sld in (getattr(self, "slider_lasso_feather_h", None), getattr(self, "slider_lasso_feather_v", None)):
            if sld and hasattr(sld, "value") and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
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
        settings = normalize_tool_settings("lasso", {
            "feather_px": self.slider_lasso_feather_h.value(),
            "aa": self.btn_lasso_aa_h.isChecked(),
            "mode": self.cbo_lasso_mode_h.currentIndex(),
        })
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
