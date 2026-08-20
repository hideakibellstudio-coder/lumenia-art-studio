import sys
import os
import time
import logging

# Adiciona o diretório pai (Lumenia/) para que 'ui' possa ser importado como pacote
# e para que aladyn_engine_native.pyd seja encontrado — único local canônico do binário
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.logger import setup_senior_logging, get_logger
from ui.core.components.splash_screen import LumeniaSplashScreen
from ui.boundary.orchestrator.main_window import MainWindow

if __name__ == "__main__":
    # Inicializa a infraestrutura de logging sênior no boot da aplicação
    log_level = logging.DEBUG if "--debug" in sys.argv else logging.INFO
    setup_senior_logging(log_level)

    logger = get_logger("MainApp")
    logger.info("🎨 Inicializando Lumenia Brush Engine 2.0...")

    app = QtWidgets.QApplication(sys.argv)

    # Configura o Ícone Oficial do Programa globalmente
    icon_path = os.path.join(parent_dir, "assets", "images", "icon_lumenia.png")
    if os.path.exists(icon_path):
        app_icon = QtGui.QIcon(icon_path)
        app.setWindowIcon(app_icon)

    # ── 1. Exibe o Splash Screen com o Banner de Inicialização ───────────
    splash = LumeniaSplashScreen()
    splash.show()
    app.processEvents()

    # ── 2. Carregamento Progressivo dos Módulos do Sistema ────────────────
    modules = [
        (15, "Carregando ALADYN C++ Native Core (Catmull-Rom, SIMD)..."),
        (35, "Registrando Motores de Pincel (Inker, Marker, Watercolor, Oil)..."),
        (55, "Inicializando Sistema de Camadas e Modos de Mesclagem..."),
        (70, "Carregando Perfis de Cor & Prova de Cores (Display P3, sRGB)..."),
        (85, "Descobrindo Plugins do Workspace e Customizações..."),
        (95, "Montando Espaço de Trabalho e Canvas de Alta Fidelidade..."),
        (100, "Lumenia Pronto para Criar!"),
    ]

    for pct, msg in modules:
        splash.set_progress(pct, msg)
        logger.info(f"[{pct}%] {msg}")
        time.sleep(0.08)

    # ── 3. Constrói a Janela Principal e faz o Fade-out do Splash ─────────
    window = MainWindow()

    # Transição fluida do Splash para a Janela Principal
    splash.finish(window)

    logger.info("✨ Lumenia 2.0 inicializado e pronto para interação do usuário.")
    sys.exit(app.exec())
