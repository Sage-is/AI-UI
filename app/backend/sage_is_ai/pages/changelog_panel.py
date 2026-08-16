"""The changelog panel. First wizard surface, and the first with no legacy URL.

Every surface before this one replaced a page. This one replaces a branch of a
modal that `(app)/+layout.svelte` mounts and a store decides to show, so there
was no address to point a spec at. The registry grew an open step for that
(`cypress/support/surfaces.ts`), which is what lets the parity gate compare a
panel you cannot visit.

Three things differ from the Svelte panel, all deliberate.

The changelog comes from a module constant. `env.CHANGELOG` is parsed from
CHANGELOG.md once at import. The Svelte panel boots, calls `/api/changelog`,
then renders: three steps to show something that has not changed since the
process started. Reading the constant follows the same rule as the other panels
(call the handler, never round-trip your own API).

Continue pages the notes before it advances. The release notes run to tens of
thousands of words, and a Continue that advances on the first click means most
readers never see past the first screen. `changelog-pager.js` scrolls one screen
per click while there is more below, then moves the button to the other side of
the row and lets it submit.

Continue is a form post. In the modal it closes the modal and, when the
changelog is the only panel, records the version as read. At a route there is
nothing to close, so what survives is the durable half: the server records the
read.

No confetti. The Svelte panel fires `svelte-confetti` on the title and this does
not, because a component whose whole job is an animation is not worth a script
tag on a server-rendered page.
"""

from __future__ import annotations

from fastapi import Request

from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

__all__ = ["render_changelog", "mark_changelog_read"]

def _runs(raw: str, flat: str) -> list[dict]:
    """One entry's content as inline runs, so `<code>` survives.

    The parser in `env.py` flattens each entry with
    `get_text(separator=" ", strip=True)`, which throws the `<code>` tags away
    AND inserts a space where each one was — so a release note reading
    "Each recipe (`scripts/build-sprig-*.sh`) runs its gate" arrived as
    "Each recipe ( scripts/build-sprig-*.sh ) runs its gate": no monospace, and
    stray spaces inside the brackets. Reported by Alexander on the live wizard.

    Fixed HERE rather than in the parser because `env.py` also feeds
    `/api/changelog`, and because the entry it produces already carries `raw` —
    the untouched `<li>`/`<p>` HTML — so nothing needed to change at the source.

    Returns runs, not HTML, so the template stays autoescaped and there is no
    `| safe` anywhere in this path. Only `<code>` is preserved; other inline
    markup still flattens to text, the same as it did before.
    """
    from bs4 import BeautifulSoup

    roots = BeautifulSoup(raw or "", "html.parser").find_all(["li", "p"], recursive=False)
    if not roots:
        return [{"text": flat, "code": False}] if flat else []

    runs: list[dict] = []
    title_dropped = False
    for i, root in enumerate(roots):
        # A multi-paragraph entry arrives as a run of <p>s. The parser joins
        # its paragraphs with a single space in `content`; a single space run
        # here keeps the rendered text equal to `content`, so the panel and
        # `/api/changelog` cannot disagree about what an entry says.
        if i:
            runs.append({"text": " ", "code": False})
        for node in root.children:
            name = getattr(node, "name", None)
            # The prose format puts the entry's title in the FIRST <strong> of
            # the first <p>; the parser drops exactly that one from `content`
            # and so must this. A later <strong> is emphasis inside the body —
            # skipping those ate the bold "2.4" out of two v2.3.1 entries.
            if name == "strong" and i == 0 and root.name == "p" and not title_dropped:
                title_dropped = True
                continue
            if name == "code":
                runs.append({"text": node.get_text(), "code": True})
            else:
                runs.append(
                    {
                        "text": node.get_text() if hasattr(node, "get_text") else str(node),
                        "code": False,
                    }
                )

    # The list format is "Title: content", split on the FIRST ": " — mirroring
    # `parse_section` exactly, so the two cannot disagree about where the title
    # ends. A list entry is always a single <li>.
    if roots[0].name == "li":
        for i, run in enumerate(runs):
            if not run["code"] and ": " in run["text"]:
                tail = run["text"].split(": ", 1)[1]
                runs = ([{"text": tail, "code": False}] if tail else []) + runs[i + 1 :]
                break

    if runs:
        runs[0]["text"] = runs[0]["text"].lstrip()
        runs[-1]["text"] = runs[-1]["text"].rstrip()
    return [r for r in runs if r["text"]]


def render_changelog(request: Request, *, base: str = "/pages/admin/setup/changelog") -> str:
    """Build the context; `templates/changelog.html` decides how it looks.

    `base` is where Continue posts. Two routes render this panel: the wizard's
    admin-only one, and `/pages/changelog`, which any signed-in reader reaches
    from Settings, About, "See what's new". The markup is identical and only the
    action differs, so the action is the parameter — a second copy of the panel
    would drift on the first change to either.

    `<dl>` in the template rather than nested divs, because a changelog entry IS
    a term and what it means: a short title and the sentence explaining it.
    """
    from sage_is_ai.env import CHANGELOG, VERSION

    _ = translator(request)
    return render(
        "changelog.html",
        base=base,
        lang=lang_query(request),
        version=VERSION,
        release_notes=_("Release Notes"),
        more_label=_("Next page"),
        end_label=_("Continue"),
        empty=_("No release notes are available."),
        versions=[
            {
                "version": str(version),
                "date": str(data.get("date", "")),
                "sections": [
                    {
                        "name": str(name),
                        "rows": [
                            {
                                "title": str(row.get("title", "")),
                                "runs": _runs(
                                    str(row.get("raw", "")), str(row.get("content", ""))
                                ),
                            }
                            for row in items
                            if isinstance(row, dict)
                        ]
                        if isinstance(items, (list, tuple))
                        else [],
                    }
                    for name, items in data.items()
                    if name != "date"
                ],
            }
            for version, data in CHANGELOG.items()
            if isinstance(data, dict)
        ],
    )


async def mark_changelog_read(request: Request, user) -> None:
    """Record that this version's changelog has been read.

    Calls the API handler rather than writing the row, so the one place that
    knows what a settings update is allowed to do stays the one place. The read
    is a merge, not a replace: the handler takes the whole `ui` blob and stores
    it, so dropping the rest of the reader's preferences on the floor is exactly
    what a naive write here would do.
    """
    from sage_is_ai.env import VERSION
    from sage_is_ai.models.users import Users, UserSettings
    from sage_is_ai.routers.users import update_user_settings_by_session_user

    current = Users.get_user_by_id(user.id)
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    ui = dict((settings or {}).get("ui") or {})
    ui["version"] = VERSION

    await update_user_settings_by_session_user(
        request, UserSettings(**{**settings, "ui": ui}), user
    )
