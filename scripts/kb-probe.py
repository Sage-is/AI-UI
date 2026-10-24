#!/usr/bin/env python3
"""Read-only knowledge-base health probe for one AI-UI instance.

usage: scripts/kb-probe.py public|keytest|admin|kbs [BASE_URL]

Run the admin parts under `sage-secret run`, so the key reaches only this
process: an env file holding SAGE_STARTR_CLOUD_ADMIN_KEY=bw:<vault item>.

The admin key comes from SAGE_STARTR_CLOUD_ADMIN_KEY in the environment and is
never printed. Output masks fields named like keys and any sk- string, and never
shows document text: knowledge bases report counts and distances only. Never
calls /retrieval/config or /retrieval/embedding (they return keys).
"""
import json, os, re, sys, urllib.error, urllib.request

BASE = (sys.argv[2] if len(sys.argv) > 2 else "https://sage.startr.cloud").rstrip("/")
UA = "sage-kb-probe/1.0 (+https://sage.is)"
SECRET_NAME = re.compile(r"key|secret|token|password|authorization|cookie", re.I)
SECRET_VAL = re.compile(r"sk-[A-Za-z0-9_\-]{8,}|://[^/\s:@]+:[^/\s@]+@")


def mask(o):
    if isinstance(o, dict):
        return {k: ("[masked]" if SECRET_NAME.search(k) and v not in (None, "", [], {}) and not isinstance(v, bool) else mask(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [mask(v) for v in o]
    if isinstance(o, str):
        return SECRET_VAL.sub("[masked]", o)
    return o


def call(method, path, auth=False, body=None, timeout=45):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if auth:
        key = os.environ.get("SAGE_STARTR_CLOUD_ADMIN_KEY", "").strip().strip('"').strip("'")
        if not key:
            sys.exit("SAGE_STARTR_CLOUD_ADMIN_KEY is not set")
        headers["Authorization"] = "Bearer " + key
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, status = r.read().decode("utf-8", "replace"), r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read().decode("utf-8", "replace"), e.code
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw[:300]


def show(label, status, payload):
    print(f"## {label} -> {status}")
    if isinstance(payload, str):
        print(SECRET_VAL.sub("[masked]", payload))
    else:
        print(json.dumps(mask(payload), indent=1, default=str)[:200000])


def public():
    for p in ("/health", "/health/db", "/api/config"):
        s, j = call("GET", p)
        if p == "/api/config" and isinstance(j, dict):
            j = {k: j.get(k) for k in ("name", "version", "features") if k in j}
        show(p, s, j)
    s, j = call("GET", "/api/v1/retrieval/")
    if isinstance(j, dict) and "template" in j:
        j["template"] = f"<{len(j['template'] or '')} chars>"
    show("/api/v1/retrieval/ (no auth)", s, j)


def keytest():
    s, _ = call("GET", "/api/v1/retrieval/models/status", auth=True)
    print(f"keytest /api/v1/retrieval/models/status -> {s}")
    sys.exit(0 if s == 200 else 1)


def admin():
    for p in ("/api/v1/retrieval/models/status", "/api/v1/retrieval/sprigs/catalog", "/api/v1/diagnostics/health"):
        s, j = call("GET", p, auth=True)
        show(p, s, j)


def kbs():
    s, j = call("GET", "/api/v1/knowledge/", auth=True)
    if s != 200 or not isinstance(j, list):
        show("/api/v1/knowledge/", s, j)
        return
    print(f"## {len(j)} knowledge bases")
    for kb in j:
        files = kb.get("files") or []
        ids = (kb.get("data") or {}).get("file_ids", [])
        row = {"id": kb.get("id"), "name": kb.get("name"), "files": len(files), "file_ids": len(ids), "updated_at": kb.get("updated_at")}
        if files or ids:
            qs, qj = call("POST", "/api/v1/retrieval/query/collection", auth=True,
                          body={"collection_names": [kb["id"]], "query": kb.get("name") or "overview", "k": 3}, timeout=120)
            if qs == 200 and isinstance(qj, dict):
                docs = (qj.get("documents") or [[]])[0]
                dists = (qj.get("distances") or [[]])[0]
                row["query"] = {"status": qs, "hits": len(docs), "distances": [round(d, 3) for d in dists if isinstance(d, (int, float))]}
            else:
                row["query"] = {"status": qs, "error": mask(qj) if not isinstance(qj, str) else SECRET_VAL.sub("[masked]", qj)}
        print(json.dumps(row, default=str))


{"public": public, "keytest": keytest, "admin": admin, "kbs": kbs}[sys.argv[1]]()
