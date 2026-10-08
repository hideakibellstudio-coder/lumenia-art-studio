"""What the engine says about the license, as the interface reads it.

The engine decides (`engine/infrastructure/licensing/LicenseAuthority.cpp`); this
module only names its answer. The state names mirror `licenseStateName` there.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class LicenseState(str, Enum):
    UNLICENSED = "unlicensed"
    LICENSED = "licensed"
    MALFORMED = "malformed"
    BAD_SIGNATURE = "bad_signature"
    EXPIRED = "expired"
    REVOKED = "revoked"
    UPDATES_EXPIRED = "updates_expired"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class LicenseStatus:
    state: LicenseState = LicenseState.UNLICENSED
    license_id: str = ""
    sku: str = ""
    holder_name: str = ""
    issued_on: str = ""
    updates_until: str = ""   # "YYYY-MM-DD"; "" = updates forever
    expires_on: str = ""      # "YYYY-MM-DD"; "" = perpetual

    @classmethod
    def from_engine(cls, data: Mapping[str, object]) -> "LicenseStatus":
        """Reads the dict of `aladyn_engine_native.license_status()`; an unknown state is unsupported."""
        try:
            state = LicenseState(str(data.get("state", "")))
        except ValueError:
            state = LicenseState.UNSUPPORTED
        return cls(state=state, license_id=str(data.get("license_id", "")), sku=str(data.get("sku", "")),
                   holder_name=str(data.get("holder_name", "")), issued_on=str(data.get("issued_on", "")),
                   updates_until=str(data.get("updates_until", "")), expires_on=str(data.get("expires_on", "")))

    @property
    def is_licensed(self) -> bool:
        return self.state is LicenseState.LICENSED

    def covers_release(self, release_date: str) -> bool | None:
        """Whether a build released on `release_date` ("YYYY-MM-DD") accepts this license.

        True without a license (the free mode updates freely) and for a license with
        updates forever; None when the release date is unknown and the license has a limit.
        """
        if not self.is_licensed or not self.updates_until:
            return True
        if not release_date:
            return None
        return release_date <= self.updates_until
