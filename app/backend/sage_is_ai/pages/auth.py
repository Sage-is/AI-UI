"""Cookie authentication for server-rendered pages and fragments.

The plan calls this the cookie bridge and treats it as a prerequisite for the
fragment phases: "Server-rendered pages can't read localStorage, where the
login token lives (478 references). The backend already sets cookies in 8
places; extending that to render routes is a prerequisite."

Measured, the extension is nearly free. `utils/auth.get_current_user` already
falls back to the `token` cookie when no Authorization header is present, and
every sign-in path already sets that cookie httponly. A render route can use
that identity today.

So this module does NOT check tokens. It calls the one function that does.

That is deliberate and it is the whole point of the migration. The first draft
of this file decoded the JWT and looked the user up itself, and within twenty
lines it had already drifted from the original two ways: it added a session
check the API path does not make, and it missed the try.sage session-reset
cutoff the API path does — so a facilitator pressing "Reset now" would have
invalidated every API session while leaving these pages signed in. The audit
behind the plan counted authorization restated ~142 times in the frontend. A
second copy in the BACKEND would be the same disease with a shorter incubation.

Pages need a different failure, not a different identity: a person who follows
a link while signed out should land on the sign-in screen, not on a JSON error
body. That difference is what lives here.
"""

from fastapi import BackgroundTasks, HTTPException, Request, Response, status

from sage_is_ai.models.users import UserModel
from sage_is_ai.utils.auth import get_current_user

__all__ = ["require_admin_page", "require_agents_reader", "require_page_user"]


def _signed_in(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
) -> UserModel:
    """Identity for a render route, or a redirect to sign in.

    `auth_token=None` is passed on purpose: this is the render path, so identity
    comes from the cookie. A render route reached with a bearer header is a
    caller mistaking a page for an API, and quietly honouring it would give the
    two surfaces different rules about what counts as signed in.

    307 rather than 302 keeps the method, and `next` carries the person back to
    what they asked for. The value is a path and never an absolute URL, because
    a redirect target taken from a request is an open redirect waiting to
    happen — the sign-in page must not be able to bounce someone to another
    origin.
    """
    try:
        return get_current_user(request, response, background_tasks, auth_token=None)
    except HTTPException:
        target = request.url.path
        if request.url.query:
            target = f"{target}?{request.url.query}"
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": f"/auth?next={target}"},
            detail="Not authenticated",
        ) from None


def require_page_user(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
) -> UserModel:
    """Any signed-in reader. The narrow exception to admin-only pages.

    Used by exactly one route, `/pages/changelog`. The release notes are not
    admin material — every reader can open Settings, About, "See what's new" —
    and until the wizard moved here that path was a Svelte component with no
    role check at all. Serving it from the admin tree would have made a
    non-admin's first click a 403.

    Keep this rare, and keep it out of `/admin/`. A route under that prefix that
    does not require an admin is a trap for whoever audits by path next.
    """
    return _signed_in(request, response, background_tasks)


def require_agents_reader(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
) -> UserModel:
    """Signed in AND permitted to use the workshop.

    A DEPENDENCY rather than a call at the top of each route body, and that is
    the whole point. It was five manual `_require_agents_reader(request, user)`
    lines, one per route — five chances for the sixth route to omit it, with
    nothing to catch the omission: not a type, not a test, not a lint. In the
    signature it cannot be forgotten without also forgetting the user.

    Reads `request.app.state.config.USER_PERMISSIONS`, NOT
    `DEFAULT_USER_PERMISSIONS` — the same table `create_new_model` consults. The
    defaults are what ships; this is what the operator saved, and reading the
    wrong one would let these pages ignore a policy the JSON API enforces.
    """
    user = _signed_in(request, response, background_tasks)
    if user.role == "admin":
        return user

    from sage_is_ai.utils.access_control import has_permission

    if not has_permission(
        user.id, "workshop.models", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workshop access required",
        )
    return user


def require_admin_page(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
) -> UserModel:
    """Admin-only render route. Sends a person to sign in, not to a 403 body."""
    user = _signed_in(request, response, background_tasks)

    if user.role != "admin":
        # A signed-in non-admin is not a sign-in problem, so it is not a
        # redirect — bouncing them to /auth would loop them straight back here.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return user
