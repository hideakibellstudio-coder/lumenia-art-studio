"""What a crash report may carry, and the user's answer about sending it.

A report leaves the machine only with the user's consent (LGPD: informed and
revocable), and even then without what identifies the person: the user name
inside paths and any e-mail address are replaced before the text is written into
the report. The painting is never part of a report.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
USER_PLACEHOLDER = "<usuario>"
EMAIL_PLACEHOLDER = "<email>"


class ReportConsent(str, Enum):
    ASK = "ask"          # ask on each report (default)
    ALWAYS = "always"    # send without asking
    NEVER = "never"      # keep reports on this machine only

    @classmethod
    def parse(cls, value: object) -> "ReportConsent":
        try:
            return cls(str(value))
        except ValueError:
            return cls.ASK


def scrub(text: str, home: Path, user_name: str) -> str:
    """Removes the user's identity from a log or a stack: home folder, user name, e-mails."""
    for spelling in {str(home), home.as_posix()}:
        if spelling and spelling not in (".", "/"):
            text = re.sub(re.escape(spelling), lambda _m: "~", text, flags=re.IGNORECASE)
    if len(user_name) >= 3:
        text = re.sub(rf"(?<![\w]){re.escape(user_name)}(?![\w])", USER_PLACEHOLDER, text, flags=re.IGNORECASE)
    return EMAIL.sub(EMAIL_PLACEHOLDER, text)
