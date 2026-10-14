"""GuideLayerCache — a camada estática das guias, pintada uma vez e reaproveitada.

Com uma guia ligada, cada movimento do mouse repinta o canvas inteiro (as linhas
que seguem o ponteiro cruzam a tela toda), e a pintura retraçava todas as linhas da
guia do zero: medido em 2026-10-12 no Windows (Qt raster, canvas 1812×951), 69 ms por
pintura com a perspectiva curvilinear completa, 29 ms na isométrica, contra 5 ms sem
guia. Só a parte que segue o ponteiro (trilho paralelo, raios de snap, anel do alvo)
muda de uma pintura para a outra; as linhas, curvas e alças dependem apenas da guia,
da simetria, da câmera e do tema.

Este colaborador pinta essa camada estática numa imagem do tamanho da tela e a desenha
de volta enquanto nada disso mudar. A chave é o conteúdo (impressão da guia e da simetria,
matriz da câmera, tamanho, escala do monitor, tema), não um aviso de "mudou": uma alça
arrastada em objeto ou um tema trocado nunca deixam a camada velha na tela. Zoom e pan
mudam a matriz a cada passo e repintam a camada, que custa o mesmo que antes mais uma
cópia da imagem.

A imagem pertence a este colaborador, não ao widget (Leis do Rio, nº 1): o widget só
mostra o que o `ViewportRenderer` pinta.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from PySide6 import QtCore, QtGui

from ..renderers.geometry_overlay_renderer import GeometryOverlayRenderer


def _fingerprint(state: Mapping[str, object]) -> str:
    """O conteúdo de um dicionário de guia ou simetria, comparável por igualdade."""
    return repr(tuple(state.items()))


@dataclass(frozen=True)
class GuideLayerView:
    """Tudo de que a camada estática depende. Duas vistas de mesma chave pintam pixels iguais."""

    size: QtCore.QSize
    pixel_ratio: float
    transform: QtGui.QTransform
    zoom: float
    theme: str
    guide: Mapping[str, object]
    symmetry: Mapping[str, object]

    def is_empty(self) -> bool:
        return self.guide.get("type", "none") == "none" and self.symmetry.get("mode", "none") == "none"

    def key(self) -> tuple:
        t = self.transform
        return (
            self.size.width(), self.size.height(), self.pixel_ratio,
            t.m11(), t.m12(), t.m21(), t.m22(), t.dx(), t.dy(),
            self.zoom, self.theme, _fingerprint(self.guide), _fingerprint(self.symmetry),
        )


class GuideLayerCache:
    """Guarda a camada estática das guias entre pinturas; pertence a um `ViewportRenderer`."""

    def __init__(self) -> None:
        self._image: QtGui.QImage | None = None
        self._key: tuple | None = None
        self.paints = 0  # quantas vezes a camada foi pintada do zero (testes e medições)

    def draw(self, painter: QtGui.QPainter, view: GuideLayerView, dirty: QtCore.QRect) -> None:
        """Desenha a camada na região suja `dirty` (coordenadas da tela), pintando-a antes se mudou."""
        if view.is_empty():
            self.release()
            return
        key = view.key()
        if key != self._key or self._image is None:
            self._paint(painter, view)
            self._key = key
        visible = dirty.intersected(QtCore.QRect(QtCore.QPoint(0, 0), view.size))
        if visible.isEmpty():
            return
        ratio = view.pixel_ratio
        source = QtCore.QRectF(visible.x() * ratio, visible.y() * ratio, visible.width() * ratio, visible.height() * ratio)
        painter.save()
        painter.resetTransform()
        painter.drawImage(QtCore.QRectF(visible), self._image, source)
        painter.restore()

    def release(self) -> None:
        """Sem guia nem simetria a imagem não serve; solta a memória (uma tela 4K são 33 MB)."""
        self._image = None
        self._key = None

    def _paint(self, painter: QtGui.QPainter, view: GuideLayerView) -> None:
        ratio = view.pixel_ratio
        pixels = QtCore.QSize(max(1, round(view.size.width() * ratio)), max(1, round(view.size.height() * ratio)))
        if self._image is None or self._image.size() != pixels or self._image.devicePixelRatio() != ratio:
            self._image = QtGui.QImage(pixels, QtGui.QImage.Format_ARGB32_Premultiplied)
            self._image.setDevicePixelRatio(ratio)
        self._image.fill(QtCore.Qt.transparent)

        layer = QtGui.QPainter(self._image)
        layer.setRenderHints(painter.renderHints())
        layer.setFont(painter.font())
        layer.setTransform(view.transform)
        GeometryOverlayRenderer.render_symmetry(layer, view.symmetry, view.zoom)
        GeometryOverlayRenderer.render_guides_static(layer, view.guide, view.zoom)
        layer.end()
        self.paints += 1
