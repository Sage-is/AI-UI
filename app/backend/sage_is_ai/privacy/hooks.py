"""Where the engine meets a request.

``active_for`` decides per model and connection; ``outbound`` rewrites the
messages about to leave; ``reverse_completion`` and the stream helpers put
the real values back. Everything reads ``PRIVACY_CONFIG`` and the instance
key, and nothing here is specific to one provider.
"""

from __future__ import annotations

import copy
import json
import logging

from sage_is_ai.privacy.engine import StreamReverser, pseudonymize, reverse
from sage_is_ai.privacy.mapper import DbMapper
from sage_is_ai.privacy.rules import rules_from_config

log = logging.getLogger(__name__)

DEFAULTS = {
    "enabled": True,
    "default_external": True,  # ON from 3.2.0; must equal config.py PRIVACY_CONFIG
    "connections": {},  # "<urlIdx>" or "hidden:<id>" -> bool
    "models": {},  # model id -> bool, overrides the connection
    "detectors": {},
    "rules": [],
}


def config(request) -> dict:
    value = getattr(request.app.state.config, "PRIVACY_CONFIG", None) or {}
    # Deep-copied: the nested {} and [] defaults would otherwise be handed out
    # by reference, and one caller mutating them rewrites the module default.
    return {**copy.deepcopy(DEFAULTS), **value}


def key() -> str:
    # Both come from env.py. The old hardcoded fallback handed a misconfigured
    # deploy predictable pseudonyms and said nothing; refusing is the point.
    from sage_is_ai.env import PRIVACY_KEY, WEBUI_SECRET_KEY

    value = PRIVACY_KEY or WEBUI_SECRET_KEY
    if not value:
        raise RuntimeError(
            "privacy is enabled but neither PRIVACY_KEY nor WEBUI_SECRET_KEY is "
            "set: pseudonyms would be keyed on nothing and trivially reversible"
        )
    return value


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
        _rewrite_message(message, rewrite)
    request.state.privacy_hits = counts
    if counts:
        log.info("privacy: pseudonymized %s", counts)
    return form_data


def _rewrite_message(message: dict, rewrite) -> None:
    """A message's text, whether a plain string or a list of typed parts."""
    content = message.get("content")
    if isinstance(content, str):
        message["content"] = rewrite(content)
        return
    for part in content if isinstance(content, list) else []:
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            part["text"] = rewrite(part["text"])


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


class PassThrough:
    """The reverser for a request privacy does not cover: every step is a no-op."""

    active = False

    def feed(self, chunk):
        return chunk

    def flush(self) -> str:
        return ""


def stream_reverser_for(request):
    """This request's stream reverser: the real one when privacy covers it."""
    if getattr(request.state, "privacy_active", False):
        return stream_reverser()
    return PassThrough()


def finish_stream(reverser, tool_calls: list) -> str:
    """End of a streamed reply: the held-back tail, and tool arguments put back."""
    tail = reverser.flush()
    if reverser.active:
        reverse_tool_calls(tool_calls)
    return tail


def reverse_sse_for(request, lines):
    """The provider's SSE lines, reversed when privacy covers this request."""
    if getattr(request.state, "privacy_active", False):
        return reverse_sse(lines)
    return lines


def _as_line(text: str, like) -> bytes | str:
    return text.encode("utf-8") if isinstance(like, bytes) else text


def _sse_body(line) -> str | None:
    """The payload of a `data:` line, or None for any other line."""
    text = (line.decode("utf-8") if isinstance(line, bytes) else line).strip()
    return text[len("data:") :].strip() if text.startswith("data:") else None


def _reverse_event(body: str, reverser: StreamReverser) -> str | None:
    """One SSE event with its content deltas reversed; None when it is not JSON."""
    try:
        data = json.loads(body)
    except ValueError:
        return None
    for choice in data.get("choices") or []:
        delta = choice.get("delta") or {}
        if isinstance(delta.get("content"), str) and delta["content"]:
            delta["content"] = reverser.feed(delta["content"])
    return f"data: {json.dumps(data)}\n\n"


async def reverse_sse(lines):
    """Server-sent event lines from a provider, content deltas reversed in order."""
    reverser = stream_reverser()
    async for line in lines:
        body = _sse_body(line)
        if body is None:
            yield line
        elif body == "[DONE]":
            tail = reverser.flush()
            if tail:
                extra = json.dumps(
                    {"choices": [{"index": 0, "delta": {"content": tail}}]}
                )
                yield _as_line(f"data: {extra}\n\n", line)
            yield line
        else:
            out = _reverse_event(body, reverser)
            yield line if out is None else _as_line(out, line)
