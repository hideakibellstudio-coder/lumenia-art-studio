"""When to look for an update, and what an update found looks like to the reader.

Pure rules, no network and no Velopack: the updater (`ui/infrastructure/updater/`)
fetches, this module decides when.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Mapping

CHECK_INTERVAL = timedelta(hours=20)
# Notes of releases made while licensing existed carry a `<!-- released: YYYY-MM-DD -->` marker.
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


class UpdateChannel(str, Enum):
    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"


@dataclass(frozen=True)
class UpdatePreferences:
    channel: UpdateChannel = UpdateChannel.STABLE
    auto_check: bool = True
    last_check: str = ""  # ISO timestamp of the last check, "" = never

    @classmethod
    def from_config(cls, section: Mapping[str, object]) -> "UpdatePreferences":
        try:
            channel = UpdateChannel(str(section.get("channel", UpdateChannel.STABLE.value)))
        except ValueError:
            channel = UpdateChannel.STABLE
        auto = section.get("auto_check", True)
        return cls(channel=channel, auto_check=auto if isinstance(auto, bool) else True,
                   last_check=str(section.get("last_check", "")))

    def to_config(self) -> dict[str, object]:
        return {"channel": self.channel.value, "auto_check": self.auto_check, "last_check": self.last_check}

    def is_check_due(self, now: datetime) -> bool:
        if not self.auto_check:
            return False
        if not self.last_check:
            return True
        try:
            previous = datetime.fromisoformat(self.last_check)
        except ValueError:
            return True
        if previous.tzinfo is None and now.tzinfo is not None:
            previous = previous.replace(tzinfo=now.tzinfo)
        return now - previous >= CHECK_INTERVAL or previous > now


@dataclass(frozen=True)
class UpdateOffer:
    version: str
    notes_markdown: str = ""

    @property
    def readable_notes(self) -> str:
        return HTML_COMMENT.sub("", self.notes_markdown).strip()
