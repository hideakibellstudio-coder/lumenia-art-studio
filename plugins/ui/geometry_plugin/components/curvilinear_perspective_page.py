"""CurvilinearPerspectivePage — 6P Curvilinear Perspective tab for AdvancedGeometryDialog.

Modularized under ARCcC v2 (< 200 LOC).
"""

from typing import Callable, List, Optional
from PySide6 import QtCore, QtWidgets

from ui.core.widgets.compact_slider import CompactSlider
from ui.core.widgets.collapsible_section import CollapsibleSection
from ui.core.i18n import tr

# Itens do combo de densidade, em graus entre linhas da grade.
_DENSITIES = (15.0, 30.0, 45.0)


def _density_index(density) -> int:
    return _DENSITIES.index(density) if density in _DENSITIES else 1


class CurvilinearPerspectivePage(QtWidgets.QScrollArea):
    """Scrollable tab page configuring 3D camera distortion and curvilinear grid."""

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

        # ── Câmera 3D & Distorção ──
        self.sec_cam = CollapsibleSection("CÂMERA 3D & DISTORÇÃO", content)
        self.slider_yaw = CompactSlider("Yaw:", 0, 360, "°", self.sec_cam, step=5)
        self.slider_yaw.setValue(int(self._state.get("yaw", 0)))
        self.slider_yaw.valueChanged.connect(self._emit_changed)
        self.sec_cam.add_widget(self.slider_yaw)

        self.slider_pitch = CompactSlider("Pitch:", -90, 90, "°", self.sec_cam, step=5)
        self.slider_pitch.setValue(int(self._state.get("pitch", 0)))
        self.slider_pitch.valueChanged.connect(self._emit_changed)
        self.sec_cam.add_widget(self.slider_pitch)

        self.slider_fov = CompactSlider("FOV:", 10, 180, "°", self.sec_cam, step=5)
        self.slider_fov.setValue(int(self._state.get("fov", 130)))
        self.slider_fov.valueChanged.connect(self._emit_changed)
        self.sec_cam.add_widget(self.slider_fov)
        lay.addWidget(self.sec_cam)

        # ── Grade Curvilínea & Elementos ──
        self.sec_grid = CollapsibleSection("GRADE CURVILÍNEA & ELEMENTOS", content)
        row_d = QtWidgets.QHBoxLayout()
        self.lbl_d = QtWidgets.QLabel("Densidade:")
        self.lbl_d.setObjectName("AdvFieldLabel")
        row_d.addWidget(self.lbl_d)
        self.combo_density = QtWidgets.QComboBox()
        self.combo_density.addItems(["Fina (15°)", "Média (30°)", "Esparsa (45°)"])
        self.combo_density.setCurrentIndex(_density_index(self._state.get("density", 30.0)))
        self.combo_density.currentIndexChanged.connect(self._emit_changed)
        row_d.addWidget(self.combo_density, 1)
        self.sec_grid.add_layout(row_d)

        row_a = QtWidgets.QHBoxLayout()
        self.lbl_a = QtWidgets.QLabel("Proporção:")
        self.lbl_a.setObjectName("AdvFieldLabel")
        row_a.addWidget(self.lbl_a)
        self.combo_aspect = QtWidgets.QComboBox()
        self.combo_aspect.addItems(["16:9", "2.35:1"])
        self.combo_aspect.setCurrentText(self._state.get("aspect_ratio", "16:9"))
        self.combo_aspect.currentIndexChanged.connect(self._emit_changed)
        row_a.addWidget(self.combo_aspect, 1)
        self.sec_grid.add_layout(row_a)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(4)
        self.chk_ring = QtWidgets.QCheckBox("Limites (180°)")
        self.chk_straight_v = QtWidgets.QCheckBox("Verticais Retas")
        self.chk_v = QtWidgets.QCheckBox("Grade Vert. (V)")
        self.chk_vps = QtWidgets.QCheckBox("Pontos Fuga (VPs)")
        self.chk_h = QtWidgets.QCheckBox("Grade Horiz. (H)")
        self.chk_letterbox = QtWidgets.QCheckBox("Letterbox")
        self.chk_d = QtWidgets.QCheckBox("Grade Prof. (D)")
        self.chk_cube = QtWidgets.QCheckBox("Cubo 3D")
        self.chk_ground = QtWidgets.QCheckBox("Grade Chão")
        self.chk_ceiling = QtWidgets.QCheckBox("Grade Teto")
        self.chk_ground_v = QtWidgets.QCheckBox("Verticais Chão")
        self.chk_ceiling_v = QtWidgets.QCheckBox("Verticais Teto")

        chk_items = [
            (self.chk_ring, "show_ring", True, 0, 0), (self.chk_straight_v, "show_straight_verticals", False, 0, 1),
            (self.chk_v, "show_v", True, 1, 0), (self.chk_vps, "show_vps", False, 1, 1),
            (self.chk_h, "show_h", True, 2, 0), (self.chk_letterbox, "show_letterbox", False, 2, 1),
            (self.chk_d, "show_d", True, 3, 0), (self.chk_cube, "show_cube", False, 3, 1),
            (self.chk_ground, "show_ground", False, 4, 0), (self.chk_ceiling, "show_ceiling", False, 4, 1),
            (self.chk_ground_v, "show_ground_verticals", False, 5, 0), (self.chk_ceiling_v, "show_ceiling_verticals", False, 5, 1),
        ]
        for chk, key, def_val, r, c in chk_items:
            chk.setChecked(self._state.get(key, def_val))
            chk.toggled.connect(self._emit_changed)
            grid.addWidget(chk, r, c)

        self.sec_grid.add_layout(grid)
        lay.addWidget(self.sec_grid)
        lay.addStretch()

        self.setWidget(content)

    def all_input_widgets(self) -> List[QtWidgets.QWidget]:
        return [
            self.slider_yaw, self.slider_pitch, self.slider_fov,
            self.combo_density, self.combo_aspect,
            self.chk_ring, self.chk_straight_v, self.chk_v, self.chk_vps,
            self.chk_h, self.chk_letterbox, self.chk_d, self.chk_cube,
            self.chk_ground, self.chk_ceiling, self.chk_ground_v, self.chk_ceiling_v,
        ]

    def collect_state(self, state: dict) -> None:
        state["yaw"] = float(self.slider_yaw.value())
        state["pitch"] = float(self.slider_pitch.value())
        state["fov"] = float(self.slider_fov.value())
        state["density"] = _DENSITIES[max(0, self.combo_density.currentIndex())]

        state["show_ring"] = self.chk_ring.isChecked()
        state["show_straight_verticals"] = self.chk_straight_v.isChecked()
        state["show_v"] = self.chk_v.isChecked()
        state["show_vps"] = self.chk_vps.isChecked()
        state["show_h"] = self.chk_h.isChecked()
        state["show_letterbox"] = self.chk_letterbox.isChecked()
        state["show_d"] = self.chk_d.isChecked()
        state["show_cube"] = self.chk_cube.isChecked()
        state["show_ground"] = self.chk_ground.isChecked()
        state["show_ceiling"] = self.chk_ceiling.isChecked()
        state["show_ground_verticals"] = self.chk_ground_v.isChecked()
        state["show_ceiling_verticals"] = self.chk_ceiling_v.isChecked()
        state["aspect_ratio"] = self.combo_aspect.currentText()

    def sync_from_state(self, state: dict) -> None:
        self.slider_yaw.setValue(int(state.get("yaw", 0)))
        self.slider_pitch.setValue(int(state.get("pitch", 0)))
        self.slider_fov.setValue(int(state.get("fov", 130)))
        self.combo_density.setCurrentIndex(_density_index(state.get("density", 30.0)))
        self.chk_ring.setChecked(state.get("show_ring", True))
        self.chk_straight_v.setChecked(state.get("show_straight_verticals", False))
        self.chk_v.setChecked(state.get("show_v", True))
        self.chk_vps.setChecked(state.get("show_vps", False))
        self.chk_h.setChecked(state.get("show_h", True))
        self.chk_letterbox.setChecked(state.get("show_letterbox", False))
        self.chk_d.setChecked(state.get("show_d", True))
        self.chk_cube.setChecked(state.get("show_cube", False))
        self.chk_ground.setChecked(state.get("show_ground", False))
        self.chk_ceiling.setChecked(state.get("show_ceiling", False))
        self.chk_ground_v.setChecked(state.get("show_ground_verticals", False))
        self.chk_ceiling_v.setChecked(state.get("show_ceiling_verticals", False))
        self.combo_aspect.setCurrentText(state.get("aspect_ratio", "16:9"))

    def retranslate_ui(self) -> None:
        self.sec_cam.set_title(tr("geometry.adv_sec_camera", "CÂMERA 3D & DISTORÇÃO"))
        self.slider_yaw.setPrefix(tr("geometry.adv_yaw", "Yaw:"))
        self.slider_pitch.setPrefix(tr("geometry.adv_pitch", "Pitch:"))
        self.slider_fov.setPrefix(tr("geometry.adv_fov", "FOV:"))

        self.sec_grid.set_title(tr("geometry.adv_sec_grid", "GRADE CURVILÍNEA & ELEMENTOS"))
        self.lbl_d.setText(tr("geometry.adv_density", "Densidade:"))
        curr_d = self.combo_density.currentIndex()
        self.combo_density.blockSignals(True)
        self.combo_density.clear()
        self.combo_density.addItems([
            tr("geometry.adv_density_fine", "Fina (15°)"),
            tr("geometry.adv_density_med", "Média (30°)"),
            tr("geometry.adv_density_sparse", "Esparsa (45°)")
        ])
        self.combo_density.setCurrentIndex(curr_d if curr_d >= 0 else 1)
        self.combo_density.blockSignals(False)

        self.lbl_a.setText(tr("geometry.adv_aspect", "Proporção:"))
        self.chk_ring.setText(tr("geometry.adv_chk_ring", "Limites (180°)"))
        self.chk_straight_v.setText(tr("geometry.adv_chk_straight_v", "Verticais Retas"))
        self.chk_v.setText(tr("geometry.adv_chk_v", "Grade Vert. (V)"))
        self.chk_vps.setText(tr("geometry.adv_chk_vps", "Pontos Fuga (VPs)"))
        self.chk_h.setText(tr("geometry.adv_chk_h", "Grade Horiz. (H)"))
        self.chk_letterbox.setText(tr("geometry.adv_chk_letterbox", "Letterbox"))
        self.chk_d.setText(tr("geometry.adv_chk_d", "Grade Prof. (D)"))
        self.chk_cube.setText(tr("geometry.adv_chk_cube", "Cubo 3D"))
        self.chk_ground.setText(tr("geometry.adv_chk_ground", "Grade Chão"))
        self.chk_ceiling.setText(tr("geometry.adv_chk_ceiling", "Grade Teto"))
        self.chk_ground_v.setText(tr("geometry.adv_chk_ground_v", "Verticais Chão"))
        self.chk_ceiling_v.setText(tr("geometry.adv_chk_ceiling_v", "Verticais Teto"))
