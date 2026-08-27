"""Main Geometry Panel for Dock/Drawer in Lumenia."""

from PySide6 import QtWidgets, QtCore, QtGui
from .components.constants import GUIDE_NAMES, SYM_NAMES, GUIDE_TYPES, SYM_TYPES
from .components.geometry_selector import GeometrySelectorButton
from .components.advanced_settings_dialog import AdvancedGeometryDialog

class GeometryPanel(QtWidgets.QWidget):
    """Painel de Réguas, Perspectiva e Simetria na gaveta de ferramentas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.adv_dialog = None
        self.state = {
            "ruler_idx": 0, "ruler_type": "none",
            "sym_idx": 0, "sym_type": "none",
            "segments": 6, "angle": 90.0,
            "stop_at_center": False, "locked": False, "hidden": False,
            "snap_radius": 32.0, "yaw": 0.0, "pitch": 0.0, "fov": 130.0,
            "density": 30.0, "density_idx": 1,
            "show_ring": True, "show_v": True, "show_h": True, "show_d": True,
            "show_vps": False, "show_cube": False, "show_ground": False, "show_ceiling": False,
        }
        self._build_ui()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # 1. Cabeçalho com Engrenagem e Seletor
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(6)

        self.btn_advanced = QtWidgets.QPushButton("⚙")
        self.btn_advanced.setFixedSize(34, 34)
        self.btn_advanced.setToolTip("Configurações Avançadas de Simetria e Réguas")
        self.btn_advanced.setStyleSheet("""
            QPushButton {
                background: #1e1e2e; color: #a855f7; border: 1px solid #3b3b54;
                border-radius: 6px; font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background: #28283d; border-color: #a855f7; }
        """)
        self.btn_advanced.clicked.connect(self._toggle_advanced)
        header.addWidget(self.btn_advanced)

        self.selector_btn = GeometrySelectorButton()
        self.selector_btn.ruler_changed.connect(self._on_ruler_changed)
        self.selector_btn.symmetry_changed.connect(self._on_sym_changed)
        header.addWidget(self.selector_btn, 1)
        main_layout.addLayout(header)

        # 2. Card de Informações e Status
        self.card = QtWidgets.QFrame()
        self.card.setStyleSheet("""
            QFrame {
                background: #181825; border: 1px solid #313244;
                border-radius: 8px; padding: 10px;
            }
            QLabel { color: #cdd6f4; font-size: 11px; }
            QPushButton {
                background: #313244; color: #cdd6f4; border-radius: 4px;
                padding: 6px 10px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #45475a; color: #ffffff; }
        """)
        card_lay = QtWidgets.QVBoxLayout(self.card)
        card_lay.setSpacing(8)

        self.lbl_status = QtWidgets.QLabel("Selecione um modo de régua ou simetria acima para iniciar o desenho assistido.")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #6c7086; margin: 8px 0;")
        card_lay.addWidget(self.lbl_status)

        # Botão Centralizar Pivô
        self.btn_center_pivot = QtWidgets.QPushButton("🎯 Centralizar Pivô no Canvas")
        self.btn_center_pivot.clicked.connect(self._center_pivot_on_canvas)
        self.btn_center_pivot.setVisible(False)
        card_lay.addWidget(self.btn_center_pivot)

        # Botão Resetar Ângulo
        self.btn_reset_angle = QtWidgets.QPushButton("🔄 Resetar Ângulo do Eixo (0°)")
        self.btn_reset_angle.clicked.connect(self._reset_angle)
        self.btn_reset_angle.setVisible(False)
        card_lay.addWidget(self.btn_reset_angle)

        main_layout.addWidget(self.card)
        main_layout.addStretch()

    def _toggle_advanced(self):
        if self.adv_dialog and self.adv_dialog.isVisible():
            self.adv_dialog.hide()
            return

        rw = self._get_render_widget()
        if rw and hasattr(rw, "geometry_ctrl"):
            for k in ("yaw", "pitch", "fov", "density", "show_ring", "show_v", "show_h", "show_d",
                      "show_vps", "show_cube", "show_ground", "show_ground_verticals",
                      "show_ceiling", "show_ceiling_verticals", "show_straight_verticals",
                      "show_letterbox", "aspect_ratio", "snap_mode", "snap_sensitivity",
                      "snap_dynamic", "show_hint", "hidden"):
                if k in rw.geometry_ctrl.guide_state:
                    self.state[k] = rw.geometry_ctrl.guide_state[k]
            for k in ("segments", "angle", "stop_at_center", "locked"):
                if k in rw.geometry_ctrl.sym_state:
                    self.state[k] = rw.geometry_ctrl.sym_state[k]

        if not self.adv_dialog:
            self.adv_dialog = AdvancedGeometryDialog(self.window(), self.state)
            self.adv_dialog.settingsChanged.connect(self._on_advanced_settings_changed)
        else:
            self.adv_dialog.sync_from_state(self.state)

        self.adv_dialog.show_near(self.btn_advanced)

    def _on_ruler_changed(self, idx: int, gtype: str):
        self.state["ruler_idx"] = idx
        self.state["ruler_type"] = gtype
        self._update_status()
        self._sync_to_render_widget()

    def _on_sym_changed(self, idx: int, stype: str):
        self.state["sym_idx"] = idx
        self.state["sym_type"] = stype
        if stype == "mirror_v":
            self.state["angle"] = 90.0
        elif stype == "mirror_h":
            self.state["angle"] = 0.0
        elif stype in ("mirror", "double_mirror", "radial", "kaleidoscope") and self.state.get("angle", 0.0) == 0.0:
            self.state["angle"] = 90.0
        self._update_status()
        self._sync_to_render_widget()

    def _on_advanced_settings_changed(self, new_state: dict):
        self.state.update(new_state)
        self._sync_to_render_widget()

    def _update_status(self):
        r_name = GUIDE_NAMES[self.state["ruler_idx"]]
        s_name = SYM_NAMES[self.state["sym_idx"]]

        lines = []
        if self.state["sym_type"] != "none":
            lines.append(f"🪞 <b>Simetria:</b> {s_name}")
        if self.state["ruler_type"] != "none":
            lines.append(f"📏 <b>Régua:</b> {r_name}")

        if not lines:
            self.lbl_status.setText("Selecione um modo de régua ou simetria acima para iniciar o desenho assistido.")
            self.lbl_status.setStyleSheet("color: #6c7086; margin: 8px 0;")
            self.btn_center_pivot.setVisible(False)
            self.btn_reset_angle.setVisible(False)
        else:
            self.lbl_status.setText("<br>".join(lines))
            self.lbl_status.setStyleSheet("color: #a855f7; margin: 4px 0;")
            self.btn_center_pivot.setVisible(True)
            self.btn_reset_angle.setVisible(self.state["sym_type"] in ("mirror", "double_mirror", "radial", "kaleidoscope"))

    def _get_render_widget(self):
        top = self.window()
        if top:
            from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
            rw = top.findChild(RenderWidget)
            return rw
        return None

    def _center_pivot_on_canvas(self):
        rw = self._get_render_widget()
        if rw and hasattr(rw, "geometry_ctrl"):
            rw.geometry_ctrl.center_on_document(rw.canvas_w, rw.canvas_h)
            rw.update()

    def _reset_angle(self):
        angle = 90.0 if self.state.get("sym_type") != "mirror_h" else 0.0
        self.state["angle"] = angle
        rw = self._get_render_widget()
        if rw and hasattr(rw, "geometry_ctrl"):
            rw.geometry_ctrl.sym_state["angle"] = angle
            rw.geometry_ctrl.sync_symmetry_to_engine()
            rw.update()

    def _sync_to_render_widget(self):
        """Syncs panel state to the canvas geometry controller."""
        rw = self._get_render_widget()
        if not rw or not hasattr(rw, "geometry_ctrl"):
            QtCore.QTimer.singleShot(200, self._sync_to_render_widget)
            return

        ctrl = rw.geometry_ctrl
        ctrl.sym_state["mode"] = self.state["sym_type"]
        ctrl.sym_state["segments"] = self.state["segments"]
        if self.state["sym_type"] == "mirror_v":
            ctrl.sym_state["angle"] = 90.0
        elif self.state["sym_type"] == "mirror_h":
            ctrl.sym_state["angle"] = 0.0
        elif "angle" in self.state and self.state["angle"] != 0.0:
            ctrl.sym_state["angle"] = self.state["angle"]
        ctrl.sym_state["stop_at_center"] = self.state["stop_at_center"]
        ctrl.sym_state["locked"] = self.state["locked"]
        ctrl.sym_state["hidden"] = self.state["hidden"]

        ctrl.guide_state["type"] = self.state["ruler_type"]
        ctrl.guide_state["hidden"] = self.state["hidden"]
        ctrl.guide_state["snap_radius"] = self.state["snap_radius"]
        
        # Camera synchronicity
        if "yaw" in self.state:
            ctrl.guide_state["yaw"] = float(self.state["yaw"])
        if "pitch" in self.state:
            ctrl.guide_state["pitch"] = float(self.state["pitch"])
        if "fov" in self.state:
            ctrl.guide_state["fov"] = float(self.state["fov"])
        if "density" in self.state:
            ctrl.guide_state["density"] = float(self.state["density"])
        ctrl.guide_state["show_ring"] = self.state.get("show_ring", True)
        ctrl.guide_state["show_straight_verticals"] = self.state.get("show_straight_verticals", False)
        ctrl.guide_state["show_v"] = self.state.get("show_v", True)
        ctrl.guide_state["show_h"] = self.state.get("show_h", True)
        ctrl.guide_state["show_d"] = self.state.get("show_d", True)
        ctrl.guide_state["show_vps"] = self.state.get("show_vps", False)
        ctrl.guide_state["show_cube"] = self.state.get("show_cube", False)
        ctrl.guide_state["show_ground"] = self.state.get("show_ground", False)
        ctrl.guide_state["show_ground_verticals"] = self.state.get("show_ground_verticals", False)
        ctrl.guide_state["show_ceiling"] = self.state.get("show_ceiling", False)
        ctrl.guide_state["show_ceiling_verticals"] = self.state.get("show_ceiling_verticals", False)
        ctrl.guide_state["show_letterbox"] = self.state.get("show_letterbox", False)
        ctrl.guide_state["aspect_ratio"] = self.state.get("aspect_ratio", "16:9")
        ctrl.guide_state["snap_mode"] = self.state.get("snap_mode", "auto")
        ctrl.guide_state["snap_sensitivity"] = self.state.get("snap_sensitivity", 3.0)
        ctrl.guide_state["snap_dynamic"] = self.state.get("snap_dynamic", True)
        ctrl.guide_state["show_hint"] = self.state.get("show_hint", True)

        ctrl.sync_symmetry_to_engine()
        ctrl.sync_guides_to_engine()
        rw.update()
