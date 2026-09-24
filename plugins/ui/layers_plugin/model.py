from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, Signal
import logging
from collections import defaultdict
from typing import List, Optional, Any

logger = logging.getLogger(__name__)

# Roles customizados
ROLE_UID        = Qt.UserRole + 1
ROLE_ID         = Qt.UserRole + 2
ROLE_IS_GROUP   = Qt.UserRole + 3
ROLE_VISIBLE    = Qt.UserRole + 4
ROLE_LOCKED     = Qt.UserRole + 5
ROLE_OPACITY    = Qt.UserRole + 6
ROLE_BLEND      = Qt.UserRole + 7
ROLE_ALPHA_LOCK = Qt.UserRole + 8
ROLE_CLIPPING_MASK = Qt.UserRole + 9
ROLE_CHILD_COUNT = Qt.UserRole + 10
ROLE_EFFECTIVE_VISIBLE = Qt.UserRole + 11
ROLE_EFFECTIVE_OPACITY = Qt.UserRole + 12
ROLE_COLLAPSED = Qt.UserRole + 13
ROLE_IS_FILTER  = Qt.UserRole + 14

from ui.core.document.history import layer_transaction
from ui.core.document.local_layer import LocalLayer

from .drop_plan import plan_layer_drop


class LayerModel(QAbstractItemModel):
    # Falha de uma transação da árvore (arrastar e soltar); o painel repassa.
    statusMessage = Signal(str)

    def __init__(self, layer_manager):
        super().__init__()
        self.manager = None
        self._resetting = False
        self._is_modifying_structure = False
        self._child_cache = defaultdict(list)
        self._row_cache = {}
        self._parent_uid_cache = {}
        
        if layer_manager:
            self.set_manager(layer_manager)

    def set_manager(self, new_manager):
        if self.manager:
            try:
                self.manager.layer_added.disconnect(self._on_layer_added)
                self.manager.order_about_to_change.disconnect(self._on_order_about_to_change)
                self.manager.order_changed.disconnect(self._on_order_changed)
                self.manager.layer_property_changed.disconnect(self._on_property_changed)
                self.manager.thumbnail_updated.disconnect(self._on_property_changed)
            except Exception as e:
                logger.debug(f"LayerModel: Disconnection failed: {e}")

        self.manager = new_manager

        self.beginResetModel()
        if self.manager:
            self.manager.layer_added.connect(self._on_layer_added)
            self.manager.order_about_to_change.connect(self._on_order_about_to_change)
            self.manager.order_changed.connect(self._on_order_changed)
            self.manager.layer_property_changed.connect(self._on_property_changed)
            self.manager.thumbnail_updated.connect(self._on_property_changed)
            self._rebuild_structure_cache()
        else:
            self._child_cache = defaultdict(list)
            self._row_cache = {}
            self._parent_uid_cache = {}
        self.endResetModel()

    def _rebuild_structure_cache(self):
        self._child_cache = defaultdict(list)
        self._row_cache = {}
        self._parent_uid_cache = {}
        
        for l in self.manager.layers:
            self._child_cache[l.parent_uid].append(l)
            self._parent_uid_cache[l.uid] = l.parent_uid
            
        for parent_uid, children in self._child_cache.items():
            children.reverse()
            for row, l in enumerate(children):
                self._row_cache[l.uid] = row

    @property
    def is_modifying_structure(self) -> bool:
        """True enquanto linhas são inseridas (a view não deve tratar a seleção como do usuário)."""
        return self._is_modifying_structure

    def row_to_child(self, parent_uid: Optional[int], row: int) -> Optional[Any]:
        children = self._child_cache[parent_uid]
        return children[row] if 0 <= row < len(children) else None

    def child_to_row(self, child_uid: int) -> Optional[int]:
        return self._row_cache.get(child_uid)

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return len(self._child_cache[None])
        parent_uid = self.data(parent, ROLE_UID)
        return len(self._child_cache[parent_uid])

    def columnCount(self, parent=QModelIndex()):
        return 1

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_uid = self.data(parent, ROLE_UID) if parent.isValid() else None
        child = self.row_to_child(parent_uid, row)
        if child:
            return self.createIndex(row, column, child)
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        child_layer = index.internalPointer()
        if not child_layer or child_layer.parent_uid is None:
            return QModelIndex()

        parent_layer = self.manager.get_layer_by_uid(child_layer.parent_uid)
        if not parent_layer:
            return QModelIndex()

        row = self.child_to_row(parent_layer.uid)
        if row is None:
            row = 0
        return self.createIndex(row, 0, parent_layer)

    def get_effective_visible(self, layer) -> bool:
        curr = layer
        while curr:
            if not getattr(curr, 'visible', True):
                return False
            curr = self.manager.get_layer_by_uid(curr.parent_uid) if curr.parent_uid else None
        return True

    def get_effective_opacity(self, layer) -> float:
        op = 1.0
        curr = layer
        while curr:
            op *= getattr(curr, 'opacity', 1.0)
            curr = self.manager.get_layer_by_uid(curr.parent_uid) if curr.parent_uid else None
        return op

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        layer = index.internalPointer()
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return layer.name
        elif role == Qt.DecorationRole:
            return layer.thumb
        elif role == ROLE_UID:
            return layer.uid
        elif role == ROLE_ID:
            return layer.id
        elif role == ROLE_IS_GROUP:
            return layer.is_group
        elif role == ROLE_VISIBLE:
            return layer.visible
        elif role == ROLE_LOCKED:
            return layer.locked
        elif role == ROLE_OPACITY:
            return layer.opacity
        elif role == ROLE_BLEND:
            return layer.blend_mode
        elif role == ROLE_ALPHA_LOCK:
            return layer.alpha_locked
        elif role == ROLE_CLIPPING_MASK:
            return layer.clipping_mask
        elif role == ROLE_COLLAPSED:
            return layer.collapsed
        elif role == ROLE_IS_FILTER:
            return getattr(layer, 'is_filter', False)
        elif role == ROLE_CHILD_COUNT:
            if layer.is_group:
                return len([l for l in self.manager.layers if l.parent_uid == layer.uid])
            return 0
        elif role == ROLE_EFFECTIVE_VISIBLE:
            return self.get_effective_visible(layer)
        elif role == ROLE_EFFECTIVE_OPACITY:
            return self.get_effective_opacity(layer)
        
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False

        layer = index.internalPointer()

        if role == ROLE_COLLAPSED:
            # Estado de exibição da árvore: não vai ao motor.
            layer.collapsed = bool(value)
            self.dataChanged.emit(index, index, [role])
            return True

        # Propriedades do documento passam pelo LocalLayerManager (fonte única):
        # ele sincroniza o motor, marca o documento como modificado e emite
        # layer_property_changed, que volta aqui como dataChanged. Até
        # 2026-09-24 este método escrevia direto nos campos da camada e o
        # painel sincronizava o motor por um segundo caminho.
        # Renomear (Qt.EditRole) também é domínio: passa pelo painel.
        setters = {
            ROLE_VISIBLE: self.manager.set_layer_visibility,
            ROLE_LOCKED: self.manager.set_layer_lock,
            ROLE_OPACITY: self.manager.set_layer_opacity,
            ROLE_BLEND: self.manager.set_layer_blend_mode,
            ROLE_ALPHA_LOCK: self.manager.set_alpha_lock,
            ROLE_CLIPPING_MASK: self.manager.set_clipping_mask,
        }
        setter = setters.get(role)
        if setter is None:
            return False
        setter(self.manager.layers.index(layer), value)
        return True

    def _notify_descendants_changed(self, parent_index):
        if not parent_index.isValid():
            return
        row_count = self.rowCount(parent_index)
        for r in range(row_count):
            child_idx = self.index(r, 0, parent_index)
            if child_idx.isValid():
                self.dataChanged.emit(child_idx, child_idx, [ROLE_VISIBLE, ROLE_OPACITY, ROLE_EFFECTIVE_VISIBLE, ROLE_EFFECTIVE_OPACITY])
                self._notify_descendants_changed(child_idx)

    def flags(self, index):
        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
        if not index.isValid():
            return Qt.ItemIsDropEnabled
        
        layer: LocalLayer = index.internalPointer()
        if layer.is_group:
            return base_flags | Qt.ItemIsDropEnabled
        return base_flags

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return ['application/x-lumenia-layer-uid']

    def mimeData(self, indexes):
        from PySide6.QtCore import QMimeData
        mime_data = QMimeData()
        uids = [str(self.data(idx, ROLE_UID)) for idx in indexes if idx.column() == 0]
        mime_data.setData('application/x-lumenia-layer-uid', ",".join(uids).encode())
        return mime_data

    @layer_transaction
    def dropMimeData(self, data, action, row, column, parent):
        if action == Qt.IgnoreAction:
            return True
        if not data.hasFormat('application/x-lumenia-layer-uid'):
            return False
        uids = [int(x) for x in data.data('application/x-lumenia-layer-uid').data().decode().split(",") if x]
        parent_uid = self.data(parent, ROLE_UID) if parent.isValid() else None
        plan = plan_layer_drop(self.manager, uids, parent_uid, row)
        if plan is None:
            return False
        self.manager.reorder_and_reparent(*plan)
        return True

    # ── Contrato de `layer_transaction` (dropMimeData é uma transação) ──

    @property
    def layer_manager(self):
        return self.manager

    def show_status(self, message: str) -> None:
        self.statusMessage.emit(message)

    def _on_layer_added(self, layer):
        self._is_modifying_structure = True
        try:
            parent_uid = layer.parent_uid
            if parent_uid is None:
                self.beginInsertRows(QModelIndex(), 0, 0)
                self._rebuild_structure_cache()
                self.endInsertRows()
            else:
                parent_index = self.find_index_by_uid(parent_uid)
                if parent_index.isValid():
                    self.beginInsertRows(parent_index, 0, 0)
                    self._rebuild_structure_cache()
                    self.endInsertRows()
                else:
                    self._rebuild_structure_cache()
                    self.layoutChanged.emit()
        finally:
            self._is_modifying_structure = False

    def find_index_by_uid(self, uid):
        if uid is None:
            return QModelIndex()
        
        target_uid = int(uid)
        if self.child_to_row(target_uid) is None:
            return QModelIndex()
            
        ancestors = []
        curr_uid = target_uid
        while True:
            parent_uid = self._parent_uid_cache.get(curr_uid)
            if parent_uid is None:
                break
            parent_layer = self.manager.get_layer_by_uid(parent_uid)
            if not parent_layer:
                break
            ancestors.append(parent_layer)
            curr_uid = parent_uid
            
        ancestors.reverse()
        
        parent_idx = QModelIndex()
        for parent_layer in ancestors:
            row = self.child_to_row(parent_layer.uid)
            if row is None:
                return QModelIndex()
            parent_idx = self.index(row, 0, parent_idx)
            
        row = self.child_to_row(target_uid)
        if row is None:
            return QModelIndex()
        return self.index(row, 0, parent_idx)

    def _on_order_about_to_change(self):
        self._resetting = True
        self.beginResetModel()

    def _on_order_changed(self):
        self._rebuild_structure_cache()
        if self._resetting:
            self._resetting = False
            self.endResetModel()
        else:
            # add_layer/add_group avisam order_changed sem order_about_to_change
            # (as linhas já entraram por layer_added): só a disposição mudou.
            self.layoutChanged.emit()

    def _on_property_changed(self, uid):
        idx = self.find_index_by_uid(uid)
        if idx.isValid():
            self.dataChanged.emit(idx, idx)
            layer = idx.internalPointer()
            if layer is not None and layer.is_group:
                # Visibilidade/opacidade efetivas dos filhos dependem do grupo.
                self._notify_descendants_changed(idx)
        else:
            self._rebuild_structure_cache()
            self.layoutChanged.emit()
