"""
PluginsWindow — Gerenciador Completo de Plugins & Inspector de Metadados (Lumenia V2)
=======================================================================================
Interface moderna de gerenciamento de plugins dividida em 2 colunas:
  - Esquerda: Filtros por categoria, barra de pesquisa, lista de cards e importar .zip.
  - Direita: Inspector de metadados completo com ações de Ativar/Desativar, Configurar e Excluir.
"""

from __future__ import annotations

import logging
from PySide6 import QtCore, QtWidgets

from ui.core.plugins.manager import PluginManager
from ui.infrastructure.i18n import tr
from ui.infrastructure.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from .components.plugin_card import PluginCard
from .components.plugin_inspector import PluginDetailsInspector

logger = logging.getLogger(__name__)


# ── JANELA PRINCIPAL GERENCIADORA DE PLUGINS ─────────────────────────────

class PluginsWindow(BaseFramelessDialog):
    """Diálogo completo de gerenciamento e inspeção de plugins."""

    def __init__(self, parent=None):
        from ui.infrastructure.i18n import tr, I18nManager
        super().__init__(title=tr("plugins.dialog_title", "Gerenciador de Plugins"), icon_name="plugin", parent=parent, modal=True)
        self.resize(1080, 680)
        self.setMinimumSize(960, 600)

        self._plugin_cards = {}
        self._selected_plugin = None

        self._build_ui()
        self.populate_list()

        ThemeManager.instance().themeChanged.connect(self.update_theme_style)
        self.update_theme_style()

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        cols_widget = QtWidgets.QWidget()
        cols_layout = QtWidgets.QHBoxLayout(cols_widget)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(12)
        self.content_layout.addWidget(cols_widget, 1)

        # ── 1. Sidebar de Filtros (Esquerda) ──
        filter_box = QtWidgets.QVBoxLayout()
        filter_box.setSpacing(6)
        filter_box.setAlignment(QtCore.Qt.AlignTop)

        self.lbl_filters = QtWidgets.QLabel("FILTROS")
        self.lbl_filters.setStyleSheet("font-size: 10px; font-weight: bold;")

        filter_box.addWidget(self.lbl_filters)

        self.btn_grp = QtWidgets.QButtonGroup(self)
        self.btn_grp.setExclusive(True)

        filters = [
            ("all", "Todos os Plugins"),
            ("active", "Ativos"),
            ("inactive", "Inativos"),
            ("system", "Sistema"),
        ]
        for fid, fname in filters:
            btn = QtWidgets.QPushButton(fname)
            btn.setCheckable(True)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setProperty("filter_id", fid)
            if fid == "all":
                btn.setChecked(True)
            btn.clicked.connect(self._apply_filters)
            self.btn_grp.addButton(btn)
            filter_box.addWidget(btn)

        filter_box.addStretch()

        from ui.infrastructure.icons import get_icon

        self.btn_import = QtWidgets.QPushButton(" Importar .zip")
        self.btn_import.setObjectName("pluginImportBtn")
        self.btn_import.setIcon(get_icon("import", ThemeManager.instance().get_color("FG_PRIMARY", "#ffffff")))
        self.btn_import.setIconSize(QtCore.QSize(15, 15))
        self.btn_import.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_import.clicked.connect(self.import_zip)
        filter_box.addWidget(self.btn_import)

        filter_widget = QtWidgets.QWidget()
        filter_widget.setObjectName("PluginFilterWidget")
        filter_widget.setFixedWidth(160)
        filter_widget.setLayout(filter_box)
        cols_layout.addWidget(filter_widget)

        # ── 2. Lista de Plugins (Centro) ──
        list_container = QtWidgets.QWidget()
        list_layout = QtWidgets.QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(10)

        # Header com Busca
        search_box = QtWidgets.QHBoxLayout()
        self.lbl_heading = QtWidgets.QLabel("Meus Plugins")
        self.lbl_heading.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.txt_search = QtWidgets.QLineEdit()
        self.txt_search.setPlaceholderText("Pesquisar plugins...")
        self.txt_search.textChanged.connect(self._apply_filters)

        search_box.addWidget(self.lbl_heading)
        search_box.addStretch()
        search_box.addWidget(self.txt_search)

        list_layout.addLayout(search_box)

        # Scroll Area para Cards
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.cards_widget = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setAlignment(QtCore.Qt.AlignTop)

        self.scroll.setWidget(self.cards_widget)
        list_layout.addWidget(self.scroll, 1)

        cols_layout.addWidget(list_container, 1)

        # ── 3. Inspector de Detalhes (Direita - Largura Fixa) ──
        self.inspector = PluginDetailsInspector(self)
        self.inspector.setFixedWidth(350)

        self.inspector.action_toggled.connect(self._on_plugin_toggled)
        self.inspector.action_delete.connect(self._on_plugin_deleted)
        self.inspector.action_configure.connect(self._open_plugin_settings)

        cols_layout.addWidget(self.inspector)

    def retranslate_ui(self) -> None:
        from ui.infrastructure.i18n import tr
        self.setWindowTitle(tr("plugins.dialog_title", "Gerenciador de Plugins"))
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(tr("plugins.dialog_title", "Gerenciador de Plugins"))
        if hasattr(self, "lbl_filters"):
            self.lbl_filters.setText(tr("plugins.filters", "FILTROS"))
        if hasattr(self, "btn_grp"):
            mapping = {
                "all": tr("plugins.filter_all", "Todos os Plugins"),
                "active": tr("plugins.filter_active", "Ativos"),
                "inactive": tr("plugins.filter_inactive", "Inativos"),
                "system": tr("plugins.filter_system", "Sistema")
            }
            for btn in self.btn_grp.buttons():
                fid = btn.property("filter_id")
                if fid in mapping:
                    btn.setText(mapping[fid])
        if hasattr(self, "btn_import"):
            self.btn_import.setText(f" {tr('plugins.import_zip', 'Importar .zip')}")
        if hasattr(self, "lbl_heading"):
            self.lbl_heading.setText(tr("plugins.heading", "Meus Plugins"))
        if hasattr(self, "txt_search"):
            self.txt_search.setPlaceholderText(tr("plugins.search_placeholder", "Pesquisar plugins..."))
        if hasattr(self, "inspector") and hasattr(self.inspector, "retranslate_ui"):
            self.inspector.retranslate_ui()

    def populate_list(self) -> None:
        # Limpa layout anterior
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._plugin_cards.clear()
        pm = PluginManager.instance()
        plugins = pm.get_all_discovered_plugins()

        for plugin in plugins:
            c_name = plugin.__class__.__name__
            is_active = c_name in pm.active_instances

            is_selected = (self._selected_plugin and self._selected_plugin.__class__.__name__ == c_name)
            card = PluginCard(plugin, is_active=is_active, is_selected=is_selected, parent=self.cards_widget)

            card.toggled.connect(lambda checked, name=c_name: self._on_plugin_toggled(name, checked))
            card.selected.connect(self._on_plugin_selected)

            self.cards_layout.addWidget(card)
            self._plugin_cards[c_name] = card

        # Se houver plugins e nenhum selecionado, seleciona o primeiro
        if plugins and not self._selected_plugin:
            self._on_plugin_selected(plugins[0])
        elif self._selected_plugin:
            c_name = self._selected_plugin.__class__.__name__
            is_act = c_name in pm.active_instances
            self.inspector.set_plugin(self._selected_plugin, is_act)

        self._apply_filters()

    def _on_plugin_selected(self, plugin) -> None:
        self._selected_plugin = plugin
        c_selected = plugin.__class__.__name__ if plugin else None

        for c_name, card in self._plugin_cards.items():
            card.set_selected(c_name == c_selected)

        pm = PluginManager.instance()
        is_active = c_selected in pm.active_instances if c_selected else False
        self.inspector.set_plugin(plugin, is_active)

    def _on_plugin_toggled(self, class_name: str, enabled: bool) -> None:
        pm = PluginManager.instance()
        if enabled:
            success = pm.enable_plugin(class_name)
            if not success:
                QtWidgets.QMessageBox.warning(
                    self, tr("messages.plugin_enable_error_title", "Erro de Inicialização"),
                    tr("messages.plugin_enable_error",
                       "Não foi possível ativar o plugin '{name}'. Verifique as dependências e os logs.",
                       name=class_name)
                )
        else:
            pm.disable_plugin(class_name)

        self.populate_list()

    def _on_plugin_deleted(self, class_name: str) -> None:
        pm = PluginManager.instance()
        success = pm.uninstall_plugin(class_name)
        if success:
            self._selected_plugin = None
            QtWidgets.QMessageBox.information(
                self, tr("messages.plugin_removed_title", "Plugin Removido"),
                tr("messages.plugin_removed", "O plugin '{name}' foi desinstalado com sucesso.", name=class_name)
            )
            self.populate_list()
        else:
            QtWidgets.QMessageBox.warning(
                self, tr("messages.plugin_remove_error_title", "Erro de Exclusão"),
                tr("messages.plugin_remove_error", "Não foi possível excluir o plugin '{name}'.", name=class_name)
            )

    def _open_plugin_settings(self, plugin) -> None:
        if hasattr(plugin, "open_settings_ui"):
            plugin.open_settings_ui(self)

    def _apply_filters(self) -> None:
        filter_btn = self.btn_grp.checkedButton()
        filter_id = filter_btn.property("filter_id") if filter_btn else "all"
        search_txt = self.txt_search.text().lower().strip()

        pm = PluginManager.instance()

        for c_name, card in self._plugin_cards.items():
            is_active = c_name in pm.active_instances
            is_sys = False
            try:
                is_sys = card.plugin.is_system_plugin()
            except Exception:
                logging.getLogger(__name__).debug("is_system_plugin() falhou.", exc_info=True)

            # Checa Filtro de Categoria
            cat_match = True
            if filter_id == "active" and not is_active:
                cat_match = False
            elif filter_id == "inactive" and is_active:
                cat_match = False
            elif filter_id == "system" and not is_sys:
                cat_match = False

            # Checa Busca de Texto
            text_match = True
            if search_txt:
                try:
                    meta = card.plugin.get_metadata()
                    searchable = f"{meta.name} {meta.author} {meta.description} {c_name}".lower()
                except Exception:
                    searchable = c_name.lower()
                text_match = search_txt in searchable

            card.setVisible(cat_match and text_match)

    def import_zip(self) -> None:

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, tr("file_dialogs.import_plugin", "Importar Pacote de Plugin"), "",
            f"{tr('file_dialogs.zip_packages', 'Pacotes Zip')} (*.zip)"
        )
        if file_path:
            pm = PluginManager.instance()
            res = pm.load_plugin_from_source(file_path)
            if res:
                QtWidgets.QMessageBox.information(
                    self, tr("messages.plugin_installed_title", "Sucesso"),
                    tr("messages.plugin_installed", "Plugin importado e instalado com sucesso!")
                )
                self.populate_list()
            else:
                QtWidgets.QMessageBox.critical(
                    self, tr("messages.plugin_install_error_title", "Erro de Instalação"),
                    tr("messages.plugin_install_error", "Falha ao extrair e validar o pacote .zip do plugin.")
                )

    def update_theme_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_main = theme.get_color("bg_main", "#0f172a")
        bg_panel = theme.get_color("bg_panel", "#1e293b")
        bg_card = theme.get_color("bg_card", "#1e293b")
        bg_input = theme.get_color("bg_input", "#0f172a")
        border = theme.get_color("border", "#334155")
        text_main = theme.get_color("text_main", "#f8fafc")
        text_sec = theme.get_color("text_sec", "#94a3b8")
        accent = theme.get_color("accent", "#3b82f6")
        accent_hover = theme.get_color("accent_hover", "#60a5fa")

        if hasattr(self, "root_container") and self.root_container:
            self.root_container.setStyleSheet(f"""
                QWidget#DialogRootContainer {{
                    background-color: {bg_main};
                    border: 1px solid {border};
                    border-radius: 10px;
                }}
                QFrame#DialogHeaderSep {{
                    background-color: {border};
                    border: none;
                }}
            """)

        self.setStyleSheet(f"""
            QWidget#PluginFilterWidget {{
                background-color: transparent;
                border-right: 1px solid {border};
            }}
            QLineEdit {{
                background-color: {bg_input};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                color: {text_main};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                color: {text_main};
                font-size: 12px;
                font-weight: 500;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {accent};
                background-color: {bg_card};
            }}
            QPushButton:checked {{
                background-color: {accent};
                border-color: {accent};
                color: {text_main};
                font-weight: bold;
            }}
            QPushButton#pluginImportBtn {{
                background-color: {accent};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                color: {text_main};
                font-weight: bold;
                font-size: 11px;
                text-align: center;
            }}
            QPushButton#pluginImportBtn:hover {{
                background-color: {accent_hover};
            }}
        """)
        if hasattr(self, "lbl_filters"):
            self.lbl_filters.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {text_sec};")
        if hasattr(self, "lbl_heading"):
            self.lbl_heading.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {text_main};")
