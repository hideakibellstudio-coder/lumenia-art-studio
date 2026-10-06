"""Document — Representação de um documento aberto no Lumenia."""

from __future__ import annotations
import copy

from PySide6 import QtCore, QtGui
from .layer_manager import LocalLayerManager


class Document(QtCore.QObject):
    """Modelo de dados isolado de um documento MDI aberto."""

    geometry_changed = QtCore.Signal(int, int)
    # Toda alteração que suja o documento (motivo). A janela principal usa
    # para atualizar Desfazer/Refazer; antes só um traço atualizava.
    modified = QtCore.Signal(str)
    # Histórico descartado ("Limpar Undo"): não suja o documento, mas muda
    # Desfazer/Refazer.
    history_cleared = QtCore.Signal()
    # Papel alterado por set_paper(): frozenset com os nomes dos campos.
    paper_changed = QtCore.Signal(object)

    # Campos de set_paper() -> atributo do documento.
    PAPER_FIELDS = {
        "color": "paper_color",
        "visible": "paper_visible",
        "texture_id": "paper_texture_id",
        "texture_enabled": "paper_texture_enabled",
        "scale": "paper_scale",
        "contrast": "paper_contrast",
        "invert": "paper_invert",
    }

    def set_paper(self, **changes) -> None:
        """Altera o papel (fonte única): suja o documento, sincroniza o motor e avisa.

        Ex.: `doc.set_paper(color=QColor(...), visible=False)`. Valor igual não
        emite. Views do papel (painel de camadas, canvas) leem daqui.
        """
        unknown = set(changes) - set(self.PAPER_FIELDS)
        if unknown:
            raise ValueError(f"campos de papel desconhecidos: {sorted(unknown)}")
        changed = frozenset(
            key for key, value in changes.items()
            if getattr(self, self.PAPER_FIELDS[key]) != value
        )
        if not changed:
            return
        for key in changed:
            setattr(self, self.PAPER_FIELDS[key], changes[key])
        self.mark_dirty("paper")
        from .paper_backend_sync import sync_paper_to_backend
        sync_paper_to_backend(self, changed)
        self.paper_changed.emit(changed)

    def set_geometry(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Dimensões inválidas.")
        if (self.width, self.height) != (width, height):
            self.width, self.height = width, height
            self.geometry_changed.emit(width, height)

    @property
    def rgba16_document(self) -> bool:
        """True quando o documento é 16 bits por canal (RGBA16)."""
        return self.pixel_format == 1

    def __init__(self, uid: str, name: str, width: int = 1920, height: int = 1080, pixel_format: int = 0):
        super().__init__()
        self.uid = uid
        self.name = name
        self.file_path: str | None = None
        self.format_id: str = "lmn"
        from .schema import CURRENT_VERSION
        self.format_version: int = CURRENT_VERSION
        self.pixel_format: int = int(pixel_format)
        self.width = max(1, width)
        self.height = max(1, height)
        # Resolução de impressão (pontos por polegada); vai no arquivo .lmn.
        self.dpi: int = 300

        # Gerenciador de camadas local do documento
        self.layer_manager = LocalLayerManager()
        self.layer_manager.document = self
        from .history import DocumentHistory
        self.history = DocumentHistory(self)

        # Posição da câmera no viewport
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.rotation = 0.0

        # Cor ativa e histórico
        self.saved_color: QtGui.QColor | None = None
        self.is_dirty: bool = False
        self.revision: int = 0
        self.dirty_reason: str | None = None

        # Papel de Fundo (Layer 0)
        self.paper_color = QtGui.QColor(255, 255, 255, 255)
        self.paper_visible = True
        self.paper_texture_id = 0
        self.paper_texture_enabled = False
        self.paper_scale = 1.0
        self.paper_contrast = 1.0
        self.paper_invert = False

        # Estados de Guias e Simetria específicos do documento
        self.guide_state: dict = {}
        self.sym_state: dict = {}

        # Perfil ICC embutido no arquivo (F-006), para regravar os mesmos bytes.
        # O id do perfil é estado do motor por documento
        # (`EngineBackend.get_color_profile` no contexto ativo).
        self.color_profile_icc_bytes: bytes | None = None
        self.color_profile_name: str | None = None

        # Qualquer mutação de camada invalida o estado salvo do documento.
        self.layer_manager.content_changed.connect(self._on_content_changed)
        # Métodos ligados, não lambdas: o lambda capturava `self` dentro de uma
        # conexão guardada no lado C++ do LocalLayerManager, formando um ciclo
        # que o coletor do Python não enxerga. Todo documento fechado ficava vivo
        # (~89 KB cada; medido em 2026-09-22 com scripts/soak_full_session.py).
        self.layer_manager.layer_property_changed.connect(self._on_layer_property_changed)
        self.layer_manager.order_changed.connect(self._on_layer_order_changed)

    def _on_content_changed(self, reason: str) -> None:
        self.mark_dirty(reason)

    def _on_layer_property_changed(self, _uid=None) -> None:
        self.mark_dirty("layer_property")

    def _on_layer_order_changed(self) -> None:
        self.mark_dirty("layer_order")

    def store_guide_state(self, state) -> None:
        """Guias do documento (escritas pelo controlador de geometria do canvas); diferente suja."""
        if self.guide_state != dict(state):
            self.guide_state = copy.deepcopy(dict(state))
            self.mark_dirty("guide_state")

    def store_sym_state(self, state) -> None:
        """Simetria do documento; diferente suja."""
        if self.sym_state != dict(state):
            self.sym_state = copy.deepcopy(dict(state))
            self.mark_dirty("sym_state")

    def mark_dirty(self, reason: str = "content") -> None:
        self.revision += 1
        self.is_dirty = True
        self.dirty_reason = str(reason)
        self.modified.emit(self.dirty_reason)

    def mark_saved(self, file_path: str | None = None, revision: int | None = None) -> None:
        """Grava no documento que ele foi salvo.

        `revision` é a do instante em que a captura foi tirada (`SaveCapture.revision`): a gravação
        acontece depois, em outra thread, e o artista pode ter editado nesse meio tempo. O arquivo
        guarda o documento como estava na captura; se o documento já passou disso, continua sujo."""
        if file_path is not None:
            self.file_path = str(file_path)
        if revision is not None and revision != self.revision:
            return
        self.is_dirty = False
        self.dirty_reason = None
