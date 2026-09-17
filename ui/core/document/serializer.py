"""Persistência do formato editável nativo do Lumenia.

O formato é um ZIP versionado com manifesto JSON e snapshots RGBA por camada.
Os buffers são copiados antes da escrita para não depender da vida útil de
memoryviews expostos pelo backend.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Any
from .document import Document
from .local_layer import LocalLayer
from .schema import CURRENT_VERSION, DocumentFormatError, encode_guides, migrate, validate_auxiliary


class DocumentSerializer:
    FORMAT_ID = "lmn"
    FORMAT_VERSION = CURRENT_VERSION
    MAX_MANIFEST_BYTES = 8 * 1024 * 1024
    MAX_PAYLOAD_BYTES = 2 * 1024 * 1024 * 1024

    @staticmethod
    def _color_tuple(color: Any) -> list[int]:
        return [int(color.red()), int(color.green()), int(color.blue()), int(color.alpha())]

    @classmethod
    def save(cls, document: Document, backend, path: str | os.PathLike[str]) -> str:
        if not backend or not getattr(backend, "available", False):
            raise DocumentFormatError("motor indisponível; salvamento cancelado para preservar o documento")
        context = getattr(backend, "get_active_document_context", None)
        if context and context() != document.uid:
            raise DocumentFormatError("contexto ativo não corresponde ao documento")
        if getattr(backend, "is_transform_active", lambda: False)():
            raise DocumentFormatError("confirme ou cancele a transformação antes de salvar")
        history = getattr(document, "history", None)
        if history is not None and hasattr(history, "assert_projection"):
            try:
                history.assert_projection(backend)
            except RuntimeError as exc:
                raise DocumentFormatError(str(exc)) from exc
        if document.width * document.height * 4 > min(cls.MAX_PAYLOAD_BYTES, 2**31 - 1):
            raise DocumentFormatError("dimensões excedem o limite do motor")
        target = Path(path).expanduser().resolve()
        if target.suffix.lower() != ".lmn":
            target = target.with_suffix(".lmn")
        target.parent.mkdir(parents=True, exist_ok=True)

        layers: list[dict[str, Any]] = []
        payloads: dict[str, bytes] = {}
        manager = document.layer_manager
        expected_size = int(document.width) * int(document.height) * 4
        layer: LocalLayer
        for index, layer in enumerate(manager.layers):
            entry: dict[str, Any] = {
                "uid": int(layer.uid),
                "name": str(layer.name),
                "parent_uid": layer.parent_uid,
                "is_group": bool(layer.is_group),
                "is_filter": bool(layer.is_filter),
                "visible": bool(layer.visible),
                "locked": bool(layer.locked),
                "opacity": float(layer.opacity),
                "blend_mode": layer.blend_mode,
                "alpha_locked": bool(layer.alpha_locked),
                "clipping_mask": bool(layer.clipping_mask),
            }
            if backend and getattr(backend, "available", False):
                raw = backend.get_layer_pixel_buffer(index)
                if not raw and not layer.is_group and not layer.is_filter:
                    raise DocumentFormatError(f"pixels da camada {layer.uid} indisponíveis")
                if raw:
                    raw_bytes = bytes(raw)
                    if len(raw_bytes) != expected_size:
                        raise DocumentFormatError(
                            f"buffer da camada {layer.uid} tem tamanho inválido ({len(raw_bytes)} != {expected_size})"
                        )
                    name = f"layers/{int(layer.uid)}.rgba"
                    payloads[name] = raw_bytes
                    entry["pixel_payload"] = name
                if layer.is_filter and hasattr(backend, "get_filter_type"):
                    entry["filter_type"] = int(backend.get_filter_type(index))
                    entry["filter_params"] = list(backend.get_filter_params(index))
            layers.append(entry)

        manifest = {
            "format": cls.FORMAT_ID,
            "version": cls.FORMAT_VERSION,
            "name": str(document.name),
            "width": int(document.width),
            "height": int(document.height),
            "file_path": str(target),
            "paper": {
                "color": cls._color_tuple(document.paper_color),
                "visible": bool(document.paper_visible),
                "texture_id": int(getattr(document, "paper_texture_id", 0)),
                "texture_enabled": bool(getattr(document, "paper_texture_enabled", False)),
            },
            "layers": layers,
            "active_uid": manager.get_active_layer().uid if manager.get_active_layer() else None,
            "zoom": float(document.zoom),
            "pan_x": float(document.pan_x),
            "pan_y": float(document.pan_y),
            "rotation": float(document.rotation),
            "guide_state": encode_guides(getattr(document, "guide_state", {}) or {}),
            "sym_state": dict(getattr(document, "sym_state", {}) or {}),
            "color_profile_id": getattr(backend, "get_color_profile", lambda: 0)(),
            "color_profile_payload": None,
            "selection_payload": None,
            "canvas_resource": None,
        }
        active_prof = manifest["color_profile_id"]
        custom_icc = getattr(document, "color_profile_icc_bytes", None)
        if not custom_icc and hasattr(backend, "get_active_profile_icc_bytes") and active_prof >= 100:
            custom_icc = backend.get_active_profile_icc_bytes()
        if custom_icc and active_prof >= 100:
            manifest["color_profile_payload"] = "profiles/document.icc"
            payloads["profiles/document.icc"] = bytes(custom_icc)
            if getattr(document, "color_profile_name", None):
                manifest["color_profile_name"] = str(document.color_profile_name)
        if getattr(backend, "has_selection", lambda: False)():
            raw = backend.get_selection_mask_buffer()
            if raw is None or len(raw) != document.width * document.height:
                raise DocumentFormatError("máscara de seleção indisponível ou inválida")
            manifest["selection_payload"] = "masks/selection.gray"
            payloads[manifest["selection_payload"]] = bytes(raw)
        resource = getattr(backend, "get_canvas_resource", lambda: None)()
        if resource is not None:
            resource = dict(resource)
            payloads["assets/canvas.gray"] = bytes(resource.pop("pixels"))
            resource["payload"] = "assets/canvas.gray"
            manifest["canvas_resource"] = resource
        cls._validate_manifest(manifest)

        fd, temp_name = tempfile.mkstemp(prefix=f".{target.stem}.", suffix=".tmp", dir=str(target.parent))
        os.close(fd)
        try:
            with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8"))
                for name, data in payloads.items():
                    archive.writestr(name, data)
            # Verify the completed archive before replacing the user's file.
            cls.read(temp_name)
            with open(temp_name, "r+b") as stream:
                os.fsync(stream.fileno())
            if target.exists():
                try:
                    cls.read(target)
                except DocumentFormatError:
                    pass  # Never replace a valid backup with a corrupt source.
                else:
                    backup_fd, backup_name = tempfile.mkstemp(prefix=".lmn-backup-", dir=target.parent)
                    os.close(backup_fd)
                    try:
                        shutil.copyfile(target, backup_name)
                        with open(backup_name, "r+b") as backup:
                            os.fsync(backup.fileno())
                        os.replace(backup_name, str(target) + ".bak")
                    finally:
                        if os.path.exists(backup_name):
                            os.unlink(backup_name)
            os.replace(temp_name, target)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        return str(target)

    @classmethod
    def read(cls, path: str | os.PathLike[str]) -> tuple[dict[str, Any], dict[str, bytes]]:
        source = Path(path).expanduser().resolve()
        try:
            with zipfile.ZipFile(source, "r") as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    raise DocumentFormatError("entradas ZIP duplicadas")
                try:
                    if archive.getinfo("manifest.json").file_size > cls.MAX_MANIFEST_BYTES:
                        raise DocumentFormatError("manifesto excede o limite permitido")
                    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise DocumentFormatError("manifest.json ausente") from exc
                if not isinstance(manifest, dict):
                    raise DocumentFormatError("manifesto inválido")
                if manifest.get("format") != cls.FORMAT_ID:
                    raise DocumentFormatError("formato de documento desconhecido")
                manifest = migrate(manifest)
                if not isinstance(manifest.get("layers"), list):
                    raise DocumentFormatError("manifesto sem lista de camadas")
                width = manifest.get("width", 0)
                height = manifest.get("height", 0)
                if type(width) is not int or type(height) is not int or width <= 0 or height <= 0 or width > 100_000 or height > 100_000:
                    raise DocumentFormatError("dimensões do documento inválidas")
                expected_size = width * height * 4
                if expected_size > min(cls.MAX_PAYLOAD_BYTES, 2**31 - 1):
                    raise DocumentFormatError("dimensões excedem o limite do motor")
                cls._validate_manifest(manifest)
                total_size = 0
                seen_uids: set[int] = set()
                payloads: dict[str, bytes] = {}
                referenced_payloads: set[str] = set()
                for layer in manifest["layers"]:
                    try:
                        uid = int(layer["uid"])
                    except (KeyError, TypeError, ValueError) as exc:
                        raise DocumentFormatError("camada sem UID válido") from exc
                    if uid in seen_uids:
                        raise DocumentFormatError("UID de camada duplicado")
                    seen_uids.add(uid)
                    payload_name = layer.get("pixel_payload")
                    if payload_name:
                        # Impede entradas ZIP que escapem do namespace de camadas.
                        if payload_name != f"layers/{uid}.rgba":
                            raise DocumentFormatError("payload de camada fora do namespace permitido")
                        if payload_name in payloads:
                            raise DocumentFormatError("payload de camada duplicado")
                        referenced_payloads.add(str(payload_name))
                        try:
                            size = archive.getinfo(payload_name).file_size
                            total_size += size
                            if size != expected_size or total_size > cls.MAX_PAYLOAD_BYTES:
                                raise DocumentFormatError("tamanho de payload inválido ou acima do limite")
                            data = archive.read(payload_name)
                        except KeyError as exc:
                            raise DocumentFormatError(f"payload ausente: {payload_name}") from exc
                        if len(data) != expected_size:
                            raise DocumentFormatError("payload de camada com tamanho inválido")
                        payloads[payload_name] = data
                extras = []
                if manifest.get("selection_payload"):
                    extras.append((manifest["selection_payload"], width * height))
                resource = manifest.get("canvas_resource")
                if resource is not None:
                    extras.append((resource["payload"], resource["width"] * resource["height"]))
                for name, expected in extras:
                    try:
                        size = archive.getinfo(name).file_size
                        total_size += size
                        if size != expected or total_size > cls.MAX_PAYLOAD_BYTES:
                            raise DocumentFormatError("tamanho de recurso inválido ou acima do limite")
                        payloads[name] = archive.read(name)
                    except KeyError as exc:
                        raise DocumentFormatError(f"recurso ausente: {name}") from exc
                    referenced_payloads.add(name)
                icc_payload = manifest.get("color_profile_payload")
                if icc_payload is not None:
                    if icc_payload != "profiles/document.icc":
                        raise DocumentFormatError("payload de perfil de cor fora do namespace permitido")
                    try:
                        size = archive.getinfo(icc_payload).file_size
                        total_size += size
                        if size <= 0 or total_size > cls.MAX_PAYLOAD_BYTES or size > 50 * 1024 * 1024:
                            raise DocumentFormatError("tamanho de perfil ICC inválido ou acima do limite")
                        payloads[icc_payload] = archive.read(icc_payload)
                    except KeyError as exc:
                        raise DocumentFormatError(f"recurso ausente: {icc_payload}") from exc
                    referenced_payloads.add(icc_payload)
                allowed_names = {"manifest.json"} | referenced_payloads
                unexpected = set(names) - allowed_names
                if unexpected:
                    raise DocumentFormatError("arquivo contém entradas ZIP não declaradas no manifesto")
                return manifest, payloads
        except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, EOFError,
                RuntimeError, RecursionError, NotImplementedError) as exc:
            raise DocumentFormatError("arquivo .lmn corrompido") from exc
        except (TypeError, ValueError, OverflowError) as exc:
            if isinstance(exc, DocumentFormatError):
                raise
            raise DocumentFormatError("manifesto contém valores inválidos") from exc

    @staticmethod
    def _validate_manifest(manifest):
        validate_auxiliary(manifest)
        if not isinstance(manifest.get("name", ""), str):
            raise DocumentFormatError("nome do documento inválido")
        records = manifest["layers"]
        if not records or len(records) > 10000:
            raise DocumentFormatError("quantidade de camadas inválida")
        nodes = {}
        for record in records:
            if not isinstance(record, dict) or type(record.get("uid")) is not int:
                raise DocumentFormatError("camada sem UID inteiro")
            uid = record["uid"]
            if uid <= 0 or uid in nodes:
                raise DocumentFormatError("UID inválido ou duplicado")
            nodes[uid] = record
            if "name" in record and not isinstance(record["name"], str):
                raise DocumentFormatError("nome de camada inválido")
            if manifest.get("version") == CURRENT_VERSION and not record.get("is_group") and not record.get("is_filter"):
                if not record.get("pixel_payload") and record.get("empty") is not True:
                    raise DocumentFormatError("camada raster sem declaração de pixels")
            opacity = float(record.get("opacity", 1.0))
            if not math.isfinite(opacity) or not 0 <= opacity <= 1:
                raise DocumentFormatError("opacidade inválida")
            for key in ("is_group", "is_filter", "visible", "locked", "alpha_locked", "clipping_mask"):
                if key in record and type(record[key]) is not bool:
                    raise DocumentFormatError(f"flag inválido: {key}")
            if record.get("is_group") and record.get("is_filter"):
                raise DocumentFormatError("camada não pode ser grupo e filtro")
            if record.get("pixel_payload") and (record.get("is_group") or record.get("is_filter")):
                raise DocumentFormatError("grupo/filtro não pode conter payload raster")
            if record.get("is_filter"):
                if type(record.get("filter_type", 0)) is not int:
                    raise DocumentFormatError("tipo de filtro inválido")
                params = record.get("filter_params", [])
                if not isinstance(params, list) or not all(isinstance(p, (int, float)) and math.isfinite(p) for p in params):
                    raise DocumentFormatError("parâmetros de filtro inválidos")
        for uid, record in nodes.items():
            seen = {uid}
            parent = record.get("parent_uid")
            while parent is not None:
                if type(parent) is not int or parent in seen or parent not in nodes or not nodes[parent].get("is_group"):
                    raise DocumentFormatError("hierarquia de camadas inválida")
                seen.add(parent)
                parent = nodes[parent].get("parent_uid")
        active_uid = manifest.get("active_uid")
        if active_uid is not None and (type(active_uid) is not int or active_uid not in nodes):
            raise DocumentFormatError("camada ativa inexistente")
        for key in ("zoom", "pan_x", "pan_y", "rotation"):
            if key in manifest and (type(manifest[key]) not in (int, float) or not math.isfinite(manifest[key])):
                raise DocumentFormatError("câmera inválida")
        if manifest.get("zoom", 1) <= 0:
            raise DocumentFormatError("zoom inválido")
        paper = manifest.get("paper", {})
        if not isinstance(paper, dict):
            raise DocumentFormatError("papel inválido")
        if type(paper.get("texture_id", 0)) is not int:
            raise DocumentFormatError("textura de papel inválida")
        for key in ("visible", "texture_enabled"):
            if key in paper and type(paper[key]) is not bool:
                raise DocumentFormatError("flag de papel inválido")
        color = paper.get("color", [255, 255, 255, 255])
        if not isinstance(color, list) or len(color) != 4 or any(type(c) is not int or not 0 <= c <= 255 for c in color):
            raise DocumentFormatError("cor do papel inválida")
        for key in ("guide_state", "sym_state"):
            if key in manifest and not isinstance(manifest[key], dict):
                raise DocumentFormatError(f"{key} inválido")
