"""Expose bibs to an ASGI server through the application factory.

Run with uvicorn; backend behavior lives in src and importing this entry point
only constructs process-local application state, without network model calls."""

from fastapi import FastAPI

from src.api.bootstrap import create_app

app = create_app()
