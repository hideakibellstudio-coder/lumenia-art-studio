import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFrame, QDialog, QLabel,
    QDialogButtonBox, QRadioButton, QButtonGroup, QSlider, QHBoxLayout,
    QGroupBox, QSizePolicy, QApplication)
from PySide6.QtCore import Qt, QModelIndex, QItemSelectionModel, QTimer

from .model import (
    LayerModel, ROLE_UID, ROLE_VISIBLE, ROLE_LOCKED,
    ROLE_OPACITY, ROLE_BLEND, ROLE_IS_GROUP, ROLE_IS_FILTER,
    ROLE_ALPHA_LOCK, ROLE_CLIPPING_MASK, ROLE_COLLAPSED
)
from .delegate import LayerItemDelegate
from .view import LayerTreeView
from .header import LayersHeader
from .grid import LayersPrimaryBox, LayersSecondaryBar
from .paper import PaperLayerWidget
from ui.core.icons import get_icon

logger = logging.getLogger(__name__)

class LayersPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Inicializa o LocalLayerManager
        from .manager import LocalLayerManager
        self.layer_manager = LocalLayerManager()
        self._updating_selection = False
        
        # Layout Principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(240)
        
        # Inner Content Container
        content_inner = QWidget()
        ci_layout = QVBoxLayout(content_inner)
        ci_layout.setContentsMargins(4, 4, 4, 4)
        ci_layout.setSpacing(4)

        # 1. Header (Opacity, Blend)
        self.header = LayersHeader()
        self.header.opacityChanged.connect(self._on_ui_opacity_changed)
        self.header.blendModeChanged.connect(self._on_ui_blend_changed)
        ci_layout.addWidget(self.header)
        
        # Container inferior (HBox)
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)
        
        # Lado Esquerdo do Container Inferior
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 2. Secondary Bar
        self.secondary_bar = LayersSecondaryBar(self)
        left_layout.addWidget(self.secondary_bar)
        
        # 3. View Central
        self.model = LayerModel(self.layer_manager)
        self.view = LayerTreeView()
        self.view.setModel(self.model)
        self.view.setMinimumHeight(150)
        
        self.delegate = LayerItemDelegate()
        self.view.setItemDelegate(self.delegate)
        
        # Conexões da View e Delegate
        self.view.selectionModel().selectionChanged.connect(self._on_view_selection_changed)
        self.delegate.actionRequested.connect(self._on_delegate_action)
        self.model.layoutChanged.connect(self._ensure_top_selection)
        self.model.modelReset.connect(self._on_model_reset)
        
        self.view.deleteRequested.connect(self.delete_selection)
        self.view.moveUpRequested.connect(self.move_up)
        self.view.moveDownRequested.connect(self.move_down)
        self.view.mergeDownRequested.connect(self.merge_down)
        self.view.duplicateRequested.connect(self.duplicate_selection)
        self.view.clearRequested.connect(self.grid_clear)
        self.view.addLayerRequested.connect(self.add_layer)
        self.view.addGroupRequested.connect(self.add_group)
        
        left_layout.addWidget(self.view)
        
        # Paper Layer (Base)
        self.paper_widget = PaperLayerWidget(None)
        left_layout.addWidget(self.paper_widget)
        
        bottom_layout.addWidget(left_widget)
        
        # Divisor Vertical
        self.v_divider = QFrame()
        self.v_divider.setFrameShape(QFrame.VLine)
        self.v_divider.setFrameShadow(QFrame.Plain)
        self.v_divider.setFixedWidth(1)
        bottom_layout.addWidget(self.v_divider)
        
        # Lado Direito (Primary Box)
        right_panel = QWidget()
        right_panel.setFixedWidth(42)
        r_lay_outer = QVBoxLayout(right_panel)
        r_lay_outer.setContentsMargins(4, 6, 4, 8)
        r_lay_outer.setAlignment(Qt.AlignTop)
        
        self.primary_box = LayersPrimaryBox(self)
        self.primary_box.setObjectName("PrimaryBox")
        r_lay_outer.addWidget(self.primary_box)
        r_lay_outer.addStretch()
        
        bottom_layout.addWidget(right_panel)
        ci_layout.addWidget(bottom_widget)

        from ui.core.widgets.card_box import PanelCardBox
        card_box = PanelCardBox("🥞 Camadas", content_inner, self)
        main_layout.addWidget(card_box)

        
        # Conexões de Sincronia com o Motor
        self.layer_manager.active_layer_changed.connect(self._on_engine_active_layer_changed)
        self.layer_manager.layer_property_changed.connect(self._sync_header_controls)
        
        self._sync_header_controls()
        self._ensure_top_selection()
        
        # Sincroniza tema
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme("")

    def set_layer_manager(self, manager):
        if self.layer_manager:
            try:
                self.layer_manager.active_layer_changed.disconnect(self._on_engine_active_layer_changed)
                self.layer_manager.layer_property_changed.disconnect(self._sync_header_controls)
            except Exception as e:
                logger.debug(f"LayersPanel: Disconnection failed: {e}")

        self.layer_manager = manager
        self.model.set_manager(manager)
        
        if manager is None:
            self.view.setEnabled(False)
            self.header.setEnabled(False)
            self.secondary_bar.setEnabled(False)
            self.paper_widget.setEnabled(False)
            self.primary_box.setEnabled(False)
        else:
            self.view.setEnabled(True)
            self.header.setEnabled(True)
            self.secondary_bar.setEnabled(True)
            self.paper_widget.setEnabled(True)
            self.primary_box.setEnabled(True)
            
            # Reconecta sinais de sincronia
            self.layer_manager.active_layer_changed.connect(self._on_engine_active_layer_changed)
            self.layer_manager.layer_property_changed.connect(self._sync_header_controls)
            
            # Sincroniza controles de opacidade e blend mode
            self._sync_header_controls()
            self._ensure_top_selection()

    # --- Ações do Grid ---
    def grid_clear(self): 
        active = self.layer_manager.get_active_layer()
        if not active:
            return
        
        if active.locked:
            self._show_status("A camada está bloqueada e não pode ser limpa.")
            return

        self._sync_to_native_engine("clear_layer")
        self._show_status(f"Conteúdo de '{active.name}' limpo.")

    def duplicate_selection(self):
        layer = self.layer_manager.get_active_layer()
        if layer:
            self._updating_selection = True
            try:
                self._sync_to_native_engine("add")
                new_uid = self.layer_manager.duplicate_layer(layer.uid)
                self._select_uid_in_view(new_uid)
                self._sync_to_native_engine("select")
                self._show_status(f"Camada '{layer.name}' duplicada.")
            finally:
                self._updating_selection = False

    def delete_selection(self):
        layer = self.layer_manager.get_active_layer()
        if layer:
            self._updating_selection = True
            try:
                self._sync_to_native_engine("delete")
                self.layer_manager.remove_layer(layer.uid)
                active = self.layer_manager.get_active_layer()
                if active:
                    self._select_uid_in_view(active.uid)
                    self._sync_to_native_engine("select")
                self._show_status(f"Camada '{layer.name}' removida.")
            finally:
                self._updating_selection = False
    
    def grid_toggle_lock(self):
        layer = self.layer_manager.get_active_layer()
        if layer:
            idx = self.model._find_index_by_uid(layer.uid)
            new_lock = not layer.locked
            self.model.setData(idx, new_lock, ROLE_LOCKED)
            self._sync_to_native_engine("lock", layer.uid, new_lock)

    def grid_toggle_alpha(self):
        layer = self.layer_manager.get_active_layer()
        if layer:
            idx = self.model._find_index_by_uid(layer.uid)
            new_val = not layer.alpha_locked
            self.model.setData(idx, new_val, ROLE_ALPHA_LOCK)
            self._sync_to_native_engine("alpha_lock", layer.uid, new_val)
            self._show_status(f"Alpha Lock em '{layer.name}': {'Ativado' if new_val else 'Desativado'}")

    def grid_toggle_clip(self):
        layer = self.layer_manager.get_active_layer()
        if layer:
            idx = self.model._find_index_by_uid(layer.uid)
            new_val = not layer.clipping_mask
            self.model.setData(idx, new_val, ROLE_CLIPPING_MASK)
            self._sync_to_native_engine("clipping_mask", layer.uid, new_val)
            self._show_status(f"Clipping Mask em '{layer.name}': {'Ativado' if new_val else 'Desativado'}")

    # --- Synchronizer com o Motor C++ ALADYN ENGINE ---
    def _sync_to_native_engine(self, action: str, *args):
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "_facade") or not backend._facade:
            return

        facade = backend._facade
        active_layer = self.layer_manager.get_active_layer()
        layer_list = self.layer_manager.layers

        try:
            c_idx = layer_list.index(active_layer) if active_layer else facade.get_active_layer_index()
        except ValueError:
            c_idx = facade.get_active_layer_index()

        if action == "clear":
            facade.clear_canvas()
        elif action == "clear_layer":
            facade.clear_layer(c_idx)
        elif action == "opacity":
            val = args[0]
            facade.set_layer_opacity(c_idx, float(val))
        elif action == "blend":
            mode_idx = args[0]
            if isinstance(mode_idx, str):
                blend_map = {
                    "Normal": 0, "Multiply": 1, "Multiplicação": 1,
                    "Screen": 2, "Divisão": 2, "Overlay": 3, "Sobreposição": 3,
                    "Darken": 4, "Escurecer": 4, "Lighten": 5, "Clarear": 5,
                    "Erase": 6, "Borracha": 6
                }
                mode_idx = blend_map.get(mode_idx, 0)

            if hasattr(backend, "_native") and hasattr(backend._native, "LayerBlendMode"):
                try:
                    bm_enum = backend._native.LayerBlendMode(int(mode_idx))
                    facade.set_layer_blend_mode(c_idx, bm_enum)
                except Exception as e:
                    logger.debug(f"Layer blend mode set error: {e}")
        elif action == "visibility":
            uid, vis = args[0], args[1]
            target_layer = self.layer_manager.get_layer_by_uid(uid)
            if target_layer and target_layer in layer_list:
                idx = layer_list.index(target_layer)
                facade.set_layer_visibility(idx, bool(vis))
        elif action == "lock":
            uid, locked = args[0], args[1]
            target_layer = self.layer_manager.get_layer_by_uid(uid)
            if target_layer and target_layer in layer_list:
                idx = layer_list.index(target_layer)
                facade.set_layer_lock(idx, bool(locked))
        elif action == "alpha_lock":
            uid, val = args[0], args[1]
            target_layer = self.layer_manager.get_layer_by_uid(uid)
            if target_layer and target_layer in layer_list:
                idx = layer_list.index(target_layer)
                facade.set_layer_alpha_lock(idx, bool(val))
        elif action == "clipping_mask":
            uid, val = args[0], args[1]
            target_layer = self.layer_manager.get_layer_by_uid(uid)
            if target_layer and target_layer in layer_list:
                idx = layer_list.index(target_layer)
                facade.set_layer_clipping_mask(idx, bool(val))
        elif action == "add":
            facade.add_layer()
        elif action == "delete":
            facade.remove_layer(c_idx)
        elif action == "move_up":
            if c_idx < facade.get_drawing_layer_count() - 1:
                facade.reorder_layer(c_idx, c_idx + 1)
        elif action == "move_down":
            if c_idx > 0:
                facade.reorder_layer(c_idx, c_idx - 1)
        elif action == "merge_down":
            idx = args[0]
            facade.merge_layer_down(idx)
        elif action == "select":
            facade.select_layer(c_idx)

        # Repinta o CanvasWidget
        for top_w in QApplication.topLevelWidgets():
            if hasattr(top_w, "workspace") and hasattr(top_w.workspace, "canvas_widget"):
                top_w.workspace.canvas_widget.update()
            elif hasattr(top_w, "canvas_widget"):
                top_w.canvas_widget.update()

    def add_layer(self, name=None):
        self._updating_selection = True
        try:
            self._sync_to_native_engine("add")
            self.layer_manager.add_layer(name)
            active = self.layer_manager.get_active_layer()
            if active:
                self._select_uid_in_view(active.uid)
                self._sync_to_native_engine("select")
        finally:
            self._updating_selection = False

    def add_group(self, name=None):
        self._show_status("Recurso 'Novo Grupo' em desenvolvimento.")

    def add_filter_layer(self, filter_type=None):
        self._show_status("Recurso 'Camada de Filtro' em desenvolvimento.")

    def move_up(self):
        layer = self.layer_manager.get_active_layer()
        if layer:
            self._updating_selection = True
            try:
                self._sync_to_native_engine("move_up")
                if self.layer_manager.move_layer_up(layer.uid):
                    self._select_uid_in_view(layer.uid)
                    self._show_status(f"Camada '{layer.name}' movida para cima.")
            finally:
                self._updating_selection = False

    def move_down(self):
        layer = self.layer_manager.get_active_layer()
        if layer:
            self._updating_selection = True
            try:
                self._sync_to_native_engine("move_down")
                if self.layer_manager.move_layer_down(layer.uid):
                    self._select_uid_in_view(layer.uid)
                    self._show_status(f"Camada '{layer.name}' movida para baixo.")
            finally:
                self._updating_selection = False

    def merge_down(self):
        layer = self.layer_manager.get_active_layer()
        if layer:
            layer_list = self.layer_manager.layers
            if layer in layer_list:
                c_idx = layer_list.index(layer)
                if c_idx > 0:
                    self._updating_selection = True
                    try:
                        self._sync_to_native_engine("merge_down", c_idx)
                        if self.layer_manager.merge_down(layer.uid):
                            active = self.layer_manager.get_active_layer()
                            if active:
                                self._select_uid_in_view(active.uid)
                                self._sync_to_native_engine("select")
                            self._show_status(f"Camada '{layer.name}' fundida para baixo.")
                    finally:
                        self._updating_selection = False

    def _show_status(self, message):
        win = QApplication.activeWindow()
        if win and hasattr(win, 'statusBar'):
            win.statusBar().showMessage(message, 3000)
        else:
            logger.info(f"[Layers] {message}")

    def _on_ui_opacity_changed(self, value):
        layer = self.layer_manager.get_active_layer()
        if layer and not self._updating_selection:
            idx = self.model._find_index_by_uid(layer.uid)
            self.model.setData(idx, value / 100.0, ROLE_OPACITY)
            self._sync_to_native_engine("opacity", value / 100.0)

    def _on_ui_blend_changed(self, blend):
        layer = self.layer_manager.get_active_layer()
        if layer and not self._updating_selection:
            idx = self.model._find_index_by_uid(layer.uid)
            self.model.setData(idx, blend, ROLE_BLEND)
            self._sync_to_native_engine("blend", blend)

    def _on_delegate_action(self, action_type, uid):
        layer = self.layer_manager.get_layer_by_uid(uid)
        if not layer: 
            return

        idx = self.model._find_index_by_uid(uid)
        if not idx.isValid():
            return

        if action_type == "toggle_visibility":
            new_vis = not layer.visible
            self.model.setData(idx, new_vis, ROLE_VISIBLE)
            self._sync_to_native_engine("visibility", uid, new_vis)
        elif action_type == "toggle_lock":
            new_lock = not layer.locked
            self.model.setData(idx, new_lock, ROLE_LOCKED)
            self._sync_to_native_engine("lock", uid, new_lock)
        elif action_type == "toggle_alpha":
            new_val = not layer.alpha_locked
            self.model.setData(idx, new_val, ROLE_ALPHA_LOCK)
            self._sync_to_native_engine("alpha_lock", uid, new_val)
            self._show_status(f"Alpha Lock em '{layer.name}': {'Ativado' if new_val else 'Desativado'}")
        elif action_type == "toggle_clipping_mask":
            new_val = not layer.clipping_mask
            self.model.setData(idx, new_val, ROLE_CLIPPING_MASK)
            self._sync_to_native_engine("clipping_mask", uid, new_val)
            self._show_status(f"Clipping Mask em '{layer.name}': {'Ativado' if new_val else 'Desativado'}")
        elif action_type == "toggle_collapse":
            is_expanded = self.view.isExpanded(idx)
            self.view.setExpanded(idx, not is_expanded)
            self.model.setData(idx, is_expanded, ROLE_COLLAPSED)

    def _on_view_selection_changed(self, selected=None, deselected=None):
        if self._updating_selection or getattr(self.model, '_is_modifying_structure', False): 
            return
        indexes = self.view.selectionModel().selectedIndexes()
        if indexes:
            uid = indexes[0].data(ROLE_UID)
            if uid:
                self.layer_manager.set_active_layer(uid)
                self._sync_to_native_engine("select")

    def _on_engine_active_layer_changed(self, uid):
        self._sync_header_controls()
        self._sync_to_native_engine("select")
        self._select_uid_in_view(uid)

    def _select_uid_in_view(self, uid):
        self._updating_selection = True
        try:
            index = self.model._find_index_by_uid(uid)
            if index.isValid():
                self.view.setCurrentIndex(index)
                self.view.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)
                self.view.scrollTo(index)
        finally:
            self._updating_selection = False

    def _sync_header_controls(self):
        layer = self.layer_manager.get_active_layer()
        if not layer: 
            return
        
        self._updating_selection = True
        try:
            self.header.set_values(int(layer.opacity * 100), layer.blend_mode, layer.is_group)
        finally:
            self._updating_selection = False

    def _ensure_top_selection(self):
        if self._updating_selection or not self.layer_manager: 
            return
        active = self.layer_manager.get_active_layer()
        if active:
            self._select_uid_in_view(active.uid)
            return
        if not self.view.selectionModel().hasSelection():
            index = self.model.index(0, 0)
            if index.isValid():
                self.view.setCurrentIndex(index)
                self.view.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)
                uid = index.data(ROLE_UID)
                self.layer_manager.set_active_layer(uid)

    def _on_model_reset(self):
        if self._updating_selection or not self.layer_manager: 
            return
        active = self.layer_manager.get_active_layer()
        if active:
            self._select_uid_in_view(active.uid)
        else:
            self._ensure_top_selection()

    def _apply_theme(self, _=""):
        from ui.core.theme.manager import ThemeManager
        tm = ThemeManager.instance()
        
        colors = {
            "bg_panel": tm.get_color("bg_panel"),
            "bg_main": tm.get_color("bg_main"),
            "border": tm.get_color("border"),
            "ACCENT": tm.get_color("accent"),
            "text_main": tm.get_color("text_main"),
            "text_sec": tm.get_color("text_sec"),
            "ACCENT_MUTED": tm.get_color("bg_panel")
        }
        
        border = colors.get("border", "#374151")
        
        if hasattr(self, 'v_divider'):
            self.v_divider.setStyleSheet(f"background-color: {border}; border: none;")
        
        if hasattr(self, 'header'):
            self.header.on_theme_changed(colors)
            
        if hasattr(self, 'paper_widget'):
            self.paper_widget.update_theme(colors)
        
        self.delegate.set_colors(colors)
        
        fg_primary = colors.get("text_main", "#f3f4f6")
        self.view.setStyleSheet(f"""
            QTreeView {{
                background-color: transparent;
                border: none;
                outline: 1px dotted {fg_primary};
            }}
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings,
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image: none;
            }}
        """)
        self.view.viewport().update()
        
        icon_color = colors.get("text_main", "#f3f4f6")
        for btn in self.primary_box.buttons + self.secondary_bar.buttons:
            icon_name = btn.property("icon_name")
            if icon_name:
                btn.setIcon(get_icon(icon_name, icon_color))
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        bg_panel = colors.get("bg_panel", "#1f2937")
        self.primary_box.setStyleSheet(f"""
            QWidget#PrimaryBox {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QFrame[class="GridSeparator"] {{
                background-color: {border};
                max-height: 1px;
                border: none;
            }}
        """)


# ─── Diálogos de Filter Layer ─────────────────────────────────────────────────

class FilterLayerDialog(QDialog):
    FILTERS = [
        ("brightness", "🌕  Brilho / Contraste"),
        ("huesat",     "🎨  Matiz / Saturação / Luminosidade"),
        ("pixelate",   "⬛  Pixelizar"),
        ("invert",     "🔄  Inverter Cores"),
        ("sharpen",    "🔍  Nitidez (Sharpen)"),
        ("vignette",   "🌑  Vinheta"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Camada de Filtro")
        self.setMinimumWidth(320)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("<b>Escolha o tipo de efeito:</b>")
        layout.addWidget(title)

        self._btn_group = QButtonGroup(self)
        self._type_keys = []

        for i, (key, label) in enumerate(self.FILTERS):
            rb = QRadioButton(label)
            if i == 0:
                rb.setChecked(True)
            self._btn_group.addButton(rb, i)
            self._type_keys.append(key)
            layout.addWidget(rb)

        layout.addSpacing(8)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def selected_filter_type(self) -> str:
        idx = self._btn_group.checkedId()
        return self._type_keys[idx] if 0 <= idx < len(self._type_keys) else "brightness"


class FilterParamsDialog(QDialog):
    PARAMS = {
        "brightness": [
            ("Brilho",    0, -100, 100, 0,   100.0),
            ("Contraste", 1, -100, 100, 0,   100.0),
        ],
        "huesat": [
            ("Matiz",      0, -180, 180,  0, 1.0),
            ("Saturação",  1, -100, 100,  0, 100.0),
            ("Luminosidade",2, -100, 100, 0, 100.0),
        ],
        "pixelate": [
            ("Tamanho do Bloco", 0, 2, 128, 8, 1.0),
        ],
        "invert": [],
        "sharpen": [
            ("Intensidade", 0, 0, 200, 50, 100.0),
        ],
        "vignette": [
            ("Raio",       0, 0, 100, 70, 100.0),
            ("Suavidade",  1, 0, 100, 50, 100.0),
            ("Intensidade",2, 0, 100, 80, 100.0),
        ],
    }

    LABELS = {
        "brightness": "Brilho / Contraste",
        "huesat":     "Matiz / Saturação",
        "pixelate":   "Pixelizar",
        "invert":     "Inverter Cores",
        "sharpen":    "Nitidez",
        "vignette":   "Vinheta",
    }

    def __init__(self, parent, layer_id: int, filter_type: str):
        super().__init__(parent)
        self.layer_id = layer_id
        self.filter_type = filter_type
        self._params = [0.0] * 8

        label = self.LABELS.get(filter_type, "Filtro")
        self.setWindowTitle(f"🎛️  {label}")
        self.setMinimumWidth(340)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        param_defs = self.PARAMS.get(filter_type, [])

        if not param_defs:
            layout.addWidget(QLabel("Este filtro não tem parâmetros adicionais.\n"
                                    "Use o slider de Opacidade da camada para controlar a intensidade."))
        else:
            group = QGroupBox("Parâmetros")
            glayout = QVBoxLayout(group)
            glayout.setSpacing(6)

            for (lbl, slot, mn, mx, dflt, scale) in param_defs:
                row = QHBoxLayout()
                row.addWidget(QLabel(lbl))

                slider = QSlider(Qt.Horizontal)
                slider.setRange(mn, mx)
                slider.setValue(dflt)
                slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

                val_lbl = QLabel(str(dflt))
                val_lbl.setFixedWidth(40)
                val_lbl.setAlignment(Qt.AlignRight | Qt.AlignBottom)

                row.addWidget(slider)
                row.addWidget(val_lbl)
                glayout.addLayout(row)

                def make_handler(s, sl, vl, sc):
                    def on_change(v):
                        real_val = v / sc
                        self._params[s] = real_val
                        vl.setText(f"{v:+d}" if sc == 1.0 else f"{real_val:+.2f}")
                        # Envia notificação na barra de status
                        win = QApplication.activeWindow()
                        if win and hasattr(win, 'statusBar'):
                            win.statusBar().showMessage(f"Filtro: Parâmetro {s} ajustado para {real_val} (simulado).", 1000)
                    sl.valueChanged.connect(on_change)
                    self._params[s] = dflt / sc
                make_handler(slot, slider, val_lbl, scale)

            layout.addWidget(group)

        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)
