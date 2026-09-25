"""Non-scrollable QComboBox widget."""

from PySide6 import QtWidgets

class NonScrollComboBox(QtWidgets.QComboBox):
    """Subclasse de QComboBox que ignora a roda do mouse para permitir rolagem suave do painel."""
    def wheelEvent(self, event):
        event.ignore()
