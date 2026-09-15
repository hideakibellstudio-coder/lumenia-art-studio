"""
ColorProfileCatalog — Catálogo Canônico Unificado de Perfis de Cor.
===================================================================
Reúne perfis nativos (IDs 0-13), perfis do sistema Windows e perfis customizados
do usuário carregados dinamicamente via LittleCMS.
"""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .icc_profile import ICCProfileInfo
from .cms_engine import get_cms_engine

logger = logging.getLogger(__name__)

# Perfis nativos canônicos (compatibilidade 100% com Aladyn C++ ColorProfileManager)
BUILTIN_PROFILES: List[Dict[str, Any]] = [
    {"id": 0, "name": "Padrão (sRGB)", "category": "Digital (RGB)", "description": "Espaço de cor padrão universal para telas e web", "gamut": "sRGB IEC61966-2.1", "whitepoint": "D65 (6500K)", "transfer": "sRGB"},
    {"id": 1, "name": "Display P3 (Wide-Gamut)", "category": "Digital (RGB)", "description": "Espaço de cor expandido para telas modernas", "gamut": "DCI-P3 D65", "whitepoint": "D65 (6500K)", "transfer": "sRGB Transfer"},
    {"id": 2, "name": "Adobe RGB (1998)", "category": "Digital (RGB)", "description": "Gamut ampliado para fotografia e pré-impressão", "gamut": "Adobe RGB 1998", "whitepoint": "D65 (6500K)", "transfer": "Gamma 2.2"},
    {"id": 3, "name": "Rec. 2020 (UHD TV)", "category": "Digital (RGB)", "description": "Gamut ultra-amplo para vídeo UHD", "gamut": "BT.2020", "whitepoint": "D65 (6500K)", "transfer": "ITU-R BT.2020"},
    {"id": 4, "name": "U.S. Web Coated (SWOP) v2", "category": "Impressão (CMYK)", "description": "Padrão americano para papel couché", "gamut": "SWOP v2 (CMYK)", "whitepoint": "D50 (5000K)", "transfer": "Press Tone Value"},
    {"id": 5, "name": "ISO Coated v2 (FOGRA39)", "category": "Impressão (CMYK)", "description": "Referência europeia ISO 12647-2", "gamut": "FOGRA39 (CMYK)", "whitepoint": "D50 (5000K)", "transfer": "ISO 12647-2"},
    {"id": 6, "name": "GRACoL 2006", "category": "Impressão (CMYK)", "description": "Especificação comercial G7", "gamut": "GRACoL 2006", "whitepoint": "D50 (5000K)", "transfer": "G7 Curves"},
    {"id": 7, "name": "Japan Color 2001 Coated", "category": "Impressão (CMYK)", "description": "Padrão japonês para papel revestido", "gamut": "Japan Color 2001", "whitepoint": "D50 (5000K)", "transfer": "Japan Print Std"},
    {"id": 8, "name": "Protanopia (Sem Vermelho)", "category": "Acessibilidade", "description": "Simulação de daltonismo para receptores L", "gamut": "Simulação Protanopia", "whitepoint": "D65", "transfer": "Linear Match"},
    {"id": 9, "name": "Deuteranopia (Sem Verde)", "category": "Acessibilidade", "description": "Simulação de daltonismo para receptores M", "gamut": "Simulação Deuteranopia", "whitepoint": "D65", "transfer": "Linear Match"},
    {"id": 10, "name": "Tritanopia (Sem Azul)", "category": "Acessibilidade", "description": "Simulação de daltonismo para receptores S", "gamut": "Simulação Tritanopia", "whitepoint": "D65", "transfer": "Linear Match"},
    {"id": 11, "name": "Acromatopsia (Monocromático)", "category": "Acessibilidade", "description": "Prova de luminância Rec.709", "gamut": "Luminância Pura (Y)", "whitepoint": "D65", "transfer": "Luminance Rec.709"},
    {"id": 12, "name": "Linear sRGB (Physical Blending)", "category": "Motor Físico", "description": "Mistura fotométrica linear", "gamut": "sRGB Primaries", "whitepoint": "D65 (6500K)", "transfer": "1.0 (Linear)"},
    {"id": 13, "name": "ACEScg (Academy Color Encoding)", "category": "Motor Físico", "description": "Codificação linear para VFX", "gamut": "AP1 Primaries", "whitepoint": "D60 (ACES)", "transfer": "1.0 (Linear Float)"},
]


class ColorProfileCatalog:
    """Catálogo unificado de perfis disponíveis para a interface e o motor."""

    _instance: Optional[ColorProfileCatalog] = None

    def __init__(self) -> None:
        self._profiles_by_id: Dict[int, ICCProfileInfo] = {}
        self._next_custom_id: int = 100
        self._init_builtins()
        self._discover_system_profiles()

    @classmethod
    def instance(cls) -> ColorProfileCatalog:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_builtins(self) -> None:
        for item in BUILTIN_PROFILES:
            info = ICCProfileInfo(
                id=item["id"],
                name=item["name"],
                category=item["category"],
                description=item["description"],
                gamut=item.get("gamut", ""),
                whitepoint=item.get("whitepoint", "D65 (6500K)"),
                transfer=item.get("transfer", "sRGB"),
                color_space="CMYK" if "CMYK" in item["category"] else "RGB",
                is_custom=False,
            )
            self._profiles_by_id[info.id] = info

    def _discover_system_profiles(self) -> None:
        try:
            sys_profiles = get_cms_engine().discover_windows_profiles()
            for prof in sys_profiles:
                # Evita sobrescrever os IDs built-in (0 a 13)
                if prof.id not in self._profiles_by_id:
                    self._profiles_by_id[prof.id] = prof
        except Exception as exc:
            logger.debug("Não foi possível carregar perfis do Windows: %s", exc)

    def get_profile(self, profile_id: int) -> Optional[ICCProfileInfo]:
        return self._profiles_by_id.get(int(profile_id))

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Retorna todos os perfis registrados formatados como dicionários."""
        # Ordena: Builtins primeiro (0-13), depois customizados (100+), depois sistema (200+)
        sorted_profiles = sorted(self._profiles_by_id.values(), key=lambda p: p.id)
        return [p.to_dict() for p in sorted_profiles]

    def register_custom_profile(self, info: ICCProfileInfo, profile_id: Optional[int] = None) -> int:
        """Registra um perfil customizado no catálogo e atribui um ID único caso necessário."""
        target_id = int(profile_id) if profile_id is not None and int(profile_id) >= 100 else info.id
        if target_id < 100:
            target_id = self._next_custom_id
        if target_id in self._profiles_by_id and profile_id is None:
            target_id = self._next_custom_id
            self._next_custom_id += 1
        else:
            self._next_custom_id = max(self._next_custom_id, target_id + 1)
        info.id = target_id
        info.is_custom = True
        self._profiles_by_id[info.id] = info
        return info.id

    def register_custom_file(self, file_path: str | Path, profile_id: Optional[int] = None) -> Optional[int]:
        """Carrega e inspeciona um arquivo .icc/.icm externo e o registra no catálogo."""
        cms = get_cms_engine()
        info = cms.inspect_profile(file_path, profile_id=profile_id or self._next_custom_id)
        if not info:
            return None
        return self.register_custom_profile(info, profile_id=profile_id)

    def register_custom_bytes(self, raw_bytes: bytes, name: Optional[str] = None, profile_id: Optional[int] = None) -> Optional[int]:
        """Registra um perfil a partir de bytes ICC incorporados em um documento LMN."""
        cms = get_cms_engine()
        info = cms.inspect_profile(raw_bytes, profile_id=profile_id or self._next_custom_id)
        if not info:
            return None
        if name:
            info.name = name
        return self.register_custom_profile(info, profile_id=profile_id)


def get_color_catalog() -> ColorProfileCatalog:
    return ColorProfileCatalog.instance()
