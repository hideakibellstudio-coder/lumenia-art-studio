from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.document.manager import DocumentManager
from ui.infrastructure.icons import get_icon

class TabCloseButton(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        
    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        
        # Tamanho do quadrado visível fixo em 16x16
        size = 16
        # Desloca a pintura do quadrado visível de 16x16 para o lado esquerdo (2px de offset), 
        # criando uma margem de segurança transparente de 8px na direita (dentro do widget de 26px)
        rect = QtCore.QRect(
            2,
            (self.height() - size) // 2,
            size,
            size
        )
        
        from ui.infrastructure.theme.manager import ThemeManager
        colors = ThemeManager.instance()._themes.get(ThemeManager.instance().current_theme, {}).get("colors", {})
        
        # Determina se está sob o cursor para pintar o fundo azul ou manter transparente
        is_hovered = self.underMouse()
        if is_hovered:
            accent_color = QtGui.QColor(ThemeManager.instance().resolve_color("ACCENT", colors))
            painter.setBrush(accent_color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(rect, 4, 4)  # Cantos arredondados com raio 4 (quadrado com cantos arredondados)
            icon_color = QtGui.QColor(ThemeManager.instance().resolve_color("FG_PRIMARY", colors))
        else:
            icon_color = QtGui.QColor(ThemeManager.instance().resolve_color("FG_SECONDARY", colors))
            
        # Desenha a cruz "X" vetorizada com alta qualidade
        painter.setPen(QtGui.QPen(icon_color, 1.5, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
        pad = 5
        x1 = rect.left() + pad
        y1 = rect.top() + pad
        x2 = rect.right() - pad
        y2 = rect.bottom() - pad
        
        painter.drawLine(x1, y1, x2, y2)
        painter.drawLine(x2, y1, x1, y2)
        
        painter.end()

class TabbedViewportContainer(QtWidgets.QWidget):
    activeTabChanged = QtCore.Signal(str)  # Emite o uid do documento ativo
    newDocumentRequested = QtCore.Signal()
    documentCloseRequested = QtCore.Signal(str)

    def __init__(self, canvas_widget, parent=None):
        super().__init__(parent)
        self.canvas_widget = canvas_widget
        self.dm = DocumentManager.instance()

        self.setup_ui()
        self.connect_signals()
        self._apply_theme()

    def setup_ui(self):
        # Layout vertical principal
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Barra superior com Abas e botão Novo (+)
        self.header_widget = QtWidgets.QWidget()
        self.header_widget.setObjectName("ViewportHeader")
        self.header_widget.setFixedHeight(34)
        
        self.header_layout = QtWidgets.QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(8, 0, 8, 0)
        self.header_layout.setSpacing(8)

        # Barra de Abas (TabBar)
        self.tab_bar = QtWidgets.QTabBar()
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setMovable(True)
        self.tab_bar.setSelectionBehaviorOnRemove(QtWidgets.QTabBar.SelectPreviousTab)
        self.tab_bar.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        self.tab_bar.setVisible(False)
        
        self.header_layout.addWidget(self.tab_bar)

        # Botão Nova Aba (+)
        self.btn_new_tab = QtWidgets.QToolButton()
        self.btn_new_tab.setObjectName("NewTabButton")
        self.btn_new_tab.setIcon(get_icon("plus", "FG_SECONDARY"))
        self.btn_new_tab.setToolTip("Criar novo canvas de desenho")
        self.btn_new_tab.setFixedSize(20, 20)
        
        self.header_layout.addWidget(self.btn_new_tab)
        self.header_layout.addStretch()

        # Adiciona o Canvas de Desenho físico no centro
        self.main_layout.addWidget(self.canvas_widget, 1)





    def set_header_insets(self, left_inset: int = 8, right_inset: int = 8) -> None:
        """Mantém margens estáticas permanentes sem deslocar as abas MDI."""
        self.header_layout.setContentsMargins(8, 0, 8, 0)



    def connect_signals(self):
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        self.btn_new_tab.clicked.connect(self._on_btn_new_tab_clicked)
        
        # Conecta eventos do DocumentManager
        self.dm.documentAdded.connect(self._on_document_added)
        self.dm.documentClosed.connect(self._on_document_closed)
        
        # Sincroniza tema e escala
        from ui.infrastructure.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        ThemeManager.instance().scaleChanged.connect(self._apply_scale)
        self._apply_scale()

    def _apply_theme(self, theme_name=None):
        from ui.infrastructure.theme.manager import ThemeManager

        # QSS unificado do contêiner e abas com alinhamento vertical e cor de hover vermelha para fechar
        qss = """
            QWidget#ViewportHeader {
                background-color: @BG_DARKEST;
                border-bottom: 1px solid @BORDER;
            }
            QTabBar {
                border: none;
            }
            QTabBar::tab {
                background-color: @BG_DARKER;
                color: @FG_SECONDARY;
                border: 1px solid @BORDER;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 28px 6px 14px; /* Padding à direita para o botão fechar */
                min-width: 100px;
                max-width: 180px;
                margin-right: 3px;
                margin-top: 5px;
                font-family: @FONT_FAMILY;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: @BG_DARK;
                color: @FG_PRIMARY;
                font-weight: bold;
                border-bottom: 2px solid @ACCENT;
                margin-top: 3px;
            }
            QTabBar::tab:hover:!selected {
                background-color: @BG_MID;
                color: @FG_PRIMARY;
            }

            QToolButton#TabCloseButton {
                background: transparent;
                border: none;
            }
            QToolButton#NewTabButton {
                background-color: @BG_DARKER;
                border: 1px solid @BORDER;
                border-radius: 10px;
            }
            QToolButton#NewTabButton:hover {
                background-color: @BG_MID;
                border-color: @ACCENT;
            }
        """
        compiled = ThemeManager.instance().compile_qss(qss)
        self.setStyleSheet(compiled)

        # Repinta o ícone do botão de novo tema
        self.btn_new_tab.setIcon(get_icon("plus", "FG_SECONDARY"))

    def _apply_scale(self, scale: float | None = None) -> None:
        """Adapta a altura do cabeçalho de abas e botões à escala global da interface."""
        from ui.infrastructure.theme.manager import ThemeManager
        s = scale if scale is not None else ThemeManager.instance().ui_scale
        h = max(24, int(34 * s))
        self.header_widget.setFixedHeight(h)
        btn_sz = max(16, int(20 * s))
        self.btn_new_tab.setFixedSize(btn_sz, btn_sz)
        self._apply_theme()

    def _on_tab_changed(self, index: int):
        if index < 0:
            return
        uid = self.tab_bar.tabData(index)
        if uid:
            self.dm.set_active_document(uid)
            self.activeTabChanged.emit(uid)

    def _on_tab_close_requested(self, index: int):
        uid = self.tab_bar.tabData(index)
        if uid:
            self.documentCloseRequested.emit(uid)

    def _on_btn_new_tab_clicked(self):
        self.newDocumentRequested.emit()

    def _on_document_added(self, doc):
        # Evita duplicatas na tab bar
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabData(i) == doc.uid:
                return
                
        index = self.tab_bar.addTab(doc.name)
        self.tab_bar.setTabData(index, doc.uid)
        
        # Cria botão de fechar customizado, quadrado arredondado e premium
        close_btn = TabCloseButton(self)
        close_btn.setObjectName("TabCloseButton")
        close_btn.setFixedSize(26, 16)
        
        uid = doc.uid
        close_btn.clicked.connect(lambda: self.documentCloseRequested.emit(uid))
        self.tab_bar.setTabButton(index, QtWidgets.QTabBar.RightSide, close_btn)
        
        # Ativa a aba recém-criada
        self.tab_bar.setCurrentIndex(index)
        self.tab_bar.setVisible(True)

    def _on_document_closed(self, uid: str):
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabData(i) == uid:
                # removeTab não destrói o botão de fechar: sem o deleteLater, cada
                # documento fechado deixava um TabCloseButton (e o lambda dele) vivo.
                close_button = self.tab_bar.tabButton(i, QtWidgets.QTabBar.RightSide)
                self.tab_bar.removeTab(i)
                if close_button is not None:
                    close_button.deleteLater()
                break
                
        # Se fechar a última aba, desabilita a interação com o canvas e oculta a barra
        if self.tab_bar.count() == 0:
            self.tab_bar.setVisible(False)
            self.canvas_widget.setEnabled(False)
        else:
            self.canvas_widget.setEnabled(True)

    def sync_active_tab(self, uid: str):
        """Atualiza a seleção visual da TabBar sem re-disparar sinais indesejados."""
        self.tab_bar.setVisible(True)
        self.tab_bar.blockSignals(True)
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabData(i) == uid:
                self.tab_bar.setCurrentIndex(i)
                break
        self.tab_bar.blockSignals(False)
        self.canvas_widget.setEnabled(True)
