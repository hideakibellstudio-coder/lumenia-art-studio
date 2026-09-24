import sys

import pytest

from scripts.build_native import artifact_metadata


# O artefato de release é o .pyd do Windows copiado para a raiz pelo
# build_native.py; em outras plataformas não há o que descrever.
@pytest.mark.skipif(sys.platform != "win32", reason="artefato de release (.pyd) só existe no Windows")
def test_native_build_metadata_describes_the_loaded_artifact():
    metadata = artifact_metadata("scalar")
    assert metadata["schema_version"] == "1"
    assert metadata["simd"] == "scalar"
    assert metadata["extension_file"].endswith(".pyd")
    assert len(metadata["extension_sha256"]) == 64
