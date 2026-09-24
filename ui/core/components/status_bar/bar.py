from PySide6 import QtWidgets

from ui.core.i18n import tr


class StatusBar(QtWidgets.QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_lbl = QtWidgets.QLabel()
        self.addPermanentWidget(self.zoom_lbl)
        self.update_zoom(1.0)
        self.showMessage(tr("status.engine_ready_hint",
                            "Lumenia Engine Pronta. Arraste com o botão do meio para mover, use Scroll para zoom."))

    def update_zoom(self, zoom: float):
        self.zoom_lbl.setText(tr("status.zoom", "Zoom: {percent}%", percent=int(zoom * 100)))
