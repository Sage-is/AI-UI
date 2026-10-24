"""Sage.is AI-UI backend package.

Kept empty on purpose. Every process imports this file first: the app server,
each Sprig™ child server (``python -m sage_is_ai.sprigs.*``) and every gate.
The container starts uvicorn directly (``start.sh``), so the package carries no
command-line entry point; the typer CLI that once lived here, and the rich and
pygments it pulled in, left the image in 3.2.1.
"""
