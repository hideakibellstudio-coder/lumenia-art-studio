"""DynamicStackedWidget — QStackedWidget cujo tamanho é o da página visível.

O QStackedWidget padrão mede pela maior página; a barra secundária precisa
encolher para a ferramenta atual. Quem troca a página (a barra) chama
`adjustSize()` e avisa o workspace; este widget só recalcula a geometria.
Até 2026-09-24 ele também subia a árvore de widgets procurando um
`update_toolbar_position` no avô (`hasattr`).
"""

from typing import Optional
from PySide6 import QtCore, QtWidgets


class DynamicStackedWidget(QtWidgets.QStackedWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.currentChanged.connect(lambda _index: self.updateGeometry())

    def sizeHint(self) -> QtCore.QSize:
        cur = self.currentWidget()
        return cur.sizeHint() if cur is not None else super().sizeHint()

    def minimumSizeHint(self) -> QtCore.QSize:
        cur = self.currentWidget()
        return cur.minimumSizeHint() if cur is not None else super().minimumSizeHint()
