"""
RecordingActions — iniciar/pausar, parar, salvar e descartar o timelapse.
=========================================================================
O fluxo com o usuário (perguntas, escolha do arquivo e exportação) em um lugar
só, usado pelos botões do painel e da barra flutuante. Até 2026-09-24 ele
morava no `RecordingPanel` e a barra chamava os métodos privados do painel
(`panel._on_toggle_clicked()`) depois de conferir com `hasattr`.

Recebe pelo construtor o motor, o widget pai dos diálogos e quem informa o
formato de exportação e a pasta de destino escolhidos no painel.
"""
from __future__ import annotations

import os
from typing import Callable

from PySide6 import QtCore, QtWidgets

from ui.infrastructure.i18n import tr

from .components.export_dialog import TimelapseExportDialog
from .engine.export_worker import TimelapseExportWorker
from .engine.recording_engine import TimelapseRecordingEngine

_Box = QtWidgets.QMessageBox


class RecordingActions:
    def __init__(
        self,
        engine: TimelapseRecordingEngine,
        dialog_parent: QtWidgets.QWidget,
        export_format: Callable[[], str],
        output_dir: Callable[[], str],
    ) -> None:
        self._engine = engine
        self._parent = dialog_parent
        self._export_format = export_format
        self._output_dir = output_dir

    def toggle(self) -> None:
        """Inicia, pausa ou retoma, conforme o estado."""
        engine = self._engine
        if not engine.is_recording:
            engine.start_recording()
        elif not engine.is_paused:
            engine.pause_recording()
        else:
            engine.resume_recording()

    def request_stop(self) -> bool:
        """Interrompe a gravação e pergunta se salva. True se a gravação acabou."""
        engine = self._engine
        if not engine.is_recording:
            return False
        was_paused = engine.is_paused
        if not was_paused:
            engine.pause_recording()

        if engine.frame_count == 0:
            engine.discard_recording()
            _Box.information(self._parent, tr("recording.stopped_title", "Gravação Parada"),
                             tr("recording.stopped_empty", "A gravação foi encerrada sem quadros capturados."))
            return True

        box = _Box(self._parent)
        box.setWindowTitle(tr("recording.stop_title", "Parar Gravação"))
        box.setText(tr("recording.stop_question", "Deseja salvar a gravação antes de parar?"))
        box.setInformativeText(tr("recording.stop_frames", "A gravação contém {n} quadros capturados.",
                                  n=engine.frame_count))
        box.setIcon(_Box.Icon.Question)
        btn_save = box.addButton(tr("recording.save_video", "Salvar Vídeo"), _Box.ButtonRole.AcceptRole)
        btn_discard = box.addButton(tr("recording.discard", "Descartar"), _Box.ButtonRole.DestructiveRole)
        box.addButton(tr("common.cancel", "Cancelar"), _Box.ButtonRole.RejectRole)
        box.setDefaultButton(btn_save)
        box.exec()
        clicked = box.clickedButton()

        if clicked == btn_save:
            saved = self.save()
            if not saved and not was_paused:
                engine.resume_recording()
            return saved
        if clicked == btn_discard:
            engine.discard_recording()
            return True
        if not was_paused:
            engine.resume_recording()
        return False

    def discard(self) -> None:
        """Pergunta e apaga todos os quadros da sessão."""
        reply = _Box.question(
            self._parent,
            tr("recording.discard_title", "Descartar Gravação"),
            tr("recording.discard_question",
               "Deseja descartar a gravação atual? Todos os quadros capturados serão apagados."),
            _Box.StandardButton.Yes | _Box.StandardButton.No,
            _Box.StandardButton.No,
        )
        if reply == _Box.StandardButton.Yes:
            self._engine.discard_recording()

    def save(self) -> bool:
        """Escolhe o arquivo e exporta (MP4 ou ZIP) em segundo plano. True se começou."""
        engine = self._engine
        # Aguarda qualquer gravação assíncrona pendente no pool de threads.
        QtCore.QThreadPool.globalInstance().waitForDone(1500)
        if engine.frame_count == 0:
            _Box.warning(self._parent, tr("recording.warning", "Aviso"),
                         tr("recording.no_frames", "Nenhum quadro foi capturado para exportar."))
            return False

        fmt = self._export_format()  # "mp4" ou "zip"
        is_mp4 = fmt == "mp4"
        ext = ".mp4" if is_mp4 else ".zip"
        filter_str = (tr("recording.filter_mp4", "Vídeo MP4 (*.mp4)") if is_mp4
                      else tr("recording.filter_zip", "Arquivo ZIP (*.zip)"))
        default_name = os.path.join(self._output_dir(), f"lumenia_timelapse{ext}")
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._parent, tr("recording.save_dialog", "Salvar Gravação"), default_name, filter_str)
        if not save_path:
            return False

        temp_dir = engine.stop_recording()
        if not temp_dir:
            return False

        dialog = TimelapseExportDialog(self._parent)
        worker = TimelapseExportWorker(temp_dir, engine.frame_count, dialog, fps=engine.fps)
        worker.progress.connect(dialog.update_progress)
        dialog.cancel_requested.connect(worker.cancel)

        def on_finished(success: bool, message: str, _path: str) -> None:
            dialog.close()
            if success:
                _Box.information(self._parent, tr("recording.export_done_title", "Exportação Concluída"), message)
            else:
                _Box.warning(self._parent, tr("recording.export_failed_title", "Exportação Cancelada"), message)
            engine.finish_session()

        worker.finished.connect(on_finished)
        dialog.show()
        worker.export(save_path, fmt, fps=engine.fps)
        return True
