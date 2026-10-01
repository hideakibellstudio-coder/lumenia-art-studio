"""Session-scoped recovery snapshots, independent of the user's saved file."""

import logging
import hashlib
import uuid
import weakref
from pathlib import Path
from PySide6.QtCore import QLockFile

from .save_capture import CaptureEngine, SaveCapture, capture_document
from .serializer import DocumentSerializer, DocumentFormatError


class RecoveryStore:
    _instances = weakref.WeakSet()

    def __init__(self, directory):
        self.directory = Path(directory)
        self.session = uuid.uuid4().hex
        self.revisions = {}
        # Gravações de recuperação em andamento, e as que perderam o sentido no meio do caminho
        # (o documento foi salvo ou fechado enquanto a cópia era gravada).
        self._inflight: set[str] = set()
        self._cancelled: set[str] = set()
        self._lock = None
        self._instances.add(self)

    @classmethod
    def close_all(cls):
        for store in list(cls._instances):
            store.close()

    def path_for(self, uid):
        key = hashlib.sha256(str(uid).encode()).hexdigest()[:24]
        return self.directory / f"{self.session}-{key}.lmn"

    def prepare(self, document, backend: CaptureEngine) -> SaveCapture | None:
        """A primeira metade de gravar a cópia (na thread do documento); None se não há o que gravar.

        Não há o que gravar quando o documento está limpo, já tem uma cópia desta revisão, ou
        uma gravação dele já está em andamento (a próxima volta pega o que mudou)."""
        if not document.is_dirty or self.revisions.get(document.uid) == document.revision:
            return None
        if document.uid in self._inflight:
            return None
        self._reserve_session()
        capture = capture_document(document, backend, self.path_for(document.uid))
        self._inflight.add(document.uid)
        return capture

    def finish(self, capture: SaveCapture, written: bool) -> None:
        """A segunda metade terminou (de volta na thread do documento)."""
        self._inflight.discard(capture.uid)
        if capture.uid in self._cancelled:
            # O documento foi salvo ou fechado durante a gravação: a cópia que acabou de sair
            # seria oferecida na próxima abertura de um documento que não precisa dela.
            self._cancelled.discard(capture.uid)
            self._remove_files(capture.uid)
        elif written:
            self.revisions[capture.uid] = capture.revision

    def capture(self, document, backend: CaptureEngine):
        """Prepara e grava de uma vez, na thread de quem chama (a recuperação da interface usa as metades)."""
        capture = self.prepare(document, backend)
        if capture is None:
            return False
        try:
            DocumentSerializer.write(capture)
        except Exception:
            self.finish(capture, written=False)
            raise
        self.finish(capture, written=True)
        return True

    def _reserve_session(self):
        if self._lock is None:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._lock = QLockFile(str(self.directory / f"{self.session}.lock"))
            self._lock.setStaleLockTime(0)
            if not self._lock.tryLock(0):
                self._lock = None
                raise OSError("não foi possível reservar a sessão de recuperação")

    def _remove_files(self, uid):
        self.path_for(uid).unlink(missing_ok=True)
        Path(str(self.path_for(uid)) + ".bak").unlink(missing_ok=True)

    def discard(self, uid):
        if uid in self._inflight:
            self._cancelled.add(uid)
        self._remove_files(uid)
        self.revisions.pop(uid, None)

    def candidates(self):
        candidates = []
        sources = set(self.directory.glob("*.lmn"))
        sources.update(Path(str(p)[:-4]) for p in self.directory.glob("*.lmn.bak"))
        for path in sorted(sources):
            session = path.stem.split("-", 1)[0]
            if session == self.session:
                continue
            lock = QLockFile(str(self.directory / f"{session}.lock"))
            lock.setStaleLockTime(0)
            if lock.tryLock(0):
                try:
                    for candidate in (path, Path(str(path) + ".bak")):
                        try:
                            DocumentSerializer.read(candidate)
                        except (OSError, DocumentFormatError):
                            continue
                        candidates.append(candidate)
                        break
                finally:
                    lock.unlock()
        return candidates

    def close(self):
        if self._lock is not None:
            self._lock.unlock()
            self._lock = None

    def discard_candidate(self, path):
        """Remove both old generations only after a new snapshot is durable."""
        path = Path(path).resolve()
        if path.parent != self.directory.resolve():
            raise ValueError("cópia de recuperação fora da pasta da sessão")
        primary = Path(str(path)[:-4]) if path.name.endswith(".lmn.bak") else path
        if primary.suffix != ".lmn":
            raise ValueError("cópia de recuperação inválida")
        primary.unlink(missing_ok=True)
        Path(str(primary) + ".bak").unlink(missing_ok=True)

    def __del__(self):
        # MainWindow instances can be collected during Qt teardown without
        # reaching the normal close path. Never leave a process-owned lock in
        # the temporary recovery profile in that case.
        try:
            self.close()
        except Exception:  # noqa: BLE001 -- destrutor: nunca propagar, mas deixar rastro
            logging.getLogger(__name__).debug("RecoveryStore: falha ao fechar no destrutor", exc_info=True)
