"""Placeholder OpenAPI tool endpoints for try.sage trial mode.

Each endpoint advertises an "advanced capability" via OpenAPI metadata so an
LLM can see the tool exists and surface it as a suggestion, but every call
returns a structured "not available in trial" response. The mounted router is
auto-registered into ``TOOL_SERVER_CONNECTIONS`` by
``utils.try_sage_tool_servers`` so the agent runtime discovers it like any
external OpenAPI tool server.
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sage_is_ai.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


# Single response shape so the LLM-side schema is consistent across every
# preview endpoint and clients can branch on `status` alone.
class TrialUnavailableResponse(BaseModel):
    status: str = Field(
        "not_available_in_try_mode",
        description="Sentinel status indicating the tool is preview-only.",
    )
    message: str = Field(
        ...,
        description="Human-readable explanation suitable to surface to the user.",
    )


_PREVIEW_TAG = "preview"
_PREVIEW_NOTE = (
    "Preview / advanced capability — not available in the try.sage trial. "
    "Calls return a structured placeholder response."
)


############################
# Web Search (preview)
############################


class WebSearchDemoRequest(BaseModel):
    query: str = Field(..., description="Free-text search query.")


@router.post(
    "/web_search_demo",
    response_model=TrialUnavailableResponse,
    summary="Web search (preview, not available in trial)",
    description=_PREVIEW_NOTE,
    tags=[_PREVIEW_TAG],
)
async def web_search_demo(payload: WebSearchDemoRequest) -> TrialUnavailableResponse:
    return TrialUnavailableResponse(
        message="Web search is a preview capability and is not available in the try.sage trial.",
    )


############################
# Internal Knowledge Base (preview)
############################


class InternalKbDemoRequest(BaseModel):
    query: str = Field(..., description="Question to ask the internal KB.")
    top_k: int = Field(5, ge=1, le=50, description="Maximum results to consider.")


@router.post(
    "/internal_kb_demo",
    response_model=TrialUnavailableResponse,
    summary="Internal knowledge base lookup (preview, not available in trial)",
    description=_PREVIEW_NOTE,
    tags=[_PREVIEW_TAG],
)
async def internal_kb_demo(payload: InternalKbDemoRequest) -> TrialUnavailableResponse:
    return TrialUnavailableResponse(
        message="Internal knowledge base lookup is a preview capability and is not available in the try.sage trial.",
    )


############################
# Code Runner (preview)
############################


class CodeRunnerDemoRequest(BaseModel):
    language: str = Field(..., description="Programming language identifier.")
    code: str = Field(..., description="Source code to execute.")


@router.post(
    "/code_runner_demo",
    response_model=TrialUnavailableResponse,
    summary="Sandboxed code execution (preview, not available in trial)",
    description=_PREVIEW_NOTE,
    tags=[_PREVIEW_TAG],
)
async def code_runner_demo(payload: CodeRunnerDemoRequest) -> TrialUnavailableResponse:
    return TrialUnavailableResponse(
        message="Sandboxed code execution is a preview capability and is not available in the try.sage trial.",
    )
