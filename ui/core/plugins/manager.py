"""
PluginManager — Gerenciador do Ciclo de Vida e Descoberta de Plugins (Lumenia V2)
==============================================================================
Orquestra a descoberta estática e dinâmica de plugins, resolução de dependências,
ativação/desativação sem afetar plugins ativos durante escaneamento e desinstalação segura.
"""

from __future__ import annotations

import inspect
import importlib.util
import json
import logging
import os
import shutil
import sys
import zipfile

from ui.core.logger import get_logger
from ui.core.plugins.base import BasePlugin
from ui.core.plugins.context import PluginContext
from ui.core.plugins.registry import ServiceRegistry

logger = get_logger("PluginManager")


class PluginManager:
    _instance = None

    @classmethod
    def instance(cls) -> PluginManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, plugins_dir: str | None = None) -> None:
        if plugins_dir is None:
            candidate_dirs = [
                os.path.join(os.path.dirname(sys.executable), "plugins"),
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                    "plugins",
                ),
            ]
            self.plugins_dir = next((d for d in candidate_dirs if os.path.isdir(d)), candidate_dirs[0])
        else:
            self.plugins_dir = plugins_dir

        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)

        if self.plugins_dir not in sys.path:
            sys.path.insert(0, self.plugins_dir)

        from ui.infrastructure.bridge_client.client import BridgeClient
        from ui.infrastructure.bridge_client.dispatcher import EngineDispatcher

        self.context = PluginContext(
            bridge_client=BridgeClient.instance(),
            dispatcher=EngineDispatcher.instance(),
        )
        self.context._service_registry = ServiceRegistry.instance()

        self.config_path = os.path.join(self.plugins_dir, "plugins_config.json")
        self.discovered_plugins = {}  # class_name -> plugin_class
        self.active_instances = {}    # class_name -> plugin_instance
        self.enabled_plugins_config = {}  # class_name -> bool

        self.load_config()

    def set_main_window(self, main_window) -> None:
        self.context._main_window = main_window
        logger.debug("[PluginManager] main_window injetado no PluginContext.")
        for name, instance in list(self.active_instances.items()):
            try:
                instance.initialize(self.context)
                instance.activate()
            except Exception as e:
                logger.error(f"Erro ao re-ativar plugin {name} no novo main_window: {e}")


    def load_config(self) -> None:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.enabled_plugins_config = json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar plugins_config.json: {e}")
                self.enabled_plugins_config = {}
        else:
            self.enabled_plugins_config = {}

    def save_config(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.enabled_plugins_config, f, indent=4)
        except Exception as e:
            logger.error(f"Erro ao salvar plugins_config.json: {e}")

    def rescan_plugins(self) -> None:
        """Varre a pasta de plugins e atualiza discovered_plugins sem desativar os ativos."""
        self.discovered_plugins.clear()
        candidates: list[tuple[str, str]] = []

        for item in os.listdir(self.plugins_dir):
            if item.startswith("__") or item == "plugins_config.json":
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

                # 1. Tentar importar canonicamente como submódulo do pacote 'plugins'
                rel_path = os.path.relpath(file_path, os.path.dirname(self.plugins_dir))
                parts = os.path.splitext(rel_path)[0].replace("\\", "/").split("/")
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                canonical_pkg = ".".join(parts)

                module = None
                try:
                    module = importlib.import_module(canonical_pkg)
                except Exception:
                    pass

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
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BasePlugin)
                            and attr is not BasePlugin
                        ):
                            attr._plugin_dir = plugin_dir
                            self.discovered_plugins[attr_name] = attr
                            logger.info(f"Plugin descoberto: {attr_name} (em {file_path})")
            except Exception as e:
                logger.error(f"Erro ao carregar o plugin '{module_name}': {e}")


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
                pass

        def get_priority_key(name):
            inst = self._temp_plugin_cache.get(name)
            if inst:
                try:
                    return inst.get_priority()
                except Exception:
                    pass
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
        if name not in self.discovered_plugins:
            return False

        if name in self.active_instances:
            return True

        try:
            cls = self.discovered_plugins[name]
            instance = cls()

            instance.initialize(self.context)
            instance.activate()

            self.active_instances[name] = instance
            self.enabled_plugins_config[name] = True
            self.save_config()
            logger.info(f"Plugin ativado com contexto: {name}")
            return True
        except Exception as e:
            logger.error(f"Erro ao ativar plugin {name}: {e}")
            return False

    def disable_plugin(self, name: str) -> bool:
        if name not in self.active_instances:
            return False

        try:
            instance = self.active_instances[name]

            if instance.is_system_plugin():
                logger.warning(f"Tentativa de desativar o plugin de sistema '{name}' bloqueada.")
                return False

            instance.deactivate()
            instance.shutdown()

            del self.active_instances[name]
            self.enabled_plugins_config[name] = False
            self.save_config()
            logger.info(f"Plugin desativado: {name}")
            return True
        except Exception as e:
            logger.error(f"Erro ao desativar plugin {name}: {e}")
            return False

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
        if not zipfile.is_zipfile(zip_path):
            return None

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(self.plugins_dir)
            self.rescan_plugins()
            return True
        except Exception as e:
            logger.error(f"Erro ao extrair plugin .zip: {e}")
            return None

    def _purge_module_from_sys(self, cls) -> None:
        """Expurga as referências do módulo compilado na memória do sys.modules."""
        try:
            mod_name = cls.__module__
            for key in list(sys.modules.keys()):
                if key == mod_name or key.endswith(f".{mod_name}") or mod_name.endswith(f".{key}"):
                    sys.modules.pop(key, None)
                    logger.debug(f"Módulo expurgado da memória sys.modules: {key}")
        except Exception as e:
            logger.warning(f"Erro ao expurgar módulo da memória: {e}")

    def uninstall_plugin(self, name: str) -> bool:
        """Exclui/desinstala um plugin customizado do disco e da memória."""
        if self.is_system_plugin(name):
            logger.warning(f"Tentativa de desinstalar plugin de sistema '{name}' foi bloqueada.")
            return False

        if name in self.active_instances:
            self.disable_plugin(name)

        cls = self.discovered_plugins.get(name)
        if not cls:
            logger.error(f"Não foi possível encontrar a classe do plugin '{name}' para desinstalação.")
            return False

        try:
            # 1. Obtém a pasta física do plugin (vínculo direto _plugin_dir da classe/instância)
            plugin_dir = getattr(cls, "_plugin_dir", None)
            if not plugin_dir:
                try:
                    file_path = inspect.getfile(cls)
                    if file_path:
                        plugin_dir = os.path.dirname(file_path)
                except Exception:
                    pass

            logger.info(f"Desinstalando plugin '{name}' | Pasta identificada: {plugin_dir}")

            # 2. Purga referências em memória sys.modules
            self._purge_module_from_sys(cls)

            # 3. Força a coleta de lixo para liberar arquivos travados no Windows
            import gc
            gc.collect()

            # 4. Remove o diretório físico do disco
            if plugin_dir and os.path.exists(plugin_dir):
                norm_plugin_dir = os.path.normcase(os.path.abspath(plugin_dir))
                norm_root = os.path.normcase(os.path.abspath(self.plugins_dir))

                if norm_plugin_dir.startswith(norm_root) and norm_plugin_dir != norm_root:
                    def _on_rm_error(func, path, exc_info):
                        import stat
                        try:
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        except Exception:
                            pass

                    shutil.rmtree(plugin_dir, onerror=_on_rm_error)
                    logger.info(f"🗑 Diretório do plugin '{name}' excluído com sucesso do disco: {plugin_dir}")

            # 5. Limpa referências internas
            self.discovered_plugins.pop(name, None)
            self.active_instances.pop(name, None)
            self.enabled_plugins_config.pop(name, None)
            self.save_config()

            # 6. Atualiza o escaneamento do disco
            self.rescan_plugins()
            return True
        except Exception as e:
            logger.error(f"Erro ao desinstalar plugin {name}: {e}")
            return False

