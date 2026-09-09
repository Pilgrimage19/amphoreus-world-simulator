import unittest

from amphoreus_sim.web import WorldServer


class WorldServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = WorldServer(("127.0.0.1", 0), seed=42, population=100)
        self.addCleanup(self.server.server_close)

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


if __name__ == "__main__":
    unittest.main()
