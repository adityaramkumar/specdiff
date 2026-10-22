from __future__ import annotations

from importlib import resources
from pathlib import Path

SKILLS_DIR = "skills"
BUILD_SKILLS = ("plan", "implement", "test", "repair", "review")
# Skill names from the previous pipeline; files with these names are no longer read.
LEGACY_SKILLS = ("architect", "interface", "implementation", "testing")


def _default(name: str) -> str | None:
    path = resources.files("specdiff") / "default_skills" / f"{name}.md"
    return path.read_text("utf-8") if path.is_file() else None


def load_skill(specs_dir: Path, skill_name: str) -> str:
    """Return .specdiff/skills/{name}.skill.md if present, else the built-in default."""
    path = specs_dir / SKILLS_DIR / f"{skill_name}.skill.md"
    if path.exists():
        return path.read_text("utf-8")
    default = _default(skill_name)
    if default is None:
        raise FileNotFoundError(
            f"Skill file not found: {path}\nCreate it at {path} to use the '{skill_name}' agent."
        )
    return default


def load_build_skills(specs_dir: Path) -> dict[str, str]:
    return {name: load_skill(specs_dir, name) for name in BUILD_SKILLS}


def legacy_skill_files(specs_dir: Path) -> list[Path]:
    """Skill files left over from the previous pipeline that no longer have any effect."""
    skills_dir = specs_dir / SKILLS_DIR
    return [p for n in LEGACY_SKILLS if (p := skills_dir / f"{n}.skill.md").exists()]
