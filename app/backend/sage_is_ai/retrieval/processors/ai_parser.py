"""
AI Document Parser — LLM post-processing for extracted text.

Takes raw text from any extraction engine and reformats it through
a chosen LLM for better markdown structure, table reconstruction,
and artifact removal before chunking/embedding.
"""

import json
import logging
import textwrap

from starlette.datastructures import Headers
from starlette.requests import Request

from sage_is_ai.utils.chat import generate_chat_completion

log = logging.getLogger(__name__)

DEFAULT_AI_PARSE_PROMPT = textwrap.dedent("""\
    You are a document formatting assistant. Take the following raw text extracted \
    from a PDF and reorganize it into clean, well-structured Markdown. Preserve all \
    factual content exactly. Apply these rules:
    - Add appropriate heading levels (# ## ###) based on document structure
    - Format tables as proper Markdown tables
    - Convert bullet points and numbered lists to proper Markdown lists
    - Remove page headers/footers, page numbers, and extraction artifacts
    - Preserve code blocks with proper fencing
    - Clean up broken words from line breaks
    - Keep all citations and references intact
    Output ONLY the reformatted content, no commentary.""")


def _chunk_text(text: str, max_chunk_size: int) -> list[str]:
    """Split text into page-sized chunks for LLM processing.

    Splits on double newlines (page/paragraph boundaries) first,
    then falls back to single newlines if chunks are still too large.
    """
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    current = ""

    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 > max_chunk_size:
            if current:
                chunks.append(current.strip())
            # If a single paragraph exceeds max_chunk_size, split on newlines
            if len(paragraph) > max_chunk_size:
                lines = paragraph.split("\n")
                current = ""
                for line in lines:
                    if len(current) + len(line) + 1 > max_chunk_size:
                        if current:
                            chunks.append(current.strip())
                        current = line
                    else:
                        current = f"{current}\n{line}" if current else line
            else:
                current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph

    if current.strip():
        chunks.append(current.strip())

    return chunks


async def ai_parse_content(
    app,
    raw_text: str,
    model_id: str,
    prompt: str,
    user,
    chunk_before_llm: bool = True,
    max_chunk_size: int = 4000,
) -> str:
    """Post-process extracted text through an LLM for better formatting.

    Args:
        app: The FastAPI application instance (for model access).
        raw_text: Raw text extracted from a document.
        model_id: LLM model ID to use for processing.
        prompt: System prompt instructing the LLM how to reformat.
        user: User object for auth context.
        chunk_before_llm: Split large docs into chunks before processing.
        max_chunk_size: Max characters per chunk sent to LLM.

    Returns:
        Reformatted text (markdown).
    """
    if not raw_text or not raw_text.strip():
        return raw_text

    if not model_id:
        log.warning("AI parse requested but no model configured, returning raw text")
        return raw_text

    if chunk_before_llm:
        chunks = _chunk_text(raw_text, max_chunk_size)
    else:
        chunks = [raw_text]

    log.info(
        f"AI parsing document: {len(raw_text)} chars, "
        f"{len(chunks)} chunk(s), model={model_id}"
    )

    processed_chunks = []
    for i, chunk in enumerate(chunks):
        try:
            result = await _call_llm(app, model_id, prompt, chunk, user)
            processed_chunks.append(result)
        except Exception as e:
            log.error(f"AI parse failed on chunk {i+1}/{len(chunks)}: {e}")
            # Fall back to raw chunk on error
            processed_chunks.append(chunk)

    return "\n\n".join(processed_chunks)


async def _call_llm(
    app,
    model_id: str,
    system_prompt: str,
    content: str,
    user,
) -> str:
    """Make a single LLM call using the existing chat completion pipeline."""
    mock_request = Request(
        scope={
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "method": "POST",
            "path": "/api/chat/completions",
            "query_string": b"",
            "headers": Headers({}).raw,
            "client": ("127.0.0.1", 0),
            "server": ("127.0.0.1", 80),
            "scheme": "http",
            "app": app,
        }
    )

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "stream": False,
        "metadata": {
            "task": "ai_document_parse",
        },
    }

    response = await generate_chat_completion(
        request=mock_request,
        form_data=payload,
        user=user,
        bypass_filter=True,
    )

    # Extract text from response (same pattern as bridges/pipeline.py)
    if hasattr(response, "body"):
        body = response.body
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        data = json.loads(body)
        if "choices" in data and data["choices"]:
            return data["choices"][0].get("message", {}).get("content", "")
    elif isinstance(response, dict):
        if "choices" in response and response["choices"]:
            return response["choices"][0].get("message", {}).get("content", "")

    log.warning("Empty LLM response during AI parse, returning original content")
    return content
