"""Where the engine meets a request.

``active_for`` decides per model and connection; ``outbound`` rewrites the
messages about to leave; ``reverse_completion`` and the stream helpers put
the real values back. Everything reads ``PRIVACY_CONFIG`` and the instance
key, and nothing here is specific to one provider.
"""

from __future__ import annotations

import json
import logging
import os

from sage_is_ai.privacy.engine import StreamReverser, pseudonymize, reverse
from sage_is_ai.privacy.mapper import DbMapper
from sage_is_ai.privacy.rules import rules_from_config

log = logging.getLogger(__name__)

DEFAULTS = {
    "enabled": True,
    "default_external": False,  # decided 2026-09-16: off this version, on next
    "connections": {},  # "<urlIdx>" or "hidden:<id>" -> bool
    "models": {},  # model id -> bool, overrides the connection
    "detectors": {},
    "rules": [],
}


def config(request) -> dict:
    value = getattr(request.app.state.config, "PRIVACY_CONFIG", None) or {}
    return {**DEFAULTS, **value}


def key() -> str:
    from sage_is_ai.env import WEBUI_SECRET_KEY

    return os.environ.get("PRIVACY_KEY") or WEBUI_SECRET_KEY or "trellis-dev-key"


def is_external(model: dict) -> bool:
    if model.get("owned_by") in ("ollama", "arena") or model.get("pipe"):
        return False
    return model.get("connection_type", "external") != "local"


def connection_key(model: dict) -> str:
    hidden = model.get("_try_sage_hidden_id")
    if hidden:
        return f"hidden:{hidden}"
    idx = model.get("urlIdx")
    return str(0 if idx is None else idx)


def active_for(request, model: dict) -> bool:
    cfg = config(request)
    if not cfg.get("enabled", True):
        return False
    override = (cfg.get("models") or {}).get(model.get("id"))
    if override is not None:
        return bool(override)
    if not is_external(model):
        return False
    flag = (cfg.get("connections") or {}).get(connection_key(model))
    return bool(cfg.get("default_external") if flag is None else flag)


def mapper() -> DbMapper:
    return DbMapper(key())


def outbound(request, form_data: dict) -> dict:
    """Pseudonymize every text part of every message, in place."""
    cfg = config(request)
    rules = rules_from_config(cfg)
    db_mapper = mapper()
    hints = ((form_data.get("metadata") or {}).get("privacy") or {}).get("known")
    counts: dict[str, int] = {}

    def rewrite(text: str) -> str:
        out, hits = pseudonymize(text, rules, db_mapper, hints)
        for hit in hits:
            counts[hit.rule] = counts.get(hit.rule, 0) + hit.count
        return out

    for message in form_data.get("messages") or []:
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = rewrite(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                    part["text"] = rewrite(part["text"])
    request.state.privacy_hits = counts
    if counts:
        log.info("privacy: pseudonymized %s", counts)
    return form_data


def reverse_text(text: str) -> str:
    return reverse(text, mapper().reverse_table())


def reverse_completion(response: dict) -> None:
    """A whole (non-streamed) completion: message content and tool arguments."""
    for choice in response.get("choices") or []:
        message = choice.get("message") or {}
        if isinstance(message.get("content"), str):
            message["content"] = reverse_text(message["content"])
        reverse_tool_calls(message.get("tool_calls") or [])


def reverse_tool_calls(tool_calls: list) -> None:
    for call in tool_calls or []:
        function = call.get("function") or {}
        if isinstance(function.get("arguments"), str):
            function["arguments"] = reverse_text(function["arguments"])


def stream_reverser() -> StreamReverser:
    return StreamReverser(mapper().reverse_table())


async def reverse_sse(lines):
    """Server-sent event lines from a provider, content deltas reversed in order."""
    reverser = stream_reverser()
    async for line in lines:
        raw = line.decode("utf-8") if isinstance(line, bytes) else line
        text = raw.strip()
        if not text.startswith("data:"):
            yield line
            continue
        body = text[len("data:"):].strip()
        if body == "[DONE]":
            tail = reverser.flush()
            if tail:
                extra = json.dumps({"choices": [{"index": 0, "delta": {"content": tail}}]})
                yield f"data: {extra}\n\n".encode("utf-8") if isinstance(line, bytes) else f"data: {extra}\n\n"
            yield line
            continue
        try:
            data = json.loads(body)
        except ValueError:
            yield line
            continue
        for choice in data.get("choices") or []:
            delta = choice.get("delta") or {}
            if isinstance(delta.get("content"), str) and delta["content"]:
                delta["content"] = reverser.feed(delta["content"])
        out = f"data: {json.dumps(data)}\n\n"
        yield out.encode("utf-8") if isinstance(line, bytes) else out
