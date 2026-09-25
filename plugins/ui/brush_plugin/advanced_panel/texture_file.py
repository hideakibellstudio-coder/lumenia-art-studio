"""Leitura de uma imagem do disco como textura de pincel (RGBA8888).

Movido de plugins/system/workspace_core/workspace/brush_texture_io.py em
2026-09-24: carregar textura de pincel é assunto do plugin de pincel, não do
workspace.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PySide6 import QtGui, QtWidgets

from ui.infrastructure.i18n import tr

TextureFile = Tuple[bytes, int, int, str]


def read_texture_file(parent: Optional[QtWidgets.QWidget] = None) -> Optional[TextureFile]:
    """Pergunta o arquivo ao usuário e devolve (pixels RGBA, largura, altura, caminho), ou None."""
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        parent,
        tr("brush.select_texture_title", "Selecionar Imagem de Textura"),
        "",
        f"{tr('file_dialogs.images', 'Imagens')} (*.png *.jpg *.jpeg *.bmp *.tga)",
    )
    if not file_path:
        return None

    image = QtGui.QImage(file_path)
    if image.isNull():
        QtWidgets.QMessageBox.warning(
            parent,
            tr("common.error", "Erro"),
            tr("brush.texture_load_failed", "Não foi possível carregar a imagem selecionada."),
        )
        return None

    image = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
    return image.constBits().tobytes(), image.width(), image.height(), file_path
