import unittest

from amphoreus_sim.audit import run_audit


class AuditTests(unittest.TestCase):
    def test_short_audit_has_structured_fire_and_anomaly_results(self) -> None:
        report = run_audit(seed=42, ticks=2, population=100)

        self.assertEqual(report["seed"], 42)
        self.assertIn("janus", report["fire_journeys"])
        self.assertIsInstance(report["lost_regions"], list)
        self.assertIsInstance(report["reason_milestones"], list)
        self.assertEqual(report["anomalies"], [])


if __name__ == "__main__":
    unittest.main()
