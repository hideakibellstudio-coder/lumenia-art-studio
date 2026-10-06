"""Versioned configuration migration; canonical values survive UI translation."""

from copy import deepcopy

SCHEMA_VERSION = 1
SPEED_ALIASES = {"Ultra Fast": "Ultra Rápido", "Fast": "Rápido", "Slow": "Lento",
                 "Disabled": "Desativado", "Normal": "Normal"}
DELAY_ALIASES = {"No Delay": "Sem Atraso", "Short (100ms)": "Curto (100ms)",
                 "Normal (350ms)": "Normal (350ms)", "Long (800ms)": "Longo (800ms)"}


class UnsupportedConfigVersion(ValueError):
    pass


def normalize_section(section, data):
    if not isinstance(data, dict):
        raise ValueError("seção de configuração deve ser um objeto")
    result = deepcopy(data)
    if section in ("dock", "floating_toolbar"):
        for key, aliases in (("speed", SPEED_ALIASES), ("hover_delay", DELAY_ALIASES)):
            if isinstance(result.get(key), str):
                result[key] = aliases.get(result[key], result[key])
    if section == "render":
        profile = result.get("profile_id")
        aliases = {"srgb": 0, "display_p3": 1, "p3": 1, "adobe_rgb": 2, "rec2020": 3}
        if isinstance(profile, str) and profile.strip().lower() in aliases:
            result["profile_id"] = aliases[profile.strip().lower()]
        for key in ("deep_color", "linear_gamma", "low_latency"):
            if key in result and type(result[key]) is not bool:
                raise ValueError(f"render.{key} deve ser booleano")
        for key in ("profile_id", "undo_max_steps", "undo_limit_mb"):
            if key in result:
                value = result[key]
                low, high = (0, 13) if key == "profile_id" else (1, 2**31 - 1)
                if type(value) is not int or not low <= value <= high:
                    raise ValueError(f"render.{key} fora do intervalo suportado")
    if section == "pen":
        # Só tipo e finitude: as faixas do produto vivem em `ui.core.state.pen_calibration`
        # (esta pasta não depende do resto da interface) e o motor ainda corrige o que sobrar.
        for key, (low, high) in {"floor": (0.0, 1.0), "ceiling": (0.0, 1.0), "gamma": (0.1, 5.0)}.items():
            if key in result:
                value = result[key]
                if type(value) not in (int, float) or value != value or not low <= value <= high:
                    raise ValueError(f"pen.{key} fora do intervalo suportado")
                result[key] = float(value)
    return result


def _v0_to_v1(data):
    data["schema_version"] = 1
    return data


MIGRATIONS = {0: _v0_to_v1}


def migrate_config(data):
    version = data.get("schema_version", 0)
    if type(version) is not int or version < 0:
        raise ValueError("versão de configuração inválida")
    if version > SCHEMA_VERSION:
        raise UnsupportedConfigVersion("configuração pertence a uma versão mais nova; arquivo preservado")
    result = deepcopy(data)
    while version < SCHEMA_VERSION:
        result = MIGRATIONS[version](result)
        version = result["schema_version"]
    for section in ("render", "pen", "dock", "floating_toolbar"):
        values = result.get(section)
        if not isinstance(values, dict):
            result.pop(section, None)
            continue
        # Discard each invalid legacy value independently, retaining valid
        # neighboring preferences and letting the manager supply defaults.
        normalized = {}
        for key, value in values.items():
            try:
                normalized.update(normalize_section(section, {key: value}))
            except ValueError:
                continue
        result[section] = normalized
    return result
