"""
LumeniaSplashScreen — Banner de Inicialização Moderno e Dinâmico
================================================================
Apresenta o logo oficial do Lumenia, barra de progresso estilizada
com as cores oficiais (violeta/lilás) e exibição em tempo real
dos módulos do sistema sendo carregados.
"""

import os
from PySide6 import QtWidgets, QtCore, QtGui
from ui.infrastructure.app_info import APP_DISPLAY_VERSION
from ui.infrastructure.runtime_paths import resource_path


class LumeniaSplashScreen(QtWidgets.QWidget):
    """
    Tela de Splash moderna, sem bordas (Frameless), com cantos arredondados,
    sombra suave e barra de carregamento progressiva dos módulos.
    """

    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.SplashScreen)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setFixedSize(540, 360)

        # Caminho do ícone oficial
        self.icon_path = str(resource_path("assets", "images", "icon_lumenia.png"))

        self._build_ui()
        self._center_on_screen()

    def _center_on_screen(self):
        """Centraliza o splash screen na tela principal do monitor."""
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Container Principal (Cápsula com sombra)
        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName("SplashContainer")

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(shadow)

        cont_layout = QtWidgets.QVBoxLayout(self.container)
        cont_layout.setContentsMargins(28, 28, 28, 24)
        cont_layout.setSpacing(14)

        # ── Topo: Logo Oficial e Títulos ────────────────────────────────────
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(18)

        # Logo Oficial
        self.lbl_logo = QtWidgets.QLabel()
        self.lbl_logo.setFixedSize(84, 84)
        self.lbl_logo.setScaledContents(True)
        if os.path.exists(self.icon_path):
            pix = QtGui.QPixmap(self.icon_path).scaled(
                84, 84, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            self.lbl_logo.setPixmap(pix)
        else:
            self.lbl_logo.setText("🎨")
            self.lbl_logo.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(self.lbl_logo)

        # Títulos e Versão
        title_vbox = QtWidgets.QVBoxLayout()
        title_vbox.setSpacing(2)
        title_vbox.setAlignment(QtCore.Qt.AlignVCenter)

        lbl_app_name = QtWidgets.QLabel("LUMENIA")
        lbl_app_name.setStyleSheet("""
            font-size: 32px;
            font-weight: 800;
            letter-spacing: 3px;
            color: #ffffff;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        """)

        lbl_subtitle = QtWidgets.QLabel("Digital Art & Paint Studio")
        lbl_subtitle.setStyleSheet("""
            font-size: 13px;
            font-weight: 500;
            color: #c084fc;
            letter-spacing: 0.5px;
        """)

        badge_hbox = QtWidgets.QHBoxLayout()
        badge_hbox.setSpacing(8)
        
        lbl_badge = QtWidgets.QLabel(f"v{APP_DISPLAY_VERSION} • ALADYN C++ Native Core")
        lbl_badge.setStyleSheet("""
            background-color: rgba(147, 51, 234, 0.25);
            color: #d8b4fe;
            border: 1px solid rgba(168, 85, 247, 0.4);
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 600;
        """)
        badge_hbox.addWidget(lbl_badge)
        badge_hbox.addStretch()

        title_vbox.addWidget(lbl_app_name)
        title_vbox.addWidget(lbl_subtitle)
        title_vbox.addSpacing(4)
        title_vbox.addLayout(badge_hbox)

        header_layout.addLayout(title_vbox)
        cont_layout.addLayout(header_layout)

        cont_layout.addStretch()

        # ── Rodapé: Status do Módulo e Barra de Progresso ───────────────────
        status_box = QtWidgets.QVBoxLayout()
        status_box.setSpacing(6)

        self.lbl_status = QtWidgets.QLabel("Iniciando módulos do sistema...")
        self.lbl_status.setStyleSheet("""
            font-size: 11px;
            color: #a1a1aa;
            font-weight: 500;
        """)
        status_box.addWidget(self.lbl_status)

        # Barra de Progresso Estilizada
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #7e22ce,
                    stop: 0.5 #9333ea,
                    stop: 1 #c084fc
                );
                border-radius: 3px;
            }
        """)
        status_box.addWidget(self.progress_bar)

        lbl_copyright = QtWidgets.QLabel("© 2026 Lumenia Team • Alta Performance GPU/CPU")
        lbl_copyright.setStyleSheet("font-size: 9px; color: #71717a; margin-top: 4px;")
        lbl_copyright.setAlignment(QtCore.Qt.AlignRight)
        status_box.addWidget(lbl_copyright)

        cont_layout.addLayout(status_box)

        main_layout.addWidget(self.container)

        # Estilo da Cápsula com degradê Obsidian Violet
        self.container.setStyleSheet("""
            #SplashContainer {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #13111c,
                    stop: 0.6 #181524,
                    stop: 1 #1f1a30
                );
                border: 1px solid #342c4c;
                border-radius: 14px;
            }
        """)

    def set_progress(self, value: int, message: str = ""):
        """Atualiza a porcentagem e a mensagem do módulo sendo carregado."""
        self.progress_bar.setValue(max(0, min(100, value)))
        if message:
            self.lbl_status.setText(message)
        QtWidgets.QApplication.processEvents()

    def finish(self, main_window: QtWidgets.QMainWindow, callback=None):
        """Faz um fade-out suave e exibe a janela principal."""
        self.anim = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)

        def _on_fade_finished():
            self.close()
            main_window.showMaximized()
            main_window.raise_()
            main_window.activateWindow()
            if callback:
                callback()

        self.anim.finished.connect(_on_fade_finished)
        self.anim.start()
