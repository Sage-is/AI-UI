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
    """What the connection's own admin setting says: Ollama connections default to
    local and OpenAI-style ones to external, as their connection forms do. An
    Ollama on a hosted box is external once its admin marks it so (2026-11-03)."""
    default = "local" if model.get("owned_by") == "ollama" else "external"
    return model.get("connection_type", default) != "local"


def connection_key(model: dict) -> str:
    """The panel's key for a model's connection. Ollama and OpenAI connections
    each count from 0, and a person's direct connections from 0 again, so every
    kind has its own namespace: flagging OpenAI connection 0 never flags Ollama 0
    or somebody's own connection (2026-11-03)."""
    hidden = model.get("_try_sage_hidden_id")
    if hidden:
        return f"hidden:{hidden}"
    if model.get("direct"):
        return "direct"
    if model.get("owned_by") == "ollama":
        urls = (model.get("ollama") or {}).get("urls") or [0]
        return f"ollama:{urls[0]}"
    idx = model.get("urlIdx")
    return str(0 if idx is None else idx)


def active_for(request, model: dict) -> bool:
    cfg = config(request)
    if not cfg.get("enabled", True):
        return False
    override = (cfg.get("models") or {}).get(model.get("id"))
    if override is not None:
        return bool(override)
    # An arena picks a model, whose own call is checked; a pipe is code on the box.
    if model.get("owned_by") == "arena" or model.get("pipe"):
        return False
    flag = (cfg.get("connections") or {}).get(connection_key(model))
    return connection_filtered(cfg, flag, is_external(model))


def connection_filtered(cfg: dict, flag, external: bool) -> bool:
    """One connection's rule, for requests and the panel alike: the admin's word
    wins, local or external; unset, an external connection follows the default."""
    if flag is not None:
        return bool(flag)
    return external and bool(cfg.get("default_external"))


def mapper() -> DbMapper:
    return DbMapper(key())


class RecordingMapper:
    """The mapper for one request: every stand-in it hands out is remembered, so
    the reply reverses only what this request sent. The instance-wide table let
    one chat's reply surface another chat's real name (F0, 2026-10-24)."""

    def __init__(self, inner):
        self.inner = inner
        self.table: dict[str, str] = {}

    def fake(self, category: str, real: str, strategy: str, replacement: str = "") -> str:
        out = self.inner.fake(category, real, strategy, replacement)
        # A redaction or a shared literal has no owner of its own: nothing to reverse.
        if out and self.inner.owner(out) == (category, real.strip()):
            self.table[out] = real.strip()
        return out

    def lookup(self, category: str, real: str):
        return self.inner.lookup(category, real)

    def owner(self, fake: str):
        return self.inner.owner(fake)

    def store(self, category: str, real: str, fake: str) -> None:
        self.inner.store(category, real, fake)

    def reverse_table(self) -> dict[str, str]:
        return self.table


def table_for(request) -> dict[str, str]:
    """The stand-ins this request sent, and nothing else."""
    return getattr(request.state, "privacy_table", None) or {}


def outbound(request, form_data: dict) -> dict:
    """Pseudonymize every text part of every message, in place."""
    cfg = config(request)
    rules = rules_from_config(cfg)
    db_mapper = RecordingMapper(mapper())
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
    request.state.privacy_mapper = db_mapper
    request.state.privacy_table = db_mapper.table
    # The reply's tool calls get real values only where these tools take them.
    request.state.privacy_tool_params = declared_tool_params(form_data.get("tools"))
    if counts:
        log.info("privacy: pseudonymized %s", counts)
    return form_data


def outbound_system(request, form_data: dict) -> dict:
    """The system messages a model's params add after `outbound` ran, the user's
    name and location filled in: through the same mapper, so the reply still
    reverses. A no-op for a request `outbound` never saw."""
    db_mapper = getattr(request.state, "privacy_mapper", None)
    if db_mapper is None:
        return form_data
    rules = rules_from_config(config(request))
    hints = ((form_data.get("metadata") or {}).get("privacy") or {}).get("known")
    for message in form_data.get("messages") or []:
        if message.get("role") == "system":
            _rewrite_message(
                message, lambda text: pseudonymize(text, rules, db_mapper, hints)[0]
            )
    return form_data


def _rewrite_message(message: dict, rewrite) -> None:
    """A message's text, whether a plain string or a list of typed parts, and the
    arguments of the tool calls it carries: a reversed reply resends them real."""
    if message.get("tool_calls"):
        # Copies: the middleware hands over the content block's own list, and
        # the UI and the database must keep the real values.
        message["tool_calls"] = copy.deepcopy(message["tool_calls"])
    _map_tool_arguments(message.get("tool_calls"), rewrite)
    content = message.get("content")
    if isinstance(content, str):
        message["content"] = rewrite(content)
        return
    for part in content if isinstance(content, list) else []:
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            part["text"] = rewrite(part["text"])


def _map_tool_arguments(tool_calls, fn, declared=None) -> None:
    """`fn` over every non-empty string in each tool call's arguments; with
    `declared` ({tool name: parameter names}), only over the parameters the
    called tool declares."""
    # Arguments arrive as a JSON string (OpenAI-style) or a parsed object. A
    # string is parsed first, because `json.dumps` writes a non-ASCII name as an
    # escape sequence and a match on the raw text would miss it; text that is
    # not JSON goes through `fn` whole. Keys are parameter names, never user
    # text. Outbound and reverse share this walker, so neither skips a shape.
    def walk(value):
        if isinstance(value, str):
            return fn(value) if value else value
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        return value

    for call in tool_calls or []:
        function = call.get("function") or {}
        keys = None if declared is None else declared.get(function.get("name"), frozenset())

        def mapped(value):
            # Undeclared parameters, and the calls of undeclared tools, keep
            # their stand-ins: a real value reaches only what the tool accepts.
            if keys is None:
                return walk(value)
            if isinstance(value, dict):
                return {k: walk(v) if k in keys else v for k, v in value.items()}
            return value

        arguments = function.get("arguments")
        if isinstance(arguments, str) and arguments:
            try:
                parsed = json.loads(arguments)
            except ValueError:
                function["arguments"] = fn(arguments) if keys is None else arguments
            else:
                function["arguments"] = json.dumps(mapped(parsed), ensure_ascii=False)
        elif arguments:
            function["arguments"] = mapped(arguments)


def declared_tool_params(tools) -> dict[str, frozenset]:
    """Each native tool's top-level parameter names, from a request's `tools`."""
    declared = {}
    for tool in tools or []:
        function = (tool or {}).get("function") or {}
        if function.get("name"):
            declared[function["name"]] = frozenset((function.get("parameters") or {}).get("properties") or {})
    return declared


def tool_params_for(request):
    """The tools `outbound` saw this request declare; None when it never ran."""
    return getattr(request.state, "privacy_tool_params", None)


def reverse_text(text: str, table: dict[str, str]) -> str:
    return reverse(text, table)


# Where providers put a model's thinking: the answer's twin, shown to the reader.
REASONING_KEYS = ("reasoning_content", "reasoning", "thinking")


def reverse_completion(response: dict, table: dict[str, str], tool_params=None) -> None:
    """A whole (non-streamed) completion: content, reasoning and tool arguments."""
    for choice in response.get("choices") or []:
        message = choice.get("message") or {}
        for key in ("content", *REASONING_KEYS):
            if isinstance(message.get(key), str):
                message[key] = reverse_text(message[key], table)
        reverse_tool_calls(message.get("tool_calls") or [], table, tool_params)


def reverse_tool_calls(tool_calls: list, table: dict[str, str], tool_params=None) -> None:
    _map_tool_arguments(tool_calls, lambda text: reverse_text(text, table), tool_params)


def stream_reverser(table: dict[str, str]) -> StreamReverser:
    return StreamReverser(table)


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
        reverser = stream_reverser(table_for(request))
        reverser.tool_params = tool_params_for(request)  # read by finish_stream
        return reverser
    return PassThrough()


def finish_stream(reverser, tool_calls: list) -> str:
    """End of a streamed reply: the held-back tail, and tool arguments put back."""
    tail = reverser.flush()
    if reverser.active:
        reverse_tool_calls(tool_calls, reverser.table, getattr(reverser, "tool_params", None))
    return tail


def flush_reasoning(reverser, content_blocks: list) -> None:
    """The reasoning the reverser held back, added to the last reasoning block."""
    tail = reverser.flush()
    if not tail:
        return
    for block in reversed(content_blocks):
        if block["type"] == "reasoning":
            block["content"] += tail
            return


def reverse_sse_for(request, lines):
    """The provider's SSE lines, reversed when privacy covers this request."""
    if getattr(request.state, "privacy_active", False):
        return reverse_sse(lines, table_for(request), tool_params_for(request))
    return lines


def _as_line(text: str, like) -> bytes | str:
    return text.encode("utf-8") if isinstance(like, bytes) else text


def _sse_body(line) -> str | None:
    """The payload of a `data:` line, or None for any other line."""
    text = (line.decode("utf-8") if isinstance(line, bytes) else line).strip()
    return text[len("data:") :].strip() if text.startswith("data:") else None


def _hold_tool_calls(choice: dict, held: dict) -> None:
    """Move a choice's tool-call argument fragments into `held`, keyed by
    (choice index, call index); the client gets an empty fragment meanwhile."""
    # A stand-in can straddle two fragments, and only the whole JSON shows which
    # parameter a value sits in, so arguments are reversed whole, never piecemeal.
    for n, call in enumerate((choice.get("delta") or {}).get("tool_calls") or []):
        function = call.get("function") or {}
        key = (choice.get("index", 0), call.get("index", n))
        name, arguments = held.get(key, (None, ""))
        fragment = function.get("arguments")
        if isinstance(fragment, str) and fragment:
            arguments += fragment
            function["arguments"] = ""
        held[key] = (name or function.get("name"), arguments)


def _release_tool_calls(held: dict, table, tool_params, only=None) -> dict[int, list]:
    """The held calls (of choice `only`, or all), arguments whole and reversed,
    as delta entries grouped by choice index."""
    released: dict[int, list] = {}
    for key in sorted(k for k in held if only is None or k[0] == only):
        name, arguments = held.pop(key)
        call = {"function": {"name": name, "arguments": arguments}}
        reverse_tool_calls([call], table, tool_params)  # the non-streamed walker
        # The name went out with the first fragment and clients append what
        # arrives, so only the arguments go again.
        entry = {"index": key[1], "function": {"arguments": call["function"]["arguments"]}}
        released.setdefault(key[0], []).append(entry)
    return released


def _reverse_event(body: str, streams: dict, held: dict, table, tool_params) -> str | None:
    """One SSE event with its text deltas reversed (the answer and the reasoning,
    each through its own hold-back buffer in `streams`) and its tool-call arguments
    held until their choice finishes; None when it is not JSON."""
    try:
        data = json.loads(body)
    except ValueError:
        return None
    for choice in data.get("choices") or []:
        delta = choice.get("delta") or {}
        for key in ("content", *REASONING_KEYS):
            if isinstance(delta.get(key), str) and delta[key]:
                delta[key] = streams.setdefault(key, StreamReverser(table)).feed(delta[key])
        _hold_tool_calls(choice, held)
        if choice.get("finish_reason"):
            index = choice.get("index", 0)
            calls = _release_tool_calls(held, table, tool_params, index).get(index)
            if calls:
                choice["delta"] = {**delta, "tool_calls": (delta.get("tool_calls") or []) + calls}
    return f"data: {json.dumps(data)}\n\n"


async def reverse_sse(lines, table: dict[str, str], tool_params=None):
    """Server-sent event lines from a provider: answer and reasoning deltas
    reversed in order, tool-call arguments reversed whole when their choice
    finishes."""
    streams, held = {"content": StreamReverser(table)}, {}
    async for line in lines:
        body = _sse_body(line)
        if body is None:
            yield line
        elif body == "[DONE]":
            for key, stream in streams.items():
                tail = stream.flush()
                if tail:
                    extra = json.dumps({"choices": [{"index": 0, "delta": {key: tail}}]})
                    yield _as_line(f"data: {extra}\n\n", line)
            # Calls of a provider that sent no finish_reason come back here.
            left = _release_tool_calls(held, table, tool_params)
            if left:
                choices = [{"index": i, "delta": {"tool_calls": calls}} for i, calls in left.items()]
                yield _as_line(f"data: {json.dumps({'choices': choices})}\n\n", line)
            yield line
        else:
            out = _reverse_event(body, streams, held, table, tool_params)
            yield line if out is None else _as_line(out, line)
