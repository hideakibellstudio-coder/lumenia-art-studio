"""PluginDetailsInspector component for PluginsWindow."""

import sys
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.plugins.manager import PluginManager
from ui.core.icons import get_icon


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

        self.btn_toggle.setStyleSheet("""
            QPushButton[btn_type="activate"] {
                background-color: #10b981; color: #ffffff; border: none; border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }
            QPushButton[btn_type="activate"]:hover { background-color: #059669; }
            QPushButton[btn_type="deactivate"] {
                background-color: #3b82f6; color: #ffffff; border: none; border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }
            QPushButton[btn_type="deactivate"]:hover { background-color: #2563eb; }
            QPushButton[btn_type="system"] {
                background-color: rgba(255, 255, 255, 0.08); color: #9ca3af; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }
        """)

        self.btn_config.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent}; color: #ffffff; border: none; border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: #4f46e5; }}
        """)

        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #ef4444; color: #ffffff; border: none; border-radius: 6px; padding: 7px 10px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #dc2626; }
            QPushButton:disabled {
                background-color: rgba(239, 68, 68, 0.15); color: rgba(239, 68, 68, 0.35); border: 1px solid rgba(239, 68, 68, 0.2);
            }
        """)
