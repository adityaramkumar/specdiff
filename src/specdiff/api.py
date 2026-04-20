from __future__ import annotations

import json
import logging
import os
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

from specdiff import hashmap
from specdiff.graph import build_graph, impact_summary
from specdiff.parser import discover_specs

logger = logging.getLogger(__name__)


def _get_graph_data(specs_dir: Path) -> dict[str, Any]:
    """Extract graph data and format it as JSON for the UI."""
    map_data = hashmap.load(specs_dir)
    nodes = discover_specs(specs_dir)
    graph = build_graph(nodes)

    stale_ids = [n.id for n in nodes if hashmap.is_stale(map_data, n.id, n.hash)]
    # Pre-compute impact for stale specs to get cascade depths
    impact = impact_summary(graph, stale_ids) if stale_ids else {"downstream": {}}
    downstream_depths = impact.get("downstream", {})

    payload_nodes = []
    payload_edges = []

    for node in nodes:
        entry = map_data.nodes.get(node.id)
        if entry is None:
            status = "new"
        elif entry.spec_hash != node.hash:
            status = "stale"
        else:
            status = "current"

        payload_nodes.append(
            {
                "id": node.id,
                "version": node.version,
                "status": status,
                "approval_status": node.status,
                "content": node.content,
                "file_path": node.file_path,
                "depends_on": node.depends_on,
                "cascade_depth": downstream_depths.get(node.id, 0),
            }
        )

        for dep_id in node.depends_on:
            payload_edges.append(
                {
                    "source": dep_id,
                    "target": node.id,
                }
            )

    return {
        "nodes": payload_nodes,
        "edges": payload_edges,
    }


class GraphUIHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler that serves the frontend and a /api/graph endpoint."""

    def __init__(self, *args, directory=None, specs_dir=None, **kwargs):
        self.specs_dir = specs_dir
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        if self.path == "/api/graph":
            try:
                data = _get_graph_data(self.specs_dir)
                body = json.dumps(data).encode("utf-8")
                self.send_response(200)
            except Exception as e:
                body = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)

            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        # Fallback to serving static files (e.g. index.html) for React Router
        path_in_dir = Path(self.directory) / self.path.lstrip("/")
        if not path_in_dir.exists() and self.path != "/":
            self.path = "/index.html"

        return super().do_GET()


def serve_ui(specs_dir: Path, port: int = 8000, open_browser: bool = True):
    """Start local web server for the Specdiff UI."""

    # We will bundle the compiled UI into src/specdiff/ui_dist
    ui_dist_dir = Path(__file__).parent / "ui_dist"

    if not ui_dist_dir.exists():
        os.makedirs(ui_dist_dir, exist_ok=True)
        placeholder = (
            "<html><body><h1>Specdiff UI not built yet.</h1>"
            "<p>Run npm run build in the ui/ directory.</p></body></html>"
        )
        (ui_dist_dir / "index.html").write_text(placeholder)

    def handler(*args, **kwargs):
        return GraphUIHandler(*args, directory=str(ui_dist_dir), specs_dir=specs_dir, **kwargs)

    httpd = HTTPServer(("0.0.0.0", port), handler)
    url = f"http://localhost:{port}"

    print(f"Starting Specdiff Graph UI Server at {url}")
    print(f"Serving API from {specs_dir} specs and static files from {ui_dist_dir}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Specdiff UI Server.")
        httpd.server_close()
