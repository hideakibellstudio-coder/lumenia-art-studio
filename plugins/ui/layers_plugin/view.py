from PySide6.QtWidgets import QTreeView, QAbstractItemView
from PySide6.QtCore import Qt, Signal
import logging

logger = logging.getLogger(__name__)

# NOTA: NÃO usar subclasses de QProxyStyle aqui. O Qt transfere a ownership do
# estilo para o C++ e o shiboken deleta o wrapper Python depois → double-free
# (crash de acesso inválido no fechamento da aplicação). A supressão da moldura
# de foco é feita via QSS (`outline: none`), 100% segura.

class LayerTreeView(QTreeView):
    deleteRequested = Signal()
    moveUpRequested = Signal()
    moveDownRequested = Signal()
    mergeDownRequested = Signal()
    duplicateRequested = Signal()
    clearRequested = Signal()
    addLayerRequested = Signal()
    addGroupRequested = Signal()
    toggleClippingRequested = Signal(int)
    editFilterRequested = Signal(int)
    renameRequested = Signal(int, object)  # (uid, rect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setStyleSheet("""
            QTreeView {
                background-color: transparent;
                border: none;
                outline: 0;
            }
            QTreeView::item {
                background: transparent;
                border: none;
                outline: 0;
            }
            QTreeView::item:hover {
                background: transparent;
                border: none;
                outline: 0;
            }
            QTreeView::item:selected {
                background: transparent;
                border: none;
                outline: 0;
            }
            QTreeView::item:selected:active {
                background: transparent;
                border: none;
                outline: 0;
            }
            QTreeView::item:selected:!active {
                background: transparent;
                border: none;
                outline: 0;
            }
            QTreeView::item:focus {
                background: transparent;
                border: none;
                outline: 0;
            }
            QTreeView::branch {
                background: transparent;
                border: none;
                outline: 0;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings,
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                image: none;
            }
        """)
        self.setIndentation(16)
        self.setRootIsDecorated(False)
        self.setAnimated(True)
        self.setAllColumnsShowFocus(False)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        
        self._expanded_uids_backup = []

    def setModel(self, model):
        super().setModel(model)
        if model:
            model.modelAboutToBeReset.connect(self._backup_expanded_state)
            model.modelReset.connect(self._restore_expanded_state)
            model.layoutAboutToBeChanged.connect(self._backup_expanded_state)
            model.layoutChanged.connect(self._restore_expanded_state)

    def _backup_expanded_state(self):
        from .model import ROLE_UID
        self._expanded_uids_backup = []
        model = self.model()
        if not model:
            return
            
        def traverse(parent_index=None):
            from PySide6.QtCore import QModelIndex
            parent = parent_index if parent_index else QModelIndex()
            for r in range(model.rowCount(parent)):
                idx = model.index(r, 0, parent)
                if self.isExpanded(idx):
                    uid = model.data(idx, ROLE_UID)
                    self._expanded_uids_backup.append(uid)
                if model.hasChildren(idx):
                    traverse(idx)
                    
        traverse()

    def _restore_expanded_state(self):
        from .model import ROLE_UID
        if not self._expanded_uids_backup:
            return
            
        model = self.model()
        if not model:
            return
            
        def traverse(parent_index=None):
            from PySide6.QtCore import QModelIndex
            parent = parent_index if parent_index else QModelIndex()
            for r in range(model.rowCount(parent)):
                idx = model.index(r, 0, parent)
                uid = model.data(idx, ROLE_UID)
                if uid in self._expanded_uids_backup:
                    self.expand(idx)
                if model.hasChildren(idx):
                    traverse(idx)
                    
        def deferred_restore():
            self.setUpdatesEnabled(False)
            was_animated = self.isAnimated()
            self.setAnimated(False)
            try:
                traverse()
            finally:
                self.setAnimated(was_animated)
                self.setUpdatesEnabled(True)
            self._expanded_uids_backup = []
            
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, deferred_restore)

    def keyPressEvent(self, event):
        mods = event.modifiers()
        key = event.key()
        
        if key == Qt.Key_Delete:
            self.deleteRequested.emit()
        elif mods & Qt.ControlModifier and key == Qt.Key_BracketRight:
            self.moveUpRequested.emit()
        elif mods & Qt.ControlModifier and key == Qt.Key_BracketLeft:
            self.moveDownRequested.emit()
        elif mods & Qt.ControlModifier and key == Qt.Key_E:
            self.mergeDownRequested.emit()
        else:
            super().keyPressEvent(event)

    def startDrag(self, supportedActions):
        indexes = self.selectedIndexes()
        if not indexes:
            return
            
        mimeData = self.model().mimeData(indexes)
        if not mimeData:
            return
            
        from PySide6.QtGui import QDrag, QPixmap, QPainter
        from PySide6.QtCore import Qt, QPoint
        
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        
        rect = self.visualRect(indexes[0])
        pixmap = QPixmap(rect.size())
        pixmap.fill(Qt.transparent)
        self.render(pixmap, QPoint(), rect)
        
        transparent_pixmap = QPixmap(pixmap.size())
        transparent_pixmap.fill(Qt.transparent)
        painter = QPainter(transparent_pixmap)
        painter.setOpacity(0.55)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        drag.setPixmap(transparent_pixmap)
        drag.setHotSpot(QPoint(16, transparent_pixmap.height() // 2))
        
        drag.exec(supportedActions)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            index = self.indexAt(pos)
            if index.isValid():
                rect = self.visualRect(index)
                delegate = self.itemDelegate(index)
                if hasattr(delegate, "get_hitboxes"):
                    from .model import ROLE_IS_GROUP, ROLE_CLIPPING_MASK, ROLE_IS_FILTER, ROLE_UID
                    is_group = bool(index.data(ROLE_IS_GROUP))
                    clip = bool(index.data(ROLE_CLIPPING_MASK))
                    boxes = delegate.get_hitboxes(rect, is_group, clip)
                    
                    name_box = boxes.get("name")
                    if name_box and name_box.contains(pos):
                        uid = index.data(ROLE_UID)
                        self.renameRequested.emit(int(uid), rect)
                        return

                    is_filter = bool(index.data(ROLE_IS_FILTER))
                    thumb_box = boxes.get("thumb")
                    if is_filter and thumb_box and thumb_box.contains(pos):
                        uid = index.data(ROLE_UID)
                        self.editFilterRequested.emit(int(uid))
                        return

                return

        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        from ui.core.icons import get_icon
        from ui.core.i18n import tr
        from PySide6.QtWidgets import QMenu

        if not index.isValid():
            menu = QMenu(self)

            act_add_layer = menu.addAction(get_icon("plus"), tr("layers.new_layer", "Nova Camada"))
            act_add_group = menu.addAction(get_icon("folder"), tr("layers.new_group", "Novo Grupo"))

            action = menu.exec(event.globalPos())
            if action == act_add_layer:
                self.addLayerRequested.emit()
            elif action == act_add_group:
                self.addGroupRequested.emit()
            return

        from .model import ROLE_IS_FILTER, ROLE_CLIPPING_MASK, ROLE_UID
        menu = QMenu(self)

        is_filter = bool(index.data(ROLE_IS_FILTER))
        is_clip = bool(index.data(ROLE_CLIPPING_MASK))
        uid = index.data(ROLE_UID)

        act_edit_filter = None
        if is_filter:
            act_edit_filter = menu.addAction(get_icon("settings"), tr("layers.edit_filter", "Editar Filtro / Ajuste..."))
            menu.addSeparator()

        clip_label = tr("layers.release_clipping", "Liberar Máscara de Recorte") if is_clip else tr("layers.create_clipping", "Criar Máscara de Recorte")
        act_toggle_clip = menu.addAction(get_icon("clip-mask"), clip_label)
        
        # A primeira camada do documento (índice 0) nunca pode ser máscara de recorte
        model = self.model()
        if hasattr(model, "layer_manager") and model.layer_manager.layers:
            if model.layer_manager.layers[0].uid == uid and not is_clip:
                act_toggle_clip.setEnabled(False)

        menu.addSeparator()

        act_rename = menu.addAction(get_icon("edit"), tr("layers.rename", "Renomear"))
        act_duplicate = menu.addAction(get_icon("duplicate"), tr("layers.duplicate", "Duplicar Camada"))
        menu.addSeparator()

        act_move_up = menu.addAction(get_icon("chevron_up"), tr("layers.move_up", "Mover para Cima"))
        act_move_down = menu.addAction(get_icon("chevron_down"), tr("layers.move_down", "Mover para Baixo"))
        act_merge_down = menu.addAction(get_icon("layer_flatten"), tr("layers.merge_down", "Mesclar para Baixo"))
        menu.addSeparator()

        act_clear = menu.addAction(get_icon("clean_layer"), tr("layers.clear_layer", "Limpar Conteúdo"))
        act_delete = menu.addAction(get_icon("trash"), tr("layers.delete", "Excluir Camada"))

        action = menu.exec(event.globalPos())
        if act_edit_filter and action == act_edit_filter:
            self.editFilterRequested.emit(int(uid))
        elif action == act_toggle_clip:
            self.toggleClippingRequested.emit(int(uid))
        elif action == act_rename:
            rect = self.visualRect(index)
            self.renameRequested.emit(int(uid), rect)
        elif action == act_duplicate:
            self.duplicateRequested.emit()
        elif action == act_move_up:
            self.moveUpRequested.emit()
        elif action == act_move_down:
            self.moveDownRequested.emit()
        elif action == act_merge_down:
            self.mergeDownRequested.emit()
        elif action == act_clear:
            self.clearRequested.emit()
        elif action == act_delete:
            self.deleteRequested.emit()
