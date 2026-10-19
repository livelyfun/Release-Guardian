import re
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def validate_http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must use http or https scheme")
    if not parsed.netloc:
        raise ValueError("URL must include a host")
    return value


class Message(BaseModel):
    detail: str
