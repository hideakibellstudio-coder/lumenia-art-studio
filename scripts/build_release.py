"""Builds a release: engine with symbols, Nuitka bundle, Velopack installer and delta, optional upload.

    python scripts/build_release.py --channel stable --notes notas.md
    python scripts/build_release.py --channel beta --notes notas.md --upload      # GITHUB_TOKEN set
    python scripts/build_release.py --channel alpha --dry-run                     # prints the plan

Steps:
  1. `build_native.py --pdb` (the PDB stays in ../build/pdb for reading crash dumps);
  2. `build_portable.py` (Lumenia.dist);
  3. `vpk download github` brings the previous release of the channel, so `vpk pack` can make the delta;
  4. `vpk pack` (Setup.exe, the full package, the delta, the feed) into ../dist/releases/<channel>;
  5. with `--upload`, `vpk upload github` publishes them on the public releases repository.

Requires the .NET SDK and `vpk` on the build machine only (`dotnet tool install -g vpk`);
the user installs nothing.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT.parent / "dist"
PACK_ID = "LumeniaTeam.Lumenia"
RELEASES_REPOSITORY = "https://github.com/hideakibellstudio-coder/lumenia-releases"
CHANNELS = ("stable", "beta", "alpha")


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def vpk_download_command(channel: str, releases_dir: Path, token: str | None) -> list[str]:
    command = ["vpk", "download", "github", "--repoUrl", RELEASES_REPOSITORY, "--channel", channel,
               "--outputDir", str(releases_dir)]
    if channel != "stable":
        command.append("--pre")
    if token:
        command += ["--token", token]
    return command


def vpk_pack_command(version: str, channel: str, dist_dir: Path, releases_dir: Path, notes: Path) -> list[str]:
    return ["vpk", "pack", "--packId", PACK_ID, "--packVersion", version, "--packDir", str(dist_dir),
            "--mainExe", "Lumenia.exe", "--packTitle", "Lumenia", "--packAuthors", "Lumenia Team",
            "--icon", str(ROOT / "assets" / "images" / "icon_lumenia.ico"), "--channel", channel,
            "--releaseNotes", str(notes), "--outputDir", str(releases_dir)]


def vpk_upload_command(version: str, channel: str, releases_dir: Path, token: str) -> list[str]:
    return ["vpk", "upload", "github", "--repoUrl", RELEASES_REPOSITORY, "--channel", channel,
            "--outputDir", str(releases_dir), "--releaseName", f"Lumenia {version} ({channel})",
            "--tag", f"v{version}-{channel}", "--publish", "--token", token]


def _run(command: list[str], dry_run: bool, secret: str | None = None, required: bool = True) -> None:
    shown = " ".join("***" if secret and part == secret else part for part in command)
    print(f"$ {shown}", flush=True)
    if dry_run:
        return
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode and required:
        raise SystemExit(f"falhou ({result.returncode}): {command[0]} {command[1] if len(command) > 1 else ''}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--channel", choices=CHANNELS, default="stable")
    parser.add_argument("--notes", type=Path, help="notas da versão em Markdown")
    parser.add_argument("--upload", action="store_true", help="publica no GitHub (precisa de GITHUB_TOKEN)")
    parser.add_argument("--dry-run", action="store_true", help="só mostra o que faria")
    args = parser.parse_args(argv)

    version = project_version()
    token = os.environ.get("GITHUB_TOKEN")
    if args.upload and not token and not args.dry_run:
        raise SystemExit("--upload precisa da variável GITHUB_TOKEN (permissão de escrever releases)")
    if not args.dry_run and not shutil.which("vpk"):
        raise SystemExit("vpk não encontrado: instale o .NET SDK e rode 'dotnet tool install -g vpk'")
    print(f"Lumenia {version}, canal {args.channel}")

    releases_dir = DIST / "releases" / args.channel
    notes_path = DIST / "releases" / f"notes-{version}-{args.channel}.md"
    notes_text = args.notes.read_text(encoding="utf-8") if args.notes else f"Lumenia {version}"
    if not args.dry_run:
        releases_dir.mkdir(parents=True, exist_ok=True)
        notes_path.write_text(f"{notes_text.strip()}\n", encoding="utf-8")

    _run([sys.executable, "scripts/build_native.py", "--simd", "scalar", "--pdb"], args.dry_run)
    _run([sys.executable, "scripts/build_portable.py"], args.dry_run)
    from scripts.build_portable import DEFAULT_OUTPUT
    # The first release of a channel has nothing to download: no delta, the full package only.
    _run(vpk_download_command(args.channel, releases_dir, token), args.dry_run, token, required=False)
    _run(vpk_pack_command(version, args.channel, DEFAULT_OUTPUT / "Lumenia.dist", releases_dir, notes_path),
         args.dry_run)
    if args.upload:
        _run(vpk_upload_command(version, args.channel, releases_dir, token or "<GITHUB_TOKEN>"), args.dry_run, token)
    print(f"Pronto: {releases_dir}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
