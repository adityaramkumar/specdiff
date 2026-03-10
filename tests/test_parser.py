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

    def test_hash_stability(self, tmp_path):
        """Same body produces the same hash regardless of frontmatter changes."""
        body = "\n## Same body\n\nIdentical content.\n"

        f1 = tmp_path / "v1.spec.md"
        f1.write_text(f"---\nid: a\nversion: '1.0.0'\nstatus: draft\n---\n{body}")

        f2 = tmp_path / "v2.spec.md"
        f2.write_text(f"---\nid: a\nversion: '2.0.0'\nstatus: approved\n---\n{body}")

        assert parse_spec_file(f1).hash == parse_spec_file(f2).hash

    def test_hash_changes_with_body(self, tmp_path):
        f1 = tmp_path / "v1.spec.md"
        f1.write_text("---\nid: a\nversion: '1.0.0'\nstatus: draft\n---\n\nBody A\n")

        f2 = tmp_path / "v2.spec.md"
        f2.write_text("---\nid: a\nversion: '1.0.0'\nstatus: draft\n---\n\nBody B\n")

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
