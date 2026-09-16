from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QLineEdit
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QEvent, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFontMetrics, QIcon, QPixmap, QFont
from ui.core.icons import get_icon

from .model import (
    ROLE_UID, ROLE_IS_GROUP, ROLE_VISIBLE, ROLE_LOCKED,
    ROLE_ALPHA_LOCK, ROLE_CLIPPING_MASK, ROLE_CHILD_COUNT,
    ROLE_EFFECTIVE_VISIBLE, ROLE_EFFECTIVE_OPACITY, ROLE_IS_FILTER
)

ROW_HEIGHT = 48
PADDING = 8
ICON_SIZE = 20
THUMB_W = 38
THUMB_H = 28

STATUS_ICON_SIZE = 16
SLOT_SPACING = 8
SLOT_WIDTH = STATUS_ICON_SIZE + SLOT_SPACING

class LayerItemDelegate(QStyledItemDelegate):
    actionRequested = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.colors = {}

    def set_colors(self, colors):
        self.colors = colors

    def sizeHint(self, option, index):
        return QSize(100, ROW_HEIGHT)

    def _get_right_content_x(self, rect: QRect, clip: bool, is_group: bool) -> int:
        curr_x = rect.left() + PADDING
        curr_x += ICON_SIZE + 4  # Visibilidade
        if clip:
            curr_x += 16
        elif is_group:
            curr_x += 18
        else:
            curr_x += 16
        curr_x += THUMB_W + PADDING  # Thumbnail
        return curr_x

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect
        is_selected = option.state & QStyle.State_Selected
        is_hovered = option.state & QStyle.State_MouseOver

        uid = index.data(ROLE_UID)
        name = index.data(Qt.DisplayRole)
        is_group = index.data(ROLE_IS_GROUP)
        is_filter = index.data(ROLE_IS_FILTER)
        visible = index.data(ROLE_VISIBLE)
        locked = index.data(ROLE_LOCKED)
        alpha_locked = index.data(ROLE_ALPHA_LOCK)
        clip = index.data(ROLE_CLIPPING_MASK)
        eff_vis = index.data(ROLE_EFFECTIVE_VISIBLE)

        from ui.core.theme import ThemeManager
        tm = ThemeManager.instance()
        
        accent_color = tm.get_color("ACCENT")
        text_color = tm.get_color("text_main")
        text_muted = tm.get_color("text_sec")
        border = tm.get_color("border")
        
        bg_darkest = tm.get_color("BG_DARKEST")
        bg_darker = tm.get_color("BG_DARKER")
        bg_dark = tm.get_color("BG_DARK")

        if not eff_vis:
            painter.setOpacity(0.4)

        # 1. Background
        if is_selected:
            sel_color = QColor(bg_darkest)
            painter.fillRect(rect, sel_color)
            accent_tint = QColor(accent_color)
            accent_tint.setAlpha(28)
            painter.fillRect(rect, accent_tint)
            accent_bar = QRect(rect.left(), rect.top(), 3, rect.height() - 1)
            painter.fillRect(accent_bar, QColor(accent_color))
        elif is_hovered:
            painter.fillRect(rect, QColor(bg_dark))
        else:
            painter.fillRect(rect, QColor(bg_darker))
            
        # Linha separadora inferior
        painter.setPen(QPen(QColor(border), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        curr_x = rect.left() + PADDING

        # --- [1] Visibilidade ---
        eye_rect = QRect(curr_x, rect.top() + (ROW_HEIGHT - ICON_SIZE)//2, ICON_SIZE, ICON_SIZE)
        eye_color = text_color if visible else text_muted
        eye_icon = get_icon("eye" if visible else "eye-off", eye_color)
        eye_icon.paint(painter, eye_rect)
        
        curr_x += ICON_SIZE + 4

        # --- [2] Indent & Type Arrow ---
        if clip:
            type_rect = QRect(curr_x, rect.top(), 16, ROW_HEIGHT)
            painter.setPen(QColor(accent_color))
            f = QFont(painter.font().family(), 12)
            painter.setFont(f)
            painter.drawText(type_rect, Qt.AlignCenter, "↳")
            curr_x += 16
        elif is_group:
            type_rect = QRect(curr_x, rect.top(), 18, ROW_HEIGHT)
            painter.setPen(QColor(text_color))
            f = QFont(painter.font().family(), 9, QFont.Bold)
            painter.setFont(f)
            is_expanded = option.state & QStyle.State_Open
            arrow = "▼" if is_expanded else "▶"
            painter.drawText(type_rect, Qt.AlignCenter, arrow)
            curr_x += 18
        else:
            curr_x += 16

        # --- [3] Preview (Thumb) ---
        thumb_rect = QRect(curr_x, rect.top() + (ROW_HEIGHT - THUMB_H)//2, THUMB_W, THUMB_H)
        if is_group:
            folder_icon = get_icon("folder", text_color)
            folder_icon.paint(painter, thumb_rect.adjusted(6, 4, -6, -4))
        elif is_filter:
            filter_bg = self.colors.get("ACCENT_MUTED", "#312e81")
            painter.setBrush(QColor(filter_bg))
            painter.setPen(QPen(QColor(accent_color), 1))
            painter.drawRoundedRect(thumb_rect, 2, 2)
            fx_icon = get_icon("sliders", text_color)
            fx_icon.paint(painter, thumb_rect.adjusted(6, 4, -6, -4))
        else:
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(QColor(border), 1))
            painter.drawRoundedRect(thumb_rect, 2, 2)
            
            thumb_pix = index.data(Qt.DecorationRole)
            if isinstance(thumb_pix, QPixmap) and not thumb_pix.isNull():
                painter.drawPixmap(thumb_rect.adjusted(1, 1, -1, -1), thumb_pix.scaled(thumb_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        curr_x += THUMB_W + PADDING

        # --- [4] Duas linhas organizadas à direita da miniatura ---
        # LINHA 1 (Topo): Nome da Camada
        name_w = rect.right() - curr_x - PADDING
        name_rect = QRect(curr_x, rect.top() + 5, max(0, name_w), 18)

        if is_filter:
            painter.setPen(QColor(accent_color) if visible else QColor(accent_color).darker(160))
        else:
            painter.setPen(QColor(text_color) if visible else QColor(text_color).darker(200))

        font = QFont(option.font.family() if option.font.family() else "Segoe UI", 9)
        font.setBold(bool(is_selected or is_group))
        painter.setFont(font)
        fm = QFontMetrics(font)
        elided_name = fm.elidedText(str(name), Qt.ElideRight, name_w)
        painter.drawText(name_rect, Qt.AlignVCenter | Qt.AlignLeft, elided_name)

        # LINHA 2 (Baixo): Ícones de Operações (Clip Mask, Alpha Lock, Lock Layer)
        icons_y = rect.top() + 26
        icon_dim = STATUS_ICON_SIZE

        # 1. Clipping Mask Icon
        clip_rect = QRect(curr_x, icons_y, icon_dim, icon_dim)
        clip_color = QColor(self.colors.get("SUCCESS", "#10b981")) if clip else QColor(text_muted)
        if not clip:
            painter.setOpacity(0.35)
        clip_icon = get_icon("clip-mask", clip_color.name())
        clip_icon.paint(painter, clip_rect)
        if not clip:
            painter.setOpacity(1.0 if eff_vis else 0.4)

        # 2. Alpha Lock Icon
        alpha_rect = QRect(curr_x + 24, icons_y, icon_dim, icon_dim)
        alpha_color = QColor(self.colors.get("WARNING", "#f59e0b")) if alpha_locked else QColor(text_muted)
        if not alpha_locked:
            painter.setOpacity(0.35)
        alpha_icon = get_icon("alpha-lock", alpha_color.name())
        alpha_icon.paint(painter, alpha_rect)
        if not alpha_locked:
            painter.setOpacity(1.0 if eff_vis else 0.4)

        # 3. Lock Layer Icon
        lock_rect = QRect(curr_x + 48, icons_y, icon_dim, icon_dim)
        lock_color = QColor(accent_color) if locked else QColor(text_muted)
        if not locked:
            painter.setOpacity(0.35)
        lock_icon = get_icon("lock", lock_color.name())
        lock_icon.paint(painter, lock_rect)
        if not locked:
            painter.setOpacity(1.0 if eff_vis else 0.4)

        painter.restore()

    def get_hitboxes(self, rect: QRect, is_group: bool, clip: bool = False) -> dict:
        eye_box = QRect(rect.left() + PADDING, rect.top(), ICON_SIZE + 4, ROW_HEIGHT)
        collapse_box = QRect(rect.left() + PADDING + ICON_SIZE + 4, rect.top(), 18, ROW_HEIGHT) if is_group else QRect()
        
        curr_x = self._get_right_content_x(rect, clip, is_group)
        icons_y = rect.top() + 24
        
        thumb_x = curr_x - PADDING - THUMB_W
        thumb_box = QRect(thumb_x, rect.top() + (ROW_HEIGHT - THUMB_H) // 2, THUMB_W, THUMB_H)

        clip_box = QRect(curr_x - 2, icons_y - 2, 22, 22)
        alpha_box = QRect(curr_x + 22, icons_y - 2, 22, 22)
        lock_box = QRect(curr_x + 46, icons_y - 2, 22, 22)
        name_box = QRect(curr_x, rect.top() + 2, max(0, rect.right() - curr_x - PADDING), 20)
        
        return {
            'eye': eye_box,
            'collapse': collapse_box,
            'thumb': thumb_box,
            'clip': clip_box,
            'alpha': alpha_box,
            'lock': lock_box,
            'name': name_box
        }

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            uid = index.data(ROLE_UID)
            is_group = index.data(ROLE_IS_GROUP)
            clip = index.data(ROLE_CLIPPING_MASK)
            
            boxes = self.get_hitboxes(option.rect, is_group, clip)
            
            if boxes['eye'].contains(pos):
                self.actionRequested.emit("toggle_visibility", uid)
                return True
                
            if is_group and boxes['collapse'].contains(pos):
                self.actionRequested.emit("toggle_collapse", uid)
                return True
                
            if boxes['clip'].contains(pos):
                self.actionRequested.emit("toggle_clipping_mask", uid)
                return True
                
            if boxes['alpha'].contains(pos):
                self.actionRequested.emit("toggle_alpha", uid)
                return True
                
            if boxes['lock'].contains(pos):
                self.actionRequested.emit("toggle_lock", uid)
                return True
                
        return super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        
        from ui.core.theme import ThemeManager
        tm = ThemeManager.instance()
        bg_light = tm.get_color("bg_panel")
        accent_color = tm.get_color("ACCENT")
        fg_color = tm.get_color("text_main")
        
        editor.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_light};
                color: {fg_color};
                border: 1px solid {accent_color};
                border-radius: 3px;
                padding: 1px 4px;
                font-size: 11px;
            }}
        """)
        return editor

    def setEditorData(self, editor, index):
        text = index.data(Qt.EditRole) or index.data(Qt.DisplayRole) or ""
        editor.setText(text)
        editor.selectAll()

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        rect = option.rect
        clip = index.data(ROLE_CLIPPING_MASK)
        is_group = index.data(ROLE_IS_GROUP)
        
        curr_x = self._get_right_content_x(rect, clip, is_group)
        name_w = rect.right() - curr_x - PADDING
        
        editor.setGeometry(curr_x, rect.top() + 3, max(0, name_w), 20)
