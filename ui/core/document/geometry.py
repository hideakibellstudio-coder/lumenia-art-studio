"""Atomic geometry changes: prepare all pixels before committing the new context."""

import copy
import uuid
from pathlib import Path
from PIL import Image

from ui.core.engine.errors import EngineContextError
from .document import Document
from .restore import restore_document
from .save_capture import capture_document
from .schema import DocumentFormatError


def _raw_document(document: Document, backend):
    """O manifesto do documento e o RGBA de cada camada, para recortar ou redimensionar com o PIL.

    Até 2026-10-01 isto gravava um `.lmn` numa pasta temporária e o lia de volta só para obter
    estes bytes. O arquivo guarda blocos de tiles (v3), que o PIL não lê; aqui se pede ao motor
    o buffer de cada camada, sem arquivo nenhum no meio.
    """
    capture = capture_document(document, backend, Path("geometry.lmn"))
    manifest = copy.deepcopy(capture.manifest)
    payloads = dict(capture.extras)
    for index, _name in capture.raster_layers:
        record = manifest["layers"][index]
        del record["tiles_payload"]
        record["pixel_payload"] = f"layers/{record['uid']}.rgba"
        payloads[record["pixel_payload"]] = bytes(backend.get_layer_pixel_buffer(index))
    return manifest, payloads


def change_geometry(document: Document, backend, width, height, *, anchor=(1, 1), crop=None, resample=None):
    width, height = int(width), int(height)
    limit = backend.max_canvas_dimension() if backend else None
    if width <= 0 or height <= 0 or (limit is not None and (width > limit or height > limit)):
        raise ValueError(f"dimensões fora do limite suportado (1 a {limit} px por lado)")
    if not backend or not backend.available or backend.get_active_document_context() != document.uid:
        raise DocumentFormatError("contexto ativo não corresponde ao documento")
    if tuple(anchor) not in {(r, c) for r in range(3) for c in range(3)}:
        raise ValueError("âncora inválida")
    if resample is not None and resample not in (0, 1, 2):
        raise ValueError("reamostragem inválida")
    if crop is not None:
        x, y = map(int, crop)
        if x < 0 or y < 0 or x + width > document.width or y + height > document.height:
            raise ValueError("recorte fora dos limites do documento")
    manifest, payloads = _raw_document(document, backend)
    original_size = (document.width, document.height)
    def transform(image, interpolation):
        if crop is not None:
            return image.crop((x, y, x + width, y + height))
        if resample is not None:
            return image.resize((width, height), interpolation)
        row, col = anchor
        dx = (width - document.width) * col // 2
        dy = (height - document.height) * row // 2
        transformed = Image.new(image.mode, (width, height))
        transformed.paste(image, (dx, dy))
        return transformed

    for name, pixels in payloads.items():
        if not name.startswith("layers/"):
            continue
        image = Image.frombytes("RGBA", original_size, pixels)
        mode = (Image.Resampling.BILINEAR, Image.Resampling.BICUBIC, Image.Resampling.NEAREST)[resample or 0]
        payloads[name] = transform(image, mode).tobytes()
    manifest.update(width=width, height=height)
    selection_name = manifest.get("selection_payload")
    if selection_name:
        selection = Image.frombytes("L", original_size, payloads[selection_name])
        payloads[selection_name] = transform(selection, Image.Resampling.NEAREST).tobytes()
    prepared_uid = "geometry_" + uuid.uuid4().hex
    shadow: Document = Document(prepared_uid, document.name, width, height)
    shadow.paper_color = document.paper_color
    shadow.paper_visible = document.paper_visible
    shadow.paper_texture_id = document.paper_texture_id
    shadow.paper_texture_enabled = document.paper_texture_enabled
    profile = backend.get_color_profile()
    options = backend.get_render_options()
    try:
        try:
            backend.set_active_document_context(prepared_uid, width, height)
        except EngineContextError as exc:
            raise DocumentFormatError("falha ao preparar contexto de geometria") from exc
        backend.set_render_options(**options)
        backend.set_color_profile(profile)
        restore_document(shadow, backend, manifest, payloads)
        backend.set_active_document_context(document.uid, *original_size)
        with document.history.transaction(backend):
            if not backend.apply_prepared_geometry(prepared_uid):
                raise DocumentFormatError("falha ao confirmar geometria")
            # The layer identities and metadata are unchanged by geometry.
            document.set_geometry(width, height)
    finally:
        backend.close_document_context(prepared_uid)
        backend.set_active_document_context(document.uid, document.width, document.height)
    document.mark_dirty("geometry")
