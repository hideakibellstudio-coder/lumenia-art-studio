from PySide6 import QtWidgets

class StatusBar(QtWidgets.QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_lbl = QtWidgets.QLabel("Zoom: 100%")
        self.addPermanentWidget(self.zoom_lbl)
        self.showMessage("Lumenia Engine Pronta. Arraste com o botão do meio para mover, use Scroll para zoom.")

    def update_zoom(self, zoom: float):
        self.zoom_lbl.setText(f"Zoom: {int(zoom * 100)}%")
