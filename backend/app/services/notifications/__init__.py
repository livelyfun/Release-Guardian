from app.services.notifications.base import Notification, NotificationError, Notifier
from app.services.notifications.email import EmailNotifier
from app.services.notifications.webhook import WebhookNotifier

__all__ = [
    "EmailNotifier",
    "Notification",
    "NotificationError",
    "Notifier",
    "WebhookNotifier",
    "build_notifier",
]


def build_notifier(kind: str, config: dict) -> Notifier:
    if kind == "webhook":
        return WebhookNotifier(config["url"])
    if kind == "email":
        return EmailNotifier(config["to"])
    raise NotificationError(f"Unsupported notification channel: {kind}")
