"""Environment configuration for the trading platform.

This module defines a simple ``Environment`` class used to
distinguish between paper trading and live trading modes.  The
environment mode influences how connectors and execution behave.  A
paper environment should never execute real trades, whereas a live
environment would interact with real exchanges and custodians.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Environment:
    """Represent the current operating environment of the trading bot.

    Parameters
    ----------
    mode: str
        Either ``"paper"`` or ``"live"``.  Additional modes may be added
        in the future (e.g. ``"staging"``) as needed.

    Example
    -------

    >>> env = Environment(mode="paper")
    >>> env.is_paper()
    True
    """

    mode: str = "paper"

    def __post_init__(self) -> None:
        if self.mode not in {"paper", "live"}:
            raise ValueError(f"Invalid environment mode: {self.mode}")

    def is_paper(self) -> bool:
        """Return ``True`` if this environment represents paper trading."""
        return self.mode == "paper"

    def is_live(self) -> bool:
        """Return ``True`` if this environment represents live trading."""
        return self.mode == "live"