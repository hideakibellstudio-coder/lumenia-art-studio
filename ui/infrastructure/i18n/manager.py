"""
I18nManager — Sistema Central de Internacionalização e Idiomas (Lumenia V2 / ARCcC).
=====================================================================================
Gerenciador singleton reativo para suporte a múltiplos idiomas com detecção automática do
sistema operacional, fallback inteligente para en_US, interpolação de parâmetros,
persistência de preferências em QSettings e emissão de sinal Qt para retranslation
dinâmico em tempo real (zero restart).
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, Optional
from PySide6 import QtCore
from ui.infrastructure.runtime_paths import resource_path

logger = logging.getLogger(__name__)


class I18nManager(QtCore.QObject):
    """Gerenciador central de idiomas e traduções do ecossistema Lumenia."""

    languageChanged = QtCore.Signal(str)

    _instance: Optional["I18nManager"] = None

    # Catálogo de idiomas oficialmente suportados
    SUPPORTED_LOCALES: Dict[str, str] = {
        "pt_BR": "Português (Brasil)",
        "en_US": "English (US)",
        "es_ES": "Español",
        "ja_JP": "日本語 (Japanese)",
    }

    @classmethod
    def instance(cls) -> "I18nManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def detect_system_locale(cls) -> str:
        """
        Detecta o idioma do sistema operacional e mapeia para um dos idiomas suportados.
        Se o idioma do sistema não estiver entre os suportados, retorna 'en_US' (fallback global).
        """
        sys_locale = QtCore.QLocale.system()
        name = sys_locale.name()
        lang = sys_locale.language()

        # 1. Correspondência exata de código de locale
        if name in cls.SUPPORTED_LOCALES:
            return name

        # 2. Correspondência por família de idioma
        if lang == QtCore.QLocale.Language.Portuguese or name.startswith("pt"):
            return "pt_BR"
        if lang == QtCore.QLocale.Language.Spanish or name.startswith("es"):
            return "es_ES"
        if lang == QtCore.QLocale.Language.Japanese or name.startswith("ja"):
            return "ja_JP"
        if lang == QtCore.QLocale.Language.English or name.startswith("en"):
            return "en_US"

        # 3. Fallback internacional padrão: Inglês (en_US)
        return "en_US"

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._locales_dir = self._resolve_locales_directory()
        self._current_locale = "en_US"
        self._is_auto = True
        self._active_dict: Dict[str, Any] = {}
        self._fallback_dict: Dict[str, Any] = {}

        # 1. Carrega o dicionário base canônico de fallback (en_US)
        self._fallback_dict = self._load_locale_file("en_US")

        # 2. Restaura o idioma salvo nas preferências ou detecta o idioma do sistema operacional
        from ui.infrastructure.config import ConfigManager
        saved_locale = ConfigManager.instance().get("locale", "current", "auto")

        if saved_locale is None or str(saved_locale).lower() in ("auto", "system", ""):
            self._is_auto = True
            chosen_locale = self.detect_system_locale()
            logger.info(f"[I18nManager] Idioma do SO detectado automaticamente: {chosen_locale}")
        elif str(saved_locale) in self.SUPPORTED_LOCALES:
            self._is_auto = False
            chosen_locale = str(saved_locale)
        else:
            self._is_auto = True
            chosen_locale = self.detect_system_locale()

        self.set_locale(chosen_locale, is_auto=self._is_auto, emit_signal=False)

    def _resolve_locales_directory(self) -> str:
        """Find read-only locales in either the checkout or the portable bundle."""
        return str(resource_path("assets", "locales"))

    def _load_locale_file(self, locale_code: str) -> Dict[str, Any]:
        """Carrega e decodifica o arquivo JSON de um idioma com codificação UTF-8."""
        file_path = os.path.join(self._locales_dir, f"{locale_code}.json")
        if not os.path.exists(file_path):
            logger.debug(f"[I18nManager] Arquivo de idioma não encontrado: {file_path}")
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[I18nManager] Erro ao carregar catálogo {file_path}: {e}")
            return {}

    def get_available_locales(self) -> Dict[str, str]:
        """Retorna o dicionário de códigos e nomes de exibição dos idiomas suportados."""
        return self.SUPPORTED_LOCALES.copy()

    def get_current_locale(self) -> str:
        """Retorna o código do idioma atualmente ativo (ex: 'pt_BR', 'en_US')."""
        return self._current_locale

    def is_auto_mode(self) -> bool:
        """Retorna True se o idioma estiver sincronizado com o SO do usuário."""
        return self._is_auto

    def set_auto_mode(self, emit_signal: bool = True) -> None:
        """Ativa o modo de detecção automática do SO e recarrega o idioma apropriado."""
        detected = self.detect_system_locale()
        self.set_locale(detected, is_auto=True, emit_signal=emit_signal)

    def set_locale(self, locale_code: str, is_auto: bool = False, emit_signal: bool = True) -> bool:
        """
        Define o idioma ativo da aplicação, carrega o catálogo correspondente,
        persiste no QSettings e emite o sinal 'languageChanged'.
        """
        if locale_code not in self.SUPPORTED_LOCALES:
            logger.warning(f"[I18nManager] Idioma '{locale_code}' não suportado. Mantendo '{self._current_locale}'.")
            return False

        self._is_auto = is_auto
        self._current_locale = locale_code
        self._active_dict = self._load_locale_file(locale_code)

        # Persiste no ConfigManager (JSON)
        from ui.infrastructure.config import ConfigManager
        val = "auto" if is_auto else locale_code
        ConfigManager.instance().set("locale", "current", val, auto_save=False)
        ConfigManager.instance().set("locale", "auto_detect", is_auto, auto_save=True)

        logger.info(f"[I18nManager] Idioma alterado para '{locale_code}' (auto={is_auto}).")

        if emit_signal:
            self.languageChanged.emit(locale_code)

        return True

    def _lookup_key(self, dictionary: Dict[str, Any], dot_key: str) -> Optional[str]:
        """Busca uma chave hierárquica separada por pontos (ex: 'menu.file.new') no dicionário."""
        parts = dot_key.split(".")
        curr: Any = dictionary
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                return None
        return str(curr) if isinstance(curr, (str, int, float)) else None

    def translate(self, key: str, default: str = "", **kwargs: Any) -> str:
        """
        Traduz uma chave para o idioma ativo com suporte a interpolação e fallback em cascata:
        1. Dicionário do Idioma Ativo
        2. Dicionário Canônico de Fallback (en_US)
        3. Valor 'default' fornecido
        4. A própria 'key'
        """
        # 1. Busca no idioma ativo
        val = self._lookup_key(self._active_dict, key)

        # 2. Fallback para en_US se não encontrar
        if val is None and self._fallback_dict:
            val = self._lookup_key(self._fallback_dict, key)

        # 3. Fallback para o default ou a própria chave
        if val is None:
            val = default if default else key

        # 4. Interpolação segura de variáveis (ex: {name}, {count})
        if kwargs:
            try:
                val = val.format(**kwargs)
            except Exception as e:
                logger.debug(f"[I18nManager] Falha ao interpolar chave '{key}' com {kwargs}: {e}")

        return val

    def t(self, key: str, default: str = "", **kwargs: Any) -> str:
        """Alias conveniente para translate()."""
        return self.translate(key, default, **kwargs)


def tr(key: str, default: str = "", **kwargs: Any) -> str:
    """Função universal para tradução de strings na UI e Plugins."""
    return I18nManager.instance().translate(key, default, **kwargs)
