"""SymmetrySettingsPage — Symmetry tab for AdvancedGeometryDialog.

Modularized under ARCcC v2 (< 130 LOC).
"""

from typing import List, Optional
from PySide6 import QtCore, QtWidgets

from ui.core.widgets.compact_slider import CompactSlider
from ui.core.widgets.collapsible_section import CollapsibleSection
from ui.infrastructure.i18n import tr


class SymmetrySettingsPage(QtWidgets.QScrollArea):
    """Scrollable tab page configuring symmetry axes, angle and painting restrictions."""

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

        # ── Eixos & Ângulo ──
        self.sec_axes = CollapsibleSection("EIXOS & ÂNGULO", content)
        self.slider_seg = CompactSlider("Segmentos:", 2, 32, "", self.sec_axes)
        self.slider_seg.setValue(int(self._state.get("segments", 6)))
        self.slider_seg.valueChanged.connect(self._emit_changed)
        self.sec_axes.add_widget(self.slider_seg)

        self.slider_ang = CompactSlider("Ângulo:", 0, 360, "°", self.sec_axes, step=5)
        self.slider_ang.setValue(int(self._state.get("angle", 0)))
        self.slider_ang.valueChanged.connect(self._emit_changed)
        self.sec_axes.add_widget(self.slider_ang)
        lay.addWidget(self.sec_axes)

        # ── Restrições de Pintura ──
        self.sec_rest = CollapsibleSection("RESTRIÇÕES DE PINTURA", content)
        self.chk_stop = QtWidgets.QCheckBox("Parar traço no centro (Stop-at-Center)")
        self.chk_stop.setChecked(self._state.get("stop_at_center", False))
        self.chk_stop.toggled.connect(self._emit_changed)
        self.sec_rest.add_widget(self.chk_stop)

        self.chk_lock = QtWidgets.QCheckBox("Bloquear posição do centro no canvas")
        self.chk_lock.setChecked(self._state.get("locked", False))
        self.chk_lock.toggled.connect(self._emit_changed)
        self.sec_rest.add_widget(self.chk_lock)
        lay.addWidget(self.sec_rest)
        lay.addStretch()

        self.setWidget(content)

    def all_input_widgets(self) -> List[QtWidgets.QWidget]:
        return [self.slider_seg, self.slider_ang, self.chk_stop, self.chk_lock]

    def collect_state(self, state: dict) -> None:
        state["segments"] = int(self.slider_seg.value())
        state["angle"] = float(self.slider_ang.value())
        state["stop_at_center"] = self.chk_stop.isChecked()
        state["locked"] = self.chk_lock.isChecked()

    def sync_from_state(self, state: dict) -> None:
        self.slider_seg.setValue(int(state.get("segments", 6)))
        self.slider_ang.setValue(int(state.get("angle", 0)))
        self.chk_stop.setChecked(state.get("stop_at_center", False))
        self.chk_lock.setChecked(state.get("locked", False))

    def retranslate_ui(self) -> None:
        self.sec_axes.set_title(tr("geometry.adv_sec_axes", "EIXOS & ÂNGULO"))
        self.slider_seg.setPrefix(tr("geometry.adv_segments", "Segmentos:"))
        self.slider_ang.setPrefix(tr("geometry.adv_angle", "Ângulo:"))
        self.sec_rest.set_title(tr("geometry.adv_sec_rest", "RESTRIÇÕES DE PINTURA"))
        self.chk_stop.setText(tr("geometry.adv_chk_stop", "Parar traço no centro (Stop-at-Center)"))
        self.chk_lock.setText(tr("geometry.adv_chk_lock", "Bloquear posição do centro no canvas"))
