"""OCI pull refusals: python -m unittest sage_is_ai.sprigs.test_oci

A fake registry runs in-process on 127.0.0.1. It answers the manifest with a
Bearer challenge and redirects blobs to a second server on another port, the
way ghcr.io hands blobs to its CDN. Runs on the host or in the image.
"""

import asyncio
import hashlib
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sage_is_ai.sprigs import oci

TAR = b"zstd-ish payload " * 512
SIG = b"untrusted comment: test\nRWQ...\n"


def digest(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def manifest(layers):
    return {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "layers": [
            {"digest": d, "size": s, "annotations": {oci.TITLE_ANNOTATION: t}}
            for t, d, s in layers
        ],
    }


GOOD = [
    ("art.tar.zst", digest(TAR), len(TAR)),
    ("art.tar.zst.minisig", digest(SIG), len(SIG)),
]


class Fake:
    """Registry on one port, blob CDN on another. Tests set .manifest and .blobs."""

    def __init__(self):
        self.manifest = manifest(GOOD)
        self.blobs = {digest(TAR): TAR, digest(SIG): SIG}
        self.cdn_saw_auth = []
        fake = self

        class Registry(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path.startswith("/token"):
                    return self._send(200, json.dumps({"token": "T0K"}).encode())
                if self.headers.get("Authorization") != "Bearer T0K":
                    realm = f"http://127.0.0.1:{fake.reg.server_port}/token"
                    self.send_response(401)
                    self.send_header(
                        "WWW-Authenticate",
                        f'Bearer realm="{realm}",service="fake",scope="repository:sage/x:pull"',
                    )
                    self.end_headers()
                    return
                if "/manifests/" in self.path:
                    return self._send(200, json.dumps(fake.manifest).encode())
                d = self.path.rsplit("/", 1)[-1]
                self.send_response(307)
                self.send_header(
                    "Location", f"http://127.0.0.1:{fake.cdn.server_port}/b/{d}"
                )
                self.end_headers()

            def _send(self, code, body):
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        class Cdn(Registry):
            def do_GET(self):
                fake.cdn_saw_auth.append(self.headers.get("Authorization"))
                body = fake.blobs.get(self.path.rsplit("/", 1)[-1])
                return (
                    self._send(200, body) if body is not None else self._send(404, b"")
                )

        self.reg = ThreadingHTTPServer(("127.0.0.1", 0), Registry)
        self.cdn = ThreadingHTTPServer(("127.0.0.1", 0), Cdn)
        for s in (self.reg, self.cdn):
            threading.Thread(target=s.serve_forever, daemon=True).start()

    @property
    def repo(self):
        return f"127.0.0.1:{self.reg.server_port}/sage/x"

    def close(self):
        for s in (self.reg, self.cdn):
            s.shutdown()
            s.server_close()


class PullAgainstFakeRegistry(unittest.TestCase):
    def setUp(self):
        self.fake = Fake()
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name) / "staging"

    def tearDown(self):
        self.fake.close()
        self.tmp.cleanup()

    def pull(self, insecure=True):
        return asyncio.run(oci.pull(self.fake.repo, "v2", self.dest, insecure=insecure))

    def assertNothingLeft(self):
        left = sorted(p.name for p in self.dest.iterdir()) if self.dest.exists() else []
        self.assertEqual(left, [])

    def test_pulls_every_titled_layer_and_verifies_it(self):
        files = self.pull()
        self.assertEqual(
            [p.name for p in files], ["art.tar.zst", "art.tar.zst.minisig"]
        )
        self.assertEqual((self.dest / "art.tar.zst").read_bytes(), TAR)
        self.assertEqual((self.dest / "art.tar.zst.minisig").read_bytes(), SIG)

    def test_token_never_reaches_the_redirect_host(self):
        self.pull()
        self.assertEqual(self.fake.cdn_saw_auth, [None, None])

    def test_tampered_blob_is_a_digest_error_and_leaves_nothing(self):
        self.fake.blobs[digest(TAR)] = TAR[:-1] + b"!"
        with self.assertRaises(oci.OCIDigestError):
            self.pull()
        self.assertNothingLeft()

    def test_extra_bytes_are_refused(self):
        self.fake.manifest = manifest([("art.tar.zst", digest(TAR), len(TAR) - 10)])
        with self.assertRaises(oci.OCIDigestError):
            self.pull()
        self.assertNothingLeft()

    def test_path_traversal_title_is_refused_before_any_download(self):
        for title in ["../escape.tar.zst", "a/b.tar.zst", ".hidden", "..", "x\\y"]:
            with self.subTest(title):
                self.fake.manifest = manifest([(title, digest(TAR), len(TAR))])
                with self.assertRaises(oci.OCIError):
                    self.pull()
        self.assertFalse((Path(self.tmp.name) / "escape.tar.zst").exists())
        self.assertEqual(self.fake.cdn_saw_auth, [])

    def test_image_index_is_refused(self):
        self.fake.manifest = {
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [],
        }
        with self.assertRaisesRegex(oci.OCIError, "image index"):
            self.pull()

    def test_oversize_layer_is_refused_before_download(self):
        os.environ["SPRIG_MAX_ARTIFACT_BYTES"] = "100"
        try:
            with self.assertRaisesRegex(oci.OCIError, "SPRIG_MAX_ARTIFACT_BYTES"):
                self.pull()
        finally:
            del os.environ["SPRIG_MAX_ARTIFACT_BYTES"]
        self.assertEqual(self.fake.cdn_saw_auth, [])

    def test_non_sha256_digest_is_refused(self):
        self.fake.manifest = manifest([("art.tar.zst", "md5:abc", len(TAR))])
        with self.assertRaises(oci.OCIError):
            self.pull()

    def test_https_is_required_unless_insecure(self):
        # The fake speaks plain HTTP only; without insecure=True the client
        # must try TLS and fail rather than fall back to HTTP.
        with self.assertRaises(oci.OCIError):
            self.pull(insecure=False)
        self.assertEqual(self.fake.cdn_saw_auth, [])


class PureHelpers(unittest.TestCase):
    def test_split_reference(self):
        self.assertEqual(
            oci.split_reference("ghcr.io/sage-is/sprig-x"),
            ("ghcr.io", "sage-is/sprig-x"),
        )
        self.assertEqual(
            oci.split_reference("local-registry:5000/sprig-x"),
            ("local-registry:5000", "sprig-x"),
        )
        with self.assertRaises(oci.OCIError):
            oci.split_reference("no-slash")

    def test_bearer_challenge(self):
        c = oci.parse_bearer_challenge(
            'Bearer realm="https://ghcr.io/token",service="ghcr.io",scope="repository:a/b:pull"'
        )
        self.assertEqual(c["realm"], "https://ghcr.io/token")
        self.assertEqual(c["scope"], "repository:a/b:pull")
        with self.assertRaises(oci.OCIError):
            oci.parse_bearer_challenge('Basic realm="x"')

    def test_untitled_layers_are_skipped_and_duplicates_refused(self):
        m = manifest(GOOD)
        m["layers"].append({"digest": digest(b"cfg"), "size": 3})
        self.assertEqual(len(oci.titled_layers(m)), 2)
        with self.assertRaises(oci.OCIError):
            oci.titled_layers(manifest(GOOD + GOOD[:1]))


if __name__ == "__main__":
    unittest.main()
