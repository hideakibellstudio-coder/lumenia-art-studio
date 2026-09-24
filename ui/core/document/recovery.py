"""Session-scoped recovery snapshots, independent of the user's saved file."""

import logging
import hashlib
import uuid
import weakref
from pathlib import Path
from PySide6.QtCore import QLockFile

from .serializer import DocumentSerializer, DocumentFormatError


class RecoveryStore:
    _instances = weakref.WeakSet()

    def __init__(self, directory):
        self.directory = Path(directory)
        self.session = uuid.uuid4().hex
        self.revisions = {}
        self._lock = None
        self._instances.add(self)

    @classmethod
    def close_all(cls):
        for store in list(cls._instances):
            store.close()

    def path_for(self, uid):
        key = hashlib.sha256(str(uid).encode()).hexdigest()[:24]
        return self.directory / f"{self.session}-{key}.lmn"

    def capture(self, document, backend):
        if not document.is_dirty or self.revisions.get(document.uid) == document.revision:
            return False
        if self._lock is None:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._lock = QLockFile(str(self.directory / f"{self.session}.lock"))
            self._lock.setStaleLockTime(0)
            if not self._lock.tryLock(0):
                self._lock = None
                raise OSError("não foi possível reservar a sessão de recuperação")
        DocumentSerializer.save(document, backend, self.path_for(document.uid))
        self.revisions[document.uid] = document.revision
        return True

    def discard(self, uid):
        self.path_for(uid).unlink(missing_ok=True)
        Path(str(self.path_for(uid)) + ".bak").unlink(missing_ok=True)
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
