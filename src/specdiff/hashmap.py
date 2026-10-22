from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import click

from specdiff.types import HashMap, HashMapEntry

HASH_MAP_FILE = "hash-map.json"


def load(specs_dir: Path) -> HashMap:
    """Load the hash map from disk. Returns empty HashMap if file is missing."""
    path = specs_dir / HASH_MAP_FILE
    if not path.exists():
        return HashMap()
    try:
        data = json.loads(path.read_text("utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(
            f"hash-map.json is corrupt: {exc}\n"
            "Delete .specdiff/hash-map.json and run `specdiff build` to regenerate."
        ) from exc
    return HashMap.from_dict(data)


def save(specs_dir: Path, hm: HashMap) -> None:
    """Atomically write the hash map: write to .tmp then os.replace()."""
    path = specs_dir / HASH_MAP_FILE
    tmp_path = specs_dir / f"{HASH_MAP_FILE}.tmp"
    specs_dir.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(json.dumps(hm.to_dict(), indent=2) + "\n", "utf-8")
    os.replace(tmp_path, path)


def is_stale(hm: HashMap, node_id: str, current_hash: str) -> bool:
    """True if the node is missing from the map or its hash has changed."""
    entry = hm.nodes.get(node_id)
    if entry is None:
        return True
    return entry.spec_hash != current_hash


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update(hm: HashMap, node_id: str, spec_hash: str, generated_files: list[str]) -> None:
    """Upsert a hash map entry, recording the current content hash of each generated file."""
    hm.nodes[node_id] = HashMapEntry(
        spec_hash=spec_hash,
        generated_files=generated_files,
        generated_at=datetime.now(timezone.utc).isoformat(),
        output_hashes={f: file_hash(Path(f)) for f in generated_files if Path(f).exists()},
    )


def modified_files(entry: HashMapEntry) -> list[str]:
    """Generated files whose contents changed on disk since they were written."""
    return [
        f
        for f, recorded in entry.output_hashes.items()
        if Path(f).exists() and file_hash(Path(f)) != recorded
    ]
