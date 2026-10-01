"""Restore a validated document into a newly allocated backend context."""

import numpy as np

from .document import Document
from .serializer import DocumentFormatError
from .schema import CURRENT_VERSION, decode_guides
from PySide6.QtGui import QColor


def same_visible_pixels(restored: bytes, expected: bytes) -> bool:
    """RGBA buffers are equal where it matters: the RGB of a fully transparent
    pixel is not data (soft brushes leave it on their fringe, and the engine
    does not paste it)."""
    if restored == expected:
        return True
    if len(restored) != len(expected):
        return False
    got = np.frombuffer(restored, dtype=np.uint8).reshape(-1, 4)
    want = np.frombuffer(expected, dtype=np.uint8).reshape(-1, 4)
    both_transparent = (got[:, 3] == 0) & (want[:, 3] == 0)
    differs = (got != want).any(axis=1)
    return not bool((differs & ~both_transparent).any())


def _restore_pixels(document: Document, backend, index: int, record, payloads, prepared) -> None:
    """Os pixels de uma camada: um bloco de tiles (v3, já decodificado ou não) ou o RGBA do canvas inteiro (v1 e v2)."""
    tiles = record.get("tiles_payload")
    if tiles:
        try:
            if tiles in prepared:
                backend.adopt_decoded_layer(index, prepared[tiles])
            else:
                backend.restore_layer_tiles(index, payloads[tiles])
        except ValueError as exc:
            raise DocumentFormatError(f"camada {record['uid']}: {exc}") from exc
        return
    payload = record.get("pixel_payload")
    if not payload:
        return
    if not backend.select_layer(index):
        raise DocumentFormatError("falha ao selecionar camada")
    backend.paste_rgba_buffer_on_active_layer(0, 0, document.width, document.height, payloads[payload])
    if not same_visible_pixels(bytes(backend.get_layer_pixel_buffer(index) or b""), payloads[payload]):
        raise DocumentFormatError("restauração de pixels não corresponde ao arquivo")


def restore_document(document: Document, backend, manifest, payloads, prepared=None):
    """Reconstrói o documento no contexto ativo do motor.

    `prepared` são as camadas de tiles já decodificadas em outra thread (`document_loader`),
    pelo nome do payload; as que faltam aí são decodificadas aqui, a partir de `payloads`.

    Tudo dentro de um lote do motor: abrir um arquivo muda dezenas de propriedades de
    camada em sequência e cada uma recompunha o canvas inteiro (50 recomposições, 0,6 s
    num 4K de dez camadas); no lote o canvas é composto uma vez, no fim.
    """
    if not backend or not backend.available:
        raise DocumentFormatError("motor indisponível para restaurar os pixels")
    backend.begin_batch()
    try:
        _restore_into_engine(document, backend, manifest, payloads, prepared or {})
    finally:
        backend.end_batch()


def _restore_into_engine(document: Document, backend, manifest, payloads, prepared):  # noqa: C901 -- dívida registrada (pendências, item 14)
    records = manifest["layers"]
    backend.clear_selection()
    # Keep the bootstrap layer until every replacement node exists. This also
    # supports a group/filter as the first node without coercing its type.
    initial_count = backend.get_drawing_layer_count()
    for record in records:
        name = record.get("name", "Camada")
        if record.get("is_group"):
            index = backend.add_group(name, -1)
        elif record.get("is_filter"):
            index = backend.add_filter_layer(name, record.get("filter_type", 0), -1)
        else:
            index = backend.add_layer(name, -1)
        if index < 0:
            raise DocumentFormatError("falha ao criar camada no motor")
    for _ in range(initial_count):
        if not backend.remove_layer(0):
            raise DocumentFormatError("falha ao remover camada inicial")
    if backend.get_drawing_layer_count() != len(records):
        raise DocumentFormatError("quantidade de camadas inconsistente")
    indices = {record["uid"]: i for i, record in enumerate(records)}
    for index, record in enumerate(records):
        # Restore pixels before locks/opacity/clipping can influence paste.
        _restore_pixels(document, backend, index, record, payloads, prepared)
        if record.get("is_filter"):
            backend.set_filter_params(index, record.get("filter_params", []))
        backend.set_layer_name(index, record.get("name", "Camada"))
        backend.set_layer_blend_mode(index, record.get("blend_mode", "Normal"))
        backend.set_layer_opacity(index, record.get("opacity", 1.0))
        backend.set_layer_visibility(index, record.get("visible", True))
        backend.set_layer_lock(index, record.get("locked", False))
        backend.set_layer_alpha_lock(index, record.get("alpha_locked", False))
        backend.set_layer_clipping_mask(index, record.get("clipping_mask", False))
    parents = [indices.get(r.get("parent_uid"), -1) for r in records]
    if not backend.set_layer_parents(parents):
        raise DocumentFormatError("falha ao restaurar hierarquia")
    document.layer_manager.replace_layers(records)
    document.history.bind_projection_identities(backend)
    active = manifest.get("active_uid") or records[0]["uid"]
    document.layer_manager.set_active_layer(active)
    backend.select_layer(indices[active])
    document.dpi = manifest.get("dpi", document.dpi)
    paper = manifest.get("paper", {})
    document.paper_color = QColor(*paper.get("color", document.paper_color.getRgb()))
    document.paper_visible = paper.get("visible", document.paper_visible)
    document.paper_texture_id = paper.get("texture_id", document.paper_texture_id)
    document.paper_texture_enabled = paper.get("texture_enabled", document.paper_texture_enabled)
    backend.set_canvas_paper_state(document.paper_color, document.paper_visible,
                                   document.paper_texture_id, document.paper_texture_enabled)
    resource = manifest.get("canvas_resource")
    if resource is not None:
        state = {key: value for key, value in resource.items() if key != "payload"}
        state["pixels"] = payloads[resource["payload"]]
        if not backend.set_canvas_resource(state):
            raise DocumentFormatError("falha ao restaurar textura do papel")
        document.paper_scale = state["scale"]
        document.paper_contrast = state["contrast"]
        document.paper_invert = state["invert"]
        document.paper_texture_enabled = state["enabled"]
    selection = manifest.get("selection_payload")
    if selection:
        expected = payloads[selection]
        if not backend.set_selection_mask_buffer(expected):
            raise DocumentFormatError("falha ao restaurar seleção")
        if (backend.get_selection_mask_buffer() or bytes(document.width * document.height)) != expected:
            raise DocumentFormatError("máscara restaurada difere do arquivo")
    icc_payload = manifest.get("color_profile_payload")
    if icc_payload and icc_payload in payloads:
        raw_icc = payloads[icc_payload]
        prof_name = manifest.get("color_profile_name")
        document.color_profile_icc_bytes = raw_icc
        document.color_profile_name = prof_name
        if hasattr(backend, "register_custom_color_profile"):
            backend.register_custom_color_profile(raw_icc, name=prof_name)
    profile = manifest.get("color_profile_id", 0)
    backend.set_color_profile(profile)
    if backend.get_color_profile() != profile:
        raise DocumentFormatError("perfil de cor não foi restaurado")
    document.guide_state = decode_guides(manifest.get("guide_state", {}))
    document.sym_state = dict(manifest.get("sym_state", {}))
    document.format_version = CURRENT_VERSION
    for key, default in (("zoom", 1.0), ("pan_x", 0.0), ("pan_y", 0.0), ("rotation", 0.0)):
        setattr(document, key, float(manifest.get(key, default)))
