#!/usr/bin/env python3
"""Re-index knowledge bases file by file, deleting nothing.

usage: scripts/kb-reindex.py [BASE_URL] [KNOWLEDGE BASE NAME ...]
       scripts/kb-reindex.py [BASE_URL] --vector-on

--vector-on only switches the vector store on: a vector-chroma graft and every
boot leave the client off on a box that is not a try.sage trial, until the AI
Engine's vector bootstrap runs. It calls that bootstrap alone (POST
/api/v1/retrieval/models/download with no components) and waits for
vector_db_ready.

The safe half of POST /api/v1/knowledge/reindex. That route deletes every
knowledge base whose data is null (5 of 18 on sage.startr.cloud in October
2026) and drops each collection first. This sends each file's stored text
through POST /api/v1/retrieval/process/file into its knowledge base's
collection, one file at a time, and leaves a knowledge base without files or
with null data exactly as it is. Names limit the run to those knowledge bases.

Run it under `sage-secret run`, so the admin key reaches only this process:
  SAGE_STARTR_CLOUD_ADMIN_KEY=bw:sage-startr-cloud-admin-key \
    sage-secret run -- python3 scripts/kb-reindex.py
The key is never printed, and the output holds counts and statuses only.
A file without stored text (`file.data.content`) has nothing to send and fails.
Check the result with scripts/kb-probe.py kbs.
"""
import json, os, sys, time, urllib.error, urllib.request

args = sys.argv[1:]
BASE = (args.pop(0) if args and args[0].startswith("http") else "https://sage.startr.cloud").rstrip("/")
VECTOR_ON = "--vector-on" in args
ONLY = {a.strip() for a in args if a != "--vector-on"}
UA = "sage-kb-reindex/1.0 (+https://sage.is)"


def call(method, path, body=None, timeout=600):
    key = os.environ.get("SAGE_STARTR_CLOUD_ADMIN_KEY", "").strip().strip('"').strip("'")
    if not key:
        sys.exit("SAGE_STARTR_CLOUD_ADMIN_KEY is not set")
    headers = {"User-Agent": UA, "Accept": "application/json", "Authorization": "Bearer " + key}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, {"detail": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:  # a Cloudflare cut or a timeout: the server may still finish the file
        return None, {"detail": f"{type(e).__name__}: {e}"}


def vector_on():
    status, _ = call("POST", "/api/v1/retrieval/models/download", {"components": []})
    print(f"vector bootstrap: {status}", flush=True)
    ms = {}
    for _ in range(36):
        _, ms = call("GET", "/api/v1/retrieval/models/status")
        if isinstance(ms, dict) and ms.get("vector_db_ready"):
            break
        time.sleep(5)
    ms = ms if isinstance(ms, dict) else {}
    print(f"vector_db_ready: {bool(ms.get('vector_db_ready'))}; embedding: {(ms.get('models') or {}).get('embedding')}")
    return 0 if ms.get("vector_db_ready") else 1


def main():
    if VECTOR_ON:
        return vector_on()
    status, kbs = call("GET", "/api/v1/knowledge/")
    if status != 200:
        sys.exit(f"listing knowledge bases failed: {status}")
    totals = {"indexed": 0, "already": 0, "cut": 0, "failed": 0}
    for kb in kbs:
        name, data = kb["name"].strip(), kb.get("data")
        if ONLY and name not in ONLY:
            continue
        if not isinstance(data, dict) or not data.get("file_ids"):
            print(f"{name!r}: no files or null data, left as it is", flush=True)
            continue
        began, counts, first = time.monotonic(), dict.fromkeys(totals, 0), ""
        for fid in data["file_ids"]:
            status, res = call("POST", "/api/v1/retrieval/process/file", {"file_id": fid, "collection_name": kb["id"]})
            detail = str((res or {}).get("detail", ""))
            if status == 200:
                kind = "indexed"
            elif "Duplicate content" in detail:  # its text is in the collection already
                kind = "already"
            elif status in (None, 502, 504, 524):  # a proxy cut the wait; the server usually finishes
                kind = "cut"
            else:
                kind = "failed"
                first = first or f"{status} {detail[:90]}"
            counts[kind] += 1
        for k in totals:
            totals[k] += counts[k]
        print(f"{name!r}: {len(data['file_ids'])} files: {counts['indexed']} indexed, {counts['already']} already, "
              f"{counts['cut']} cut, {counts['failed']} failed, {time.monotonic() - began:.0f}s"
              + (f"; first failure: {first}" if first else ""), flush=True)
    print("total: " + ", ".join(f"{v} {k}" for k, v in totals.items())
          + (". Run again to settle the cut ones: a finished file answers 'already'." if totals["cut"] else ""))
    return 1 if totals["failed"] or totals["cut"] else 0


if __name__ == "__main__":
    sys.exit(main())
