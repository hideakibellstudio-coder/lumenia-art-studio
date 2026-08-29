"""
PluginsWindow — Gerenciador Completo de Plugins & Inspector de Metadados (Lumenia V2)
=======================================================================================
Interface moderna de gerenciamento de plugins dividida em 2 colunas:
  - Esquerda: Filtros por categoria, barra de pesquisa, lista de cards e importar .zip.
  - Direita: Inspector de metadados completo com ações de Ativar/Desativar, Configurar e Excluir.
"""

from __future__ import annotations

import os
import sys
import logging
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.widgets.toggle.toggle_switch import ToggleSwitch
from ui.core.plugins.manager import PluginManager
from ui.core.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from .components.plugin_card import PluginCard
from .components.plugin_inspector import PluginDetailsInspector

logger = logging.getLogger(__name__)


# ── JANELA PRINCIPAL GERENCIADORA DE PLUGINS ─────────────────────────────

class PluginsWindow(BaseFramelessDialog):
    """Diálogo completo de gerenciamento e inspeção de plugins."""

    def __init__(self, parent=None):
        super().__init__(title="Gerenciador de Plugins", icon_name="plugin", parent=parent, modal=True)
        self.resize(1080, 680)
        self.setMinimumSize(960, 600)

        self._plugin_cards = {}
        self._selected_plugin = None

        self._build_ui()
        self.populate_list()

        ThemeManager.instance().themeChanged.connect(self.update_theme_style)
        self.update_theme_style()

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

        lbl_filters = QtWidgets.QLabel("FILTROS")
        lbl_filters.setStyleSheet("font-size: 10px; font-weight: bold;")

        filter_box.addWidget(lbl_filters)

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

        from ui.core.icons import get_icon

        btn_import = QtWidgets.QPushButton(" Importar .zip")
        btn_import.setIcon(get_icon("import", "#ffffff"))
        btn_import.setIconSize(QtCore.QSize(15, 15))
        btn_import.setCursor(QtCore.Qt.PointingHandCursor)
        btn_import.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        btn_import.clicked.connect(self.import_zip)
        filter_box.addWidget(btn_import)

        filter_widget = QtWidgets.QWidget()

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
                    self, "Erro de Inicialização",
                    f"Não foi possível ativar o plugin '{class_name}'. Verifique as dependências e os logs."
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
                self, "Plugin Removido", f"O plugin '{class_name}' foi desinstalado com sucesso."
            )
            self.populate_list()
        else:
            QtWidgets.QMessageBox.warning(
                self, "Erro de Exclusão", f"Não foi possível excluir o plugin '{class_name}'."
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
                pass

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
            self, "Importar Pacote de Plugin", "", "Pacotes Zip (*.zip)"
        )
        if file_path:
            pm = PluginManager.instance()
            res = pm.load_plugin_from_source(file_path)
            if res:
                QtWidgets.QMessageBox.information(
                    self, "Sucesso", "Plugin importado e instalado com sucesso!"
                )
                self.populate_list()
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Erro de Instalação", "Falha ao extrair e validar o pacote .zip do plugin."
                )

    def update_theme_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_main = theme.get_color("bg_main", "#0f172a")
        bg_panel = theme.get_color("bg_panel", "#1e293b")
        border = theme.get_color("border", "#334155")
        text_main = theme.get_color("text_main", "#f8fafc")
        text_sec = theme.get_color("text_sec", "#94a3b8")
        accent = theme.get_color("accent", "#3b82f6")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_main};
                color: {text_main};
            }}
            QLineEdit {{
                background-color: {bg_panel};
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
                background-color: rgba(99, 102, 241, 0.1);
            }}
            QPushButton:checked {{
                background-color: {accent};
                border-color: {accent};
                color: #ffffff;
                font-weight: bold;
            }}
        """)
        self.lbl_heading.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {text_main};")
