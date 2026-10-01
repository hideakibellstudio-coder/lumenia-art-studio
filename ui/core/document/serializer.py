"""Persistência do formato editável nativo do Lumenia.

O formato é um ZIP versionado com manifesto JSON e uma entrada por camada. Desde a versão 3
(2026-10-01) a camada é um bloco de tiles (só os tiles pintados, em LZ4); as versões 1 e 2
guardavam o RGBA do canvas inteiro e continuam abrindo. Salvar tem duas metades
(`save_capture.py`): congelar o documento na thread dele e gravar em qualquer thread.
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
from . import layer_properties
from .save_capture import MAX_PAYLOAD_BYTES, SaveCapture, capture_document
from .schema import CURRENT_VERSION, DocumentFormatError, migrate, validate_auxiliary


class DocumentSerializer:
    FORMAT_ID = "lmn"
    FORMAT_VERSION = CURRENT_VERSION
    MAX_MANIFEST_BYTES = 8 * 1024 * 1024
    MAX_PAYLOAD_BYTES = MAX_PAYLOAD_BYTES
    # Cabeçalho de um bloco de tiles (engine/core/canvas/TileGridCodec.hpp) e o maior registro
    # de um tile: 12 bytes de cabeçalho + o tile cru de 128 x 128 x 4.
    TILE_BLOCK_MAGIC = b"LMNT"
    TILE_BLOCK_HEADER = 24
    TILE_BLOCK_ENTRY = 12 + 128 * 128 * 4

    @classmethod
    def save(cls, document: Document, backend, path: str | os.PathLike[str]) -> str:
        """Captura e grava de uma vez, na thread de quem chama.

        A interface usa as duas metades em separado (`capture_document` na thread dela,
        `write` numa thread de gravação); isto serve a quem não tem interface a proteger.
        """
        return cls.write(capture_document(document, backend, path))

    @classmethod
    def write(cls, capture: SaveCapture) -> str:
        """A metade que roda em qualquer thread: comprime os tiles, grava, confere e troca o arquivo."""
        target = capture.target
        target.parent.mkdir(parents=True, exist_ok=True)
        cls._validate_manifest(capture.manifest)
        manifest_bytes = json.dumps(capture.manifest, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.stem}.", suffix=".tmp", dir=str(target.parent))
        os.close(fd)
        try:
            # Os blocos de tiles já vêm comprimidos (LZ4): guardados, não comprimidos de novo.
            with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_STORED) as archive:
                for index, name in capture.raster_layers:
                    archive.writestr(name, capture.snapshot.encode_layer(index))
                for name, data in capture.extras.items():
                    archive.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
                archive.writestr("manifest.json", manifest_bytes, compress_type=zipfile.ZIP_DEFLATED)
            cls._publish(temp_name, target)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        return str(target)

    @classmethod
    def _publish(cls, temp_name: str, target: Path) -> None:
        """Confere o arquivo pronto, guarda a cópia `.bak` do anterior e o troca de forma atômica."""
        cls.verify(temp_name)  # a estrutura e o CRC de cada entrada, antes de tocar no arquivo do usuário
        with open(temp_name, "r+b") as stream:
            os.fsync(stream.fileno())
        if target.exists():
            try:
                cls.verify(target)
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

    @staticmethod
    def _consume(archive: zipfile.ZipFile, name: str, keep: bool) -> bytes:
        """Lê a entrada inteira (e o ZIP confere o CRC ao chegar no fim). Guarda os bytes só se `keep`;
        senão devolve os 4 primeiros, o bastante para conferir o bloco, sem ocupar a memória do arquivo."""
        with archive.open(name) as stream:
            if keep:
                return stream.read()
            head = stream.read(4)
            while stream.read(1 << 20):
                pass
            return head

    @classmethod
    def verify(cls, path: str | os.PathLike[str]) -> None:
        """Confere um arquivo sem carregá-lo: a estrutura, os tamanhos e o CRC de cada entrada.

        Gravar confere o arquivo pronto antes de trocá-lo pelo do usuário; carregar todas as
        camadas na memória só para isso dobrava o pico (294 MB num 4K denso)."""
        cls.read(path, keep_payloads=False)

    @classmethod
    def read(cls, path: str | os.PathLike[str], keep_payloads: bool = True) -> tuple[dict[str, Any], dict[str, bytes]]:  # noqa: C901 -- dívida registrada (pendências, item 14)
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
                    if layer.get("pixel_payload") and layer.get("tiles_payload"):
                        raise DocumentFormatError("camada declara pixels de dois jeitos")
                    payload_name = layer.get("pixel_payload") or layer.get("tiles_payload")
                    if payload_name:
                        is_tiles = bool(layer.get("tiles_payload"))
                        # Impede entradas ZIP que escapem do namespace de camadas.
                        if payload_name != f"layers/{uid}.{'tiles' if is_tiles else 'rgba'}":
                            raise DocumentFormatError("payload de camada fora do namespace permitido")
                        if payload_name in payloads:
                            raise DocumentFormatError("payload de camada duplicado")
                        referenced_payloads.add(str(payload_name))
                        tiles_limit = cls.TILE_BLOCK_HEADER + (-(-width // 128)) * (-(-height // 128)) * cls.TILE_BLOCK_ENTRY
                        try:
                            size = archive.getinfo(payload_name).file_size
                            total_size += size
                            bad_size = not cls.TILE_BLOCK_HEADER <= size <= tiles_limit if is_tiles else size != expected_size
                            if bad_size or total_size > cls.MAX_PAYLOAD_BYTES:
                                raise DocumentFormatError("tamanho de payload inválido ou acima do limite")
                            data = cls._consume(archive, payload_name, keep_payloads)
                        except KeyError as exc:
                            raise DocumentFormatError(f"payload ausente: {payload_name}") from exc
                        if keep_payloads and len(data) != size:
                            raise DocumentFormatError("payload de camada com tamanho inválido")
                        if is_tiles and data[:4] != cls.TILE_BLOCK_MAGIC:
                            raise DocumentFormatError("bloco de tiles inválido")
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
                        payloads[name] = cls._consume(archive, name, keep_payloads)
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
                        payloads[icc_payload] = cls._consume(archive, icc_payload, keep_payloads)
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
    def _validate_manifest(manifest):  # noqa: C901 -- dívida registrada (pendências, item 14)
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
                if not record.get("pixel_payload") and not record.get("tiles_payload") and record.get("empty") is not True:
                    raise DocumentFormatError("camada raster sem declaração de pixels")
            opacity = float(record.get("opacity", 1.0))
            if not math.isfinite(opacity) or not 0 <= opacity <= 1:
                raise DocumentFormatError("opacidade inválida")
            for key in ("is_group", "is_filter", *layer_properties.TABLE.flag_keys):
                if key in record and type(record[key]) is not bool:
                    raise DocumentFormatError(f"flag inválido: {key}")
            if record.get("is_group") and record.get("is_filter"):
                raise DocumentFormatError("camada não pode ser grupo e filtro")
            if (record.get("pixel_payload") or record.get("tiles_payload")) and (record.get("is_group") or record.get("is_filter")):
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
