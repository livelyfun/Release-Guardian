import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.services.notifications.base import Notification, NotificationError


class EmailNotifier:
    kind = "email"

    def __init__(self, to: str) -> None:
        self.to = to

    def send(self, notification: Notification) -> None:
        if not settings.smtp_host:
            raise NotificationError(
                "Email transport is not configured. Set SMTP_HOST (and credentials) before enabling email."
            )

        body = notification.body
        if notification.url:
            body = f"{body}\n\n{notification.url}"
        message = EmailMessage()
        message["Subject"] = notification.subject
        message["From"] = settings.smtp_from
        message["To"] = self.to
        message.set_content(body)

        try:
            if settings.smtp_ssl:
                client = smtplib.SMTP_SSL(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=settings.smtp_timeout_seconds,
                )
            else:
                client = smtplib.SMTP(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=settings.smtp_timeout_seconds,
                )
            with client:
                if settings.smtp_starttls and not settings.smtp_ssl:
                    client.starttls()
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password or "")
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise NotificationError(str(exc)) from exc
