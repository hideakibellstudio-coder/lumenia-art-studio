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
    content_changed = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.layers = []
        self._active_uid = None
        self._next_uid = 1
        self._history_guard = False
        self.backend_projection_restoring = False

    def _snapshot(self):
        return {
            "layers": [{k: getattr(layer, k) for k in (
                "uid", "name", "parent_uid", "is_group", "is_filter", "visible",
                "locked", "opacity", "blend_mode", "alpha_locked", "clipping_mask", "collapsed"
            )} for layer in self.layers],
            "active_uid": self._active_uid,
            "next_uid": self._next_uid,
        }

    def _restore_snapshot(self, snapshot) -> None:
        self._history_guard = True
        try:
            self.replace_layers(snapshot["layers"])
            for layer, record in zip(self.layers, snapshot["layers"]):
                layer.collapsed = bool(record.get("collapsed", False))
            self._next_uid = max(self._next_uid, int(snapshot["next_uid"]))
            self.set_active_layer(snapshot["active_uid"])
            self._last_structural_snapshot = snapshot
        finally:
            self._history_guard = False

    def get_active_layer(self):
        if self._active_uid is None and self.layers:
            return self.layers[0]
        for l in self.layers:
            if l.uid == self._active_uid:
                return l
        return self.layers[0] if self.layers else None

    def set_active_layer(self, uid):
        if uid is not None and self.get_layer_by_uid(uid) is None:
            raise ValueError("camada ativa inexistente")
        if uid != self._active_uid:
            self._active_uid = uid
            self.active_layer_changed.emit(uid)

    def get_layer_by_uid(self, uid):
        if type(uid) is not int or uid <= 0:
            return None
        for l in self.layers:
            if l.uid == uid:
                return l
        return None

    def get_layer_at_index(self, index: int):
        """Retorna uma camada por posição, sem misturar posição e identidade."""
        if not isinstance(index, int) or index < 0 or index >= len(self.layers):
            return None
        return self.layers[index]

    def _resolve_uid(self, target):
        """Resolve somente por UID ou objeto; índices usam get_layer_at_index."""
        if isinstance(target, LocalLayer):
            return target if target in self.layers else None
        return self.get_layer_by_uid(target) if type(target) is int else None

    def validate_integrity(self) -> None:
        """Validate stable IDs and the parent graph before native projection."""
        uids = [layer.uid for layer in self.layers]
        if any(type(uid) is not int or uid <= 0 for uid in uids) or len(uids) != len(set(uids)):
            raise ValueError("UIDs de camadas devem ser inteiros positivos e únicos")
        nodes = {layer.uid: layer for layer in self.layers}
        for layer in self.layers:
            seen = {layer.uid}
            parent = layer.parent_uid
            while parent is not None:
                if type(parent) is not int or parent in seen or parent not in nodes or not nodes[parent].is_group:
                    raise ValueError("hierarquia de camadas inválida")
                seen.add(parent)
                parent = nodes[parent].parent_uid
        if self._active_uid is not None and self._active_uid not in nodes:
            raise ValueError("camada ativa inexistente")

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
        self.content_changed.emit("add_layer")
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
        self.content_changed.emit("add_group")
        return uid

    @property
    def active_index(self) -> int:
        active = self.get_active_layer()
        if active and active in self.layers:
            return self.layers.index(active)
        return -1

    def remove_layer(self, target) -> bool:
        layer = self._resolve_uid(target)
        if not layer:
            return False
            
        # Não deleta se for a única restante
        if len(self.layers) <= 1:
            return False
            
        removed = {layer.uid}
        while True:
            descendants = {item.uid for item in self.layers if item.parent_uid in removed}
            if descendants <= removed:
                break
            removed |= descendants
        if len(removed) == len(self.layers):
            return False
        self.order_about_to_change.emit()
        idx = self.layers.index(layer)
        self.layers = [item for item in self.layers if item.uid not in removed]
        if self._active_uid in removed:
            self.set_active_layer(self.layers[min(idx, len(self.layers) - 1)].uid)

        self.order_changed.emit()
        self._validate_clipping_masks()
        self.content_changed.emit("remove_layer")
        return True

    def duplicate_layer(self, target) -> int:
        layer = self._resolve_uid(target)
        if not layer or layer.is_group:
            return 0
            
        new_uid = self._next_uid
        self._next_uid += 1
        
        new_layer = LocalLayer(new_uid, f"{layer.name} Copiar", is_filter=layer.is_filter)
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
        self.content_changed.emit("duplicate_layer")
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
        self.content_changed.emit("move_layer")
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
        self._validate_clipping_masks()
        self.set_active_layer(uid)
        self.content_changed.emit("move_layer")
        return True

    def merge_down(self, target) -> bool:
        layer = self._resolve_uid(target)
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
        self._validate_clipping_masks()
        self.content_changed.emit("merge_down")
        return True

    def _validate_clipping_masks(self) -> None:
        """Garante que a primeira camada (índice 0) nunca permaneça como máscara de recorte."""
        if self.layers and self.layers[0].clipping_mask:
            self.layers[0].clipping_mask = False
            self.layer_property_changed.emit(self.layers[0].uid)

    def set_clipping_mask(self, idx: int, enabled: bool) -> None:
        layer = self.get_layer_at_index(idx)
        if layer:
            if self.layers.index(layer) == 0 and enabled:
                enabled = False  # A camada na base nunca pode ser máscara de recorte
            layer.clipping_mask = bool(enabled)
            self.layer_property_changed.emit(layer.uid)
            self.content_changed.emit("clipping_mask")

    def set_alpha_lock(self, idx: int, enabled: bool) -> None:
        layer = self.get_layer_at_index(idx)
        if layer:
            layer.alpha_locked = bool(enabled)
            self.layer_property_changed.emit(layer.uid)
            self.content_changed.emit("alpha_lock")

    def set_layer_visibility(self, idx: int, visible: bool) -> None:
        layer = self.get_layer_at_index(idx)
        if layer:
            layer.visible = bool(visible)
            self.layer_property_changed.emit(layer.uid)
            self.content_changed.emit("visibility")

    def rename_layer(self, uid: int, name: str) -> bool:
        layer = self.get_layer_by_uid(uid)
        name = str(name).strip()
        if not layer or not name:
            return False
        if layer.name == name:
            return True
        layer.name = name
        self.layer_property_changed.emit(layer.uid)
        self.content_changed.emit("rename_layer")
        return True

    def set_layer_name(self, idx: int, name: str) -> bool:
        layer = self.get_layer_at_index(idx)
        return self.rename_layer(layer.uid, name) if layer else False

    def set_layer_opacity(self, idx: int, opacity: float) -> bool:
        layer = self.get_layer_at_index(idx)
        if not layer:
            return False
        layer.opacity = max(0.0, min(1.0, float(opacity)))
        self.layer_property_changed.emit(layer.uid)
        self.content_changed.emit("opacity")
        return True

    def set_layer_blend_mode(self, idx: int, blend_mode) -> bool:
        layer = self.get_layer_at_index(idx)
        if not layer:
            return False
        layer.blend_mode = blend_mode
        self.layer_property_changed.emit(layer.uid)
        self.content_changed.emit("blend_mode")
        return True

    def flatten_group(self, idx: int) -> bool:
        group = self.get_layer_at_index(idx)
        if not group or not group.is_group:
            return False
        if group and group.is_group:
            descendants = {group.uid}
            while True:
                children = {layer.uid for layer in self.layers if layer.parent_uid in descendants}
                if children <= descendants:
                    break
                descendants |= children
            self.order_about_to_change.emit()
            group.is_group = False
            if group.blend_mode in ("Atravessar", "PassThrough", "Pass-Through", 7):
                group.blend_mode = "Normal"
            self.layers = [layer for layer in self.layers if layer.uid == group.uid or layer.uid not in descendants]
            if self._active_uid in descendants:
                self.set_active_layer(group.uid)
            self.order_changed.emit()
            self.content_changed.emit("flatten_group")
            self.validate_integrity()
            return True
        return False

    def flatten_image(self) -> bool:
        if len(self.layers) > 1:
            base = self.layers[0]
            base.is_group = False
            base.parent_uid = None
            self.layers = [base]
            self.set_active_layer(base.uid)
            self.order_changed.emit()
            self.content_changed.emit("flatten_image")
            self.validate_integrity()
            return True
        return False

    def reorder_and_reparent(self, new_order_uids, parent_map):
        order = [str(uid) for uid in new_order_uids]
        nodes = {str(layer.uid): layer for layer in self.layers}
        if len(order) != len(nodes) or set(order) != set(nodes):
            raise ValueError("A ordem deve conter cada camada exatamente uma vez.")
        parents = {uid: str(parent_map[uid]) if parent_map.get(uid) is not None else None for uid in order}
        for uid in order:
            seen = {uid}
            parent = parents[uid]
            while parent is not None:
                if parent in seen or parent not in nodes or not nodes[parent].is_group:
                    raise ValueError("Hierarquia de camadas inválida.")
                seen.add(parent)
                parent = parents[parent]
        self.order_about_to_change.emit()
        
        id_to_layer = {str(l.uid): l for l in self.layers}
        new_list = []
        for uid_str in order:
            if uid_str in id_to_layer:
                l = id_to_layer[uid_str]
                p_uid = parent_map.get(uid_str)
                l.parent_uid = int(p_uid) if p_uid is not None else None
                new_list.append(l)
                
        self.layers = new_list
        self.order_changed.emit()
        self.validate_integrity()

    def replace_layers(self, records) -> None:
        """Reconstrói a projeção local a partir de registros persistidos."""
        new_layers = []
        max_uid = 0
        for record in records or []:
            uid = int(record.get("uid", max_uid + 1))
            max_uid = max(max_uid, uid)
            layer = LocalLayer(
                uid,
                str(record.get("name", f"Camada {uid}")),
                parent_uid=record.get("parent_uid"),
                is_group=bool(record.get("is_group", False)),
                is_filter=bool(record.get("is_filter", False)),
            )
            layer.visible = bool(record.get("visible", True))
            layer.locked = bool(record.get("locked", False))
            layer.opacity = max(0.0, min(1.0, float(record.get("opacity", 1.0))))
            layer.blend_mode = record.get("blend_mode", "Atravessar" if layer.is_group else "Normal")
            layer.alpha_locked = bool(record.get("alpha_locked", False))
            layer.clipping_mask = bool(record.get("clipping_mask", False))
            new_layers.append(layer)
        self.order_about_to_change.emit()
        self.layers = new_layers
        self._next_uid = max_uid + 1
        active_uid = next((r.get("uid") for r in records or [] if r.get("uid") == self._active_uid), None)
        self._active_uid = active_uid if active_uid is not None else (new_layers[0].uid if new_layers else None)
        self.order_changed.emit()
        if not self._history_guard:
            self._last_structural_snapshot = self._snapshot()
