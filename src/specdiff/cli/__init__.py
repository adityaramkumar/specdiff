"""Specdiff command line. Each command lives in the module for its area."""

from __future__ import annotations

import click
from dotenv import load_dotenv

from specdiff.cli.build_cmd import build
from specdiff.cli.info_cmds import impact, status, validate
from specdiff.cli.project_cmds import clean, extract, init, skill, ui
from specdiff.cli.review_cmd import review


@click.group()
def cli() -> None:
    """Specdiff — spec-driven code generation."""
    load_dotenv()


for command in (build, status, validate, impact, review, ui, init, skill, clean, extract):
    cli.add_command(command)
