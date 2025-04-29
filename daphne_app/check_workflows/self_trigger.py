"""
Shim that re-exports the check() function implemented in
config_workflows.self_trigger so the CLI import works.
"""

from daphne_app.config_workflows.self_trigger import check  # noqa: F401

__all__ = ["check"]
