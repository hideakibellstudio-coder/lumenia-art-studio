"""
Test Report Dialog — Relatório de Testes e Verificação do Sistema.
==================================================================
Executa `tests/run_all_tests.py` sem travar a interface (log em tempo real)
e mostra o resultado MEDIDO: total, taxa de sucesso, falhas e pulados, e o
resultado por seção (`test_report_model.SECTIONS`). Antes de executar, os
valores aparecem como "—".

Até 2026-09-24 os cartões e a tabela eram fixos ("110 testes", "100%",
"SIMD AVX2 Ativo", "APROVADO" em todas as linhas), independentes da execução.
"""

import os

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.dialogs.test_report_model import SECTIONS, SuiteReport, parse_junit
from ui.core.dialogs.test_report_runner import TestRunnerThread
from ui.core.theme.manager import ThemeManager
from ui.core.i18n import I18nManager, tr
from ui.core.icons import get_icon

# (chave de tradução, título padrão, token de cor do tema)
_KPIS = (
    ("kpi_total", "Total de Testes", "ACCENT"),
    ("kpi_pass_rate", "Taxa de Sucesso", "SUCCESS"),
    ("kpi_failed", "Falhas", "DANGER"),
    ("kpi_skipped", "Pulados", "WARNING"),
)
_NOT_RUN = "—"


class TestReportDialog(BaseFramelessDialog):
    """Diálogo executivo com relatório dos testes, métricas e console de execução."""

    __test__ = False

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(
            title=tr("test_report.title", "Relatório de Testes & Verificação do Sistema"),
            icon_name="check",
            parent=parent,
            modal=True,
        )
        self.resize(840, 660)
        self.setMinimumSize(680, 500)

        self._current_locale = I18nManager.instance().get_current_locale()
        self._runner_thread = None
        self._report: SuiteReport | None = None  # None = ainda não executado

        self._build_report_ui()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

        I18nManager.instance().languageChanged.connect(self._on_app_language_changed)

    def _build_report_ui(self) -> None:
        tm = ThemeManager.instance()
        # ── 1. Barra Superior: Idioma & Subtítulo ───────────────────────────
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setSpacing(10)

        self.lbl_subtitle = QtWidgets.QLabel(
            tr("test_report.subtitle", "Validação Executiva do Motor ALADYN C++20 e Arquitetura ARCcC")
        )
        self.lbl_subtitle.setStyleSheet("font-size: 11px; font-weight: 600;")
        top_bar.addWidget(self.lbl_subtitle, 1)

        self.lbl_lang = QtWidgets.QLabel(tr("test_report.language", "Idioma do Relatório:"))
        self.lbl_lang.setStyleSheet("font-size: 11px; font-weight: bold;")
        top_bar.addWidget(self.lbl_lang)

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

        for idx in range(self.combo_lang.count()):
            if self.combo_lang.itemData(idx) == self._current_locale:
                self.combo_lang.setCurrentIndex(idx)
                break

        self.combo_lang.currentIndexChanged.connect(self._on_lang_combo_changed)
        top_bar.addWidget(self.combo_lang)

        self.content_layout.addLayout(top_bar)

        # ── 2. Cards de KPIs Executivos ─────────────────────────────────────
        kpi_layout = QtWidgets.QHBoxLayout()
        kpi_layout.setSpacing(10)

        self.kpi_cards = []
        for key, default_title, color_token in _KPIS:
            card = QtWidgets.QFrame()
            card.setObjectName("KpiCard")
            card_lay = QtWidgets.QVBoxLayout(card)
            card_lay.setContentsMargins(12, 10, 12, 10)
            card_lay.setSpacing(4)
            lbl_t = QtWidgets.QLabel(tr(f"test_report.{key}", default_title))
            lbl_t.setObjectName("KpiTitle")
            lbl_t.setStyleSheet("font-size: 10px; font-weight: bold;")
            lbl_v = QtWidgets.QLabel(_NOT_RUN)
            lbl_v.setObjectName("KpiValue")
            lbl_v.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {tm.get_color(color_token)};")
            card_lay.addWidget(lbl_t)
            card_lay.addWidget(lbl_v)
            kpi_layout.addWidget(card)
            self.kpi_cards.append((card, lbl_t, lbl_v, key, default_title))

        self.content_layout.addLayout(kpi_layout)

        # ── 3. Tabela de Módulos Auditados ──────────────────────────────────
        self.table = QtWidgets.QTableWidget(len(SECTIONS), 3)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setFixedHeight(175)

        self._set_table_headers()
        self._populate_module_table()
        self.content_layout.addWidget(self.table)

        # ── 4. Ações & Console de Execução ──────────────────────────────────
        actions_bar = QtWidgets.QHBoxLayout()
        actions_bar.setSpacing(10)

        self.lbl_log_title = QtWidgets.QLabel(tr("test_report.log_output", "Console de Execução em Tempo Real"))
        self.lbl_log_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        actions_bar.addWidget(self.lbl_log_title)
        actions_bar.addStretch()

        self.btn_run = QtWidgets.QPushButton(f" {tr('test_report.run_tests', 'Executar Suíte de Testes')}")
        self.btn_run.setObjectName("accentButton")
        self.btn_run.setIcon(get_icon("play", tm.get_color("FG_PRIMARY", "#ffffff")))
        self.btn_run.setIconSize(QtCore.QSize(14, 14))
        self.btn_run.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self._start_tests)
        actions_bar.addWidget(self.btn_run)

        self.content_layout.addLayout(actions_bar)

        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(2000)
        self.txt_log.setPlaceholderText("Clique em 'Executar Suíte de Testes' para rodar a validação completa...")
        self.content_layout.addWidget(self.txt_log, 1)

        # ── 5. Rodapé ───────────────────────────────────────────────────────
        footer = QtWidgets.QHBoxLayout()
        footer.addStretch()

        self.btn_close = QtWidgets.QPushButton(tr("dialogs.close", "Fechar"))
        self.btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_close.setFixedWidth(90)
        self.btn_close.clicked.connect(self.accept)
        footer.addWidget(self.btn_close)

        self.content_layout.addLayout(footer)

    def _populate_module_table(self) -> None:
        """Seções com o resultado medido (ou "—" antes de executar)."""
        self.table.setRowCount(0)
        tm = ThemeManager.instance()
        report = self._report
        for key, default_title, _prefixes in SECTIONS:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 24)
            item_mod = QtWidgets.QTableWidgetItem(f" {tr(f'test_report.{key}', default_title)}")
            item_mod.setForeground(QtGui.QBrush(QtGui.QColor(tm.get_color("text_main"))))
            self.table.setItem(row, 0, item_mod)

            counts = report.sections[key] if report is not None else None
            if counts is None or counts.total == 0:
                status, detail, color, icon = _NOT_RUN, _NOT_RUN, tm.get_color("text_sec"), None
            elif counts.failed:
                status, color, icon = tr("test_report.failed", "FALHOU"), tm.get_color("DANGER"), "warning"
                detail = self._counts_text(counts)
            else:
                status, color, icon = tr("test_report.passed", "APROVADO"), tm.get_color("SUCCESS"), "check_circle"
                detail = self._counts_text(counts)
            item_st = QtWidgets.QTableWidgetItem(status)
            item_st.setTextAlignment(QtCore.Qt.AlignCenter)
            item_st.setForeground(QtGui.QBrush(QtGui.QColor(color)))
            if icon:
                item_st.setIcon(get_icon(icon, color))
            self.table.setItem(row, 1, item_st)
            item_res = QtWidgets.QTableWidgetItem(detail)
            item_res.setTextAlignment(QtCore.Qt.AlignCenter)
            item_res.setForeground(QtGui.QBrush(QtGui.QColor(tm.get_color("text_sec"))))
            self.table.setItem(row, 2, item_res)

    @staticmethod
    def _counts_text(counts) -> str:
        return tr("test_report.result_fmt", "{passed} de {ran} passaram").format(
            passed=counts.passed, ran=counts.passed + counts.failed)

    def _show_kpis(self) -> None:
        report = self._report
        values = (_NOT_RUN,) * 4 if report is None else (
            str(report.total.total), f"{report.pass_rate:.1f}%", str(report.total.failed), str(report.total.skipped))
        for (_card, _title, lbl_value, _key, _default), value in zip(self.kpi_cards, values):
            lbl_value.setText(value)

    def show_report(self, report: SuiteReport | None) -> None:
        """Mostra um resultado medido (None volta para "não executado")."""
        self._report = report
        self._show_kpis()
        self._populate_module_table()

    def _start_tests(self) -> None:
        if self._runner_thread and self._runner_thread.isRunning():
            return

        self.btn_run.setEnabled(False)
        self.btn_run.setText(f" {tr('test_report.running', 'Executando testes...')}")
        self.txt_log.clear()
        self.txt_log.appendPlainText("Iniciando suíte executiva completa (python tests/run_all_tests.py)...\n")

        self._runner_thread = TestRunnerThread(self)
        self._runner_thread.log_received.connect(self._on_log_line)
        self._runner_thread.tests_finished.connect(self._on_tests_finished)
        self._runner_thread.start()

    def _on_log_line(self, line: str) -> None:
        self.txt_log.insertPlainText(line)
        self.txt_log.ensureCursorVisible()

    def _on_tests_finished(self, exit_code: int, junit_path: str) -> None:
        self.btn_run.setEnabled(True)
        self.btn_run.setText(f" {tr('test_report.run_tests', 'Executar Suíte de Testes')}")
        if junit_path and os.path.getsize(junit_path) > 0:
            self.show_report(parse_junit(junit_path))
        if junit_path:
            os.remove(junit_path)
        if exit_code == 0:
            self.txt_log.appendPlainText("\nTODOS OS TESTES FORAM CONCLUÍDOS COM 100% DE SUCESSO!\n")
        else:
            self.txt_log.appendPlainText(f"\nSuíte finalizada com código de erro {exit_code}.\n")

    def _on_lang_combo_changed(self, idx: int) -> None:
        loc_id = self.combo_lang.itemData(idx)
        if loc_id:
            self._current_locale = loc_id
            I18nManager.instance().set_locale(loc_id)

    def _on_app_language_changed(self, new_locale: str) -> None:
        self._current_locale = new_locale
        self.combo_lang.blockSignals(True)
        for idx in range(self.combo_lang.count()):
            if self.combo_lang.itemData(idx) == new_locale:
                self.combo_lang.setCurrentIndex(idx)
                break
        self.combo_lang.blockSignals(False)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        title = tr("test_report.title", "Relatório de Testes & Verificação do Sistema")
        self.setWindowTitle(title)
        self.title_bar.set_title(title)
        self.lbl_subtitle.setText(
            tr("test_report.subtitle", "Validação Executiva do Motor ALADYN C++20 e Arquitetura ARCcC")
        )
        self.lbl_lang.setText(tr("test_report.language", "Idioma do Relatório:"))
        self.lbl_log_title.setText(tr("test_report.log_output", "Console de Execução em Tempo Real"))
        self.btn_run.setText(f" {tr('test_report.run_tests', 'Executar Suíte de Testes')}")
        self.btn_close.setText(tr("dialogs.close", "Fechar"))

        for _card, lbl_t, _value, key, default_title in self.kpi_cards:
            lbl_t.setText(tr(f"test_report.{key}", default_title))
        self._set_table_headers()
        self._populate_module_table()

    def _set_table_headers(self) -> None:
        self.table.setHorizontalHeaderLabels([
            tr("dialogs.module_col", "Módulo / Subsistema"),
            tr("dialogs.status_col", "Status"),
            tr("test_report.result_col", "Resultado"),
        ])

    def _apply_theme(self, *args) -> None:
        tm = ThemeManager.instance()
        bg_main = tm.get_color("bg_main", "#0f172a")
        bg_card = tm.get_color("bg_card", "#1e293b")
        bg_panel = tm.get_color("bg_panel", "#1e293b")
        bg_input = tm.get_color("bg_input", "#0f172a")
        border = tm.get_color("border", "#334155")
        text_main = tm.get_color("text_main", "#f8fafc")
        text_sec = tm.get_color("text_sec", "#94a3b8")
        accent = tm.get_color("accent", "#3b82f6")
        accent_hover = tm.get_color("accent_hover", "#60a5fa")

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
            QFrame#KpiCard {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLabel#KpiTitle {{
                color: {text_sec};
            }}
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
            QTableWidget {{
                background-color: {bg_panel};
                color: {text_main};
                border: 1px solid {border};
                gridline-color: {border};
                border-radius: 8px;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {bg_card};
                color: {text_sec};
                font-weight: bold;
                font-size: 11px;
                padding: 6px;
                border: none;
                border-bottom: 1px solid {border};
            }}
            QPlainTextEdit {{
                background-color: {bg_input};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 10px;
                font-family: Consolas, "Courier New", monospace;
                font-size: 11px;
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
            QPushButton#accentButton {{
                background-color: {accent};
                color: {text_main};
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton#accentButton:hover {{
                background-color: {accent_hover};
            }}
        """)
        self.lbl_subtitle.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {text_sec};")
        self.lbl_lang.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_sec};")
        self.lbl_log_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_sec};")
        self._populate_module_table()
