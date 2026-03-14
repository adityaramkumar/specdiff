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


class TestIsStale:
    def test_new_node(self):
        m = HashMap()
        assert hashmap.is_stale(m, "new/node", "somehash") is True

    def test_changed_hash(self):
        m = HashMap(
            nodes={
                "a": HashMapEntry(spec_hash="old", generated_files=[], generated_at=""),
            }
        )
        assert hashmap.is_stale(m, "a", "new") is True

    def test_current(self):
        m = HashMap(
            nodes={
                "a": HashMapEntry(spec_hash="same", generated_files=[], generated_at=""),
            }
        )
        assert hashmap.is_stale(m, "a", "same") is False


class TestUpdate:
    def test_upsert(self):
        m = HashMap()
        hashmap.update(m, "a", "h1", ["f1.py"])
        assert m.nodes["a"].spec_hash == "h1"

        hashmap.update(m, "a", "h2", ["f2.py"])
        assert m.nodes["a"].spec_hash == "h2"
        assert m.nodes["a"].generated_files == ["f2.py"]
