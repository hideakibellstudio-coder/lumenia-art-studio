from PySide6 import QtCore, QtGui
import logging

logger = logging.getLogger(__name__)

class LocalLayer:
    def __init__(self, uid: int, name: str, parent_uid=None, is_group=False, is_filter=False):
        self.uid = uid
        self.id = uid  # Compatibilidade com camada.id
        self.name = name
        self.parent_uid = parent_uid
        self.is_group = is_group
        self.is_filter = is_filter
        
        self.visible = True
        self.locked = False
        self.opacity = 1.0
        self.blend_mode = "Atravessar" if is_group else "Normal"
        self.alpha_locked = False
        self.clipping_mask = False
        self.collapsed = False
        
        # Miniaturas procedurais simples
        self.thumb = QtGui.QPixmap(38, 28)
        
        from ui.core.theme.manager import ThemeManager
        theme = ThemeManager.instance()._themes.get(ThemeManager.instance().current_theme, {})
        colors = theme.get("colors", {})
        
        bg_darker = QtGui.QColor(ThemeManager.instance().resolve_color("BG_DARKER", colors))
        bg_dark = QtGui.QColor(ThemeManager.instance().resolve_color("BG_DARK", colors))
        bg_mid = QtGui.QColor(ThemeManager.instance().resolve_color("BG_MID", colors))
        border = QtGui.QColor(ThemeManager.instance().resolve_color("BORDER", colors))
        accent = QtGui.QColor(ThemeManager.instance().resolve_color("ACCENT", colors))
        accent_muted = QtGui.QColor(ThemeManager.instance().resolve_color("accent_bg", colors))
        bg_light = QtGui.QColor(ThemeManager.instance().resolve_color("BG_LIGHT", colors))
        
        self.thumb.fill(bg_darker if is_group else bg_dark)
        
        painter = QtGui.QPainter(self.thumb)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if is_group:
            painter.setPen(QtGui.QPen(border, 1))
            painter.setBrush(bg_mid)
            painter.drawRoundedRect(4, 4, 30, 20, 2, 2)
        elif is_filter:
            painter.setPen(QtGui.QPen(accent, 1))
            painter.setBrush(accent_muted)
            painter.drawRoundedRect(4, 4, 30, 20, 2, 2)
        else:
            painter.setPen(QtGui.QPen(border, 1))
            painter.setBrush(bg_light)
            painter.drawRoundedRect(4, 4, 30, 20, 1, 1)
        painter.end()

class LocalLayerManager(QtCore.QObject):
    active_layer_changed = QtCore.Signal(int)
    layer_added = QtCore.Signal(object)
    order_about_to_change = QtCore.Signal()
    order_changed = QtCore.Signal()
    layer_property_changed = QtCore.Signal(int)
    thumbnail_updated = QtCore.Signal(int)

    def __init__(self):
        super().__init__()
        self.layers = []
        self._active_uid = None
        self._next_uid = 1

    def get_active_layer(self):
        if self._active_uid is None and self.layers:
            return self.layers[0]
        for l in self.layers:
            if l.uid == self._active_uid:
                return l
        return self.layers[0] if self.layers else None

    def set_active_layer(self, uid):
        if uid != self._active_uid:
            self._active_uid = uid
            self.active_layer_changed.emit(uid)

    def get_layer_by_uid(self, uid):
        for l in self.layers:
            if l.uid == uid:
                return l
        return None

    def add_layer(self, name=None) -> int:
        uid = self._next_uid
        self._next_uid += 1
        
        if not name:
            name = f"Camada {uid}"
            
        layer = LocalLayer(uid, name)
        
        # Insere acima da camada ativa, se houver
        active = self.get_active_layer()
        if active:
            idx = self.layers.index(active) + 1
            if active.is_group:
                layer.parent_uid = active.uid
            else:
                layer.parent_uid = active.parent_uid
            self.layers.insert(idx, layer)
        else:
            self.layers.append(layer)
            
        self.set_active_layer(uid)
        self.layer_added.emit(layer)
        self.order_changed.emit()
        return uid

    def add_group(self, name="Novo Grupo") -> int:
        uid = self._next_uid
        self._next_uid += 1
        
        if not name:
            name = f"Grupo {uid}"
            
        group = LocalLayer(uid, name, is_group=True)
        
        active = self.get_active_layer()
        if active:
            idx = self.layers.index(active) + 1
            if active.is_group:
                group.parent_uid = active.uid
            else:
                group.parent_uid = active.parent_uid
            self.layers.insert(idx, group)
        else:
            self.layers.append(group)
            
        self.set_active_layer(uid)
        self.layer_added.emit(group)
        self.order_changed.emit()
        return uid

    @property
    def active_index(self) -> int:
        active = self.get_active_layer()
        if active and active in self.layers:
            return self.layers.index(active)
        return -1

    def remove_layer(self, target) -> bool:
        if isinstance(target, int) and target < len(self.layers) and target >= 0 and not any(l.uid == target for l in self.layers):
            layer = self.layers[target]
        else:
            layer = self.get_layer_by_uid(target) if isinstance(target, int) else target
        if not layer:
            return False
            
        # Não deleta se for a única restante
        if len(self.layers) <= 1:
            return False
            
        self.order_about_to_change.emit()
        
        idx = self.layers.index(layer)
        uid = layer.uid
        self.layers.remove(layer)
        
        # Remove filhos do grupo
        if layer.is_group:
            children = [l for l in self.layers if l.parent_uid == uid]
            for child in children:
                self.layers.remove(child)
                
        if self._active_uid == uid:
            new_idx = max(0, idx - 1)
            if self.layers:
                self.set_active_layer(self.layers[new_idx].uid)
            else:
                self._active_uid = None
                
        self.order_changed.emit()
        return True

    def duplicate_layer(self, target) -> int:
        if isinstance(target, int) and target < len(self.layers) and target >= 0 and not any(l.uid == target for l in self.layers):
            layer = self.layers[target]
        else:
            layer = self.get_layer_by_uid(target) if isinstance(target, int) else target
        if not layer or layer.is_group:
            return 0
            
        new_uid = self._next_uid
        self._next_uid += 1
        
        new_layer = LocalLayer(new_uid, f"{layer.name} Copiar")
        new_layer.parent_uid = layer.parent_uid
        new_layer.visible = layer.visible
        new_layer.locked = layer.locked
        new_layer.opacity = layer.opacity
        new_layer.blend_mode = layer.blend_mode
        new_layer.alpha_locked = layer.alpha_locked
        new_layer.clipping_mask = layer.clipping_mask
        
        idx = self.layers.index(layer) + 1
        self.layers.insert(idx, new_layer)
        
        self.set_active_layer(new_uid)
        self.layer_added.emit(new_layer)
        return new_uid

    def move_layer_up(self, uid) -> bool:
        layer = self.get_layer_by_uid(uid)
        if not layer:
            return False
            
        idx = self.layers.index(layer)
        if idx >= len(self.layers) - 1:
            return False
            
        self.order_about_to_change.emit()
        self.layers[idx], self.layers[idx + 1] = self.layers[idx + 1], self.layers[idx]
        self.order_changed.emit()
        self.set_active_layer(uid)
        return True

    def move_layer_down(self, uid) -> bool:
        layer = self.get_layer_by_uid(uid)
        if not layer:
            return False
            
        idx = self.layers.index(layer)
        if idx <= 0:
            return False
            
        self.order_about_to_change.emit()
        self.layers[idx], self.layers[idx - 1] = self.layers[idx - 1], self.layers[idx]
        self.order_changed.emit()
        self.set_active_layer(uid)
        return True

    def merge_down(self, target) -> bool:
        if isinstance(target, int) and target < len(self.layers) and target >= 0 and not any(l.uid == target for l in self.layers):
            layer = self.layers[target]
        else:
            layer = self.get_layer_by_uid(target) if isinstance(target, int) else target
        if not layer or layer.is_group:
            return False
            
        idx = self.layers.index(layer)
        if idx <= 0:
            return False
            
        target_layer = self.layers[idx - 1]
        if target_layer.is_group:
            return False
            
        self.order_about_to_change.emit()
        self.layers.remove(layer)
        self.set_active_layer(target_layer.uid)
        self.order_changed.emit()
        return True

    def set_clipping_mask(self, idx: int, enabled: bool) -> None:
        if 0 <= idx < len(self.layers):
            self.layers[idx].clipping_mask = bool(enabled)
            self.layer_property_changed.emit(self.layers[idx].uid)

    def set_alpha_lock(self, idx: int, enabled: bool) -> None:
        if 0 <= idx < len(self.layers):
            self.layers[idx].alpha_locked = bool(enabled)
            self.layer_property_changed.emit(self.layers[idx].uid)

    def set_layer_visibility(self, idx: int, visible: bool) -> None:
        if 0 <= idx < len(self.layers):
            self.layers[idx].visible = bool(visible)
            self.layer_property_changed.emit(self.layers[idx].uid)

    def flatten_group(self, idx: int) -> None:
        if 0 <= idx < len(self.layers) and self.layers[idx].is_group:
            g_uid = self.layers[idx].uid
            self.layers[idx].is_group = False
            children = [l for l in self.layers if l.parent_uid == g_uid]
            for child in children:
                self.layers.remove(child)
            self.order_changed.emit()

    def flatten_image(self) -> None:
        if len(self.layers) > 1:
            base = self.layers[0]
            base.is_group = False
            base.parent_uid = None
            self.layers = [base]
            self.set_active_layer(base.uid)
            self.order_changed.emit()

    def reorder_and_reparent(self, new_order_uids, parent_map):
        self.order_about_to_change.emit()
        
        id_to_layer = {str(l.uid): l for l in self.layers}
        new_list = []
        for uid_str in new_order_uids:
            if uid_str in id_to_layer:
                l = id_to_layer[uid_str]
                p_uid = parent_map.get(uid_str)
                l.parent_uid = int(p_uid) if p_uid is not None else None
                new_list.append(l)
                
        self.layers = new_list
        self.order_changed.emit()
