from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import frontmatter

from specdiff.types import SpecNode


def parse_spec_file(file_path: Path) -> SpecNode:
    """Parse a .spec.md file into a SpecNode."""
    post = frontmatter.load(str(file_path))
    meta = post.metadata

    missing = [f for f in ("id", "version", "status") if f not in meta]
    if missing:
        raise ValueError(f"{file_path}: missing required frontmatter fields: {', '.join(missing)}")

    # Status is a workflow flag that changes during review, so exclude it from
    # staleness checks. The rest of the frontmatter shapes the spec graph and
    # generation inputs, so it must affect the hash.
    body = post.content
    tracked_meta = {k: v for k, v in meta.items() if k not in {"status", "hash"}}
    payload = json.dumps(
        {"meta": tracked_meta, "content": body},
        sort_keys=True,
        separators=(",", ":"),
    )
    content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    raw_depends = _string_list(meta, "depends_on", file_path)

    return SpecNode(
        id=meta["id"],
        version=str(meta["version"]),
        status=meta["status"],
        hash=content_hash,
        content=body,
        file_path=str(file_path),
        parent=meta.get("parent"),
        depends_on=raw_depends,
        language=meta.get("language"),
        acceptance=_string_list(meta, "acceptance", file_path),
        generate=_bool(meta, "generate", file_path, default=True),
    )


def _bool(meta: dict, key: str, file_path: Path, *, default: bool) -> bool:
    value = meta.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{file_path}: '{key}' must be true or false, got {value!r}")
    return value


def _string_list(meta: dict, key: str, file_path: Path) -> list[str]:
    value = meta.get(key) or []
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"{file_path}: '{key}' must be a list of strings, got {value!r}")
    return value


def discover_specs(root_dir: Path) -> list[SpecNode]:
    """Find and parse all *.spec.md files under root_dir, excluding proposed/."""
    nodes: list[SpecNode] = []
    for path in sorted(root_dir.rglob("*.spec.md")):
        if "proposed" in path.parts:
            continue
        try:
            nodes.append(parse_spec_file(path))
        except (ValueError, OSError) as exc:
            warnings.warn(f"Skipping {path}: {exc}", stacklevel=2)
    return nodes
