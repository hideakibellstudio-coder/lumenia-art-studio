"""
AppRunner — Orquestrador Canônico de Inicialização do Lumenia (ARCcC Pilar 1).
=============================================================================
Centraliza o ciclo de vida de boot, logging sênior, splash screen progressivo,
configuração global de ícones e transição para MainWindow.
"""

from __future__ import annotations

import sys
import logging
from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.logger import setup_senior_logging, get_logger
from ui.core.components.splash_screen import LumeniaSplashScreen
from ui.core.runtime_paths import resource_path
from ui.boundary.orchestrator.main_window import MainWindow


def launch(args: list[str] | None = None) -> int:
    """Ponto de entrada canônico para execução da aplicação Lumenia."""
    if args is None:
        args = sys.argv

    # 1. Configuração do Logging Sênior
    log_level = logging.DEBUG if "--debug" in args else logging.INFO
    setup_senior_logging(log_level)

    logger = get_logger("MainApp")
    logger.info("🎨 Inicializando Lumenia Brush Engine 2.0 (ARCcC Runtime)...")

    # 2. Inicialização da Aplicação Qt (desativa compressão de eventos para preservar cadência real da caneta/mouse)
    # (os dois atributos existem em todo Qt 6; o PySide6 é a versão mínima)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_CompressHighFrequencyEvents, False)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_CompressTabletEvents, False)


    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(args)

    # Injeta a folha de estilos do tema globalmente na QApplication (diálogos, popups e janelas)
    from ui.core.theme.manager import ThemeManager
    app.setStyleSheet(ThemeManager.instance().get_stylesheet())

    # 3. Ícone Oficial do Programa
    icon_path = resource_path("assets", "images", "icon_lumenia.png")
    if icon_path.is_file():
        app_icon = QtGui.QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

    # 4. Splash Screen Progressivo
    splash = LumeniaSplashScreen()
    splash.show()
    app.processEvents()

    modules = [
        (15, "Carregando ALADYN C++ Native Core (Catmull-Rom, SIMD)..."),
        (35, "Registrando Motores de Pincel (Inker, Marker, Watercolor, Oil)..."),
        (55, "Inicializando Sistema de Camadas e Modos de Mesclagem..."),
        (70, "Carregando Perfis de Cor e Prova de Cores (Display P3, sRGB)..."),
        (85, "Descobrindo Plugins do Workspace e Customizações..."),
        (95, "Montando Espaço de Trabalho e Canvas de Alta Fidelidade..."),
        (100, "Lumenia Pronto para Criar!"),
    ]

    for pct, msg in modules:
        splash.set_progress(pct, msg)
        logger.info(f"[{pct}%] {msg}")
        QtCore.QThread.msleep(25)
        app.processEvents()

    # 5. Construção da Janela Principal e Transição
    window = MainWindow()
    splash.finish(window)

    logger.info("✨ Lumenia 2.0 inicializado e pronto para interação do usuário.")
    return app.exec()
