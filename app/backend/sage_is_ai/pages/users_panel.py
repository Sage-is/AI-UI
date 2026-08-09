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

from fastapi import Request

from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

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
    """Build the context; `templates/users.html` decides how it looks."""
    _ = translator(request)
    return render(
        "users.html",
        lang=lang_query(request),
        people=[{"name": n, "email": em, "role": r} for n, em, r in _people(request)],
        alone=_working_alone(user),
        roles=list(ROLES),
        csv_columns=", ".join(CSV_COLUMNS),
        message=message,
        alone_label=_("I am working alone"),
        alone_hint=_("Skip user setup. You can add people later from Admin settings."),
        add_legend=_("Add a team member"),
        name_label=_("Name"),
        email_label=_("Email"),
        password_label=_("Password"),
        role_label=_("Role"),
        add_label=_("Add"),
        import_label=_("Import a CSV"),
        import_button=_("Import"),
        template_label=_("Download template"),
        people_label=_("People"),
    )

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
