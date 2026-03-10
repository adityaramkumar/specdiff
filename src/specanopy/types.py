from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpecNode:
    id: str
    version: str
    status: str
    hash: str
    content: str
    file_path: str
    parent: str | None = None
    depends_on: list[str] = field(default_factory=list)


@dataclass
class HashMapEntry:
    spec_hash: str
    generated_files: list[str]
    generated_at: str

    def to_dict(self) -> dict:
        return {
            "spec_hash": self.spec_hash,
            "generated_files": self.generated_files,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> HashMapEntry:
        return cls(
            spec_hash=data["spec_hash"],
            generated_files=data["generated_files"],
            generated_at=data["generated_at"],
        )


@dataclass
class HashMap:
    nodes: dict[str, HashMapEntry] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self.nodes.items()}

    @classmethod
    def from_dict(cls, data: dict) -> HashMap:
        return cls(nodes={k: HashMapEntry.from_dict(v) for k, v in data.items()})


@dataclass
class SpecanopyConfig:
    model: str = "gemini-3.1-flash-lite-preview"
    test_command: str | None = None
    output_dir: str = "src"
    specs_dir: str = ".specanopy"
    review_before_build: bool = False


@dataclass
class ReviewResult:
    passed: bool
    feedback: str
    proposed_revision: str | None = None


@dataclass
class FilePlan:
    files: dict[str, str] = field(default_factory=dict)


@dataclass
class SwarmResult:
    file_plan: FilePlan
    generated_files: dict[str, str] = field(default_factory=dict)
    generated_tests: dict[str, str] = field(default_factory=dict)
    review_passed: bool = True
    review_feedback: str = ""
