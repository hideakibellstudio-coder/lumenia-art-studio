"""SecondaryToolBar Options Event Handlers."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.icons import get_icon

class SecondaryToolBarHandlers:
    """Concentra os manipuladores de eventos e sincronização dos painéis da SecondaryToolBar."""

    @staticmethod
    def on_eyedrop_sample_changed(tb, idx: int, src: str):
        target = tb.cbo_sample_v if src == "h" else tb.cbo_sample_h
        target.blockSignals(True)
        target.setCurrentIndex(idx)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_eyedrop_settings(tb)

    @staticmethod
    def on_eyedrop_merged_changed(tb, val: bool, src: str):
        target = tb.btn_eye_merged_v if src == "h" else tb.btn_eye_merged_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_eyedrop_settings(tb)

    @staticmethod
    def emit_eyedrop_settings(tb):
        radius_map = {0: 0, 1: 1, 2: 2, 3: 5}
        idx = tb.cbo_sample_h.currentIndex()
        settings = {
            "sample_size": tb.cbo_sample_h.currentText(),
            "sample_radius": radius_map.get(idx, 0),
            "sample_all": tb.btn_eye_merged_h.isChecked(),
            "show_loupe": True,
        }
        tb._settings_cache["eyedrop"] = settings
        tb.settingsChanged.emit("eyedrop", settings)

    @staticmethod
    def on_bucket_tol_changed(tb, val: int, src: str):
        tb.lbl_bkt_tol_val_h.setText(f"{val}%")
        tb.lbl_bkt_tol_val_v.setText(f"{val}%")
        target = tb.slider_bkt_tol_v if src == "h" else tb.slider_bkt_tol_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_bucket_settings(tb)

    @staticmethod
    def on_bucket_exp_changed(tb, val: int, src: str):
        t = f"{val:+d}px" if val != 0 else "0px"
        tb.lbl_bkt_exp_val_h.setText(t)
        tb.lbl_bkt_exp_val_v.setText(t)
        target = tb.slider_bkt_exp_v if src == "h" else tb.slider_bkt_exp_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_bucket_settings(tb)

    @staticmethod
    def on_bucket_contig_changed(tb, val: bool, src: str):
        target = tb.btn_bkt_contig_v if src == "h" else tb.btn_bkt_contig_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_bucket_settings(tb)

    @staticmethod
    def on_bucket_merged_changed(tb, val: bool, src: str):
        target = tb.btn_bkt_merged_v if src == "h" else tb.btn_bkt_merged_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_bucket_settings(tb)

    @staticmethod
    def emit_bucket_settings(tb):
        settings = {
            "tolerance": tb.slider_bkt_tol_h.value(),
            "expansion": tb.slider_bkt_exp_h.value(),
            "contiguous": tb.btn_bkt_contig_h.isChecked(),
            "sample_all": tb.btn_bkt_merged_h.isChecked(),
        }
        tb._settings_cache["bucket"] = settings
        tb.settingsChanged.emit("bucket", settings)

    @staticmethod
    def on_wand_tol_changed(tb, val: int, src: str):
        tb.lbl_wand_tol_val_h.setText(f"{val}%")
        tb.lbl_wand_tol_val_v.setText(f"{val}%")
        target = tb.slider_wand_tol_v if src == "h" else tb.slider_wand_tol_h
        target.blockSignals(True)
        target.setValue(val)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_wand_settings(tb)

    @staticmethod
    def on_wand_contig_changed(tb, val: bool, src: str):
        target = tb.btn_wand_contig_v if src == "h" else tb.btn_wand_contig_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_wand_settings(tb)

    @staticmethod
    def on_wand_merged_changed(tb, val: bool, src: str):
        target = tb.btn_wand_merged_v if src == "h" else tb.btn_wand_merged_h
        target.blockSignals(True)
        target.setChecked(val)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_wand_settings(tb)

    @staticmethod
    def on_wand_mode_changed(tb, idx: int, src: str):
        target = tb.cbo_wand_mode_v if src == "h" else tb.cbo_wand_mode_h
        target.blockSignals(True)
        target.setCurrentIndex(idx)
        target.blockSignals(False)
        SecondaryToolBarHandlers.emit_wand_settings(tb)

    @staticmethod
    def emit_wand_settings(tb):
        settings = {
            "tolerance": tb.slider_wand_tol_h.value(),
            "contiguous": tb.btn_wand_contig_h.isChecked(),
            "sample_all": tb.btn_wand_merged_h.isChecked(),
            "mode": tb.cbo_wand_mode_h.currentIndex(),
        }
        tb._settings_cache["wand"] = settings
        tb.settingsChanged.emit("wand", settings)
