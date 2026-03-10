from __future__ import annotations

import pytest

from specanopy.skills import discover_skills, load_skill


class TestLoadSkill:
    def test_load_existing(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "spec-eval.skill.md").write_text("## Role\nYou review specs.\n")

        content = load_skill(tmp_path, "spec-eval")
        assert "You review specs" in content

    def test_load_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Skill file not found"):
            load_skill(tmp_path, "nonexistent")


class TestDiscoverSkills:
    def test_finds_multiple(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "spec-eval.skill.md").write_text("spec eval content")
        (skills / "impl.skill.md").write_text("impl content")

        result = discover_skills(tmp_path)
        assert set(result.keys()) == {"spec-eval", "impl"}
        assert "spec eval content" in result["spec-eval"]

    def test_empty_dir(self, tmp_path):
        assert discover_skills(tmp_path) == {}
