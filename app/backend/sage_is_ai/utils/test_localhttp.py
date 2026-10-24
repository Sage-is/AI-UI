"""localhttp, the curl replacement: python -m unittest sage_is_ai.utils.test_localhttp"""

import contextlib
import io
import json
import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from sage_is_ai.utils import localhttp


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def _reply(self, code, doc):
        body = json.dumps(doc).encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        Handler.seen.append(("GET", self.path, dict(self.headers), b""))
        if self.path == "/health":
            return self._reply(200, {"status": True})
        if self.path == "/sick":
            return self._reply(200, {"status": False})
        if self.path == "/me":
            return self._reply(200, {"role": "admin", "n": 3})
        return self._reply(403, {"detail": "no"})

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        Handler.seen.append(("POST", self.path, dict(self.headers), body))
        return self._reply(200, {"token": "abc"})


def run(*argv, stdin=""):
    out = io.StringIO()
    with (
        contextlib.redirect_stdout(out),
        contextlib.redirect_stderr(io.StringIO()),
        mock.patch("sys.stdin", io.StringIO(stdin)),
    ):
        code = localhttp.main(list(argv))
    return code, out.getvalue().strip()


class LocalHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        Handler.seen.clear()

    def test_healthcheck_contract(self):
        self.assertEqual(run("--require-true", "status", f"{self.base}/health")[0], 0)
        self.assertEqual(run("--require-true", "status", f"{self.base}/sick")[0], 1)

    def test_field_prints_one_value(self):
        self.assertEqual(run("--field", "role", f"{self.base}/me"), (0, "admin"))
        self.assertEqual(run("--field", "n", f"{self.base}/me"), (0, "3"))
        self.assertEqual(run("--field", "missing", f"{self.base}/me")[0], 1)

    def test_http_error_exits_22_like_curl_f(self):
        self.assertEqual(run(f"{self.base}/forbidden")[0], localhttp.EXIT_HTTP_ERROR)

    def test_body_from_stdin_stays_out_of_argv(self):
        code, out = run(
            "--json",
            "@-",
            "--field",
            "token",
            f"{self.base}/signup",
            stdin='{"password":"s3cret"}',
        )
        self.assertEqual((code, out), (0, "abc"))
        method, _, headers, body = Handler.seen[-1]
        self.assertEqual(method, "POST")
        self.assertEqual(json.loads(body), {"password": "s3cret"})
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_auth_headers(self):
        run("--bearer", "T", f"{self.base}/me")
        self.assertEqual(Handler.seen[-1][2]["Authorization"], "Bearer T")
        run("--cookie-token", "C", f"{self.base}/me")
        self.assertEqual(Handler.seen[-1][2]["Cookie"], "token=C")

    def test_refuses_non_http_schemes(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            for url in ("file:///etc/passwd", "ftp://127.0.0.1/x", "127.0.0.1/health"):
                self.assertEqual(run(url)[0], localhttp.EXIT_UNSUPPORTED, url)
        urlopen.assert_not_called()

    def test_unreachable_exits_7_after_waiting(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        self.assertEqual(
            run("--wait-seconds", "1", f"http://127.0.0.1:{port}/health")[0], 7
        )


if __name__ == "__main__":
    unittest.main()
