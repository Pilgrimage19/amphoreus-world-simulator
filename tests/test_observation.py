import copy
import unittest

from amphoreus_sim.models import Event
from amphoreus_sim.observation import build_observation, person_observation
from amphoreus_sim.simulation import Simulation


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation(42, population=100)

    def event(self, kind, year=1, *, witnesses=(), causes=(), effects=(), summary=None):
        event = Event(f"test-{len(self.sim.state.events)}", year, kind,
                      summary or f"实际记录：{kind}", causes, effects, witnesses)
        self.sim.state.events.append(event)
        return event

    def test_initial_world_has_a_phase_without_fabricated_progress(self):
        observed = build_observation(self.sim.state)
        self.assertEqual(observed["chapter"]["title"], "逐火初曙")
        self.assertEqual(observed["metrics"]["ordinary_returned"], 0)
        self.assertEqual(observed["metrics"]["active_bearers"], 1)
        self.assertIsNone(observed["recap"])
        self.assertIsNone(observed["ending"])
        self.assertEqual(len(observed["timeline"]), 1)
        self.assertEqual(observed["spotlight"][0]["name"], "缇里西庇俄丝")

    def test_old_major_events_survive_more_than_twenty_five_routine_logs(self):
        rescue = self.event("gate_rescue", witnesses=("tribios",), summary="一次实际救援")
        for _ in range(40):
            self.event("world_status", year=2)
        observed = build_observation(self.sim.state)
        self.assertIn(rescue.id, [card["id"] for card in observed["timeline"]])
        self.assertIn(rescue.id, [card["id"] for card in observed["highlights"]])
        self.assertNotIn("world_status", [card["type"] for card in observed["timeline"]])

    def test_batch_recap_uses_actual_event_boundary_not_only_event_year(self):
        self.sim.state.year = 10
        previous = self.event("region_lost", year=10)
        start = len(self.sim.state.events)
        current = self.event("gate_rescue", year=10)
        self.sim.state.year = 110
        before_population = sum(r.population for r in self.sim.state.regions.values())
        self.sim.state.regions["okhema"].population -= 12
        recap = build_observation(self.sim.state, last_advance={
            "from_year": 10, "event_index": start, "population": before_population,
        })["recap"]
        self.assertEqual(recap["from_year"], 10)
        self.assertEqual(recap["to_year"], 110)
        self.assertEqual(recap["important_count"], 1)
        self.assertEqual(recap["population_delta"], -12)
        self.assertEqual([card["id"] for card in recap["events"]], [current.id])
        self.assertNotEqual(previous.id, current.id)

    def test_empty_batch_is_honest_about_absent_major_events(self):
        start = len(self.sim.state.events)
        self.sim.state.year = 1
        self.event("world_status")
        recap = build_observation(self.sim.state, last_advance={
            "from_year": 0, "event_index": start,
            "population": sum(r.population for r in self.sim.state.regions.values()),
        })["recap"]
        self.assertEqual(recap["important_count"], 0)
        self.assertEqual(recap["events"], [])

    def test_only_real_prior_event_references_become_causal_links(self):
        past = self.event("gate_rescue")
        current = self.event("coreflame_returned", causes=(f"event:{past.id}", "event:missing", "factor:harmony"))
        future = self.event("region_lost", causes=(f"event:{current.id}",))
        # A self-reference or a future reference cannot be presented as a cause.
        changed = Event(current.id, current.year, current.type, current.summary,
                        (*current.causes, f"event:{future.id}", f"event:{current.id}"), current.effects)
        self.sim.state.events[-2] = changed
        cards = {card["id"]: card for card in build_observation(self.sim.state)["timeline"]}
        self.assertEqual(cards[current.id]["causal_event_ids"], [past.id])

    def test_related_people_are_real_deduplicated_records(self):
        self.event("gate_rescue", witnesses=("tribios", "tribios", "missing"))
        card = build_observation(self.sim.state)["timeline"][-1]
        self.assertEqual(card["people"], [{"id": "tribios", "name": "缇里西庇俄丝"}])

    def test_living_tide_does_not_average_empty_ruins_into_civilian_pressure(self):
        for region in self.sim.state.regions.values():
            region.status = "lost"
            region.black_tide = 100
        okhema = self.sim.state.regions["okhema"]
        okhema.status, okhema.black_tide = "stable", 12
        self.assertEqual(build_observation(self.sim.state)["metrics"]["living_tide"], 12)
        okhema.status = "lost"
        self.assertIsNone(build_observation(self.sim.state)["metrics"]["living_tide"])

    def test_person_journey_is_fact_based_and_does_not_match_other_ids_by_substring(self):
        person = self.sim.state.people["person-0001"]
        unrelated = self.event("gate_rescue", witnesses=("person-0010",))
        actual = self.event("golden_awakening", effects=(f"person:{person.id}:awakened",))
        journey = person_observation(person, self.sim.state)["journey"]
        self.assertEqual([card["id"] for card in journey], [actual.id])
        self.assertNotIn(unrelated.id, [card["id"] for card in journey])

    def test_attributes_distinguish_abilities_personality_and_counters(self):
        person = self.sim.state.people["tribios"]
        person.life_traces = {"betrayal": 12, "loss": 428}
        guide = person_observation(person, self.sim.state)["attribute_guide"]
        self.assertEqual(len(guide["abilities"]), 4)
        self.assertEqual(len(guide["personality"]), 7)
        self.assertNotIn("victory_choice", [trace["key"] for trace in guide["traces"]])
        self.assertIn("不代表", guide["traces"][0]["description"])
        self.assertIn("不能据此推断", guide["traces"][1]["description"])
        self.assertIn("不是某次行动的已确认动机", guide["note"])

    def test_ending_recalls_only_verified_legacy_and_refuges(self):
        story = self.sim.state.flame_stories["janus"]
        story["imprint"] = "没有归还事实的假印记"
        story["returned_event_id"] = "missing-event"
        observed = build_observation(self.sim.state, ending="collapse", ending_summary="实际文明终局")
        self.assertEqual(observed["ending"]["summary"], "实际文明终局")
        self.assertEqual(observed["ending"]["legacy"], [])
        self.assertEqual(observed["ending"]["refuge_names"], [])
        actual = self.event("coreflame_returned", witnesses=("tribios",))
        story["returned_event_id"], story["imprint"] = actual.id, "真正的印记"
        legacy = build_observation(self.sim.state, ending="collapse")["ending"]["legacy"]
        self.assertEqual(legacy, ["缇里西庇俄丝留下：真正的印记"])

    def test_ready_ending_never_claims_a_new_world_has_been_generated(self):
        observed = build_observation(self.sim.state, ending="recreation_ready")
        self.assertEqual(observed["chapter"]["title"], "再创世前夜")
        self.assertIn("下一代世界尚未生成", observed["ending"]["summary"])

    def test_observation_reads_neither_mutate_state_nor_consume_randomness(self):
        baseline = Simulation(42, population=100)
        before = self.sim.state_hash()
        original = copy.deepcopy(self.sim.state)
        for _ in range(3):
            build_observation(self.sim.state)
            person_observation(self.sim.state.people["tribios"], self.sim.state)
        self.assertEqual(self.sim.state, original)
        self.assertEqual(self.sim.state_hash(), before)
        for _ in range(8):
            self.sim.step()
            baseline.step()
        self.assertEqual(self.sim.state_hash(), baseline.state_hash())


if __name__ == "__main__":
    unittest.main()
