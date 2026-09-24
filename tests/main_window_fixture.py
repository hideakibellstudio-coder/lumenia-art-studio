"""Acesso compartilhado à MainWindow dos testes de integração.

O PluginManager é singleton: só a PRIMEIRA MainWindow do processo recebe o
WorkspaceCore (canvas, docas). E `QApplication.topLevelWidgets()` não tem ordem
garantida -- é um conjunto. Pegar "a primeira MainWindow da lista" fazia o
teste depender de ordem de memória e, às vezes, receber uma janela sem
workspace (achado em 2026-09-22, quando a suíte passou a limpar janelas
órfãs entre módulos). Não começa com `test_`, então não é coletado.
"""

from __future__ import annotations


def main_window_com_workspace():
    from ui.boundary.orchestrator.main_window import MainWindow

    from tests.qt_windows import top_level_widgets

    with top_level_widgets() as widgets:
        for widget in widgets:
            if isinstance(widget, MainWindow) and getattr(widget, "workspace", None) is not None:
                return widget
    return MainWindow()
