"""CORS middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI) -> None:
    """Add CORS middleware.

    In production, replace ``allow_origins=["*"]`` with the exact frontend
    origin (e.g. ``["http://localhost:5173"]``) so cookies/credentials are
    handled correctly.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
