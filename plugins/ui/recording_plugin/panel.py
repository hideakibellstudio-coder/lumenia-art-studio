"""
Timelapse Recording Panel — Painel Visual de Gravação & Timelapse (ARCcC).
=========================================================================
Interface do usuário integrada ao Workspace em PanelCardBox:
  - LED pulsante animado e cronômetro em tempo real.
  - Botões táteis de início, pausa, retomada, salvamento e descarte.
  - Seletores de resolução, gatilho de captura e formato de exportação.
  - Painel de diagnósticos ao vivo (quadros capturados, disco e duração).
"""

from __future__ import annotations

import os
import logging
from typing import Optional

from PySide6 import QtCore, QtWidgets, QtGui

from ui.core.widgets.card_box import PanelCardBox
from ui.core.theme.manager import ThemeManager
from .engine.recording_engine import TimelapseRecordingEngine
from .engine.export_worker import TimelapseExportWorker
from .components.export_dialog import TimelapseExportDialog
from .components.recording_floating_bar import RecordingFloatingBar

logger = logging.getLogger(__name__)


class RecordingPanel(QtWidgets.QWidget):
    """Painel de controle do timelapse encapsulado em CardBox."""

    def __init__(self, canvas: Optional[QtCore.QObject] = None, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setMaximumWidth(int(280 * ThemeManager.instance().ui_scale))
        self.canvas = canvas
        self.engine = TimelapseRecordingEngine(self)
        if canvas is not None:
            self.engine.attach_canvas(canvas)

        self.output_dir: str = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.DocumentsLocation)

        self._pulse_state: bool = True
        self.pulse_timer = QtCore.QTimer(self)
        self.pulse_timer.setInterval(500)
        self.pulse_timer.timeout.connect(self._on_pulse_tick)

        self.floating_bar = RecordingFloatingBar(parent=self.window(), panel=self, canvas=canvas)

        self._setup_ui()
        self._wire_engine()
        self._apply_theme()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        ThemeManager.instance().scaleChanged.connect(self._apply_theme)

    def set_canvas(self, canvas: QtCore.QObject) -> None:
        """Conecta dinamicamente uma nova instância de canvas."""
        self.canvas = canvas
        self.engine.attach_canvas(canvas)
        if hasattr(self, "floating_bar") and self.floating_bar:
            self.floating_bar.set_canvas(canvas)

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
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)
        c_layout.addWidget(self.btn_toggle)

        self.row_extra = QtWidgets.QWidget()
        rx_layout = QtWidgets.QHBoxLayout(self.row_extra)
        rx_layout.setContentsMargins(0, 0, 0, 0)
        rx_layout.setSpacing(4)

        self.btn_stop = QtWidgets.QPushButton("Parar")
        self.btn_stop.setFixedHeight(28)
        self.btn_stop.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.btn_stop.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self.request_stop_recording)

        self.btn_save = QtWidgets.QPushButton("Salvar")
        self.btn_save.setFixedHeight(28)
        self.btn_save.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.btn_save.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save_clicked)

        self.btn_discard = QtWidgets.QPushButton("Descartar")
        self.btn_discard.setFixedHeight(28)
        self.btn_discard.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.btn_discard.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_discard.clicked.connect(self._on_discard_clicked)

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
        fg_sec, danger, warning = theme.get_color("text_muted"), "#f85149", "#d29922"

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
        color = "#f85149" if self._pulse_state else "transparent"
        self.lbl_led.setStyleSheet(f"color: {color}; font-size: 16px;")
        if hasattr(self, "floating_bar") and self.floating_bar:
            self.floating_bar.update_pulse(self._pulse_state)

    def _on_toggle_clicked(self) -> None:
        if not self.engine.is_recording:
            # Garante que o canvas está conectado caso tenha sido instanciado tardiamente
            if self.canvas is None:
                try:
                    from ui.core.plugins.registry import ServiceRegistry
                    from ui.core.plugins.workspace_contract import WorkspaceService
                    ws = ServiceRegistry.instance().get(WorkspaceService)
                    if ws and hasattr(ws, "canvas") and ws.canvas:
                        self.set_canvas(ws.canvas)
                except Exception:
                    pass
            elif self.engine._connected_canvas is None:
                self.engine.attach_canvas(self.canvas)

            self.engine.start_recording()
        elif self.engine.is_recording and not self.engine.is_paused:
            self.engine.pause_recording()
        else:
            self.engine.resume_recording()

    def request_stop_recording(self) -> bool:
        """Interrompe a gravação e pergunta ao usuário se deseja salvar e o local."""
        if not self.engine.is_recording:
            return False

        was_paused = self.engine.is_paused
        if not was_paused:
            self.engine.pause_recording()

        if self.engine.frame_count == 0:
            self.engine.discard_recording()
            self.lbl_time.setText("00:00:00")
            QtWidgets.QMessageBox.information(
                self, "Gravação Parada", "A gravação foi encerrada sem quadros capturados."
            )
            return True

        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Parar Gravação")
        msg.setText("Deseja salvar a gravação antes de parar?")
        msg.setInformativeText(f"A gravação contém {self.engine.frame_count} quadros capturados.")
        msg.setIcon(QtWidgets.QMessageBox.Icon.Question)

        btn_save = msg.addButton("Salvar Vídeo", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        btn_discard = msg.addButton("Descartar", QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = msg.addButton("Cancelar", QtWidgets.QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_save)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked == btn_save:
            saved = self._on_save_clicked()
            if not saved and not was_paused:
                self.engine.resume_recording()
            return bool(saved)
        elif clicked == btn_discard:
            self.engine.discard_recording()
            self.lbl_time.setText("00:00:00")
            return True
        else:
            if not was_paused:
                self.engine.resume_recording()
            return False

    def _on_discard_clicked(self) -> None:
        reply = QtWidgets.QMessageBox.question(
            self,
            "Descartar Gravação",
            "Deseja descartar a gravação atual? Todos os quadros capturados serão apagados.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.engine.discard_recording()
            self.lbl_time.setText("00:00:00")

    def _on_save_clicked(self) -> bool:
        # Aguarda qualquer gravação assíncrona pendente no pool de threads
        QtCore.QThreadPool.globalInstance().waitForDone(1500)

        if self.engine.frame_count == 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum quadro foi capturado para exportar.")
            return False

        fmt = self.combo_format.currentText()
        is_mp4 = "MP4" in fmt
        ext = ".mp4" if is_mp4 else ".zip"
        filter_str = "Vídeo MP4 (*.mp4)" if is_mp4 else "Arquivo ZIP (*.zip)"

        default_name = os.path.join(self.output_dir, f"lumenia_timelapse{ext}")
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Salvar Gravação", default_name, filter_str)
        if not save_path:
            return False

        temp_dir = self.engine.stop_recording()
        if not temp_dir:
            return False

        # Abre o diálogo de exportação assíncrona com FPS selecionado
        dlg = TimelapseExportDialog(self)
        worker = TimelapseExportWorker(temp_dir, self.engine.frame_count, dlg, fps=self.engine.fps)

        worker.progress.connect(dlg.update_progress)
        dlg.cancel_requested.connect(worker.cancel)

        def on_finished(success: bool, message: str, path: str):
            dlg.close()
            if success:
                QtWidgets.QMessageBox.information(self, "Exportação Concluída", message)
            else:
                QtWidgets.QMessageBox.warning(self, "Exportação Cancelada", message)
            self.engine.cleanup_temp_files()
            self.lbl_time.setText("00:00:00")

        worker.finished.connect(on_finished)
        dlg.show()
        worker.export(save_path, fmt, fps=self.engine.fps)
        return True

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
        if hasattr(self, "floating_bar") and self.floating_bar:
            self.floating_bar.update_state(is_rec, is_paused)
            self.floating_bar.show_bar() if is_rec else self.floating_bar.hide_bar()

    def _on_engine_stats_updated(self, frames: int, size_mb: float, dur_secs: float) -> None:
        secs = self.engine.elapsed_seconds
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        self.lbl_time.setText(f"{h:02d}:{m:02d}:{s:02d}")
        self.lbl_diag_frames.setText(f"Quadros: {frames}")
        self.lbl_diag_size.setText(f"Tamanho: {size_mb:.1f} MB")
        self.lbl_diag_dur.setText(f"Duração: {dur_secs:.1f}s (a {self.engine.fps} FPS)")
        if hasattr(self, "floating_bar") and self.floating_bar:
            self.floating_bar.update_stats(frames, secs)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if hasattr(self, "floating_bar") and self.floating_bar:
            self.floating_bar.hide_bar()
            self.floating_bar.close()
        super().closeEvent(event)
