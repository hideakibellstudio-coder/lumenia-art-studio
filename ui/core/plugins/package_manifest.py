"""Contrato verificável para pacotes de plugins instalados externamente."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import re
from typing import Any, Mapping


PLUGIN_API_VERSION = 1
ALLOWED_PERMISSIONS = frozenset({
    "ui",
    "engine",
    "filesystem_read",
    "filesystem_write",
    "network",
})

_PLUGIN_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_DEPENDENCY_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class PackageManifestError(ValueError):
    """O pacote externo não satisfaz o contrato de instalação."""


@dataclass(frozen=True)
class PluginPackageManifest:
    """Manifesto validado antes de um pacote deixar a área de staging."""

    plugin_id: str
    version: str
    minimum_api_version: int
    dependencies: tuple[str, ...]
    permissions: tuple[str, ...]


def validate_package_manifest(raw: Any, package_dir: str) -> PluginPackageManifest:
    """Valida o schema e a integridade opcional de um pacote já extraído.

    A validação acontece antes da promoção atômica para ``plugins_dir``. As
    permissões são uma declaração de contrato para a interface de instalação;
    elas não tentam transformar o interpretador Python em um sandbox.
    """
    if not isinstance(raw, Mapping):
        raise PackageManifestError("manifest.json deve conter um objeto")

    plugin_id = _required_string(raw, "id")
    if not _PLUGIN_ID.fullmatch(plugin_id):
        raise PackageManifestError("id de plugin inválido")

    version = _required_string(raw, "version")
    if not _SEMVER.fullmatch(version):
        raise PackageManifestError("version deve usar SemVer (por exemplo, 1.0.0)")

    minimum_api_version = raw.get("minimum_api_version")
    if isinstance(minimum_api_version, bool) or not isinstance(minimum_api_version, int):
        raise PackageManifestError("minimum_api_version inteiro é obrigatório")
    if minimum_api_version < 1:
        raise PackageManifestError("minimum_api_version deve ser positivo")
    if minimum_api_version > PLUGIN_API_VERSION:
        raise PackageManifestError(
            f"plugin requer API {minimum_api_version}, disponível: {PLUGIN_API_VERSION}"
        )

    dependencies = _identifier_list(raw.get("dependencies"), "dependencies", plugin_id)
    permissions = _permission_list(raw.get("permissions"))
    _validate_entrypoint(raw.get("entrypoint", "__init__.py"), package_dir)
    _validate_integrity(raw.get("integrity"), package_dir)

    return PluginPackageManifest(
        plugin_id=plugin_id,
        version=version,
        minimum_api_version=minimum_api_version,
        dependencies=dependencies,
        permissions=permissions,
    )


def _required_string(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PackageManifestError(f"{key} é obrigatório")
    return value.strip()


def _identifier_list(value: Any, key: str, plugin_id: str | None = None) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise PackageManifestError(f"{key} deve ser uma lista de IDs")
    normalized = tuple(item.strip() for item in value)
    if any(not _DEPENDENCY_ID.fullmatch(item) for item in normalized):
        raise PackageManifestError(f"{key} contém ID inválido")
    if len(set(normalized)) != len(normalized):
        raise PackageManifestError(f"{key} não pode conter IDs repetidos")
    if plugin_id and plugin_id in normalized:
        raise PackageManifestError("plugin não pode depender de si próprio")
    return normalized


def _permission_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise PackageManifestError("permissions deve ser uma lista")
    normalized = tuple(item.strip() for item in value)
    if len(set(normalized)) != len(normalized):
        raise PackageManifestError("permissions não pode conter valores repetidos")
    unsupported = sorted(set(normalized) - ALLOWED_PERMISSIONS)
    if unsupported:
        raise PackageManifestError(f"permissions não suportadas: {', '.join(unsupported)}")
    return normalized


def _safe_relative_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or os.path.isabs(value):
        raise PackageManifestError(f"{field} deve ser um caminho relativo")
    normalized = os.path.normpath(value.replace("/", os.sep).replace("\\", os.sep))
    if normalized in (".", "..") or normalized.startswith(f"..{os.sep}"):
        raise PackageManifestError(f"{field} contém caminho inseguro")
    return normalized


def _package_file(package_dir: str, relative_path: str, field: str) -> str:
    root = os.path.abspath(package_dir)
    candidate = os.path.abspath(os.path.join(root, relative_path))
    try:
        inside_package = os.path.commonpath((root, candidate)) == root
    except ValueError:
        inside_package = False
    if not inside_package or not os.path.isfile(candidate):
        raise PackageManifestError(f"{field} não referencia um arquivo do pacote")
    return candidate


def _validate_entrypoint(value: Any, package_dir: str) -> None:
    relative_path = _safe_relative_path(value, "entrypoint")
    if relative_path != "__init__.py":
        raise PackageManifestError("entrypoint deve ser __init__.py")
    _package_file(package_dir, relative_path, "entrypoint")


def _validate_integrity(value: Any, package_dir: str) -> None:
    if value is None:
        return
    if not isinstance(value, Mapping) or set(value) != {"algorithm", "files"}:
        raise PackageManifestError("integrity deve conter algorithm e files")
    if value["algorithm"] != "sha256" or not isinstance(value["files"], Mapping):
        raise PackageManifestError("integrity deve usar sha256 e um mapa de arquivos")
    if not value["files"]:
        raise PackageManifestError("integrity.files não pode ficar vazio")

    for raw_path, expected in value["files"].items():
        relative_path = _safe_relative_path(raw_path, "integrity.files")
        if not isinstance(expected, str) or not _SHA256.fullmatch(expected):
            raise PackageManifestError("integrity.files contém checksum SHA-256 inválido")
        file_path = _package_file(package_dir, relative_path, "integrity.files")
        with open(file_path, "rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual.lower() != expected.lower():
            raise PackageManifestError(f"checksum inválido: {raw_path}")
