"""Small dependency-free local web viewer for the annual simulation."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse

from .models import EndingKind
from .simulation import Simulation


STATIC_DIR = Path(__file__).with_name("web")


class WorldServer(ThreadingHTTPServer):
    """HTTP server that owns one interactive, deterministic world instance."""

    def __init__(self, address: tuple[str, int], seed: int, population: int) -> None:
        super().__init__(address, WorldRequestHandler)
        self.seed = seed
        self.population = population
        self.simulation = Simulation(seed=seed, population=population)
        self.ending: EndingKind | None = None
        self.ending_summary: str | None = None
        self._world_lock = RLock()

    def snapshot(self) -> dict[str, object]:
        with self._world_lock:
            snapshot = self.simulation.world_snapshot()
            snapshot["seed"] = self.seed
            snapshot["ended"] = self.ending is not None
            snapshot["ending"] = self.ending.value if self.ending is not None else None
            snapshot["ending_summary"] = self.ending_summary
            return snapshot

    def advance(self, years: int = 1) -> None:
        """Advance only while this interactive world has not reached an ending."""
        with self._world_lock:
            for _ in range(years):
                if self.ending is not None:
                    break
                ending = self.simulation.step()
                if ending is not None:
                    self.ending = ending
                    self.ending_summary = next(
                        (
                            event.summary
                            for event in reversed(self.simulation.state.events)
                            if event.type == ending.value
                        ),
                        self.simulation._ending_summary(ending),
                    )

    def reset(self, seed: int | None = None) -> None:
        with self._world_lock:
            self.seed = self.seed if seed is None else seed
            self.simulation = Simulation(seed=self.seed, population=self.population)
            self.ending = None
            self.ending_summary = None

    def person_detail(self, person_id: str) -> dict[str, object] | None:
        person = self.simulation.state.people.get(person_id)
        if person is None:
            return None
        detail = person.snapshot()
        detail["region_name"] = self.simulation.state.regions[person.region_id].name
        detail["titan_relations"] = [
            {
                "id": titan_id,
                "name": self.simulation.state.titans[titan_id].name,
                "domain": self.simulation.state.titans[titan_id].domain,
                "stance": stance,
            }
            for titan_id, stance in sorted(person.titan_stances.items(), key=lambda item: (-item[1], item[0]))
            if titan_id in self.simulation.state.titans
        ]
        organization = self.simulation.state.organizations.get(person.organization_id or "")
        detail["organization"] = organization.snapshot() if organization else None
        detail["parents"] = [
            {"id": parent_id, "name": self.simulation.state.people[parent_id].name}
            for parent_id in person.parent_ids if parent_id in self.simulation.state.people
        ]
        detail["relationship_details"] = [
            {**relation.snapshot(), "target_name": self.simulation.state.people[relation.target_id].name}
            for relation in person.relations.values() if relation.target_id in self.simulation.state.people
        ]
        return detail


class WorldRequestHandler(BaseHTTPRequestHandler):
    server: WorldServer

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path
        if path == "/api/state":
            self._json(self.server.snapshot())
        elif path.startswith("/api/person/"):
            detail = self.server.person_detail(path.rsplit("/", 1)[-1])
            if detail is None:
                self.send_error(HTTPStatus.NOT_FOUND)
            else:
                self._json(detail)
        elif path in ("/", "/index.html"):
            self._file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/app.js":
            self._file(STATIC_DIR / "app.js", "text/javascript; charset=utf-8")
        elif path == "/style.css":
            self._file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path
        if path == "/api/step":
            self.server.advance()
            self._json(self.server.snapshot())
        elif path == "/api/advance":
            years = self._body().get("years", 10)
            years = years if isinstance(years, int) else 10
            self.server.advance(max(1, min(100, years)))
            self._json(self.server.snapshot())
        elif path == "/api/reset":
            body = self._body()
            self.server.reset(body.get("seed"))
            self._json(self.server.snapshot())
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return {}

    def _json(self, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _file(self, path: Path, content_type: str) -> None:
        encoded = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format: str, *_args: object) -> None:
        """Keep ordinary browser polling out of the user's terminal."""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Amphoreus observation panel.")
    parser.add_argument("--seed", type=int, default=20260905)
    parser.add_argument("--population", type=int, default=1000)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = WorldServer(("127.0.0.1", args.port), args.seed, args.population)
    print(f"翁法罗斯观察面板已启动：http://127.0.0.1:{args.port}")
    print("按 Ctrl+C 停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n观察面板已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
