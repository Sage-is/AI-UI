"""Add users, or declare that you are working alone.

Four things: work alone, add one person, import a CSV, see who is already here.

The CSV is parsed on the server. The Svelte panel reads the file with
`FileReader`, splits it in the browser, and issues one POST per row, so a
fifty-row import is fifty round trips and a partial failure leaves the operator
guessing which rows landed. Here the file is uploaded once, parsed once, and
every row is reported back with its line number.

One role list, `ROLES`, feeds the picker and the importer. They disagreed
before: the picker offered `facilitator` and the importer validated against
`['admin', 'user', 'pending']`, so a role you could choose by hand was refused
from a file. `facilitator` is a real role that `auths.add_user` handles, which
made the importer's list the wrong one. Fixed on both implementations, because
one guard-rail spec judges both.

Passwords are never rendered back, for the same reason the connection panel
never renders an API key. The list below the form shows name, email and role.
"""

from __future__ import annotations

import csv
import io
from html import escape as e

from fastapi import Request

__all__ = [
    "render_users",
    "add_one_user",
    "import_csv",
    "set_working_alone",
    "ROLES",
    "CSV_ROLES",
]

# The roles this wizard offers. `auths.add_user` knows others (`pending`,
# `temporary`); those are lifecycle states rather than something an admin picks
# while setting an instance up.
ROLES: tuple[str, ...] = ("user", "facilitator", "admin")

# What a CSV may carry. The picker's three, plus `pending`, which the old
# importer already accepted. Adding `facilitator` is the fix; removing `pending`
# would break files that import correctly today, so it stays.
CSV_ROLES: tuple[str, ...] = ROLES + ("pending",)

# CSV column order, which is also what static/user-import.csv ships.
CSV_COLUMNS = ("name", "email", "password", "role")

_ROW_S = ("--d:flex; --jc:space-between; --ai:center; --p:.3rem .5rem; "
          "--br:.35rem; --b:1px solid var(--line); --m:0 0 .25rem; --size:.75rem")
_LABEL_S = "--size:.7rem; --weight:500; --d:block; --m:.4rem 0 .15rem"
_INPUT_S = ("--w:100%; --bxs:border-box; --p:.4rem .6rem; --size:.78rem; "
            "--br:.4rem; --b:1px solid var(--line); --bgc:transparent; --c:inherit")
_BUTTON_S = ("--p:.4rem .9rem; --size:.78rem; --br:.4rem; "
             "--b:1px solid var(--line); --cur:pointer")


def _people(request: Request) -> list[tuple[str, str, str]]:
    """Everyone who is not an admin, which is who this step is about."""
    from sage_is_ai.models.users import Users

    users = Users.get_users()
    rows = users["users"] if isinstance(users, dict) else users
    return [
        (str(u.name), str(u.email), str(u.role))
        for u in rows
        if getattr(u, "role", "") != "admin"
    ]


def _working_alone(user) -> bool:
    from sage_is_ai.models.users import Users

    current = Users.get_user_by_id(user.id) if user else None
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    return bool((settings.get("ui") or {}).get("workingAlone", False))


def render_users(request: Request, user, message: str = "") -> str:
    people = _people(request)
    alone = _working_alone(user)
    options = "".join(
        f'<option value="{e(r, quote=True)}">{e(r)}</option>' for r in ROLES
    )
    listing = "".join(
        f'<li data-cy="users-row" style="{_ROW_S}">'
        f"<span>{e(name)} <span style=\"--op:.65\">{e(email)}</span></span>"
        f'<span data-role="{e(role, quote=True)}" style="--op:.65">{e(role)}</span></li>'
        for name, email, role in people
    )
    note = (
        f'<output data-cy="users-result" style="--size:.8rem; --op:.8">{e(message)}</output>'
        if message
        else ""
    )
    return f"""
<section data-cy="users-panel" data-user-count="{len(people)}"
         data-working-alone="{str(alone).lower()}">
  <form method="post" action="/pages/admin/setup/users/alone" style="--m:0 0 1rem">
    <button data-cy="users-working-alone" type="submit" style="{_BUTTON_S}">
      I&rsquo;m working alone
    </button>
    <small style="--size:.7rem; --op:.7; --d:block; --m:.25rem 0 0">
      Skip user setup. You can add people later from Admin settings.
    </small>
  </form>

  <form method="post" action="/pages/admin/setup/users/add">
    <fieldset style="--b:0; --p:0; --m:0">
      <legend style="--size:.85rem; --weight:600; --p:0">Add a team member</legend>
      <label style="{_LABEL_S}">Name</label>
      <input data-cy="users-name" type="text" name="name" style="{_INPUT_S}" />
      <label style="{_LABEL_S}">Email</label>
      <input data-cy="users-email" type="email" name="email" style="{_INPUT_S}" />
      <label style="{_LABEL_S}">Password</label>
      <input data-cy="users-password" type="password" name="password"
             autocomplete="new-password" style="{_INPUT_S}" />
      <label style="{_LABEL_S}">Role</label>
      <select data-cy="users-role" name="role" style="{_INPUT_S}">{options}</select>
    </fieldset>
    <button data-cy="users-add" type="submit" style="{_BUTTON_S}; --m:.6rem 0 0">Add</button>
  </form>

  <!-- A real file input posting multipart. The Svelte panel hides its input
       behind a styled button and drives it with getElementById; the browser
       already renders a file picker, so this uses the one it has. -->
  <form method="post" action="/pages/admin/setup/users/import"
        enctype="multipart/form-data" style="--m:1rem 0 0">
    <label style="{_LABEL_S}">Import a CSV: {", ".join(CSV_COLUMNS)}</label>
    <input data-cy="users-csv" type="file" name="csv" accept=".csv,text/csv"
           style="--size:.75rem" />
    <button data-cy="users-import" type="submit" style="{_BUTTON_S}; --m:.5rem 0 0">
      Import
    </button>
    <a href="/static/user-import.csv" style="--size:.7rem; --ml:.5rem">Download template</a>
  </form>

  <h2 style="--size:.8rem; --weight:600; --m:1.25rem 0 .4rem">
    People ({len(people)})
  </h2>
  <ul data-cy="users-list" style="--p:0; --list-style:none; --maxh:10rem; --ofy:auto">{listing}</ul>
  {note}
</section>
"""


async def _create(request: Request, user, name: str, email: str, password: str,
                  role: str) -> str:
    """Add one user through the API handler. Returns "" on success, else why not."""
    from fastapi import HTTPException

    from sage_is_ai.models.auths import AddUserForm
    from sage_is_ai.routers.auths import add_user

    if role not in CSV_ROLES:
        return f"role must be one of {', '.join(CSV_ROLES)}"
    try:
        await add_user(
            AddUserForm(name=name, email=email, password=password, role=role), user
        )
    except HTTPException as exc:
        return str(exc.detail)
    except Exception as exc:  # noqa: BLE001 — the reason is the message
        return str(exc)
    return ""


async def add_one_user(request: Request, user, form: dict) -> str:
    name = str(form.get("name", "")).strip()
    email = str(form.get("email", "")).strip()
    password = str(form.get("password", ""))
    role = str(form.get("role", "user")).strip().lower()

    if not (name and email and password):
        return render_users(request, user, "Name, email and password are all required.")

    problem = await _create(request, user, name, email, password, role)
    if problem:
        return render_users(request, user, f"Could not add {email}: {problem}")
    return render_users(request, user, f"Added {email}.")


async def import_csv(request: Request, user, raw: bytes) -> str:
    """Parse the whole file, add every valid row, and report each failure by line.

    `csv.DictReader` rather than `split(',')`, which is what the Svelte panel
    does. A quoted field containing a comma is legal CSV and splitting on commas
    silently mangles it, so a name like "Doe, Jane" would import as garbage
    without anything reporting a problem.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return render_users(request, user, "That file is not UTF-8 text.")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return render_users(request, user, "That file has no header row.")

    # Match the header case-insensitively; a template downloaded and re-saved by
    # a spreadsheet often comes back title-cased.
    lookup = {str(f).strip().lower(): f for f in reader.fieldnames}
    missing = [c for c in CSV_COLUMNS if c not in lookup]
    if missing:
        return render_users(
            request, user, f"Missing column(s): {', '.join(missing)}."
        )

    added, problems = 0, []
    for line, row in enumerate(reader, start=2):  # line 1 is the header
        values = {c: str(row.get(lookup[c]) or "").strip() for c in CSV_COLUMNS}
        if not any(values.values()):
            continue  # a blank line is not an error
        if not (values["name"] and values["email"] and values["password"]):
            problems.append(f"line {line}: name, email and password are all required")
            continue
        problem = await _create(
            request, user, values["name"], values["email"],
            values["password"], values["role"].lower() or "user",
        )
        if problem:
            problems.append(f"line {line}: {problem}")
        else:
            added += 1

    report = f"Imported {added} user{'' if added == 1 else 's'}."
    if problems:
        report += " " + "; ".join(problems)
    return render_users(request, user, report)


async def set_working_alone(request: Request, user) -> None:
    """Record that this admin is the only account they intend to have."""
    from sage_is_ai.models.users import Users, UserSettings
    from sage_is_ai.routers.users import update_user_settings_by_session_user

    current = Users.get_user_by_id(user.id)
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    ui = dict((settings or {}).get("ui") or {})
    ui["workingAlone"] = True

    await update_user_settings_by_session_user(
        request, UserSettings(**{**settings, "ui": ui}), user
    )
