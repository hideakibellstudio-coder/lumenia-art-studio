"""
ColorManagementEngine — Motor de Gestão de Cor baseado em LittleCMS 2.x (Pillow ImageCms).
===========================================================================================
Executa carregamento de perfis ICC, transformações de cores colorimétricas,
conversões de espaço de trabalho, e simulação de prova de cor (Soft-Proofing).
"""

from __future__ import annotations
import io
import os
import sys
import glob
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from PIL import Image, ImageCms
from .icc_profile import ICCProfileInfo
from .proofing import SoftProofConfig, RenderingIntent

logger = logging.getLogger(__name__)


class ColorManagementEngine:
    """Motor LittleCMS para Lumenia. Cacheia perfis e transformadores de alto desempenho."""

    _instance: Optional[ColorManagementEngine] = None

    def __init__(self) -> None:
        self._profiles_cache: Dict[str, ImageCms.ImageCmsProfile] = {}
        self._transforms_cache: Dict[Tuple, ImageCms.ImageCmsTransform] = {}
        self._srgb_profile = self._init_srgb()

    @classmethod
    def instance(cls) -> ColorManagementEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_srgb(self) -> ImageCms.ImageCmsProfile:
        try:
            profile = ImageCms.createProfile("sRGB")
            self._profiles_cache["sRGB"] = profile
            return profile
        except Exception as exc:
            logger.error("Falha ao inicializar perfil interno sRGB LittleCMS: %s", exc)
            raise

    def get_srgb_profile(self) -> ImageCms.ImageCmsProfile:
        return self._srgb_profile

    # ── CARREGAMENTO DE PERFIS ICC ───────────────────────────────────────────

    def open_profile(self, source: str | bytes | Path) -> Optional[ImageCms.ImageCmsProfile]:
        """Abre e cacheia um perfil ICC a partir de um caminho em disco ou bytes em memória."""
        key: str
        if isinstance(source, (str, Path)):
            path_obj = Path(source).resolve()
            if not path_obj.is_file():
                logger.warning("Arquivo de perfil ICC não encontrado: %s", source)
                return None
            key = str(path_obj)
            if key in self._profiles_cache:
                return self._profiles_cache[key]
            try:
                profile = ImageCms.getOpenProfile(str(path_obj))
                self._profiles_cache[key] = profile
                return profile
            except Exception as exc:
                logger.warning("Erro ao carregar perfil ICC de '%s': %s", path_obj, exc)
                return None
        elif isinstance(source, bytes):
            import hashlib
            key = hashlib.sha256(source).hexdigest()
            if key in self._profiles_cache:
                return self._profiles_cache[key]
            try:
                stream = io.BytesIO(source)
                profile = ImageCms.getOpenProfile(stream)
                self._profiles_cache[key] = profile
                return profile
            except Exception as exc:
                logger.warning("Erro ao decodificar bytes de perfil ICC (%s bytes): %s", len(source), exc)
                return None
        return None

    def inspect_profile(self, source: str | bytes | Path, profile_id: int = 100) -> Optional[ICCProfileInfo]:
        """Analisa um perfil ICC e extrai todos os metadados canônicos estruturados."""
        cms_prof = self.open_profile(source)
        if not cms_prof:
            return None

        raw_bytes: Optional[bytes] = None
        file_path: Optional[str] = None
        if isinstance(source, (str, Path)):
            file_path = str(Path(source).resolve())
            try:
                raw_bytes = Path(source).read_bytes()
            except OSError:
                pass
        elif isinstance(source, bytes):
            raw_bytes = source

        prof_core = getattr(cms_prof, "profile", cms_prof)
        desc = getattr(prof_core, "profile_description", "")
        if not desc:
            desc = Path(file_path).stem if file_path else f"Perfil {profile_id}"

        c_space = str(getattr(prof_core, "xcolor_space", "RGB")).strip()
        conn_space = str(getattr(prof_core, "connection_space", "XYZ ")).strip()

        # Determina a categoria adequada
        category = "Digital (RGB)"
        if "CMYK" in c_space.upper():
            category = "Impressão (CMYK)"
        elif "GRAY" in c_space.upper():
            category = "Escala de Cinza"

        return ICCProfileInfo(
            id=profile_id,
            name=desc,
            category=category,
            description=f"Perfil ICC {c_space} ({conn_space})",
            color_space=c_space,
            connection_space=conn_space,
            gamut=c_space,
            whitepoint="D50 / D65",
            transfer="ICC Tagged",
            file_path=file_path,
            icc_bytes=raw_bytes,
            is_custom=True,
        )

    # ── DESCOBERTA DE PERFIS DO SISTEMA OPERACIONAL ──────────────────────────

    def discover_windows_profiles(self) -> List[ICCProfileInfo]:
        """Varre o diretório do spooler de cores do Windows em busca de perfis válidos."""
        discovered: List[ICCProfileInfo] = []
        if sys.platform != "win32":
            return discovered

        spool_dir = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "spool" / "drivers" / "color"
        if not spool_dir.is_dir():
            return discovered

        curr_id = 200
        for pattern in ("*.icc", "*.icm"):
            for entry in spool_dir.glob(pattern):
                try:
                    info = self.inspect_profile(entry, profile_id=curr_id)
                    if info:
                        info.is_custom = False
                        discovered.append(info)
                        curr_id += 1
                except Exception as exc:
                    logger.debug("Ignorando perfil do sistema '%s': %s", entry.name, exc)

        return discovered

    # ── CONSTRUÇÃO E CACHE DE TRANSFORMAÇÕES LITTLECMS ────────────────────────

    def _get_transform(
        self,
        in_prof: ImageCms.ImageCmsProfile,
        out_prof: ImageCms.ImageCmsProfile,
        proof_prof: Optional[ImageCms.ImageCmsProfile] = None,
        intent: int = 1,
        proof_intent: int = 1,
        bpc: bool = True,
        gamut_check: bool = False,
    ) -> Optional[ImageCms.ImageCmsTransform]:
        """Recupera ou compila um transformador LittleCMS otimizado."""
        in_key = id(in_prof)
        out_key = id(out_prof)
        proof_key = id(proof_prof) if proof_prof else 0
        cache_key = (in_key, out_key, proof_key, intent, proof_intent, bpc, gamut_check)

        if cache_key in self._transforms_cache:
            return self._transforms_cache[cache_key]

        try:
            flags = ImageCms.Flags.HIGHRESPRECALC
            if bpc:
                flags |= ImageCms.Flags.BLACKPOINTCOMPENSATION

            intent_enum = ImageCms.Intent(intent)
            proof_intent_enum = ImageCms.Intent(proof_intent)

            if proof_prof is not None:
                proof_flags = flags | ImageCms.Flags.SOFTPROOFING
                if gamut_check:
                    proof_flags |= ImageCms.Flags.GAMUTCHECK
                transform = ImageCms.buildProofTransform(
                    inputProfile=in_prof,
                    outputProfile=out_prof,
                    proofProfile=proof_prof,
                    inMode="RGBA",
                    outMode="RGBA",
                    renderingIntent=intent_enum,
                    proofRenderingIntent=proof_intent_enum,
                    flags=proof_flags,
                )
            else:
                transform = ImageCms.buildTransform(
                    inputProfile=in_prof,
                    outputProfile=out_prof,
                    inMode="RGBA",
                    outMode="RGBA",
                    renderingIntent=intent_enum,
                    flags=flags,
                )
            self._transforms_cache[cache_key] = transform
            return transform
        except Exception as exc:
            logger.error("Falha ao compilar transformador LittleCMS: %s", exc)
            return None

    # ── EXECUÇÃO DE TRANSFORMAÇÃO SOBRE BUFFERS RGBA ─────────────────────────

    def transform_rgba_buffer(
        self,
        pixels: bytes,
        width: int,
        height: int,
        in_profile: ImageCms.ImageCmsProfile,
        out_profile: ImageCms.ImageCmsProfile,
        proof_profile: Optional[ImageCms.ImageCmsProfile] = None,
        intent: int = 1,
        proof_intent: int = 1,
        bpc: bool = True,
        gamut_check: bool = False,
    ) -> bytes:
        """Aplica a transformação colorimétrica de cores em um buffer RGBA de largura x altura."""
        if not pixels or width <= 0 or height <= 0:
            return pixels
        expected_len = width * height * 4
        if len(pixels) != expected_len:
            raise ValueError(f"Tamanho do buffer ({len(pixels)}) não bate com {width}x{height}x4 ({expected_len})")

        transform = self._get_transform(
            in_prof=in_profile,
            out_prof=out_profile,
            proof_prof=proof_profile,
            intent=intent,
            proof_intent=proof_intent,
            bpc=bpc,
            gamut_check=gamut_check,
        )
        if not transform:
            return pixels

        try:
            # Envolve o buffer RGBA existente sem cópia preliminar redundante
            img = Image.frombuffer("RGBA", (width, height), pixels, "raw", "RGBA", 0, 1)
            out_img = ImageCms.applyTransform(img, transform)
            return out_img.tobytes()
        except Exception as exc:
            logger.warning("Falha na execução de applyTransform: %s. Mantendo buffer original.", exc)
            return pixels


def get_cms_engine() -> ColorManagementEngine:
    return ColorManagementEngine.instance()
