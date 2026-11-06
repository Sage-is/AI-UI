#!/usr/bin/env python3
"""Usage census of an AI-UI database: counts and shapes, never content.

    python3 census.py PATH.db [PATH.db ...]   JSON report on stdout
    python3 census.py --self-test             plant canaries, prove none leak

Each file opens read-only and immutable, so a snapshot is never touched.
The report holds row counts, typeof() mixes, activity by month, top-level
and message-level JSON key frequencies, enum counts, and the stored config
as a tree whose booleans keep their value and whose other leaves become
shapes. A JSON key or enum value is printed only when it looks like an
identifier and occurs for at least K_USERS distinct users; anything else
is counted under "<other>". Stdlib only.
"""
import json
import os
import re
import sqlite3
import statistics
import sys
import tempfile
import time

K_USERS = 2
IDENT = re.compile(r"^[a-z][a-z0-9_]{0,31}$", re.I)
ENUMS = {
    "user": ("role",), "auth": ("active",), "channel": ("type",),
    "function": ("type", "is_active", "is_global"), "model": ("is_active",),
    "feedback": ("type",), "magic_link": ("role", "is_active"),
    "bridge_connection": ("platform", "mode", "status", "enabled"),
    "chat": ("archived", "pinned"), "chat_share": ("target_type", "share_mode"),
}
PRESENCE = {
    "chat": ("share_id", "folder_id"), "model": ("base_model_id",),
    "user": ("api_key", "oauth_sub", "last_active_at"), "file": ("path", "hash"),
}
TIME_COLS = ("created_at", "updated_at", "last_active_at", "timestamp")


def connect(path):
    uri = f"file:{os.path.abspath(path)}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True)


def q(con, sql, *args):
    return con.execute(sql, args).fetchall()


def to_epoch(v):
    """Seconds since 1970 from int seconds, ms, ns, or an ISO string."""
    if isinstance(v, (int, float)):
        for div in (1, 1e3, 1e6, 1e9):
            if v / div < 4e9:
                return v / div
        return None
    if isinstance(v, str) and v[:4].isdigit():
        try:
            return time.mktime(time.strptime(v[:19], "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            return None
    return None


FIXED = {
    ("user", "role"): {"admin", "user", "pending", "temporary", "facilitator"},
    ("magic_link", "role"): {"admin", "user", "pending", "temporary", "facilitator"},
    ("function", "type"): {"filter", "action", "pipe"},
    ("bridge_connection", "platform"): {"whatsapp", "telegram", "signal", "email"},
    ("message", "role"): {"user", "assistant", "system", "tool"},
}


def anon_counts(pairs, allowed=frozenset()):
    """Count (value, user) pairs. A string is shown when it is in `allowed`, or
    looks like an identifier and K_USERS distinct users share it."""
    users, n = {}, {}
    for value, user in pairs:
        n[value] = n.get(value, 0) + 1
        users.setdefault(value, set()).add(user)
    out = {}
    for value, count in sorted(n.items(), key=lambda kv: -kv[1]):
        if not isinstance(value, str):
            key = json.dumps(value)
        elif value in allowed or (not allowed and IDENT.match(value)
                                  and len(users[value]) >= K_USERS):
            key = value
        else:
            key = "<other>"
        out[key] = out.get(key, 0) + count
    return out


def as_dict(raw):
    if isinstance(raw, (bytes, str)):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return None
    return raw if isinstance(raw, dict) else None


USER_COL = {"user": "id", "auth": "id", "chat_share": "shared_by",
            "magic_link": "created_by", "bridge_thread": "sage_user_id"}
SUBKEYS = {("user", "settings"): ("ui",), ("model", "meta"): ("capabilities",),
           ("group", "permissions"): ("workspace", "chat", "features")}


def months(values):
    """Rows per YYYY-MM, oldest first."""
    out = {}
    for v in values:
        t = to_epoch(v)
        if t is not None:
            m = time.strftime("%Y-%m", time.gmtime(t))
            out[m] = out.get(m, 0) + 1
    return dict(sorted(out.items()))


def json_keys(rows, table, col):
    """Top-level key frequency (k-anonymous by user), plus chosen sub-keys."""
    pairs, sub, true, dicts = [], {}, {}, 0
    for raw, user in rows:
        d = as_dict(raw)
        if d is None:
            continue
        dicts += 1
        pairs.extend((k, user) for k in d)
        for parent in SUBKEYS.get((table, col), ()):
            child = d.get(parent)
            if isinstance(child, dict):
                for k, v in child.items():
                    sub.setdefault(parent, []).append((k, user))
                    if v is True:
                        true.setdefault(parent, []).append((k, user))
    if not dicts:
        return None
    out = {"dicts": dicts, "keys": anon_counts(pairs)}
    for parent, p in sub.items():
        out[f"{parent}.*"] = anon_counts(p)
        if parent in true:
            out[f"{parent}.*=true"] = anon_counts(true[parent])
    return out


def table_census(con, table):
    t = f'"{table}"'
    cols = [(r[1], (r[2] or "").upper()) for r in q(con, f"pragma table_info({t})")]
    names = {c for c, _ in cols}
    user = USER_COL.get(table, "user_id")
    user_expr = f'"{user}"' if user in names else "NULL"
    info = {"rows": q(con, f"select count(*) from {t}")[0][0], "columns": {}}
    for name, decl in cols:
        col = {"type": decl, "typeof": dict(q(con, f'select typeof("{name}"), count(*) from {t} group by 1'))}
        if "text" in col["typeof"]:
            empty = q(con, f"""select count(*) from {t} where "{name}" = ''""")[0][0]
            if empty:
                col["empty"] = empty
        info["columns"][name] = col
        if name in ENUMS.get(table, ()):
            pairs = q(con, f'select "{name}", {user_expr} from {t}')
            info.setdefault("enums", {})[name] = anon_counts(pairs, FIXED.get((table, name), frozenset()))
        if name in PRESENCE.get(table, ()):
            info.setdefault("present", {})[name] = q(
                con, f"""select count(*) from {t} where "{name}" is not null and "{name}" != ''""")[0][0]
        if name in TIME_COLS:
            info.setdefault("months", {})[name] = months(v for (v,) in q(con, f'select "{name}" from {t}'))
        if decl in ("JSON", "TEXT", "") and table not in ("config", "chat") or (table, name) == ("chat", "meta"):
            keys = json_keys(q(con, f'select "{name}", {user_expr} from {t}'), table, name)
            if keys:
                info.setdefault("json", {})[name] = keys
    return info


def spread(values):
    values = sorted(values)
    if not values:
        return None
    pick = lambda f: values[min(len(values) - 1, int(f * len(values)))]  # noqa: E731
    return {"n": len(values), "p50": pick(0.5), "p90": pick(0.9), "max": values[-1]}


def chat_census(con):
    """What a conversation holds: message counts, roles, message-level keys."""
    agents = {r[0] for r in q(con, "select id from model where base_model_id is not null")}
    per_user, sizes, msg_keys, roles, kinds, top = {}, [], [], [], {}, []
    for raw, user in q(con, 'select chat, user_id from chat'):
        per_user[user] = per_user.get(user, 0) + 1
        d = as_dict(raw) or {}
        top.extend((k, user) for k in d)
        msgs = (d.get("history") or {}).get("messages") or {}
        msgs = msgs.values() if isinstance(msgs, dict) else []
        n = 0
        for m in msgs:
            if isinstance(m, dict):
                n += 1
                msg_keys.extend((k, user) for k in m)
                roles.append((m.get("role"), user))
        sizes.append(n)
        models = d.get("models")
        for model in models if isinstance(models, list) else []:
            kind = "agent" if isinstance(model, str) and model in agents else "base_or_external"
            kinds[kind] = kinds.get(kind, 0) + 1
    return {"chats_per_user": spread(per_user.values()), "messages_per_chat": spread(sizes),
            "chat.*": anon_counts(top), "message.*": anon_counts(msg_keys),
            "message.role": anon_counts(roles, FIXED[("message", "role")]),
            "model_kind": kinds}


def shape(v, depth=0):
    """A config value as its shape: booleans stay, the rest is described."""
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "str" if v else "str:empty"
    if isinstance(v, list):
        return f"list[{len(v)}]"
    if isinstance(v, dict):
        if depth > 6 or (v and all(k.isdigit() for k in v)):
            return f"dict[{len(v)}]"
        out = {k: shape(x, depth + 1) for k, x in v.items() if IDENT.match(k)}
        if len(out) < len(v):
            out["<other>"] = len(v) - len(out)
        return out
    return type(v).__name__


def census(path):
    con = connect(path)
    tables = [r[0] for r in q(con, "select name from sqlite_master where type='table' order by name")]
    head = q(con, "select version_num from alembic_version") if "alembic_version" in tables else []
    report = {
        "file_bytes": os.path.getsize(path),
        "journal_mode": q(con, "pragma journal_mode")[0][0],
        "freelist_pages": q(con, "pragma freelist_count")[0][0],
        "alembic_head": head[0][0] if head else None,
        "tables": {t: table_census(con, t) for t in tables},
    }
    if "chat" in tables and "model" in tables:
        report["chat"] = chat_census(con)
    if "config" in tables:
        rows = q(con, "select data from config order by id desc limit 1")
        report["config"] = shape(as_dict(rows[0][0]) or {}) if rows else None
    if "user" in tables:
        last = [t for (v,) in q(con, "select last_active_at from user") if (t := to_epoch(v))]
        if last:
            newest = max(last)
            report["users_active_within_days"] = {
                str(d): sum(1 for t in last if newest - t <= d * 86400) for d in (7, 30, 90)}
    con.close()
    return report


CANARY = "zqxcanary"


def plant(path):
    """A small database with the canary everywhere content can hide."""
    c, now = CANARY, int(time.time())
    con = sqlite3.connect(path)
    con.executescript("""
        create table user(id text, name text, email text, role text, settings text,
                          last_active_at integer, api_key text);
        create table model(id text, user_id text, base_model_id text, meta text);
        create table chat(id text, user_id text, title text, chat JSON, meta JSON,
                          archived integer, created_at integer, share_id text);
        create table channel(id text, user_id text, name text, type text);
        create table config(id integer, data JSON);""")
    for i, role in ((1, "admin"), (2, "user"), (3, c + "role"), (4, c + "role")):
        ui = {"theme": "dark", f"{c}_once": True} if i == 1 else {"theme": "light"}
        con.execute("insert into user values (?,?,?,?,?,?,?)",
                    (f"u{i}", f"{c} name", f"{c}@example.invalid", role,
                     json.dumps({"ui": ui}), now - i * 86400, f"sk-{c}"))
    con.execute("insert into model values ('m-agent','u1','gpt-x',?)", (json.dumps({c: 1}),))
    for i, user in enumerate(("u1", "u1", "u2")):
        message = {"role": "user", "content": f"{c} text", "files": [], "shared_mkey": 1}
        chat = {"title": f"{c} title", "shared_key": 1, "models": [f"{c}-model", "m-agent"],
                "history": {"messages": {f"{c}-id": message}}}
        if user == "u1":  # one user's own keys, however often, never print
            chat[f"{c}_key"] = 1
            message[f"{c}_mkey"] = 1
        con.execute("insert into chat values (?,?,?,?,?,?,?,?)",
                    (f"c{i}", user, f"{c} title", json.dumps(chat), json.dumps({"tags": [c]}),
                     0, now, f"{c}-share"))
    for user, kind in (("u1", "space"), ("u2", "space"), ("u1", c + "type"), ("u1", c + "type")):
        con.execute("insert into channel values (?,?,?,?)", (f"ch-{user}", user, f"{c} room", kind))
    config = {"openai": {"enable": True, "api_keys": [f"sk-{c}"],
                         "api_base_urls": [f"https://{c}.invalid"]},
              "ui": {"default_locale": c}, f"{c}@mail": {"x": 1}, "map": {"0": {c: c}}}
    con.execute("insert into config values (1, ?)", (json.dumps(config),))
    con.commit()
    con.close()


def self_test():
    """Fail if any planted canary reaches the report, or the counts drift."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "t.db")
        plant(path)
        report = census(path)
    text = json.dumps(report).lower()
    at = text.find(CANARY)
    assert at < 0, f"canary leaked: ...{text[max(0, at - 80):at + 40]}..."
    tables = report["tables"]
    assert tables["user"]["enums"]["role"] == {"admin": 1, "user": 1, "<other>": 2}, tables["user"]["enums"]
    assert tables["channel"]["enums"]["type"] == {"space": 2, "<other>": 2}, tables["channel"]["enums"]
    assert report["config"]["openai"] == {"enable": True, "api_keys": "list[1]", "api_base_urls": "list[1]"}
    assert report["config"]["<other>"] == 1 and report["config"]["map"] == "dict[1]", report["config"]
    assert report["chat"]["model_kind"] == {"base_or_external": 3, "agent": 3}, report["chat"]
    assert report["chat"]["message.*"]["role"] == 3 and report["chat"]["message.*"]["files"] == 3
    assert report["chat"]["chat.*"]["shared_key"] == 3 and report["chat"]["chat.*"]["<other>"] == 2
    assert report["chat"]["message.*"]["shared_mkey"] == 3 and report["chat"]["message.*"]["<other>"] == 2
    assert tables["user"]["json"]["settings"]["ui.*"]["theme"] == 4, tables["user"]["json"]
    assert tables["user"]["present"]["api_key"] == 4
    print("self-test: ok (no canary in", len(text), "bytes of report)")


def main(argv):
    if argv[1:] == ["--self-test"]:
        self_test()
        return 0
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    reports = {}
    for path in argv[1:]:
        label = os.path.join(os.path.basename(os.path.dirname(os.path.abspath(path))),
                             os.path.basename(path))
        reports[label] = census(path)
    json.dump(reports, sys.stdout, indent=1, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
