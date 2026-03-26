"""Feature flag service for staged rollouts.

The ``FeatureFlagService`` centralizes the management of experimental or
conditional features.  Feature flags allow us to enable or disable
components and behaviours at runtime without modifying code.  This is
especially useful during staged rollouts (Phase 11) where new
functionality is gradually exposed to users.
"""

from __future__ import annotations

from typing import Dict


class FeatureFlagService:
    """Store and query boolean feature flags.

    Parameters
    ----------
    flags: Dict[str, bool]
        A mapping of feature names to their enabled/disabled status.
    """

    def __init__(self, flags: Dict[str, bool] | None = None) -> None:
        self.flags: Dict[str, bool] = flags.copy() if flags else {}

    def is_enabled(self, flag_name: str) -> bool:
        """Return ``True`` if the given feature is enabled."""
        return bool(self.flags.get(flag_name))

    def set_flag(self, flag_name: str, enabled: bool) -> None:
        """Enable or disable a feature flag."""
        self.flags[flag_name] = bool(enabled)

    def all_flags(self) -> Dict[str, bool]:
        """Return a copy of all known feature flags."""
        return self.flags.copy()