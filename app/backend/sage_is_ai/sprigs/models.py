"""Dataclasses and API schemas for the Sprig™ grafting subsystem."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel


@dataclass
class SprigHandle:
    """Runtime handle for a grafted Sprig™ (one local child process)."""

    name: str
    capability: str
    port: int
    base_url: str
    health_url: str
    model: str
    process: Optional[asyncio.subprocess.Process] = None
    # Explicit state for non-process ("deliver") sprigs; otherwise derived from
    # the child process's liveness in handles().
    state: Optional[str] = None


class GraftRequest(BaseModel):
    name: str = "mock-embedding"
    capability: str = "embedding"


class PruneRequest(BaseModel):
    name: str


class GraftResponse(BaseModel):
    status: bool
    name: str
    capability: str
    base_url: Optional[str] = None
    embedding_engine: Optional[str] = None
    embedding_model: Optional[str] = None
    reranking_engine: Optional[str] = None
    reranking_model: Optional[str] = None
    warning: Optional[str] = None
    delivered: Optional[bool] = None
