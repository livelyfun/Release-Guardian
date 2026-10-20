import smtplib

import pytest

from app.core.config import settings
from app.services.notifications.base import Notification, NotificationError
from app.services.notifications.email import EmailNotifier


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args = None
        self.message = None
        self.sent = False
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, message):
        self.message = message
        self.sent = True


@pytest.fixture
def smtp_settings(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_username", "mailer")
    monkeypatch.setattr(settings, "smtp_password", "smtp-secret")
    monkeypatch.setattr(settings, "smtp_from", "alerts@example.com")
    monkeypatch.setattr(settings, "smtp_starttls", True)
    monkeypatch.setattr(settings, "smtp_ssl", False)
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def test_email_notifier_sends_via_smtp(smtp_settings):
    EmailNotifier("ops@example.com").send(
        Notification(subject="Incident opened", body="Homepage failed", url="https://rg.test/i/1")
    )

    client = smtp_settings.instances[0]
    assert client.host == "smtp.example.com"
    assert client.started_tls is True
    assert client.login_args == ("mailer", "smtp-secret")
    assert client.sent is True
    assert client.message["To"] == "ops@example.com"
    assert client.message["From"] == "alerts@example.com"
    assert client.message["Subject"] == "Incident opened"
    assert "https://rg.test/i/1" in client.message.get_content()


def test_email_notifier_requires_smtp_configuration(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
    with pytest.raises(NotificationError, match="not configured"):
        EmailNotifier("ops@example.com").send(Notification(subject="x", body="y"))


def test_email_notifier_wraps_smtp_errors(smtp_settings, monkeypatch):
    class BrokenSMTP(FakeSMTP):
        def send_message(self, message):
            raise smtplib.SMTPException("relay denied")

    monkeypatch.setattr(smtplib, "SMTP", BrokenSMTP)
    with pytest.raises(NotificationError, match="relay denied"):
        EmailNotifier("ops@example.com").send(Notification(subject="x", body="y"))
