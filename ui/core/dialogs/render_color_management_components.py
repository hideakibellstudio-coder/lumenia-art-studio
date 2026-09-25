"""
ColorManagementGroup — Componente UI de Gestão Profissional de Cor e Soft-Proofing.
===================================================================================
Fornece controles para importação de perfis ICC externos (.icc/.icm), configuração
de Intenções de Renderização (Rendering Intents), Black Point Compensation (BPC),
simulação de Prova de Cor de Impressão (Soft-Proofing) e Alerta de Gamut.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any

from PySide6 import QtCore, QtWidgets
from ui.infrastructure.i18n import tr
from ui.infrastructure.icons import get_icon
from ui.core.widgets.toggle.toggle_switch import ToggleSwitch
from ui.core.color.proofing import SoftProofConfig, RenderingIntent
from ui.core.color.catalog import get_color_catalog

logger = logging.getLogger(__name__)


class ColorManagementGroup(QtWidgets.QGroupBox):
    """Grupo de interface para configuração de LittleCMS, perfis ICC externos e prova de cor."""

    profileImported = QtCore.Signal(int)
    softProofChanged = QtCore.Signal(dict)
    renderingIntentChanged = QtCore.Signal(int, bool)

    def __init__(self, saved_cfg: Dict[str, Any], parent=None):
        super().__init__("Gestão Profissional de Cor & LittleCMS", parent)
        self._saved_cfg = saved_cfg
        self._soft_proof_config = SoftProofConfig()
        self._build_ui()
        self._load_state()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(10)

        # 1. Botão de Importação de Perfil ICC Externo
        import_row = QtWidgets.QHBoxLayout()
        import_row.setSpacing(8)
        self.btn_import_icc = QtWidgets.QPushButton(" Importar Perfil ICC (.icc / .icm)...")
        self.btn_import_icc.setIcon(get_icon("folder"))
        self.btn_import_icc.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_import_icc.setFixedHeight(30)
        self.btn_import_icc.clicked.connect(self._on_import_icc_clicked)
        import_row.addWidget(self.btn_import_icc)
        layout.addLayout(import_row)

        # 2. Intenção de Renderização & BPC
        row_intent = QtWidgets.QHBoxLayout()
        row_intent.setSpacing(8)
        lbl_intent = QtWidgets.QLabel("Intenção:")
        lbl_intent.setFixedWidth(65)
        self.combo_intent = QtWidgets.QComboBox()
        self.combo_intent.setFixedHeight(28)
        self.combo_intent.addItem("Colorimétrico Relativo", int(RenderingIntent.RELATIVE_COLORIMETRIC))
        self.combo_intent.addItem("Perceptual (Fotográfico)", int(RenderingIntent.PERCEPTUAL))
        self.combo_intent.addItem("Saturação", int(RenderingIntent.SATURATION))
        self.combo_intent.addItem("Colorimétrico Absoluto", int(RenderingIntent.ABSOLUTE_COLORIMETRIC))
        self.combo_intent.currentIndexChanged.connect(self._on_intent_changed)
        row_intent.addWidget(lbl_intent)
        row_intent.addWidget(self.combo_intent, 1)
        layout.addLayout(row_intent)

        # Switch BPC (Black Point Compensation)
        row_bpc = QtWidgets.QHBoxLayout()
        lbl_bpc = QtWidgets.QLabel("Compensação de Ponto Preto (BPC):")
        self.switch_bpc = ToggleSwitch()
        self.switch_bpc.setChecked(True)
        self.switch_bpc.toggled.connect(self._on_intent_changed)
        row_bpc.addWidget(lbl_bpc)
        row_bpc.addStretch()
        row_bpc.addWidget(self.switch_bpc)
        layout.addLayout(row_bpc)

        # Divisor
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.08);")
        layout.addWidget(line)

        # 3. Seção Prova de Impressão (Soft-Proofing)
        row_proof_enable = QtWidgets.QHBoxLayout()
        lbl_proof = QtWidgets.QLabel("Prova de Cor (Soft-Proofing):")
        lbl_proof.setStyleSheet("font-weight: bold;")
        self.switch_proof = ToggleSwitch()
        self.switch_proof.setChecked(False)
        self.switch_proof.toggled.connect(self._on_soft_proof_toggled)
        row_proof_enable.addWidget(lbl_proof)
        row_proof_enable.addStretch()
        row_proof_enable.addWidget(self.switch_proof)
        layout.addLayout(row_proof_enable)

        # Seletor de Perfil Alvo de Prova (CMYK / Impressão)
        row_target = QtWidgets.QHBoxLayout()
        row_target.setSpacing(8)
        lbl_target = QtWidgets.QLabel("Alvo:")
        lbl_target.setFixedWidth(65)
        self.combo_proof_target = QtWidgets.QComboBox()
        self.combo_proof_target.setFixedHeight(28)
        self._populate_proof_targets()
        self.combo_proof_target.currentIndexChanged.connect(self._on_proof_target_changed)
        row_target.addWidget(lbl_target)
        row_target.addWidget(self.combo_proof_target, 1)
        layout.addLayout(row_target)

        # Alerta de Cores Fora de Gama (Gamut Warning)
        row_gamut = QtWidgets.QHBoxLayout()
        lbl_gamut = QtWidgets.QLabel("Alerta de Fora de Gama (Gamut Warning):")
        self.switch_gamut = ToggleSwitch()
        self.switch_gamut.setChecked(False)
        self.switch_gamut.toggled.connect(self._on_gamut_warning_toggled)
        row_gamut.addWidget(lbl_gamut)
        row_gamut.addStretch()
        row_gamut.addWidget(self.switch_gamut)
        layout.addLayout(row_gamut)

    def _populate_proof_targets(self):
        self.combo_proof_target.clear()
        catalog = get_color_catalog()
        profiles = catalog.get_all_profiles()
        # Prioriza perfis CMYK ou de impressão
        for p in profiles:
            cat = p.get("category", "")
            if "Impressão" in cat or "CMYK" in p.get("color_space", "") or p.get("id") in (4, 5, 6, 7):
                self.combo_proof_target.addItem(f"{p['name']} ({p.get('color_space', 'CMYK')})", p["id"])

        if self.combo_proof_target.count() == 0:
            for p in profiles[:5]:
                self.combo_proof_target.addItem(p["name"], p["id"])

    def _load_state(self):
        intent = int(self._saved_cfg.get("rendering_intent", 1))
        idx = self.combo_intent.findData(intent)
        if idx >= 0:
            self.combo_intent.setCurrentIndex(idx)
        self.switch_bpc.setChecked(bool(self._saved_cfg.get("bpc", True)))
        self.switch_proof.setChecked(bool(self._saved_cfg.get("soft_proof_enabled", False)))
        self.switch_gamut.setChecked(bool(self._saved_cfg.get("gamut_warning", False)))

    def _on_import_icc_clicked(self):
        from ui.core.engine.registry import EngineRegistry
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            tr("file_dialogs.import_icc", "Importar Perfil ICC / ICM"),
            "",
            f"{tr('file_dialogs.icc_profiles', 'Perfis ICC')} (*.icc *.icm);;"
            f"{tr('file_dialogs.all_files', 'Todos os Arquivos')} (*.*)",
        )
        if not path:
            return

        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "register_custom_color_profile"):
            QtWidgets.QMessageBox.warning(
                self, tr("messages.warning", "Aviso"),
                tr("messages.icc_import_unsupported", "O backend ativo não suporta importação dinâmica de perfis."))
            return

        try:
            new_id = backend.register_custom_color_profile(path)
            self._populate_proof_targets()
            self.profileImported.emit(new_id)
            QtWidgets.QMessageBox.information(
                self,
                tr("messages.icc_imported_title", "Perfil Importado"),
                tr("messages.icc_imported", "Perfil '{name}' carregado e registrado com sucesso!", name=Path(path).name),
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self,
                tr("messages.icc_import_error_title", "Erro de Importação"),
                tr("messages.icc_import_error", "Falha ao carregar perfil ICC: {error}", error=exc),
            )

    def _on_intent_changed(self):
        intent = self.combo_intent.currentData()
        bpc = self.switch_bpc.isChecked()
        self.renderingIntentChanged.emit(int(intent), bool(bpc))
        self._notify_soft_proof()

    def _on_soft_proof_toggled(self, checked: bool):
        self.combo_proof_target.setEnabled(checked)
        self.switch_gamut.setEnabled(checked)
        self._notify_soft_proof()

    def _on_proof_target_changed(self):
        self._notify_soft_proof()

    def _on_gamut_warning_toggled(self, checked: bool):
        self._notify_soft_proof()

    def _notify_soft_proof(self):
        proof_id = self.combo_proof_target.currentData() or 5
        config = {
            "enabled": self.switch_proof.isChecked(),
            "proof_profile_id": int(proof_id),
            "rendering_intent": int(self.combo_intent.currentData() or 1),
            "proof_rendering_intent": int(self.combo_intent.currentData() or 1),
            "bpc": bool(self.switch_bpc.isChecked()),
            "gamut_warning": bool(self.switch_gamut.isChecked()),
        }
        self.softProofChanged.emit(config)

    def get_state(self) -> Dict[str, Any]:
        return {
            "rendering_intent": int(self.combo_intent.currentData() or 1),
            "bpc": bool(self.switch_bpc.isChecked()),
            "soft_proof_enabled": bool(self.switch_proof.isChecked()),
            "proof_profile_id": int(self.combo_proof_target.currentData() or 5),
            "gamut_warning": bool(self.switch_gamut.isChecked()),
        }
