"""
PluginManager — Gerenciador do Ciclo de Vida e Descoberta de Plugins (Lumenia V2)
==============================================================================
Orquestra a descoberta estática e dinâmica de plugins, resolução de dependências,
ativação/desativação sem afetar plugins ativos durante escaneamento e desinstalação segura.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

from ui.infrastructure.logging import get_logger
from ui.core.plugins.base import BasePlugin
from ui.core.plugins.context import PluginContext
from ui.core.plugins.discovery import discover_compiled_plugins, register_module_plugins
from ui.core.plugins.lifecycle import PluginLifecycle
from ui.core.plugins.registry import ServiceRegistry
from ui.infrastructure.config.storage import read_object, save_with_backup
from ui.infrastructure.runtime_paths import is_packaged, writable_data_dir

logger = get_logger("PluginManager")

# Plugins embutidos (ui/plugins), importáveis como `ui.plugins.<...>`.
_BUILTIN_PLUGINS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "plugins")


class PluginManager:
    _instance = None

    @classmethod
    def instance(cls) -> PluginManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, plugins_dir: str | None = None) -> None:
        self._builtin_plugin_modules: tuple[str, ...] = ()
        self._builtin_plugin_classes: set[str] = set()
        if plugins_dir is None:
            if is_packaged():
                self.plugins_dir = str(writable_data_dir() / "plugins")
                from ui.plugins.builtin_registry import BUILTIN_PLUGIN_MODULES
                self._builtin_plugin_modules = BUILTIN_PLUGIN_MODULES
            else:
                candidate_dirs = [
                    os.path.join(os.path.dirname(sys.executable), "plugins"),
                    _BUILTIN_PLUGINS_DIR,
                ]
                self.plugins_dir = next((d for d in candidate_dirs if os.path.isdir(d)), candidate_dirs[0])
        else:
            self.plugins_dir = plugins_dir

        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)

        if self.plugins_dir not in sys.path:
            sys.path.insert(0, self.plugins_dir)

        self.context = PluginContext(ServiceRegistry.instance())

        config_root = writable_data_dir() if is_packaged() and plugins_dir is None else Path(self.plugins_dir)
        self.config_path = (os.environ.get("LUMENIA_PLUGINS_CONFIG_PATH") if plugins_dir is None else None) or str(config_root / "plugins_config.json")
        self.discovered_plugins = {}  # class_name -> plugin_class
        self.active_instances = {}    # class_name -> plugin_instance
        self.enabled_plugins_config = {}  # class_name -> bool
        self._activating_plugins: set[str] = set()

        self.load_config()

    def set_main_window(self, main_window) -> None:
        self.context.attach_main_window(main_window)
        logger.debug("[PluginManager] main_window injetado no PluginContext.")


    def load_config(self) -> None:
        for candidate in (self.config_path, self.config_path + ".bak"):
            if not os.path.exists(candidate):
                continue
            try:
                loaded = read_object(candidate)
                if any(not isinstance(name, str) or type(enabled) is not bool
                       for name, enabled in loaded.items()):
                    raise ValueError("plugins_config.json contém valores inválidos")
                self.enabled_plugins_config = dict(loaded)
                return
            except Exception as e:
                logger.error(f"Erro ao carregar plugins_config.json: {e}")
        self.enabled_plugins_config = {name: True for name in (
            "WorkspaceCore", "BrushPlugin", "ColorPlugin", "GeometryPlugin",
            "LayersPlugin", "NavigatorPlugin", "TelemetryPlugin",
        )}

    def save_config(self) -> bool:
        try:
            save_with_backup(self.config_path, self.enabled_plugins_config)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar plugins_config.json: {e}")
            return False

    def rescan_plugins(self) -> None:
        """Varre a pasta de plugins e atualiza discovered_plugins sem desativar os ativos."""
        self.discovered_plugins.clear()
        self._builtin_plugin_classes.clear()
        discover_compiled_plugins(
            self._builtin_plugin_modules, self.discovered_plugins, logger
        )
        self._builtin_plugin_classes.update(self.discovered_plugins)
        candidates: list[tuple[str, str]] = []

        for item in os.listdir(self.plugins_dir):
            if item.startswith(".") or item.startswith("__") or item == "plugins_config.json":
                continue

            item_path = os.path.join(self.plugins_dir, item)

            if os.path.isfile(item_path) and item.endswith(".py"):
                candidates.append((item[:-3], item_path))
            elif os.path.isdir(item_path):
                init_path = os.path.join(item_path, "__init__.py")
                if os.path.exists(init_path):
                    candidates.append((item, init_path))
                else:
                    try:
                        for sub_item in os.listdir(item_path):
                            if sub_item.startswith("__"):
                                continue
                            sub_path = os.path.join(item_path, sub_item)
                            sub_init = os.path.join(sub_path, "__init__.py")
                            if os.path.isdir(sub_path) and os.path.exists(sub_init):
                                candidates.append((sub_item, sub_init))
                    except PermissionError:
                        pass

        for module_name, file_path in candidates:
            try:
                plugin_dir = os.path.dirname(file_path)
                if plugin_dir not in sys.path:
                    sys.path.insert(0, plugin_dir)

                # 1. Tentar importar canonicamente: `ui.plugins.<...>` para os
                # embutidos; numa pasta externa, relativo à pasta-mãe dela.
                rel_path = os.path.relpath(file_path, self._package_root())
                parts = os.path.splitext(rel_path)[0].replace("\\", "/").split("/")
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                canonical_pkg = ".".join(parts)

                module = None
                try:
                    module = importlib.import_module(canonical_pkg)
                except Exception:
                    logger.debug(
                        "Import canônico de '%s' falhou; tentando spec_from_file_location.",
                        canonical_pkg, exc_info=True,
                    )

                # 2. Fallback: carregar via spec_from_file_location com submódulos registrados
                if module is None:
                    safe_mod_name = f"_plugin_{module_name.replace('-', '_')}"
                    sub_locations = [plugin_dir] if file_path.endswith("__init__.py") else None
                    spec = importlib.util.spec_from_file_location(
                        safe_mod_name, file_path, submodule_search_locations=sub_locations
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        if sub_locations:
                            module.__path__ = sub_locations
                        module.__package__ = safe_mod_name
                        sys.modules[safe_mod_name] = module
                        spec.loader.exec_module(module)

                if module:
                    register_module_plugins(
                        self.discovered_plugins, module, plugin_dir, file_path, logger
                    )
            except Exception as e:
                logger.error(f"Erro ao carregar o plugin '{module_name}': {e}")


    def _package_root(self) -> str:
        """Pasta a partir da qual o caminho de um plugin vira nome de módulo."""
        if os.path.normcase(os.path.abspath(self.plugins_dir)) == os.path.normcase(_BUILTIN_PLUGINS_DIR):
            return os.path.dirname(os.path.dirname(_BUILTIN_PLUGINS_DIR))
        return os.path.dirname(self.plugins_dir)

    def discover_plugins(self) -> None:
        """Executa a descoberta e ativação inicial no boot da aplicação."""
        self.rescan_plugins()

        # Cache de instâncias temporárias para metadados/prioridade no boot
        self._temp_plugin_cache: dict[str, BasePlugin] = {}

        try:
            load_order = self._resolve_load_order()
        except Exception as e:
            logger.critical(f"Erro na resolução de dependências dos plugins: {e}")
            load_order = list(self.discovered_plugins.keys())

        for name in load_order:
            cls = self.discovered_plugins[name]
            is_system = False
            if name in self._temp_plugin_cache:
                is_system = self._temp_plugin_cache[name].is_system_plugin()
            else:
                try:
                    temp_inst = cls()
                    is_system = temp_inst.is_system_plugin()
                except Exception as e:
                    logger.error(f"Erro ao verificar se {name} é plugin de sistema: {e}")

            if is_system or self.enabled_plugins_config.get(name, False):
                success = self.enable_plugin(name)
                if not success and is_system:
                    raise RuntimeError(f"FALHA CRÍTICA NO BOOT: O plugin de sistema '{name}' falhou ao ativar.")

        self._temp_plugin_cache.clear()

    def _resolve_load_order(self) -> list[str]:
        id_to_classname = {}
        for classname, cls in self.discovered_plugins.items():
            try:
                inst = cls()
                self._temp_plugin_cache[classname] = inst
                plugin_id = inst.get_metadata().id
                id_to_classname[plugin_id] = classname
            except Exception:
                logger.warning(
                    "Plugin '%s' não pôde ser instanciado para ler metadados; "
                    "fica fora da resolução de dependências.", classname, exc_info=True,
                )

        def get_priority_key(name):
            inst = self._temp_plugin_cache.get(name)
            if inst:
                try:
                    return inst.get_priority()
                except Exception:
                    logger.debug("get_priority() falhou em '%s'; usando 0.", name, exc_info=True)
            return 0

        sorted_names = sorted(self.discovered_plugins.keys(), key=get_priority_key, reverse=True)

        visited = {}
        order = []

        def dfs(name):
            if visited.get(name) == 0:
                raise ValueError(f"Dependência cíclica detectada no plugin: {name}")
            if visited.get(name) == 1:
                return

            visited[name] = 0

            inst = self._temp_plugin_cache.get(name)
            deps = []
            if inst:
                try:
                    deps = inst.get_metadata().dependencies
                except Exception:
                    deps = []

            for dep_id in deps:
                if dep_id in id_to_classname:
                    dep_classname = id_to_classname[dep_id]
                    dfs(dep_classname)
                else:
                    logger.warning(f"Plugin dependente '{dep_id}' (exigido por '{name}') não está instalado.")

            visited[name] = 1
            order.append(name)

        for name in sorted_names:
            if name not in visited:
                dfs(name)

        return order

    def enable_plugin(self, name: str) -> bool:
        return PluginLifecycle.enable(self, name, logger)

    def disable_plugin(self, name: str) -> bool:
        return PluginLifecycle.disable(self, name, logger)

    def get_all_discovered_plugins(self) -> list:
        plugins = []
        for name, cls in self.discovered_plugins.items():
            if name in self.active_instances:
                plugins.append(self.active_instances[name])
            else:
                try:
                    plugins.append(cls())
                except Exception as e:
                    logger.error(f"Erro ao instanciar metadados do plugin {name}: {e}")
        return plugins

    def is_system_plugin(self, class_name: str) -> bool:
        if class_name in self.active_instances:
            return self.active_instances[class_name].is_system_plugin()
        if class_name in self.discovered_plugins:
            try:
                return self.discovered_plugins[class_name]().is_system_plugin()
            except Exception:
                return False
        return False
    def load_plugin_from_source(self, zip_path: str) -> bool | None:
        from ui.core.plugins.package_installer import install_plugin_package
        return install_plugin_package(self, zip_path, logger)

    def _package_was_discovered(self, target_dir: str, manifest) -> bool:
        from ui.core.plugins.package_installer import package_was_discovered
        return package_was_discovered(self, target_dir, manifest, logger)

    def _quarantine_package(self, target_dir: str) -> None:
        from ui.core.plugins.package_installer import quarantine_package
        quarantine_package(self.plugins_dir, target_dir, logger)

    def _purge_module_from_sys(self, cls) -> None:
        from ui.core.plugins.package_installer import purge_module_from_sys
        purge_module_from_sys(cls, logger)

    def uninstall_plugin(self, name: str) -> bool:
        """Exclui/desinstala um plugin customizado do disco e da memória."""
        from ui.core.plugins.package_installer import uninstall_plugin_package
        return uninstall_plugin_package(self, name, logger)

