"""try.sage trial-mode seed and reset helpers.

This module owns the *idempotent* parts of try-mode setup: persona accounts,
default agents, knowledge-base ingestion, and persona magic-link minting.
It does **not** own scheduling — `lifespan()` and `periodic_try_sage_reset()`
in main.py call into us; we just do the work and return.

Why each piece lives here together:

- Persona accounts, agents, and KBs are deeply coupled (an agent binds to
  a KB owned by a specific persona). Splitting them across files would mean
  a single seed run touching three modules in lockstep — easier to break,
  harder to reason about. One file, one entry point, one reset entry point.

- Magic-link minting is also here (not in routers/auths.py) because the
  seed cache (`app.state.try_sage_persona_links`) is a seed-owned concern.
  The router-side helper would have to call back into seed to populate the
  cache anyway. The JWT signing path is shared by reusing
  `utils.auth.create_token` directly — same secret, same algorithm, same
  claim shape as the System 2 send endpoint at `routers/auths.py:1150-1234`.

Idempotency strategy: every operation is "find-or-create / refresh from
source". Personas are looked up by email; agents by id (slug); KB files
by content hash of the source folder. Re-running this module is always
safe, which is exactly what the auto-reset task and lifespan startup both
need.
"""

import hashlib
import json
import logging
import os
import re
import secrets
import uuid
from datetime import timedelta
from typing import Any, Optional

log = logging.getLogger(__name__)

# Where the agent definition + KB source files live. Resolved relative to
# this module so the layout survives both editable installs and the docker
# image. Sibling of `utils/` → `data/try_sage_agents/`.
_AGENTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "try_sage_agents")
)


# ---------------------------------------------------------------------------
# Persona definitions
# ---------------------------------------------------------------------------


def get_persona_definitions(app) -> list[dict]:
    """Canonical persona list for this app instance.

    Driven by `TRY_SAGE_USER_SEAT_COUNT` (capped at 5 by config). Always
    yields admin + facilitator first, then N user personas. Caller treats
    this list as the source of truth — order matters because the admin and
    facilitator slots are assumed positional by the frontend persona
    switcher (B3).
    """
    seat_count = max(1, min(5, int(app.state.config.TRY_SAGE_USER_SEAT_COUNT)))

    personas: list[dict] = [
        {
            "key": "admin",
            "email": "try-admin@try.sage.is",
            "role": "admin",
            "label": "Sage Admin",
            "group": None,
        },
        {
            "key": "facilitator",
            "email": "try-facilitator@try.sage.is",
            "role": "user",
            "label": "Workshop Facilitator",
            # The "facilitator" group is a label only — actual group
            # membership is admin-managed via Groups model elsewhere.
            "group": "facilitator",
        },
    ]
    for i in range(1, seat_count + 1):
        personas.append(
            {
                "key": f"user-{i}",
                "email": f"try-user-{i}@try.sage.is",
                "role": "user",
                "label": f"Trial User {i}",
                "group": None,
            }
        )
    return personas


# ---------------------------------------------------------------------------
# Agent definition file parsing
# ---------------------------------------------------------------------------


# Slugs of the three default try-mode agents and which ones ship with a KB.
# Keep this in lock-step with the .md files committed under data/try_sage_agents/.
_DEFAULT_AGENT_SLUGS: list[str] = [
    "sage-strawberry",
    "sage-startr-style",
    "astropi-ai-tutor",
]
_AGENTS_WITH_KB: set[str] = {"sage-startr-style", "astropi-ai-tutor"}


def _parse_agent_md(path: str) -> Optional[dict]:
    """Parse one agent definition file.

    Frontmatter format (kept tiny on purpose — full YAML would pull in a
    new dep):

        ---json
        {"slug": "...", "name": "...", "description": "...", "base_model": "..."}
        ---
        <system prompt body…>

    Returns a dict with `slug`, `name`, `description`, `base_model`, and
    `system_prompt`, or None if the file is malformed. We parse via
    `re.split` instead of a YAML lib so this stays a stdlib-only module.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as e:
        log.warning(f"try_sage_seed: failed to read agent file {path}: {e}")
        return None

    match = re.match(
        r"^---json\s*\n(\{.*?\})\s*\n---\s*\n(.*)$",
        raw,
        re.DOTALL,
    )
    if not match:
        log.warning(f"try_sage_seed: no JSON frontmatter in {path}")
        return None

    try:
        meta = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        log.warning(f"try_sage_seed: invalid JSON frontmatter in {path}: {e}")
        return None

    body = match.group(2).strip()
    return {
        "slug": meta.get("slug"),
        "name": meta.get("name"),
        "description": meta.get("description", ""),
        "base_model": meta.get("base_model", ""),
        "system_prompt": body,
    }


def _kb_folder_hash(slug: str) -> Optional[str]:
    """Stable hash of an agent's `kb/` directory contents.

    Used as the version key in `TRY_SAGE_KB_INGESTED_VERSION`. We hash
    file *contents*, not mtime, so editing a doc invalidates the cache
    but a fresh git checkout (which resets mtimes) does not.

    Returns None when the kb folder doesn't exist — that's a signal to
    skip ingestion entirely rather than re-ingesting an empty set.
    """
    kb_dir = os.path.join(_AGENTS_DIR, slug, "kb")
    if not os.path.isdir(kb_dir):
        return None

    h = hashlib.sha256()
    # Sort for deterministic ordering across filesystems.
    for filename in sorted(os.listdir(kb_dir)):
        if not filename.endswith(".md"):
            continue
        full = os.path.join(kb_dir, filename)
        try:
            with open(full, "rb") as fh:
                h.update(filename.encode("utf-8"))
                h.update(b"\0")
                h.update(fh.read())
                h.update(b"\0")
        except OSError as e:
            log.warning(f"try_sage_seed: failed reading {full}: {e}")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Persona ensure (find-or-create)
# ---------------------------------------------------------------------------


def _ensure_persona_account(persona: dict) -> Optional[Any]:
    """Find-or-create the User+Auth row for a single persona.

    Returns the `UserModel` (or None on failure). Idempotent: if the user
    already exists the role is refreshed but the password is left alone
    (rotating it would invalidate any password-based sessions in flight).

    Why not `Auths.insert_new_auth` for new accounts? That path always
    generates a uuid for the user id, which is fine here. We import it
    inside the function so the seed module stays free of DB-touching
    imports at module load time.
    """
    from sage_is_ai.env import (
        TRY_SAGE_ADMIN_PASSWORD,
        TRY_SAGE_FACILITATOR_PASSWORD,
        TRY_SAGE_USER_PASSWORD,
    )
    from sage_is_ai.models.auths import Auths
    from sage_is_ai.models.users import Users
    from sage_is_ai.utils.auth import get_password_hash

    existing = Users.get_user_by_email(persona["email"])
    if existing:
        # Drift correction: persona role might have been changed via the
        # admin UI (e.g. someone demoting try-admin to user by mistake).
        # Force back to canonical.
        if existing.role != persona["role"]:
            Users.update_user_role_by_id(existing.id, persona["role"])
        return existing

    # Pick the right env-supplied password for this persona key. If none
    # is set, generate a strong random one and log it ONCE — facilitators
    # can grab it from the boot log if magic links somehow break.
    password_overrides = {
        "admin": TRY_SAGE_ADMIN_PASSWORD,
        "facilitator": TRY_SAGE_FACILITATOR_PASSWORD,
    }
    if persona["key"].startswith("user-"):
        password = TRY_SAGE_USER_PASSWORD
    else:
        password = password_overrides.get(persona["key"], "")

    generated = False
    if not password:
        password = secrets.token_urlsafe(24)
        generated = True

    user = Auths.insert_new_auth(
        email=persona["email"],
        password=get_password_hash(password),
        name=persona["label"],
        role=persona["role"],
    )

    if user and generated:
        # One-time disclosure. Subsequent boots find the existing row and
        # never re-log the password. Persona is normally reached via magic
        # link anyway; this is a fallback for an SMTP-down workshop.
        log.warning(
            f"try_sage_seed: generated persona password for {persona['email']}: {password}"
        )

    return user


# ---------------------------------------------------------------------------
# Agent + KB ensure
# ---------------------------------------------------------------------------


def _ensure_agent(persona_user_id: str, agent_def: dict) -> None:
    """Find-or-update one agent (a Model row) by slug.

    Agents in this codebase ARE model rows with `base_model_id` set —
    same shape the admin Models UI creates. We reuse `Models.insert_new_model`
    on first boot and `Models.update_model_by_id` on subsequent boots to
    refresh the system prompt from source.
    """
    from sage_is_ai.models.models import (
        ModelForm,
        ModelMeta,
        ModelParams,
        Models,
    )

    slug = agent_def["slug"]
    if not slug:
        log.warning("try_sage_seed: agent definition missing slug; skipping")
        return

    # Bind the agent's params to its system prompt — that's what propagates
    # into the chat completion request. We dump as plain dict because
    # ModelParams allows extra keys.
    params = ModelParams(system=agent_def["system_prompt"])
    meta = ModelMeta(description=agent_def["description"])

    form = ModelForm(
        id=slug,
        base_model_id=agent_def["base_model"] or None,
        name=agent_def["name"] or slug,
        params=params,
        meta=meta,
        access_control=None,  # public to all "user" role accounts
        is_active=True,
    )

    existing = Models.get_model_by_id(slug)
    if existing:
        Models.update_model_by_id(slug, form)
    else:
        Models.insert_new_model(form, persona_user_id)


def _ensure_kb(app, persona_user_id: str, slug: str) -> Optional[str]:
    """Ensure a knowledge collection exists for `slug` and ingest its docs
    when the source folder hash differs from the persisted version.

    Returns the KB id (or None if there's no kb folder for this agent).

    Why hash-gated: KB ingestion is the slowest step in the seed path —
    every reset re-running it would push our cycle from seconds to minutes
    on a big embedding model. Hashing the kb folder lets us skip the work
    when nothing changed, while still re-ingesting cleanly when an editor
    updates a doc.

    Why we DO NOT call `VECTOR_DB_CLIENT.reset()` anywhere in this flow:
    that would wipe ALL vector collections, including chat-scoped ones
    owned by other users in non-try deployments, and force a full
    re-embed of every persona KB on every reset — exactly the "fast
    reset" property we're trying to preserve.
    """
    from sage_is_ai.config import TRY_SAGE_KB_INGESTED_VERSION
    from sage_is_ai.models.files import FileForm, Files
    from sage_is_ai.models.knowledge import (
        KnowledgeForm,
        Knowledges,
    )

    kb_dir = os.path.join(_AGENTS_DIR, slug, "kb")
    if not os.path.isdir(kb_dir):
        return None

    folder_hash = _kb_folder_hash(slug)
    if not folder_hash:
        return None

    # Read the persisted version map. Stored as a JSON string (config
    # values are scalar-ish and a dict-shaped persistent flag would
    # require schema changes); a tiny json.loads keeps it simple.
    try:
        version_map = json.loads(TRY_SAGE_KB_INGESTED_VERSION.value or "{}")
        if not isinstance(version_map, dict):
            version_map = {}
    except (json.JSONDecodeError, TypeError):
        version_map = {}

    kb_collection_name = f"try_sage_kb_{slug}"

    # Find-or-create the Knowledge row. We look it up by name+owner because
    # there's no uniqueness constraint on Knowledge.id beyond the uuid;
    # using name as the lookup key keeps the seed re-entrant.
    knowledge = None
    for kb in Knowledges.get_knowledge_bases():
        if kb.name == kb_collection_name and kb.user_id == persona_user_id:
            knowledge = kb
            break
    if not knowledge:
        knowledge = Knowledges.insert_new_knowledge(
            persona_user_id,
            KnowledgeForm(
                name=kb_collection_name,
                description=f"try.sage built-in KB for agent {slug}",
                data={"file_ids": []},
                access_control=None,
            ),
        )
        if not knowledge:
            log.error(f"try_sage_seed: failed to create KB for {slug}")
            return None

    # Skip ingestion if the source hasn't changed. We still return the kb
    # id so the caller can bind it to the agent.
    if version_map.get(slug) == folder_hash:
        return knowledge.id

    # Hash differs — re-ingest. We deliberately do NOT delete the existing
    # collection here; `process_file` writes per-file embeddings and the
    # new file_ids will replace the previous content keyed by collection
    # name. Old file rows are orphaned (cheap; they're metadata only).
    log.info(f"try_sage_seed: ingesting KB for {slug} (hash {folder_hash[:8]}…)")

    new_file_ids: list[str] = []
    for filename in sorted(os.listdir(kb_dir)):
        if not filename.endswith(".md"):
            continue
        full_path = os.path.join(kb_dir, filename)
        try:
            with open(full_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError as e:
            log.warning(f"try_sage_seed: skipping unreadable KB doc {full_path}: {e}")
            continue

        # Insert a File row. We don't go through Storage.upload_file
        # because the source-of-truth is the on-disk md (a re-read on
        # next boot will find the same hash and skip); a Storage write
        # would add a useless filesystem copy.
        file_id = str(uuid.uuid4())
        file_form = FileForm(
            id=file_id,
            filename=filename,
            path=full_path,
            data={"content": content},
            meta={
                "name": filename,
                "content_type": "text/markdown",
                "size": len(content.encode("utf-8")),
            },
        )
        file_row = Files.insert_new_file(persona_user_id, file_form)
        if not file_row:
            continue

        # Push into the vector store under the KB's collection id. The
        # knowledge router uses the same `process_file(content=...)`
        # shape — see `routers/retrieval.py:1295`.
        try:
            _ingest_file_into_collection(
                app=app,
                file_id=file_id,
                collection_name=knowledge.id,
                filename=filename,
                content=content,
            )
        except Exception as e:
            log.exception(f"try_sage_seed: ingest failure for {full_path}: {e}")
            continue
        new_file_ids.append(file_id)

    # Stamp the new file ids into the KB row and persist the version.
    Knowledges.update_knowledge_data_by_id(
        knowledge.id, {"file_ids": new_file_ids}
    )

    version_map[slug] = folder_hash
    TRY_SAGE_KB_INGESTED_VERSION.value = json.dumps(version_map)
    TRY_SAGE_KB_INGESTED_VERSION.save()

    return knowledge.id


class _AppRequestShim:
    """Minimal stand-in for `fastapi.Request` carrying just `app`.

    `save_docs_to_vector_db` (routers/retrieval.py:1072) reads chunker
    settings, embedding model config, and BYPASS flags off
    `request.app.state.config`. Constructing a real Request would need
    a Scope dict and a receive callable for no benefit; this shim hands
    back the live app reference and nothing else.
    """

    __slots__ = ("app",)

    def __init__(self, app):
        self.app = app


def _ingest_file_into_collection(
    app, file_id: str, collection_name: str, filename: str, content: str
) -> None:
    """Direct vector-store write for a single markdown file.

    Reuses `save_docs_to_vector_db` (the same helper the knowledge router
    calls) so chunking/embedding settings stay consistent with the rest of
    the app. Why a shim instead of the real `process_file`: process_file
    insists on a FastAPI Request + user dependency; we have neither at
    seed time, but the only thing it actually needs from the request is
    `request.app.state.config` — exactly what _AppRequestShim provides.
    """
    from langchain_core.documents import Document

    from sage_is_ai.routers.retrieval import save_docs_to_vector_db

    docs = [
        Document(
            page_content=content.replace("<br/>", "\n"),
            metadata={
                "name": filename,
                "created_by": "try_sage_seed",
                "file_id": file_id,
                "source": filename,
            },
        )
    ]

    save_docs_to_vector_db(
        request=_AppRequestShim(app),
        docs=docs,
        collection_name=collection_name,
        metadata={"file_id": file_id, "name": filename},
        overwrite=False,
        split=True,
        add=True,
        user=None,
    )


# ---------------------------------------------------------------------------
# Magic link
# ---------------------------------------------------------------------------


def mint_persona_magic_link(email: str, ttl_hours: int) -> str:
    """Mint a System-2-compatible magic-link URL for a persona.

    The JWT shape mirrors `routers/auths.py:1150-1234` exactly:
      - signed with `SESSION_SECRET` via `utils.auth.create_token`
      - claim `type="magic_link"` so `verify_magic_link_login` accepts it
      - `sub` is the persona email
      - unique `jti` to prevent replay across resets
    Only the TTL differs (24h-ish vs. 15min) — that's the whole point of
    this helper.

    Returns the full URL or, if WEBUI_URL is empty (e.g. local dev with
    no host configured), a relative `/auth#magic_token=...` URL. The
    frontend banner handles both shapes.
    """
    # Deferred imports — same reason as the rest of the module: we don't
    # want a `mint_persona_magic_link` import to drag the entire auth
    # stack into a caller that just wants the function reference.
    from sage_is_ai.config import WEBUI_URL
    from sage_is_ai.utils.auth import create_token

    token = create_token(
        data={
            "sub": email,
            "type": "magic_link",
            "jti": secrets.token_hex(8),
        },
        expires_delta=timedelta(hours=max(1, int(ttl_hours))),
    )

    base = (WEBUI_URL.value or "").rstrip("/")
    if not base:
        return f"/auth#magic_token={token}"
    return f"{base}/auth#magic_token={token}"


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


async def seed_try_sage(app) -> None:
    """Idempotent boot/reset hook.

    Skips entirely when try-mode is off or the seed flag is disabled.
    Otherwise: ensure persona accounts exist, ensure agents exist,
    re-ingest any KB whose source folder hash changed, refresh the
    persona-link cache on `app.state.try_sage_persona_links`.

    Safe to call from `lifespan()` startup AND from `reset_persona_state`
    (which calls back here for drift correction). All operations are
    additive or idempotent overwrites.
    """
    # Deferred import — env values are cheap but config import has side
    # effects we'd rather not run at module-load time.
    from sage_is_ai.env import ENABLE_TRY_SAGE

    if not ENABLE_TRY_SAGE:
        return
    if not app.state.config.TRY_SAGE_PERSONA_SEED_ENABLED:
        return

    personas = get_persona_definitions(app)

    # Persona-account pass. Done before agents because the agents are
    # owned by the admin persona; we need its id.
    persona_users: dict[str, Any] = {}
    for persona in personas:
        user = _ensure_persona_account(persona)
        if user:
            persona_users[persona["key"]] = user

    admin_user = persona_users.get("admin")
    if not admin_user:
        # Without the admin persona we can't own the seed-managed agents.
        # Bail loud — this is a configuration error worth surfacing.
        log.error("try_sage_seed: admin persona missing; cannot seed agents")
        return

    # Agent + KB pass. Each agent file → ensure agent row → if KB folder
    # exists, ensure KB row + ingest.
    for slug in _DEFAULT_AGENT_SLUGS:
        md_path = os.path.join(_AGENTS_DIR, f"{slug}.md")
        agent_def = _parse_agent_md(md_path)
        if not agent_def:
            continue

        _ensure_agent(admin_user.id, agent_def)

        if slug in _AGENTS_WITH_KB:
            _ensure_kb(app, admin_user.id, slug)

    # Persona-link cache. Lives on app.state (not in DB) — these are
    # short-lived enough that a pod bounce regenerating them is fine,
    # and storing JWTs in the config DB would be a credential-leak vector.
    ttl_hours = int(app.state.config.TRY_SAGE_RESET_INTERVAL_HOURS)
    app.state.try_sage_persona_links = {
        persona["key"]: mint_persona_magic_link(persona["email"], ttl_hours)
        for persona in personas
    }
    log.info(
        f"try_sage_seed: seeded {len(personas)} personas, "
        f"{len(_DEFAULT_AGENT_SLUGS)} agents, KB folders for "
        f"{sorted(_AGENTS_WITH_KB)}"
    )


async def reset_persona_state(app) -> None:
    """Per-reset wipe.

    Removes each persona's chats and uploaded files, rotates magic links,
    and re-runs seed for drift correction. Persona accounts and KBs
    survive — the whole point of this design is a fast reset.

    Explicitly does NOT:
      - call `Storage.delete_all_files()` (would wipe persona-KB source)
      - call `VECTOR_DB_CLIENT.reset()` (would force re-embed of every KB)
      - delete persona User rows (would break magic-link continuity and
        every Chat/File foreign key on the next reset)
    """
    from sage_is_ai.env import ENABLE_TRY_SAGE
    from sage_is_ai.models.chats import Chats
    from sage_is_ai.models.files import Files
    from sage_is_ai.retrieval.vector.factory import VECTOR_DB_CLIENT
    from sage_is_ai.storage.provider import Storage

    if not ENABLE_TRY_SAGE:
        return

    personas = get_persona_definitions(app)

    for persona in personas:
        from sage_is_ai.models.users import Users

        user = Users.get_user_by_email(persona["email"])
        if not user:
            # Seed will create it on the re-run below; nothing to wipe yet.
            continue

        # Chats first — delete_chats_by_user_id also handles shared chats.
        Chats.delete_chats_by_user_id(user.id)

        # Then user-uploaded files. Skip files owned by the admin persona
        # whose paths point into the agent KB tree — those are seed-managed
        # and survive the reset alongside the KB embeddings.
        for f in Files.get_files_by_user_id(user.id):
            if persona["key"] == "admin" and f.path and f.path.startswith(_AGENTS_DIR):
                continue
            Files.delete_file_by_id(f.id)
            try:
                if f.path:
                    Storage.delete_file(f.path)
                # Per-file vector collection (chat-scoped). Safe to drop;
                # KB collections use the knowledge id, not `file-{id}`.
                VECTOR_DB_CLIENT.delete(collection_name=f"file-{f.id}")
            except Exception as e:
                # Best-effort cleanup — a missing storage object or vector
                # collection should not block the reset. Log + move on.
                log.warning(f"try_sage_seed: file cleanup partial for {f.id}: {e}")

    # Re-run seed for drift correction (idempotent) and to refresh the
    # persona-link cache with newly-minted JWTs. The previous cycle's
    # links would JWT-expire on their own, but rotating signals "new
    # session" to anyone holding an old link from the projector.
    await seed_try_sage(app)
    log.info("try_sage_seed: reset complete; persona chats/files wiped, KBs preserved")
