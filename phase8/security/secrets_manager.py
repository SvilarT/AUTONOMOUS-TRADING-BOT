"""Secrets management utilities.

This module provides a thin abstraction for retrieving and storing
sensitive secrets such as API keys and encryption keys.  In a
production environment this would interface with a dedicated
secrets manager like HashiCorp Vault, AWS Secrets Manager or
Azure Key Vault.  Secrets would be encrypted at rest and in
transit.  For demonstration purposes we simply read from
environment variables or in‑memory storage.
"""

from __future__ import annotations

import os
from typing import Optional


class SecretsManager:
    """Simple secrets manager using environment variables or in‑memory store.

    This class exposes methods to fetch API credentials for
    exchanges or services.  In a real implementation, methods would
    communicate with an external secrets manager and handle
    versioning, rotation and fine‑grained access control.
    """

    def __init__(self) -> None:
        # In‑memory fallback store for demonstration; not secure.
        self._store: dict[str, str] = {}

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key from environment or in‑memory store."""
        # Check environment variables first
        value = os.getenv(key)
        if value is not None:
            return value
        return self._store.get(key)

    def set_secret(self, key: str, value: str) -> None:
        """Set or update a secret in the in‑memory store (for testing)."""
        self._store[key] = value

    def get_exchange_credentials(self, exchange: str) -> dict[str, str]:
        """Retrieve API key and secret for a given exchange.

        Keys are expected to be stored under environment variables
        following the pattern ``{exchange}_API_KEY`` and
        ``{exchange}_API_SECRET`` (upper‑cased).  If not found, the
        in‑memory store is consulted.  Returns an empty dict if no
        credentials are configured.
        """
        key_env = f"{exchange.upper()}_API_KEY"
        secret_env = f"{exchange.upper()}_API_SECRET"
        return {
            "api_key": self.get_secret(key_env) or "",
            "api_secret": self.get_secret(secret_env) or "",
        }
