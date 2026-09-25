"""SnappingGuidesPage — Snapping & Guides tab for AdvancedGeometryDialog.

Modularized under ARCcC v2 (< 150 LOC).
"""

from typing import List, Optional
from PySide6 import QtCore, QtWidgets

from ui.core.widgets.compact_slider import CompactSlider
from ui.core.widgets.collapsible_section import CollapsibleSection
from ui.infrastructure.i18n import tr


class SnappingGuidesPage(QtWidgets.QScrollArea):
    """Scrollable tab page configuring snapping mode, sensitivity and drawing behavior."""

    changed = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, initial_state: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self._state = initial_state or {}
        self._build_ui()

    def _emit_changed(self, *_) -> None:
        self.changed.emit()

    def _build_ui(self) -> None:
        content = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(content)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(6)

        # ── Modo & Sensibilidade ──
        self.sec_snap = CollapsibleSection("MODO & SENSIBILIDADE", content)
        row_m = QtWidgets.QHBoxLayout()
        self.lbl_m = QtWidgets.QLabel("Eixo de Snap:")
        self.lbl_m.setObjectName("AdvFieldLabel")
        row_m.addWidget(self.lbl_m)

        self.combo_snap_mode = QtWidgets.QComboBox()
        self.combo_snap_mode.addItems([
            "Auto (Todas as Guias)", "Apenas Vertical (V)",
            "Apenas Horizontal (H)", "Apenas Profundidade (D)"
        ])
        mode_map = {"auto": 0, "v": 1, "h": 2, "d": 3}
        self.combo_snap_mode.setCurrentIndex(mode_map.get(self._state.get("snap_mode", "auto"), 0))
        self.combo_snap_mode.currentIndexChanged.connect(self._emit_changed)
        row_m.addWidget(self.combo_snap_mode, 1)
        self.sec_snap.add_layout(row_m)

        self.slider_sens = CompactSlider("Sensib:", 1, 50, "px", self.sec_snap)
        self.slider_sens.setValue(int(self._state.get("snap_sensitivity", 3)))
        self.slider_sens.valueChanged.connect(self._emit_changed)
        self.sec_snap.add_widget(self.slider_sens)
        lay.addWidget(self.sec_snap)

        # ── Comportamento de Desenho ──
        self.sec_draw = CollapsibleSection("COMPORTAMENTO DE DESENHO", content)
        self.chk_dynamic = QtWidgets.QCheckBox("Ativar Snap Dinâmico (Desenho Livre)")
        self.chk_dynamic.setChecked(self._state.get("snap_dynamic", True))
        self.chk_dynamic.toggled.connect(self._emit_changed)
        self.sec_draw.add_widget(self.chk_dynamic)

        self.chk_hint = QtWidgets.QCheckBox("Exibir Guia Cursor Hint (Laranja)")
        self.chk_hint.setChecked(self._state.get("show_hint", True))
        self.chk_hint.toggled.connect(self._emit_changed)
        self.sec_draw.add_widget(self.chk_hint)

        self.chk_hide = QtWidgets.QCheckBox("Ocultar guias visuais durante a pintura")
        self.chk_hide.setChecked(self._state.get("hidden", False))
        self.chk_hide.toggled.connect(self._emit_changed)
        self.sec_draw.add_widget(self.chk_hide)
        lay.addWidget(self.sec_draw)
        lay.addStretch()

        self.setWidget(content)

    def all_input_widgets(self) -> List[QtWidgets.QWidget]:
        return [self.combo_snap_mode, self.slider_sens, self.chk_dynamic, self.chk_hint, self.chk_hide]

    def collect_state(self, state: dict) -> None:
        mode_inv = {0: "auto", 1: "v", 2: "h", 3: "d"}
        state["snap_mode"] = mode_inv.get(self.combo_snap_mode.currentIndex(), "auto")
        state["snap_sensitivity"] = float(self.slider_sens.value())
        state["snap_dynamic"] = self.chk_dynamic.isChecked()
        state["show_hint"] = self.chk_hint.isChecked()
        state["hidden"] = self.chk_hide.isChecked()

    def sync_from_state(self, state: dict) -> None:
        mode_map = {"auto": 0, "v": 1, "h": 2, "d": 3}
        self.combo_snap_mode.setCurrentIndex(mode_map.get(state.get("snap_mode", "auto"), 0))
        self.slider_sens.setValue(int(state.get("snap_sensitivity", 3)))
        self.chk_dynamic.setChecked(state.get("snap_dynamic", True))
        self.chk_hint.setChecked(state.get("show_hint", True))
        self.chk_hide.setChecked(state.get("hidden", False))

    def retranslate_ui(self) -> None:
        self.sec_snap.set_title(tr("geometry.adv_sec_snap", "MODO & SENSIBILIDADE"))
        self.lbl_m.setText(tr("geometry.adv_snap_axis", "Eixo de Snap:"))
        curr_s = self.combo_snap_mode.currentIndex()
        self.combo_snap_mode.blockSignals(True)
        self.combo_snap_mode.clear()
        self.combo_snap_mode.addItems([
            tr("geometry.adv_snap_auto", "Auto (Todas as Guias)"),
            tr("geometry.adv_snap_v", "Apenas Vertical (V)"),
            tr("geometry.adv_snap_h", "Apenas Horizontal (H)"),
            tr("geometry.adv_snap_d", "Apenas Profundidade (D)")
        ])
        self.combo_snap_mode.setCurrentIndex(curr_s if curr_s >= 0 else 0)
        self.combo_snap_mode.blockSignals(False)

        self.slider_sens.setPrefix(tr("geometry.adv_sens", "Sensib:"))
        self.sec_draw.set_title(tr("geometry.adv_sec_draw", "COMPORTAMENTO DE DESENHO"))
        self.chk_dynamic.setText(tr("geometry.adv_chk_dynamic", "Ativar Snap Dinâmico (Desenho Livre)"))
        self.chk_hint.setText(tr("geometry.adv_chk_hint", "Exibir Guia Cursor Hint (Laranja)"))
        self.chk_hide.setText(tr("geometry.adv_chk_hide", "Ocultar guias visuais durante a pintura"))
