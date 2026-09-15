"""One timeline for native pixels and the document's layer metadata.

Native steps own COW layer snapshots. Python only associates stable UIDs and
view metadata with the native step ID; it never guesses identity from names.
"""

from contextlib import contextmanager
from copy import deepcopy
from functools import wraps


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

    def bind_projection_identities(self, backend):
        """Bind immutable document UIDs to the aligned native layer stack."""
        manager = self.document.layer_manager
        if backend.get_drawing_layer_count() != len(manager.layers):
            raise RuntimeError("não é possível vincular identidades em pilhas divergentes")
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
            for index, layer in enumerate(layers):
                if backend.is_group(index) != layer.is_group or backend.is_filter_layer(index) != layer.is_filter:
                    raise RuntimeError("Operação cancelada: tipo de camada divergente.")
                backend.set_layer_name(index, layer.name)
                backend.set_layer_opacity(index, layer.opacity)
                backend.set_layer_blend_mode(index, layer.blend_mode)
                backend.set_layer_visibility(index, layer.visible)
                backend.set_layer_lock(index, layer.locked)
                backend.set_layer_alpha_lock(index, layer.alpha_locked)
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
    """Wrap an entire UI action, including both model and backend mutations."""
    @wraps(function)
    def run(host, *args, **kwargs):
        from .manager import DocumentManager
        from ui.core.engine.registry import EngineRegistry
        dm = getattr(host, "dm", None) or DocumentManager.instance()
        document = dm.active_document()
        backend = EngineRegistry.instance().get_backend()
        if document is None or backend is None or not backend.available:
            return function(host, *args, **kwargs)
        manager = getattr(host, "layer_manager", getattr(host, "manager", document.layer_manager))
        if manager is not document.layer_manager:
            raise RuntimeError("O painel não corresponde ao documento ativo.")
        if manager.backend_projection_restoring:
            return None
        try:
            with document.history.transaction(backend):
                return function(host, *args, **kwargs)
        except Exception as exc:
            if hasattr(host, "status_bar"):
                host.status_bar.showMessage(str(exc), 5000)
            elif hasattr(host, "_show_status"):
                host._show_status(str(exc))
            else:
                raise
            return False
    return run
