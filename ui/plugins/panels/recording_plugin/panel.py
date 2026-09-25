"""
Timelapse Recording Panel — Painel Visual de Gravação & Timelapse (ARCcC).
=========================================================================
Interface do usuário integrada ao Workspace em PanelCardBox:
  - LED pulsante animado e cronômetro em tempo real.
  - Botões táteis de início, pausa, retomada, salvamento e descarte.
  - Seletores de resolução, gatilho de captura e formato de exportação.
  - Painel de diagnósticos ao vivo (quadros capturados, disco e duração).

Recebe o motor de gravação pelo construtor (o plugin cria e liga ao canvas) e
o widget onde a barra flutuante se ancora. Iniciar, parar, salvar e descartar
ficam no `RecordingActions`, usado também pela barra flutuante.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6 import QtCore, QtWidgets, QtGui

from ui.core.widgets.card_box import PanelCardBox
from ui.infrastructure.theme.manager import ThemeManager
from .engine.recording_engine import TimelapseRecordingEngine
from .components.recording_floating_bar import RecordingFloatingBar
from .recording_actions import RecordingActions

logger = logging.getLogger(__name__)


class RecordingPanel(QtWidgets.QWidget):
    """Painel de controle do timelapse encapsulado em CardBox."""

    def __init__(
        self,
        engine: TimelapseRecordingEngine,
        anchor: Optional[QtWidgets.QWidget] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.setMaximumWidth(int(280 * ThemeManager.instance().ui_scale))
        self.engine = engine
        self.actions = RecordingActions(
            engine, self, lambda: self.combo_format.currentText(), lambda: self.output_dir
        )

        self.output_dir: str = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.DocumentsLocation)

        self._pulse_state: bool = True
        self.pulse_timer = QtCore.QTimer(self)
        self.pulse_timer.setInterval(500)
        self.pulse_timer.timeout.connect(self._on_pulse_tick)

        self.floating_bar = RecordingFloatingBar(anchor=anchor, parent=self)
        self.floating_bar.pauseResumeRequested.connect(self.actions.toggle)
        self.floating_bar.stopRequested.connect(self.actions.request_stop)
        self.floating_bar.saveRequested.connect(self.actions.save)

        self._setup_ui()
        self._wire_engine()
        self._apply_theme()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        ThemeManager.instance().scaleChanged.connect(self._apply_theme)

    def _setup_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content = QtWidgets.QWidget(self)
        c_layout = QtWidgets.QVBoxLayout(content)
        c_layout.setContentsMargins(6, 6, 6, 6)
        c_layout.setSpacing(10)

        # ── 1. Status Bar / LED Header ─────────────────────────────────────
        self.status_box = QtWidgets.QFrame()
        self.status_box.setFixedHeight(44)
        sb_layout = QtWidgets.QHBoxLayout(self.status_box)
        sb_layout.setContentsMargins(10, 0, 10, 0)
        sb_layout.setSpacing(8)

        self.lbl_led = QtWidgets.QLabel("●")
        self.lbl_led.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.lbl_status = QtWidgets.QLabel("INATIVO")
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.lbl_time = QtWidgets.QLabel("00:00:00")
        self.lbl_time.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: bold;")

        sb_layout.addWidget(self.lbl_led)
        sb_layout.addWidget(self.lbl_status)
        sb_layout.addStretch()
        sb_layout.addWidget(self.lbl_time)
        c_layout.addWidget(self.status_box)

        # ── 2. Botões de Ação ──────────────────────────────────────────────
        self.btn_toggle = QtWidgets.QPushButton("Iniciar Gravação")
        self.btn_toggle.setFixedHeight(34)
        self.btn_toggle.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.actions.toggle)
        c_layout.addWidget(self.btn_toggle)

        self.row_extra = QtWidgets.QWidget()
        rx_layout = QtWidgets.QHBoxLayout(self.row_extra)
        rx_layout.setContentsMargins(0, 0, 0, 0)
        rx_layout.setSpacing(4)

        self.btn_stop = QtWidgets.QPushButton("Parar")
        self.btn_stop.setFixedHeight(28)
        self.btn_stop.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.btn_stop.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self.actions.request_stop)

        self.btn_save = QtWidgets.QPushButton("Salvar")
        self.btn_save.setFixedHeight(28)
        self.btn_save.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.btn_save.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.actions.save)

        self.btn_discard = QtWidgets.QPushButton("Descartar")
        self.btn_discard.setFixedHeight(28)
        self.btn_discard.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.btn_discard.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_discard.clicked.connect(self.actions.discard)

        rx_layout.addWidget(self.btn_stop)
        rx_layout.addWidget(self.btn_save)
        rx_layout.addWidget(self.btn_discard)
        self.row_extra.setVisible(False)
        c_layout.addWidget(self.row_extra)

        # ── 3. Opções de Timelapse ─────────────────────────────────────────
        self.group_options = QtWidgets.QGroupBox("OPÇÕES DE TIMELAPSE")
        self.group_options.setStyleSheet("font-weight: bold; font-size: 10px;")
        opt_layout = QtWidgets.QVBoxLayout(self.group_options)
        opt_layout.setContentsMargins(8, 12, 8, 8)
        opt_layout.setSpacing(8)

        lbl_res = QtWidgets.QLabel("Resolução:")
        lbl_res.setStyleSheet("font-size: 11px;")
        self.combo_res = QtWidgets.QComboBox()
        self.combo_res.addItems(["Original (Canvas)", "1080p (Full HD)", "720p (HD)"])
        self.combo_res.currentTextChanged.connect(self._on_res_changed)
        opt_layout.addWidget(lbl_res)
        opt_layout.addWidget(self.combo_res)

        lbl_trig = QtWidgets.QLabel("Gatilho de Captura:")
        lbl_trig.setStyleSheet("font-size: 11px;")
        self.combo_trigger = QtWidgets.QComboBox()
        self.combo_trigger.addItems(["Por Traço (Recomendado)", "Por Tempo (2s)"])
        self.combo_trigger.currentIndexChanged.connect(self._on_trigger_changed)
        opt_layout.addWidget(lbl_trig)
        opt_layout.addWidget(self.combo_trigger)

        lbl_fmt = QtWidgets.QLabel("Formato de Exportação:")
        lbl_fmt.setStyleSheet("font-size: 11px;")
        self.combo_format = QtWidgets.QComboBox()
        self.combo_format.addItems(["MP4 (H.264/AVC)", "Sequência JPG (ZIP)"])
        opt_layout.addWidget(lbl_fmt)
        opt_layout.addWidget(self.combo_format)

        lbl_fps = QtWidgets.QLabel("Taxa de Quadros (FPS):")
        lbl_fps.setStyleSheet("font-size: 11px;")
        self.combo_fps = QtWidgets.QComboBox()
        self.combo_fps.addItems(["30 FPS (Padrão)", "60 FPS (Fluido)", "24 FPS (Cinema)"])
        self.combo_fps.currentIndexChanged.connect(self._on_fps_changed)
        opt_layout.addWidget(lbl_fps)
        opt_layout.addWidget(self.combo_fps)

        self.chk_watermark = QtWidgets.QCheckBox("Incluir Marca d'Água")
        self.chk_watermark.setToolTip("Adiciona marca d'água oficial do Lumenia no canto inferior direito")
        self.chk_watermark.setChecked(True)
        self.chk_watermark.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.chk_watermark.setStyleSheet("font-size: 11px;")
        self.chk_watermark.toggled.connect(self._on_watermark_toggled)
        opt_layout.addWidget(self.chk_watermark)

        self.chk_guides = QtWidgets.QCheckBox("Incluir Guias Ativas")
        self.chk_guides.setToolTip("Captura guias de perspectiva e eixos de simetria ativos no vídeo")
        self.chk_guides.setChecked(False)
        self.chk_guides.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.chk_guides.setStyleSheet("font-size: 11px;")
        self.chk_guides.toggled.connect(self._on_guides_toggled)
        opt_layout.addWidget(self.chk_guides)

        lbl_dir = QtWidgets.QLabel("Pasta de Destino:")
        lbl_dir.setStyleSheet("font-size: 11px;")
        opt_layout.addWidget(lbl_dir)

        row_dir = QtWidgets.QHBoxLayout()
        row_dir.setSpacing(4)
        self.txt_dir = QtWidgets.QLineEdit(self.output_dir)
        self.txt_dir.setReadOnly(True)
        self.txt_dir.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        self.txt_dir.setMinimumWidth(40)
        self.txt_dir.setStyleSheet("font-size: 10px; padding: 2px;")
        self.btn_browse = QtWidgets.QPushButton("...")
        self.btn_browse.setFixedSize(24, 22)
        self.btn_browse.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        row_dir.addWidget(self.txt_dir)
        row_dir.addWidget(self.btn_browse)
        opt_layout.addLayout(row_dir)

        c_layout.addWidget(self.group_options)

        # ── 4. Diagnósticos da Sessão ──────────────────────────────────────
        self.group_diag = QtWidgets.QGroupBox("DIAGNÓSTICOS DA GRAVAÇÃO")
        self.group_diag.setStyleSheet("font-weight: bold; font-size: 10px;")
        diag_layout = QtWidgets.QVBoxLayout(self.group_diag)
        diag_layout.setContentsMargins(8, 12, 8, 8)
        diag_layout.setSpacing(6)

        self.lbl_diag_frames = QtWidgets.QLabel("Quadros: 0")
        self.lbl_diag_frames.setStyleSheet("font-size: 11px;")
        self.lbl_diag_size = QtWidgets.QLabel("Tamanho: 0.0 MB")
        self.lbl_diag_size.setStyleSheet("font-size: 11px;")
        self.lbl_diag_dur = QtWidgets.QLabel("Duração: 0.0s (a 30 FPS)")
        self.lbl_diag_dur.setStyleSheet("font-size: 11px;")

        diag_layout.addWidget(self.lbl_diag_frames)
        diag_layout.addWidget(self.lbl_diag_size)
        diag_layout.addWidget(self.lbl_diag_dur)
        c_layout.addWidget(self.group_diag)

        c_layout.addStretch()

        card_box = PanelCardBox("", content, self)
        main_layout.addWidget(card_box)

    def _wire_engine(self) -> None:
        self.engine.state_changed.connect(self._on_engine_state_changed)
        self.engine.stats_updated.connect(self._on_engine_stats_updated)

    def _apply_theme(self, *args) -> None:
        theme = ThemeManager.instance()
        self.setMaximumWidth(max(180, int(280 * theme.ui_scale)))
        bg, border = theme.get_color("bg_darker"), theme.get_color("border")
        self.status_box.setStyleSheet(f"QFrame {{ background-color: {bg}; border: 1px solid {border}; border-radius: 6px; }}")
        self._update_status_view()

    def _update_status_view(self) -> None:
        theme = ThemeManager.instance()
        fg_sec = theme.get_color("text_muted")
        danger, warning = theme.get_color("DANGER", "#f85149"), theme.get_color("WARNING", "#d29922")

        if not self.engine.is_recording:
            self.lbl_led.setStyleSheet(f"color: {fg_sec}; font-size: 16px;")
            self.lbl_status.setText("INATIVO")
            self.lbl_status.setStyleSheet(f"color: {fg_sec}; font-size: 11px; font-weight: bold;")
            self.btn_toggle.setText("Iniciar Gravação")
            self.row_extra.setVisible(False)
            self._set_options_enabled(True)
            self.pulse_timer.stop()
        elif self.engine.is_recording and not self.engine.is_paused:
            self.lbl_led.setStyleSheet(f"color: {danger}; font-size: 16px;")
            self.lbl_status.setText("GRAVANDO")
            self.lbl_status.setStyleSheet(f"color: {danger}; font-size: 11px; font-weight: bold;")
            self.btn_toggle.setText("Pausar Gravação")
            self.row_extra.setVisible(True)
            self._set_options_enabled(False)
            self.pulse_timer.start()
        else:
            self.lbl_led.setStyleSheet(f"color: {warning}; font-size: 16px;")
            self.lbl_status.setText("PAUSADO")
            self.lbl_status.setStyleSheet(f"color: {warning}; font-size: 11px; font-weight: bold;")
            self.btn_toggle.setText("Retomar Gravação")
            self.row_extra.setVisible(True)
            self._set_options_enabled(False)
            self.pulse_timer.stop()

    def _set_options_enabled(self, enabled: bool) -> None:
        for w in (self.combo_res, self.combo_fps, self.combo_trigger, self.combo_format, self.chk_watermark, self.chk_guides, self.btn_browse):
            w.setEnabled(enabled)

    def _on_watermark_toggled(self, checked: bool) -> None:
        self.engine.add_watermark = bool(checked)

    def _on_guides_toggled(self, checked: bool) -> None:
        self.engine.include_guides = bool(checked)

    def _on_pulse_tick(self) -> None:
        self._pulse_state = not self._pulse_state
        color = ThemeManager.instance().get_color("DANGER", "#f85149") if self._pulse_state else "transparent"
        self.lbl_led.setStyleSheet(f"color: {color}; font-size: 16px;")
        self.floating_bar.update_pulse(self._pulse_state)

    def _on_browse_clicked(self) -> None:
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Saída", self.output_dir)
        if dir_path:
            self.output_dir = dir_path
            self.txt_dir.setText(dir_path)

    def _on_res_changed(self, text: str) -> None:
        self.engine.target_resolution = text

    def _on_fps_changed(self, idx: int) -> None:
        fps_map = {0: 30, 1: 60, 2: 24}
        fps_val = fps_map.get(idx, 30)
        self.engine.fps = fps_val
        dur_secs = self.engine.frame_count / float(fps_val)
        self.lbl_diag_dur.setText(f"Duração: {dur_secs:.1f}s (a {fps_val} FPS)")

    def _on_trigger_changed(self, idx: int) -> None:
        self.engine.trigger_mode = "stroke" if idx == 0 else "time"

    def _on_engine_state_changed(self, is_rec: bool, is_paused: bool) -> None:
        self._update_status_view()
        self.floating_bar.update_state(is_rec, is_paused)
        if is_rec:
            self.floating_bar.show_bar()
        else:
            self.floating_bar.hide_bar()

    def _on_engine_stats_updated(self, frames: int, size_mb: float, dur_secs: float) -> None:
        secs = self.engine.elapsed_seconds
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        self.lbl_time.setText(f"{h:02d}:{m:02d}:{s:02d}")
        self.lbl_diag_frames.setText(f"Quadros: {frames}")
        self.lbl_diag_size.setText(f"Tamanho: {size_mb:.1f} MB")
        self.lbl_diag_dur.setText(f"Duração: {dur_secs:.1f}s (a {self.engine.fps} FPS)")
        self.floating_bar.update_stats(frames, secs)

    def shutdown(self) -> None:
        """Fecha a barra flutuante e a solta do canvas (o plugin chama ao desativar)."""
        self.floating_bar.hide_bar()
        self.floating_bar.detach_anchor()
        self.floating_bar.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.shutdown()
        super().closeEvent(event)
