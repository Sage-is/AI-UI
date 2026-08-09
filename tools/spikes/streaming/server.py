#!/usr/bin/env python3
"""Phase S streaming spike — server half. THROWAWAY (see MEMO.md).

Answers one question: can a vanilla island in a server-rendered shell stream a
completion as well as the SvelteKit chat core does, over HTTP/2, with autoscroll
and a stop button that really stops?

Deliberately stdlib-only and standalone. It does NOT import the app: the point
is to judge the transport and rendering pattern, not to re-test our backend. It
streams a deterministic markdown document token-by-token so runs are comparable
and a reviewer can replay them. Swap the generator for a real
/api/chat/completions proxy and nothing else changes.

The stop button is the load-bearing check: a client abort must stop SERVER work,
not just hide output. We log every token written, so `stopped_at` in the run log
is the proof — if the server keeps generating after a stop, this spike failed
regardless of what the UI looks like.
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8140

# Exercises the streaming-markdown cases the real chat hits: prose, inline
# emphasis, a fenced code block (the one that breaks naive incremental
# renderers, since it is invalid markdown until the closing fence arrives), a
# list, and a heading.
DOC = """## Streaming markdown

The island renders **incrementally** while tokens arrive, so a partial document
must never look broken. A fenced block is the hard case:

```python
def graft(sprig: str) -> bool:
    # invalid markdown until the closing fence lands
    return verify(sprig) and extract(sprig)
```

Then it keeps going with a list:

- autoscroll must hold at the bottom
- unless the reader scrolls up, which pins it
- and the stop button must stop *server* work

That is the whole spike.

### Why the document is long

Autoscroll only means anything once content OVERFLOWS the viewport, so a short
demo document proves nothing about pinning. A real answer is long; this one is
too, deliberately.

The reader must be able to scroll up mid-stream and stay there. That is the
behaviour people notice when it is missing, and it is the one a naive
`scrollTop = scrollHeight` on every token gets wrong.

```javascript
// the naive version, which fights the reader
output.addEventListener('change', () => {
  scroller.scrollTop = scroller.scrollHeight;  // always. even when scrolled up.
});
```

- pinning holds while the reader sits at the bottom
- it releases the moment they scroll away
- it never yanks them back mid-read
- and stopping must halt the server, not just the paint

Enough text to overflow a 22rem box several times over, which is the point."""

# Doubled for manual testing: you cannot judge "too stuck to the bottom" without
# enough scrollback to get properly lost in. Numbered so scroll POSITION is
# legible at a glance — when you scroll up mid-stream you can see exactly where
# you are, which an undifferentiated wall of text does not tell you.
DOC += "\n\n" + "\n\n".join(
    f"""### Section {n}

Scrollback marker {n}. Streaming continues below this point, so if the view is
pinned you will be carried past it. Scroll up and this heading should stay put
under your cursor while tokens keep arriving underneath.

- marker {n}.a — pinning must not fight you here
- marker {n}.b — the jump button is the way back
"""
    for n in range(1, 8)
)

# ~3 chars/token, the granularity a real SSE completion arrives at.
TOKENS = [DOC[i:i + 3] for i in range(0, len(DOC), 3)]
RUNLOG = HERE / "run.log"


def log(event, **kw):
    rec = {"t": round(time.time(), 3), "event": event, **kw}
    with open(RUNLOG, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # Caddy fronts this and speaks h2 to browsers

    def log_message(self, *a):
        pass  # our own structured log instead

    def _send(self, code, ctype, body=b"", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            # The shell is SERVER-RENDERED chrome. htmx swaps fragments into it;
            # the island only owns the streaming region.
            return self._send(200, "text/html; charset=utf-8",
                              (HERE / "shell.html").read_bytes())
        if path == "/island.js":
            return self._send(200, "application/javascript; charset=utf-8",
                              (HERE / "island.js").read_bytes())
        if path == "/vendor/htmx.min.js":
            return self._send(200, "application/javascript; charset=utf-8",
                              (HERE / "vendor" / "htmx.min.js").read_bytes(),
                              {"Cache-Control": "public, max-age=31536000, immutable"})
        if path == "/vendor/md.js":
            return self._send(200, "application/javascript; charset=utf-8",
                              (HERE / "vendor" / "md.js").read_bytes())
        if path == "/fragment/composer":
            # An htmx-swapped server fragment, to prove shell and island coexist.
            # startr.style inline props, mobile-first: buttons stay comfortably
            # tappable at phone size, and the row only needs to grow its gap on
            # wider viewports. Nothing repeats a base value in a suffix.
            btn = ("--ff:inherit; --size:inherit; --p:.5rem 1rem; --br:.4rem; --cur:pointer; "
                   "--b:1px solid color-mix(in srgb, currentColor 30%, transparent); "
                   "--bgc:transparent; --c:inherit; "
                   "--hvr-bgc:color-mix(in srgb, currentColor 8%, Canvas)")
            return self._send(200, "text/html; charset=utf-8", (
                '<div id="composer" style="--d:flex; --ai:center; --g:.5rem; '
                '--g-md:.75rem; --mt:.8rem; --fw:wrap">'
                f'<button id="send" style="{btn}">Send</button>'
                f'<button id="stop" disabled style="{btn}; '
                '--bc:color-mix(in srgb, red 45%, currentColor)">Stop</button>'
                '<span id="status" style="--size:.8rem; --op:.7">idle</span>'
                "</div>"
            ).encode())
        if path == "/meta":
            return self._send(200, "application/json",
                              json.dumps({"tokens": len(TOKENS)}).encode())
        if path == "/stream":
            return self.stream()
        return self._send(404, "text/plain", b"not found")

    def stream(self):
        """Chunked token stream. Abort-aware: a client disconnect stops work."""
        run = str(int(time.time() * 1000))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        log("stream_open", run=run, tokens=len(TOKENS))

        sent = 0
        try:
            for tok in TOKENS:
                self.wfile.write(
                    b"data: " + json.dumps({"tok": tok}).encode() + b"\n\n")
                self.wfile.flush()  # raises once the client goes away
                sent += 1
                time.sleep(0.02)
        except (BrokenPipeError, ConnectionResetError):
            # THE assertion this spike exists for: server work ceased on abort.
            log("stream_aborted", run=run, sent=sent, total=len(TOKENS))
            return
        try:
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            log("stream_aborted", run=run, sent=sent, total=len(TOKENS))
            return
        log("stream_complete", run=run, sent=sent, total=len(TOKENS))


if __name__ == "__main__":
    RUNLOG.write_text("")
    print(f"spike server on http://0.0.0.0:{PORT} (tokens={len(TOKENS)})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
