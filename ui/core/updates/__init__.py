"""Atualizações: quando procurar e se a versão encontrada pode ser oferecida."""

from ui.core.updates.update_policy import (
    CHECK_INTERVAL,
    UpdateChannel,
    UpdateDecision,
    UpdateOffer,
    UpdatePreferences,
    decide,
)

__all__ = ["CHECK_INTERVAL", "UpdateChannel", "UpdateDecision", "UpdateOffer", "UpdatePreferences", "decide"]
