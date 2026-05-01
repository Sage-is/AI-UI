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
            "label": "Admin",
            "group": None,
        },
        {
            "key": "facilitator",
            "email": "try-facilitator@try.sage.is",
            "role": "facilitator",
            "label": "Facilitator",
            # Group membership is set up by `_ensure_facilitator_group` —
            # the facilitator persona joins a "Facilitators" group with
            # workshop.* permissions enabled.
            "group": "facilitator",
        },
    ]
    for i in range(1, seat_count + 1):
        personas.append(
            {
                "key": f"user-{i}",
                "email": f"try-user-{i}@try.sage.is",
                "role": "user",
                "label": f"User {i}",
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

# Per-slug fallback `base_model` when the MD frontmatter ships an empty
# value. The MD files are content, not code — workshop authors edit them
# without rebuilding — so we keep a code-side safety net mapping each
# canonical agent to a sensible Groq-served model. If the upstream
# provider changes its model IDs, edit here AND the MD frontmatter
# together. Slugs not in this map fall through to "" (admin must pick).
_AGENT_DEFAULT_BASE_MODELS: dict[str, str] = {
    "sage-strawberry": "openai/gpt-oss-120b",
    "sage-startr-style": "qwen/qwen3-32b",
    "astropi-ai-tutor": "meta-llama/llama-4-scout-17b-16e-instruct",
}


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
    slug = meta.get("slug")
    # Fall back to the per-slug default when the MD ships empty. Without
    # a base_model the agent has nothing to call and never appears in
    # the model selector — see the seed-data README for the rationale.
    base_model = meta.get("base_model", "") or _AGENT_DEFAULT_BASE_MODELS.get(slug, "")
    return {
        "slug": slug,
        "name": meta.get("name"),
        "description": meta.get("description", ""),
        "base_model": base_model,
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


def _ensure_persona_ui_settings(user: Any) -> None:
    """Pin a persona's default UI settings (model + theme) without clobbering
    existing customization.

    Sets `settings.ui.models = ["sage-strawberry"]` and
    `settings.ui.theme = "light"` only when those keys are absent. An admin
    who explored other models in a previous session keeps their pick;
    a freshly-seeded admin lands on Strawberry like every other persona.

    `update_user_settings_by_id` does a top-level dict.update, so we read
    the existing `ui` block, merge with `setdefault`, and write the merged
    dict back as a single `{"ui": {...}}` key.
    """
    from sage_is_ai.models.users import Users

    existing_settings = user.settings.model_dump() if user.settings else {}
    existing_ui = dict(existing_settings.get("ui") or {})

    desired_ui = dict(existing_ui)
    desired_ui.setdefault("models", ["sage-strawberry"])
    desired_ui.setdefault("theme", "light")

    if desired_ui != existing_ui:
        Users.update_user_settings_by_id(user.id, {"ui": desired_ui})


_FACILITATOR_GROUP_NAME = "Facilitators"


def _ensure_facilitator_group(admin_user_id: str, facilitator_user_id: str) -> None:
    """Find-or-create the Facilitators group and add the persona to it.

    Workshop access in this codebase is gated by
    `has_permission(user.id, "workshop.<resource>", USER_PERMISSIONS)`,
    which consults group-level permission overrides before falling back
    to the global default. Granting facilitators workshop access without
    flipping the global default for *all* users means a dedicated group
    with `workshop.*` overrides set to True.

    Idempotent on both axes: `add_users_to_group` already de-dupes user
    ids, and we look up by name rather than creating a new row each boot.
    """
    from sage_is_ai.models.groups import GroupForm, Groups

    group = next(
        (g for g in Groups.get_groups() if g.name == _FACILITATOR_GROUP_NAME),
        None,
    )
    if not group:
        group = Groups.insert_new_group(
            admin_user_id,
            GroupForm(
                name=_FACILITATOR_GROUP_NAME,
                description="try.sage facilitator workshop access",
                permissions={
                    "workshop": {
                        "models": True,
                        "knowledge": True,
                        "prompts": True,
                        "tools": True,
                    },
                },
            ),
        )
        if not group:
            log.error("try_sage_seed: failed to create Facilitators group")
            return

    Groups.add_users_to_group(group.id, [facilitator_user_id])


# ---------------------------------------------------------------------------
# Agent + KB ensure
# ---------------------------------------------------------------------------


_DEFAULT_AGENT_CAPABILITIES: dict = {
    # Workshop default: lock down everything except citations so trial
    # users see clean, focused chats. Citations is the one signal we
    # explicitly want — KB-backed agents (Startr.Style, AstroPi) cite
    # their source documents, which is the whole point of seeding KBs.
    # Admins can flip individual capabilities on per-agent post-seed
    # if they want to demo vision/code/etc.
    "vision": False,
    "file_upload": False,
    "image_generation": False,
    "code_interpreter": False,
    "citations": True,
}


def _ensure_agent(persona_user_id: str, agent_def: dict, kb_id: Optional[str] = None) -> None:
    """Find-or-update one agent (a Model row) by slug.

    Agents in this codebase ARE model rows with `base_model_id` set —
    same shape the admin Models UI creates. We reuse `Models.insert_new_model`
    on first boot and `Models.update_model_by_id` on subsequent boots to
    refresh the system prompt from source.

    When `kb_id` is provided, the agent gets bound to that knowledge
    collection via `meta.knowledge` (same shape the admin UI writes when
    a user picks a KB from the Knowledge selector — see
    `app/src/lib/components/workshop/Models/Knowledge.svelte:212-218`).
    """
    from sage_is_ai.models.knowledge import Knowledges
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

    # Build meta extras: KB binding (if any) and capability defaults.
    # ModelMeta allows extra keys (`extra="allow"`) so `knowledge` flows
    # through unchanged into the JSON column.
    meta_kwargs: dict = {
        "description": agent_def["description"],
        "capabilities": dict(_DEFAULT_AGENT_CAPABILITIES),
    }
    if kb_id:
        kb_record = Knowledges.get_knowledge_by_id(kb_id)
        if kb_record:
            # Mirror the dict shape the admin UI emits when binding a KB
            # to a model — name/description/data fields, not just id.
            # `routers/knowledge.py:633-640` reads back via `k.get("id")`,
            # so id is the load-bearing field; the rest is for display.
            meta_kwargs["knowledge"] = [
                {
                    "id": kb_record.id,
                    "user_id": kb_record.user_id,
                    "name": kb_record.name,
                    "description": kb_record.description,
                    "data": kb_record.data,
                    "type": "collection",
                }
            ]
    meta = ModelMeta(**meta_kwargs)

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
    from sage_is_ai.retrieval.vector.factory import VECTOR_DB_CLIENT

    # Bail out cleanly when the vector backend is missing — typically
    # chromadb hasn't been installed yet (the AI Engine wizard handles
    # that). Without a vector client, ingestion would silently fail per
    # file and leave behind an empty KB row that breaks the workshop UI
    # (`/workshop/knowledge/{id}` 404s, agent editor throws on load).
    # Returning None here means: do not create a KB row, do not bind
    # anything to the agent. When chromadb is later installed and the
    # container restarts, this function runs again and seeds cleanly.
    if VECTOR_DB_CLIENT is None:
        # Clean up any orphaned empty KB rows from a previous boot that
        # tried to ingest before chromadb was available. Leaving them
        # in place keeps the workshop page broken even after we stop
        # binding them to agents.
        kb_collection_name = f"try_sage_kb_{slug}"
        for kb in Knowledges.get_knowledge_bases():
            if kb.name == kb_collection_name and not (
                (kb.data or {}).get("file_ids") or []
            ):
                Knowledges.delete_knowledge_by_id(kb.id)
                log.info(
                    f"try_sage_seed: deleted orphan empty KB row {kb.id} "
                    f"for {slug}; will re-create on next vector-DB-ready boot."
                )
        log.warning(
            f"try_sage_seed: vector DB unavailable; skipping KB for {slug}. "
            "Install chromadb (or your configured vector backend) via the "
            "AI Engine wizard, then restart to seed the agent KB."
        )
        return None

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

    # Skip ingestion if the source hasn't changed AND the existing KB
    # actually has data. The `data.file_ids` sanity check catches the
    # case where a previous boot stamped the version map as "done" even
    # though every per-file ingestion failed (e.g. chromadb wasn't
    # installed yet). Without this check we'd return a kb_id pointing
    # at an empty KB row that breaks the agent editor and the KB page.
    existing_file_ids = (knowledge.data or {}).get("file_ids") or []
    if version_map.get(slug) == folder_hash and existing_file_ids:
        return knowledge.id
    if version_map.get(slug) == folder_hash and not existing_file_ids:
        log.info(
            f"try_sage_seed: KB {slug} hash matches but file_ids empty; "
            "previous ingestion failed silently, re-ingesting."
        )

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

    # Bail out before stamping anything if every file failed. Marking the
    # version as "done" with no data is exactly the bug that caused
    # silent half-baked KBs to persist across resets — see the empty
    # `data.file_ids` recovery branch above. Returning None also stops
    # the caller from binding a useless KB to the agent.
    if not new_file_ids:
        log.warning(
            f"try_sage_seed: no files ingested for {slug}; will retry next boot."
        )
        return None

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

    Returns a fully-qualified URL. Resolution order for the host:
      1. ``WEBUI_URL`` config (operator-set, the prod or LAN-friendly path)
      2. ``http://localhost:{WEBUI_PORT}`` env (single-host local dev)
      3. ``http://localhost:8080`` (matches the default Makefile mapping)

    A relative URL is never returned — that path used to land here when
    operators printed links to a terminal and tried to copy-paste, ending
    up with broken `localhost`-less URLs that wouldn't resolve in a
    browser. Always emit something a human can click.
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
        # Last-resort fallback for local-dev workshops where the operator
        # never configured WEBUI_URL. Matches `PORT_MAPPING ?= 8080:8080`
        # in the Makefile. Operator can still override via WEBUI_URL.
        port = os.environ.get("WEBUI_PORT", "8080")
        base = f"http://localhost:{port}"
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

    # Agent + KB pass. KB ingestion runs FIRST so we can capture the KB
    # id and bind it into the agent's `meta.knowledge` on the same pass.
    # Without that binding the KB sits in the vector store unconnected
    # and RAG never fires for its agent.
    for slug in _DEFAULT_AGENT_SLUGS:
        md_path = os.path.join(_AGENTS_DIR, f"{slug}.md")
        agent_def = _parse_agent_md(md_path)
        if not agent_def:
            continue

        kb_id: Optional[str] = None
        if slug in _AGENTS_WITH_KB:
            kb_id = _ensure_kb(app, admin_user.id, slug)

        _ensure_agent(admin_user.id, agent_def, kb_id=kb_id)

    # UI settings pass. Pin every persona to Sage Strawberry as the
    # default model and Light theme — non-destructively (existing
    # custom values win). Run after agents exist so the model id we
    # pin actually resolves.
    for user in persona_users.values():
        _ensure_persona_ui_settings(user)

    # Facilitator group + workshop access.
    facilitator_user = persona_users.get("facilitator")
    if facilitator_user:
        _ensure_facilitator_group(admin_user.id, facilitator_user.id)

    # Persona-link cache. Lives on app.state (not in DB).
    #
    # Stable links by design: mint once on first boot and reuse across
    # every subsequent seed call (resets, drift correction). Reset wipes
    # account contents, not the magic-link tokens — operators want to
    # hand out URLs once before a workshop and trust them across a
    # week-long campaign. TTL is `TRY_SAGE_PERSONA_LINK_TTL_DAYS`
    # (default 7 days) rather than the reset interval so links outlast
    # many reset cycles within a single workshop.
    #
    # If the cache survives the seed call (the normal path), no new JWTs
    # get minted and no fresh URLs print to the terminal — the previously-
    # shared links remain valid.
    ttl_days = int(app.state.config.TRY_SAGE_PERSONA_LINK_TTL_DAYS)
    ttl_hours = ttl_days * 24

    existing = getattr(app.state, "try_sage_persona_links", None) or {}
    cached_keys = {p["key"] for p in personas if p["key"] in existing}
    needs_mint = cached_keys != {p["key"] for p in personas}

    if needs_mint:
        # First boot, or seat-count change added new personas. Mint only
        # the missing ones — preserve any links that were already cached.
        new_links = dict(existing)
        for persona in personas:
            if persona["key"] not in new_links:
                new_links[persona["key"]] = mint_persona_magic_link(
                    persona["email"], ttl_hours
                )
        app.state.try_sage_persona_links = new_links

    log.info(
        f"try_sage_seed: seeded {len(personas)} personas, "
        f"{len(_DEFAULT_AGENT_SLUGS)} agents, KB folders for "
        f"{sorted(_AGENTS_WITH_KB)}"
    )

    # Print persona magic links to stdout — but only when we actually
    # minted (or re-minted) something. Reset cycles preserve the cache,
    # so the operator's terminal stays clean. First boot prints once;
    # adding a new persona seat prints once per added seat.
    if needs_mint:
        _print_persona_links(
            personas, app.state.try_sage_persona_links, ttl_hours
        )


def _print_persona_links(
    personas: list[dict], links: dict[str, str], ttl_hours: int
) -> None:
    """Render the persona-link block to stdout in a workshop-friendly format.

    Kept as its own helper so the formatting is testable and so `flush=True`
    is in one place. Width is fixed at 80 columns to fit a typical terminal
    without wrapping URLs to a second line.

    Fires only on initial seed (or when a new persona seat is added) —
    reset cycles preserve the cache and stay quiet. See `seed_try_sage`.
    """
    bar = "=" * 80
    # Persona key column width sized to the longest key for tidy alignment.
    key_width = max(len(p["key"]) for p in personas)
    ttl_days = max(1, ttl_hours // 24)

    print(bar, flush=True)
    print(
        f"try.sage trial — persona magic links (valid for ~{ttl_days} days)",
        flush=True,
    )
    print(bar, flush=True)
    print(
        "Open any URL below to sign in as that persona. Links survive "
        "resets — only account contents (chats, files) get wiped.",
        flush=True,
    )
    print("", flush=True)
    for persona in personas:
        url = links.get(persona["key"], "<unavailable>")
        print(f"  {persona['key']:<{key_width}}  {url}", flush=True)
    print("", flush=True)
    print(
        "Same links appear in the trial banner and at "
        "GET /api/v1/sage/runtime/personas.",
        flush=True,
    )
    print(bar, flush=True)


async def reset_persona_state(app) -> None:
    """Per-reset wipe.

    Removes each persona's chats and uploaded files, invalidates active
    session JWTs (so everyone bounces back to the welcome page on their
    next API call), and re-runs seed for drift correction. Persona
    accounts, KBs, and the persona magic-link cache survive — the whole
    point of this design is a fast reset where the same magic links keep
    working across the workshop window.

    Session invalidation is implemented as an issued-at cutoff: every
    session token mints with `iat`; the cutoff timestamp is the most
    recent reset; `get_current_user` rejects sessions whose `iat <
    cutoff`. The magic-link JWTs (separate token type) are NOT subject
    to this check, so the persona links stay valid for their full TTL.

    Explicitly does NOT:
      - call `Storage.delete_all_files()` (would wipe persona-KB source)
      - call `VECTOR_DB_CLIENT.reset()` (would force re-embed of every KB)
      - delete persona User rows (would break magic-link continuity and
        every Chat/File foreign key on the next reset)
      - rotate the persona magic-link cache (links stay stable across
        every in-window reset; only natural JWT expiry rotates them)
    """
    import time as _time

    from sage_is_ai.env import ENABLE_TRY_SAGE
    from sage_is_ai.models.chats import Chats
    from sage_is_ai.models.files import Files
    from sage_is_ai.retrieval.vector.factory import VECTOR_DB_CLIENT
    from sage_is_ai.storage.provider import Storage

    if not ENABLE_TRY_SAGE:
        return

    # Invalidate every session JWT issued before this moment. Done up
    # front so a slow chats/files wipe doesn't leave a window where a
    # signed-in admin can still poke the API mid-reset.
    app.state.config.TRY_SAGE_SESSIONS_INVALIDATED_AT = int(_time.time())

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
