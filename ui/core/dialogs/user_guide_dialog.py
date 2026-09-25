"""
User Guide Dialog — Diálogo de Visualização do Guia do Usuário e Documentação.
==============================================================================
Renderiza o guia em formato Markdown nativo com suporte a múltiplos idiomas,
busca e reatividade total ao Design System e Temas do Lumenia Studio.
"""

from pathlib import Path
from PySide6 import QtCore, QtWidgets
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.i18n import I18nManager, tr
from ui.infrastructure.runtime_paths import resource_path


class UserGuideDialog(BaseFramelessDialog):
    """Diálogo sem bordas que renderiza a documentação Markdown em múltiplos idiomas."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(
            title=tr("guide.title", "Guia do Usuário & Documentação"),
            icon_name="help",
            parent=parent,
            modal=True
        )
        self.resize(780, 620)
        self.setMinimumSize(600, 450)

        self._current_locale = I18nManager.instance().get_current_locale()
        self._build_guide_ui()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

        I18nManager.instance().languageChanged.connect(self._on_app_language_changed)

    def _build_guide_ui(self) -> None:
        # ── Barra de Ferramentas Superior do Guia ───────────────────────────
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setSpacing(10)

        self.lbl_lang = QtWidgets.QLabel(tr("guide.language", "Idioma do Guia:"))
        self.lbl_lang.setStyleSheet("font-size: 11px; font-weight: bold;")
        toolbar.addWidget(self.lbl_lang)

        self.combo_lang = QtWidgets.QComboBox()
        self.combo_lang.setFixedWidth(180)
        self.combo_lang.setCursor(QtCore.Qt.PointingHandCursor)

        locales = [
            ("pt_BR", "🇧🇷 Português (Brasil)"),
            ("en_US", "🇺🇸 English (US)"),
            ("es_ES", "🇪🇸 Español"),
            ("ja_JP", "🇯🇵 日本語"),
        ]
        for loc_id, loc_name in locales:
            self.combo_lang.addItem(loc_name, loc_id)

        # Seleciona o idioma atual
        for idx in range(self.combo_lang.count()):
            if self.combo_lang.itemData(idx) == self._current_locale:
                self.combo_lang.setCurrentIndex(idx)
                break

        self.combo_lang.currentIndexChanged.connect(self._on_lang_combo_changed)
        toolbar.addWidget(self.combo_lang)

        toolbar.addStretch()

        # Visualizador de Markdown
        self.browser = QtWidgets.QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setReadOnly(True)

        self.content_layout.addLayout(toolbar)
        self.content_layout.addWidget(self.browser, 1)

        # ── Rodapé com botão Fechar ─────────────────────────────────────────
        footer = QtWidgets.QHBoxLayout()
        footer.addStretch()

        self.btn_close = QtWidgets.QPushButton(tr("dialogs.close", "Fechar"))
        self.btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_close.setFixedWidth(90)
        self.btn_close.clicked.connect(self.accept)
        footer.addWidget(self.btn_close)

        self.content_layout.addLayout(footer)

        self._load_guide(self._current_locale)

    def _get_docs_dir(self) -> Path:
        """Localiza o diretório de documentação de forma determinística."""
        return resource_path("assets", "docs")

    def _load_guide(self, locale_code: str) -> None:
        """Carrega e renderiza o arquivo markdown correspondente ao idioma."""
        docs_dir = self._get_docs_dir()
        guide_file = docs_dir / f"guide_{locale_code}.md"

        if not guide_file.exists():
            guide_file = docs_dir / "guide_pt_BR.md"
        if not guide_file.exists():
            guide_file = docs_dir / "guide_en_US.md"

        content = ""
        if guide_file.exists():
            try:
                content = guide_file.read_text(encoding="utf-8")
            except Exception as ex:
                content = f"# Erro ao carregar documentação\n\nNão foi possível ler o arquivo: {ex}"
        else:
            content = "# Guia do Usuário\n\nArquivo de documentação não encontrado."

        self.browser.setMarkdown(content)

    def _on_lang_combo_changed(self, idx: int) -> None:
        loc_id = self.combo_lang.itemData(idx)
        if loc_id:
            self._current_locale = loc_id
            self._load_guide(loc_id)

    def _on_app_language_changed(self, new_locale: str) -> None:
        self._current_locale = new_locale
        self.combo_lang.blockSignals(True)
        for idx in range(self.combo_lang.count()):
            if self.combo_lang.itemData(idx) == new_locale:
                self.combo_lang.setCurrentIndex(idx)
                break
        self.combo_lang.blockSignals(False)
        self.retranslate_ui()
        self._load_guide(new_locale)

    def retranslate_ui(self) -> None:
        title = tr("guide.title", "Guia do Usuário & Documentação")
        self.setWindowTitle(title)
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(title)
        self.lbl_lang.setText(tr("guide.language", "Idioma do Guia:"))
        self.btn_close.setText(tr("dialogs.close", "Fechar"))

    def _apply_theme(self, *args) -> None:
        tm = ThemeManager.instance()
        bg_main = tm.get_color("bg_main", "#0f172a")
        bg_card = tm.get_color("bg_card", "#1e293b")
        bg_panel = tm.get_color("bg_panel", "#1e293b")
        bg_input = tm.get_color("bg_input", "#0f172a")
        border = tm.get_color("border", "#334155")
        text_main = tm.get_color("text_main", "#f8fafc")
        accent = tm.get_color("accent", "#3b82f6")

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
            QLabel {{ color: {text_main}; }}
            QComboBox {{
                background-color: {bg_input};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_card};
                color: {text_main};
                selection-background-color: {accent};
                selection-color: {text_main};
                border: 1px solid {border};
            }}
            QPushButton {{
                background-color: {bg_panel};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: {text_main};
                border-color: {accent};
            }}
        """)

        # Estilo do visualizador de Markdown
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg_card};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 16px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 13px;
                line-height: 1.6;
            }}
        """)
