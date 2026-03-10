from __future__ import annotations

import hashlib
from pathlib import Path

import frontmatter

from specanopy.types import SpecNode


def parse_spec_file(file_path: Path) -> SpecNode:
    """Parse a .spec.md file into a SpecNode."""
    post = frontmatter.load(str(file_path))
    meta = post.metadata

    missing = [f for f in ("id", "version", "status") if f not in meta]
    if missing:
        raise ValueError(
            f"{file_path}: missing required frontmatter fields: {', '.join(missing)}"
        )

    # Hash the body only — NOT the frontmatter. The frontmatter contains the
    # hash field itself and mutable metadata like status, so including it would
    # create a circular dependency (changing status would change the hash, which
    # would change the frontmatter, which would change the hash again).
    body = post.content
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    return SpecNode(
        id=meta["id"],
        version=str(meta["version"]),
        status=meta["status"],
        hash=content_hash,
        content=body,
        file_path=str(file_path),
        parent=meta.get("parent"),
        depends_on=meta.get("depends_on", []),
    )


def discover_specs(root_dir: Path) -> list[SpecNode]:
    """Find and parse all *.spec.md files under root_dir."""
    nodes: list[SpecNode] = []
    for path in sorted(root_dir.rglob("*.spec.md")):
        nodes.append(parse_spec_file(path))
    return nodes
