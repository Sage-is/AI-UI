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


class UiScriptingGrantRequest(BaseModel):
    """An admin's per-Sprig decision to let one ui-Sprig™ carry script.

    `name` is required even when revoking. Revoking by name means an admin
    cannot clear a grant they were not looking at, and it keeps the request
    honest about which Sprig it concerns.
    """

    name: str
    allow: bool


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


class WireRequest(BaseModel):
    """An admin supplying wires for one grafted Sprig™.

    `values` is free-form on the wire and validated against the catalog
    declaration in `sprigs/wiring.validate` — the CATALOG is the authority, so
    an undeclared name is refused rather than stored. A partial submission is a
    merge, and an empty `secret` means "keep what is stored" rather than "erase
    it", so a form that cannot render a secret cannot destroy one either.
    """

    name: str
    values: dict = {}
