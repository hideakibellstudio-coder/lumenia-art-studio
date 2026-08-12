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

logger = logging.getLogger(__name__)


# ── 1. CARTÃO INDIVIDUAL DO PLUGIN (Lista da Esquerda) ───────────────────────

class PluginCard(QtWidgets.QFrame):
    """Cartão individual representando um plugin na lista."""

    toggled = QtCore.Signal(bool)
    selected = QtCore.Signal(object)  # plugin instance

    def __init__(self, plugin, is_active: bool, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.is_selected = is_selected
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._build_ui(is_active)
        ThemeManager.instance().themeChanged.connect(self.update_theme_style)
        self.update_theme_style()

    def _build_ui(self, is_active: bool) -> None:
        self.setFixedHeight(84)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # 1. Ícone
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setFixedSize(40, 40)
        icon = self.plugin.get_icon() if hasattr(self.plugin, "get_icon") else None
        if icon and not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(40, 40))
        else:
            self.icon_label.setPixmap(
                QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileIcon).pixmap(40, 40)
            )
        layout.addWidget(self.icon_label)

        # 2. Informações do Plugin
        info_layout = QtWidgets.QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(QtCore.Qt.AlignVCenter)

        is_system = False
        try:
            is_system = self.plugin.is_system_plugin()
        except Exception:
            pass

        try:
            metadata = self.plugin.get_metadata()
            p_name = metadata.name
            p_version = metadata.version
            p_author = metadata.author
            p_desc = metadata.description
        except Exception:
            p_name = self.plugin.__class__.__name__
            p_version = "0.0.0"
            p_author = "Desconhecido"
            p_desc = "Sem descrição."

        name_text = p_name
        if is_system:
            name_text += " [Sistema]"

        self.name_label = QtWidgets.QLabel(name_text)
        self.name_label.setStyleSheet("font-size: 13px; font-weight: bold;")

        self.meta_label = QtWidgets.QLabel(f"v{p_version} por {p_author}")
        self.meta_label.setStyleSheet("font-size: 11px;")

        short_desc = p_desc.split('\n')[0]
        if len(short_desc) > 60:
            short_desc = short_desc[:60] + "..."
        self.desc_label = QtWidgets.QLabel(short_desc)
        self.desc_label.setStyleSheet("font-size: 11px;")

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.meta_label)
        info_layout.addWidget(self.desc_label)

        layout.addLayout(info_layout, 1)

        # 3. Toggle Switch
        self.switch = ToggleSwitch(parent=self)
        self.switch.setChecked(is_active)
        if is_system:
            self.switch.setEnabled(False)
            self.switch.setToolTip("Plugins de sistema não podem ser desativados.")
        else:
            self.switch.toggled.connect(self.toggled.emit)

        layout.addWidget(self.switch)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.plugin)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self.update_theme_style()

    def update_theme_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border = theme.get_color("border", "#2e2e38")
        text_main = theme.get_color("text_main", "#f3f4f6")
        text_sec = theme.get_color("text_sec", "#9ca3af")
        accent = theme.get_color("accent", "#6366f1")

        bg_color = theme.get_color("bg_hover", "#2a2a32") if self.is_selected else bg_panel
        border_color = accent if self.is_selected else border

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {accent};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        self.name_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {text_main};")
        self.meta_label.setStyleSheet(f"font-size: 11px; color: {text_sec};")
        self.desc_label.setStyleSheet(f"font-size: 11px; color: {text_sec};")


# ── 2. PAINEL DE INSPECTOR DE METADADOS DO PLUGIN (Coluna Direita) ───────────

class PluginDetailsInspector(QtWidgets.QFrame):
    """Painel de exibição detalhada de metadados e ações do plugin selecionado."""

    action_toggled = QtCore.Signal(str, bool)     # class_name, enabled
    action_delete = QtCore.Signal(str)          # class_name
    action_configure = QtCore.Signal(object)      # plugin instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_plugin = None

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self.update_theme_style)
        self.update_theme_style()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Estado Vazio
        self.empty_label = QtWidgets.QLabel("Selecione um plugin na lista ao lado para visualizar os detalhes.")
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_label.setWordWrap(True)

        # Scroll Area para o Inspector de Detalhes (Garante isolamento sem sobrepor a lista de cards)
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        # Conteúdo do Inspector
        self.details_widget = QtWidgets.QWidget()
        det_layout = QtWidgets.QVBoxLayout(self.details_widget)
        det_layout.setContentsMargins(0, 0, 0, 0)
        det_layout.setSpacing(12)

        # Cabeçalho (Ícone + Título + Badges)
        head_box = QtWidgets.QHBoxLayout()
        head_box.setSpacing(12)

        self.det_icon = QtWidgets.QLabel()
        self.det_icon.setFixedSize(48, 48)
        head_box.addWidget(self.det_icon)

        head_title_layout = QtWidgets.QVBoxLayout()
        head_title_layout.setSpacing(3)

        self.det_title = QtWidgets.QLabel()
        self.det_title.setWordWrap(True)
        self.det_title.setStyleSheet("font-size: 15px; font-weight: bold;")

        self.det_meta = QtWidgets.QLabel()
        self.det_meta.setStyleSheet("font-size: 11px;")

        head_title_layout.addWidget(self.det_title)
        head_title_layout.addWidget(self.det_meta)
        head_box.addLayout(head_title_layout, 1)

        det_layout.addLayout(head_box)

        # Badges
        self.badges_layout = QtWidgets.QHBoxLayout()
        self.badges_layout.setSpacing(6)
        self.badges_layout.setAlignment(QtCore.Qt.AlignLeft)
        det_layout.addLayout(self.badges_layout)

        # Linha Divisória
        self.sep = QtWidgets.QFrame()
        self.sep.setFrameShape(QtWidgets.QFrame.HLine)
        det_layout.addWidget(self.sep)

        # Formulário de Propriedades
        props_form = QtWidgets.QFormLayout()
        props_form.setSpacing(8)
        props_form.setLabelAlignment(QtCore.Qt.AlignLeft)
        props_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.lbl_id = QtWidgets.QLabel()
        self.lbl_id.setWordWrap(True)
        self.lbl_id.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.lbl_id.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")

        self.lbl_path = QtWidgets.QLabel()
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.lbl_path.setStyleSheet("font-family: Consolas, monospace; font-size: 10px;")

        self.lbl_type = QtWidgets.QLabel()
        self.lbl_priority = QtWidgets.QLabel()
        self.lbl_deps = QtWidgets.QLabel()
        self.lbl_deps.setWordWrap(True)

        props_form.addRow("ID Único:", self.lbl_id)
        props_form.addRow("Caminho:", self.lbl_path)
        props_form.addRow("Tipo:", self.lbl_type)
        props_form.addRow("Prioridade:", self.lbl_priority)
        props_form.addRow("Dependências:", self.lbl_deps)

        det_layout.addLayout(props_form)

        # Descrição Completa
        det_layout.addWidget(QtWidgets.QLabel("Descrição Completa:"))
        self.txt_desc = QtWidgets.QTextEdit()
        self.txt_desc.setReadOnly(True)
        self.txt_desc.setFixedHeight(85)
        det_layout.addWidget(self.txt_desc)

        det_layout.addStretch()

        # Barra de Ações (Rodapé do Inspector)
        actions_box = QtWidgets.QHBoxLayout()
        actions_box.setSpacing(8)

        from ui.core.icons import get_icon

        self.btn_toggle = QtWidgets.QPushButton()
        self.btn_toggle.setIconSize(QtCore.QSize(14, 14))
        self.btn_toggle.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)

        self.btn_config = QtWidgets.QPushButton(" Configurar")
        self.btn_config.setIcon(get_icon("settings", "#ffffff"))
        self.btn_config.setIconSize(QtCore.QSize(14, 14))
        self.btn_config.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_config.clicked.connect(lambda: self.current_plugin and self.action_configure.emit(self.current_plugin))

        self.btn_delete = QtWidgets.QPushButton(" Excluir")
        self.btn_delete.setIcon(get_icon("trash", "#ffffff"))
        self.btn_delete.setIconSize(QtCore.QSize(14, 14))
        self.btn_delete.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        actions_box.addWidget(self.btn_toggle)
        actions_box.addWidget(self.btn_config)
        actions_box.addWidget(self.btn_delete)

        det_layout.addLayout(actions_box)


        self.scroll_area.setWidget(self.details_widget)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.scroll_area)
        self.scroll_area.hide()


    def set_plugin(self, plugin, is_active: bool) -> None:
        self.current_plugin = plugin
        if not plugin:
            self.empty_label.show()
            self.scroll_area.hide()
            return

        self.empty_label.hide()
        self.scroll_area.show()


        class_name = plugin.__class__.__name__

        is_system = False
        try:
            is_system = plugin.is_system_plugin()
        except Exception:
            pass

        try:
            meta = plugin.get_metadata()
            p_id = str(meta.id)
            p_name = str(meta.name)
            p_version = str(meta.version)
            p_author = str(meta.author)
            p_desc = str(meta.description)
            if hasattr(meta, "plugin_type"):
                pt = meta.plugin_type
                if hasattr(pt, "name"):
                    p_type = str(pt.name)
                elif hasattr(pt, "value"):
                    p_type = str(pt.value)
                else:
                    p_type = str(pt)
            else:
                p_type = "UI"
            p_deps = ", ".join(meta.dependencies) if meta.dependencies else "Nenhuma"
        except Exception:
            p_id = class_name
            p_name = class_name
            p_version = "0.0.0"
            p_author = "Desconhecido"
            p_desc = "Sem descrição disponível."
            p_type = "UI"
            p_deps = "Nenhuma"

        priority = plugin.get_priority() if hasattr(plugin, "get_priority") else 50
        mod = sys.modules.get(plugin.__module__)
        file_path = getattr(mod, "__file__", "Desconhecido") if mod else "Desconhecido"

        # Preenche UI
        icon = plugin.get_icon() if hasattr(plugin, "get_icon") else None
        if icon and not icon.isNull():
            self.det_icon.setPixmap(icon.pixmap(48, 48))
        else:
            self.det_icon.setPixmap(
                QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileIcon).pixmap(48, 48)
            )

        self.det_title.setText(p_name)
        self.det_meta.setText(f"Versão {p_version} • Criado por {p_author}")
        self.lbl_id.setText(p_id)
        formatted_path = file_path.replace("\\", "/").replace("/", "/\u200b")
        self.lbl_path.setText(formatted_path)

        self.lbl_type.setText(str(p_type).upper())
        self.lbl_priority.setText(str(priority))
        self.lbl_deps.setText(p_deps)
        self.txt_desc.setText(p_desc)


        # Botão Toggle
        from ui.core.icons import get_icon
        if is_system:
            self.btn_toggle.setText(" Sistema")
            self.btn_toggle.setIcon(get_icon("lock", "#9ca3af"))
            self.btn_toggle.setEnabled(False)
            self.btn_toggle.setProperty("btn_type", "system")
        elif is_active:
            self.btn_toggle.setText(" Desativar")
            self.btn_toggle.setIcon(get_icon("power", "#ffffff"))
            self.btn_toggle.setEnabled(True)
            self.btn_toggle.setProperty("btn_type", "deactivate")
        else:
            self.btn_toggle.setText(" Ativar")
            self.btn_toggle.setIcon(get_icon("power", "#ffffff"))
            self.btn_toggle.setEnabled(True)
            self.btn_toggle.setProperty("btn_type", "activate")

        self.btn_toggle.style().unpolish(self.btn_toggle)
        self.btn_toggle.style().polish(self.btn_toggle)

        # Configuração
        self.btn_config.setVisible(hasattr(plugin, "has_settings_ui") and plugin.has_settings_ui())

        # Exclusão
        if is_system:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setToolTip("Plugins de sistema não podem ser excluídos.")
        else:
            self.btn_delete.setEnabled(True)
            self.btn_delete.setToolTip("Excluir plugin do disco permanentemente.")

    def _on_toggle_clicked(self) -> None:
        if not self.current_plugin:
            return
        c_name = self.current_plugin.__class__.__name__
        pm = PluginManager.instance()
        is_active = c_name in pm.active_instances
        self.action_toggled.emit(c_name, not is_active)

    def _on_delete_clicked(self) -> None:
        if not self.current_plugin:
            return
        c_name = self.current_plugin.__class__.__name__
        try:
            p_name = self.current_plugin.get_metadata().name
        except Exception:
            p_name = c_name

        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirmar Exclusão de Plugin",
            f"Deseja realmente excluir e remover do disco o plugin '{p_name}'?\n\nEsta ação não poderá ser desfeita.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.action_delete.emit(c_name)

    def update_theme_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border = theme.get_color("border", "#2e2e38")
        text_main = theme.get_color("text_main", "#f3f4f6")
        text_sec = theme.get_color("text_sec", "#9ca3af")
        accent = theme.get_color("accent", "#6366f1")

        self.setStyleSheet(f"""
            PluginDetailsInspector {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLabel {{ color: {text_main}; }}
            QTextEdit {{
                background-color: rgba(0, 0, 0, 0.15);
                border: 1px solid {border};
                border-radius: 4px;
                color: {text_main};
                font-size: 11px;
            }}
        """)
        self.empty_label.setStyleSheet(f"color: {text_sec}; font-size: 13px;")
        self.sep.setStyleSheet(f"background-color: {border}; max-height: 1px;")

        self.btn_toggle.setStyleSheet(f"""
            QPushButton[btn_type="activate"] {{
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton[btn_type="activate"]:hover {{
                background-color: #059669;
            }}
            QPushButton[btn_type="activate"]:pressed {{
                background-color: #047857;
            }}
            QPushButton[btn_type="deactivate"] {{
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton[btn_type="deactivate"]:hover {{
                background-color: #2563eb;
            }}
            QPushButton[btn_type="deactivate"]:pressed {{
                background-color: #1d4ed8;
            }}
            QPushButton[btn_type="system"] {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 11px;
            }}
        """)

        self.btn_config.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #4f46e5;
            }}
            QPushButton:pressed {{
                background-color: #4338ca;
            }}
        """)

        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
            QPushButton:disabled {
                background-color: rgba(239, 68, 68, 0.15);
                color: rgba(239, 68, 68, 0.35);
                border: 1px solid rgba(239, 68, 68, 0.2);
            }
        """)



# ── 3. JANELA PRINCIPAL GERENCIADORA DE PLUGINS ─────────────────────────────

class PluginsWindow(QtWidgets.QDialog):
    """Diálogo completo de gerenciamento e inspeção de plugins."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciador de Plugins")
        self.resize(1060, 660)
        self.setMinimumSize(960, 600)

        self._plugin_cards = {}
        self._selected_plugin = None

        self._build_ui()
        self.populate_list()

        ThemeManager.instance().themeChanged.connect(self.update_theme_style)
        self.update_theme_style()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

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
        main_layout.addWidget(filter_widget)

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

        main_layout.addWidget(list_container, 1)

        # ── 3. Inspector de Detalhes (Direita - Largura Fixa) ──
        self.inspector = PluginDetailsInspector(self)
        self.inspector.setFixedWidth(350)

        self.inspector.action_toggled.connect(self._on_plugin_toggled)
        self.inspector.action_delete.connect(self._on_plugin_deleted)
        self.inspector.action_configure.connect(self._open_plugin_settings)

        main_layout.addWidget(self.inspector)



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
