"""Static catalog for plugins compiled into a standalone Lumenia bundle.

The development runtime discovers source files dynamically. A compiled Nuitka
package has no source ``__init__.py`` files to enumerate, so its built-ins are
listed here while user-installed plugins remain discoverable from disk.
"""

BUILTIN_PLUGIN_MODULES = (
    "ui.plugins.system.workspace_core",
    "ui.plugins.panels.brush_plugin",
    "ui.plugins.panels.color_plugin",
    "ui.plugins.panels.geometry_plugin.plugin",
    "ui.plugins.panels.layers_plugin",
    "ui.plugins.panels.navigator_plugin",
    "ui.plugins.panels.recording_plugin",
    "ui.plugins.panels.telemetry_plugin",
)
