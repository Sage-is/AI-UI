"""AI engine components. The one wizard panel that grafts.

Two capabilities, two ways to get them: download the model weights, or graft the
in-housed Sprig™ that carries them. The Svelte panel offers both and so does
this.

The graft targets real cultivars. This panel used to graft `mock-embedding`,
whose vectors are seeded from a sha256 of the input text, and then tell the
operator "Document search is ready". Uploads succeeded, queries returned
results, and the results were noise, with every surface reporting success.
`minilm-onnx-inhoused` is deliberately the same 384-dim width as the mock, so
the swap needs no reindex. Both cultivars arrive as OCI artifacts from the
configured registry, so this stays zero-egress. Fixed on both implementations at
once, because one guard-rail spec judges both.

The checkboxes decide what happens. The old graft path read neither of them, so
ticking or unticking either changed nothing about what was grafted. Here the
form is the input, and an unticked box posts nothing, so absence means "not this
one". That is the same rule the features panel follows.

The capability is looked up, never posted. The browser sends which components it
wants; the catalog says what capability each cultivar provides. A value the
client cannot send is a value it cannot get wrong, and `graft_sprig` checks the
name against the catalog, which doubles as the allowlist.
"""

from __future__ import annotations


from fastapi import Request

from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

__all__ = ["render_search_audio", "graft_components", "download_components", "COMPONENTS"]

# form field, cultivars to graft IN ORDER, label, caption. One row per
# component; the renderer, the graft and the download all read this, so they
# cannot disagree about which components exist.
#
# Embedding is a chain, not one graft. `minilm-onnx-inhoused` refuses to start
# without chromadb, onnxruntime and numpy, which left the base rootstock and now
# ride the vector-chroma overlay. The supervisor fails fast and says so rather
# than spawning a child that dies on import. That prerequisite is enforced at
# graft time and not declared in the catalog, so it is spelled out here. Nothing
# else knows it, which is exactly why the old one-shot graft of `mock-embedding`
# was the path of least resistance.
COMPONENTS: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("embedding", ("vector-chroma", "minilm-onnx-inhoused"), "Document Search",
     "Embedding model for document search and knowledge base queries."),
    ("whisper", ("whisper-base-ggml",), "Speech-to-Text",
     "Transcribes audio files and voice input into text."),
)



def _status(request: Request) -> dict[str, str]:
    status = getattr(request.app.state, "MODEL_DOWNLOAD_STATUS", {}) or {}
    return {key: str(status.get(key, "pending")) for key, _, _, _ in COMPONENTS}


def render_search_audio(request: Request, message: str = "") -> str:
    """Build the context; `templates/search-audio.html` decides how it looks."""
    _ = translator(request)
    state = _status(request)
    said = {"ready": _("already installed"), "downloading": _("downloading now")}
    return render(
        "search-audio.html",
        lang=lang_query(request),
        states=state,
        message=message,
        legend=_("Install local AI components for document search and audio transcription."),
        graft_label=_("Graft Sprigs"),
        for_me_label=_("for me"),
        download_label=_("Download weights"),
        rows=[
            {
                "key": key,
                "label": _(label),
                "caption": _(caption),
                "state": state[key],
                "busy": state[key] in _BUSY,
                "badge": said.get(state[key], state[key]) if state[key] != "pending" else "",
            }
            # `cultivars` rather than `_` for the discarded column. `_` is the
            # translator here, and unpacking over it would shadow it mid-loop.
            for key, cultivars, label, caption in COMPONENTS
        ],
    )

# A component is off-limits when it is already installed, and equally when its
# weights are mid-download. Both mean "do not start work on this one".
_BUSY = ("ready", "downloading")


def _selected(request: Request, form: dict) -> list[tuple[str, tuple[str, ...]]]:
    """The components the operator asked for that are free to be worked on.

    `downloading` is excluded for a reason found in review, not in theory. The
    supervisor allows exactly one cultivar per capability and prunes the
    incumbent when a new one is grafted — so a graft started while a download is
    still running gets SIGTERMed the moment the download's own sprig lands, and
    reports "exited on boot (rc=-15)" as though it had crashed.

    In the modal you could not hit this: both buttons advance out of the panel.
    At a route the page re-renders and you stay on it, so pressing one and then
    the other is the obvious thing to do. That is a failure mode this surface
    introduced, so this surface refuses it.
    """
    state = _status(request)
    return [
        (key, cultivars)
        for key, cultivars, _, _ in COMPONENTS
        if key in form and state[key] not in _BUSY
    ]


def _skipped(request: Request, form: dict) -> list[str]:
    """Asked-for components that are busy, so the reply can say why."""
    state = _status(request)
    return [
        f"{key} is {state[key]}"
        for key, _, _, _ in COMPONENTS
        if key in form and state[key] in _BUSY
    ]


async def graft_components(request: Request, user, form: dict) -> str:
    """Graft each selected cultivar through the API handler.

    Sequential rather than concurrent: each graft unpacks an OCI artifact and
    starts a child process, and the supervisor is the shared resource.

    The backend's own `detail` is what reaches the operator on failure, because
    it names the actual fix — "cultivar needs numpy, graft vector-chroma first"
    — and "Failed to graft" does not. Same rule as the Sprigs panel.
    """
    from fastapi import HTTPException

    from sage_is_ai.routers.sprigs import graft_sprig
    from sage_is_ai.sprigs.models import GraftRequest

    wanted = _selected(request, form)
    skipped = _skipped(request, form)
    if not wanted:
        return render_search_audio(
            request, "Nothing to install" + (f" — {'; '.join(skipped)}." if skipped else ".")
        )

    supervisor = request.app.state.sprig_supervisor
    done, failed = [], []
    for _, cultivars in wanted:
        for cultivar in cultivars:
            capability = (supervisor.CATALOG.get(cultivar) or {}).get("capability", "")
            try:
                await graft_sprig(
                    request, GraftRequest(name=cultivar, capability=capability), user
                )
                done.append(cultivar)
            except HTTPException as exc:
                failed.append(f"{cultivar}: {exc.detail}")
                # Stop this chain: a prerequisite that failed makes the cultivar
                # riding on it fail too, and a second error naming the same
                # cause reads as two problems.
                break
            except Exception as exc:  # noqa: BLE001 — the reason is the message
                failed.append(f"{cultivar}: {exc}")
                break

    if failed:
        return render_search_audio(request, "Failed to graft " + "; ".join(failed))
    return render_search_audio(request, f"Grafted {', '.join(done)}.")


async def download_components(request: Request, user, form: dict) -> str:
    """Start the weight download for each selected component.

    Returns as soon as the download is queued, which is what the Svelte panel
    does too — this is a ~2.5 GB fetch and nothing waits for it.
    """
    from sage_is_ai.routers.retrieval import ModelDownloadForm, trigger_model_download

    wanted = [key for key, _ in _selected(request, form)]
    skipped = _skipped(request, form)
    if not wanted:
        return render_search_audio(
            request, "Nothing to install" + (f" — {'; '.join(skipped)}." if skipped else ".")
        )

    try:
        await trigger_model_download(
            request, ModelDownloadForm(components=wanted), user
        )
    except Exception as exc:  # noqa: BLE001
        return render_search_audio(request, f"Failed to start download: {exc}")
    return render_search_audio(
        request, f"Downloading {', '.join(wanted)} in the background."
    )
