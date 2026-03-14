from __future__ import annotations

from pathlib import Path

SKILLS_DIR = "skills"


def load_skill(specs_dir: Path, skill_name: str) -> str:
    """Load a skill file by name from .specdiff/skills/{name}.skill.md."""
    path = specs_dir / SKILLS_DIR / f"{skill_name}.skill.md"
    if not path.exists():
        raise FileNotFoundError(
            f"Skill file not found: {path}\nCreate it at {path} to use the '{skill_name}' agent."
        )
    return path.read_text("utf-8")


def discover_skills(specs_dir: Path) -> dict[str, str]:
    """Find all *.skill.md files and return {name: content}."""
    skills_path = specs_dir / SKILLS_DIR
    if not skills_path.exists():
        return {}
    return {
        p.stem.removesuffix(".skill"): p.read_text("utf-8")
        for p in sorted(skills_path.glob("*.skill.md"))
    }
