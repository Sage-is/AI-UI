"""HTTP helpers for the security tests: standard library only, against a running box.

RS_BASE_URL names the box (default http://localhost:8181). The first sign-up on an
empty box becomes its admin; RS_ADMIN_EMAIL and RS_ADMIN_PASSWORD name that account
(defaults below) so a second run signs in instead. Every other user a test needs is
signed up fresh with a unique address, then given its role by the admin.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("RS_BASE_URL", "http://localhost:8181").rstrip("/")
ADMIN_EMAIL = os.environ.get("RS_ADMIN_EMAIL", "rs-admin@example.com")
ADMIN_PASSWORD = os.environ.get("RS_ADMIN_PASSWORD", "rs-admin-password-1")


class Response:
    def __init__(self, status: int, headers, body: bytes):
        self.status, self.headers, self.body = status, headers, body

    def json(self):
        try:
            return json.loads(self.body or b"null")
        except ValueError:
            return None

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


def call(method: str, path: str, token: str | None = None, body=None, *, raw: bytes | None = None,
         headers: dict | None = None, timeout: float = 60) -> Response:
    """One request. `body` is sent as JSON; `raw` as given. Errors come back as responses."""
    hdrs = {"User-Agent": "sage-rootstock-security-tests", "Accept": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    hdrs.update(headers or {})
    req = urllib.request.Request(BASE + path, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 — BASE is the test box's http(s) URL
            return Response(r.status, r.headers, r.read())
    except urllib.error.HTTPError as e:
        return Response(e.code, e.headers, e.read())


class User:
    def __init__(self, data: dict, password: str):
        self.id, self.email, self.role = data["id"], data["email"], data["role"]
        self.token, self.password = data["token"], password

    def get(self, path, **kw):
        return call("GET", path, self.token, **kw)

    def post(self, path, body=None, **kw):
        return call("POST", path, self.token, body, **kw)

    def delete(self, path, **kw):
        return call("DELETE", path, self.token, **kw)


def signin(email: str, password: str) -> User | None:
    r = call("POST", "/api/v1/auths/signin", body={"email": email, "password": password})
    return User(r.json(), password) if r.status == 200 else None


def signup(email: str, password: str, name: str) -> User:
    r = call("POST", "/api/v1/auths/signup", body={"email": email, "password": password, "name": name})
    if r.status != 200:
        raise RuntimeError(f"signup {email} failed: HTTP {r.status} {r.text[:200]}")
    return User(r.json(), password)


def admin() -> User:
    """The box's admin: signed in, or created as the first account of an empty box."""
    return signin(ADMIN_EMAIL, ADMIN_PASSWORD) or signup(ADMIN_EMAIL, ADMIN_PASSWORD, "Rootstock Admin")


def new_user(role: str = "user", *, admin_user: User | None = None) -> User:
    """A fresh account with a unique address, set to `role` by the admin when it is not the default."""
    tag = uuid.uuid4().hex[:10]
    user = signup(f"rs-{tag}@example.com", f"pw-{tag}-long-enough", f"RS {tag}")
    if user.role != role:
        boss = admin_user or admin()
        r = boss.post(f"/api/v1/users/{user.id}/update",
                      {"role": role, "name": f"RS {tag}", "email": user.email, "profile_image_url": "/user.png"})
        if r.status != 200:
            raise RuntimeError(f"could not set role {role}: HTTP {r.status} {r.text[:200]}")
        user = signin(user.email, user.password) or user
        user.role = role
    return user
