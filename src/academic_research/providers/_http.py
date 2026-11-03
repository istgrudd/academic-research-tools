"""Shared timeout, retry, and network-error helpers for provider clients."""

from __future__ import annotations

import http.client
import os
import time
from collections.abc import Callable, Mapping
from urllib.error import HTTPError

TIMEOUT_ENV = "ACADEMIC_RESEARCH_TIMEOUT"
DEFAULT_TIMEOUT = 30.0
MIN_TIMEOUT = 1.0
MAX_TIMEOUT = 120.0
RETRY_DELAYS = (1.0, 2.0)
PROJECT_URL = "https://github.com/istgrudd/academic-research-tools"

Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]

# Connection, DNS, TLS, timeout, and truncated-response failures. HTTPError is
# excluded because default transports return HTTP statuses instead of raising.
NETWORK_ERRORS: tuple[type[BaseException], ...] = (OSError, http.client.HTTPException)

_sleep = time.sleep


def resolve_timeout(
    timeout: float | None = None, *, environ: Mapping[str, str] | None = None
) -> float:
    """Return an explicit or ACADEMIC_RESEARCH_TIMEOUT timeout clamped to 1-120 s."""
    if timeout is None:
        raw = str((os.environ if environ is None else environ).get(TIMEOUT_ENV, "")).strip()
        try:
            timeout = float(raw) if raw else DEFAULT_TIMEOUT
        except ValueError:
            timeout = DEFAULT_TIMEOUT
        if timeout != timeout:  # NaN
            timeout = DEFAULT_TIMEOUT
    return max(MIN_TIMEOUT, min(float(timeout), MAX_TIMEOUT))


def user_agent() -> str:
    """Return a descriptive user agent for the installed release."""
    from .. import __version__

    return f"academic-research-tools/{__version__} (+{PROJECT_URL})"


def is_retryable_status(status: int) -> bool:
    return status == 429 or 500 <= status <= 599


def network_error_message(service: str, host: str, error: BaseException, attempts: int) -> str:
    detail = str(error) or type(error).__name__
    noun = "attempt" if attempts == 1 else "attempts"
    return (
        f"Network error while calling {service} after {attempts} {noun}: {detail}. "
        f"{host} could not be reached from this network; check firewall, ISP, or VPN "
        "restrictions, or set HTTPS_PROXY if a proxy is required."
    )


def request_with_retries(
    transport: Transport,
    url: str,
    headers: dict[str, str],
    timeout: float,
    *,
    max_retries: int,
    service: str,
    host: str,
    error_type: Callable[[str], Exception],
) -> tuple[int, dict[str, str], bytes]:
    """Call a transport, retrying network failures, HTTP 429, and HTTP 5xx.

    Retries wait 1 s and then 2 s. Other 4xx responses are returned immediately.
    When retries are exhausted, the last HTTP response is returned so the provider
    can build its usual error, or a network failure becomes ``error_type``.
    """
    delays = RETRY_DELAYS[: max(0, int(max_retries))]
    attempt = 0
    while True:
        attempt += 1
        try:
            response = transport(url, headers, timeout)
        except HTTPError:
            raise
        except NETWORK_ERRORS as exc:
            if attempt <= len(delays):
                _sleep(delays[attempt - 1])
                continue
            raise error_type(network_error_message(service, host, exc, attempt)) from exc
        if is_retryable_status(response[0]) and attempt <= len(delays):
            _sleep(delays[attempt - 1])
            continue
        return response
