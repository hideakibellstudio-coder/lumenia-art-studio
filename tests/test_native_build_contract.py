from scripts.build_native import artifact_metadata


def test_native_build_metadata_describes_the_loaded_artifact():
    metadata = artifact_metadata("scalar")
    assert metadata["schema_version"] == "1"
    assert metadata["simd"] == "scalar"
    assert metadata["extension_file"].endswith(".pyd")
    assert len(metadata["extension_sha256"]) == 64
