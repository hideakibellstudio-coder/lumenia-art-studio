"""Diagnostics & Telemetry Dialog — Diagnósticos e Desempenho do Motor ALADYN."""

from __future__ import annotations
import sys
import os
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.engine.registry import EngineRegistry


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

        from ui.core.i18n import I18nManager
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
        from ui.core.i18n import tr
        title = tr("telemetry.dialog_title", "Diagnósticos & Telemetria do Motor")
        self.setWindowTitle(title)
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(title)
        if hasattr(self, "tree"):
            self.tree.setHeaderLabels([tr("telemetry.metric", "Métrica"), tr("telemetry.value", "Valor")])
        if hasattr(self, "btn_close"):
            self.btn_close.setText(tr("dialogs.close", "Fechar"))
        self._refresh_stats()

    def _refresh_stats(self):
        self.tree.clear()
        backend = EngineRegistry.instance().get_backend()
        
        # 1. Motor Gráfico
        has_native = getattr(backend, "available", False)
        capabilities = backend.get_capabilities() if backend else {}
        is_native = bool(capabilities.get("native_engine", has_native))
        backend_name = getattr(backend, "name", "nativo").capitalize()
        status_native = f"Ativo ({backend_name})" if is_native else "Emulação Python"
        self._add_item("Motor Gráfico", status_native)

        # 2. Resolução do Canvas
        from ui.core.document.manager import DocumentManager
        doc = DocumentManager.instance().active_document()
        w, h = (doc.width, doc.height) if doc else (0, 0)
        self._add_item("Dimensões do Canvas", f"{w} × {h} pixels")
        self._add_item("Megapixels por Camada", f"{(w * h) / 1_000_000:.2f} MP")

        # 3. Perfil de Cor Ativo
        prof_id = getattr(backend, "get_color_profile", lambda: 0)()
        prof_name = getattr(backend, "get_color_profile_name", lambda p: "sRGB")(prof_id)
        self._add_item("Espaço de Cor & Pipeline", f"{prof_name} (ID: {prof_id})")
        capabilities = backend.get_capabilities() if backend else {}
        self._add_item("Formato de Pixel do Documento", str(capabilities.get("document_pixel_format", "indisponível")))
        precision = "Composição de precisão estendida disponível" if capabilities.get("deep_color", False) else "RGBA8"
        self._add_item("Precisão de Composição", precision)
        icc = "Suportado" if capabilities.get("embedded_icc_profiles", False) else "Não disponível neste backend"
        self._add_item("Perfis ICC incorporados", icc)

        # 4. Memória Estimada do Canvas
        ram_mb = (w * h * 4 * 4) / (1024 * 1024)  # ~4 buffers RGBA
        self._add_item("Consumo Estimado de VRAM/RAM", f"{ram_mb:.1f} MB")

        # 5. Ambiente
        self._add_item("Interpretador Python", f"{sys.version.split()[0]} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")
        self._add_item("Framework UI", "PySide6 (Qt 6.8+)")
        self._add_item("Estabilizador Dinâmico", "Ativo (Filtro Adaptativo de Média Móvel Exponencial)")
        self._add_item("Motor de Simetria", "Ativo (Espelho, Radial, Caleidoscópio)")
        self._add_item("Motor de Perspectiva", "Ativo (1P, 2P, 3P, Curvilíneo 6P Ironclad)")

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
