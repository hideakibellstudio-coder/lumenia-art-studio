"""Keep application preferences and recovery files out of the real user profile."""

import os
import tempfile
import gc
from pathlib import Path

_profile = tempfile.TemporaryDirectory(prefix="lumenia-test-profile-")
_previous = os.environ.get("LUMENIA_CONFIG_PATH")
_previous_plugins = os.environ.get("LUMENIA_PLUGINS_CONFIG_PATH")
os.environ["LUMENIA_PLUGINS_CONFIG_PATH"] = str(Path(_profile.name) / "plugins_config.json")
os.environ["LUMENIA_CONFIG_PATH"] = str(Path(_profile.name) / "config.json")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("OMP_NUM_THREADS", "2")


def pytest_unconfigure(config):
    # Ensure MainWindow-owned recovery stores release QLockFile before the
    # temporary profile is removed on Windows (open handles cannot be unlinked).
    try:
        from PySide6 import QtWidgets
        QtWidgets.QApplication.closeAllWindows()
        QtWidgets.QApplication.processEvents()
    except Exception:
        pass
    try:
        from ui.core.document.recovery import RecoveryStore
        RecoveryStore.close_all()
    except Exception:
        pass
    gc.collect()
    if _previous is None:
        os.environ.pop("LUMENIA_CONFIG_PATH", None)
    else:
        os.environ["LUMENIA_CONFIG_PATH"] = _previous
    _profile.cleanup()
    if _previous_plugins is None:
        os.environ.pop("LUMENIA_PLUGINS_CONFIG_PATH", None)
    else:
        os.environ["LUMENIA_PLUGINS_CONFIG_PATH"] = _previous_plugins
