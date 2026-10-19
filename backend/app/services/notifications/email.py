from app.services.notifications.base import Notification, NotificationError


class EmailNotifier:
    kind = "email"

    def __init__(self, to: str) -> None:
        self.to = to

    def send(self, notification: Notification) -> None:
        raise NotificationError(
            "Email transport is not configured. Set an SMTP/provider integration before enabling email."
        )
