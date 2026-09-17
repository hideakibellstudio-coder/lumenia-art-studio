from PySide6 import QtCore
from .document import Document

class DocumentManager(QtCore.QObject):
    activeDocumentChanged = QtCore.Signal(object)  # Emite o Document ativo (ou None se todos fechados)
    documentAdded = QtCore.Signal(object)
    documentClosed = QtCore.Signal(str)           # Emite o uid do documento fechado

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._documents = {}
        self._active_document = None
        self._counter = 0

    def new_document(
        self,
        width: int = 1920,
        height: int = 1080,
        name: str = None,
        bg_color: tuple[int, int, int, int] | None = None,
        paper_texture_id: int = 0,
        activate: bool = True
    ) -> Document:
        self._counter += 1
        uid = f"doc_{self._counter}"
        if not name:
            name = f"Sem Título {self._counter}"
            
        doc: Document = Document(uid, name, width, height)

        if bg_color is not None:
            from PySide6.QtGui import QColor
            doc.paper_color = QColor(*bg_color)
            if bg_color[3] == 0:  # Transparente
                doc.paper_visible = False

        if paper_texture_id > 0:
            doc.paper_texture_id = paper_texture_id
            doc.paper_texture_enabled = True
        
        # Garante exatamente uma camada padrão inicial (Camada 1)
        if len(doc.layer_manager.layers) == 0:
            doc.layer_manager.add_layer("Camada 1")
        # A camada criada pelo bootstrap faz parte do estado inicial, não de uma
        # alteração do usuário.
        doc.mark_saved()
        
        self._documents[uid] = doc
        self.documentAdded.emit(doc)
        
        if activate:
            self.set_active_document(uid)
            
        return doc

    def get_document(self, uid: str) -> Document:
        return self._documents.get(uid)

    def has_document(self) -> bool:
        return self._active_document is not None

    def active_document(self) -> Document:
        return self._active_document

    def documents(self) -> list[Document]:
        """Retorna uma cópia ordenada dos documentos abertos."""
        return list(self._documents.values())

    def set_active_document(self, uid: str):
        if uid in self._documents and (self._active_document is None or self._active_document.uid != uid):
            self._active_document = self._documents[uid]
            self.activeDocumentChanged.emit(self._active_document)

    def close_document(self, uid: str):
        if uid in self._documents:
            doc = self._documents[uid]
            del self._documents[uid]
            self.documentClosed.emit(uid)
            
            # Se o fechado era o ativo, escolhe o próximo ou None
            if self._active_document == doc:
                if self._documents:
                    # Pega o primeiro disponível
                    next_uid = list(self._documents.keys())[0]
                    self.set_active_document(next_uid)
                else:
                    self._active_document = None
                    self.activeDocumentChanged.emit(None)
