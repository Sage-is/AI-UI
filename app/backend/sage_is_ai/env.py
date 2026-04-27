import importlib.metadata
import json
import logging
import os
import pkgutil
import sys
import shutil
from uuid import uuid4
from pathlib import Path

import markdown
from bs4 import BeautifulSoup
from sage_is_ai.constants import ERROR_MESSAGES

####################################
# Load .env file
####################################

SAGE_IS_AI_DIR = Path(__file__).parent

BACKEND_DIR = SAGE_IS_AI_DIR.parent
BASE_DIR = BACKEND_DIR.parent

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(str(BASE_DIR / ".env")))
except ImportError:
    print("dotenv not installed, skipping...")

DOCKER = os.environ.get("DOCKER", "False").lower() == "true"

# device type embedding models - "cpu" (default), "cuda" (nvidia gpu required) or "mps" (apple silicon) - choosing this right can lead to better performance
USE_CUDA = os.environ.get("USE_CUDA_DOCKER", "false")

if USE_CUDA.lower() == "true":
    try:
        import torch

        assert torch.cuda.is_available(), "CUDA not available"
        DEVICE_TYPE = "cuda"
    except Exception as e:
        cuda_error = (
            "Error when testing CUDA but USE_CUDA_DOCKER is true. "
            f"Resetting USE_CUDA_DOCKER to false: {e}"
        )
        os.environ["USE_CUDA_DOCKER"] = "false"
        USE_CUDA = "false"
        DEVICE_TYPE = "cpu"
else:
    DEVICE_TYPE = "cpu"

try:
    import torch

    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        DEVICE_TYPE = "mps"
except Exception:
    pass

####################################
# LOGGING
####################################

_env_mode = os.environ.get("ENV", "dev")
_default_log_level = "WARNING" if _env_mode == "prod" else "INFO"

GLOBAL_LOG_LEVEL = os.environ.get("GLOBAL_LOG_LEVEL", "").upper()
if GLOBAL_LOG_LEVEL in logging.getLevelNamesMapping():
    logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL, force=True)
else:
    GLOBAL_LOG_LEVEL = _default_log_level

log = logging.getLogger(__name__)
log.info(f"GLOBAL_LOG_LEVEL: {GLOBAL_LOG_LEVEL}")

if "cuda_error" in locals():
    log.exception(cuda_error)
    del cuda_error

log_sources = [
    "AUDIO",
    "COMFYUI",
    "CONFIG",
    "DB",
    "IMAGES",
    "MAIN",
    "MODELS",
    "OLLAMA",
    "OPENAI",
    "RAG",
    "WEBHOOK",
    "SOCKET",
    "OAUTH",
]

SRC_LOG_LEVELS = {}

for source in log_sources:
    log_env_var = source + "_LOG_LEVEL"
    SRC_LOG_LEVELS[source] = os.environ.get(log_env_var, "").upper()
    if SRC_LOG_LEVELS[source] not in logging.getLevelNamesMapping():
        SRC_LOG_LEVELS[source] = GLOBAL_LOG_LEVEL
    log.info(f"{log_env_var}: {SRC_LOG_LEVELS[source]}")

log.setLevel(SRC_LOG_LEVELS["CONFIG"])

WEBUI_NAME = os.environ.get("WEBUI_NAME", "Sage.is AI")
if WEBUI_NAME != "Sage.is AI":
    WEBUI_NAME += " (Sage.is AI)"

WEBUI_FAVICON_URL = "https://sage.is/favicon.png"

TRUSTED_SIGNATURE_KEY = os.environ.get("TRUSTED_SIGNATURE_KEY", "")

####################################
# ENV (dev,test,prod)
####################################

ENV = os.environ.get("ENV", "dev")
DEV_MODE = os.environ.get("DEV_MODE", "false").lower() == "true"

FROM_INIT_PY = os.environ.get("FROM_INIT_PY", "False").lower() == "true"

if FROM_INIT_PY:
    try:
        PACKAGE_DATA = {"version": importlib.metadata.version("WEB-AI-Sage-WebUI")}
    except importlib.metadata.PackageNotFoundError:
        PACKAGE_DATA = {"version": "0.0.0"}
else:
    try:
        PACKAGE_DATA = json.loads((BASE_DIR / "package.json").read_text())
    except Exception:
        PACKAGE_DATA = {"version": "0.0.0"}

VERSION = PACKAGE_DATA["version"]
INSTANCE_ID = os.environ.get("INSTANCE_ID", str(uuid4()))


# ---------------------------------------------------------------------------
# Changelog parser
# ---------------------------------------------------------------------------
# Reads CHANGELOG.md and produces a JSON dict consumed by /api/changelog.
# Supports two formats:
#   - Bullet list:  `- **Title:** description`  (classic Keep-a-Changelog)
#   - Prose:        `**Title**\ndescription`     (paragraph-based, our style)
# Date separators: ` - ` (hyphen) or ` — ` (em dash).
# Versions without a date (e.g. [Unreleased]) are skipped.


def parse_section(h3_tag):
    """Parse items under a ### heading. Handles both <ul><li> and <p><strong> formats."""
    items = []
    current = h3_tag.find_next_sibling()

    while current and current.name not in ("h2", "h3"):
        # Format 1: bullet list (<ul> with <li> items)
        if current.name == "ul":
            for li in current.find_all("li"):
                raw_html = str(li)
                text = li.get_text(separator=" ", strip=True)
                parts = text.split(": ", 1)
                title = parts[0].strip() if len(parts) > 1 else ""
                content = parts[1].strip() if len(parts) > 1 else text
                items.append({"title": title, "content": content, "raw": raw_html})

        # Format 2: prose paragraphs (<p> with <strong> title)
        elif current.name == "p":
            strong = current.find("strong")
            if strong:
                title = strong.get_text(strip=True)
                # Content is the rest of this <p> plus any following <p> before next <strong>
                # Remove the strong tag text from the paragraph
                content_parts = []
                for child in current.children:
                    if child.name == "strong":
                        continue
                    text = child.get_text(strip=True) if hasattr(child, "get_text") else str(child).strip()
                    if text:
                        content_parts.append(text)
                content_text = " ".join(content_parts).strip()

                # Check if next sibling is a plain <p> (continuation of this entry)
                nxt = current.find_next_sibling()
                if nxt and nxt.name == "p" and not nxt.find("strong"):
                    content_text = (content_text + " " + nxt.get_text(strip=True)).strip()
                    # Skip that sibling in the outer loop
                    current = nxt

                items.append({
                    "title": title,
                    "content": content_text,
                    "raw": str(current),
                })

        current = current.find_next_sibling()

    return items


try:
    changelog_path = BASE_DIR / "CHANGELOG.md"
    with open(str(changelog_path.absolute()), "r", encoding="utf8") as file:
        changelog_content = file.read()

except Exception:
    changelog_content = (pkgutil.get_data("sage_is_ai", "CHANGELOG.md") or b"").decode()

# Convert markdown content to HTML
html_content = markdown.markdown(changelog_content)

# Parse the HTML content
soup = BeautifulSoup(html_content, "html.parser")

# Initialize JSON structure
changelog_json = {}

# Iterate over each version heading
for version in soup.find_all("h2"):
    heading = version.get_text().strip()

    # Split on " — " (em dash) or " - " (hyphen)
    for sep in (" — ", " - "):
        if sep in heading:
            version_number = heading.split(sep)[0].strip().strip("[]")
            date = heading.split(sep, 1)[1].strip()
            break
    else:
        # No date separator (e.g. [Unreleased]) — skip
        continue

    version_data = {"date": date}

    # Walk siblings collecting h3 sections
    current = version.find_next_sibling()
    while current and current.name != "h2":
        if current.name == "h3":
            section_title = current.get_text().lower()  # e.g., "added", "fixed"
            version_data[section_title] = parse_section(current)
        current = current.find_next_sibling()

    changelog_json[version_number] = version_data

CHANGELOG = changelog_json

####################################
# SAFE_MODE
####################################

SAFE_MODE = os.environ.get("SAFE_MODE", "false").lower() == "true"


####################################
# ENABLE_FORWARD_USER_INFO_HEADERS
####################################

ENABLE_FORWARD_USER_INFO_HEADERS = (
    os.environ.get("ENABLE_FORWARD_USER_INFO_HEADERS", "False").lower() == "true"
)

####################################
# WEBUI_BUILD_HASH
####################################

WEBUI_BUILD_HASH = os.environ.get("WEBUI_BUILD_HASH", "dev-build")

####################################
# DATA/FRONTEND BUILD DIR
####################################

DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data")).resolve()

if FROM_INIT_PY:
    NEW_DATA_DIR = Path(os.getenv("DATA_DIR", SAGE_IS_AI_DIR / "data")).resolve()
    NEW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check if the data directory exists in the package directory
    if DATA_DIR.exists() and DATA_DIR != NEW_DATA_DIR:
        log.info(f"Moving {DATA_DIR} to {NEW_DATA_DIR}")
        for item in DATA_DIR.iterdir():
            dest = NEW_DATA_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        # Zip the data directory
        shutil.make_archive(DATA_DIR.parent / "sage_is_ai_data", "zip", DATA_DIR)

        # Remove the old data directory
        shutil.rmtree(DATA_DIR)

    DATA_DIR = Path(os.getenv("DATA_DIR", SAGE_IS_AI_DIR / "data"))

STATIC_DIR = Path(os.getenv("STATIC_DIR", SAGE_IS_AI_DIR / "static"))

FONTS_DIR = Path(os.getenv("FONTS_DIR", SAGE_IS_AI_DIR / "static" / "fonts"))

FRONTEND_BUILD_DIR = Path(os.getenv("FRONTEND_BUILD_DIR", BASE_DIR / "build")).resolve()

if FROM_INIT_PY:
    FRONTEND_BUILD_DIR = Path(
        os.getenv("FRONTEND_BUILD_DIR", SAGE_IS_AI_DIR / "frontend")
    ).resolve()

####################################
# Database
####################################

# Check if the file exists
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/webui.db")
    log.info("Database migrated from Ollama-WebUI successfully.")
else:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR}/webui.db")

# Maximum upload size (MB) for backup restore during onboarding
BACKUP_RESTORE_MAX_SIZE_MB = int(os.environ.get("BACKUP_RESTORE_MAX_SIZE_MB", "512"))

RESET_CONFIG_ON_START = (
    os.environ.get("RESET_CONFIG_ON_START", "False").lower() == "true"
)

ENABLE_REALTIME_CHAT_SAVE = (
    os.environ.get("ENABLE_REALTIME_CHAT_SAVE", "False").lower() == "true"
)

####################################
# REDIS
####################################

REDIS_URL = os.environ.get("REDIS_URL", "")
REDIS_KEY_PREFIX = os.environ.get("REDIS_KEY_PREFIX", "sage-is-ai")
REDIS_SENTINEL_HOSTS = os.environ.get("REDIS_SENTINEL_HOSTS", "")
REDIS_SENTINEL_PORT = os.environ.get("REDIS_SENTINEL_PORT", "26379")

# Maximum number of retries for Redis operations when using Sentinel fail-over
REDIS_SENTINEL_MAX_RETRY_COUNT = os.environ.get("REDIS_SENTINEL_MAX_RETRY_COUNT", "2")
try:
    REDIS_SENTINEL_MAX_RETRY_COUNT = int(REDIS_SENTINEL_MAX_RETRY_COUNT)
    if REDIS_SENTINEL_MAX_RETRY_COUNT < 1:
        REDIS_SENTINEL_MAX_RETRY_COUNT = 2
except ValueError:
    REDIS_SENTINEL_MAX_RETRY_COUNT = 2

####################################
# UVICORN WORKERS
####################################

# Number of uvicorn worker processes for handling requests
UVICORN_WORKERS = os.environ.get("UVICORN_WORKERS", "1")
try:
    UVICORN_WORKERS = int(UVICORN_WORKERS)
    if UVICORN_WORKERS < 1:
        UVICORN_WORKERS = 1
except ValueError:
    UVICORN_WORKERS = 1
    log.info(f"Invalid UVICORN_WORKERS value, defaulting to {UVICORN_WORKERS}")

####################################
# WEBUI_AUTH (Required for security)
####################################

WEBUI_AUTH = os.environ.get("WEBUI_AUTH", "True").lower() == "true"
WEBUI_AUTH_TRUSTED_EMAIL_HEADER = os.environ.get(
    "WEBUI_AUTH_TRUSTED_EMAIL_HEADER", None
)
WEBUI_AUTH_TRUSTED_NAME_HEADER = os.environ.get("WEBUI_AUTH_TRUSTED_NAME_HEADER", None)
WEBUI_AUTH_TRUSTED_GROUPS_HEADER = os.environ.get(
    "WEBUI_AUTH_TRUSTED_GROUPS_HEADER", None
)


BYPASS_MODEL_ACCESS_CONTROL = (
    os.environ.get("BYPASS_MODEL_ACCESS_CONTROL", "False").lower() == "true"
)

WEBUI_AUTH_SIGNOUT_REDIRECT_URL = os.environ.get(
    "WEBUI_AUTH_SIGNOUT_REDIRECT_URL", None
)

####################################
# WEBUI_SECRET_KEY
####################################

WEBUI_SECRET_KEY = os.environ.get(
    "WEBUI_SECRET_KEY",
    os.environ.get(
        "WEBUI_JWT_SECRET_KEY", "t0p-s3cr3t"
    ),  # DEPRECATED: remove at next major version
)

WEBUI_SESSION_COOKIE_SAME_SITE = os.environ.get("WEBUI_SESSION_COOKIE_SAME_SITE", "lax")

WEBUI_SESSION_COOKIE_SECURE = (
    os.environ.get("WEBUI_SESSION_COOKIE_SECURE", "false").lower() == "true"
)

WEBUI_AUTH_COOKIE_SAME_SITE = os.environ.get(
    "WEBUI_AUTH_COOKIE_SAME_SITE", WEBUI_SESSION_COOKIE_SAME_SITE
)

WEBUI_AUTH_COOKIE_SECURE = (
    os.environ.get(
        "WEBUI_AUTH_COOKIE_SECURE",
        os.environ.get("WEBUI_SESSION_COOKIE_SECURE", "false"),
    ).lower()
    == "true"
)

if WEBUI_AUTH and WEBUI_SECRET_KEY == "":
    raise ValueError(ERROR_MESSAGES.ENV_VAR_NOT_FOUND)

ENABLE_COMPRESSION_MIDDLEWARE = (
    os.environ.get("ENABLE_COMPRESSION_MIDDLEWARE", "True").lower() == "true"
)

####################################
# MODELS
####################################

MODELS_CACHE_TTL = os.environ.get("MODELS_CACHE_TTL", "1")
if MODELS_CACHE_TTL == "":
    MODELS_CACHE_TTL = None
else:
    try:
        MODELS_CACHE_TTL = int(MODELS_CACHE_TTL)
    except Exception:
        MODELS_CACHE_TTL = 1


####################################
# WEBSOCKET SUPPORT
####################################

ENABLE_WEBSOCKET_SUPPORT = (
    os.environ.get("ENABLE_WEBSOCKET_SUPPORT", "True").lower() == "true"
)


WEBSOCKET_MANAGER = os.environ.get("WEBSOCKET_MANAGER", "")

WEBSOCKET_REDIS_URL = os.environ.get("WEBSOCKET_REDIS_URL", REDIS_URL)

websocket_redis_lock_timeout = os.environ.get("WEBSOCKET_REDIS_LOCK_TIMEOUT", "60")

try:
    WEBSOCKET_REDIS_LOCK_TIMEOUT = int(websocket_redis_lock_timeout)
except ValueError:
    WEBSOCKET_REDIS_LOCK_TIMEOUT = 60

WEBSOCKET_SENTINEL_HOSTS = os.environ.get("WEBSOCKET_SENTINEL_HOSTS", "")

WEBSOCKET_SENTINEL_PORT = os.environ.get("WEBSOCKET_SENTINEL_PORT", "26379")

AIOHTTP_CLIENT_TIMEOUT = os.environ.get("AIOHTTP_CLIENT_TIMEOUT", "")

if AIOHTTP_CLIENT_TIMEOUT == "":
    AIOHTTP_CLIENT_TIMEOUT = None
else:
    try:
        AIOHTTP_CLIENT_TIMEOUT = int(AIOHTTP_CLIENT_TIMEOUT)
    except Exception:
        AIOHTTP_CLIENT_TIMEOUT = 300


AIOHTTP_CLIENT_SESSION_SSL = (
    os.environ.get("AIOHTTP_CLIENT_SESSION_SSL", "True").lower() == "true"
)

AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = os.environ.get(
    "AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST",
    os.environ.get("AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST", "10"),
)

if AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST == "":
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = None
else:
    try:
        AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = int(AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    except Exception:
        AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = 10


AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = os.environ.get(
    "AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA", "10"
)

if AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA == "":
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = None
else:
    try:
        AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = int(
            AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA
        )
    except Exception:
        AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = 10


AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL = (
    os.environ.get("AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL", "True").lower() == "true"
)


####################################
# SENTENCE TRANSFORMERS
####################################


SENTENCE_TRANSFORMERS_BACKEND = os.environ.get("SENTENCE_TRANSFORMERS_BACKEND", "")
if SENTENCE_TRANSFORMERS_BACKEND == "":
    SENTENCE_TRANSFORMERS_BACKEND = "torch"


SENTENCE_TRANSFORMERS_MODEL_KWARGS = os.environ.get(
    "SENTENCE_TRANSFORMERS_MODEL_KWARGS", ""
)
if SENTENCE_TRANSFORMERS_MODEL_KWARGS == "":
    SENTENCE_TRANSFORMERS_MODEL_KWARGS = None
else:
    try:
        SENTENCE_TRANSFORMERS_MODEL_KWARGS = json.loads(
            SENTENCE_TRANSFORMERS_MODEL_KWARGS
        )
    except Exception:
        SENTENCE_TRANSFORMERS_MODEL_KWARGS = None


SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND = os.environ.get(
    "SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND", ""
)
if SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND == "":
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND = "torch"


SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = os.environ.get(
    "SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS", ""
)
if SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS == "":
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = None
else:
    try:
        SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = json.loads(
            SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS
        )
    except Exception:
        SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = None

####################################
# OFFLINE_MODE
####################################

ENABLE_VERSION_UPDATE_CHECK = (
    os.environ.get("ENABLE_VERSION_UPDATE_CHECK", "true").lower() == "true"
)
OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "false").lower() == "true"

if OFFLINE_MODE:
    os.environ["HF_HUB_OFFLINE"] = "1"
    ENABLE_VERSION_UPDATE_CHECK = False

####################################
# AUDIT LOGGING
####################################
# Where to store log file
AUDIT_LOGS_FILE_PATH = f"{DATA_DIR}/audit.log"
# Maximum size of a file before rotating into a new log file
AUDIT_LOG_FILE_ROTATION_SIZE = os.getenv("AUDIT_LOG_FILE_ROTATION_SIZE", "10MB")

# Comma separated list of logger names to use for audit logging
# Default is "uvicorn.access" which is the access log for Uvicorn
# You can add more logger names to this list if you want to capture more logs
AUDIT_UVICORN_LOGGER_NAMES = os.getenv(
    "AUDIT_UVICORN_LOGGER_NAMES", "uvicorn.access"
).split(",")

# METADATA | REQUEST | REQUEST_RESPONSE
AUDIT_LOG_LEVEL = os.getenv("AUDIT_LOG_LEVEL", "NONE").upper()
try:
    MAX_BODY_LOG_SIZE = int(os.environ.get("MAX_BODY_LOG_SIZE") or 2048)
except ValueError:
    MAX_BODY_LOG_SIZE = 2048

# Comma separated list for urls to exclude from audit
AUDIT_EXCLUDED_PATHS = os.getenv("AUDIT_EXCLUDED_PATHS", "/chats,/chat,/folders").split(
    ","
)
AUDIT_EXCLUDED_PATHS = [path.strip() for path in AUDIT_EXCLUDED_PATHS]
AUDIT_EXCLUDED_PATHS = [path.lstrip("/") for path in AUDIT_EXCLUDED_PATHS]


####################################
# OPENTELEMETRY
####################################

ENABLE_OTEL = os.environ.get("ENABLE_OTEL", "False").lower() == "true"
ENABLE_OTEL_METRICS = os.environ.get("ENABLE_OTEL_METRICS", "False").lower() == "true"
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
)
OTEL_EXPORTER_OTLP_INSECURE = (
    os.environ.get("OTEL_EXPORTER_OTLP_INSECURE", "False").lower() == "true"
)
OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "sage-is-ai")
OTEL_RESOURCE_ATTRIBUTES = os.environ.get(
    "OTEL_RESOURCE_ATTRIBUTES", ""
)  # e.g. key1=val1,key2=val2
OTEL_TRACES_SAMPLER = os.environ.get(
    "OTEL_TRACES_SAMPLER", "parentbased_always_on"
).lower()
OTEL_BASIC_AUTH_USERNAME = os.environ.get("OTEL_BASIC_AUTH_USERNAME", "")
OTEL_BASIC_AUTH_PASSWORD = os.environ.get("OTEL_BASIC_AUTH_PASSWORD", "")


OTEL_OTLP_SPAN_EXPORTER = os.environ.get(
    "OTEL_OTLP_SPAN_EXPORTER", "grpc"
).lower()  # grpc or http


####################################
# TOOLS/FUNCTIONS PIP OPTIONS
####################################

PIP_OPTIONS = os.getenv("PIP_OPTIONS", "").split()
PIP_PACKAGE_INDEX_OPTIONS = os.getenv("PIP_PACKAGE_INDEX_OPTIONS", "").split()


####################################
# PROGRESSIVE WEB APP OPTIONS
####################################

EXTERNAL_PWA_MANIFEST_URL = os.environ.get("EXTERNAL_PWA_MANIFEST_URL")


####################################
# try.sage TRIAL MODE
####################################
# Trial-deployment configuration for try.sage.is.
# All values here are env-only — never persisted to the config DB and never
# returned in any API response. Tunable runtime values (intervals, seat
# count, banner text, etc.) live in config.py wrapped in PersistentConfig.
#
# Why split this way:
#   - ENABLE_TRY_SAGE toggles whole subsystems at import time (router
#     registration, lifespan task spawn, hidden-connection install).
#     Persisting it would let an admin flip it via the UI without a restart,
#     which is unsafe — handlers would race against startup wiring.
#   - The hidden LLM connection is the trial's keys-to-the-kingdom.
#     Persisting URL/key to the config DB would defeat the "admins cannot
#     see or edit" contract from the plan. Keeping them env-only means they
#     never touch the DB at rest.
#   - Persona passwords are optional; if unset, the seed routine generates
#     random ones and logs them once at first boot. Personas are normally
#     reached via magic-link JWT, so a password is a fallback.

ENABLE_TRY_SAGE = os.environ.get("ENABLE_TRY_SAGE", "False").lower() == "true"

# Hidden OpenAI-compatible inference connection.
# When try mode is on, the inference resolver unions this connection into
# its provider list, but every admin-facing connections endpoint filters it
# out. Exposed models are restricted to TRY_SAGE_LLM_MODELS so users cannot
# call non-trial models by ID.
TRY_SAGE_LLM_API_URL = os.environ.get("TRY_SAGE_LLM_API_URL", "")
TRY_SAGE_LLM_API_KEY = os.environ.get("TRY_SAGE_LLM_API_KEY", "")


def _parse_try_sage_models(raw: str) -> list[str]:
    """Accept either a JSON array (e.g. '["gpt-4o","gpt-4o-mini"]') or a
    comma-separated list (e.g. 'gpt-4o, gpt-4o-mini'). Anything else logs
    a warning and degrades to an empty allowlist."""
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(m).strip() for m in parsed if str(m).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    return [m.strip() for m in raw.split(",") if m.strip()]


TRY_SAGE_LLM_MODELS = _parse_try_sage_models(os.environ.get("TRY_SAGE_LLM_MODELS", ""))

# Per-persona seed passwords. Optional — the seed routine generates random
# passwords and logs them once if any are unset. Personas use magic-link
# JWTs in normal use; passwords are a fallback for direct sign-in.
TRY_SAGE_ADMIN_PASSWORD = os.environ.get("TRY_SAGE_ADMIN_PASSWORD", "")
TRY_SAGE_FACILITATOR_PASSWORD = os.environ.get("TRY_SAGE_FACILITATOR_PASSWORD", "")
TRY_SAGE_USER_PASSWORD = os.environ.get("TRY_SAGE_USER_PASSWORD", "")
