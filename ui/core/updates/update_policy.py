"""When to look for an update and whether an update found may be offered.

Pure rules, no network and no Velopack: the updater (`ui/infrastructure/updater/`)
fetches, this module decides. The release script writes the release date into the
release notes (`<!-- released: YYYY-MM-DD -->`) so the license coverage is known
before anything is downloaded: installing a version the license does not cover
would turn a paying user into a free one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Mapping

from ui.core.licensing import LicenseStatus

CHECK_INTERVAL = timedelta(hours=20)
RELEASE_DATE = re.compile(r"<!--\s*released:\s*(\d{4}-\d{2}-\d{2})\s*-->")


class UpdateChannel(str, Enum):
    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"


class UpdateDecision(Enum):
    OFFER = "offer"                    # download and ask to restart
    NOT_COVERED = "not_covered"        # newer than the license's update period: tell, never install
    UNKNOWN_COVERAGE = "unknown"       # no release date in the notes and the license has a limit


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
    def release_date(self) -> str:
        match = RELEASE_DATE.search(self.notes_markdown)
        return match.group(1) if match else ""

    @property
    def readable_notes(self) -> str:
        return RELEASE_DATE.sub("", self.notes_markdown).strip()


def decide(offer: UpdateOffer, license_status: LicenseStatus) -> UpdateDecision:
    covered = license_status.covers_release(offer.release_date)
    if covered is None:
        return UpdateDecision.UNKNOWN_COVERAGE
    return UpdateDecision.OFFER if covered else UpdateDecision.NOT_COVERED
