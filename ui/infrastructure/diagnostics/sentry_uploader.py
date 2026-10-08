"""Sends a report bundle to Sentry (or to a self-hosted Sentry/GlitchTip), with no SDK.

Only HTTP from the standard library: a minidump goes to the minidump endpoint
(Sentry symbolicates it with the PDB uploaded for that build); a report without a
dump goes as an event in an envelope. The DSN comes from `app_info.CRASH_REPORT_DSN`
or the `LUMENIA_CRASH_DSN` variable; without one, nothing is sent and the user
gets the zip to attach to an e-mail.
"""

from __future__ import annotations

import json
import time
import urllib.request
import uuid
from dataclasses import dataclass
from urllib.parse import urlparse

TIMEOUT_SECONDS = 20
CLIENT = "lumenia-crash/1"


@dataclass(frozen=True)
class SentryEndpoint:
    scheme: str
    host: str
    project: str
    public_key: str

    @classmethod
    def parse(cls, dsn: str) -> "SentryEndpoint | None":
        """`https://<key>@o123.ingest.sentry.io/456` -> endpoint; None for an empty or odd DSN."""
        parsed = urlparse(dsn.strip())
        project = parsed.path.strip("/")
        if parsed.scheme not in ("http", "https") or not parsed.username or not parsed.hostname or not project:
            return None
        host = parsed.hostname + (f":{parsed.port}" if parsed.port else "")
        return cls(parsed.scheme, host, project, parsed.username)

    def url(self, kind: str) -> str:
        return f"{self.scheme}://{self.host}/api/{self.project}/{kind}/?sentry_key={self.public_key}"


def _multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, data) in files.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                      "Content-Type: application/octet-stream\r\n\r\n".encode())
        chunks.append(data + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _post(url: str, body: bytes, content_type: str) -> bool:
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": content_type, "User-Agent": CLIENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return 200 <= response.status < 300


def upload_minidump(endpoint: SentryEndpoint, dump: tuple[str, bytes], tags: dict[str, str],
                    attachments: dict[str, bytes]) -> bool:
    fields = {f"sentry[tags][{key}]": value for key, value in tags.items()}
    fields["sentry[release]"] = tags.get("release", "")
    fields["sentry[environment]"] = tags.get("channel", "")
    files = {"upload_file_minidump": dump}
    files.update({name: (name, data) for name, data in attachments.items()})
    body, content_type = _multipart(fields, files)
    return _post(endpoint.url("minidump"), body, content_type)


def upload_event(endpoint: SentryEndpoint, message: str, tags: dict[str, str], extra: dict[str, str]) -> bool:
    event_id = uuid.uuid4().hex
    event = {"event_id": event_id, "timestamp": time.time(), "platform": "python", "level": "fatal",
             "logger": "lumenia.crash", "release": tags.get("release", ""), "environment": tags.get("channel", ""),
             "message": {"formatted": message}, "tags": tags, "extra": extra}
    payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
    envelope = b"\n".join([
        json.dumps({"event_id": event_id, "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}).encode(),
        json.dumps({"type": "event", "length": len(payload)}).encode(),
        payload,
    ])
    return _post(endpoint.url("envelope"), envelope, "application/x-sentry-envelope")
