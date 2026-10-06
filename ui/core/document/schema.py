"""Explicit migrations and portable document state for the LMN container."""

import copy
import math
from PySide6.QtCore import QPointF

CURRENT_VERSION = 3
POINT_KEYS = {"p0", "p1", "p2", "p3", "vpA", "vpB", "vpC"}


class DocumentFormatError(ValueError):
    """Invalid or unsupported editable document."""


def encode_guides(state):
    return {key: [value.x(), value.y()] if isinstance(value, QPointF) else value
            for key, value in state.items()}


def decode_guides(state):
    return {key: QPointF(*value) if key in POINT_KEYS else copy.deepcopy(value)
            for key, value in state.items()}


def _v0_to_v1(manifest):
    manifest.setdefault("name", "Documento sem nome")
    manifest.setdefault("paper", {"color": [255, 255, 255, 255], "visible": True,
                                  "texture_id": 0, "texture_enabled": False})
    for key, value in {"zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0, "rotation": 0.0,
                       "guide_state": {}, "sym_state": {}}.items():
        manifest.setdefault(key, value)
    manifest["version"] = 1
    return manifest


def _v1_to_v2(manifest):
    manifest.setdefault("color_profile_id", 0)
    manifest.setdefault("color_profile_payload", None)
    manifest.setdefault("selection_payload", None)
    manifest.setdefault("canvas_resource", None)
    # Old files could omit empty raster payloads. Preserve that legacy meaning
    # explicitly; new v2 files must declare every raster layer's storage.
    for record in manifest.get("layers", []):
        if isinstance(record, dict) and not record.get("pixel_payload"):
            record.setdefault("empty", True)
    manifest["version"] = 2
    return manifest


def _v2_to_v3(manifest):
    # v3 stores a raster layer as a block of tiles (`tiles_payload`, only the painted tiles,
    # LZ4) instead of full-canvas RGBA (`pixel_payload`). A v2 manifest already describes its
    # layers validly and `restore_document` reads both, so nothing is rewritten: the file is
    # upgraded the next time it is saved.
    manifest["version"] = 3
    return manifest


MIGRATIONS = {0: _v0_to_v1, 1: _v1_to_v2, 2: _v2_to_v3}


def migrate(manifest):
    version = manifest.get("version", 0)
    if type(version) is not int or version < 0:
        raise DocumentFormatError("versão de documento inválida")
    if version > CURRENT_VERSION:
        raise DocumentFormatError(f"versão {version} requer uma versão mais nova do Lumenia")
    result = copy.deepcopy(manifest)
    while version < CURRENT_VERSION:
        result = MIGRATIONS[version](result)
        version = result["version"]
    return result


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_auxiliary(manifest):  # noqa: C901 -- dívida registrada (pendências, item 14)
    # "dpi" é opcional: arquivos anteriores a 2026-09-24 não têm (restaura 300).
    dpi = manifest.get("dpi", 300)
    if type(dpi) is not int or not 1 <= dpi <= 100000:
        raise DocumentFormatError("resolução (DPI) inválida")
    pixel_format = manifest.get("pixel_format", 0)
    if type(pixel_format) is not int or pixel_format not in (0, 1):
        raise DocumentFormatError("formato de pixel inválido")
    paper = manifest.get("paper", {})
    if not isinstance(paper, dict):
        raise DocumentFormatError("papel inválido")
    # Os campos do papel chegam ao motor como `int`/`bool` da ponte: um valor fora disso era um TypeError
    # com a assinatura do pybind na mensagem em vez de um arquivo recusado (achado por mutação do manifesto).
    texture = paper.get("texture_id", 0)
    if type(texture) is not int or not 0 <= texture <= 1_000_000:
        raise DocumentFormatError("textura do papel inválida")
    for key in ("visible", "texture_enabled"):
        if key in paper and type(paper[key]) is not bool:
            raise DocumentFormatError(f"flag do papel inválido: {key}")
    paper_color = paper.get("color", [255, 255, 255, 255])
    if not (isinstance(paper_color, (list, tuple)) and len(paper_color) in (3, 4)
            and all(type(c) is int and 0 <= c <= 255 for c in paper_color)):
        raise DocumentFormatError("cor do papel inválida")
    profile = manifest.get("color_profile_id", 0)
    if type(profile) is not int or type(profile) is bool:
        raise DocumentFormatError("perfil de cor não suportado")
    if 0 <= profile <= 13:
        pass
    elif profile >= 100 and manifest.get("color_profile_payload") == "profiles/document.icc":
        pass
    else:
        raise DocumentFormatError("perfil de cor não suportado")
    icc_payload = manifest.get("color_profile_payload")
    if icc_payload is not None and icc_payload != "profiles/document.icc":
        raise DocumentFormatError("payload de perfil de cor inválido")
    for key in ("guide_state", "sym_state"):
        state = manifest.get(key, {})
        if not isinstance(state, dict):
            raise DocumentFormatError(f"{key} inválido")
        for name, value in state.items():
            if key == "guide_state" and name in POINT_KEYS:
                if not isinstance(value, list) or len(value) != 2 or not all(map(_number, value)):
                    raise DocumentFormatError("ponto de guia inválido")
            elif type(value) not in (str, bool, int, float) or (type(value) in (int, float) and not _number(value)):
                raise DocumentFormatError(f"estado de geometria inválido: {name}")
        numeric = {"cx", "cy", "angle", "snap_increment", "base_radius", "yaw", "pitch",
                   "fov", "density", "snap_radius", "snap_sensitivity"}
        for name in numeric & state.keys():
            if not _number(state[name]):
                raise DocumentFormatError(f"valor numérico inválido: {name}")
        for name in state:
            if name.startswith("show_") or name in {"hidden", "locked", "stop_at_center", "snap_dynamic"}:
                if type(state[name]) is not bool:
                    raise DocumentFormatError(f"flag de geometria inválido: {name}")
    sym = manifest.get("sym_state", {})
    if sym.get("mode", "none") not in {"none", "mirror", "mirror_v", "mirror_h", "double_mirror", "radial", "kaleidoscope"}:
        raise DocumentFormatError("modo de simetria inválido")
    if manifest.get("guide_state", {}).get("type", "none") not in {"none", "straight", "curve_ruler", "curvilinear", "one_point", "two_point", "three_point", "isometric"}:
        raise DocumentFormatError("tipo de guia inválido")
    if "segments" in sym and (type(sym["segments"]) is not int or not 1 <= sym["segments"] <= 360):
        raise DocumentFormatError("segmentos de simetria inválidos")
    resource = manifest.get("canvas_resource")
    if resource is not None:
        if not isinstance(resource, dict):
            raise DocumentFormatError("recurso do papel inválido")
        for key in ("width", "height"):
            if type(resource.get(key)) is not int or not 1 <= resource[key] <= 100000:
                raise DocumentFormatError("dimensões de textura inválidas")
        for key in ("enabled", "invert"):
            if type(resource.get(key)) is not bool:
                raise DocumentFormatError("flag de textura inválido")
        for key in ("scale", "contrast"):
            if not _number(resource.get(key)) or resource[key] <= 0:
                raise DocumentFormatError("parâmetro de textura inválido")
        if resource.get("payload") != "assets/canvas.gray":
            raise DocumentFormatError("payload de textura inválido")
        curve = resource.get("curve")
        if not isinstance(curve, list) or len(curve) != 256 or not all(map(_number, curve)):
            raise DocumentFormatError("curva de textura inválida")
    if manifest.get("selection_payload") not in (None, "masks/selection.gray"):
        raise DocumentFormatError("payload de seleção inválido")
