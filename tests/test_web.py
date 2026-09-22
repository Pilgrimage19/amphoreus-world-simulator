from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
import json
from threading import Thread
import unittest

from amphoreus_sim.web import WorldServer


class WorldServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = WorldServer(("127.0.0.1", 0), seed=42, population=100)
        self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server_thread.join(timeout=5)
        self.server.server_close()

    def request(
        self,
        method: str,
        path: str,
        payload: object | None = None,
        *,
        raw_body: bytes | None = None,
    ) -> tuple[int, str, bytes]:
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        body = raw_body if raw_body is not None else (json.dumps(payload).encode("utf-8") if payload is not None else None)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        response_body = response.read()
        content_type = response.getheader("Content-Type", "")
        status = response.status
        connection.close()
        return status, content_type, response_body

    def test_all_lost_regions_end_the_world_and_stop_batch_advance(self) -> None:
        for region in self.server.simulation.state.regions.values():
            region.status = "lost"
            region.black_tide = 100
            region.population = 100
            region.collapse_years = 8

        self.server.advance(10)
        snapshot = self.server.snapshot()

        self.assertEqual(snapshot["year"], 1)
        self.assertTrue(snapshot["ended"])
        self.assertEqual(snapshot["ending"], "collapse")
        self.assertGreater(snapshot["population"]["total_civilians"], 0)
        self.assertIn("所有城邦均已失陷", snapshot["ending_summary"])

        event_count = len(self.server.simulation.state.events)
        self.server.advance(10)
        self.assertEqual(self.server.simulation.state.year, 1)
        self.assertEqual(len(self.server.simulation.state.events), event_count)

    def test_reset_clears_the_persisted_ending(self) -> None:
        for region in self.server.simulation.state.regions.values():
            region.population = 0
        self.server.advance()
        self.assertTrue(self.server.snapshot()["ended"])

        self.server.reset(seed=7)
        snapshot = self.server.snapshot()

        self.assertEqual(snapshot["seed"], 7)
        self.assertEqual(snapshot["year"], 0)
        self.assertFalse(snapshot["ended"])
        self.assertIsNone(snapshot["ending"])
        self.assertIsNone(snapshot["ending_summary"])

    def test_state_and_static_assets_are_served_over_http(self) -> None:
        status, content_type, body = self.request("GET", "/api/state")
        state = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("application/json", content_type)
        self.assertEqual(state["seed"], 42)
        self.assertEqual(state["year"], 0)

        for path, expected_type, marker in (
            ("/", "text/html", "世界观察"),
            ("/app.js", "text/javascript", "function render"),
            ("/style.css", "text/css", ".view-tabs"),
        ):
            status, content_type, body = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertIn(expected_type, content_type)
            self.assertIn(marker, body.decode("utf-8"))

    def test_http_step_advance_and_reset_have_consistent_snapshots(self) -> None:
        status, _, body = self.request("POST", "/api/step")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["year"], 1)

        status, _, body = self.request("POST", "/api/advance", {"years": 3})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["year"], 4)

        status, _, body = self.request("POST", "/api/reset", {"seed": 7})
        reset_state = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(reset_state["seed"], 7)
        self.assertEqual(reset_state["year"], 0)
        self.assertFalse(reset_state["ended"])

    def test_http_advance_is_bounded_to_one_through_one_hundred_years(self) -> None:
        status, _, body = self.request("POST", "/api/advance", {"years": 0})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["year"], 1)

        self.server.reset()
        status, _, body = self.request("POST", "/api/advance", {"years": 1000})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["year"], 100)

    def test_invalid_json_and_field_types_return_json_errors_without_advancing(self) -> None:
        cases = (
            ("/api/advance", b"{"),
            ("/api/advance", b"[]"),
            ("/api/advance", json.dumps({"years": "ten"}).encode("utf-8")),
            ("/api/advance", json.dumps({"years": True}).encode("utf-8")),
            ("/api/reset", json.dumps({"seed": "seven"}).encode("utf-8")),
        )
        for path, raw_body in cases:
            with self.subTest(path=path, body=raw_body):
                status, content_type, body = self.request("POST", path, raw_body=raw_body)
                self.assertEqual(status, 400)
                self.assertIn("application/json", content_type)
                self.assertIn("error", json.loads(body))
                self.assertEqual(self.server.snapshot()["year"], 0)
                self.assertEqual(self.server.snapshot()["seed"], 42)

    def test_person_detail_and_missing_routes_have_expected_http_status(self) -> None:
        status, _, body = self.request("GET", "/api/person/tribios")
        detail = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(detail["id"], "tribios")
        self.assertIn("region_name", detail)
        self.assertEqual(detail["origin_region_name"], "雅努萨波利斯")
        self.assertIn("relationship_details", detail)

        self.assertEqual(self.request("GET", "/api/person/not-found")[0], 404)
        self.assertEqual(self.request("GET", "/not-found")[0], 404)
        self.assertEqual(self.request("POST", "/not-found", {})[0], 404)

    def test_concurrent_advances_are_serialized_without_lost_years(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda _: self.server.advance(2), range(8)))
        self.assertEqual(self.server.snapshot()["year"], 16)


if __name__ == "__main__":
    unittest.main()
