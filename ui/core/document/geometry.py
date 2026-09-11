"""Atomic geometry changes: prepare all pixels before committing the new context."""

import tempfile
import uuid
from pathlib import Path
from PIL import Image

from .document import Document
from .serializer import DocumentSerializer, DocumentFormatError
from .restore import restore_document


def change_geometry(document, backend, width, height, *, anchor=(1, 1), crop=None, resample=None):
    width, height = int(width), int(height)
    if width <= 0 or height <= 0 or width * height * 4 > DocumentSerializer.MAX_PAYLOAD_BYTES:
        raise ValueError("dimensões fora do limite suportado")
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
    with tempfile.TemporaryDirectory(prefix="lumenia-geometry-") as directory:
        path = DocumentSerializer.save(document, backend, Path(directory) / "before.lmn")
        manifest, payloads = DocumentSerializer.read(path)
    original_size = (document.width, document.height)
    for name, pixels in payloads.items():
        if not name.startswith("layers/"):
            continue
        image = Image.frombytes("RGBA", original_size, pixels)
        if crop is not None:
            transformed = image.crop((x, y, x + width, y + height))
        elif resample is not None:
            mode = (Image.Resampling.BILINEAR, Image.Resampling.BICUBIC, Image.Resampling.NEAREST)[resample]
            transformed = image.resize((width, height), mode)
        else:
            row, col = anchor
            dx = (width - document.width) * col // 2
            dy = (height - document.height) * row // 2
            transformed = Image.new("RGBA", (width, height))
            transformed.paste(image, (dx, dy))
        payloads[name] = transformed.tobytes()
    manifest.update(width=width, height=height)
    # Geometry currently clears the active selection; its previous value is
    # retained in native history and restored by undo.
    manifest["selection_payload"] = None
    prepared_uid = "geometry_" + uuid.uuid4().hex
    shadow = Document(prepared_uid, document.name, width, height)
    shadow.paper_color = document.paper_color
    shadow.paper_visible = document.paper_visible
    shadow.paper_texture_id = document.paper_texture_id
    shadow.paper_texture_enabled = document.paper_texture_enabled
    profile = backend.get_color_profile()
    options = backend.get_render_options()
    try:
        backend.set_active_document_context(prepared_uid, width, height)
        if backend.get_active_document_context() != prepared_uid:
            raise DocumentFormatError("falha ao preparar contexto de geometria")
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
