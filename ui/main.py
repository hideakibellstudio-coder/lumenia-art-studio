import sys
import os
import logging

# Adiciona o diretório pai para que 'ui' possa ser importado como um pacote
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Garante que o próprio diretório ui/ esteja no path para carregar a extensão engine_core
ui_dir = os.path.dirname(os.path.abspath(__file__))
if ui_dir not in sys.path:
    sys.path.insert(0, ui_dir)

from PySide6 import QtWidgets
from ui.core.logger import setup_senior_logging, get_logger
from ui.boundary.orchestrator.main_window import MainWindow

if __name__ == "__main__":
    # Inicializa a infraestrutura de logging sênior no boot da aplicação
    log_level = logging.DEBUG if "--debug" in sys.argv else logging.INFO
    setup_senior_logging(log_level)

    logger = get_logger("MainApp")
    logger.info("🎨 Inicializando Lumenia Brush Engine 2.0...")

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    
    logger.info("✨ Lumenia 2.0 inicializado e pronto para interação do usuário.")
    sys.exit(app.exec())
