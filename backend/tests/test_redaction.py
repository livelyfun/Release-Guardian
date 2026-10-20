import json

import pytest

from app.services.redaction import REDACTED, redact_har, redact_url


def _har() -> bytes:
    return json.dumps(
        {
            "log": {
                "version": "1.2",
                "entries": [
                    {
                        "request": {
                            "method": "POST",
                            "url": "https://example.com/login?token=abc&page=1",
                            "headers": [
                                {"name": "Authorization", "value": "Bearer secret"},
                                {"name": "Accept", "value": "application/json"},
                            ],
                            "cookies": [{"name": "session", "value": "cookie-secret"}],
                            "queryString": [
                                {"name": "token", "value": "abc"},
                                {"name": "page", "value": "1"},
                            ],
                            "postData": {
                                "mimeType": "application/json",
                                "text": json.dumps(
                                    {"email": "a@example.com", "password": "hunter2"}
                                ),
                            },
                        },
                        "response": {
                            "status": 200,
                            "headers": [{"name": "Set-Cookie", "value": "session=abc"}],
                            "cookies": [{"name": "session", "value": "abc"}],
                        },
                    }
                ],
            }
        }
    ).encode()


def test_redact_har_removes_credentials():
    data, count = redact_har(_har())
    har = json.loads(data)
    entry = har["log"]["entries"][0]

    headers = {header["name"]: header["value"] for header in entry["request"]["headers"]}
    assert headers["Authorization"] == REDACTED
    assert headers["Accept"] == "application/json"
    assert entry["request"]["cookies"][0]["value"] == REDACTED
    query = {pair["name"]: pair["value"] for pair in entry["request"]["queryString"]}
    assert query == {"token": REDACTED, "page": "1"}
    assert json.loads(entry["request"]["postData"]["text"]) == {
        "email": "a@example.com",
        "password": REDACTED,
    }
    response_headers = {
        header["name"]: header["value"] for header in entry["response"]["headers"]
    }
    assert response_headers["Set-Cookie"] == REDACTED
    assert entry["response"]["cookies"][0]["value"] == REDACTED
    assert count >= 6
    assert b"secret" not in data
    assert b"hunter2" not in data


def test_redact_har_rejects_malformed_payload():
    with pytest.raises(ValueError):
        redact_har(b'{"log": {}}')
    with pytest.raises(json.JSONDecodeError):
        redact_har(b"not json")


def test_redact_url_only_changes_sensitive_query_values():
    assert redact_url("https://example.com/a?token=abc&page=2") == (
        "https://example.com/a?token=%5BREDACTED%5D&page=2"
    )
    assert redact_url("https://example.com/a?page=2") == "https://example.com/a?page=2"
