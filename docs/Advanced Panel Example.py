import sys
import math
from PySide6 import QtWidgets, QtCore, QtGui, QtSvg

# SVG da ponta de fechar em Feather style
CLOSE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
</svg>"""

def svg_to_icon(svg_xml: str, size: QtCore.QSize = QtCore.QSize(16, 16)) -> QtGui.QIcon:
    byte_array = QtCore.QByteArray(svg_xml.encode('utf-8'))
    renderer = QtSvg.QSvgRenderer(byte_array)
    pixmap = QtGui.QPixmap(size)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QtGui.QIcon(pixmap)


class NonScrollSlider(QtWidgets.QSlider):
    """Subclasse de QSlider que ignora rolagem do mouse."""
    def wheelEvent(self, event):
        event.ignore()


class LabeledSliderExample(QtWidgets.QWidget):
    """Controle com título, valor numérico e slider sem rolagem."""
    def __init__(self, label_text: str, min_v: int, max_v: int, default_v: int, suffix: str = "", parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        hl = QtWidgets.QHBoxLayout()
        self.lbl_title = QtWidgets.QLabel(label_text)
        self.lbl_val = QtWidgets.QLabel(f"{default_v}{suffix}")
        self.lbl_val.setStyleSheet("font-weight: bold; color: #3b82f6;")
        hl.addWidget(self.lbl_title)
        hl.addWidget(self.lbl_val)
        layout.addLayout(hl)

        self.slider = NonScrollSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(min_v, max_v)
        self.slider.setValue(default_v)
        self.slider.valueChanged.connect(lambda v: self.lbl_val.setText(f"{v}{suffix}"))
        layout.addWidget(self.slider)


class CollapsibleSectionExample(QtWidgets.QWidget):
    """Seção colapsável estilizada com título e seta indicativa."""
    def __init__(self, title: str, expanded: bool = True, parent=None):
        super().__init__(parent)
        self._expanded = expanded
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header button
        self.header = QtWidgets.QWidget()
        self.header.setObjectName("CollapsHeader")
        self.header.setFixedHeight(24)
        self.header.setCursor(QtCore.Qt.PointingHandCursor)
        self.header.mousePressEvent = self._toggle
        
        hl = QtWidgets.QHBoxLayout(self.header)
        hl.setContentsMargins(6, 0, 6, 0)
        
        self.arrow = QtWidgets.QLabel("▼" if expanded else "▶")
        self.arrow.setObjectName("CollapsArrow")
        self.lbl_title = QtWidgets.QLabel(title)
        self.lbl_title.setObjectName("CollapsTitle")
        
        hl.addWidget(self.arrow)
        hl.addWidget(self.lbl_title, 1)

        # Content area
        self.content_widget = QtWidgets.QWidget()
        self.content_widget.setObjectName("CollapsContent")
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 4, 8, 4)
        self.content_layout.setSpacing(6)

        layout.addWidget(self.header)
        layout.addWidget(self.content_widget)
        
        self.content_widget.setVisible(expanded)

    def add_widget(self, widget: QtWidgets.QWidget):
        self.content_layout.addWidget(widget)

    def _toggle(self, event):
        self._expanded = not self._expanded
        self.arrow.setText("▼" if self._expanded else "▶")
        self.content_widget.setVisible(self._expanded)


class AdvancedPanelExample(QtWidgets.QDialog):
    """Janela flutuante de exemplo com todas as correções estruturais e visuais."""
    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setFixedWidth(300)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._drag_pos = None

        self._build_ui()
        self._apply_theme()

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & QtCore.Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def show_near(self, anchor_widget: QtWidgets.QWidget):
        mpos = anchor_widget.mapToGlobal(QtCore.QPoint(0, 0))
        mw = anchor_widget.width()
        pos = QtCore.QPoint(mpos.x() + mw + 6, mpos.y())
        self.move(pos)
        self.show()
        self.raise_()
        self.activateWindow()

    def _build_ui(self):
        # 1. Layout principal da Dialog (translúcida) com margem 0
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 2. Contêiner de estilo
        self.container = QtWidgets.QWidget()
        self.container.setObjectName("AdvContainer")
        main_layout.addWidget(self.container)

        # 3. Layout interno do contêiner com 1px de recuo (Abordagem 2)
        outer = QtWidgets.QVBoxLayout(self.container)
        outer.setContentsMargins(1, 0, 1, 1)
        outer.setSpacing(0)

        # Barra de Título
        title_bar = QtWidgets.QWidget()
        title_bar.setObjectName("AdvTitleBar")
        title_bar.setFixedHeight(34)
        tbl = QtWidgets.QHBoxLayout(title_bar)
        tbl.setContentsMargins(10, 0, 8, 0)
        
        lbl_icon = QtWidgets.QLabel("⚙")
        lbl_icon.setObjectName("AdvTitleIcon")
        lbl_title = QtWidgets.QLabel("Configurações Avançadas")
        lbl_title.setObjectName("AdvTitleLabel")
        
        self.btn_close = QtWidgets.QToolButton()
        self.btn_close.setObjectName("AdvCloseBtn")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setIconSize(QtCore.QSize(12, 12))
        self.btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide)
        
        tbl.addWidget(lbl_icon)
        tbl.addWidget(lbl_title)
        tbl.addStretch()
        tbl.addWidget(self.btn_close)
        outer.addWidget(title_bar)

        # Divisor
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setObjectName("AdvSep")
        outer.addWidget(sep)

        # Tab Bar esticada de largura igual
        self.tab_bar = QtWidgets.QTabBar()
        self.tab_bar.setExpanding(True)
        self.tab_bar.addTab("Pincel")
        self.tab_bar.addTab("Dinâmica")
        self.tab_bar.setObjectName("AdvTabBar")

        tab_wrap = QtWidgets.QWidget()
        tab_wrap.setObjectName("AdvTabWrap")
        tw = QtWidgets.QHBoxLayout(tab_wrap)
        tw.setContentsMargins(8, 6, 8, 0)
        tw.addWidget(self.tab_bar, 1)
        outer.addWidget(tab_wrap)

        # QStackedWidget e QScrollArea
        self.stack = QtWidgets.QStackedWidget()
        outer.addWidget(self.stack)

        # Página Pincel com área de rolagem
        page_brush = QtWidgets.QWidget()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        scroll_content = QtWidgets.QWidget()
        pb = QtWidgets.QVBoxLayout(scroll_content)
        pb.setContentsMargins(8, 4, 8, 8)
        pb.setSpacing(6)

        # ── 1. Ponta (Forma) no Topo
        sec_ponta = CollapsibleSectionExample("Ponta (Forma)", expanded=True)
        ponta_header = QtWidgets.QHBoxLayout()
        shape_preview = QtWidgets.QLabel()
        shape_preview.setFixedSize(48, 48)
        shape_preview.setObjectName("BTexPreview")
        shape_preview.setStyleSheet("border: 1px solid #334155; border-radius: 4px; background: #101010;")
        # Desenha círculo branco simulando preview de ponta
        pm = QtGui.QPixmap(48, 48)
        pm.fill(QtGui.QColor(16, 16, 16))
        pt = QtGui.QPainter(pm)
        pt.setRenderHint(QtGui.QPainter.Antialiasing)
        grad = QtGui.QRadialGradient(24, 24, 24)
        grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 255))
        grad.setColorAt(0.8, QtGui.QColor(255, 255, 255, 200))
        grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
        pt.setBrush(QtGui.QBrush(grad))
        pt.setPen(QtCore.Qt.NoPen)
        pt.drawRect(0, 0, 48, 48)
        pt.end()
        shape_preview.setPixmap(pm)
        ponta_header.addWidget(shape_preview)

        ponta_info = QtWidgets.QWidget()
        ponta_info_layout = QtWidgets.QVBoxLayout(ponta_info)
        ponta_info_layout.setContentsMargins(4, 0, 0, 0)
        ponta_info_layout.setSpacing(4)
        ponta_lbl = QtWidgets.QLabel("Ponta do Pincel")
        ponta_lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
        btn_load_shape = QtWidgets.QPushButton("Carregar")
        btn_load_shape.setObjectName("BTexBtn")
        btn_load_shape.setFixedSize(60, 20)
        ponta_info_layout.addWidget(ponta_lbl)
        ponta_info_layout.addWidget(btn_load_shape)
        ponta_info_layout.addStretch()
        ponta_header.addWidget(ponta_info, 1)

        ponta_box = QtWidgets.QWidget()
        p_box_lo = QtWidgets.QVBoxLayout(ponta_box)
        p_box_lo.setContentsMargins(0, 0, 0, 0)
        p_box_lo.setSpacing(6)
        p_box_lo.addLayout(ponta_header)
        p_box_lo.addWidget(LabeledSliderExample("Contraste (Dureza):", 1, 30, 10, ""))
        sec_ponta.add_widget(ponta_box)
        pb.addWidget(sec_ponta)

        # ── 2. Relevo (Textura) logo abaixo
        sec_relevo = CollapsibleSectionExample("Relevo (Textura)", expanded=True)
        relevo_header = QtWidgets.QHBoxLayout()
        heightmap_preview = QtWidgets.QLabel()
        heightmap_preview.setFixedSize(48, 48)
        heightmap_preview.setObjectName("BTexPreview")
        heightmap_preview.setStyleSheet("border: 1px solid #334155; border-radius: 4px; background: #101010;")
        # Desenha ruído de seno simulando preview de textura
        pm2 = QtGui.QPixmap(48, 48)
        pm2.fill(QtGui.QColor(16, 16, 16))
        pt2 = QtGui.QPainter(pm2)
        for y in range(48):
            for x in range(48):
                val = int(127 + 100 * math.sin(x * 0.3) * math.cos(y * 0.3))
                val = max(0, min(255, val))
                pt2.setPen(QtGui.QColor(val, val, val))
                pt2.drawPoint(x, y)
        pt2.end()
        heightmap_preview.setPixmap(pm2)
        relevo_header.addWidget(heightmap_preview)

        relevo_info = QtWidgets.QWidget()
        relevo_info_layout = QtWidgets.QVBoxLayout(relevo_info)
        relevo_info_layout.setContentsMargins(4, 0, 0, 0)
        relevo_info_layout.setSpacing(4)
        relevo_lbl = QtWidgets.QLabel("Textura de Relevo")
        relevo_lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
        btn_load_heightmap = QtWidgets.QPushButton("Carregar")
        btn_load_heightmap.setObjectName("BTexBtn")
        btn_load_heightmap.setFixedSize(60, 20)
        relevo_info_layout.addWidget(relevo_lbl)
        relevo_info_layout.addWidget(btn_load_heightmap)
        relevo_info_layout.addStretch()
        relevo_header.addWidget(relevo_info, 1)

        relevo_box = QtWidgets.QWidget()
        r_box_lo = QtWidgets.QVBoxLayout(relevo_box)
        r_box_lo.setContentsMargins(0, 0, 0, 0)
        r_box_lo.setSpacing(6)
        r_box_lo.addLayout(relevo_header)
        r_box_lo.addWidget(QtWidgets.QCheckBox("Inverter Topografia"))
        sec_relevo.add_widget(relevo_box)
        pb.addWidget(sec_relevo)

        # ── 3. Tamanho e Opacidade
        sec_size_opac = CollapsibleSectionExample("Parâmetros Rápidos", expanded=True)
        sec_size_opac.add_widget(LabeledSliderExample("Tamanho:", 10, 200, 60, "px"))
        sec_size_opac.add_widget(LabeledSliderExample("Opacidade:", 1, 100, 100, "%"))
        pb.addWidget(sec_size_opac)

        # ── 4. Entrada de Pressão
        sec_press = CollapsibleSectionExample("Entrada de Pressão", expanded=True)
        sec_press.add_widget(LabeledSliderExample("Pressão (Mouse):", 1, 100, 50, "%"))
        sec_press.add_widget(LabeledSliderExample("Curva de Pressão (Stylus):", 1, 40, 10, ""))
        pb.addWidget(sec_press)

        # ── 5. Estabilização
        sec_stab = CollapsibleSectionExample("Estabilização", expanded=True)
        sec_stab.add_widget(LabeledSliderExample("Suavização (Estabilizador):", 0, 95, 0, "%"))
        pb.addWidget(sec_stab)

        # ── 6. Traço
        sec_trace = CollapsibleSectionExample("Traço", expanded=True)
        sec_trace.add_widget(LabeledSliderExample("Espaçamento:", 1, 100, 10, "%"))
        pb.addWidget(sec_trace)

        # Adiciona stretch no fim para empurrar o conteúdo
        pb.addStretch()

        scroll.setWidget(scroll_content)
        self.stack.addWidget(scroll)

        # Página Dinâmica Placeholder
        page_dyn = QtWidgets.QWidget()
        dl = QtWidgets.QVBoxLayout(page_dyn)
        lbl_dyn = QtWidgets.QLabel("Configurações de dinâmica e velocidade.")
        lbl_dyn.setAlignment(QtCore.Qt.AlignCenter)
        lbl_dyn.setObjectName("AdvMuted")
        dl.addStretch()
        dl.addWidget(lbl_dyn)
        dl.addStretch()
        self.stack.addWidget(page_dyn)

        self.tab_bar.currentChanged.connect(self.stack.setCurrentIndex)

    def _apply_theme(self):
        # Paleta de Cores simulada do Tema Escuro
        bg     = "#0f172a"
        bg2    = "#1e293b"
        text   = "#f8fafc"
        muted  = "#64748b"
        accent = "#3b82f6"
        border = "#334155"

        # Converte SVG Close para Icon colorido
        svg_xml = CLOSE_SVG.replace("{color}", text)
        self.btn_close.setIcon(svg_to_icon(svg_xml))

        self.setStyleSheet(f"""
            AdvancedPanelExample {{
                background: transparent;
                background-color: transparent;
            }}
            #AdvContainer {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            #AdvTitleBar {{
                background: {bg2};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            #AdvTitleLabel {{
                color: {text};
                font-weight: 600;
                font-size: 11px;
            }}
            #AdvTitleIcon {{
                color: {accent};
                font-size: 13px;
            }}
            #AdvCloseBtn {{
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            #AdvCloseBtn:hover { background: {accent}; }
            #AdvSep { color: {border}; }
            #AdvTabWrap { background: {bg}; }
            #AdvTabBar::tab {
                background: {bg2}; color: {muted}; padding: 4px 10px; border: 1px solid {border}; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; font-size: 10px;
            }
            #AdvTabBar::tab:selected { background: {accent}; color: {text}; font-weight: 600; }
            #AdvMuted { color: {muted}; font-size: 11px; }
            #BTexBtn { background: {bg2}; color: {text}; border: 1px solid {border}; border-radius: 3px; font-size: 10px; padding: 2px 4px; }
            #BTexBtn:hover { border-color: {accent}; color: {accent}; }
            #CollapsHeader { background: {bg2}; border-radius: 4px; }
            #CollapsHeader:hover { background: {accent}; }
            #CollapsArrow { color: {muted}; font-size: 10px; }
            #CollapsTitle { color: {text}; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
            #CollapsContent { background: transparent; }
            QStackedWidget, QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: transparent; }
            QStackedWidget, QScrollArea { border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; }
            QScrollArea > QWidget, QScrollArea > QWidget > QWidget { border-bottom-left-radius: 7px; border-bottom-right-radius: 7px; }
            QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 4px 4px 12px 0px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: {border}; border-radius: 4px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: {accent}; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { border: none; background: none; height: 0px; }
            QLabel, QCheckBox { color: {text}; font-size: 11px; }
            QSlider::groove:horizontal { height: 4px; background: {border}; border-radius: 2px; }
            QSlider::handle:horizontal { background: {accent}; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
        """)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Janela principal de testes atuando como âncora
    main_win = QtWidgets.QMainWindow()
    main_win.setWindowTitle("Lumenia Brush Engine - Exemplo de Janela Avançada")
    main_win.resize(600, 500)
    main_win.setStyleSheet("background: #090d16;")
    
    btn = QtWidgets.QPushButton("Abrir Janela Avançada", main_win)
    btn.setFixedSize(160, 30)
    btn.move(40, 20)
    
    panel = AdvancedPanelExample(main_win)
    btn.clicked.connect(lambda: panel.show_near(btn))
    
    main_win.show()
    sys.exit(app.exec())