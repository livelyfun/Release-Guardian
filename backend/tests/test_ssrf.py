import pytest

from app.services.url_guard import UrlValidationError, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost:8000/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/",
        "file:///etc/passwd",
        "ftp://example.com/file",
    ],
)
def test_blocked_targets(url):
    with pytest.raises(UrlValidationError):
        validate_url(url)


def test_public_literal_ip_allowed_when_not_private():
    assert validate_url("http://93.184.216.34/") == "http://93.184.216.34/"


def test_private_allowed_when_explicitly_enabled():
    assert validate_url("http://127.0.0.1/", allow_private=True) == "http://127.0.0.1/"


def test_missing_host_rejected():
    with pytest.raises(UrlValidationError):
        validate_url("http:///nohost")
