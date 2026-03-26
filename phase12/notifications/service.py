"""Notification service implementation.

The NotificationService encapsulates logic for sending various types of
user notifications.  In this phase, the service simply collects
messages in an internal list and prints them to stdout.  In a
production system, these methods would integrate with external
providers (SMTP servers, SMS gateways, push notification APIs) and
handle retries, templating and localization.
"""

from __future__ import annotations

from typing import Dict, Any, List


class NotificationService:
    """Simple notification manager storing sent messages."""

    def __init__(self) -> None:
        self.sent_messages: List[Dict[str, Any]] = []

    def send_trade_confirmation(self, user_id: str, details: Dict[str, Any]) -> None:
        msg = {
            "type": "trade_confirmation",
            "user_id": user_id,
            "details": details,
        }
        self._dispatch(msg)

    def send_risk_alert(self, user_id: str, message: str) -> None:
        msg = {
            "type": "risk_alert",
            "user_id": user_id,
            "message": message,
        }
        self._dispatch(msg)

    def send_system_status(self, message: str) -> None:
        msg = {
            "type": "system_status",
            "message": message,
        }
        self._dispatch(msg)

    def _dispatch(self, message: Dict[str, Any]) -> None:
        """Dispatch a notification.  For now, append to list and print."""
        self.sent_messages.append(message)
        # Print the message to simulate delivery; in real implementation
        # this would call an external provider.
        print(f"Notification sent: {message}")
