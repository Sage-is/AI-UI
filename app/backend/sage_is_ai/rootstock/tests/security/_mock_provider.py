"""A mock OpenAI-compatible provider for the security tests. Standard library only.

GET  /v1/models            one model, "mock-echo"
POST /v1/chat/completions  echoes the last user message, streamed or not
anything else              200 {"ok": true, "path": ...}: so a proxied path that AI-UI
                           should have refused shows up as a 200, never as the provider's 404
GET  /_requests            every request seen: method, path, authorization, JSON body
DELETE /_requests          forget them

    python3 _mock_provider.py [PORT]      (default 8098)
"""

import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

SEEN: list = []


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
        if self.path.startswith("/v1/models"):
            return self._json(200, {"object": "list", "data": [{"id": "mock-echo", "object": "model", "owned_by": "mock"}]})
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
        if not self.path.startswith("/v1/chat/completions"):
            return self._json(200, {"ok": True, "path": self.path})
        last = next((m for m in reversed(body.get("messages", [])) if m.get("role") == "user"), {})
        text = last.get("content") if isinstance(last.get("content"), str) else json.dumps(last.get("content"))
        reply = f"You said: {text}"
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for i in range(0, len(reply), 7):  # 7-character chunks split stand-ins on purpose
                chunk = {"id": "m", "object": "chat.completion.chunk", "model": "mock-echo",
                         "choices": [{"index": 0, "delta": {"content": reply[i:i + 7]}, "finish_reason": None}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()
            done = {"id": "m", "object": "chat.completion.chunk", "model": "mock-echo",
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            self.wfile.write(f"data: {json.dumps(done)}\n\ndata: [DONE]\n\n".encode())
            self.wfile.flush()
            return
        self._json(200, {"id": "m", "object": "chat.completion", "model": "mock-echo", "created": int(time.time()),
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})


if __name__ == "__main__":
    # It runs inside a test container on a private network, so it listens on every interface there.
    HTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 8098), Handler).serve_forever()  # nosec B104
