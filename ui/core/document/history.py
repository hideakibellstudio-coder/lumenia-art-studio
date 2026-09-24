"""One timeline for native pixels and the document's layer metadata.

Native steps own COW layer snapshots. Python only associates stable UIDs and
view metadata with the native step ID; it never guesses identity from names.
"""

import logging
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from .local_layer import LocalLayer

logger = logging.getLogger(__name__)


class LayerTransactionCancelled(Exception):
    """Sinaliza cancelamento explícito de uma operação interativa.

    Diálogos de preview mantêm a operação nativa aberta enquanto o usuário
    experimenta parâmetros. O cancelamento precisa desfazer a transação sem
    criar uma entrada vazia no histórico e sem ser reportado como erro.
    """


class DocumentHistory:
    def __init__(self, document):
        self.document = document
        self.entries = {}
        self.recording = False

    def _check_context(self, backend):
        if backend.get_active_document_context() != self.document.uid:
            raise RuntimeError("O documento ativo não corresponde ao motor.")

    def _model_projection_signature(self):
        manager = self.document.layer_manager
        manager.validate_integrity()
        return tuple((layer.uid, bool(layer.is_group), bool(layer.is_filter), layer.parent_uid or 0)
                     for layer in manager.layers)

    def _bootstrap_projection_signature(self):
        manager = self.document.layer_manager
        layer: LocalLayer  # anotacao para o resolvedor do Navigator (usado nas comprehensions abaixo)
        indices = {layer.uid: index for index, layer in enumerate(manager.layers)}
        return tuple((bool(layer.is_group), bool(layer.is_filter), indices.get(layer.parent_uid, -1))
                     for layer in manager.layers)

    def _native_projection_signature(self, backend):
        if not hasattr(backend, "get_layer_info"):
            return None
        infos = [backend.get_layer_info(index) for index in range(backend.get_drawing_layer_count())]
        if any(not isinstance(info, dict) for info in infos):
            return None
        uids = [info.get("document_uid") for info in infos]
        if all(uid in (None, 0) for uid in uids):
            return tuple((bool(info.get("is_group", False)), bool(info.get("is_filter", False)),
                          int(info.get("parent_index", -1))) for info in infos)
        result = []
        for info in infos:
            parent_index = int(info.get("parent_index", -1))
            parent_uid = 0 if parent_index < 0 else uids[parent_index]
            if type(info.get("document_uid")) is not int or type(parent_uid) is not int:
                return None
            result.append((info["document_uid"], bool(info.get("is_group", False)),
                           bool(info.get("is_filter", False)), parent_uid))
        return tuple(result)

    def assert_projection(self, backend):
        native = self._native_projection_signature(backend)
        if native is not None and native != self._model_projection_signature():
            if native == self._bootstrap_projection_signature():
                return
            raise RuntimeError("projeção de camadas divergente entre Document e motor")

    def _native_document_uids(self, backend):
        """UIDs de documento que o motor carrega hoje, por índice.

        None quando o backend não expõe get_layer_info (dublês de teste) ou
        quando algum índice não devolve um uid inteiro -- nesses casos não há
        o que comparar e o chamador simplesmente segue.
        """
        if not hasattr(backend, "get_layer_info"):
            return None
        uids = []
        for index in range(backend.get_drawing_layer_count()):
            info = backend.get_layer_info(index)
            if not isinstance(info, dict) or type(info.get("document_uid")) is not int:
                return None
            uids.append(info["document_uid"])
        return uids

    def _warn_if_order_diverged(self, backend, model_uids):
        """Registra (sem interromper) a única divergência que escapa aos guards.

        Quando esta função roda, transaction() já conferiu contagem, tipo de
        camada e hierarquia. Sobra um caso: mesma população de camadas em
        ordem diferente entre Document e motor. Ele é invisível hoje porque
        bind_projection_identities vincula identidade POR POSIÇÃO -- ou seja,
        reescreve os uids nativos para casarem com o modelo e apaga a
        evidência antes que assert_projection possa olhar.

        Comparar os conjuntos isola exatamente esse caso e só ele: em add o
        motor tem um uid 0, em duplicate o clone nativo herda o uid da origem
        (LayerStack.cpp: cloneLayer copia o documentUid), e em remove/merge as
        populações diferem -- nenhum deles tem conjunto igual com ordem
        diferente, então não geram falso positivo.

        Deliberadamente só registra em log, não levanta: não existe caso
        reproduzível conhecido (Achado #5 do panorama de auditoria de
        camadas), e um falso positivo aqui abortaria uma ação legítima do
        usuário com rollback. O log é o que transforma "sem caso reproduzível"
        em "temos a ação que causou" -- se ele aparecer, aí sim vale fechar a
        divergência na origem.
        """
        native_uids = self._native_document_uids(backend)
        if native_uids is None or native_uids == model_uids:
            return
        if sorted(native_uids) != sorted(model_uids):
            return
        logger.error(
            "ordem de camadas divergente entre Document e motor "
            "(documento=%s, modelo=%s, motor=%s)",
            self.document.uid, model_uids, native_uids,
        )

    def bind_projection_identities(self, backend):
        """Bind immutable document UIDs to the aligned native layer stack."""
        manager = self.document.layer_manager
        if backend.get_drawing_layer_count() != len(manager.layers):
            raise RuntimeError("não é possível vincular identidades em pilhas divergentes")
        self._warn_if_order_diverged(backend, [layer.uid for layer in manager.layers])
        for index, layer in enumerate(manager.layers):
            if not backend.set_layer_document_uid(index, layer.uid):
                raise RuntimeError("não foi possível vincular a identidade da camada nativa")

    @contextmanager
    def transaction(self, backend):
        if self.recording:
            yield
            return
        self._check_context(backend)
        manager = self.document.layer_manager
        self.assert_projection(backend)
        before = self._snapshot()
        generation = backend.get_document_generation()
        if not backend.begin_layer_transaction():
            raise RuntimeError("Não foi possível iniciar a operação de camadas.")
        self.recording = True
        try:
            yield
            after = self._snapshot()
            if before == after and generation == backend.get_document_generation():
                backend.cancel_layer_transaction()
                return
            layers = manager.layers
            if backend.get_drawing_layer_count() != len(layers):
                raise RuntimeError("Operação cancelada: camadas divergentes entre documento e motor.")
            layer: LocalLayer
            # Achado #3 do panorama de auditoria profunda de camadas
            # (claude/panorama-motor-camadas-auditoria-profunda-2026-09-19.md):
            # este laço reescrevia incondicionalmente as 7 propriedades de
            # TODAS as camadas a cada transação bem-sucedida -- 4 delas
            # disparam uma composição completa do canvas (opacity, blend_mode,
            # visible, clipping_mask), então uma única ação de UI (ex.: mover
            # uma camada) custava 4xN composições completas, mesmo quando só
            # uma camada mudou. Agora cada propriedade só é reenviada ao motor
            # quando difere do valor nativo LIDO AO VIVO via get_layer_info().
            # Ler o estado nativo real (em vez de comparar apenas snapshots
            # Python antes/depois) preserva a garantia original de "cinto e
            # suspensórios": qualquer divergência acumulada no motor, seja
            # qual for a origem, ainda é detectada e corrigida aqui -- só o
            # trabalho redundante de reescrever um valor que já está correto
            # é eliminado. Backends sem get_layer_info (ex.: dublês de teste)
            # caem de volta no comportamento incondicional original.
            can_diff_live_state = hasattr(backend, "get_layer_info")
            for index, layer in enumerate(layers):
                if backend.is_group(index) != layer.is_group or backend.is_filter_layer(index) != layer.is_filter:
                    raise RuntimeError("Operação cancelada: tipo de camada divergente.")
                live = backend.get_layer_info(index) if can_diff_live_state else None
                if not isinstance(live, dict):
                    live = None
                if live is None or live.get("name") != layer.name:
                    backend.set_layer_name(index, layer.name)
                if live is None or live.get("opacity") != layer.opacity:
                    backend.set_layer_opacity(index, layer.opacity)
                if live is None or live.get("blend_mode") != layer.blend_mode:
                    backend.set_layer_blend_mode(index, layer.blend_mode)
                if live is None or live.get("visible") != layer.visible:
                    backend.set_layer_visibility(index, layer.visible)
                if live is None or live.get("locked") != layer.locked:
                    backend.set_layer_lock(index, layer.locked)
                if live is None or live.get("alpha_locked") != layer.alpha_locked:
                    backend.set_layer_alpha_lock(index, layer.alpha_locked)
                if live is None or live.get("clipping_mask") != layer.clipping_mask:
                    backend.set_layer_clipping_mask(index, layer.clipping_mask)
            indices = {layer.uid: index for index, layer in enumerate(layers)}
            parents = [indices.get(layer.parent_uid, -1) for layer in layers]
            if not backend.set_layer_parents(parents):
                raise RuntimeError("Não foi possível confirmar a hierarquia.")
            self.bind_projection_identities(backend)
            self.assert_projection(backend)
            backend.select_layer(manager.active_index)
            step = backend.commit_layer_transaction()
            if not step:
                raise RuntimeError("Não foi possível confirmar o histórico.")
            self.entries[step] = (before, after)
            retained = set(backend.get_history_step_ids())
            self.entries = {key: value for key, value in self.entries.items() if key in retained}
            self.document.mark_dirty("layer_transaction")
        except LayerTransactionCancelled:
            backend.cancel_layer_transaction()
            self._restore(before)
            return
        except Exception:
            backend.cancel_layer_transaction()
            self._restore(before)
            raise
        finally:
            self.recording = False

    def _snapshot(self):
        snapshot = deepcopy(self.document.layer_manager._snapshot())
        snapshot["document_size"] = (self.document.width, self.document.height)
        return snapshot

    def _restore(self, snapshot):
        manager = self.document.layer_manager
        manager.backend_projection_restoring = True
        try:
            manager._restore_snapshot(deepcopy(snapshot))
            self.document.set_geometry(*snapshot["document_size"])
        finally:
            manager.backend_projection_restoring = False

    def undo(self, backend):
        return self._move(backend, False)

    def redo(self, backend):
        return self._move(backend, True)

    def _move(self, backend, redo):
        self._check_context(backend)
        if self.recording:
            return False
        step = backend.get_redo_step_id() if redo else backend.get_undo_step_id()
        entry = self.entries.get(step)
        previous = self._snapshot() if entry else None
        if not (backend.redo() if redo else backend.undo()):
            return False
        if entry:
            try:
                self._restore(entry[1 if redo else 0])
            except Exception:
                # A failed model allocation must not leave native pixels on
                # the other side of the history step.
                if not (backend.undo() if redo else backend.redo()):
                    raise RuntimeError("Falha ao recuperar a transação de histórico.")
                self._restore(previous)
                raise
        self.document.mark_dirty("redo" if redo else "undo")
        return True


def layer_transaction(function):
    """Envolve uma ação de camadas inteira (modelo e motor) num passo de histórico.

    Contrato do dono (`host`), sem descoberta por `hasattr`:
    - `host.layer_manager`: o gerenciador que a ação altera (None = nada a
      fazer); tem de ser o do documento ativo;
    - `host.show_status(mensagem)`: onde a falha é relatada ao usuário.
    Hoje o único dono é `ui.core.document.layer_commands.LayerCommands`.
    """
    @wraps(function)
    def run(host, *args, **kwargs):
        from .manager import DocumentManager
        from ui.core.engine.registry import EngineRegistry
        manager = host.layer_manager
        if manager is None:
            return None
        document = DocumentManager.instance().active_document()
        backend = EngineRegistry.instance().get_backend()
        if document is None or backend is None or not backend.available:
            return function(host, *args, **kwargs)
        if manager is not document.layer_manager:
            raise RuntimeError("O painel não corresponde ao documento ativo.")
        if manager.backend_projection_restoring:
            return None
        try:
            with document.history.transaction(backend):
                return function(host, *args, **kwargs)
        except Exception as exc:
            host.show_status(str(exc))
            return False
    return run
