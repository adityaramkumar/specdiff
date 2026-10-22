from __future__ import annotations

from pathlib import Path

import yaml

from specdiff.types import SpecdiffConfig


def load_config(specs_dir: Path) -> SpecdiffConfig:
    """Read .specdiff/config.yaml, falling back to defaults for missing fields."""
    config_path = specs_dir / "config.yaml"
    if not config_path.exists():
        return SpecdiffConfig()
    raw = yaml.safe_load(config_path.read_text("utf-8")) or {}
    return SpecdiffConfig(
        model=raw.get("model", SpecdiffConfig.model),
        test_command=raw.get("test_command"),
        output_dir=raw.get("output_dir", SpecdiffConfig.output_dir),
        specs_dir=raw.get("specs_dir", SpecdiffConfig.specs_dir),
        review_before_build=raw.get("review_before_build", False),
        language=raw.get("language", SpecdiffConfig.language),
        test_framework=raw.get("test_framework"),
        check_command=raw.get("check_command"),
        acceptance_command=raw.get("acceptance_command"),
        max_retries=raw.get("max_retries", SpecdiffConfig.max_retries),
    )
