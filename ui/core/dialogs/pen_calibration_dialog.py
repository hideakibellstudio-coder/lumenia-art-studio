"""PenCalibrationDialog — calibra a pressão da caneta: mede o aperto habitual e ajusta a curva global.

A conta da curva mora no motor (`PressureCalibration`); aqui o artista escolhe os três números
(zona morta, pressão total, gama) à mão ou deixa o assistente sugerir a pressão total a partir
do que desenhou no quadro. O valor vale para todos os documentos e fica salvo na configuração.
"""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.dialogs.pen_calibration_pad import PressurePad
from ui.core.dialogs.render_settings_components import apply_render_dialog_styles
from ui.core.engine.backend_protocols import RoleProvider, StrokeProtocol
from ui.core.state import (
    CEILING_RANGE,
    FLOOR_RANGE,
    GAMMA_RANGE,
    MIN_MEASURED_SAMPLES,
    PenCalibration,
    suggest_from_pressures,
    summarize_pressures,
)
from ui.infrastructure.config import ConfigManager
from ui.infrastructure.i18n import I18nManager, tr
from ui.infrastructure.theme import ThemeManager

__all__ = ["PenCalibrationDialog"]

PERCENT = 100.0


def _percent_spin(bounds: tuple[float, float], value: float) -> QtWidgets.QDoubleSpinBox:
    spin = QtWidgets.QDoubleSpinBox()
    spin.setRange(bounds[0] * PERCENT, bounds[1] * PERCENT)
    spin.setDecimals(0)
    spin.setSuffix(" %")
    spin.setValue(value * PERCENT)
    return spin


class PenCalibrationDialog(BaseFramelessDialog):
    """Quadro de medição + os três números da curva; Aplicar grava no motor e na configuração."""

    calibrationApplied = QtCore.Signal()

    def __init__(self, backend: RoleProvider[StrokeProtocol], parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(title=tr("dialogs.pen_title", "Calibrar Caneta (Pressão)"), icon_name="brush", parent=parent, modal=True)
        self.setObjectName("PenCalibrationDialog")
        self.resize(520, 560)
        self._backend = backend
        self._suggestion: PenCalibration | None = None
        self._setup_ui()
        self._show_values(self._stored_calibration())
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()
        self._refresh_reading()

    # ── Construção ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.lbl_intro = QtWidgets.QLabel()
        self.lbl_intro.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_intro)

        self.pad = PressurePad()
        self.pad.measured.connect(self._refresh_reading)
        self.content_layout.addWidget(self.pad, 1)

        self.lbl_reading = QtWidgets.QLabel()
        self.lbl_reading.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_reading)

        row = QtWidgets.QHBoxLayout()
        self.btn_suggest = QtWidgets.QPushButton()
        self.btn_suggest.clicked.connect(self._use_suggestion)
        self.btn_clear = QtWidgets.QPushButton()
        self.btn_clear.clicked.connect(self.pad.clear)
        row.addWidget(self.btn_suggest)
        row.addWidget(self.btn_clear)
        row.addStretch(1)
        self.content_layout.addLayout(row)

        self.group_manual = QtWidgets.QGroupBox()
        form = QtWidgets.QFormLayout(self.group_manual)
        self.spin_floor = _percent_spin(FLOOR_RANGE, 0.0)
        self.spin_ceiling = _percent_spin(CEILING_RANGE, 1.0)
        self.spin_gamma = QtWidgets.QDoubleSpinBox()
        self.spin_gamma.setRange(*GAMMA_RANGE)
        self.spin_gamma.setDecimals(2)
        self.spin_gamma.setSingleStep(0.05)
        self.lbl_floor, self.lbl_ceiling, self.lbl_gamma = QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel()
        form.addRow(self.lbl_floor, self.spin_floor)
        form.addRow(self.lbl_ceiling, self.spin_ceiling)
        form.addRow(self.lbl_gamma, self.spin_gamma)
        self.content_layout.addWidget(self.group_manual)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_reset = QtWidgets.QPushButton()
        self.btn_reset.clicked.connect(lambda: self._show_values(PenCalibration()))
        self.btn_apply = QtWidgets.QPushButton()
        self.btn_apply.setDefault(True)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_close = QtWidgets.QPushButton()
        self.btn_close.clicked.connect(self.reject)
        buttons.addWidget(self.btn_reset)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_apply)
        buttons.addWidget(self.btn_close)
        self.content_layout.addLayout(buttons)

    # ── Valores ──────────────────────────────────────────────────────────

    def _stored_calibration(self) -> PenCalibration:
        backend = self._backend()
        if backend is not None:
            return PenCalibration(*backend.get_pressure_calibration()).normalized()
        return PenCalibration.from_config(ConfigManager.instance().get_section("pen"))

    def _show_values(self, calibration: PenCalibration) -> None:
        self.spin_floor.setValue(calibration.floor * PERCENT)
        self.spin_ceiling.setValue(calibration.ceiling * PERCENT)
        self.spin_gamma.setValue(calibration.gamma)

    def chosen_calibration(self) -> PenCalibration:
        """Os três campos como o motor os receberá (já presos nas faixas aceitas)."""
        return PenCalibration(
            self.spin_floor.value() / PERCENT, self.spin_ceiling.value() / PERCENT, self.spin_gamma.value()
        ).normalized()

    # ── Medição ──────────────────────────────────────────────────────────

    def _refresh_reading(self) -> None:
        samples = self.pad.samples
        summary = summarize_pressures(samples)
        self._suggestion = suggest_from_pressures(samples)
        if summary is None:
            self.lbl_reading.setText(tr("dialogs.pen_reading_empty", "Nenhuma pressão medida ainda."))
        elif self._suggestion is None:
            self.lbl_reading.setText(tr(
                "dialogs.pen_reading_few", "Continue desenhando: {count} de {need} amostras.",
                count=summary.count, need=MIN_MEASURED_SAMPLES,
            ))
        else:
            self.lbl_reading.setText(tr(
                "dialogs.pen_reading", "Pico: {peak}% · aperto habitual: {habitual}% ({count} amostras).",
                peak=round(summary.peak * PERCENT), habitual=round(summary.habitual * PERCENT), count=summary.count,
            ))
            if self._suggestion.is_identity:
                self.lbl_reading.setText(self.lbl_reading.text() + " " + tr(
                    "dialogs.pen_reading_full", "Sua caneta já cobre a faixa inteira."))
        self.btn_suggest.setEnabled(self._suggestion is not None and not self._suggestion.is_identity)

    def _use_suggestion(self) -> None:
        if self._suggestion is not None:
            self._show_values(self._suggestion)

    def _apply(self) -> None:
        calibration = self.chosen_calibration()
        backend = self._backend()
        if backend is not None:
            backend.set_pressure_calibration(calibration.floor, calibration.ceiling, calibration.gamma)
        ConfigManager.instance().set_section("pen", calibration.to_config())
        self.calibrationApplied.emit()
        self.accept()

    # ── Texto e tema ─────────────────────────────────────────────────────

    def retranslate_ui(self) -> None:
        self.set_dialog_title(tr("dialogs.pen_title", "Calibrar Caneta (Pressão)"))
        self.lbl_intro.setText(tr(
            "dialogs.pen_intro",
            "Desenhe no quadro como você desenha de verdade. O assistente usa o aperto que você mais "
            "usa como pressão total, para que os pincéis respondam em toda a sua faixa.",
        ))
        self.btn_suggest.setText(tr("dialogs.pen_use_suggestion", "Usar sugestão"))
        self.btn_clear.setText(tr("dialogs.pen_clear", "Limpar medição"))
        self.group_manual.setTitle(tr("dialogs.pen_manual", "Curva de pressão"))
        self.lbl_floor.setText(tr("dialogs.pen_floor", "Zona morta (pressão ignorada)"))
        self.lbl_ceiling.setText(tr("dialogs.pen_ceiling", "Pressão total (a que conta como 100%)"))
        self.lbl_gamma.setText(tr("dialogs.pen_gamma", "Curva (menor que 1 levanta o toque leve)"))
        self.btn_reset.setText(tr("dialogs.pen_reset", "Restaurar padrão"))
        self.btn_apply.setText(tr("dialogs.apply", "Aplicar"))
        self.btn_close.setText(tr("dialogs.close", "Fechar"))
        self._refresh_reading()

    def _apply_theme(self, *args) -> None:
        apply_render_dialog_styles(self)
        theme = ThemeManager.instance()
        self.setStyleSheet(self.styleSheet() + f"""
            QDoubleSpinBox {{
                background-color: {theme.get_color("bg_card")};
                color: {theme.get_color("text_main")};
                border: 1px solid {theme.get_color("border")};
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
