"""The release script refuses the development license key and packs with Velopack (scripts/build_release.py)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts import build_release

DEV_HEADER = 'inline constexpr std::string_view kLicenseKeyName = "dev";'
PROD_HEADER = 'inline constexpr std::string_view kLicenseKeyName = "prod";'


def test_a_build_that_trusts_the_development_key_is_refused():
    with pytest.raises(SystemExit, match="DESENVOLVIMENTO"):
        build_release.ensure_release_key(DEV_HEADER, allow_dev_key=False)
    assert build_release.ensure_release_key(DEV_HEADER, allow_dev_key=True) == "dev"
    assert build_release.ensure_release_key(PROD_HEADER, allow_dev_key=False) == "prod"
    with pytest.raises(SystemExit):
        build_release.trusted_key_name("// nothing here")


def test_the_repository_header_names_a_key():
    text = build_release.PUBLIC_KEY_HEADER.read_text(encoding="utf-8")
    assert build_release.trusted_key_name(text) in ("dev", "prod")


def test_release_notes_carry_the_release_date_the_program_reads():
    from ui.core.updates import UpdateOffer

    notes = build_release.release_notes("## Novidades\n", date(2026, 10, 8))
    assert UpdateOffer("0.3.0", notes).release_date == "2026-10-08"


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
