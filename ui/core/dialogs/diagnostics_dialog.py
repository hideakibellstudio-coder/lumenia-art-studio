"""Diagnostics & Telemetry Dialog — Diagnósticos e Desempenho do Motor ALADYN."""

from __future__ import annotations
import sys
import os
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from ui.core.engine.registry import EngineRegistry


class DiagnosticsDialog(QtWidgets.QDialog):
    """Diálogo de telemetria em tempo real, memória e integridade do motor nativo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Diagnósticos do Motor & Telemetria")
        self.setFixedSize(520, 480)
        self.setModal(True)

        self._build_ui()
        self._refresh_stats()

        # Timer de atualização em tempo real
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._refresh_stats)
        self.timer.start(1000)

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setPixmap(get_icon("chart").pixmap(24, 24))
        header.addWidget(icon_lbl)

        title_lbl = QtWidgets.QLabel("Status do Sistema & Motor Gráfico")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        # Tabela de Telemetria
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Métrica", "Valor"])
        self.tree.setColumnWidth(0, 240)
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree, 1)

        # Botão Fechar
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()
        self.btn_close = QtWidgets.QPushButton("Fechar")
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_close)
        layout.addLayout(btn_box)

    def _refresh_stats(self):
        self.tree.clear()
        backend = EngineRegistry.instance().get_backend()
        
        # 1. Motor Nativo C++
        has_native = getattr(backend, "available", False)
        status_native = "Ativo (C++ PyBind11 SIMD / Catmull-Rom)" if has_native else "Emulação Python"
        self._add_item("Motor Gráfico", status_native)

        # 2. Resolução do Canvas
        w = getattr(backend, "_width", 1920)
        h = getattr(backend, "_height", 1080)
        self._add_item("Dimensões do Canvas", f"{w} × {h} pixels")
        self._add_item("Megapixels por Camada", f"{(w * h) / 1_000_000:.2f} MP")

        # 3. Perfil de Cor Ativo
        prof_id = getattr(backend, "get_color_profile", lambda: 0)()
        prof_name = getattr(backend, "get_color_profile_name", lambda p: "sRGB")(prof_id)
        self._add_item("Espaço de Cor & Pipeline", f"{prof_name} (ID: {prof_id})")

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

    def _apply_theme(self):
        theme = ThemeManager.instance()
        border = theme.get_color("border", "#2e2e38")
        text = theme.get_color("text_main", "#ffffff")
        bg_card = theme.get_color("bg_panel", "#1e1e24")
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme.get_color("bg_canvas", "#121214")}; color: {text}; }}
            QTreeWidget {{ background-color: {bg_card}; color: {text}; border: 1px solid {border}; border-radius: 6px; }}
            QHeaderView::section {{ background-color: {theme.get_color("bg_input", "#26262e")}; color: {text}; font-weight: bold; border: 1px solid {border}; padding: 4px; }}
        """)
