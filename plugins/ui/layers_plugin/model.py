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

class LayerModel(QAbstractItemModel):
    def __init__(self, layer_manager):
        super().__init__()
        self.manager = None
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

    def row_to_child(self, parent_uid: Optional[int], row: int, layers_list: List = None) -> Optional[Any]:
        if layers_list is None:
            children = self._child_cache[parent_uid]
            if 0 <= row < len(children):
                return children[row]
            return None
        else:
            children = [l for l in layers_list if l.parent_uid == parent_uid]
            inverted_index = len(children) - 1 - row
            if 0 <= inverted_index < len(children):
                return children[inverted_index]
            return None

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
            return getattr(layer, 'thumb', None)
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
        
        if role == Qt.EditRole:
            # Renomeação é uma operação de domínio e deve passar pelo
            # LayersPanel/open_rename_popup, que abre uma transação conjunta
            # com o motor. O modelo não pode alterar a fonte de verdade
            # diretamente via edição Qt.
            return False
        elif role == ROLE_VISIBLE:
            layer.visible = value
        elif role == ROLE_LOCKED:
            layer.locked = value
        elif role == ROLE_OPACITY:
            layer.opacity = value
        elif role == ROLE_BLEND:
            layer.blend_mode = value
        elif role == ROLE_ALPHA_LOCK:
            layer.alpha_locked = value
        elif role == ROLE_CLIPPING_MASK:
            layer.clipping_mask = value
        elif role == ROLE_COLLAPSED:
            layer.collapsed = value
        else:
            return False

        self.dataChanged.emit(index, index, [role])
        if role in (ROLE_VISIBLE, ROLE_OPACITY, ROLE_LOCKED) and getattr(layer, 'is_group', False):
            self._notify_descendants_changed(index)
        self.manager.layer_property_changed.emit(layer.uid)
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
        
        layer = index.internalPointer()
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
        
        if parent_uid in uids:
            return False

        forced_insert_idx = None
        if parent_uid is not None:
            parent_layer = self.manager.get_layer_by_uid(parent_uid)
            if parent_layer and not parent_layer.is_group:
                all_layers_temp = [l for l in self.manager.layers if l.uid not in uids]
                if parent_layer in all_layers_temp:
                    forced_insert_idx = all_layers_temp.index(parent_layer) + 1
                parent_uid = parent_layer.parent_uid

        all_layers = [l for l in self.manager.layers if l.uid not in uids]
        
        if forced_insert_idx is not None:
            insert_idx = forced_insert_idx
        else:
            children_before_drop = [l for l in all_layers if l.parent_uid == parent_uid]
            if row == -1 or row >= len(children_before_drop):
                if parent_uid is None:
                    insert_idx = 0
                else:
                    parent_layer = self.manager.get_layer_by_uid(parent_uid)
                    insert_idx = all_layers.index(parent_layer) + 1
            else:
                target_sibling = self.row_to_child(parent_uid, row, all_layers)
                if target_sibling:
                    insert_idx = all_layers.index(target_sibling) + 1
                else:
                    insert_idx = 0

        moved_layers = []
        for uid in uids:
            l = self.manager.get_layer_by_uid(uid)
            if l:
                moved_layers.append(l)
        
        new_layers_list = all_layers[:insert_idx] + moved_layers + all_layers[insert_idx:]
        
        new_order_uids = [str(l.uid) for l in new_layers_list]
        parent_map = {}
        for l in new_layers_list:
            if l in moved_layers:
                parent_map[str(l.uid)] = str(parent_uid) if parent_uid is not None else None
            else:
                parent_map[str(l.uid)] = str(l.parent_uid) if l.parent_uid is not None else None
        
        self.manager.reorder_and_reparent(new_order_uids, parent_map)
        return True

    def _on_layer_added(self, layer):
        self._is_modifying_structure = True
        try:
            parent_uid = layer.parent_uid
            if parent_uid is None:
                self.beginInsertRows(QModelIndex(), 0, 0)
                self._rebuild_structure_cache()
                self.endInsertRows()
            else:
                parent_index = self._find_index_by_uid(parent_uid)
                if parent_index.isValid():
                    self.beginInsertRows(parent_index, 0, 0)
                    self._rebuild_structure_cache()
                    self.endInsertRows()
                else:
                    self._rebuild_structure_cache()
                    self.layoutChanged.emit()
        finally:
            self._is_modifying_structure = False

    def _find_index_by_uid(self, uid):
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
        self.beginResetModel()

    def _on_order_changed(self):
        self._rebuild_structure_cache()
        self.endResetModel()

    def _on_property_changed(self, uid):
        idx = self._find_index_by_uid(uid)
        if idx.isValid():
            self.dataChanged.emit(idx, idx)
        else:
            self._rebuild_structure_cache()
            self.layoutChanged.emit()
