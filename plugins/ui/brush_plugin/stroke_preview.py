"""
StrokePreview  (portado de BrushC/src/ui/components/stroke_preview.py)
────────────────────────────────────────────────────────────────────────
Renderiza uma senoide que simula o traço do brush atual de forma dinâmica,
respeitando o diâmetro, a opacidade, o espaçamento de carimbo e a dureza.
Widget puro Qt, sem dependências externas.
"""
import math
from PySide6 import QtWidgets, QtCore, QtGui


class StrokePreview(QtWidgets.QWidget):
    DEFAULT_HEIGHT = 52

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.DEFAULT_HEIGHT)
        self.setMinimumWidth(80)

        # Estado inicial do pincel
        self._size     = 60.0
        self._opacity  = 1.0
        self._hardness = 1.0
        self._spacing  = 0.10  # 10% por padrão
        self._pressure = 0.50  # 50% por padrão
        self._color    = [0.0, 0.0, 0.0]

    def update_preview(self):
        self.update()

    def update_brush_state(self,
                           size: float = None,
                           opacity: float = None,
                           hardness: float = None,
                           spacing: float = None,
                           pressure: float = None,
                           color: list = None):
        """Atualiza parcialmente ou totalmente os estados de traço do preview."""
        if size is not None:     self._size = size
        if opacity is not None:  self._opacity = opacity
        if hardness is not None: self._hardness = hardness
        if spacing is not None:  self._spacing = spacing
        if pressure is not None: self._pressure = pressure
        if color is not None:    self._color = color
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # 1. Desenha o fundo de tabuleiro quadriculado (Checkerboard)
        p.fillRect(self.rect(), QtCore.Qt.white)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(220, 220, 220))
        sq = 8
        for x in range(0, self.width(), sq):
            for y in range(0, self.height(), sq):
                if (x // sq + y // sq) % 2 == 1:
                    p.drawRect(x, y, sq, sq)

        w, h = self.width(), self.height()
        margin = 10
        amp = (h / 2) - margin

        c = self._color
        base_color = QtGui.QColor(
            int(c[0] * 255), int(c[1] * 255), int(c[2] * 255)
        )

        # 2. Desenha o traço em um buffer temporário transparente
        img = QtGui.QImage(self.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
        img.fill(QtCore.Qt.transparent)

        ip = QtGui.QPainter(img)
        ip.setRenderHint(QtGui.QPainter.Antialiasing)
        ip.setPen(QtCore.Qt.NoPen)

        # Passo do carimbo calculado dinamicamente com base no tamanho e espaçamento (%)
        passo_pixels = max(1.0, self._size * self._spacing)

        x_atual = float(margin)
        largura_util = float(w - 2 * margin)

        while x_atual < (w - margin):
            # Calcula o progresso t (0.0 a 1.0)
            t = (x_atual - margin) / largura_util if largura_util > 0 else 0.0
            
            # Coordenada Y da senoide
            y = h / 2 + math.sin(t * math.pi * 2) * amp * 0.65
            
            # Variação de pressão simulada (começo e fim finos) multiplicada pela pressão configurada
            pressure_sim = self._pressure * (0.3 + 0.7 * math.sin(t * math.pi))
            
            # Raio do carimbo
            r = (self._size * pressure_sim) / 2.0
            if r < 0.25:
                r = 0.25 # Garante visibilidade mínima

            # Cria ponta esfumaçada proporcional à dureza (hardness) usando gradiente radial
            grad = QtGui.QRadialGradient(QtCore.QPointF(x_atual, y), r)
            alpha = int(self._opacity * 255)
            
            # Hardness define onde inicia a interpolação suave até o preto transparente
            stop = max(0.01, min(0.99, self._hardness))
            
            grad.setColorAt(0, QtGui.QColor(base_color.red(), base_color.green(), base_color.blue(), alpha))
            grad.setColorAt(stop, QtGui.QColor(base_color.red(), base_color.green(), base_color.blue(), alpha))
            grad.setColorAt(1.0, QtGui.QColor(base_color.red(), base_color.green(), base_color.blue(), 0))
            
            ip.setBrush(grad)
            ip.drawEllipse(QtCore.QPointF(x_atual, y), r, r)
            
            # Avança o X pelo passo calculado
            x_atual += passo_pixels

        ip.end()

        # Renderiza o traço final sobre o fundo quadriculado
        p.drawImage(0, 0, img)

        # 3. Contorno visual arredondado do widget
        p.setPen(QtGui.QPen(QtGui.QColor(128, 128, 128, 60), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)
        p.end()
