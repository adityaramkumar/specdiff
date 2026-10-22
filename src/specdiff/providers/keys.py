from __future__ import annotations

import os

import click


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise click.ClickException(f"{name} not set. Export it:\n\n  export {name}=your-key-here\n")
    return value
