"""FloatingToolWindow — Base compartilhada para janelas-ferramenta flutuantes sobre o canvas."""

from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets


class FloatingToolWindow(QtWidgets.QDialog):
    """Janela de nível superior independente (``Qt.Tool``), sem chrome de SO.

    Usada por painéis que precisam flutuar visualmente por cima do canvas
    sem entrar na árvore de widgets da janela principal -- barra de
    ferramentas, barra de opções secundária, painéis avançados de pincel e
    de geometria, e o painel de configurações do pincel. Cada instância
    recebe um HWND próprio do Windows, independente do HWND da janela
    principal (efeito colateral conhecido e documentado: não aparecem em
    captura de tela "por janela específica" -- OBS Window Capture, Win+G.
    Isso NÃO é um bug do Lumenia: menus dropdown padrão do Qt têm a mesma
    limitação; é uma característica documentada do próprio Windows/OBS.
    Ver claude/panorama-ui-global-subjanelas-captura-tela.md no projeto).

    Antes desta base existir, cada arquivo repetia manualmente as mesmas
    2-3 linhas de flags/atributos, com pequenas variações não documentadas
    entre si. Os três parâmetros abaixo cobrem exatamente as variações que
    existiam entre os cinco usos reais no código (nenhum comportamento
    visual muda ao migrar um arquivo para esta base -- é consolidação de
    duplicação, não uma mudança de design):

    - ``no_drop_shadow``: soma ``Qt.NoDropShadowWindowHint`` aos flags.
      Usado pelos painéis "Configurações Avançadas" (pincel e geometria).
    - ``translucent``: aplica ``WA_TranslucentBackground``. É o padrão
      (True) para a maioria; ``BrushSettingsDialog`` é a exceção que
      desliga isso, porque desenha um fundo opaco próprio via QSS.
    - ``transparent_stylesheet``: aplica
      ``QDialog { background: transparent; border: none; }``. Usado pela
      barra flutuante de ferramentas e pela barra de opções secundária,
      que desenham sua própria cápsula num container interno.
    """

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        no_drop_shadow: bool = False,
        translucent: bool = True,
        transparent_stylesheet: bool = False,
    ) -> None:
        flags = QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
        if no_drop_shadow:
            flags |= QtCore.Qt.NoDropShadowWindowHint
        super().__init__(parent, flags)

        if translucent:
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        if transparent_stylesheet:
            self.setStyleSheet("QDialog { background: transparent; border: none; }")
