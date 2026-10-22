"""Agents return files as tagged blocks rather than JSON strings.

Code inside JSON has to be escaped, and models get the escaping wrong often
enough to corrupt files (a `\\n` inside a string literal becomes a real line
break). Tagged blocks carry file contents verbatim:

    <file path="auth/login.py">
    ...contents...
    </file>
    <unchanged path="auth/models.py"/>
    <delete path="auth/old.py"/>
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_FILE = re.compile(r'<file path="([^"]+)">\n?(.*?)\n?</file>', re.DOTALL)
_UNCHANGED = re.compile(r'<unchanged path="([^"]+)"\s*/>')
_DELETE = re.compile(r'<delete path="([^"]+)"\s*/>')


@dataclass
class FileBlocks:
    files: dict[str, str] = field(default_factory=dict)
    unchanged: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)


def parse(text: str) -> FileBlocks:
    """Extract every <file> and <unchanged/> block from an agent's reply."""
    blocks = FileBlocks()
    for path, contents in _FILE.findall(text):
        blocks.files[path.strip()] = contents if contents.endswith("\n") else contents + "\n"
    blocks.unchanged = [p.strip() for p in _UNCHANGED.findall(text)]
    blocks.deleted = [p.strip() for p in _DELETE.findall(text)]
    return blocks


def render(files: dict[str, str]) -> str:
    """Format files the same way agents are asked to write them."""
    return "\n".join(
        f'<file path="{path}">\n{body.rstrip()}\n</file>' for path, body in files.items()
    )


FORMAT_INSTRUCTIONS = """\
Return each file as a block, with the complete file contents between the tags:

<file path="relative/path.ext">
complete contents
</file>

Paths are relative to the output directory. Write file contents verbatim: no
markdown fences, no escaping. To keep one of this spec's existing files exactly
as it is, write <unchanged path="relative/path.ext"/> instead of repeating it.
"""
