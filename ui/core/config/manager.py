"""
ConfigManager — Sistema Central de Configurações e Preferências (Lumenia V2 / ARCcC)
==================================================================================
Substitui 100% o uso fragmentado do Registro do Windows (QSettings) por um arquivo
JSON único, canônico, legível, crash-safe e imune a contaminações de testes.
"""

from __future__ import annotations

import os
import copy
import json
import logging
from typing import Any, Dict, Optional
from PySide6 import QtCore
from .storage import read_object, save_with_backup
from .schema import SCHEMA_VERSION, UnsupportedConfigVersion, migrate_config, normalize_section

logger = logging.getLogger(__name__)

# Configuração Padrão Canônica de Fábrica
DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "2.0",
    "schema_version": SCHEMA_VERSION,
    "locale": {
        "current": "auto",
        "auto_detect": True,
    },
    "theme": {
        "active": "lumenia_purple",
    },
    "interface": {
        "scale": 1.0,
    },
    "floating_toolbar": {
        "active": True,
        "dock_state": "snapped_bottom",
        "speed": "Normal",
        "tools": [
            "brush", "eraser", "smudge", "bucket", "eyedrop", "wand",
            "transform", "rect_select", "ellipse_select", "lasso", "shapes", "text"
        ],
    },
    "dock": {
        "auto_collapse": False,
        "speed": "Rápido",
        "hover_delay": "Normal (350ms)",
    },
    "cursor": {
        "style": "crosshair_ring",
        "brush_outline": True,
        "precision_cross": True,
        "anti_flicker": True,
    },
    "render": {
        "profile_id": 0,
        "deep_color": False,
        "linear_gamma": False,
        "low_latency": True,
        "undo_max_steps": 50,
        "undo_limit_mb": 512,
    },
    "shortcuts": {},
}


def get_default_config_path() -> str:
    """Retorna o caminho padrão de %APPDATA%/Lumenia/config.json ou ~/.lumenia/config.json."""
    override = os.environ.get("LUMENIA_CONFIG_PATH")
    if override:
        return os.path.abspath(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        base_dir = os.path.join(appdata, "Lumenia")
    else:
        base_dir = os.path.join(os.path.expanduser("~"), ".lumenia")
    return os.path.join(base_dir, "config.json")


class ConfigManager(QtCore.QObject):
    """
    Gerenciador singleton de configurações do usuário.
    Garante persistência atômica em JSON e modo de isolamento para testes unitários.
    """

    configChanged = QtCore.Signal(str, str, object)  # (section, key, value)
    sectionChanged = QtCore.Signal(str, dict)       # (section, full_section_dict)
    persistenceFailed = QtCore.Signal(str)

    _instance: Optional["ConfigManager"] = None

    @classmethod
    def instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, config_path: Optional[str] = None, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._config_path = config_path or get_default_config_path()
        self._data: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self._test_mode: bool = False
        self.last_error: str | None = None
        self._read_only_reason: str | None = None

        self.load()

    @property
    def config_path(self) -> str:
        return self._config_path

    @property
    def is_test_mode(self) -> bool:
        return self._test_mode

    def set_test_mode(self, enabled: bool) -> None:
        """
        Ativa/desativa o modo de testes.
        Quando ativado, alterações ficam estritamente em memória e NÃO gravam em disco.
        """
        self._test_mode = enabled
        if enabled:
            self._data = copy.deepcopy(DEFAULT_CONFIG)

    def load(self) -> None:
        """Carrega o arquivo JSON do disco ou realiza migração de versões anteriores."""
        if self._test_mode:
            return

        for candidate in (self._config_path, self._config_path + ".bak"):
            if not os.path.exists(candidate):
                continue
            try:
                loaded = migrate_config(read_object(candidate))
                if isinstance(loaded, dict):
                    self._merge_dicts(self._data, loaded)
                    logger.info(f"[ConfigManager] Configurações carregadas com sucesso de '{self._config_path}'.")
                    return
            except UnsupportedConfigVersion as e:
                self._read_only_reason = self.last_error = str(e)
                logger.error("[ConfigManager] %s", e)
                return
            except Exception as e:
                logger.error(f"[ConfigManager] Falha ao ler '{self._config_path}': {e}. Usando padrões.")

        self._migrate_from_legacy_qsettings()
        self._data = migrate_config(self._data)
        self.save()

    def _merge_dicts(self, target: dict, source: dict) -> None:
        for k, v in source.items():
            if k in target and isinstance(target[k], dict):
                if isinstance(v, dict):
                    self._merge_dicts(target[k], v)
            elif k in target and type(target[k]) is bool:
                if type(v) is bool:
                    target[k] = v
            elif k in target and type(target[k]) is int:
                if type(v) is int and v >= 0:
                    target[k] = v
            elif k in target and isinstance(target[k], list):
                if isinstance(v, list):
                    target[k] = copy.deepcopy(v)
            else:
                target[k] = copy.deepcopy(v)

    def _migrate_from_legacy_qsettings(self) -> None:
        """Migra chaves legadas dispersas no Registro do Windows (QSettings) para o JSON."""
        try:
            from PySide6 import QtCore

            # 1. Locale
            s_i18n = QtCore.QSettings("Aladyn", "Lumenia")
            saved_locale = s_i18n.value("locale/current", None)
            if saved_locale and str(saved_locale).strip():
                loc_str = str(saved_locale).strip()
                if loc_str.lower() in ("auto", "system"):
                    self._data["locale"]["current"] = "auto"
                    self._data["locale"]["auto_detect"] = True
                elif loc_str in ("pt_BR", "en_US", "es_ES", "ja_JP"):
                    self._data["locale"]["current"] = loc_str
                    self._data["locale"]["auto_detect"] = False

            # 2. Barra Flutuante
            s_ft = QtCore.QSettings("Lumenia", "LumeniaApp")
            if s_ft.contains("active"):
                self._data["floating_toolbar"]["active"] = s_ft.value("active", True, type=bool)
            if s_ft.contains("speed"):
                self._data["floating_toolbar"]["speed"] = str(s_ft.value("speed", "Normal"))
            tools_str = s_ft.value("tools", "")
            if tools_str:
                parts = [t.strip() for t in str(tools_str).split(",") if t.strip()]
                if parts:
                    self._data["floating_toolbar"]["tools"] = parts

            # 3. Gavetas (Dock)
            s_dock = QtCore.QSettings("Lumenia", "LumeniaArtStudio")
            if s_dock.contains("dock/auto_collapse"):
                self._data["dock"]["auto_collapse"] = s_dock.value("dock/auto_collapse", False, type=bool)
            if s_dock.contains("dock/speed"):
                self._data["dock"]["speed"] = str(s_dock.value("dock/speed", "Rápido"))
            if s_dock.contains("dock/hover_delay"):
                self._data["dock"]["hover_delay"] = str(s_dock.value("dock/hover_delay", "Normal (350ms)"))

            logger.info("[ConfigManager] Migração concluída com sucesso a partir das chaves legadas do sistema.")
        except Exception as e:
            logger.warning(f"[ConfigManager] Migração parcial do QSettings legados: {e}")

    def save(self) -> bool:
        """Salva atomicamente o estado atual no arquivo JSON."""
        if self._test_mode:
            return True
        if self._read_only_reason:
            self.last_error = self._read_only_reason
            self.persistenceFailed.emit(self.last_error)
            return False

        try:
            save_with_backup(self._config_path, self._data)
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = str(e)
            self.persistenceFailed.emit(self.last_error)
            logger.error(f"[ConfigManager] Erro ao salvar '{self._config_path}': {e}")
            return False

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Obtém um valor da configuração dentro de uma seção."""
        sec = self._data.get(section)
        if isinstance(sec, dict):
            return copy.deepcopy(sec.get(key, default))
        return default

    def set(self, section: str, key: str, value: Any, auto_save: bool = True) -> None:
        """Define um valor em uma seção e emite sinais de alteração."""
        value = normalize_section(section, {key: value})[key]
        if section not in self._data or not isinstance(self._data[section], dict):
            self._data[section] = {}

        if self._data[section].get(key) != value:
            self._data[section][key] = copy.deepcopy(value)
            if auto_save:
                self.save()
            self.configChanged.emit(section, key, value)
            self.sectionChanged.emit(section, copy.deepcopy(self._data[section]))

    def get_section(self, section: str) -> Dict[str, Any]:
        """Retorna uma cópia defensiva de uma seção inteira."""
        sec = self._data.get(section, {})
        if isinstance(sec, dict):
            return copy.deepcopy(sec)
        return {}

    def set_section(self, section: str, data: Dict[str, Any], auto_save: bool = True) -> None:
        """Atualiza múltiplos valores de uma seção atomicamente."""
        data = normalize_section(section, data)
        if section not in self._data or not isinstance(self._data[section], dict):
            self._data[section] = {}

        self._data[section].update(copy.deepcopy(data))
        if auto_save:
            self.save()
        self.sectionChanged.emit(section, copy.deepcopy(self._data[section]))

    def reset_to_defaults(self) -> None:
        """Restaura todas as configurações para o padrão de fábrica."""
        self._data = copy.deepcopy(DEFAULT_CONFIG)
        self.save()
        for sec_name, sec_val in self._data.items():
            if isinstance(sec_val, dict):
                self.sectionChanged.emit(sec_name, copy.deepcopy(sec_val))
