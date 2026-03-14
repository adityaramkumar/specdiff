from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from specdiff.types import HashMap, HashMapEntry

HASH_MAP_FILE = "hash-map.json"


def load(specs_dir: Path) -> HashMap:
    """Load the hash map from disk. Returns empty HashMap if file is missing."""
    path = specs_dir / HASH_MAP_FILE
    if not path.exists():
        return HashMap()
    data = json.loads(path.read_text("utf-8"))
    return HashMap.from_dict(data)


def save(specs_dir: Path, map: HashMap) -> None:
    """Atomically write the hash map: write to .tmp then os.replace()."""
    path = specs_dir / HASH_MAP_FILE
    tmp_path = specs_dir / f"{HASH_MAP_FILE}.tmp"
    specs_dir.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(json.dumps(map.to_dict(), indent=2) + "\n", "utf-8")
    os.replace(tmp_path, path)


def is_stale(map: HashMap, node_id: str, current_hash: str) -> bool:
    """True if the node is missing from the map or its hash has changed."""
    entry = map.nodes.get(node_id)
    if entry is None:
        return True
    return entry.spec_hash != current_hash


def update(map: HashMap, node_id: str, hash: str, generated_files: list[str]) -> None:
    """Upsert a hash map entry with the current timestamp."""
    map.nodes[node_id] = HashMapEntry(
        spec_hash=hash,
        generated_files=generated_files,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
