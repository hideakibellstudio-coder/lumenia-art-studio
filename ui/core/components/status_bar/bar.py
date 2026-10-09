from PySide6 import QtCore, QtWidgets

from ui.infrastructure.i18n import tr


class StatusBar(QtWidgets.QStatusBar):
    """Messages, zoom and, while there is no license, the "Free version · Activate" button.

    The bar does not know about licenses: the window tells it whether the
    session is in free mode (`show_free_mode`) and connects `activateRequested`.
    """

    activateRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.free_mode_btn = QtWidgets.QPushButton()
        self.free_mode_btn.setFlat(True)
        self.free_mode_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.free_mode_btn.clicked.connect(self.activateRequested)
        self.free_mode_btn.setVisible(False)
        self.addPermanentWidget(self.free_mode_btn)
        self.zoom_lbl = QtWidgets.QLabel()
        self.addPermanentWidget(self.zoom_lbl)
        self.update_zoom(1.0)
        self.showMessage(tr("status.engine_ready_hint",
                            "Lumenia Engine Pronta. Arraste com o botão do meio para mover, use Scroll para zoom."))

    def update_zoom(self, zoom: float):
        self.zoom_lbl.setText(tr("status.zoom", "Zoom: {percent}%", percent=int(zoom * 100)))

    def show_free_mode(self, free: bool) -> None:
        self.free_mode_btn.setText(tr("status.free_mode", "Versão gratuita · Ativar"))
        self.free_mode_btn.setToolTip(tr("status.free_mode_tip",
                                         "As imagens exportadas saem com marca d'água. Clique para ativar sua licença."))
        self.free_mode_btn.setVisible(free)
