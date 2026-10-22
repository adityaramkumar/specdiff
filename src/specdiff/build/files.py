from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from specdiff.types import SpecNode

BACKUP_DIR = ".backup"
HEADER_KEY = "generated_from"
# "agent" was written by older versions.
_HEADER_KEYS = {HEADER_KEY, "spec_hash", "generated_at", "agent"}

_LINE_COMMENT = {".js": "//", ".jsx": "//", ".ts": "//", ".tsx": "//", ".java": "//",
                 ".go": "//", ".rs": "//", ".c": "//", ".cc": "//", ".cpp": "//"}  # fmt: skip
_BLOCK_COMMENT = {".css": ("/*", "*/"), ".scss": ("/*", "*/"), ".less": ("/*", "*/"),
                  ".sql": ("/*", "*/"), ".html": ("<!--", "-->"), ".xml": ("<!--", "-->"),
                  ".svg": ("<!--", "-->"), ".md": ("<!--", "-->")}  # fmt: skip
_BLOCK_END = {start: end for start, end in _BLOCK_COMMENT.values()}
# Formats with no comment syntax get no header.
_NO_HEADER = {".json"}


def resolve_output_path(output_dir: str, rel_path: str) -> Path:
    """Join an agent-supplied path onto output_dir, rejecting anything that escapes it."""
    root = Path(output_dir).resolve()
    if not (root / rel_path).resolve().is_relative_to(root):
        raise ValueError(f"Generated path {rel_path!r} escapes output_dir {output_dir!r}.")
    return Path(output_dir) / rel_path


def traceability_header(path: Path, node: SpecNode) -> str:
    """Comment lines naming the spec a file was generated from. Empty if the format has none."""
    ext = path.suffix.lower()
    if ext in _NO_HEADER:
        return ""
    metadata = {
        HEADER_KEY: node.id,
        "spec_hash": node.hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if ext in _BLOCK_COMMENT:
        start, end = _BLOCK_COMMENT[ext]
        return "\n".join([start, *(f"  {k}: {v}" for k, v in metadata.items()), end]) + "\n"
    prefix = _LINE_COMMENT.get(ext, "#")
    return "\n".join(f"{prefix} {k}: {v}" for k, v in metadata.items()) + "\n"


def strip_header(text: str) -> str:
    """Remove a traceability header so agents see, and re-emit, only the code."""
    lines = text.split("\n")
    if lines and HEADER_KEY in lines[0]:
        prefix = lines[0].split(" ", 1)[0] + " "
        n = next(
            (
                i
                for i, line in enumerate(lines)
                if not line.startswith(prefix)
                or line[len(prefix) :].split(":", 1)[0] not in _HEADER_KEYS
            ),
            len(lines),
        )
    elif len(lines) > 1 and HEADER_KEY in lines[1]:
        end = _BLOCK_END.get(lines[0].strip())
        n = next((i + 1 for i, line in enumerate(lines) if line.strip() == end), 0)
    else:
        return text
    return "\n".join(lines[n:])


def _backup_path(backup_root: Path, rel: str) -> Path:
    path = Path(rel)
    return backup_root / path.relative_to(path.anchor) if path.is_absolute() else backup_root / path


def backup(files: list[str], specs_dir: Path) -> None:
    """Copy existing files into .specdiff/.backup/ before they are overwritten or deleted.

    A file that already has a backup keeps it, so the backup always holds the original.
    """
    backup_root = specs_dir / BACKUP_DIR
    for rel in files:
        src = Path(rel)
        dest = _backup_path(backup_root, rel)
        if not src.exists() or dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def restore(files: list[str], specs_dir: Path) -> None:
    """Put backed-up files back and delete files that had no backup (they were new)."""
    backup_root = specs_dir / BACKUP_DIR
    for rel in files:
        backed = _backup_path(backup_root, rel)
        if not backed.exists():
            Path(rel).unlink(missing_ok=True)
            continue
        dest = Path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backed, dest)
    clean_backups(specs_dir)


def clean_backups(specs_dir: Path) -> None:
    backup_root = specs_dir / BACKUP_DIR
    if backup_root.exists():
        shutil.rmtree(backup_root)


class NodeWriter:
    """Writes one node's files to disk, remembering every path it touched so it can undo."""

    def __init__(self, node: SpecNode, output_dir: str, specs_dir: Path, previous: list[str]):
        self.node = node
        self.output_dir = output_dir
        self.specs_dir = specs_dir
        self.previous = previous
        self.touched: set[str] = set()

    def sync(self, files: dict[str, str]) -> list[str]:
        """Make the node's files on disk exactly `files`. Returns the written paths."""
        out = self.output_dir
        targets = {str(resolve_output_path(out, rel)): body for rel, body in files.items()}
        removed = [p for p in [*self.previous, *self.touched] if p not in targets]
        # Only a path's first touch is backed up: later syncs would otherwise save this
        # node's own output as the "original" and rollback would restore it.
        backup([p for p in [*targets, *removed] if p not in self.touched], self.specs_dir)
        self.touched.update(targets)
        self.touched.update(removed)
        for path in removed:
            Path(path).unlink(missing_ok=True)
        for path, body in targets.items():
            dest = Path(path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(traceability_header(dest, self.node) + body, "utf-8")
        return list(targets)

    def rollback(self) -> None:
        restore(sorted(self.touched), self.specs_dir)

    def commit(self) -> None:
        clean_backups(self.specs_dir)
