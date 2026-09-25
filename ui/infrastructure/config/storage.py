"""Durable JSON replacement with a validated previous generation."""

import json
import os
import tempfile
from pathlib import Path


def read_object(path):
    with open(path, encoding="utf-8") as stream:
        result = json.load(stream)
    if not isinstance(result, dict):
        raise ValueError("configuração deve ser um objeto JSON")
    return result


def write_object(path, data):
    target = Path(path).absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_with_backup(path, data):
    try:
        previous = read_object(path)
    except (OSError, ValueError):
        previous = None
    if previous is not None:
        write_object(str(path) + ".bak", previous)
    write_object(path, data)
