"""Structured exceptions for endpoint-health failures.

Replaces the `except Exception: return None` pattern that silently degrades
HTTP-backed capabilities (embeddings, reranker, audio, tika, docling) and
produces misleading downstream TypeErrors such as

    TypeError: 'NoneType' object is not iterable

at the consumer (e.g. embeddings.extend(generate_openai_batch_embeddings(...))).

EndpointUnreachable carries enough context for the FastAPI exception handler
to build a structured 503 response naming the bad URL, the underlying error
class, and a pointer to /admin/diagnostics for triage.
"""

from typing import Optional


class EndpointUnreachable(Exception):
    """Raised when an HTTP-backed capability can't talk to its endpoint.

    Distinct from upstream library exceptions (requests.RequestException,
    aiohttp.ClientConnectorError, etc.) so the FastAPI exception handler
    can recognize it without coupling to a specific HTTP client.
    """

    def __init__(
        self,
        url: str,
        underlying: Optional[BaseException] = None,
        capability: Optional[str] = None,
    ):
        self.url = url
        self.underlying = underlying
        self.capability = capability
        underlying_msg = (
            f"{type(underlying).__name__}: {underlying}"
            if underlying is not None
            else "unknown"
        )
        super().__init__(
            f"Endpoint unreachable: {url}"
            + (f" (capability: {capability})" if capability else "")
            + f" — {underlying_msg}"
        )
