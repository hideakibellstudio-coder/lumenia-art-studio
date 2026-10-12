"""The release script packs with Velopack (scripts/build_release.py)."""
from __future__ import annotations

from pathlib import Path

from scripts import build_release


def test_the_pack_command_names_the_app_the_channel_and_the_notes():
    command = build_release.vpk_pack_command("0.3.0", "beta", Path("dist"), Path("out"), Path("notes.md"))
    assert command[:2] == ["vpk", "pack"]
    pairs = dict(zip(command[2::2], command[3::2]))
    assert pairs["--packId"] == build_release.PACK_ID and pairs["--packVersion"] == "0.3.0"
    assert pairs["--channel"] == "beta" and pairs["--mainExe"] == "Lumenia.exe"
    assert pairs["--releaseNotes"] == "notes.md"


def test_prereleases_are_read_outside_the_stable_channel():
    assert "--pre" in build_release.vpk_download_command("alpha", Path("out"), None)
    assert "--pre" not in build_release.vpk_download_command("stable", Path("out"), None)


def test_the_upload_hides_the_token_when_printed(capsys):
    build_release._run(["vpk", "upload", "--token", "s3cret"], dry_run=True, secret="s3cret")
    assert "s3cret" not in capsys.readouterr().out
