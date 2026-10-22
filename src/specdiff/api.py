from __future__ import annotations

import json
import logging
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

from specdiff import hashmap
from specdiff.config import load_config
from specdiff.graph import build_graph, impact_summary
from specdiff.parser import discover_specs
from specdiff.plan import compute_states, skills_hash

logger = logging.getLogger(__name__)


def _get_graph_data(specs_dir: Path) -> dict[str, Any]:
    """Extract graph data and format it as JSON for the UI."""
    map_data = hashmap.load(specs_dir)
    nodes = discover_specs(specs_dir)
    graph = build_graph(nodes)
    states = compute_states(graph, map_data, load_config(specs_dir), skills_hash(specs_dir))

    payload_nodes = []
    payload_edges = []

    for node in nodes:
        state = states[node.id]
        payload_nodes.append(
            {
                "id": node.id,
                "version": node.version,
                "status": state.label,
                "stale_reasons": state.reasons,
                "approval_status": node.status,
                "content": node.content,
                "file_path": node.file_path,
                "depends_on": node.depends_on,
                "parent": node.parent,
                "acceptance": node.acceptance,
                # Rebuilds triggered downstream if this spec changes.
                "cascade_depth": impact_summary(graph, [node.id])["cascade_depth"],
            }
        )

        for dep_id in node.depends_on:
            payload_edges.append({"source": dep_id, "target": node.id, "kind": "depends_on"})
        if node.parent:
            payload_edges.append({"source": node.parent, "target": node.id, "kind": "parent"})

    return {
        "nodes": payload_nodes,
        "edges": payload_edges,
    }


# Shown when running from a source checkout where the UI has not been built.
PLACEHOLDER = (
    "<html><body><h1>Specdiff UI not built yet.</h1>"
    "<p>Run <code>npm ci && npm run build</code> in the ui/ directory. "
    "The graph data is available at <a href='/api/graph'>/api/graph</a>.</p></body></html>"
)


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
            self.end_headers()
            self.wfile.write(body)
            return

        if not (Path(self.directory) / "index.html").exists():
            body = PLACEHOLDER.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(body)
            return

        # Unknown paths get index.html so the single-page app can handle them.
        path_in_dir = Path(self.directory) / self.path.split("?", 1)[0].lstrip("/")
        if not path_in_dir.exists() and self.path != "/":
            self.path = "/index.html"

        return super().do_GET()


def serve_ui(specs_dir: Path, port: int = 8000, open_browser: bool = True):
    """Start local web server for the Specdiff UI."""

    ui_dist_dir = Path(__file__).parent / "ui_dist"

    def handler(*args, **kwargs):
        return GraphUIHandler(*args, directory=str(ui_dist_dir), specs_dir=specs_dir, **kwargs)

    httpd = HTTPServer(("127.0.0.1", port), handler)
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
