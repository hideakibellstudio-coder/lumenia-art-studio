"""telemetry_common — o que as três telas de telemetria compartilham.

Cockpit em grade, painel de telemetria e diálogo de diagnóstico são views do
`TelemetryTracker`; aqui ficam as peças iguais entre elas:

- `banner_style(chave)`: cor do banner de diagnóstico por estado do pipeline;
- `copy_report(pai)`: copia o relatório único (`TelemetryTracker.generate_full_report`);
- `clear_undo_history(pai)`: o botão "Limpar Undo", que descarta de verdade o
  histórico do documento ativo (`DocumentHistory.clear` → motor nativo).

Até 2026-09-24 os dois botões "Limpar Undo" esvaziavam listas privadas do
backend (`_action_stack`, removida em 2026-10-01) e diziam "limpa com sucesso" sem tocar no
histórico do motor, que continuava ocupando a mesma RAM.
"""
from __future__ import annotations

from typing import Optional

from PySide6 import QtGui, QtWidgets

from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.core.engine.telemetry_tracker import TelemetryTracker
from ui.infrastructure.i18n import tr
from ui.infrastructure.theme.manager import ThemeManager

# Estado do pipeline -> token do tema (todos os temas têm os tokens)
_STATE_COLORS = {
    "PIPELINE_EQUILIBRADO": "SUCCESS",
    "GARGALO_BLIT": "DANGER",
    "GARGALO_RASTER": "TELEMETRY_STAGE_RASTER",
    "GARGALO_UNDO": "TELEMETRY_STAGE_UNDO",
    "GARGALO_COMPOSITOR": "TELEMETRY_STAGE_COMPOSITOR",
}


def banner_style(state_key: str, font_px: int = 10) -> str:
    """QSS do banner: fundo translúcido e borda na cor do estado."""
    token = _STATE_COLORS.get(state_key, _STATE_COLORS["PIPELINE_EQUILIBRADO"])
    base = QtGui.QColor(ThemeManager.instance().get_color(token))
    alpha = 0.15 if state_key == "PIPELINE_EQUILIBRADO" else 0.2
    return (
        f"background-color: rgba({base.red()},{base.green()},{base.blue()},{alpha}); "
        f"color: {base.lighter(140).name()}; border: 1px solid {base.name()}; border-radius: 4px; "
        f"font-size: {font_px}px; font-weight: bold;"
    )


def enable_capture() -> None:
    """Liga a coleta de métricas no motor (as telas de telemetria só leem)."""
    TelemetryTracker.instance().enable_capture()


def copy_report(parent: QtWidgets.QWidget, stay_on_top: Optional[bool] = None) -> str:
    """Copia o relatório completo para a área de transferência e avisa."""
    report = TelemetryTracker.instance().generate_full_report(stay_on_top)
    QtWidgets.QApplication.clipboard().setText(report)
    QtWidgets.QMessageBox.information(
        parent,
        tr("messages.telemetry_copied_title", "Relatório de Telemetria Copiado"),
        tr("messages.telemetry_copied",
           "Relatório completo de telemetria (20 medidores, diagnóstico do pipeline, picos de "
           "estresse e histórico de alterações de estado) copiado para a Área de Transferência."),
    )
    return report


def clear_active_history() -> tuple[bool, str]:
    """Descarta desfazer/refazer do documento ativo. Retorna (limpou?, mensagem)."""
    doc = DocumentManager.instance().active_document()
    if doc is None:
        return False, tr("status.no_document", "Nenhum documento aberto.")
    backend = EngineRegistry.instance().get_backend()
    if backend is None:
        return False, tr("messages.history_engine_unavailable", "Motor indisponível: o histórico não foi alterado.")
    try:
        cleared = doc.history.clear(backend)
    except RuntimeError as exc:  # motor apontando para outro documento
        return False, tr("messages.history_not_changed", "O histórico não foi alterado: {error}", error=exc)
    if not cleared:
        return False, tr("messages.history_busy",
                         "Não dá para limpar o histórico durante um traço ou uma operação de camadas.")
    return True, tr("messages.history_cleared", "Histórico de desfazer e refazer de “{name}” descartado.",
                    name=doc.name)


def clear_undo_history(parent: QtWidgets.QWidget) -> bool:
    """O botão "Limpar Undo": confirma, limpa e mostra o resultado real."""
    answer = QtWidgets.QMessageBox.question(
        parent,
        tr("messages.clear_history_title", "Limpar Histórico"),
        tr("messages.clear_history_question",
           "Descartar todo o histórico de desfazer e refazer do documento ativo?\n"
           "Isso libera a memória do histórico e não pode ser desfeito."),
    )
    if answer != QtWidgets.QMessageBox.StandardButton.Yes:
        return False
    cleared, message = clear_active_history()
    if cleared:
        QtWidgets.QMessageBox.information(parent, tr("messages.memory_title", "Memória"), message)
    else:
        QtWidgets.QMessageBox.warning(parent, tr("messages.memory_title", "Memória"), message)
    return cleared
