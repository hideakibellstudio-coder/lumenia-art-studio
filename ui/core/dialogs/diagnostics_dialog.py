"""Diagnostics & Telemetry Dialog — Diagnósticos e Desempenho do Motor ALADYN."""

from __future__ import annotations
import sys

import PySide6
from PySide6 import QtCore, QtWidgets

from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.core.engine.telemetry_meters import simd_text
from ui.core.i18n import I18nManager, tr
from ui.core.theme.manager import ThemeManager


class DiagnosticsDialog(BaseFramelessDialog):
    """Diálogo de telemetria em tempo real, memória e integridade do motor nativo."""

    def __init__(self, parent=None):
        super().__init__(title="Diagnósticos & Telemetria do Motor", icon_name="chart", parent=parent, modal=True)
        self.resize(540, 500)

        self._build_ui()
        self._refresh_stats()

        # Timer de atualização em tempo real
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._refresh_stats)
        self.timer.start(1000)

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _build_ui(self):
        # Tabela de Telemetria
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Métrica", "Valor"])
        self.tree.setColumnWidth(0, 240)
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.content_layout.addWidget(self.tree, 1)

        # Botão Fechar
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()
        self.btn_close = QtWidgets.QPushButton("Fechar")
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_close)
        self.content_layout.addLayout(btn_box)

    def retranslate_ui(self) -> None:
        title = tr("telemetry.dialog_title", "Diagnósticos & Telemetria do Motor")
        self.setWindowTitle(title)
        self.title_bar.set_title(title)
        self.tree.setHeaderLabels([tr("telemetry.metric", "Métrica"), tr("telemetry.value", "Valor")])
        self.btn_close.setText(tr("dialogs.close", "Fechar"))
        self._refresh_stats()

    def _refresh_stats(self):
        """Só o que é lido do motor e do ambiente (até 2026-09-24 havia uma RAM
        "estimada" por fórmula e linhas fixas dizendo "Ativo")."""
        self.tree.clear()
        backend = EngineRegistry.instance().get_backend()
        caps = backend.get_capabilities() if backend is not None else {}

        # 1. Motor Gráfico
        engine = f"Ativo ({backend.name.capitalize()})" if caps.get("native_engine") else "Indisponível"
        self._add_item("Motor Gráfico", engine)

        # 2. Resolução do Canvas
        doc = DocumentManager.instance().active_document()
        w, h = (doc.width, doc.height) if doc else (0, 0)
        self._add_item("Dimensões do Canvas", f"{w} × {h} pixels")
        self._add_item("Megapixels por Camada", f"{(w * h) / 1_000_000:.2f} MP")

        # 3. Perfil de Cor Ativo
        if backend is not None:
            prof_id = backend.get_color_profile()
            self._add_item("Espaço de Cor & Pipeline", f"{backend.get_color_profile_name(prof_id)} (ID: {prof_id})")
        self._add_item("Formato de Pixel do Documento", str(caps.get("document_pixel_format", "indisponível")))
        precision = "Composição de precisão estendida disponível" if caps.get("deep_color", False) else "RGBA8"
        self._add_item("Precisão de Composição", precision)
        icc = "Suportado" if caps.get("embedded_icc_profiles", False) else "Não disponível neste backend"
        self._add_item("Perfis ICC incorporados", icc)

        # 4. Memória medida pelo motor (tiles alocados e histórico)
        if backend is not None:
            snap = backend.get_telemetry_snapshot()
            self._add_item("RAM do Canvas (tiles)", f"{snap.tile_grid_memory_mb:.1f} MB ({snap.active_tile_count} tiles)")
            self._add_item("RAM do Histórico", f"{snap.undo_stack_memory_mb:.1f} MB ({snap.undo_steps_count} passos)")
            self._add_item("Instruções SIMD", simd_text(snap))

        # 5. Ambiente
        self._add_item("Interpretador Python", f"{sys.version.split()[0]} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")
        self._add_item("Framework UI", f"PySide6 {PySide6.__version__} (Qt {QtCore.qVersion()})")

    def _add_item(self, key: str, val: str):
        item = QtWidgets.QTreeWidgetItem([key, val])
        self.tree.addTopLevelItem(item)

    def _apply_theme(self, *args):
        theme = ThemeManager.instance()
        border = theme.get_color("border", "#2e2e38")
        text = theme.get_color("text_main", "#ffffff")
        bg_card = theme.get_color("bg_panel", "#1e1e24")
        self.setStyleSheet(f"""
            QTreeWidget {{ background-color: {bg_card}; color: {text}; border: 1px solid {border}; border-radius: 6px; }}
            QHeaderView::section {{ background-color: {theme.get_color("bg_input", "#26262e")}; color: {text}; font-weight: bold; border: 1px solid {border}; padding: 4px; }}
        """)
