from __future__ import annotations

import json
import threading
import urllib.request
from functools import partial
from http.server import HTTPServer

import pytest

from specdiff.api import GraphUIHandler, _get_graph_data


def _spec(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def specs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / ".specdiff"
    _spec(
        root / "constitution.spec.md",
        "---\nid: constitution\nversion: '1'\nstatus: approved\ngenerate: false\n---\nRules.\n",
    )
    _spec(root / "users.spec.md", "---\nid: users\nversion: '1'\nstatus: approved\n---\nUsers.\n")
    _spec(root / "login.spec.md",
          "---\nid: login\nversion: '1'\nstatus: draft\nparent: constitution\ndepends_on:\n"
          "  - users\nacceptance:\n  - tests/test_login.py\n---\nLogin.\n")  # fmt: skip
    return root


def test_graph_payload(specs):
    data = _get_graph_data(specs)
    nodes = {n["id"]: n for n in data["nodes"]}

    assert nodes["constitution"]["status"] == "context"
    assert nodes["login"]["status"] == "new"
    assert nodes["login"]["approval_status"] == "draft"
    assert nodes["login"]["acceptance"] == ["tests/test_login.py"]
    assert nodes["users"]["cascade_depth"] == 1
    assert sorted((e["source"], e["target"], e["kind"]) for e in data["edges"]) == [
        ("constitution", "login", "parent"),
        ("users", "login", "depends_on"),
    ]


@pytest.fixture
def server(specs, tmp_path):
    ui_dir = tmp_path / "no-ui-build"
    ui_dir.mkdir()
    httpd = HTTPServer(
        ("127.0.0.1", 0), partial(GraphUIHandler, directory=str(ui_dir), specs_dir=specs)
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", ui_dir
    httpd.shutdown()
    httpd.server_close()


def test_api_endpoint_serves_json_without_wildcard_cors(server):
    url, _ = server
    with urllib.request.urlopen(f"{url}/api/graph") as resp:
        assert resp.headers.get("Access-Control-Allow-Origin") is None
        assert {n["id"] for n in json.load(resp)["nodes"]} == {"constitution", "users", "login"}


def test_missing_ui_build_serves_placeholder_without_writing_files(server):
    url, ui_dir = server
    with urllib.request.urlopen(f"{url}/") as resp:
        assert "UI not built yet" in resp.read().decode()
    assert list(ui_dir.iterdir()) == []


def test_unknown_paths_fall_back_to_index(server):
    url, ui_dir = server
    (ui_dir / "index.html").write_text("<html>app</html>")
    with urllib.request.urlopen(f"{url}/some/client/route?x=1") as resp:
        assert resp.read().decode() == "<html>app</html>"
