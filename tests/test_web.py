from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from html.parser import HTMLParser
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
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, str, bytes]:
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        body = raw_body if raw_body is not None else (json.dumps(payload).encode("utf-8") if payload is not None else None)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        headers.update(extra_headers or {})
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

    def test_growing_history_lists_are_accessible_internal_scroll_regions(self) -> None:
        class ListParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.elements = {}

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if attributes.get("id"):
                    self.elements[attributes["id"]] = attributes

        _, _, body = self.request("GET", "/")
        parser = ListParser()
        parser.feed(body.decode("utf-8"))
        for list_id in ("flame-stories", "organizations", "events", "crises", "refuge-crises", "archive"):
            with self.subTest(list_id=list_id):
                attributes = parser.elements[list_id]
                self.assertIn("scroll-list", attributes.get("class", "").split())
                self.assertEqual(attributes.get("tabindex"), "0")
                self.assertEqual(attributes.get("role"), "region")
                self.assertTrue(attributes.get("aria-label"))
        _, _, stylesheet = self.request("GET", "/style.css")
        css = stylesheet.decode("utf-8")
        self.assertIn("max-height:clamp(16rem,45vh,28rem)", css)
        self.assertIn("overflow-y:auto", css)
        self.assertIn("overscroll-behavior-y:contain", css)
        self.assertIn(".scroll-list:focus-visible", css)

    def test_http_advance_is_bounded_to_one_through_one_hundred_years(self) -> None:
        status, _, body = self.request("POST", "/api/advance", {"years": 0})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["year"], 1)

        self.server.reset()
        status, _, body = self.request("POST", "/api/advance", {"years": 1000})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["year"], 100)

    def test_hundred_year_button_is_served_and_advances_a_full_century(self) -> None:
        _, _, html = self.request("GET", "/")
        self.assertIn('<button id="advance-century">推进 100 年</button>', html.decode("utf-8"))
        _, _, script = self.request("GET", "/app.js")
        javascript = script.decode("utf-8")
        self.assertIn('byId("advance-century").addEventListener("click"', javascript)
        self.assertIn('body: JSON.stringify({years: 100})', javascript)
        self.assertIn('["step", "advance", "advance-century"]', javascript)
        self.assertIn('byId(id).disabled = actionInFlight || ended', javascript)
        status, _, body = self.request("POST", "/api/advance", {"years": 100})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["year"], 100)

    def test_hundred_year_advance_stops_at_an_ending(self) -> None:
        for region in self.server.simulation.state.regions.values():
            region.status = "lost"
        status, _, body = self.request("POST", "/api/advance", {"years": 100})
        state = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(state["year"], 1)
        self.assertTrue(state["ended"])
        status, _, body = self.request("POST", "/api/advance", {"years": 100})
        self.assertEqual(json.loads(body)["year"], 1)

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
        self.assertIn("journey", detail)
        self.assertEqual(len(detail["attribute_guide"]["abilities"]), 4)

        self.assertEqual(self.request("GET", "/api/person/not-found")[0], 404)
        self.assertEqual(self.request("GET", "/not-found")[0], 404)
        self.assertEqual(self.request("POST", "/not-found", {})[0], 404)

    def test_concurrent_advances_are_serialized_without_lost_years(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda _: self.server.advance(2), range(8)))
        self.assertEqual(self.server.snapshot()["year"], 16)

    def test_observation_recap_tracks_a_real_batch_and_reset_clears_it(self) -> None:
        self.assertIsNone(self.server.snapshot()["observation"]["recap"])
        status, _, body = self.request("POST", "/api/advance", {"years": 10})
        self.assertEqual(status, 200)
        recap = json.loads(body)["observation"]["recap"]
        self.assertEqual((recap["from_year"], recap["to_year"]), (0, 10))
        self.assertEqual(self.server.snapshot()["observation"]["recap"], recap)
        self.server.reset(seed=7)
        self.assertIsNone(self.server.snapshot()["observation"]["recap"])

    def test_concurrent_batch_snapshots_belong_to_their_own_advance(self) -> None:
        with ThreadPoolExecutor(max_workers=4) as executor:
            snapshots = list(executor.map(lambda _: self.server.advance_snapshot(2), range(4)))
        self.assertEqual(sorted(snapshot["year"] for snapshot in snapshots), [2, 4, 6, 8])
        for snapshot in snapshots:
            recap = snapshot["observation"]["recap"]
            self.assertEqual(recap["to_year"], snapshot["year"])
            self.assertEqual(recap["to_year"] - recap["from_year"], 2)

    def test_compact_view_preserves_full_archive_and_on_demand_person_details(self) -> None:
        for person in self.server.simulation.state.people.values():
            if person.id != "tribios":
                person.alive = False
                person.golden_status = "awakened"
        before = self.server.simulation.state_hash()
        _, _, full_body = self.request("GET", "/api/state")
        _, _, compact_body = self.request("GET", "/api/state", extra_headers={"X-Amphoreus-View": "compact"})
        full, compact = json.loads(full_body), json.loads(compact_body)
        self.assertGreater(len(full["historical_archive"]), len(compact["historical_archive"]))
        for field in ("factor_paths", "titans", "regions", "observation", "population"):
            self.assertEqual(full[field], compact[field])
        omitted = next(key for key in full["historical_archive"] if key not in compact["historical_archive"])
        status, _, body = self.request("GET", f"/api/person/{omitted}")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["id"], omitted)
        self.assertEqual(self.server.simulation.state_hash(), before)
        self.assertLess(len(compact_body), len(full_body))


if __name__ == "__main__":
    unittest.main()
