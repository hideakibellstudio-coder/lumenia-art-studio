"""
SecondaryToolBar — Barra Secundária de Opções Contextuais da Ferramenta Ativa (Lumenia V2)
==========================================================================================
Barra flutuante compacta em formato de cápsula que se acopla dinamicamente à FloatingToolbar
ou ao topo do canvas, exibindo as opções contextuais imediatas da ferramenta selecionada.
"""

from __future__ import annotations

from typing import Optional, Dict
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class SecondaryToolBar(QtWidgets.QDialog):
    """Barra flutuante secundária exibindo opções contextuais da ferramenta ativa."""

    settingsChanged = QtCore.Signal(str, dict)  # tool_id, settings

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("QDialog { background: transparent; border: none; }")

        self._active_tool_id: str = "eyedrop"
        self._current_color: QtGui.QColor = QtGui.QColor(0, 0, 0)
        self._settings_cache: Dict[str, dict] = {
            "eyedrop": {"sample_size": "1x1 Ponto Único", "sample_radius": 0, "sample_all": True, "show_loupe": True},
            "bucket": {"tolerance": 20, "contiguous": True, "sample_all": True},
        }

        self._build_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(lambda _: self._apply_theme())

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        # Container Cápsula
        self.container = QtWidgets.QWidget(self)
        self.container.setObjectName("SecondaryBarContainer")

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(6)
        shadow.setXOffset(0)
        shadow.setYOffset(1)
        shadow.setColor(QtGui.QColor(0, 0, 0, 120))
        self.container.setGraphicsEffect(shadow)

        self.box_layout = QtWidgets.QHBoxLayout(self.container)
        self.box_layout.setContentsMargins(8, 2, 8, 2)
        self.box_layout.setSpacing(6)
        self.box_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Stack de widgets por ferramenta
        self.stacked_widget = QtWidgets.QStackedWidget(self.container)
        self.stacked_widget.setFixedHeight(26)

        # ── 1. Painel Eyedrop ──────────────────────────────────────────────
        self.panel_eyedrop = QtWidgets.QWidget()
        lay_eye = QtWidgets.QHBoxLayout(self.panel_eyedrop)
        lay_eye.setContentsMargins(0, 0, 0, 0)
        lay_eye.setSpacing(6)

        from ui.core.icons import get_icon
        lbl_eye = QtWidgets.QLabel()
        lbl_eye.setFixedSize(20, 20)
        lbl_eye.setPixmap(get_icon("eyedrop").pixmap(16, 16))
        lay_eye.addWidget(lbl_eye)

        self.cbo_sample = QtWidgets.QComboBox()
        self.cbo_sample.addItems(["1x1 Ponto", "3x3 Média", "5x5 Média", "11x11 Média"])
        self.cbo_sample.setFixedHeight(24)
        self.cbo_sample.currentIndexChanged.connect(self._on_eyedrop_changed)
        lay_eye.addWidget(self.cbo_sample)

        self.btn_merged = QtWidgets.QToolButton()
        self.btn_merged.setText("Todas Camadas")
        self.btn_merged.setCheckable(True)
        self.btn_merged.setChecked(True)
        self.btn_merged.setFixedHeight(24)
        self.btn_merged.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_merged.toggled.connect(self._on_eyedrop_changed)
        lay_eye.addWidget(self.btn_merged)

        self.swatch = QtWidgets.QLabel()
        self.swatch.setFixedSize(22, 22)
        self.swatch.setStyleSheet("background: #000000; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);")
        lay_eye.addWidget(self.swatch)

        self.lbl_hex = QtWidgets.QLabel("#000000")
        self.lbl_hex.setStyleSheet("font-size: 11px; font-weight: bold;")
        lay_eye.addWidget(self.lbl_hex)

        self.stacked_widget.addWidget(self.panel_eyedrop)

        # ── 2. Painel Balde de Tinta (Bucket) ──────────────────────────────
        self.panel_bucket = QtWidgets.QWidget()
        lay_bkt = QtWidgets.QHBoxLayout(self.panel_bucket)
        lay_bkt.setContentsMargins(0, 0, 0, 0)
        lay_bkt.setSpacing(6)

        lbl_bkt = QtWidgets.QLabel()
        lbl_bkt.setFixedSize(20, 20)
        lbl_bkt.setPixmap(get_icon("bucket").pixmap(16, 16))
        lay_bkt.addWidget(lbl_bkt)

        lbl_tol = QtWidgets.QLabel("Tol:")
        lbl_tol.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        lay_bkt.addWidget(lbl_tol)

        self.slider_bkt_tol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_bkt_tol.setRange(0, 100)
        self.slider_bkt_tol.setValue(20)
        self.slider_bkt_tol.setFixedWidth(60)
        self.slider_bkt_tol.setFixedHeight(18)
        self.lbl_bkt_tol_val = QtWidgets.QLabel("20%")
        self.lbl_bkt_tol_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_bkt_tol.valueChanged.connect(lambda v: self.lbl_bkt_tol_val.setText(f"{v}%"))
        self.slider_bkt_tol.valueChanged.connect(self._on_bucket_changed)
        lay_bkt.addWidget(self.slider_bkt_tol)
        lay_bkt.addWidget(self.lbl_bkt_tol_val)

        lbl_exp = QtWidgets.QLabel("Exp:")
        lbl_exp.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        lay_bkt.addWidget(lbl_exp)

        self.slider_bkt_exp = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_bkt_exp.setRange(-10, 10)
        self.slider_bkt_exp.setValue(1)
        self.slider_bkt_exp.setFixedWidth(50)
        self.slider_bkt_exp.setFixedHeight(18)
        self.lbl_bkt_exp_val = QtWidgets.QLabel("+1px")
        self.lbl_bkt_exp_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_bkt_exp.valueChanged.connect(lambda v: self.lbl_bkt_exp_val.setText(f"{v:+d}px" if v != 0 else "0px"))
        self.slider_bkt_exp.valueChanged.connect(self._on_bucket_changed)
        lay_bkt.addWidget(self.slider_bkt_exp)
        lay_bkt.addWidget(self.lbl_bkt_exp_val)

        self.btn_bkt_contig = QtWidgets.QToolButton()
        self.btn_bkt_contig.setText("Contíguo")
        self.btn_bkt_contig.setCheckable(True)
        self.btn_bkt_contig.setChecked(True)
        self.btn_bkt_contig.setFixedHeight(24)
        self.btn_bkt_contig.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_bkt_contig.toggled.connect(self._on_bucket_changed)
        lay_bkt.addWidget(self.btn_bkt_contig)

        self.btn_bkt_merged = QtWidgets.QToolButton()
        self.btn_bkt_merged.setText("Todas Camadas")
        self.btn_bkt_merged.setCheckable(True)
        self.btn_bkt_merged.setChecked(True)
        self.btn_bkt_merged.setFixedHeight(24)
        self.btn_bkt_merged.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_bkt_merged.toggled.connect(self._on_bucket_changed)
        lay_bkt.addWidget(self.btn_bkt_merged)

        self.stacked_widget.addWidget(self.panel_bucket)

        # ── 3. Painel Varinha Mágica (Magic Wand) ──────────────────────────
        self.panel_wand = QtWidgets.QWidget()
        lay_wnd = QtWidgets.QHBoxLayout(self.panel_wand)
        lay_wnd.setContentsMargins(0, 0, 0, 0)
        lay_wnd.setSpacing(6)

        lbl_wnd = QtWidgets.QLabel()
        lbl_wnd.setFixedSize(20, 20)
        lbl_wnd.setPixmap(get_icon("wand").pixmap(16, 16))
        lay_wnd.addWidget(lbl_wnd)

        lbl_wtol = QtWidgets.QLabel("Tol:")
        lbl_wtol.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        lay_wnd.addWidget(lbl_wtol)

        self.slider_wand_tol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_wand_tol.setRange(0, 100)
        self.slider_wand_tol.setValue(20)
        self.slider_wand_tol.setFixedWidth(60)
        self.slider_wand_tol.setFixedHeight(18)
        self.lbl_wand_tol_val = QtWidgets.QLabel("20%")
        self.lbl_wand_tol_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_wand_tol.valueChanged.connect(lambda v: self.lbl_wand_tol_val.setText(f"{v}%"))
        self.slider_wand_tol.valueChanged.connect(self._on_wand_changed)
        lay_wnd.addWidget(self.slider_wand_tol)
        lay_wnd.addWidget(self.lbl_wand_tol_val)

        self.btn_wand_contig = QtWidgets.QToolButton()
        self.btn_wand_contig.setText("Contíguo")
        self.btn_wand_contig.setCheckable(True)
        self.btn_wand_contig.setChecked(True)
        self.btn_wand_contig.setFixedHeight(24)
        self.btn_wand_contig.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_wand_contig.toggled.connect(self._on_wand_changed)
        lay_wnd.addWidget(self.btn_wand_contig)

        self.btn_wand_merged = QtWidgets.QToolButton()
        self.btn_wand_merged.setText("Todas Camadas")
        self.btn_wand_merged.setCheckable(True)
        self.btn_wand_merged.setChecked(True)
        self.btn_wand_merged.setFixedHeight(24)
        self.btn_wand_merged.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_wand_merged.toggled.connect(self._on_wand_changed)
        lay_wnd.addWidget(self.btn_wand_merged)

        self.cbo_wand_mode = QtWidgets.QComboBox()
        self.cbo_wand_mode.addItems(["Nova Seleção", "Adicionar (+)", "Subtrair (-)", "Interseção"])
        self.cbo_wand_mode.setFixedHeight(24)
        self.cbo_wand_mode.currentIndexChanged.connect(self._on_wand_changed)
        lay_wnd.addWidget(self.cbo_wand_mode)

        self.btn_wand_deselect = QtWidgets.QToolButton()
        self.btn_wand_deselect.setIcon(get_icon("deselect"))
        self.btn_wand_deselect.setText(" Desmarcar")
        self.btn_wand_deselect.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.btn_wand_deselect.setToolTip("Desmarcar / Limpar Seleção (Ctrl+D)")
        self.btn_wand_deselect.setFixedHeight(24)
        self.btn_wand_deselect.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_wand_deselect.clicked.connect(self._on_deselect_clicked)
        lay_wnd.addWidget(self.btn_wand_deselect)

        self.stacked_widget.addWidget(self.panel_wand)

        # ── 4. Painel Seleção Geométrica (Retangular & Elíptica) ───────────
        self.panel_geom_select = QtWidgets.QWidget()
        lay_geom = QtWidgets.QHBoxLayout(self.panel_geom_select)
        lay_geom.setContentsMargins(0, 0, 0, 0)
        lay_geom.setSpacing(6)

        self.lbl_geom_icon = QtWidgets.QLabel()
        self.lbl_geom_icon.setFixedSize(20, 20)
        self.lbl_geom_icon.setPixmap(get_icon("select_rect").pixmap(16, 16))
        lay_geom.addWidget(self.lbl_geom_icon)

        lbl_gfeather = QtWidgets.QLabel("Feather:")
        lbl_gfeather.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        lay_geom.addWidget(lbl_gfeather)

        self.slider_geom_feather = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_geom_feather.setRange(0, 50)
        self.slider_geom_feather.setValue(0)
        self.slider_geom_feather.setFixedWidth(55)
        self.slider_geom_feather.setFixedHeight(18)
        self.lbl_geom_feather_val = QtWidgets.QLabel("0px")
        self.lbl_geom_feather_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_geom_feather.valueChanged.connect(lambda v: self.lbl_geom_feather_val.setText(f"{v}px"))
        self.slider_geom_feather.valueChanged.connect(self._on_geom_select_changed)
        lay_geom.addWidget(self.slider_geom_feather)
        lay_geom.addWidget(self.lbl_geom_feather_val)

        self.btn_geom_aa = QtWidgets.QToolButton()
        self.btn_geom_aa.setText("Anti-Alias")
        self.btn_geom_aa.setCheckable(True)
        self.btn_geom_aa.setChecked(True)
        self.btn_geom_aa.setFixedHeight(24)
        self.btn_geom_aa.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_geom_aa.toggled.connect(self._on_geom_select_changed)
        lay_geom.addWidget(self.btn_geom_aa)

        self.cbo_geom_mode = QtWidgets.QComboBox()
        self.cbo_geom_mode.addItems(["Nova Seleção", "Adicionar (+)", "Subtrair (-)", "Interseção"])
        self.cbo_geom_mode.setFixedHeight(24)
        self.cbo_geom_mode.currentIndexChanged.connect(self._on_geom_select_changed)
        lay_geom.addWidget(self.cbo_geom_mode)

        self.btn_geom_deselect = QtWidgets.QToolButton()
        self.btn_geom_deselect.setIcon(get_icon("deselect"))
        self.btn_geom_deselect.setText(" Desmarcar")
        self.btn_geom_deselect.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.btn_geom_deselect.setToolTip("Desmarcar / Limpar Seleção (Ctrl+D)")
        self.btn_geom_deselect.setFixedHeight(24)
        self.btn_geom_deselect.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_geom_deselect.clicked.connect(self._on_deselect_clicked)
        lay_geom.addWidget(self.btn_geom_deselect)

        self.stacked_widget.addWidget(self.panel_geom_select)

        # ── 5. Painel Laço de Seleção (Livre & Poligonal) ───────────────────
        self.panel_lasso = QtWidgets.QWidget()
        lay_lso = QtWidgets.QHBoxLayout(self.panel_lasso)
        lay_lso.setContentsMargins(0, 0, 0, 0)
        lay_lso.setSpacing(6)

        lbl_lso = QtWidgets.QLabel()
        lbl_lso.setFixedSize(20, 20)
        lbl_lso.setPixmap(get_icon("lasso").pixmap(16, 16))
        lay_lso.addWidget(lbl_lso)

        self.cbo_lasso_type = QtWidgets.QComboBox()
        self.cbo_lasso_type.addItems(["Mão Livre", "Poligonal"])
        self.cbo_lasso_type.setFixedHeight(24)
        self.cbo_lasso_type.currentIndexChanged.connect(self._on_lasso_changed)
        lay_lso.addWidget(self.cbo_lasso_type)

        lbl_lfeather = QtWidgets.QLabel("Feather:")
        lbl_lfeather.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        lay_lso.addWidget(lbl_lfeather)

        self.slider_lasso_feather = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_lasso_feather.setRange(0, 50)
        self.slider_lasso_feather.setValue(0)
        self.slider_lasso_feather.setFixedWidth(55)
        self.slider_lasso_feather.setFixedHeight(18)
        self.lbl_lasso_feather_val = QtWidgets.QLabel("0px")
        self.lbl_lasso_feather_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_lasso_feather.valueChanged.connect(lambda v: self.lbl_lasso_feather_val.setText(f"{v}px"))
        self.slider_lasso_feather.valueChanged.connect(self._on_lasso_changed)
        lay_lso.addWidget(self.slider_lasso_feather)
        lay_lso.addWidget(self.lbl_lasso_feather_val)

        self.btn_lasso_aa = QtWidgets.QToolButton()
        self.btn_lasso_aa.setText("Anti-Alias")
        self.btn_lasso_aa.setCheckable(True)
        self.btn_lasso_aa.setChecked(True)
        self.btn_lasso_aa.setFixedHeight(24)
        self.btn_lasso_aa.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_lasso_aa.toggled.connect(self._on_lasso_changed)
        lay_lso.addWidget(self.btn_lasso_aa)

        self.cbo_lasso_mode = QtWidgets.QComboBox()
        self.cbo_lasso_mode.addItems(["Nova Seleção", "Adicionar (+)", "Subtrair (-)", "Interseção"])
        self.cbo_lasso_mode.setFixedHeight(24)
        self.cbo_lasso_mode.currentIndexChanged.connect(self._on_lasso_changed)
        lay_lso.addWidget(self.cbo_lasso_mode)

        self.btn_lasso_deselect = QtWidgets.QToolButton()
        self.btn_lasso_deselect.setIcon(get_icon("deselect"))
        self.btn_lasso_deselect.setText(" Desmarcar")
        self.btn_lasso_deselect.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.btn_lasso_deselect.setToolTip("Desmarcar / Limpar Seleção (Ctrl+D)")
        self.btn_lasso_deselect.setFixedHeight(24)
        self.btn_lasso_deselect.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_lasso_deselect.clicked.connect(self._on_deselect_clicked)
        lay_lso.addWidget(self.btn_lasso_deselect)

        self.stacked_widget.addWidget(self.panel_lasso)

        # ── 6. Painel Transformação Livre (Transform Tool) ─────────────────
        self.panel_transform = QtWidgets.QWidget()
        lay_tr = QtWidgets.QHBoxLayout(self.panel_transform)
        lay_tr.setContentsMargins(0, 0, 0, 0)
        lay_tr.setSpacing(6)

        self.btn_trans_commit = QtWidgets.QToolButton()
        self.btn_trans_commit.setText("✔ Aplicar")
        self.btn_trans_commit.setToolTip("Confirmar Transformação (Enter)")
        self.btn_trans_commit.setFixedHeight(24)
        self.btn_trans_commit.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_trans_commit.setStyleSheet("background-color: #10b981; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 2px 8px;")
        self.btn_trans_commit.clicked.connect(self._on_transform_commit_clicked)
        lay_tr.addWidget(self.btn_trans_commit)

        self.btn_trans_cancel = QtWidgets.QToolButton()
        self.btn_trans_cancel.setText("✖ Cancelar")
        self.btn_trans_cancel.setToolTip("Cancelar Transformação (Esc)")
        self.btn_trans_cancel.setFixedHeight(24)
        self.btn_trans_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_trans_cancel.clicked.connect(self._on_transform_cancel_clicked)
        lay_tr.addWidget(self.btn_trans_cancel)

        # Separador vertical
        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.VLine)
        sep1.setStyleSheet("color: rgba(255,255,255,0.15);")
        lay_tr.addWidget(sep1)

        self.btn_trans_flip_h = QtWidgets.QToolButton()
        self.btn_trans_flip_h.setText("Espelhar H")
        self.btn_trans_flip_h.setToolTip("Espelhar Horizontalmente")
        self.btn_trans_flip_h.setFixedHeight(24)
        self.btn_trans_flip_h.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_trans_flip_h.clicked.connect(self._on_transform_flip_h_clicked)
        lay_tr.addWidget(self.btn_trans_flip_h)

        self.btn_trans_flip_v = QtWidgets.QToolButton()
        self.btn_trans_flip_v.setText("Espelhar V")
        self.btn_trans_flip_v.setToolTip("Espelhar Verticalmente")
        self.btn_trans_flip_v.setFixedHeight(24)
        self.btn_trans_flip_v.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_trans_flip_v.clicked.connect(self._on_transform_flip_v_clicked)
        lay_tr.addWidget(self.btn_trans_flip_v)

        self.btn_trans_rot_90 = QtWidgets.QToolButton()
        self.btn_trans_rot_90.setText("Girar 90°")
        self.btn_trans_rot_90.setToolTip("Girar 90° no Sentido Horário")
        self.btn_trans_rot_90.setFixedHeight(24)
        self.btn_trans_rot_90.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_trans_rot_90.clicked.connect(self._on_transform_rot_90_clicked)
        lay_tr.addWidget(self.btn_trans_rot_90)

        # Separador vertical
        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.VLine)
        sep2.setStyleSheet("color: rgba(255,255,255,0.15);")
        lay_tr.addWidget(sep2)

        lbl_interp = QtWidgets.QLabel("Interpolação:")
        lbl_interp.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        lay_tr.addWidget(lbl_interp)

        self.cbo_trans_interp = QtWidgets.QComboBox()
        self.cbo_trans_interp.addItems(["Mais Próximo", "Bilinear", "Bicúbica"])
        self.cbo_trans_interp.setCurrentIndex(2) # Bicubic default
        self.cbo_trans_interp.setFixedHeight(24)
        self.cbo_trans_interp.currentIndexChanged.connect(self._on_transform_changed)
        lay_tr.addWidget(self.cbo_trans_interp)

        self.btn_trans_aspect = QtWidgets.QToolButton()
        self.btn_trans_aspect.setText("Travar Proporção")
        self.btn_trans_aspect.setCheckable(True)
        self.btn_trans_aspect.setChecked(False)
        self.btn_trans_aspect.setFixedHeight(24)
        self.btn_trans_aspect.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_trans_aspect.toggled.connect(self._on_transform_changed)
        lay_tr.addWidget(self.btn_trans_aspect)

        self.stacked_widget.addWidget(self.panel_transform)

        # ── 7. Painel Padrão (Placeholder / Vazio para outras) ──────────────
        self.panel_default = QtWidgets.QWidget()
        lay_def = QtWidgets.QHBoxLayout(self.panel_default)
        lay_def.setContentsMargins(0, 0, 0, 0)
        self.lbl_default = QtWidgets.QLabel("Opções da Ferramenta")
        self.lbl_default.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        lay_def.addWidget(self.lbl_default)
        self.stacked_widget.addWidget(self.panel_default)

        self.box_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(self.container)

    def _on_deselect_clicked(self):
        """Desmarca/limpa a seleção ativa ao clicar no botão."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "clear_selection"):
            backend.clear_selection()

        parent = self.parent()
        if parent:
            if hasattr(parent, "canvas_widget"):
                if hasattr(parent.canvas_widget, "_selection_timer"):
                    parent.canvas_widget._selection_timer.stop()
                parent.canvas_widget.update()
            if hasattr(parent, "_on_status_notification"):
                parent._on_status_notification("Seleção cancelada.")

    def _on_bucket_changed(self):
        settings = {
            "tolerance": self.slider_bkt_tol.value(),
            "expand_px": self.slider_bkt_exp.value(),
            "gap_closing_px": 0,
            "contiguous": self.btn_bkt_contig.isChecked(),
            "sample_all": self.btn_bkt_merged.isChecked(),
            "aa": True,
        }
        self._settings_cache["bucket"] = settings
        self.settingsChanged.emit("bucket", settings)

    def _on_wand_changed(self):
        settings = {
            "tolerance": self.slider_wand_tol.value(),
            "expand_px": 0,
            "contiguous": self.btn_wand_contig.isChecked(),
            "sample_all": self.btn_wand_merged.isChecked(),
            "mode": self.cbo_wand_mode.currentIndex(),
            "aa": True,
        }
        self._settings_cache["wand"] = settings
        self.settingsChanged.emit("wand", settings)

    def _on_geom_select_changed(self):
        settings = {
            "feather_px": self.slider_geom_feather.value(),
            "aa": self.btn_geom_aa.isChecked(),
            "mode": self.cbo_geom_mode.currentIndex(),
        }
        self._settings_cache[self._active_tool_id] = settings
        self.settingsChanged.emit(self._active_tool_id, settings)

    def _on_lasso_changed(self):
        settings = {
            "lasso_type": "freehand" if self.cbo_lasso_type.currentIndex() == 0 else "polygonal",
            "feather_px": self.slider_lasso_feather.value(),
            "aa": self.btn_lasso_aa.isChecked(),
            "mode": self.cbo_lasso_mode.currentIndex(),
        }
        self._settings_cache["lasso"] = settings
        self.settingsChanged.emit("lasso", settings)

    def _on_transform_commit_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.commit_transform()

    def _on_transform_cancel_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.cancel_transform()

    def _on_transform_flip_h_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.transform_flip_h()

    def _on_transform_flip_v_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.transform_flip_v()

    def _on_transform_rot_90_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "canvas_widget"):
            parent.canvas_widget.transform_rotate_90()

    def _on_transform_changed(self):
        settings = {
            "interp_mode": self.cbo_trans_interp.currentIndex(),
            "lock_aspect": self.btn_trans_aspect.isChecked(),
        }
        self._settings_cache["transform"] = settings
        self.settingsChanged.emit("transform", settings)

    def set_tool(self, tool_id: str):
        self._active_tool_id = tool_id
        if tool_id == "eyedrop":
            self.stacked_widget.setCurrentWidget(self.panel_eyedrop)
            self.show()
            self.adjustSize()
        elif tool_id == "bucket":
            self.stacked_widget.setCurrentWidget(self.panel_bucket)
            self.show()
            self.adjustSize()
        elif tool_id == "wand":
            self.stacked_widget.setCurrentWidget(self.panel_wand)
            self.show()
            self.adjustSize()
        elif tool_id in ("rect_select", "ellipse_select"):
            icon_name = "select_rect" if tool_id == "rect_select" else "select_ellipse"
            self.lbl_geom_icon.setPixmap(get_icon(icon_name).pixmap(16, 16))
            self.stacked_widget.setCurrentWidget(self.panel_geom_select)
            self.show()
            self.adjustSize()
        elif tool_id == "lasso":
            self.stacked_widget.setCurrentWidget(self.panel_lasso)
            self.show()
            self.adjustSize()
        elif tool_id == "transform":
            self.stacked_widget.setCurrentWidget(self.panel_transform)
            self.show()
            self.adjustSize()
        else:
            self.hide()

    def set_captured_color(self, color: QtGui.QColor):
        self._current_color = color
        hex_str = color.name().upper()
        self.swatch.setStyleSheet(f"background: {hex_str}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);")
        self.lbl_hex.setText(hex_str)

    def _on_eyedrop_changed(self):
        radius_map = {0: 0, 1: 1, 2: 2, 3: 5}
        idx = self.cbo_sample.currentIndex()
        settings = {
            "sample_size": self.cbo_sample.currentText(),
            "sample_radius": radius_map.get(idx, 0),
            "sample_all": self.btn_merged.isChecked(),
            "show_loupe": True,
        }
        self._settings_cache["eyedrop"] = settings
        self.settingsChanged.emit("eyedrop", settings)

    def _apply_theme(self):
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel") or "#1f1f23"
        border = theme.get_color("border") or "#3f3f46"
        text_main = theme.get_color("text_main") or "#ffffff"
        accent = theme.get_color("accent") or "#ff5252"

        self.container.setStyleSheet(f"""
            #SecondaryBarContainer {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QLabel {{
                color: {text_main};
            }}
            QComboBox {{
                background-color: rgba(255,255,255,0.08);
                color: {text_main};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 11px;
            }}
            QToolButton {{
                background-color: rgba(255,255,255,0.08);
                color: {text_main};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
            }}
            QToolButton:checked {{
                background-color: {accent};
                color: #ffffff;
                border: 1px solid {border};
            }}
        """)
