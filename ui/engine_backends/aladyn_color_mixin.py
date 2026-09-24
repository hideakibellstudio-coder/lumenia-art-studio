"""
AladynColorMixin — Gerenciamento Atômico de Amostragem de Cor e Perfis ICC para o AladynBackend.
================================================================================================
Isola a amostragem de cores por Eyedropper (mesclado ou por camada) e os perfis de cor do motor C++,
integrando LittleCMS para perfis arbitrários e simulação de Prova de Cor (Soft-Proofing).
"""

from __future__ import annotations
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from ui.core.color.icc_profile import ICCProfileInfo
from ui.core.color.proofing import SoftProofConfig, RenderingIntent
from ui.core.color.cms_engine import get_cms_engine
from ui.core.color.catalog import get_color_catalog
from .aladyn_base import AladynBackendBase

logger = logging.getLogger(__name__)


class AladynColorMixin(AladynBackendBase):
    """Mixin responsável pela amostragem de cores e perfis de cor no AladynBackend."""

    def pick_color_merged(self, x: int, y: int, sample_radius: int = 0) -> tuple:
        if self._facade:
            return self._facade.pick_color_merged(int(x), int(y), int(sample_radius))
        return (0, 0, 0, 0)

    def pick_color_layer(self, layer_index: int, x: int, y: int, sample_radius: int = 0) -> tuple:
        if self._facade:
            return self._facade.pick_color_layer(int(layer_index), int(x), int(y), int(sample_radius))
        return (0, 0, 0, 0)

    def set_color_profile(self, profile_id: int) -> None:
        profile_id = int(profile_id)
        available_ids = {int(profile["id"]) for profile in self.get_available_color_profiles()}
        if profile_id not in available_ids:
            raise ValueError("perfil de cor desconhecido")
        old_profile_id = self.get_color_profile()
        self._color_profile_id = profile_id
        if self._facade:
            # Para perfis nativos (0-13), sincroniza com a facade C++
            if profile_id <= 13:
                if old_profile_id != int(profile_id):
                    self._mark_document_dirty("color_profile")
                self._facade.set_color_profile(int(profile_id))
            else:
                # Perfil customizado: a facade opera em sRGB neutro e o display é mediado pelo LittleCMS
                self._facade.set_color_profile(0)
                if old_profile_id != int(profile_id):
                    self._mark_document_dirty("color_profile")

    def get_color_profile(self) -> int:
        return self._color_profile_id

    def get_color_profile_name(self, profile_id: int) -> str:
        profiles = self.get_available_color_profiles()
        for p in profiles:
            if p.get("id") == int(profile_id):
                return p.get("name", "Padrão (sRGB)")
        return "Padrão (sRGB)"

    def get_available_color_profiles(self) -> list[dict]:
        """Retorna todos os perfis registrados no catálogo unificado (nativos + customizados)."""
        catalog = get_color_catalog()
        profiles = catalog.get_all_profiles()
        if profiles:
            return profiles
        if self._facade:
            return [dict(p) for p in self._facade.get_available_color_profiles()]
        return []

    # ─── EXTENSÕES PROFISSIONAIS: ICC CUSTOMIZADO & SOFT-PROOFING ─────────────

    def register_custom_color_profile(
        self, source: str | bytes | Path, name: Optional[str] = None, profile_id: Optional[int] = None
    ) -> int:
        """Registra um perfil ICC externo e retorna seu novo ID alocado (>= 100)."""
        catalog = get_color_catalog()
        if isinstance(source, (str, Path)):
            new_id = catalog.register_custom_file(source, profile_id=profile_id)
        else:
            new_id = catalog.register_custom_bytes(source, name=name, profile_id=profile_id)
        if new_id is None:
            raise ValueError("Falha ao analisar ou registrar perfil ICC customizado.")
        return new_id

    def set_soft_proofing(self, config: SoftProofConfig | dict) -> None:
        """Configura a simulação de prova de cor para visualização."""
        if isinstance(config, dict):
            self._soft_proof_config = SoftProofConfig.from_dict(config)
        elif isinstance(config, SoftProofConfig):
            self._soft_proof_config = config
        else:
            raise TypeError("config deve ser SoftProofConfig ou dict")
        self._mark_document_dirty("soft_proof")

    def get_soft_proofing(self) -> SoftProofConfig:
        return self._soft_proof_config

    def get_active_profile_icc_bytes(self) -> Optional[bytes]:
        """Retorna os bytes ICC correspondentes ao perfil ativo no documento."""
        pid = self.get_color_profile()
        catalog = get_color_catalog()
        prof_info = catalog.get_profile(pid)
        if prof_info and prof_info.icc_bytes:
            return prof_info.icc_bytes
        # Se for sRGB padrão (id=0), gera via LittleCMS
        if pid == 0:
            from PIL import ImageCms
            cms = get_cms_engine()
            srgb = cms.get_srgb_profile()
            return ImageCms.ImageCmsProfile(srgb).tobytes()
        return None

    def transform_rgba_for_profile(self, pixels: bytes, profile_id: int) -> bytes:
        """Aplica a transformação colorimétrica ao buffer RGBA."""
        raw = bytes(pixels)
        if len(raw) % 4:
            raise ValueError("pixels RGBA devem ter grupos de quatro bytes")

        # 1. Se Soft-Proofing estiver ativo, a transformação é mediada pelo LittleCMS
        if self._soft_proof_config.enabled:
            return self._transform_with_soft_proof(raw, profile_id)

        # 2. Se for perfil customizado (id >= 100), utiliza LittleCMS
        if int(profile_id) >= 100:
            return self._transform_custom_profile(raw, profile_id)

        # 3. Perfis nativos (0-13): rota acelerada C++
        if self._facade:
            return bytes(self._facade.transform_rgba_for_profile(raw, int(profile_id)))

        if int(profile_id) != 0:
            raise RuntimeError("transformação de perfil indisponível sem o motor Aladyn")
        return raw

    def _transform_with_soft_proof(self, raw: bytes, profile_id: int) -> bytes:
        """Executa a transformação de soft-proofing (Document -> Display com Prova CMYK)."""
        cms = get_cms_engine()
        catalog = get_color_catalog()

        # Perfil de entrada (documento)
        in_prof = cms.get_srgb_profile()
        doc_prof_info = catalog.get_profile(profile_id)
        if doc_prof_info and doc_prof_info.icc_bytes:
            opened_in = cms.open_profile(doc_prof_info.icc_bytes)
            if opened_in:
                in_prof = opened_in

        # Perfil de prova (target press, ex: FOGRA39 / SWOP)
        proof_id = self._soft_proof_config.proof_profile_id
        proof_prof = None
        if self._soft_proof_config.custom_proof_icc:
            proof_prof = cms.open_profile(self._soft_proof_config.custom_proof_icc)
        else:
            target_info = catalog.get_profile(proof_id)
            if target_info and target_info.file_path:
                proof_prof = cms.open_profile(target_info.file_path)
            elif target_info and target_info.icc_bytes:
                proof_prof = cms.open_profile(target_info.icc_bytes)

        # Se não encontrou perfil de prova específico, usa SWOP/FOGRA do sistema ou fallback
        if not proof_prof:
            # Procura RSWOP.icm no sistema como fallback de prova CMYK
            sys_swop = Path(r"C:\Windows\System32\spool\drivers\color\RSWOP.icm")
            if sys_swop.is_file():
                proof_prof = cms.open_profile(str(sys_swop))

        if not proof_prof:
            # Sem perfil de prova disponível, usa o transformador nativo padrão
            if self._facade:
                return bytes(self._facade.transform_rgba_for_profile(raw, int(profile_id)))
            return raw

        # Calcula largura e altura presumidas (ou 1 x N)
        total_pixels = len(raw) // 4
        return cms.transform_rgba_buffer(
            pixels=raw,
            width=total_pixels,
            height=1,
            in_profile=in_prof,
            out_profile=cms.get_srgb_profile(),
            proof_profile=proof_prof,
            intent=self._soft_proof_config.rendering_intent,
            proof_intent=self._soft_proof_config.proof_rendering_intent,
            bpc=self._soft_proof_config.bpc,
            gamut_check=self._soft_proof_config.gamut_warning,
        )

    def _transform_custom_profile(self, raw: bytes, profile_id: int) -> bytes:
        """Converte de um perfil customizado para o espaço de exibição sRGB via LittleCMS."""
        cms = get_cms_engine()
        catalog = get_color_catalog()
        info = catalog.get_profile(profile_id)
        if not info or not info.icc_bytes:
            return raw

        in_prof = cms.open_profile(info.icc_bytes)
        if not in_prof:
            return raw

        total_pixels = len(raw) // 4
        return cms.transform_rgba_buffer(
            pixels=raw,
            width=total_pixels,
            height=1,
            in_profile=in_prof,
            out_profile=cms.get_srgb_profile(),
            intent=int(RenderingIntent.RELATIVE_COLORIMETRIC),
            bpc=True,
        )
