"""Expose the HTTP application factory for bibs.

Application setup lives in bootstrap; routes and schemas define the HTTP interface."""

from src.api.bootstrap import create_app
