import json
import time

import httpx

from app.core.config import settings
from app.core.security import sign_webhook
from app.services.notifications.base import Notification, NotificationError
from app.services.url_guard import UrlValidationError, validate_url


class WebhookNotifier:
    kind = "webhook"

    def __init__(self, url: str) -> None:
        self.url = url

    def send(self, notification: Notification) -> None:
        try:
            validate_url(self.url, settings.allow_private_urls)
        except UrlValidationError as exc:
            raise NotificationError(str(exc)) from exc

        timestamp = str(int(time.time()))
        body = json.dumps(
            {
                "subject": notification.subject,
                "body": notification.body,
                "severity": notification.severity,
                "url": notification.url,
            }
        ).encode("utf-8")
        signature = sign_webhook(body, timestamp)
        try:
            response = httpx.post(
                self.url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-RG-Timestamp": timestamp,
                    "X-RG-Signature": signature,
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise NotificationError(str(exc)) from exc
