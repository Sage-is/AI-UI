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

from html import escape as e

from fastapi import Request

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

_ROW_S = ("--d:flex; --ai:center; --g:.75rem; --p:.7rem; --br:.6rem; "
          "--b:1px solid var(--line); --m:0 0 .5rem; --cur:pointer")
_NAME_S = "--size:.85rem; --weight:500"
_CAPTION_S = "--size:.7rem; --op:.7; --d:block"
_STATE_S = "--size:.6rem; --weight:500; --tt:uppercase; --ml:.35rem"


def _status(request: Request) -> dict[str, str]:
    status = getattr(request.app.state, "MODEL_DOWNLOAD_STATUS", {}) or {}
    return {key: str(status.get(key, "pending")) for key, _, _, _ in COMPONENTS}


def _row(key: str, label: str, caption: str, state: str) -> str:
    # A busy component cannot be selected: ready means there is nothing to do,
    # downloading means starting a graft would race the download and lose.
    busy = state in _BUSY
    attrs = " disabled" if busy else " checked"
    # "installed" and "downloading" rather than the raw state word: a disabled
    # checkbox beside a badge reading "ready" reads as a bug, because the reader
    # has to infer that ready is WHY they cannot tick it.
    said = {"ready": "already installed", "downloading": "downloading now"}.get(state, state)
    badge = (
        f'<small data-state="{e(state, quote=True)}" style="{_STATE_S}">{e(said)}</small>'
        if state != "pending"
        else ""
    )
    return (
        f'<label style="{_ROW_S}">'
        f'<input data-cy="search-audio-{e(key, quote=True)}" type="checkbox" '
        f'name="{e(key, quote=True)}" value="1"{attrs} />'
        f'<span><span style="{_NAME_S}">{e(label)}</span>{badge}'
        f'<small style="{_CAPTION_S}">{e(caption)}</small></span></label>'
    )


def render_search_audio(request: Request, message: str = "") -> str:
    state = _status(request)
    rows = "".join(_row(k, lb, cp, state[k]) for k, _, lb, cp in COMPONENTS)
    note = (
        f'<output data-cy="search-audio-result" style="--size:.8rem; --op:.75">{e(message)}</output>'
        if message
        else ""
    )
    attrs = " ".join(
        f'data-{k}-status="{e(v, quote=True)}"' for k, v in state.items()
    )
    # Two submit buttons, one form: the operator's choice of components is the
    # same either way, and only the verb differs. `formaction` is the element
    # that already means that, so there is no second copy of the checkboxes.
    return f"""
<section data-cy="search-audio-panel" {attrs}>
  <form method="post" action="/pages/admin/setup/search-audio/graft">
    <fieldset style="--b:0; --p:0; --m:0">
      <legend style="--size:.85rem; --weight:600; --p:0">
        Install local AI components for document search and audio transcription.
      </legend>
      {rows}
    </fieldset>
    <button data-cy="search-audio-graft" type="submit"
            style="--p:.45rem 1rem; --br:999px; --b:1px solid var(--line); --cur:pointer">
      Graft Sprigs&trade; for me
    </button>
    <button data-cy="search-audio-download" type="submit"
            formaction="/pages/admin/setup/search-audio/download"
            style="--p:.45rem 1rem; --br:999px; --b:1px solid var(--line); --cur:pointer; --ml:.5rem">
      Download weights
    </button>
    {note}
  </form>
</section>
"""


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
