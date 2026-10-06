"""O que se leva do documento no instante de salvar (S1.2).

Salvar tem duas metades. A primeira precisa da thread que é dona do documento e do
motor: conferir que o documento e o motor concordam, ler o manifesto e congelar as
camadas (`LayerSnapshot`, que custa o número de tiles e não copia pixel). Ela termina em
poucos milissegundos e devolve um `SaveCapture`. A segunda, `DocumentSerializer.write`,
só lê o que está no `SaveCapture`: comprime os tiles e grava o arquivo, e pode rodar em
outra thread enquanto o artista continua pintando.

Até 2026-10-01 tudo era uma coisa só na thread da interface: 2,1 s com 4K e dez
camadas (4,1 s antes das camadas vazias), repetidos a cada minuto pela recuperação.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ui.core.engine.backend_protocols import (
    ColorProtocol, CoreLifecycleProtocol, HistoryProtocol, LayerProtocol, RenderPipelineProtocol, SelectionTransformProtocol,
)
from ui.core.engine.persistence_backend import PersistenceBackend

from .document import Document
from . import layer_properties
from .local_layer import LocalLayer
from .schema import CURRENT_VERSION, DocumentFormatError, encode_guides

MAX_PAYLOAD_BYTES = 2 * 1024 * 1024 * 1024


class CaptureEngine(
    ColorProtocol, CoreLifecycleProtocol, HistoryProtocol, LayerProtocol, PersistenceBackend, RenderPipelineProtocol,
    SelectionTransformProtocol, Protocol,
):
    """O que tirar o documento do motor pede: o instantâneo das camadas, o contexto ativo, o perfil de cor,
    a seleção e o papel; e o histórico (que a captura confere contra o documento)."""


@dataclass(frozen=True)
class SaveCapture:
    """Tudo o que a gravação precisa, já tirado do documento e do motor."""

    uid: str                                # documento de onde veio
    revision: int                           # `Document.revision` no instante da captura
    target: Path
    manifest: dict[str, Any]
    snapshot: Any                           # LayerSnapshot do motor: `encode_layer(i)` serve a outra thread
    raster_layers: tuple[tuple[int, str], ...]  # (índice no motor, nome da entrada no arquivo)
    extras: dict[str, bytes]                # máscara de seleção, textura do papel, perfil ICC


def _color_tuple(color: Any) -> list[int]:
    return [int(color.red()), int(color.green()), int(color.blue()), int(color.alpha())]


def _check_ready(document: Document, backend: CaptureEngine) -> None:
    if not backend or not backend.available:
        raise DocumentFormatError("motor indisponível; salvamento cancelado para preservar o documento")
    if backend.get_active_document_context() != document.uid:
        raise DocumentFormatError("contexto ativo não corresponde ao documento")
    if backend.is_transform_active():
        raise DocumentFormatError("confirme ou cancele a transformação antes de salvar")
    try:
        document.history.assert_projection(backend)
    except RuntimeError as exc:
        raise DocumentFormatError(str(exc)) from exc
    bpp = 8 if document.rgba16_document else 4
    if document.width * document.height * bpp > min(MAX_PAYLOAD_BYTES, 2**31 - 1):
        raise DocumentFormatError("dimensões excedem o limite do motor")


def _layer_entries(document: Document, backend: CaptureEngine, snapshot) -> tuple[list[dict[str, Any]], list[tuple[int, str]]]:
    layers_model = document.layer_manager.layers
    if snapshot is None or snapshot.layer_count != len(layers_model):
        raise DocumentFormatError("camadas do documento e do motor divergem; salvamento cancelado")
    entries: list[dict[str, Any]] = []
    raster: list[tuple[int, str]] = []
    layer: LocalLayer
    for index, layer in enumerate(layers_model):
        entry: dict[str, Any] = {
            "uid": int(layer.uid),
            "parent_uid": layer.parent_uid,
            "is_group": bool(layer.is_group),
            "is_filter": bool(layer.is_filter),
        }
        for prop in layer_properties.TABLE.all:
            if prop.saved:
                entry[prop.name] = prop.coerce(getattr(layer, prop.name))
        if not layer.is_group and not layer.is_filter:
            if not snapshot.has_pixels(index):
                raise DocumentFormatError(f"pixels da camada {layer.uid} indisponíveis")
            name = f"layers/{int(layer.uid)}.tiles"
            entry["tiles_payload"] = name
            raster.append((index, name))
        if layer.is_filter:
            entry["filter_type"] = int(backend.get_filter_type(index))
            entry["filter_params"] = list(backend.get_filter_params(index))
        entries.append(entry)
    return entries, raster


def _extras(document: Document, backend: CaptureEngine, manifest: dict[str, Any]) -> dict[str, bytes]:
    extras: dict[str, bytes] = {}
    profile = manifest["color_profile_id"]
    icc = document.color_profile_icc_bytes
    if not icc and profile >= 100:
        icc = backend.get_active_profile_icc_bytes()
    if icc and profile >= 100:
        manifest["color_profile_payload"] = "profiles/document.icc"
        extras["profiles/document.icc"] = bytes(icc)
        if document.color_profile_name:
            manifest["color_profile_name"] = str(document.color_profile_name)
    if backend.has_selection():
        raw = backend.get_selection_mask_buffer()
        if raw is None or len(raw) != document.width * document.height:
            raise DocumentFormatError("máscara de seleção indisponível ou inválida")
        manifest["selection_payload"] = "masks/selection.gray"
        extras["masks/selection.gray"] = bytes(raw)
    resource = backend.get_canvas_resource()
    if resource is not None:
        resource = dict(resource)
        extras["assets/canvas.gray"] = bytes(resource.pop("pixels"))
        resource["payload"] = "assets/canvas.gray"
        manifest["canvas_resource"] = resource
    return extras


def capture_document(document: Document, backend: CaptureEngine, path: str | os.PathLike[str]) -> SaveCapture:
    """A metade da gravação que precisa da thread do documento. Levanta `DocumentFormatError`."""
    _check_ready(document, backend)
    target = Path(path).expanduser().resolve()
    if target.suffix.lower() != ".lmn":
        target = target.with_suffix(".lmn")
    manager = document.layer_manager
    snapshot = backend.snapshot_layers()
    entries, raster = _layer_entries(document, backend, snapshot)
    active = manager.get_active_layer()
    manifest: dict[str, Any] = {
        "format": "lmn",
        "version": CURRENT_VERSION,
        "name": str(document.name),
        "width": int(document.width),
        "height": int(document.height),
        "dpi": int(document.dpi),
        "pixel_format": int(document.pixel_format),
        "paper": {
            "color": _color_tuple(document.paper_color),
            "visible": bool(document.paper_visible),
            "texture_id": int(document.paper_texture_id),
            "texture_enabled": bool(document.paper_texture_enabled),
        },
        "layers": entries,
        "active_uid": active.uid if active else None,
        "zoom": float(document.zoom),
        "pan_x": float(document.pan_x),
        "pan_y": float(document.pan_y),
        "rotation": float(document.rotation),
        "guide_state": encode_guides(document.guide_state or {}),
        "sym_state": dict(document.sym_state or {}),
        "color_profile_id": backend.get_color_profile(),
        "color_profile_payload": None,
        "selection_payload": None,
        "canvas_resource": None,
    }
    extras = _extras(document, backend, manifest)
    return SaveCapture(
        uid=document.uid, revision=document.revision, target=target, manifest=manifest,
        snapshot=snapshot, raster_layers=tuple(raster), extras=extras,
    )
