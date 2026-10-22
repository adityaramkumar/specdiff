from __future__ import annotations

import json

from specdiff import hashmap
from specdiff.types import HashMap, HashMapEntry


class TestLoad:
    def test_missing_file(self, tmp_path):
        result = hashmap.load(tmp_path)
        assert result.nodes == {}

    def test_existing_file(self, tmp_path):
        data = json.dumps(
            {
                "node/a": {
                    "spec_hash": "abc",
                    "generated_files": ["f.py"],
                    "generated_at": "2025-01-01T00:00:00Z",
                }
            }
        )
        (tmp_path / "hash-map.json").write_text(data)
        result = hashmap.load(tmp_path)
        assert "node/a" in result.nodes
        assert result.nodes["node/a"].spec_hash == "abc"


class TestSave:
    def test_roundtrip(self, tmp_path):
        m = HashMap(
            nodes={
                "x": HashMapEntry(
                    spec_hash="h1",
                    generated_files=["a.py", "b.py"],
                    generated_at="2025-01-01T00:00:00Z",
                ),
            }
        )
        hashmap.save(tmp_path, m)
        loaded = hashmap.load(tmp_path)

        assert loaded.nodes["x"].spec_hash == "h1"
        assert loaded.nodes["x"].generated_files == ["a.py", "b.py"]

    def test_atomic_no_tmp_remains(self, tmp_path):
        m = HashMap()
        hashmap.save(tmp_path, m)
        files = list(tmp_path.iterdir())
        names = {f.name for f in files}
        assert "hash-map.json" in names
        assert "hash-map.json.tmp" not in names


class TestUpdate:
    def test_upsert(self):
        m = HashMap()
        hashmap.update(m, "a", "h1", ["f1.py"])
        assert m.nodes["a"].spec_hash == "h1"

        hashmap.update(m, "a", "h2", ["f2.py"])
        assert m.nodes["a"].spec_hash == "h2"
        assert m.nodes["a"].generated_files == ["f2.py"]


class TestOutputHashes:
    def test_update_records_hash_of_each_existing_file(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x = 1\n")
        m = HashMap()
        hashmap.update(m, "n", "h", [str(f), str(tmp_path / "missing.py")])
        assert m.nodes["n"].output_hashes == {str(f): hashmap.file_hash(f)}

    def test_modified_files_detects_edits_only(self, tmp_path):
        edited, untouched, deleted = (tmp_path / n for n in ("e.py", "u.py", "d.py"))
        for f in (edited, untouched, deleted):
            f.write_text("orig\n")
        m = HashMap()
        hashmap.update(m, "n", "h", [str(edited), str(untouched), str(deleted)])
        edited.write_text("changed\n")
        deleted.unlink()
        assert hashmap.modified_files(m.nodes["n"]) == [str(edited)]

    def test_entries_without_output_hashes_load(self):
        entry = HashMapEntry.from_dict(
            {"spec_hash": "h", "generated_files": [], "generated_at": ""}
        )
        assert entry.output_hashes == {}
        assert hashmap.modified_files(entry) == []
