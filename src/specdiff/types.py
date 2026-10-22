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
    language: str | None = None


@dataclass
class HashMapEntry:
    spec_hash: str
    generated_files: list[str]
    generated_at: str
    # SHA-256 of each generated file as written, used to detect hand edits.
    output_hashes: dict[str, str] = field(default_factory=dict)
    # Everything the build depended on (see plan.compute_states); empty for legacy maps.
    inputs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "spec_hash": self.spec_hash,
            "generated_files": self.generated_files,
            "generated_at": self.generated_at,
            "output_hashes": self.output_hashes,
            "inputs": self.inputs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> HashMapEntry:
        return cls(
            spec_hash=data["spec_hash"],
            generated_files=data["generated_files"],
            generated_at=data["generated_at"],
            output_hashes=data.get("output_hashes", {}),
            inputs=data.get("inputs", {}),
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
class SpecdiffConfig:
    model: str = "gemini-2.5-flash"
    test_command: str | None = None
    output_dir: str = "src"
    specs_dir: str = ".specdiff"
    review_before_build: bool = False
    language: str = "python"
    test_framework: str | None = None
    max_retries: int = 2

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("model must be a non-empty string")
        if not self.output_dir:
            raise ValueError("output_dir must be a non-empty string")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")


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
