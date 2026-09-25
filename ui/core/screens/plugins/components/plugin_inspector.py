"""PluginDetailsInspector component for PluginsWindow."""
import logging

import sys
from PySide6 import QtCore, QtGui, QtWidgets
from ui.infrastructure.i18n import tr
from ui.infrastructure.theme.manager import ThemeManager
from ui.core.plugins.manager import PluginManager
from ui.core.plugins.metadata import PluginMetadata
from ui.infrastructure.icons import get_icon


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

        # Scroll Area para o Inspector de Detalhes
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

        self.lbl_id_title = QtWidgets.QLabel("Identificador:")
        self.lbl_path_title = QtWidgets.QLabel("Caminho:")
        self.lbl_type_title = QtWidgets.QLabel("Tipo:")
        self.lbl_priority_title = QtWidgets.QLabel("Prioridade:")
        self.lbl_deps_title = QtWidgets.QLabel("Dependências:")

        props_form.addRow(self.lbl_id_title, self.lbl_id)
        props_form.addRow(self.lbl_path_title, self.lbl_path)
        props_form.addRow(self.lbl_type_title, self.lbl_type)
        props_form.addRow(self.lbl_priority_title, self.lbl_priority)
        props_form.addRow(self.lbl_deps_title, self.lbl_deps)

        det_layout.addLayout(props_form)

        # Descrição Completa
        self.lbl_desc_title = QtWidgets.QLabel("Descrição Completa:")
        det_layout.addWidget(self.lbl_desc_title)
        self.txt_desc = QtWidgets.QTextEdit()
        self.txt_desc.setReadOnly(True)
        self.txt_desc.setFixedHeight(85)
        det_layout.addWidget(self.txt_desc)

        det_layout.addStretch()

        # Barra de Ações (Rodapé do Inspector)
        actions_box = QtWidgets.QHBoxLayout()
        actions_box.setSpacing(8)

        self.btn_toggle = QtWidgets.QPushButton()
        self.btn_toggle.setIconSize(QtCore.QSize(14, 14))
        self.btn_toggle.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)

        self.btn_config = QtWidgets.QPushButton(" Configurar")
        self.btn_config.setIcon(get_icon("settings", ThemeManager.instance().get_color("FG_PRIMARY", "#ffffff")))
        self.btn_config.setIconSize(QtCore.QSize(14, 14))
        self.btn_config.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_config.clicked.connect(lambda: self.current_plugin and self.action_configure.emit(self.current_plugin))

        self.btn_delete = QtWidgets.QPushButton(" Excluir")
        self.btn_delete.setIcon(get_icon("trash", ThemeManager.instance().get_color("FG_PRIMARY", "#ffffff")))
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

    def retranslate_ui(self):
        from ui.infrastructure.i18n import tr
        if hasattr(self, "empty_label"):
            self.empty_label.setText(tr("plugins.select_plugin", "Selecione um plugin na lista ao lado para visualizar os detalhes."))
        if hasattr(self, "btn_config"):
            self.btn_config.setText(f" {tr('plugins.configure', 'Configurações')}")
        if hasattr(self, "btn_delete"):
            self.btn_delete.setText(f" {tr('plugins.uninstall', 'Desinstalar Plugin')}")
        if hasattr(self, "lbl_id_title"):
            self.lbl_id_title.setText(tr("plugins.id", "Identificador:"))
        if hasattr(self, "lbl_path_title"):
            self.lbl_path_title.setText(tr("plugins.path", "Caminho no Disco:"))
        if hasattr(self, "lbl_type_title"):
            self.lbl_type_title.setText(tr("plugins.type", "Tipo de Plugin:"))
        if hasattr(self, "lbl_priority_title"):
            self.lbl_priority_title.setText(tr("plugins.priority", "Prioridade:"))
        if hasattr(self, "lbl_deps_title"):
            self.lbl_deps_title.setText(tr("plugins.deps", "Dependências:"))
        if hasattr(self, "lbl_desc_title"):
            self.lbl_desc_title.setText(tr("plugins.desc", "Descrição:"))
        if hasattr(self, "current_plugin") and self.current_plugin:
            self.set_plugin(self.current_plugin, getattr(self, "_is_active", False))

    def set_plugin(self, plugin, is_active: bool) -> None:
        self.current_plugin = plugin
        self._is_active = is_active
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
            logging.getLogger(__name__).debug("is_system_plugin() falhou.", exc_info=True)

        try:
            meta: PluginMetadata = plugin.get_metadata()
            p_id = meta.id if hasattr(meta, "id") and meta.id else class_name
            p_name = meta.name
            p_version = meta.version
            p_author = meta.author
            p_desc = meta.description
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

        from ui.infrastructure.i18n import tr
        if is_system:
            self.btn_toggle.setText(f" {tr('plugins.filter_system', 'Sistema')}")
            self.btn_toggle.setIcon(get_icon("lock", ThemeManager.instance().get_color("FG_SECONDARY", "#9ca3af")))
            self.btn_toggle.setEnabled(False)
            self.btn_toggle.setProperty("btn_type", "system")
        elif is_active:
            self.btn_toggle.setText(f" {tr('plugins.deactivate', 'Desativar')}")
            self.btn_toggle.setIcon(get_icon("power", ThemeManager.instance().get_color("FG_PRIMARY", "#ffffff")))
            self.btn_toggle.setEnabled(True)
            self.btn_toggle.setProperty("btn_type", "deactivate")
        else:
            self.btn_toggle.setText(f" {tr('plugins.activate', 'Ativar')}")
            self.btn_toggle.setIcon(get_icon("power", ThemeManager.instance().get_color("FG_PRIMARY", "#ffffff")))
            self.btn_toggle.setEnabled(True)
            self.btn_toggle.setProperty("btn_type", "activate")

        self.btn_toggle.style().unpolish(self.btn_toggle)
        self.btn_toggle.style().polish(self.btn_toggle)

        self.btn_config.setVisible(hasattr(plugin, "has_settings_ui") and plugin.has_settings_ui())

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
            tr("messages.plugin_delete_title", "Confirmar Exclusão de Plugin"),
            tr("messages.plugin_delete_question",
               "Deseja realmente excluir e remover do disco o plugin '{name}'?\n\nEsta ação não poderá ser desfeita.",
               name=p_name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.action_delete.emit(c_name)

    def update_theme_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        bg_card = theme.get_color("bg_card", "#1e1e24")
        bg_input = theme.get_color("bg_input", "#121214")
        border = theme.get_color("border", "#2e2e38")
        text_main = theme.get_color("text_main", "#f3f4f6")
        text_sec = theme.get_color("text_sec", "#94a3b8")
        accent = theme.get_color("accent", "#6366f1")
        accent_hover = theme.get_color("accent_hover", "#4f46e5")
        danger = theme.get_color("danger", "#ef4444")
        danger_hover = theme.get_color("danger_hover", "#dc2626")
        success = theme.get_color("success", "#10b981")

        self.setStyleSheet(f"""
            PluginDetailsInspector {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLabel {{ color: {text_main}; }}
            QTextEdit {{
                background-color: {bg_input};
                border: 1px solid {border};
                border-radius: 4px;
                color: {text_main};
                font-size: 11px;
            }}
        """)
        self.empty_label.setStyleSheet(f"color: {text_sec}; font-size: 13px;")
        self.sep.setStyleSheet(f"background-color: {border}; max-height: 1px;")

        for lbl in [getattr(self, a, None) for a in ["lbl_id_title", "lbl_path_title", "lbl_type_title", "lbl_priority_title", "lbl_deps_title", "lbl_desc_title"]]:
            if lbl:
                lbl.setStyleSheet(f"color: {text_sec}; font-size: 11px; font-weight: 500;")

        self.btn_toggle.setStyleSheet(f"""
            QPushButton[btn_type="activate"] {{
                background-color: {success}; color: {text_main}; border: none; border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }}
            QPushButton[btn_type="activate"]:hover {{ background-color: #059669; }}
            QPushButton[btn_type="deactivate"] {{
                background-color: {accent}; color: {text_main}; border: none; border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }}
            QPushButton[btn_type="deactivate"]:hover {{ background-color: {accent_hover}; }}
            QPushButton[btn_type="system"] {{
                background-color: {bg_card}; color: {text_sec}; border: 1px solid {border}; border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }}
        """)

        self.btn_config.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent}; color: {text_main}; border: none; border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {accent_hover}; }}
        """)

        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background-color: {danger}; color: {text_main}; border: none; border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {danger_hover}; }}
            QPushButton:disabled {{
                background-color: {bg_card}; color: {text_sec}; border: 1px solid {border};
            }}
        """)
