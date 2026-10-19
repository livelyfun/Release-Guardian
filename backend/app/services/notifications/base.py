from dataclasses import dataclass
from typing import Protocol


@dataclass
class Notification:
    subject: str
    body: str
    severity: str = "medium"
    url: str | None = None


class Notifier(Protocol):
    kind: str

    def send(self, notification: Notification) -> None: ...


class NotificationError(RuntimeError):
    pass
