from __future__ import annotations

import pytest

from specdiff.skills import BUILD_SKILLS, legacy_skill_files, load_build_skills, load_skill


class TestLoadSkill:
    def test_user_file_overrides_builtin(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "implement.skill.md").write_text("Custom rules.\n")
        assert load_skill(tmp_path, "implement") == "Custom rules.\n"

    def test_builtin_used_when_no_override(self, tmp_path):
        assert "implementation stage" in load_skill(tmp_path, "implement")

    def test_every_build_skill_and_spec_eval_has_a_builtin(self, tmp_path):
        assert set(load_build_skills(tmp_path)) == set(BUILD_SKILLS)
        assert "spec quality reviewer" in load_skill(tmp_path, "spec-eval")

    def test_unknown_skill_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Skill file not found"):
            load_skill(tmp_path, "nonexistent")


class TestLegacySkills:
    def test_reports_files_from_previous_pipeline(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        for name in ("architect", "implementation", "review"):
            (skills / f"{name}.skill.md").write_text("x")
        assert [p.name for p in legacy_skill_files(tmp_path)] == [
            "architect.skill.md",
            "implementation.skill.md",
        ]
