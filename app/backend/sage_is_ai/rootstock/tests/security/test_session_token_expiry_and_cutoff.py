"""Session tokens carry `iat` and `exp`, and one without `iat` is refused at the API and at
the socket (2026-10-23).

JWT_EXPIRES_IN defaulted to "-1", so a sign-in minted a token that never expired, and most
mint sites set no `iat`, the claim the try.sage reset cutoff compares. Every session mint
now goes through one helper, and the socket applies the same rules as the API.

Runs against a box (RS_BASE_URL). Forging a token without `iat` needs the box's signing
key: RS_SECRET_KEY, or RS_SECRET_KEY_FILE naming a copy of the box's
/app/backend/data/.webui_secret_key. Without either, the two refusal tests skip.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import socket
import ssl
import time
import unittest
import urllib.parse
import uuid
from pathlib import Path

from ._http import BASE, admin, call, new_user

SECRET = os.environ.get("RS_SECRET_KEY", "")
if not SECRET and os.environ.get("RS_SECRET_KEY_FILE"):
    SECRET = Path(os.environ["RS_SECRET_KEY_FILE"]).read_text().strip()
FOUR_WEEKS = 4 * 7 * 24 * 3600
# A forged control token is issued this long ago: PyJWT refuses an `iat` in its future, and
# a box in a VM can run a few seconds behind the host.
CLOCK_SKEW = 300
SOCKET_PATH = "/ws/socket.io/?EIO=4&transport=websocket"


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def claims_of(token: str) -> dict:
    """The payload of a JWT, read without checking the signature."""
    part = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def forge(claims: dict) -> str:
    """An HS256 token signed with the box's key, the way the app signs its own."""
    head = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64url(json.dumps(claims, separators=(",", ":")).encode())
    sig = hmac.new(SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{b64url(sig)}"


class WebSocket:
    """Just enough of RFC 6455 to send text frames and read them back."""

    def __init__(self, base: str, path: str):
        u = urllib.parse.urlparse(base)
        host, port = u.hostname, u.port or (443 if u.scheme == "https" else 80)
        self.sock = socket.create_connection((host, port), timeout=15)
        if u.scheme == "https":
            self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=host)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                           "Sec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            head += chunk
        status = head.split(b"\r\n", 1)[0].decode(errors="replace")
        if " 101 " not in status:
            raise RuntimeError(f"the websocket handshake was refused: {status} {head[-200:]!r}")
        self.buf = head.split(b"\r\n\r\n", 1)[1]

    def _exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("the socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self) -> str:
        """The next text frame's payload; control frames are skipped."""
        while True:
            b1, b2 = self._exact(2)
            opcode, length = b1 & 0x0F, b2 & 0x7F
            if length == 126:
                length = int.from_bytes(self._exact(2), "big")
            elif length == 127:
                length = int.from_bytes(self._exact(8), "big")
            mask = self._exact(4) if b2 & 0x80 else b""
            data = self._exact(length)
            if mask:
                data = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
            if opcode == 0x8:
                raise RuntimeError(f"the server closed the socket: {data!r}")
            if opcode == 0x1:
                return data.decode()

    def send(self, text: str) -> None:
        data, mask = text.encode(), os.urandom(4)
        head = bytearray([0x81])
        if len(data) < 126:
            head.append(0x80 | len(data))
        elif len(data) < 65536:
            head += bytes([0x80 | 126]) + len(data).to_bytes(2, "big")
        else:
            head += bytes([0x80 | 127]) + len(data).to_bytes(8, "big")
        self.sock.sendall(bytes(head) + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(data)))

    def close(self) -> None:
        self.sock.close()


def socket_user_join(token: str):
    """Connect to the box's Socket.IO as the frontend does and emit user-join; the ack's
    payload, which names the user, or is empty when the token was refused."""
    ws = WebSocket(BASE, SOCKET_PATH)
    try:
        opened = ws.recv()  # Engine.IO open: 0{"sid": ...}
        if not opened.startswith("0"):
            raise RuntimeError(f"unexpected first packet: {opened[:80]!r}")
        ws.send("40" + json.dumps({"token": token}))  # Socket.IO connect, with auth
        connected = ws.recv()
        if not connected.startswith("40"):
            raise RuntimeError(f"the connect was refused: {connected[:120]!r}")
        ws.send("421" + json.dumps(["user-join", {"auth": {"token": token}}]))  # event, ack id 1
        while True:
            packet = ws.recv()
            if packet.startswith("431"):
                return json.loads(packet[3:])
            if packet == "2":  # Engine.IO ping
                ws.send("3")
    finally:
        ws.close()


class SessionTokenExpiryAndCutoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = admin()

    def assert_session_claims(self, token: str, where: str) -> None:
        claims = claims_of(token)
        self.assertIn("iat", claims, f"{where} minted a session without iat: {claims}")
        self.assertIn("exp", claims, f"{where} minted a session without exp: {claims}")
        self.assertAlmostEqual(claims["exp"] - claims["iat"], FOUR_WEEKS, delta=60,
                               msg=f"{where}: exp - iat is not four weeks: {claims}")

    def test_a_sign_in_mints_iat_and_a_four_week_exp(self):
        user = new_user("user", admin_user=self.admin)  # new_user signs in through /signin
        self.assert_session_claims(user.token, "/api/v1/auths/signin")

    def test_the_other_mint_sites_stamp_the_same_claims(self):
        tag = uuid.uuid4().hex[:10]
        r = self.admin.post("/api/v1/auths/add", {"name": f"RS {tag}", "email": f"rs-{tag}@example.com",
                                                   "password": f"pw-{tag}-long-enough", "role": "user"})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assert_session_claims(r.json()["token"], "/api/v1/auths/add")
        temp = new_user("temporary", admin_user=self.admin)
        r = temp.post("/api/v1/auths/claim", {"email": f"rs-claimed-{tag}@example.com",
                                              "password": f"claimed-{tag}-long-enough"})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assert_session_claims(r.json()["token"], "/api/v1/auths/claim")

    @unittest.skipUnless(SECRET, "RS_SECRET_KEY (the box's signing key) is needed to forge a token")
    def test_the_api_refuses_a_session_token_without_iat(self):
        user = new_user("user", admin_user=self.admin)
        now = int(time.time())
        r = call("GET", "/api/v1/auths/", forge({"id": user.id, "iat": now - CLOCK_SKEW, "exp": now + 600}))
        self.assertEqual(r.status, 200, f"the forged control token must pass; is RS_SECRET_KEY the box's key? "
                                        f"HTTP {r.status} {r.text[:120]}")
        r = call("GET", "/api/v1/auths/", forge({"id": user.id, "exp": now + 600}))
        self.assertEqual(r.status, 401, f"a session without iat was accepted: HTTP {r.status} {r.text[:120]}")

    @unittest.skipUnless(SECRET, "RS_SECRET_KEY (the box's signing key) is needed to forge a token")
    def test_the_socket_refuses_a_session_token_without_iat(self):
        user = new_user("user", admin_user=self.admin)
        now = int(time.time())
        ack = socket_user_join(forge({"id": user.id, "iat": now - CLOCK_SKEW, "exp": now + 600}))
        self.assertEqual([a.get("id") for a in ack], [user.id], f"the control token must join: {ack}")
        ack = socket_user_join(forge({"id": user.id, "exp": now + 600}))
        self.assertEqual(ack, [], f"the socket joined a session without iat: {ack}")


if __name__ == "__main__":
    unittest.main()
