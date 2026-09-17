"""Static catalog for plugins compiled into a standalone Lumenia bundle.

The development runtime discovers source files dynamically. A compiled Nuitka
package has no source ``__init__.py`` files to enumerate, so its built-ins are
listed here while user-installed plugins remain discoverable from disk.
"""

BUILTIN_PLUGIN_MODULES = (
    "plugins.system.workspace_core",
    "plugins.ui.brush_plugin",
    "plugins.ui.color_plugin",
    "plugins.ui.geometry_plugin.plugin",
    "plugins.ui.layers_plugin",
    "plugins.ui.navigator_plugin",
    "plugins.ui.telemetry_plugin",
)
