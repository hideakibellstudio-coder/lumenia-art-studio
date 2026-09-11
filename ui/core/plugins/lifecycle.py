"""Transações de ativação e encerramento de plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ui.core.plugins.base import BasePlugin

if TYPE_CHECKING:
    from ui.core.plugins.manager import PluginManager


class PluginLifecycle:
    """Executa hooks em ordem e compensa ativações interrompidas."""

    @classmethod
    def enable(cls, manager: PluginManager, name: str, logger: Any) -> bool:
        if name not in manager.discovered_plugins:
            return False
        if name in manager.active_instances:
            return True
        if name in manager._activating_plugins:
            logger.error(f"Dependência cíclica durante ativação do plugin '{name}'.")
            return False

        instance = None
        activation_started = False
        manager._activating_plugins.add(name)
        try:
            instance = manager.discovered_plugins[name]()
            if not cls._activate_dependencies(manager, name, instance, logger):
                cls._teardown(name, instance, logger, deactivate=False)
                return False

            instance.initialize(manager.context)
            activation_started = True
            instance.activate()
            manager.active_instances[name] = instance
            manager.enabled_plugins_config[name] = True
            manager.save_config()
            logger.info(f"Plugin ativado com contexto: {name}")
            return True
        except Exception as error:
            logger.error(f"Erro ao ativar plugin {name}: {error}")
            if instance is not None:
                cls._teardown(name, instance, logger, deactivate=activation_started)
            return False
        finally:
            manager._activating_plugins.discard(name)

    @classmethod
    def disable(cls, manager: PluginManager, name: str, logger: Any) -> bool:
        if name not in manager.active_instances:
            return False
        instance = manager.active_instances[name]
        if instance.is_system_plugin():
            logger.warning(f"Tentativa de desativar o plugin de sistema '{name}' bloqueada.")
            return False

        clean = cls._teardown(name, instance, logger, deactivate=True)
        # Nunca retenha um plugin parcialmente encerrado como se continuasse ativo.
        manager.active_instances.pop(name, None)
        manager.enabled_plugins_config[name] = False
        manager.save_config()
        if clean:
            logger.info(f"Plugin desativado: {name}")
        return clean

    @classmethod
    def _activate_dependencies(
        cls, manager: PluginManager, name: str, instance: BasePlugin, logger: Any
    ) -> bool:
        try:
            dependencies = instance.get_metadata().dependencies
        except Exception as error:
            logger.error(f"Não foi possível ler dependências de '{name}': {error}")
            return False

        for dependency_id in dependencies:
            dependency_name = cls._plugin_name_for_id(manager, dependency_id, logger)
            if dependency_name is None:
                logger.error(f"Dependência '{dependency_id}' ausente para '{name}'.")
                return False
            if dependency_name == name or not cls.enable(manager, dependency_name, logger):
                logger.error(f"Dependência '{dependency_id}' não foi ativada para '{name}'.")
                return False
        return True

    @staticmethod
    def _plugin_name_for_id(manager: PluginManager, plugin_id: str, logger: Any) -> str | None:
        for class_name, plugin_class in manager.discovered_plugins.items():
            instance = manager.active_instances.get(class_name)
            try:
                metadata = (instance or plugin_class()).get_metadata()
                if metadata.id == plugin_id:
                    return class_name
            except Exception as error:
                logger.warning(f"Não foi possível ler metadados de '{class_name}': {error}")
        return None

    @staticmethod
    def _teardown(name: str, instance: BasePlugin, logger: Any, *, deactivate: bool) -> bool:
        clean = True
        for hook_name, should_run in (("deactivate", deactivate), ("shutdown", True), ("dispose", True)):
            if not should_run:
                continue
            try:
                getattr(instance, hook_name)()
            except Exception as error:
                clean = False
                logger.error(f"Erro em {hook_name} do plugin '{name}': {error}")
        return clean
