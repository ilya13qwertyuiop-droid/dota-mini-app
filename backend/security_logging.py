"""Central redaction and safe logging defaults for credentials."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable


_BOT_API_RE = re.compile(
    r"(https?://api\.telegram\.org/(?:file/)?bot)[^/\s?]+", re.IGNORECASE
)
_QUERY_SECRET_RE = re.compile(
    r"([?&](?:token|access_token|refresh_token|init_data|api_key|apikey)=)[^&\s]+",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(Authorization\s*:\s*Bearer\s+)[^\s,;]+", re.IGNORECASE)
_DATABASE_PASSWORD_RE = re.compile(
    r"((?:postgres(?:ql)?(?:\+[a-z0-9_]+)?|mysql(?:\+[a-z0-9_]+)?)://"
    r"[^:/@\s]+:)[^@/\s]+(@)",
    re.IGNORECASE,
)

_RECORD_FACTORY_INSTALLED = False
_RECORD_FACTORY_SECRETS: tuple[str, ...] = ()
_ORIGINAL_RECORD_FACTORY = logging.getLogRecordFactory()


def redact_text(value: object, secrets: Iterable[str] = ()) -> str:
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    text = _BOT_API_RE.sub(r"\1<redacted>", text)
    text = _QUERY_SECRET_RE.sub(r"\1<redacted>", text)
    text = _BEARER_RE.sub(r"\1<redacted>", text)
    text = _DATABASE_PASSWORD_RE.sub(r"\1<redacted>\2", text)
    return text


class _RedactingFormatter(logging.Formatter):
    def __init__(self, delegate: logging.Formatter, secrets: tuple[str, ...]):
        super().__init__()
        self._delegate = delegate
        self._secrets = secrets

    def format(self, record: logging.LogRecord) -> str:
        return redact_text(self._delegate.format(record), self._secrets)


class _RedactingFilter(logging.Filter):
    """Redact structured logging arguments before a handler formats them."""

    def __init__(self, secrets: tuple[str, ...]):
        super().__init__()
        self._secrets = secrets

    def _clean(self, value):
        if isinstance(value, str):
            return redact_text(value, self._secrets)
        if isinstance(value, tuple):
            return tuple(self._clean(item) for item in value)
        if isinstance(value, dict):
            return {key: self._clean(item) for key, item in value.items()}
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        # Render %-style structured arguments before redaction. Redacting the
        # format string and its args independently can consume a placeholder
        # (e.g. ``.../bot%s``) and leave logging with a mismatched arg tuple.
        try:
            rendered = record.getMessage()
        except Exception:
            record.msg = self._clean(record.msg)
            record.args = self._clean(record.args)
        else:
            record.msg = redact_text(rendered, self._secrets)
            record.args = ()
        # A handler installed after secure logging may format ``exc_info``
        # itself and would otherwise bypass message/argument redaction. Cache a
        # sanitized traceback on the record so every formatter reuses it.
        if record.exc_info:
            try:
                trace = logging.Formatter().formatException(record.exc_info)
                record.exc_text = redact_text(trace, self._secrets)
            except Exception:
                record.exc_text = "<exception redacted>"
        if record.stack_info:
            record.stack_info = redact_text(record.stack_info, self._secrets)
        return True


def configure_secure_logging(*secrets: str | None) -> None:
    """Suppress verbose HTTP URL logging and redact all installed handlers."""

    global _RECORD_FACTORY_INSTALLED, _RECORD_FACTORY_SECRETS
    secret_values = tuple(s for s in secrets if s)
    _RECORD_FACTORY_SECRETS = tuple(dict.fromkeys(
        _RECORD_FACTORY_SECRETS + secret_values
    ))
    if not _RECORD_FACTORY_INSTALLED:
        def _secure_record_factory(*args, **kwargs):
            record = _ORIGINAL_RECORD_FACTORY(*args, **kwargs)
            _RedactingFilter(_RECORD_FACTORY_SECRETS).filter(record)
            return record

        logging.setLogRecordFactory(_secure_record_factory)
        _RECORD_FACTORY_INSTALLED = True
    logger_names = (
        "httpx",
        "httpcore",
        "telegram.request",
        "telegram.ext.ExtBot",
    )
    for logger_name in logger_names:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Uvicorn access records contain the request target (including query
    # parameters). The filter is attached to the named logger itself so it
    # also covers handlers installed after this module is imported.
    protected_loggers = [logging.getLogger(), logging.getLogger("uvicorn.access")]
    for protected_logger in protected_loggers:
        if not any(isinstance(f, _RedactingFilter) for f in protected_logger.filters):
            protected_logger.addFilter(_RedactingFilter(secret_values))
        for handler in protected_logger.handlers:
            formatter = handler.formatter or logging.Formatter("%(message)s")
            if not isinstance(formatter, _RedactingFormatter):
                handler.setFormatter(_RedactingFormatter(formatter, secret_values))
