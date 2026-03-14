from __future__ import annotations

import pytest

from specanopy.parser import discover_specs, parse_spec_file

VALID_SPEC = """\
---
id: test/example
version: "1.0.0"
status: approved
depends_on:
  - contracts/api/users
---

## Example Behavior

This is the spec body.
"""

MISSING_ID_SPEC = """\
---
version: "1.0.0"
status: draft
---

Body content here.
"""


class TestParseSpecFile:
    def test_valid_spec(self, tmp_path):
        f = tmp_path / "example.spec.md"
        f.write_text(VALID_SPEC)

        node = parse_spec_file(f)
        assert node.id == "test/example"
        assert node.version == "1.0.0"
        assert node.status == "approved"
        assert node.depends_on == ["contracts/api/users"]
        assert "Example Behavior" in node.content
        assert node.hash  # non-empty

    def test_missing_required_field(self, tmp_path):
        f = tmp_path / "bad.spec.md"
        f.write_text(MISSING_ID_SPEC)

        with pytest.raises(ValueError, match="missing required frontmatter fields.*id"):
            parse_spec_file(f)

    def test_hash_changes_with_graph_shaping_frontmatter(self, tmp_path):
        body = "\n## Same body\n\nIdentical content.\n"

        f1 = tmp_path / "v1.spec.md"
        fm1 = "---\nid: a\nversion: '1.0.0'\nstatus: draft\ndepends_on:\n  - contracts/a\n---\n"
        f1.write_text(f"{fm1}{body}")

        f2 = tmp_path / "v2.spec.md"
        fm2 = "---\nid: a\nversion: '1.0.0'\nstatus: draft\ndepends_on:\n  - contracts/b\n---\n"
        f2.write_text(f"{fm2}{body}")

        assert parse_spec_file(f1).hash != parse_spec_file(f2).hash

    def test_hash_ignores_status_only(self, tmp_path):
        """Status changes should not force a rebuild on their own."""
        body = "\n## Same body\n\nIdentical content.\n"

        f1 = tmp_path / "v1.spec.md"
        f1.write_text(f"---\nid: a\nversion: '1.0.0'\nstatus: draft\n---\n{body}")

        f2 = tmp_path / "v2.spec.md"
        f2.write_text(f"---\nid: a\nversion: '1.0.0'\nstatus: approved\n---\n{body}")

        assert parse_spec_file(f1).hash == parse_spec_file(f2).hash

    def test_hash_changes_with_body(self, tmp_path):
        f1 = tmp_path / "v1.spec.md"
        f1.write_text("---\nid: a\nversion: '1.0.0'\nstatus: draft\n---\n\nBody A\n")

        f2 = tmp_path / "v2.spec.md"
        f2.write_text("---\nid: a\nversion: '1.0.0'\nstatus: draft\n---\n\nBody B\n")

        assert parse_spec_file(f1).hash != parse_spec_file(f2).hash

    def test_language_field_parsed(self, tmp_path):
        f = tmp_path / "example.spec.md"
        f.write_text(
            "---\nid: test/example\nversion: '1.0.0'\nstatus: approved\n"
            "language: typescript\n---\n\n## Body\n"
        )
        node = parse_spec_file(f)
        assert node.language == "typescript"

    def test_language_default_is_none(self, tmp_path):
        f = tmp_path / "example.spec.md"
        f.write_text("---\nid: test/example\nversion: '1.0.0'\nstatus: approved\n---\n\n## Body\n")
        node = parse_spec_file(f)
        assert node.language is None

    def test_language_change_affects_hash(self, tmp_path):
        body = "\n## Same body\n"

        f1 = tmp_path / "v1.spec.md"
        f1.write_text(f"---\nid: a\nversion: '1.0.0'\nstatus: draft\n---\n{body}")

        f2 = tmp_path / "v2.spec.md"
        f2.write_text(
            f"---\nid: a\nversion: '1.0.0'\nstatus: draft\nlanguage: typescript\n---\n{body}"
        )

        assert parse_spec_file(f1).hash != parse_spec_file(f2).hash


class TestDiscoverSpecs:
    def test_finds_nested_specs(self, tmp_path):
        (tmp_path / "behaviors" / "auth").mkdir(parents=True)
        (tmp_path / "behaviors" / "auth" / "login.spec.md").write_text(
            "---\nid: auth/login\nversion: '1.0.0'\nstatus: draft\n---\n\nLogin\n"
        )
        (tmp_path / "behaviors" / "auth" / "signup.spec.md").write_text(
            "---\nid: auth/signup\nversion: '1.0.0'\nstatus: draft\n---\n\nSignup\n"
        )

        nodes = discover_specs(tmp_path)
        ids = {n.id for n in nodes}
        assert ids == {"auth/login", "auth/signup"}

    def test_empty_dir(self, tmp_path):
        assert discover_specs(tmp_path) == []

    def test_ignores_non_spec_files(self, tmp_path):
        (tmp_path / "readme.md").write_text("# Not a spec")
        (tmp_path / "config.yaml").write_text("key: value")
        assert discover_specs(tmp_path) == []
