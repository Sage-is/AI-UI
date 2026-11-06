"""A mock OpenAI-compatible provider for the security tests. Standard library only.

GET  /v1/models            one model, "mock-echo". MOCK_MODEL_COUNT=N serves N, the rest
                           shaped like OpenRouter's catalog, and /cK/v1/models gives
                           connection K its own ids: the surface-budget gate's frozen
                           catalog
POST /v1/chat/completions  echoes the last user message, streamed or not. A request
                           that offers tools and holds no tool result gets one call
                           to its first tool instead, with the last user message as
                           that tool's first parameter, so the call carries exactly
                           what left the box
GET  /openapi.json         a one-tool OpenAPI server for AI-UI's tool loop:
POST /echo                 returns the JSON body it was sent
                           A last user message starting "think:" gets its echo as
                           reasoning first (reasoning_content), streamed or not
anything else              200 {"ok": true, "path": ...}: so a proxied path that AI-UI
                           should have refused shows up as a 200, never as the provider's 404
GET  /_requests            every request seen: method, path, authorization, JSON body
DELETE /_requests          forget them

    python3 _mock_provider.py [PORT]      (default 8098)
"""

import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

SEEN: list = []

MODEL_COUNT = int(os.environ.get("MOCK_MODEL_COUNT", "1"))
CATALOG_PATH = re.compile(r"^/(?:(c\d+)/)?v1/models")


def catalog(prefix) -> list:
    """mock-echo, then synthetic models with OpenRouter's fields; fixed, so a byte count holds still."""
    models = [{"id": "mock-echo", "object": "model", "owned_by": "mock"}]
    for i in range(MODEL_COUNT - 1):
        models.append({
            "id": f"{prefix or 'mock'}/model-{i:03d}",
            "name": f"Mock Model {i:03d}",
            "created": 1730000000 + i,
            "description": "A synthetic model in a frozen catalog, sized like a real provider's entry. " * 3,
            "context_length": 131072,
            "architecture": {"modality": "text->text", "input_modalities": ["text"],
                             "output_modalities": ["text"], "tokenizer": "Other"},
            "pricing": {"prompt": "0.0000004", "completion": "0.000002", "request": "0", "image": "0"},
            "top_provider": {"context_length": 131072, "max_completion_tokens": 8192, "is_moderated": False},
            "supported_parameters": ["max_tokens", "temperature", "top_p", "stop", "tools", "reasoning"],
        })
    return models

ECHO_TOOL_SERVER = {
    "openapi": "3.1.0",
    "info": {"title": "rs-mock tools", "version": "1"},
    "paths": {"/echo": {"post": {
        "operationId": "echo",
        "description": "Returns the text it was given.",
        "requestBody": {"required": True, "content": {"application/json": {"schema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Any text."}},
            "required": ["text"],
        }}}},
    }}},
}


def answer(body: dict):
    """The reply to one chat request, as (content, tool_calls); one of them is None."""
    messages = body.get("messages", [])
    last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
    text = last.get("content") if isinstance(last.get("content"), str) else json.dumps(last.get("content"))
    tools = body.get("tools") or []
    if tools and not any(m.get("role") == "tool" for m in messages):
        # AI-UI drops arguments a tool does not declare, so the text goes in the first one.
        function = tools[0].get("function") or {}
        first = next(iter((function.get("parameters") or {}).get("properties") or {}), "text")
        call = {"id": "call-1", "type": "function",
                "function": {"name": function.get("name"), "arguments": json.dumps({first: text})}}
        return None, [call]
    return f"You said: {text}", None


def thought(body: dict):
    """The reasoning a "think:" request gets: its own text, so stand-ins ride in it."""
    last = next((m for m in reversed(body.get("messages", [])) if m.get("role") == "user"), {})
    text = last.get("content") if isinstance(last.get("content"), str) else ""
    return f"Thinking about: {text}" if text.startswith("think:") else None


def chunk(delta: dict, finish_reason=None) -> dict:
    return {"id": "m", "object": "chat.completion.chunk", "model": "mock-echo",
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]}


def stream_events(content, tool_calls, reasoning=None) -> list:
    """The SSE events of a reply, cut in 7-character pieces to split stand-ins on purpose."""
    if tool_calls:
        call = tool_calls[0]
        arguments = call["function"]["arguments"]
        head = {**call, "index": 0, "function": {"name": call["function"]["name"], "arguments": ""}}
        events = [chunk({"role": "assistant", "tool_calls": [head]})]
        events += [chunk({"tool_calls": [{"index": 0, "function": {"arguments": arguments[i:i + 7]}}]})
                   for i in range(0, len(arguments), 7)]
        return events + [chunk({}, "tool_calls")]
    events = [chunk({"reasoning_content": reasoning[i:i + 7]}) for i in range(0, len(reasoning or ""), 7)]
    return events + [chunk({"content": content[i:i + 7]}) for i in range(0, len(content), 7)] + [chunk({}, "stop")]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record(self, body):
        SEEN.append({"method": self.command, "path": self.path,
                     "authorization": self.headers.get("Authorization", ""), "body": body})

    def do_GET(self):
        if self.path.startswith("/_requests"):
            return self._json(200, SEEN)
        self._record(None)
        listing = CATALOG_PATH.match(self.path)
        if listing:
            return self._json(200, {"object": "list", "data": catalog(listing.group(1))})
        if self.path.startswith("/openapi.json"):
            return self._json(200, ECHO_TOOL_SERVER)
        self._json(200, {"ok": True, "path": self.path})

    def do_DELETE(self):
        if self.path.startswith("/_requests"):
            SEEN.clear()
            return self._json(200, {"ok": True})
        self._record(None)
        self._json(200, {"ok": True, "path": self.path})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            body = {"raw": raw.decode("utf-8", "replace")[:500]}
        self._record(body)
        if self.path.startswith("/echo"):
            return self._json(200, body)
        if not self.path.startswith("/v1/chat/completions"):
            return self._json(200, {"ok": True, "path": self.path})
        content, tool_calls = answer(body)
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for event in stream_events(content, tool_calls, thought(body)):
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            return
        message = {"role": "assistant", "content": content, **({"tool_calls": tool_calls} if tool_calls else {})}
        if thought(body):
            message["reasoning_content"] = thought(body)
        self._json(200, {"id": "m", "object": "chat.completion", "model": "mock-echo", "created": int(time.time()),
                         "choices": [{"index": 0, "message": message,
                                      "finish_reason": "tool_calls" if tool_calls else "stop"}],
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})


if __name__ == "__main__":
    # It runs inside a test container on a private network, so it listens on every interface there.
    HTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 8098), Handler).serve_forever()  # nosec B104
