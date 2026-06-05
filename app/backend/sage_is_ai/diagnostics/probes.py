"""Reusable probes for boot-time and on-demand health checks.

probe_http() is the workhorse. It performs a short-timeout request, classifies
the outcome, and returns a ProbeResult that the EndpointHealth registry can
consume directly.

Design notes:
- Probes never raise. Failure modes are first-class return values.
- A 4xx response is "reachable" (the URL is alive even if the call would
  have failed); a 5xx is "reachable but degraded"; a connect/DNS/timeout
  is "unreachable".
- The probe deliberately uses a HEAD-then-GET fallback because many embedding
  servers reject HEAD with 405 even though the URL is healthy.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass(frozen=True)
class ProbeResult:
    url: str
    reachable: bool
    status_code: Optional[int]
    error_class: Optional[str]
    error_message: Optional[str]
    latency_ms: float

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "reachable": self.reachable,
            "status_code": self.status_code,
            "error_class": self.error_class,
            "error_message": self.error_message,
            "latency_ms": round(self.latency_ms, 1),
        }


def probe_http(url: str, timeout: float = 5.0) -> ProbeResult:
    """Probe an HTTP URL with HEAD, falling back to GET on 405.

    Returns a ProbeResult; never raises. Use the result to feed the
    EndpointHealth registry, render the diagnostics page, or short-circuit
    boot when a probe is mandatory.
    """
    start = time.monotonic()
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code == 405:
            r = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
            r.close()
        latency_ms = (time.monotonic() - start) * 1000
        return ProbeResult(
            url=url,
            reachable=True,
            status_code=r.status_code,
            error_class=None,
            error_message=None,
            latency_ms=latency_ms,
        )
    except requests.RequestException as e:
        latency_ms = (time.monotonic() - start) * 1000
        return ProbeResult(
            url=url,
            reachable=False,
            status_code=None,
            error_class=type(e).__name__,
            error_message=str(e),
            latency_ms=latency_ms,
        )
