"""Runtime Python installs go through uv; pip, setuptools and wheel left the image in 3.2.1.

Three callers install packages while the app runs: Function and Tool
requirements (utils/plugin.py), the chromadb fallback (sprigs/vector_bootstrap.py)
and the AI Engine wizard (routers/retrieval.py, already on uv). The first two
build their command here, so there is one place that knows how uv is called.

``PIP_OPTIONS`` and ``PIP_PACKAGE_INDEX_OPTIONS`` keep their names and still take
pip spellings: uv accepts nearly all of them (``--pre``, ``--trusted-host``,
``--no-cache-dir``, ``--force-reinstall`` ...). The four it refuses are dropped
here with a warning instead of failing every install; ``test_runtime_install.py``
pins that list against what uv 0.12.24 rejected (2026-10-15).
"""

from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)

# pip flags uv rejects outright. None changes what gets installed in this image:
# the first three tune pip's own behaviour, and --user targets a user site the
# container does not use.
PIP_ONLY_FLAGS = frozenset(
    ("--root-user-action", "--prefer-binary", "--no-warn-script-location", "--user")
)
_TAKES_VALUE = frozenset(("--root-user-action",))


def uv_compatible(options: list[str]) -> list[str]:
    """Drop the pip-only flags (and a separate value after one), keep the rest."""
    kept: list[str] = []
    dropped: list[str] = []
    skip_value = False
    for opt in options:
        if skip_value:
            dropped.append(opt)
            skip_value = False
            continue
        name, has_value, _ = opt.partition("=")
        if name in PIP_ONLY_FLAGS:
            dropped.append(opt)
            skip_value = name in _TAKES_VALUE and not has_value
            continue
        kept.append(opt)
    if dropped:
        log.warning(
            "uv does not take these pip options; ignoring them: %s", " ".join(dropped)
        )
    return kept


def system_install_cmd(
    requirements: list[str], pip_options: list[str], index_options: list[str]
) -> list[str]:
    """Install into the image's own site-packages, as `python -m pip install` did."""
    return [
        "uv", "pip", "install",
        "--python", sys.executable, "--system", "--break-system-packages",
        *uv_compatible(pip_options), *requirements, *uv_compatible(index_options),
    ]  # fmt: skip


def target_install_cmd(requirements: list[str], target: str, *extra: str) -> list[str]:
    """Install into a separate directory (DATA_DIR/ml_packages)."""
    return [
        "uv", "pip", "install",
        "--python", sys.executable, "--target", target, "--break-system-packages",
        *extra, *requirements,
    ]  # fmt: skip
