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


class GraftRequest(BaseModel):
    name: str = "mock-embedding"
    capability: str = "embedding"


class GraftResponse(BaseModel):
    status: bool
    name: str
    capability: str
    base_url: str
    embedding_engine: str
    embedding_model: str
    warning: Optional[str] = None
