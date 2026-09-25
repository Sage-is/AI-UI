---
title: "Documentation Index"
description: "Guide to active project docs and the historical archive layout."
date: 2026-04-09
tags:
  - docs
  - index
  - navigation
---

# Documentation Index

This directory now separates active reference material from historical audits, plans, and retrospectives.

## Start Here

- [release-runbook.md](release-runbook.md) — `make ship`, what preflight refuses, and how to recover from a half-finished release
- [try-sage-deployment.md](try-sage-deployment.md) — try.sage.is, the demo box: persona magic links, the 24-hour wipe and reset, and production deployment
- [development-workflow.md](development-workflow.md) — gates, hooks, verification steps, and daily workflow
- [product-stack.md](product-stack.md) — architecture and product stack overview
- [bridges.md](bridges.md) — WhatsApp, Telegram, Signal, and Email bridge setup
- [SECURITY.md](SECURITY.md) — security posture and reporting notes
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution process and expectations
- [troubleshooting.md](troubleshooting.md) — common local and deployment issues

## Active Reference Docs

- [API-examples.md](API-examples.md) — API usage examples (older; some routes predate the current API, check against `/docs` on your instance)
- [api-refactoring-plan.md](api-refactoring-plan.md) — the 2025 API cleanup plan, kept for history
- [backend-rewrite-research.md](backend-rewrite-research.md) — backend rewrite options and research notes
- [community-hub.md](community-hub.md) — Community Hub product and integration notes
- [env-scripts.md](env-scripts.md) — helper scripts and environment setup details
- [knowledge-ingestion-modes-plan.md](knowledge-ingestion-modes-plan.md) — current ingestion-mode planning for documents
- [completed-todos.md](completed-todos.md) — completed roadmap items and stale-task audit trail

## Archive

Historical docs now live under `archive/`.

- `archive/audits/` — dated codebase audits
- `archive/roadmaps/` — superseded roadmaps and strategic snapshots
- `archive/docker/` — completed Docker optimization plans and summaries
- `archive/fixes/` — point-in-time fix writeups
- `archive/plans/` — completed or superseded implementation plans

See `archive/README.md` for a simple map of what moved.
