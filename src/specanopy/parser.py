from __future__ import annotations

import hashlib
import json
from pathlib import Path

import frontmatter

from specanopy.types import SpecNode


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

    return SpecNode(
        id=meta["id"],
        version=str(meta["version"]),
        status=meta["status"],
        hash=content_hash,
        content=body,
        file_path=str(file_path),
        parent=meta.get("parent"),
        depends_on=meta.get("depends_on", []),
        language=meta.get("language"),
    )


def discover_specs(root_dir: Path) -> list[SpecNode]:
    """Find and parse all *.spec.md files under root_dir."""
    nodes: list[SpecNode] = []
    for path in sorted(root_dir.rglob("*.spec.md")):
        nodes.append(parse_spec_file(path))
    return nodes
