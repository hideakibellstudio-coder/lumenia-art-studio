"""
PackageInstaller — Instalação, Validação e Desinstalação Segura de Pacotes de Plugins
=====================================================================================
Extrai pacotes .zip em staging seguro, valida integridade e manifest.json,
promove para a pasta de plugins, gerencia quarentena e remoção limpa do disco e sys.modules.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import shutil
import sys
import tempfile
import uuid
import zipfile
from typing import TYPE_CHECKING, Any

from ui.core.plugins.package_manifest import validate_package_manifest

if TYPE_CHECKING:
    from ui.core.plugins.manager import PluginManager


def install_plugin_package(
    manager: PluginManager, zip_path: str, logger: logging.Logger
) -> bool | None:
    """Extrai, valida e promove um arquivo de plugin .zip para a pasta de plugins."""
    if not zipfile.is_zipfile(zip_path):
        return None

    staging = None
    target_dir = None
    promoted = False
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            root = os.path.abspath(manager.plugins_dir)
            if len(zip_ref.infolist()) > 10000:
                raise ValueError("Pacote com entradas demais")
            staging = tempfile.mkdtemp(prefix=".plugin-staging-", dir=root)
            total_size = 0
            seen_paths = set()
            for member in zip_ref.infolist():
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError(f"Symlink não permitido no pacote: {member.filename}")
                normalized_member = member.filename.replace("\\", "/").rstrip("/")
                if normalized_member and normalized_member in seen_paths:
                    raise ValueError(f"Entrada duplicada no pacote: {member.filename}")
                seen_paths.add(normalized_member)
                # Reject absolute paths and traversal before touching disk.
                target = os.path.abspath(os.path.join(root, member.filename))
                if os.path.commonpath((root, target)) != root:
                    raise ValueError(f"Caminho inseguro no pacote: {member.filename}")
                if member.filename.replace("\\", "/").startswith("/"):
                    raise ValueError(f"Caminho absoluto no pacote: {member.filename}")
                total_size += member.file_size
                if total_size > 512 * 1024 * 1024:
                    raise ValueError("Pacote excede 512 MiB")
                staged_target = os.path.abspath(os.path.join(staging, member.filename))
                if os.path.commonpath((staging, staged_target)) != staging:
                    raise ValueError(f"Caminho inseguro no staging: {member.filename}")
                if member.is_dir():
                    os.makedirs(staged_target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(staged_target), exist_ok=True)
                    with zip_ref.open(member, "r") as src, open(staged_target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
            manifest_path = os.path.join(staging, "manifest.json")
            source_dir = staging
            if not os.path.exists(manifest_path):
                package_dirs = [
                    name for name in os.listdir(staging)
                    if os.path.isdir(os.path.join(staging, name))
                ]
                if len(package_dirs) == 1:
                    source_dir = os.path.join(staging, package_dirs[0])
                    manifest_path = os.path.join(source_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                raise ValueError("Pacote sem manifest.json")
            with open(manifest_path, encoding="utf-8") as stream:
                manifest = validate_package_manifest(json.load(stream), source_dir)
            if source_dir != staging and os.path.basename(source_dir) != manifest.plugin_id:
                raise ValueError("diretório do pacote deve corresponder ao id do manifesto")

            target_dir = os.path.join(root, manifest.plugin_id)
            if os.path.exists(target_dir):
                raise ValueError(f"Plugin já instalado: {manifest.plugin_id}")
            os.replace(source_dir, target_dir)
            promoted = True
        manager.rescan_plugins()
        if not package_was_discovered(manager, target_dir, manifest, logger):
            raise RuntimeError("pacote promovido não expõe o contrato BasePlugin declarado")
        return True
    except Exception as e:
        if promoted and target_dir and os.path.isdir(target_dir):
            quarantine_package(manager.plugins_dir, target_dir, logger)
            manager.rescan_plugins()
        logger.error(f"Erro ao extrair plugin .zip: {e}")
        return None
    finally:
        if staging and os.path.isdir(staging):
            shutil.rmtree(staging, ignore_errors=True)


def package_was_discovered(
    manager: PluginManager, target_dir: str, manifest: Any, logger: logging.Logger
) -> bool:
    """Confirma classe carregável e equivalência com o manifesto promovido."""
    target = os.path.normcase(os.path.abspath(target_dir))
    for plugin_class in manager.discovered_plugins.values():
        plugin_dir = getattr(plugin_class, "_plugin_dir", "")
        try:
            if os.path.normcase(os.path.abspath(plugin_dir)) != target:
                continue
            metadata = plugin_class().get_metadata()
            if metadata.id != manifest.plugin_id:
                continue
            if tuple(metadata.dependencies) != manifest.dependencies:
                logger.error("Dependências do manifesto e do plugin não coincidem.")
                return False
            return True
        except (TypeError, OSError, ValueError) as error:
            logger.error(f"Não foi possível validar plugin promovido: {error}")
            continue
    return False


def quarantine_package(plugins_dir: str, target_dir: str, logger: logging.Logger) -> None:
    """Retira uma promoção inválida da árvore que pode ser descoberta."""
    quarantine_root = os.path.join(plugins_dir, ".plugin-quarantine")
    os.makedirs(quarantine_root, exist_ok=True)
    base_name = os.path.basename(target_dir)
    destination = os.path.join(quarantine_root, f"{base_name}-{uuid.uuid4().hex}")
    try:
        os.replace(target_dir, destination)
        logger.warning(f"Pacote de plugin movido para quarentena: {destination}")
    except OSError as error:
        logger.error(f"Não foi possível colocar pacote inválido em quarentena: {error}")


def purge_module_from_sys(cls: Any, logger: logging.Logger) -> None:
    """Expurga as referências do módulo compilado na memória do sys.modules."""
    try:
        mod_name = cls.__module__
        for key in list(sys.modules.keys()):
            if key == mod_name or key.endswith(f".{mod_name}") or mod_name.endswith(f".{key}"):
                sys.modules.pop(key, None)
                logger.debug(f"Módulo expurgado da memória sys.modules: {key}")
    except Exception as e:
        logger.warning(f"Erro ao expurgar módulo da memória: {e}")


def uninstall_plugin_package(
    manager: PluginManager, name: str, logger: logging.Logger
) -> bool:
    """Exclui/desinstala um plugin customizado do disco e da memória."""
    if name in manager._builtin_plugin_classes or manager.is_system_plugin(name):
        logger.warning(f"Tentativa de desinstalar plugin de sistema '{name}' foi bloqueada.")
        return False

    if name in manager.active_instances:
        manager.disable_plugin(name)

    cls = manager.discovered_plugins.get(name)
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
            except (TypeError, OSError):
                pass  # classe sem arquivo de origem (embutida/compilada)

        logger.info(f"Desinstalando plugin '{name}' | Pasta identificada: {plugin_dir}")

        # 2. Purga referências em memória sys.modules
        purge_module_from_sys(cls, logger)

        # 3. Força a coleta de lixo para liberar arquivos travados no Windows
        import gc
        gc.collect()

        # 4. Remove o diretório físico do disco
        if plugin_dir and os.path.exists(plugin_dir):
            norm_plugin_dir = os.path.normcase(os.path.abspath(plugin_dir))
            norm_root = os.path.normcase(os.path.abspath(manager.plugins_dir))

            try:
                inside_root = os.path.commonpath((norm_root, norm_plugin_dir)) == norm_root
            except ValueError:
                inside_root = False
            if inside_root and norm_plugin_dir != norm_root:
                def _on_rm_error(func, path, exc_info):
                    import stat
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except OSError as exc:
                        logging.getLogger(__name__).warning("Desinstalação: não foi possível remover %s (%s)", path, exc)

                shutil.rmtree(plugin_dir, onerror=_on_rm_error)
                logger.info(f"Diretório do plugin '{name}' excluído com sucesso do disco: {plugin_dir}")

        # 5. Limpa referências internas
        manager.discovered_plugins.pop(name, None)
        manager.active_instances.pop(name, None)
        manager.enabled_plugins_config.pop(name, None)
        manager.save_config()

        # 6. Atualiza o escaneamento do disco
        manager.rescan_plugins()
        return True
    except Exception as e:
        logger.error(f"Erro ao desinstalar plugin {name}: {e}")
        return False
