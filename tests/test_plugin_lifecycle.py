from PySide6.QtCore import QObject, Signal

from ui.plugins.system.workspace_core.workspace.panel_connections import PanelConnections
from ui.core.plugins.base import BasePlugin
from ui.core.plugins.manager import PluginManager
from ui.core.plugins.metadata import PluginMetadata


class _TrackingPlugin(BasePlugin):
    events = []
    plugin_id = "tracking"
    dependencies = []
    fail_activation = False
    fail_deactivation = False

    def get_metadata(self):
        return PluginMetadata(
            id=self.plugin_id,
            name=self.plugin_id,
            version="1.0.0",
            author="tests",
            description="Lifecycle test plugin",
            dependencies=list(self.dependencies),
        )

    def initialize(self, context):
        super().initialize(context)
        self.events.append((self.plugin_id, "initialize"))

    def activate(self):
        self.events.append((self.plugin_id, "activate"))
        if self.fail_activation:
            raise RuntimeError("activation failed")

    def deactivate(self):
        self.events.append((self.plugin_id, "deactivate"))
        if self.fail_deactivation:
            raise RuntimeError("deactivation failed")

    def shutdown(self):
        self.events.append((self.plugin_id, "shutdown"))

    def dispose(self):
        self.events.append((self.plugin_id, "dispose"))


class _DependencyPlugin(_TrackingPlugin):
    plugin_id = "dependency"


class _ConsumerPlugin(_TrackingPlugin):
    plugin_id = "consumer"
    dependencies = ["dependency"]


class _FailingPlugin(_TrackingPlugin):
    plugin_id = "failing"
    fail_activation = True


class _CleanupFailingPlugin(_TrackingPlugin):
    plugin_id = "cleanup-failing"
    fail_deactivation = True


def _manager(tmp_path, plugins):
    _TrackingPlugin.events = []
    manager = PluginManager(str(tmp_path / "plugins"))
    manager.discovered_plugins = plugins
    return manager


def test_activation_orders_dependencies_and_does_not_reactivate_on_window_update(tmp_path):
    manager = _manager(tmp_path, {
        "Consumer": _ConsumerPlugin,
        "Dependency": _DependencyPlugin,
    })
    assert manager.enable_plugin("Consumer") is True
    assert _TrackingPlugin.events == [
        ("dependency", "initialize"),
        ("dependency", "activate"),
        ("consumer", "initialize"),
        ("consumer", "activate"),
    ]

    manager.set_main_window(object())
    assert len(_TrackingPlugin.events) == 4


def test_failed_activation_runs_compensating_cleanup(tmp_path):
    manager = _manager(tmp_path, {"Failing": _FailingPlugin})
    assert manager.enable_plugin("Failing") is False
    assert _TrackingPlugin.events == [
        ("failing", "initialize"),
        ("failing", "activate"),
        ("failing", "deactivate"),
        ("failing", "shutdown"),
        ("failing", "dispose"),
    ]
    assert not manager.active_instances


def test_disable_runs_remaining_cleanup_after_hook_failure(tmp_path):
    manager = _manager(tmp_path, {"CleanupFailing": _CleanupFailingPlugin})
    assert manager.enable_plugin("CleanupFailing") is True
    assert manager.disable_plugin("CleanupFailing") is False
    assert _TrackingPlugin.events[-3:] == [
        ("cleanup-failing", "deactivate"),
        ("cleanup-failing", "shutdown"),
        ("cleanup-failing", "dispose"),
    ]
    assert "CleanupFailing" not in manager.active_instances
    assert manager.enabled_plugins_config["CleanupFailing"] is False


class _SignalSource(QObject):
    changed = Signal()


class _Counter:
    def __init__(self):
        self.calls = 0

    def on_changed(self):
        self.calls += 1


def test_panel_connections_are_removed_before_panel_reuse():
    panels = PanelConnections()
    counter = _Counter()
    source = _SignalSource()
    signal = source.changed
    panels.register("panel", object())
    panels.bind("panel", signal, counter.on_changed)
    panels.bind("panel", signal, counter.on_changed)
    signal.emit()
    assert counter.calls == 1

    panels.release("panel")
    signal.emit()
    assert counter.calls == 1
    assert panels.widget("panel") is None

    panels.register("panel", object())
    panels.bind("panel", signal, counter.on_changed)
    signal.emit()
    assert counter.calls == 2
