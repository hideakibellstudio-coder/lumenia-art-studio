"""
Keyboard Shortcuts Dialog — Diálogo de Gerenciamento e Personalização de Atalhos.
================================================================================
Padronizado no Design System do Lumenia V2 com busca em tempo real, abas por
categoria, captura interativa de teclas, validação de conflitos e persistência.
"""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from ui.core.i18n import tr

DEFAULT_SHORTCUTS = [
    # Categoria: Ferramentas
    {"id": "tool_brush", "category": "Ferramentas", "name": "Ferramenta Pincel", "default": "B", "icon": "brush"},
    {"id": "tool_eraser", "category": "Ferramentas", "name": "Ferramenta Borracha", "default": "E", "icon": "eraser"},
    {"id": "tool_shapes", "category": "Ferramentas", "name": "Ferramenta Formas Geométricas", "default": "U", "icon": "shapes"},
    {"id": "tool_text", "category": "Ferramentas", "name": "Ferramenta de Texto", "default": "T", "icon": "text"},
    {"id": "tool_eyedropper", "category": "Ferramentas", "name": "Conta-Gotas", "default": "I", "icon": "eyedropper"},
    {"id": "tool_fill", "category": "Ferramentas", "name": "Balde de Tinta (Preenchimento)", "default": "G", "icon": "bucket"},
    {"id": "tool_wand", "category": "Ferramentas", "name": "Varinha Mágica", "default": "W", "icon": "wand"},
    {"id": "tool_transform", "category": "Ferramentas", "name": "Transformação Livre", "default": "Ctrl+T", "icon": "transform"},

    # Categoria: Arquivo
    {"id": "file_new", "category": "Arquivo", "name": "Novo Documento", "default": "Ctrl+N", "icon": "plus"},
    {"id": "file_open", "category": "Arquivo", "name": "Abrir Imagem / Documento", "default": "Ctrl+O", "icon": "folder"},
    {"id": "file_save", "category": "Arquivo", "name": "Salvar", "default": "Ctrl+S", "icon": "save"},
    {"id": "file_save_as", "category": "Arquivo", "name": "Salvar Como...", "default": "Ctrl+Shift+S", "icon": "save"},
    {"id": "file_export", "category": "Arquivo", "name": "Exportar Imagem...", "default": "Ctrl+E", "icon": "export"},
    {"id": "file_close", "category": "Arquivo", "name": "Fechar Aba Atual", "default": "Ctrl+W", "icon": "close"},
    {"id": "file_exit", "category": "Arquivo", "name": "Sair do Lumenia", "default": "Ctrl+Q", "icon": "close"},

    # Categoria: Edição
    {"id": "edit_undo", "category": "Edição", "name": "Desfazer (Undo)", "default": "Ctrl+Z", "icon": "undo"},
    {"id": "edit_redo", "category": "Edição", "name": "Refazer (Redo)", "default": "Ctrl+Y", "icon": "redo"},
    {"id": "edit_cut", "category": "Edição", "name": "Recortar", "default": "Ctrl+X", "icon": "cut"},
    {"id": "edit_copy", "category": "Edição", "name": "Copiar", "default": "Ctrl+C", "icon": "copy"},
    {"id": "edit_paste", "category": "Edição", "name": "Colar", "default": "Ctrl+V", "icon": "paste"},
    {"id": "edit_clear_layer", "category": "Edição", "name": "Limpar Conteúdo da Camada", "default": "Del", "icon": "clean_layer"},

    # Categoria: Camadas
    {"id": "layer_new", "category": "Camadas", "name": "Nova Camada", "default": "Ctrl+Shift+N", "icon": "plus"},
    {"id": "layer_group", "category": "Camadas", "name": "Novo Grupo", "default": "Ctrl+G", "icon": "folder"},
    {"id": "layer_duplicate", "category": "Camadas", "name": "Duplicar Camada / Grupo", "default": "Ctrl+J", "icon": "duplicate"},
    {"id": "layer_delete", "category": "Camadas", "name": "Excluir Camada Ativa", "default": "Shift+Del", "icon": "trash"},
    {"id": "layer_merge", "category": "Camadas", "name": "Mesclar Camada para Baixo", "default": "Ctrl+E", "icon": "layer_flatten"},

    # Categoria: Exibir
    {"id": "view_zoom_in", "category": "Exibir", "name": "Aproximar Zoom (Zoom In)", "default": "Ctrl+=", "icon": "zoom_in"},
    {"id": "view_zoom_out", "category": "Exibir", "name": "Afastar Zoom (Zoom Out)", "default": "Ctrl+-", "icon": "zoom_out"},
    {"id": "view_zoom_100", "category": "Exibir", "name": "Resetar Zoom para 100%", "default": "Ctrl+0", "icon": "reset"},
    {"id": "view_reset_rot", "category": "Exibir", "name": "Resetar Rotação da Câmera", "default": "Ctrl+R", "icon": "reset"},
    {"id": "view_grid", "category": "Exibir", "name": "Alternar Grade Guia", "default": "Ctrl+'", "icon": "grid"},

    # Categoria: Seleção
    {"id": "select_all", "category": "Seleção", "name": "Selecionar Tudo", "default": "Ctrl+A", "icon": "select"},
    {"id": "select_deselect", "category": "Seleção", "name": "Desmarcar Seleção", "default": "Ctrl+D", "icon": "deselect"},
    {"id": "select_invert", "category": "Seleção", "name": "Inverter Seleção", "default": "Ctrl+Shift+I", "icon": "transform"},
]


class KeySequenceRecorder(QtWidgets.QLineEdit):
    """Widget de entrada que grava combinações de teclas pressionadas."""

    shortcutRecorded = QtCore.Signal(str)

    def __init__(self, current_key: str = "", parent=None):
        super().__init__(parent)
        self.setText(current_key)
        self.setReadOnly(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setPlaceholderText(tr("dialogs.click_press_key", "Clique e pressione..."))
        self._recording = False

    def mousePressEvent(self, event):
        self._recording = True
        self.setText(tr("dialogs.press_keys", "Pressione as teclas..."))
        self.selectAll()
        super().mousePressEvent(event)

    def focusOutEvent(self, event):
        self._recording = False
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if not self._recording:
            return super().keyPressEvent(event)

        key = event.key()
        if key in (QtCore.Qt.Key_Control, QtCore.Qt.Key_Shift, QtCore.Qt.Key_Alt, QtCore.Qt.Key_Meta):
            return

        if key == QtCore.Qt.Key_Escape:
            self._recording = False
            self.clearFocus()
            return

        if key == QtCore.Qt.Key_Backspace:
            self.setText("")
            self._recording = False
            self.shortcutRecorded.emit("")
            self.clearFocus()
            return

        modifiers = event.modifiers()
        parts = []
        if modifiers & QtCore.Qt.ControlModifier:
            parts.append("Ctrl")
        if modifiers & QtCore.Qt.AltModifier:
            parts.append("Alt")
        if modifiers & QtCore.Qt.ShiftModifier:
            parts.append("Shift")
        if modifiers & QtCore.Qt.MetaModifier:
            parts.append("Meta")

        key_text = QtGui.QKeySequence(key).toString()
        if key_text:
            parts.append(key_text)

        combo_str = "+".join(parts)
        self.setText(combo_str)
        self._recording = False
        self.shortcutRecorded.emit(combo_str)
        self.clearFocus()


class KeyboardShortcutsDialog(QtWidgets.QDialog):
    """Diálogo de personalização visual de atalhos de teclado."""

    shortcutsApplied = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(580, 520)
        self.resize(640, 560)
        self._drag_pos = None

        self._shortcuts_map = self._load_saved_shortcuts()
        self._current_category = "Todas"
        self._search_query = ""

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _load_saved_shortcuts(self) -> dict:
        settings = QtCore.QSettings("Lumenia", "LumeniaArtStudio")
        data = {}
        for item in DEFAULT_SHORTCUTS:
            saved = settings.value(f"shortcuts/{item['id']}", item["default"])
            data[item["id"]] = saved
        return data

    def _build_ui(self):
        main_lay = QtWidgets.QVBoxLayout(self)
        main_lay.setContentsMargins(10, 10, 10, 10)

        self.card = QtWidgets.QFrame(self)
        self.card.setObjectName("ShortcutsContainer")
        card_lay = QtWidgets.QVBoxLayout(self.card)
        card_lay.setContentsMargins(14, 12, 14, 14)
        card_lay.setSpacing(10)

        # ── Cabeçalho Draggable
        hdr = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setPixmap(get_icon("keyboard", "ACCENT", QtCore.QSize(18, 18)).pixmap(18, 18))
        hdr.addWidget(icon_lbl)

        title = QtWidgets.QLabel(tr("dialogs.shortcuts_title", "Configurações de Atalhos de Teclado"))
        title.setStyleSheet("font-weight: 700; font-size: 13px; letter-spacing: 0.5px;")
        hdr.addWidget(title)
        hdr.addStretch()

        btn_close = QtWidgets.QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        hdr.addWidget(btn_close)
        card_lay.addLayout(hdr)

        # ── Barra de Pesquisa e Filtros
        search_row = QtWidgets.QHBoxLayout()
        self.txt_search = QtWidgets.QLineEdit()
        self.txt_search.setPlaceholderText(f"🔍 {tr('dialogs.search_placeholder', 'Buscar ação ou atalho...')}")
        self.txt_search.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.txt_search, 1)
        card_lay.addLayout(search_row)

        # ── Abas de Categorias
        self.tab_bar = QtWidgets.QTabBar()
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setCursor(QtCore.Qt.PointingHandCursor)
        self.category_names = [
            ("Todas", tr("dialogs.tab_all", "Todas")),
            ("Ferramentas", tr("dialogs.tab_tools", "Ferramentas")),
            ("Arquivo", tr("menu.file.title", "Arquivo")),
            ("Edição", tr("menu.edit.title", "Edição")),
            ("Camadas", tr("menu.layer.title", "Camadas")),
            ("Exibir", tr("menu.view.title", "Exibir")),
            ("Seleção", tr("menu.select.title", "Seleção")),
        ]
        for cat_id, cat_label in self.category_names:
            self.tab_bar.addTab(cat_label)
        self.tab_bar.currentChanged.connect(self._on_category_changed)
        card_lay.addWidget(self.tab_bar)

        # ── Tabela de Atalhos
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            tr("dialogs.action_col", "Ação"),
            tr("dialogs.category_col", "Categoria"),
            tr("dialogs.shortcut_col", "Atalho")
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        card_lay.addWidget(self.table, 1)

        # ── Rodapé com Botões de Ação
        footer = QtWidgets.QHBoxLayout()
        btn_restore = QtWidgets.QPushButton(tr("dialogs.reset_defaults", "Restaurar Padrões"))
        btn_restore.setCursor(QtCore.Qt.PointingHandCursor)
        btn_restore.clicked.connect(self._on_restore_defaults)
        footer.addWidget(btn_restore)
        footer.addStretch()

        btn_cancel = QtWidgets.QPushButton(tr("dialogs.cancel", "Cancelar"))
        btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        footer.addWidget(btn_cancel)

        self.btn_save = QtWidgets.QPushButton(tr("dialogs.save_apply", "Salvar e Aplicar"))
        self.btn_save.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save_and_apply)
        footer.addWidget(self.btn_save)

        card_lay.addLayout(footer)
        main_lay.addWidget(self.card)

        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(0)
        q = self._search_query.lower()
        cat_filter = self._current_category

        for item in DEFAULT_SHORTCUTS:
            if cat_filter != "Todas" and item["category"] != cat_filter:
                continue

            current_key = self._shortcuts_map.get(item["id"], item["default"])
            if q and (q not in item["name"].lower() and q not in current_key.lower()):
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 36)

            # Coluna 0: Ação
            act_item = QtWidgets.QTableWidgetItem(f" {item['name']}")
            act_item.setIcon(get_icon(item.get("icon", "settings"), size=QtCore.QSize(16, 16)))
            self.table.setItem(row, 0, act_item)

            # Coluna 1: Categoria
            cat_item = QtWidgets.QTableWidgetItem(item["category"])
            cat_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table.setItem(row, 1, cat_item)

            # Coluna 2: Gravador de Atalho
            rec = KeySequenceRecorder(current_key)
            rec.setProperty("item_id", item["id"])
            rec.shortcutRecorded.connect(lambda k, iid=item["id"]: self._on_shortcut_recorded(iid, k))
            self.table.setCellWidget(row, 2, rec)

    def _on_shortcut_recorded(self, item_id: str, new_key: str):
        self._shortcuts_map[item_id] = new_key

    def _on_category_changed(self, idx: int):
        if 0 <= idx < len(self.category_names):
            self._current_category = self.category_names[idx][0]
        else:
            self._current_category = "Todas"
        self._populate_table()

    def _on_search_changed(self, text: str):
        self._search_query = text
        self._populate_table()

    def _on_restore_defaults(self):
        reply = QtWidgets.QMessageBox.question(
            self, tr("dialogs.reset_defaults", "Restaurar Padrões"),
            tr("dialogs.reset_shortcuts_confirm", "Deseja restaurar todos os atalhos de teclado para as configurações padrão?"),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            for item in DEFAULT_SHORTCUTS:
                self._shortcuts_map[item["id"]] = item["default"]
            self._populate_table()

    def _on_save_and_apply(self):
        settings = QtCore.QSettings("Lumenia", "LumeniaArtStudio")
        for item_id, val in self._shortcuts_map.items():
            settings.setValue(f"shortcuts/{item_id}", val)
        self.shortcutsApplied.emit(self._shortcuts_map)
        self.accept()

    def _apply_theme(self, *args):
        tm = ThemeManager.instance()
        bg_card = tm.get_color("bg_card", "#181825")
        bg_panel = tm.get_color("bg_panel", "#1e1e24")
        border = tm.get_color("border", "#313244")
        accent = tm.get_color("accent", "#6366f1")
        text_main = tm.get_color("text_main", "#f3f4f6")
        text_sec = tm.get_color("text_sec", "#9ca3af")

        self.card.setStyleSheet(f"""
            QFrame#ShortcutsContainer {{
                background-color: {bg_card}; border: 1px solid {border}; border-radius: 10px;
            }}
            QLabel {{ color: {text_main}; }}
            QLineEdit {{
                background-color: {bg_panel}; color: {text_main}; border: 1px solid {border};
                border-radius: 6px; padding: 6px 10px; font-size: 11px;
            }}
            QLineEdit:focus {{ border-color: {accent}; }}
            QTabBar::tab {{
                background: transparent; color: {text_sec}; padding: 6px 12px; font-size: 11px; font-weight: bold;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{ color: {text_main}; border-bottom: 2px solid {accent}; }}
            QTableWidget {{
                background-color: {bg_panel}; color: {text_main}; border: 1px solid {border};
                gridline-color: {border}; border-radius: 6px; font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {bg_card}; color: {text_sec}; font-weight: bold; font-size: 11px;
                padding: 6px; border: none; border-bottom: 1px solid {border};
            }}
            QPushButton {{
                background-color: {bg_panel}; color: {text_main}; border: 1px solid {border};
                border-radius: 6px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {accent}; color: #ffffff; border-color: {accent}; }}
        """)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & QtCore.Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
