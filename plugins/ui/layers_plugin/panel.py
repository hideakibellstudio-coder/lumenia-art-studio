"""
LayersPanel — Painel de Controle de Camadas do Lumenia (Decomposto conforme ARCcC)
===================================================================================
Gerencia a lista hierárquica de camadas, visualização em árvore, opacidade e blend mode.
Decomposto nos submódulos atômicos:
  - panel_rename_popup.py (Popup flutuante de renomeação)
  - panel_filter_dialogs.py (Diálogos auxiliares de filtros)
  - panel_sync.py (Sincronizador C++ nativo)
"""

from __future__ import annotations

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QModelIndex, QItemSelectionModel, QRect

from .model import (
    LayerModel, ROLE_UID, ROLE_OPACITY, ROLE_BLEND,
    ROLE_VISIBLE, ROLE_LOCKED, ROLE_ALPHA_LOCK, ROLE_CLIPPING_MASK, ROLE_COLLAPSED
)
from .delegate import LayerItemDelegate
from .view import LayerTreeView
from .header import LayersHeader
from .grid import LayersPrimaryBox, LayersSecondaryBar
from .paper import PaperLayerWidget
from ui.core.icons import get_icon

from .panel_rename_popup import LayerRenamePopup
from .panel_filter_dialogs import FilterLayerDialog, FilterParamsDialog
from .panel_sync import sync_to_native_engine, refresh_layer_thumbnail

logger = logging.getLogger(__name__)


from ui.core.document.history import layer_transaction

class LayersPanel(QWidget):
    """Widget principal do Painel de Camadas."""

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
        self.view.toggleClippingRequested.connect(self._on_context_toggle_clipping)
        self.view.editFilterRequested.connect(self.open_edit_filter_popup)
        self.view.renameRequested.connect(self.open_rename_popup)
        
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
        card_box = PanelCardBox("", content_inner, self)
        main_layout.addWidget(card_box)

        # Conexões de Sincronia com o Motor
        self.layer_manager.active_layer_changed.connect(self._on_engine_active_layer_changed)
        self.layer_manager.layer_property_changed.connect(self._sync_header_controls)
        self.layer_manager.order_changed.connect(self._on_order_changed)
        self.layer_manager.layer_added.connect(self._on_layer_added)
        self.layer_manager.thumbnail_updated.connect(self._on_thumbnail_updated)
        
        self._sync_header_controls()
        self._ensure_top_selection()
        
        # Sincroniza tema
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme("")

    def _on_order_changed(self):
        if self.layer_manager.backend_projection_restoring:
            self._synced_uids = [layer.uid for layer in self.layer_manager.layers]
            return
        if not self._updating_selection:
            self._sync_to_native_engine("reorder_all")

    def _on_layer_added(self, layer):
        pass

    def set_layer_manager(self, manager):
        if self.layer_manager:
            try:
                self.layer_manager.active_layer_changed.disconnect(self._on_engine_active_layer_changed)
                self.layer_manager.layer_property_changed.disconnect(self._sync_header_controls)
                self.layer_manager.order_changed.disconnect(self._on_order_changed)
                self.layer_manager.layer_added.disconnect(self._on_layer_added)
                self.layer_manager.thumbnail_updated.disconnect(self._on_thumbnail_updated)
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
            
            self.layer_manager.active_layer_changed.connect(self._on_engine_active_layer_changed)
            self.layer_manager.layer_property_changed.connect(self._sync_header_controls)
            self.layer_manager.order_changed.connect(self._on_order_changed)
            self.layer_manager.layer_added.connect(self._on_layer_added)
            self.layer_manager.thumbnail_updated.connect(self._on_thumbnail_updated)
            
            self._sync_header_controls()
            self._ensure_top_selection()

    # --- Ações do Grid ---
    @layer_transaction
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
        self.duplicate_layer()

    @layer_transaction
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
    
    @layer_transaction
    def grid_toggle_lock(self):
        layer = self.layer_manager.get_active_layer()
        if layer:
            idx = self.model._find_index_by_uid(layer.uid)
            new_lock = not layer.locked
            self.model.setData(idx, new_lock, ROLE_LOCKED)
            self._sync_to_native_engine("lock", layer.uid, new_lock)

    @layer_transaction
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
            self._on_context_toggle_clipping(layer.uid)

    @layer_transaction
    def _on_context_toggle_clipping(self, uid: int):
        layer = self.layer_manager.get_layer_by_uid(uid)
        if layer:
            idx = self.model._find_index_by_uid(layer.uid)
            new_val = not layer.clipping_mask
            self.model.setData(idx, new_val, ROLE_CLIPPING_MASK)
            self._sync_to_native_engine("clipping_mask", layer.uid, new_val)
            self._show_status(f"Clipping Mask em '{layer.name}': {'Ativado' if new_val else 'Desativado'}")

    def _sync_to_native_engine(self, action: str, *args):
        sync_to_native_engine(self, action, *args)

    @layer_transaction
    def add_layer(self, name=None):
        self._updating_selection = True
        try:
            layer_name = name if name else f"Camada {len(self.layer_manager.layers) + 1}"
            self._sync_to_native_engine("add", layer_name)
            self.layer_manager.add_layer(layer_name)
            self._synced_uids = [l.uid for l in self.layer_manager.layers]
            active = self.layer_manager.get_active_layer()
            if active:
                self._select_uid_in_view(active.uid)
        finally:
            self._updating_selection = False

    @layer_transaction
    def add_group(self, name=None):
        self._updating_selection = True
        try:
            group_name = name if name else "Novo Grupo"
            self._sync_to_native_engine("add_group", group_name)
            self.layer_manager.add_group(group_name)
            self._synced_uids = [l.uid for l in self.layer_manager.layers]
            active = self.layer_manager.get_active_layer()
            if active:
                self._select_uid_in_view(active.uid)
            self._show_status(f"Grupo '{group_name}' criado com sucesso.")
        finally:
            self._updating_selection = False

    @layer_transaction
    def add_filter_layer(self, filter_type=None):
        from .panel_actions import add_filter_layer
        add_filter_layer(self, filter_type)

    @layer_transaction
    def open_edit_filter_popup(self, uid: int = None):
        from .panel_actions import open_edit_filter_popup
        open_edit_filter_popup(self, uid)

    def open_rename_popup(self, uid: int, rect: QRect):
        from .panel_actions import open_rename_popup
        open_rename_popup(self, uid, rect)

    @layer_transaction
    def move_up(self):
        from .panel_actions import move_layer_up
        move_layer_up(self)

    @layer_transaction
    def move_down(self):
        from .panel_actions import move_layer_down
        move_layer_down(self)

    @layer_transaction
    def merge_down(self):
        from .panel_actions import merge_layer_down
        merge_layer_down(self)

    @layer_transaction
    def duplicate_layer(self):
        from .panel_actions import duplicate_layer
        duplicate_layer(self)

    def _show_status(self, message):
        win = QApplication.activeWindow()
        if win and hasattr(win, 'statusBar'):
            win.statusBar().showMessage(message, 3000)
        else:
            logger.info(f"[Layers] {message}")

    @layer_transaction
    def _on_ui_opacity_changed(self, value):
        layer = self.layer_manager.get_active_layer()
        if layer and not self._updating_selection:
            idx = self.model._find_index_by_uid(layer.uid)
            self.model.setData(idx, value / 100.0, ROLE_OPACITY)
            self._sync_to_native_engine("opacity", value / 100.0)

    @layer_transaction
    def _on_ui_blend_changed(self, blend):
        layer = self.layer_manager.get_active_layer()
        if layer and not self._updating_selection:
            idx = self.model._find_index_by_uid(layer.uid)
            self.model.setData(idx, blend, ROLE_BLEND)
            self._sync_to_native_engine("blend", blend)

    @layer_transaction
    def _on_delegate_action(self, action_type, uid):
        from .panel_actions import handle_delegate_action
        handle_delegate_action(self, action_type, uid)

    def _on_view_selection_changed(self, selected=None, deselected=None):
        if self._updating_selection or getattr(self.model, '_is_modifying_structure', False): 
            return
        indexes = self.view.selectionModel().selectedIndexes()
        if indexes:
            uid = indexes[0].data(ROLE_UID)
            if uid:
                self._updating_selection = True
                try:
                    self.layer_manager.set_active_layer(uid)
                    self._sync_header_controls()
                    self._sync_to_native_engine("select")
                finally:
                    self._updating_selection = False

    def _on_engine_active_layer_changed(self, uid):
        self._sync_header_controls()
        self._sync_to_native_engine("select")
        if not self._updating_selection:
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

    def _on_thumbnail_updated(self, uid: int):
        """Fetch real pixel thumbnail from C++ backend and refresh the layer item."""
        refresh_layer_thumbnail(self, uid)

    def _apply_theme(self, _=""):
        from .panel_theme import apply_layers_panel_theme
        apply_layers_panel_theme(self)

