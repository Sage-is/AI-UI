"""A mock OpenAI-compatible provider that records every request it receives.

GET  /v1/models            -> one model, "mock-echo"
POST /v1/chat/completions  -> echoes the last user message back, streamed or not
GET  /captured             -> the last request body it saw (what actually left AI-UI)
"""
import json, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer

CAPTURED = []

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, code, obj):
        body = json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path.startswith("/v1/models"):
            return self._json(200, {"object": "list", "data": [{"id": "mock-echo", "object": "model", "owned_by": "mock"}]})
        if self.path.startswith("/captured"):
            return self._json(200, CAPTURED[-1] if CAPTURED else {})
        self._json(404, {"error": "no"})
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(length) or b"{}")
        CAPTURED.append(body)
        last = next((m for m in reversed(body.get("messages", [])) if m.get("role") == "user"), {})
        text = last.get("content") if isinstance(last.get("content"), str) else json.dumps(last.get("content"))
        reply = f"You said: {text}"
        if body.get("stream"):
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
            for i in range(0, len(reply), 7):  # 7-char chunks split pseudonyms on purpose
                chunk = {"id": "m", "object": "chat.completion.chunk", "model": "mock-echo",
                         "choices": [{"index": 0, "delta": {"content": reply[i:i+7]}, "finish_reason": None}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode()); self.wfile.flush()
            done = {"id": "m", "object": "chat.completion.chunk", "model": "mock-echo", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            self.wfile.write(f"data: {json.dumps(done)}\n\ndata: [DONE]\n\n".encode()); self.wfile.flush()
            return
        self._json(200, {"id": "m", "object": "chat.completion", "model": "mock-echo", "created": int(time.time()),
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})

HTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 8098), Handler).serve_forever()
