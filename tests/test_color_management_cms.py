"""
Test Suite: LittleCMS Professional Color Management, ICC Profiles, Soft-Proofing & LMN Persistence.
===================================================================================================
Valida a integração do LittleCMS (PIL.ImageCms), transformações colorimétricas,
prova de impressão CMYK (Soft-Proofing), gamut warning, embutimento em LMN e exportação de imagem.
"""

from __future__ import annotations
import io
import os
import shutil
import tempfile
import zipfile
import pytest
from pathlib import Path
from PIL import Image, ImageCms

from ui.core.color.icc_profile import ICCProfileInfo
from ui.core.color.proofing import SoftProofConfig, RenderingIntent
from ui.core.color.cms_engine import get_cms_engine, ColorManagementEngine
from ui.core.color.catalog import get_color_catalog, ColorProfileCatalog
from ui.engine_backends.aladyn import AladynBackend
from ui.core.document.document import Document
from ui.core.document.serializer import DocumentSerializer
from ui.core.document.restore import restore_document
from ui.core.document.schema import DocumentFormatError
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(["--platform", "offscreen"])


@pytest.fixture
def cms():
    return get_cms_engine()


@pytest.fixture
def catalog():
    return get_color_catalog()


@pytest.fixture
def srgb_icc_bytes():
    """Gera bytes binários canônicos de um perfil ICC sRGB via LittleCMS."""
    prof = ImageCms.createProfile("sRGB")
    return ImageCms.ImageCmsProfile(prof).tobytes()


@pytest.fixture
def swop_profile_path():
    """Localiza o perfil CMYK SWOP padrão do Windows caso exista."""
    path = Path(r"C:\Windows\System32\spool\drivers\color\RSWOP.icm")
    return str(path) if path.is_file() else None


# ─── 1. LittleCMS Engine & Perfil sRGB ───────────────────────────────────────

def test_01_cms_engine_srgb_initialization(cms):
    """Valida que o motor LittleCMS inicializa e fornece o perfil sRGB nativo."""
    srgb = cms.get_srgb_profile()
    assert srgb is not None
    info = cms.inspect_profile(ImageCms.ImageCmsProfile(srgb).tobytes())
    assert info is not None
    assert "sRGB" in info.name or "RGB" in info.color_space


def test_02_cms_profile_from_bytes(cms, srgb_icc_bytes):
    """Valida a criação e inspeção estruturada de perfil a partir de bytes em memória."""
    info = cms.inspect_profile(srgb_icc_bytes, profile_id=101)
    assert info is not None
    assert info.id == 101
    assert info.is_custom is True
    assert info.color_space == "RGB"
    assert len(info.sha256) == 64
    assert info.icc_bytes == srgb_icc_bytes


# ─── 2. Soft-Proofing & Gamut Warning LittleCMS ───────────────────────────────

def test_03_soft_proofing_cmyk_transformation(cms, swop_profile_path):
    """Valida que a prova de cor CMYK altera valores saturados de forma consistente."""
    if not swop_profile_path:
        pytest.skip("RSWOP.icm não disponível neste sistema")

    in_prof = cms.get_srgb_profile()
    proof_prof = cms.open_profile(swop_profile_path)
    assert proof_prof is not None

    # Pixel vermelho puro sRGB (255, 0, 0, 255)
    red_pixel = bytes([255, 0, 0, 255])
    transformed = cms.transform_rgba_buffer(
        pixels=red_pixel,
        width=1,
        height=1,
        in_profile=in_prof,
        out_profile=in_prof,
        proof_profile=proof_prof,
        intent=int(RenderingIntent.RELATIVE_COLORIMETRIC),
        proof_intent=int(RenderingIntent.RELATIVE_COLORIMETRIC),
        bpc=True,
        gamut_check=False,
    )
    assert len(transformed) == 4
    # Em CMYK SWOP, vermelho 255 perde um pouco da saturação absoluta RGB
    assert tuple(transformed) != (255, 0, 0, 255)
    assert transformed[3] == 255  # Alpha preservado


def test_04_gamut_warning_highlights_out_of_gamut(cms, swop_profile_path):
    """Valida que o Gamut Warning substitui cores fora de gama por código de alarme."""
    if not swop_profile_path:
        pytest.skip("RSWOP.icm não disponível neste sistema")

    in_prof = cms.get_srgb_profile()
    proof_prof = cms.open_profile(swop_profile_path)

    # Verde super saturado (0, 255, 0) está tipicamente fora do gamut CMYK SWOP
    green_pixel = bytes([0, 255, 0, 255])
    gamut_out = cms.transform_rgba_buffer(
        pixels=green_pixel,
        width=1,
        height=1,
        in_profile=in_prof,
        out_profile=in_prof,
        proof_profile=proof_prof,
        intent=int(RenderingIntent.RELATIVE_COLORIMETRIC),
        proof_intent=int(RenderingIntent.RELATIVE_COLORIMETRIC),
        bpc=True,
        gamut_check=True,
    )
    # Com GAMUTCHECK ativo, o LittleCMS marca o pixel fora de gama (cinza neutro)
    assert tuple(gamut_out[:3]) == (128, 128, 128) or tuple(gamut_out[:3]) == (127, 127, 127)


# ─── 3. Catálogo Unificado de Perfis ──────────────────────────────────────────

def test_05_catalog_contains_builtins_and_system(catalog):
    """Valida que o catálogo unificado contém todos os 14 perfis nativos."""
    profiles = catalog.get_all_profiles()
    assert len(profiles) >= 14
    ids = [p["id"] for p in profiles]
    for expected_id in range(14):
        assert expected_id in ids

    # Testa busca de perfil individual
    p0 = catalog.get_profile(0)
    assert p0 is not None and p0.name == "Padrão (sRGB)"


def test_06_catalog_register_custom_bytes(catalog, srgb_icc_bytes):
    """Valida o registro de um perfil customizado no catálogo."""
    new_id = catalog.register_custom_bytes(srgb_icc_bytes, name="Meu Perfil Monitor")
    assert new_id >= 100
    info = catalog.get_profile(new_id)
    assert info is not None
    assert info.name == "Meu Perfil Monitor"
    assert info.icc_bytes == srgb_icc_bytes
    assert info.is_custom is True


# ─── 4. Integração com Backend & Soft-Proofing ───────────────────────────────

def test_07_backend_soft_proofing_and_custom_profiles():
    """Valida a configuração de soft-proofing e perfis customizados no AladynBackend."""
    backend = AladynBackend()
    try:
        assert backend.supports_capability("soft_proofing")
        assert backend.supports_capability("custom_color_profiles")

        # Configura soft-proofing
        config = SoftProofConfig(enabled=True, proof_profile_id=4, gamut_warning=False)
        backend.set_soft_proofing(config)
        retrieved = backend.get_soft_proofing()
        assert retrieved.enabled is True
        assert retrieved.proof_profile_id == 4

        # A prova CMYK precisa de um perfil CMYK instalado (no Windows, o
        # RSWOP.icm do sistema). Sem ele o backend cai no caminho nativo, que
        # é identidade para sRGB -- não há o que comparar nesta máquina.
        swop = Path(r"C:\Windows\System32\spool\drivers\color\RSWOP.icm")
        proof_info = get_color_catalog().get_profile(4)
        has_proof_profile = swop.is_file() or bool(proof_info and (proof_info.file_path or proof_info.icc_bytes))
        if not has_proof_profile:
            pytest.skip("sem perfil CMYK de prova instalado nesta máquina")

        # Testa transformação de buffer com soft-proofing ativo
        src_buf = bytes([200, 100, 50, 255] * 10)
        transformed = backend.transform_rgba_for_profile(src_buf, profile_id=0)
        assert len(transformed) == len(src_buf)
        assert transformed != src_buf  # Sofreu transformação de prova
    finally:
        backend.close_document_context("default_doc")


# ─── 5. Persistência LMN com Perfil ICC Embutido ─────────────────────────────

def test_08_lmn_roundtrip_with_embedded_icc_profile(tmp_path, srgb_icc_bytes):
    """Valida que um documento com perfil ICC customizado embute o arquivo no LMN e o restaura perfeitamente."""
    backend = AladynBackend()
    doc_uid = "icc-test-doc"
    try:
        w, h = 4, 4
        doc = Document(doc_uid, "Arte com ICC", width=w, height=h)
        doc.layer_manager.add_layer("Pintura")
        backend.set_active_document_context(doc_uid, w, h)
        doc.color_profile_icc_bytes = srgb_icc_bytes
        doc.color_profile_name = "Studio Wide Gamut ICC"

        # Registra perfil no backend com ID 150
        pid = backend.register_custom_color_profile(srgb_icc_bytes, name="Studio Wide Gamut ICC", profile_id=150)
        assert pid == 150
        backend.set_color_profile(150)

        # Salva para arquivo .lmn
        lmn_file = tmp_path / "arte_com_icc.lmn"
        saved_path = DocumentSerializer.save(doc, backend, lmn_file)
        assert Path(saved_path).is_file()

        # Inspeciona o arquivo ZIP LMN gerado
        with zipfile.ZipFile(saved_path, "r") as z:
            namelist = z.namelist()
            assert "profiles/document.icc" in namelist
            assert "manifest.json" in namelist
            manifest_raw = z.read("manifest.json").decode("utf-8")
            assert '"color_profile_payload": "profiles/document.icc"' in manifest_raw
            assert '"color_profile_id": 150' in manifest_raw

            # Valida que os bytes salvos batem exatamente com o perfil original
            saved_icc_bytes = z.read("profiles/document.icc")
            assert saved_icc_bytes == srgb_icc_bytes

        # Restaura o documento em uma nova instância limpa
        restored_doc: Document = Document("restored-icc-doc", "Restaurado", width=w, height=h)
        manifest, payloads = DocumentSerializer.read(saved_path)
        backend.set_active_document_context(restored_doc.uid, w, h)
        restore_document(restored_doc, backend, manifest, payloads)

        assert restored_doc.color_profile_icc_bytes == srgb_icc_bytes
        assert restored_doc.color_profile_name == "Studio Wide Gamut ICC"
        assert backend.get_color_profile() == 150
    finally:
        backend.close_document_context(doc_uid)
        backend.close_document_context("restored-icc-doc")


# ─── 6. Exportação de Imagem com ICC Embutido ─────────────────────────────────

def test_09_export_image_embeds_icc_profile(tmp_path, srgb_icc_bytes):
    """Valida que a exportação de PNG/JPEG embute os metadados do perfil ICC ativo."""
    backend = AladynBackend()
    try:
        # Registra perfil customizado no backend
        pid = backend.register_custom_color_profile(srgb_icc_bytes, name="Export Test Profile")
        backend.set_color_profile(pid)

        # Exporta PNG
        png_path = tmp_path / "export_test.png"
        success = backend.export_image(png_path, embed_icc=True)
        assert success is True
        assert png_path.is_file() and png_path.stat().st_size > 0

        # Abre o PNG gerado com Pillow e valida a presença dos metadados ICC
        with Image.open(png_path) as exported_img:
            assert "icc_profile" in exported_img.info
            exported_icc = exported_img.info["icc_profile"]
            assert exported_icc == srgb_icc_bytes
    finally:
        backend.close_document_context("default_doc")
