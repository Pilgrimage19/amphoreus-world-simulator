import unittest
from unittest.mock import Mock

from amphoreus_sim.flamechase import ORDINARY_FIRES
from amphoreus_sim.models import EndingKind, Factor, Relation
from amphoreus_sim.simulation import Simulation


class FlamechaseTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation(42, population=100)

    def candidate(self, index, factor, special=None):
        person = self.sim.state.people[f"person-{index:04d}"]
        person.age, person.golden_status, person.region_id = 25, "awakened", "okhema"
        person.factors = {key: 20 for key in Factor}
        person.factors[factor] = 100
        person.special_role = special
        return person

    def test_terminal_step_is_idempotent(self):
        for region in self.sim.state.regions.values():
            region.status = "lost"
        self.assertEqual(self.sim.step(), EndingKind.COLLAPSE)
        before = self.sim.state_hash()
        self.assertEqual(self.sim.step(), EndingKind.COLLAPSE)
        self.assertEqual(before, self.sim.state_hash())

    def test_trial_progress_does_not_transfer_between_candidates(self):
        first = self.candidate(1, Factor.ORDER)
        second = self.candidate(2, Factor.ORDER)
        titan = self.sim.state.titans["talanton"]
        self.sim._advance_person_trial(titan, first, 96)
        self.sim._advance_person_trial(titan, second, 8)
        self.assertEqual(titan.trial_progress, 8)
        self.assertEqual(first.trial_evidence["talanton_progress"], 96)

    def test_return_is_recorded_once_and_no_longer_inherits(self):
        person = self.candidate(1, Factor.ORDER)
        titan = self.sim.state.titans["talanton"]
        self.sim._inherit_coreflame(titan, person, "测试裁断")
        self.sim._return_coreflame(titan, person, "测试献祭")
        self.sim._return_coreflame(titan, person, "重复归还")
        returns = [e for e in self.sim.state.events if "coreflame:talanton:returned" in e.effects]
        self.assertEqual(len(returns), 1)
        with self.assertRaises(ValueError):
            self.sim._inherit_coreflame(titan, person, "错误承接")

    def test_reason_does_not_claim_an_untaught_demigod(self):
        teacher = self.candidate(1, Factor.ERUDITION)
        candidate = self.candidate(2, Factor.ORDER)
        self.sim._inherit_coreflame(self.sim.state.titans["cerces"], teacher, "四证")
        self.sim._inherit_coreflame(self.sim.state.titans["talanton"], candidate, "裁断")
        self.assertEqual(self.sim.state.titans["cerces"].authority_state.get("created_demigod_ids", []), [])

    def test_reason_training_does_not_erase_an_ocean_trial_already_started(self):
        candidate = self.candidate(1, Factor.NIHILITY)
        candidate.region_id, candidate.empathy = "styxia", 30
        region = self.sim.state.regions["styxia"]
        region.black_tide = 30
        self.sim.state.year = 50
        self.sim._record_ocean_passage(candidate, region, "aid")
        candidate.empathy = 60
        self.assertTrue(self.sim._is_ocean_candidate(candidate))
        for _ in range(4):
            self.sim._record_ocean_passage(candidate, region, "aid")
        self.assertEqual(candidate.trial_evidence["phagousa"], 5)
        outsider = self.candidate(2, Factor.NIHILITY)
        outsider.empathy = 60
        self.assertFalse(self.sim._is_ocean_candidate(outsider))

    def test_romance_requires_mutual_and_distinct_bonds(self):
        candidate = self.candidate(1, Factor.BEAUTY)
        self.sim.state.year = 50
        region = self.sim.state.regions["okhema"]
        region.black_tide = 40
        candidate.relations.clear()
        for index in (2, 3, 4):
            target = self.candidate(index, Factor.ORDER)
            candidate.relations[target.id] = Relation(target.id, "友人", 80)
            target.relations[candidate.id] = Relation(candidate.id, "友人", 60)
        for _ in range(4):
            self.sim._record_romance_weaving(candidate, region, "aid")
        self.assertEqual(candidate.trial_evidence["mnestia"], 3)
        self.assertEqual(len([m for m in candidate.memories if m.startswith("mnestia_wove:")]), 3)

    def test_death_calls_highest_talent_and_requires_a_voluntary_bond(self):
        candidate = self.candidate(1, Factor.EQUILIBRIUM)
        self.candidate(2, Factor.EQUILIBRIUM).factors[Factor.EQUILIBRIUM] = 90
        candidate.relations.clear()
        for year in (51, 54, 57):
            self.sim.state.year = year
            self.sim._resolve_death_trial()
        titan = self.sim.state.titans["thanatos"]
        self.assertEqual(titan.authority_state["candidate_id"], candidate.id)
        self.assertEqual(len(titan.authority_state["curse_victim_ids"]), 3)
        self.assertEqual(titan.coreflame_status, "within_titan")
        companion = self.candidate(3, Factor.ORDER)
        companion.courage = companion.willpower = 80
        candidate.relations[companion.id] = Relation(companion.id, "友人", 70)
        companion.relations[candidate.id] = Relation(candidate.id, "友人", 70)
        self.sim._resolve_death_trial()
        self.assertEqual(titan.coreflame_holder, candidate.id)
        self.assertEqual(companion.relations[candidate.id].oath, "渡厄之心")

    def test_death_guides_each_soul_once_and_returns_at_population_threshold(self):
        holder = self.candidate(1, Factor.EQUILIBRIUM)
        titan = self.sim.state.titans["thanatos"]
        self.sim._inherit_coreflame(titan, holder, "冥河试炼")
        self.sim.state.pending_souls = 12
        self.sim._resolve_death_authority()
        self.sim._resolve_death_authority()
        self.assertEqual(self.sim.state.ferried_souls, 12)
        for region in self.sim.state.regions.values():
            region.population = 100
        self.sim.state.year = 5
        self.sim._resolve_death_authority()
        self.assertEqual(titan.coreflame_status, "returned")
        self.assertFalse(holder.alive)

    def test_equal_death_talent_does_not_reset_a_called_candidates_trial(self):
        candidate = self.candidate(1, Factor.EQUILIBRIUM)
        self.sim.state.year = 51
        self.sim._resolve_death_trial()
        rival = self.candidate(2, Factor.EQUILIBRIUM)
        self.sim.state.year = 54
        self.sim._resolve_death_trial()
        titan = self.sim.state.titans["thanatos"]
        self.assertEqual(titan.authority_state["candidate_id"], candidate.id)
        self.assertEqual(len(titan.authority_state["curse_victim_ids"]), 2)
        self.assertTrue(rival.alive)

    def test_strife_has_a_lethal_failure_and_a_real_victory(self):
        candidate = self.candidate(1, Factor.HUNT)
        candidate.courage = candidate.body = 100
        self.sim.state.year = 50
        self.sim.random = Mock()
        self.sim.random.get.return_value.random.return_value = 1.0
        self.sim._resolve_strife_trial()
        self.assertFalse(candidate.alive)
        successor = self.candidate(2, Factor.HUNT)
        successor.courage = successor.body = 100
        self.sim.state.year = 55
        self.sim.random.get.return_value.random.return_value = 0.0
        self.sim._resolve_strife_trial()
        self.assertEqual(self.sim.state.titans["nikador"].coreflame_holder, successor.id)

    def test_strife_refuge_conserves_population_and_does_not_revive_ruins(self):
        holder = self.candidate(1, Factor.HUNT)
        titan = self.sim.state.titans["nikador"]
        self.sim._inherit_coreflame(titan, holder, "击碎神躯")
        titan.authority_state["journey_years"] = 4
        self.sim.state.regions["swordpeak"].status = "lost"
        before = sum(r.population for r in self.sim.state.regions.values())
        self.sim._resolve_strife_authority()
        self.assertEqual(sum(r.population for r in self.sim.state.regions.values()), before)
        self.assertEqual(self.sim.state.regions["swordpeak"].status, "lost")
        self.assertGreater(self.sim.state.regions["nikador_refuge_swordpeak"].population, 0)
        self.assertLessEqual(len(self.sim._residents("swordpeak")), self.sim.state.regions["swordpeak"].population)
        for _ in range(5):
            self.sim._resolve_strife_authority()
        self.assertEqual(sum(r.population for r in self.sim.state.regions.values()), before)
        self.assertEqual(len(titan.authority_state["refuge_ids"]), 1)

    def test_strife_travel_into_an_empty_ruin_accounts_for_the_holder(self):
        holder = self.candidate(1, Factor.HUNT)
        titan = self.sim.state.titans["nikador"]
        self.sim._inherit_coreflame(titan, holder, "击碎神躯")
        titan.authority_state["journey_years"] = 4
        ruin = self.sim.state.regions["skyward"]
        ruin.status, ruin.population = "lost", 0
        for person in self.sim._residents(ruin.id):
            person.region_id = "okhema"
        before = sum(r.population for r in self.sim.state.regions.values())
        self.sim._resolve_strife_authority()
        self.assertEqual(ruin.population, 1)
        self.assertEqual(len(self.sim._residents(ruin.id)), 1)
        self.assertEqual(sum(r.population for r in self.sim.state.regions.values()), before)

    def test_special_trials_reject_a_high_factor_without_special_destiny(self):
        self.candidate(1, Factor.REMEMBRANCE)
        self.sim.state.flame_stories.update({key: {} for key in ("aquila", "georios")})
        for _ in range(20):
            self.sim._resolve_time_trial()
        self.assertEqual(self.sim.state.titans["oronyx"].coreflame_status, "within_titan")

    def test_special_destiny_requires_both_the_factor_tail_and_independent_judgment(self):
        candidate = self.candidate(1, Factor.REMEMBRANCE)
        self.sim.random = Mock()
        rng = self.sim.random.get.return_value
        rng.randrange.side_effect = [0, 1]
        rng.randint.return_value = 98
        self.sim._seed_special_role(candidate)
        self.assertEqual(candidate.factors[Factor.REMEMBRANCE], 98)
        self.assertIsNone(candidate.special_role)
        rng.randrange.side_effect = [0, 0]
        self.sim._seed_special_role(candidate)
        self.assertEqual(candidate.special_role, "unblemished_soul")

    def test_time_candidate_completes_three_questions_in_fifteen_years(self):
        candidate = self.candidate(1, Factor.REMEMBRANCE, "unblemished_soul")
        self.sim.state.flame_stories.update({key: {} for key in ("aquila", "georios")})
        for year in range(1, 16):
            self.sim.state.year = year
            self.sim._resolve_time_trial()
        self.assertEqual(self.sim.state.titans["oronyx"].coreflame_holder, candidate.id)

    def test_worldbearer_requires_crisis_choices_and_five_preceding_fires(self):
        candidate = self.candidate(1, Factor.DESTRUCTION, "perfect_vessel")
        region = self.sim.state.regions["okhema"]
        self.sim._record_worldbearing(candidate, region, "aid")
        self.assertNotIn("kephale_burdens", candidate.trial_evidence)
        region.black_tide = 40
        for _ in range(10):
            self.sim._record_worldbearing(candidate, region, "aid")
        self.sim._resolve_worldbearing_trial()
        self.assertEqual(self.sim.state.titans["kephale"].coreflame_status, "within_titan")
        for index, key in enumerate(("aquila", "georios", "talanton", "mnestia"), 2):
            holder = self.candidate(index, self.sim.state.titans[key].factor)
            self.sim._inherit_coreflame(self.sim.state.titans[key], holder, "先行试炼")
        self.sim._resolve_worldbearing_trial()
        self.assertEqual(self.sim.state.titans["kephale"].coreflame_holder, candidate.id)

    def test_strife_cannot_die_before_minimum_journey_and_returns_on_battle_death(self):
        holder = self.candidate(1, Factor.HUNT)
        titan = self.sim.state.titans["nikador"]
        self.sim._inherit_coreflame(titan, holder, "挑战获胜")
        self.sim.state.regions["swordpeak"].status = "lost"
        self.sim.random = Mock()
        self.sim.random.get.return_value.random.return_value = 0.0
        titan.authority_state["journey_years"] = 14
        self.sim._resolve_strife_authority()
        self.assertTrue(holder.alive)
        titan.authority_state["journey_years"] = 19
        self.sim._resolve_strife_authority()
        self.assertFalse(holder.alive)
        self.assertEqual(titan.coreflame_status, "returned")

    def test_law_returns_without_waiting_for_ten_fires(self):
        holder = self.candidate(1, Factor.ORDER)
        titan = self.sim.state.titans["talanton"]
        self.sim._inherit_coreflame(titan, holder, "共同之律")
        titan.authority_state["judgment_count"] = 3
        for index, key in enumerate(("georios", "zagreus"), 2):
            candidate = self.candidate(index, self.sim.state.titans[key].factor)
            self.sim._inherit_coreflame(self.sim.state.titans[key], candidate, "测试试炼")
            self.sim._return_coreflame(self.sim.state.titans[key], candidate, "测试献祭")
        self.sim.state.year = 20
        self.sim._resolve_law_authority()
        self.assertEqual(titan.coreflame_status, "returned")

    def test_ten_returns_time_witness_and_worldbearer_form_a_complete_chain(self):
        time_holder = self.candidate(1, Factor.REMEMBRANCE, "unblemished_soul")
        bearer = self.candidate(2, Factor.DESTRUCTION, "perfect_vessel")
        self.sim._inherit_coreflame(self.sim.state.titans["oronyx"], time_holder, "忆页三问")
        self.sim._inherit_coreflame(self.sim.state.titans["kephale"], bearer, "承载试炼")
        for index, key in enumerate(sorted(ORDINARY_FIRES), 3):
            titan = self.sim.state.titans[key]
            holder = self.sim.state.people["tribios"] if key == "janus" else self.candidate(index, titan.factor)
            if key != "janus":
                self.sim._inherit_coreflame(titan, holder, "可追溯试炼")
            self.sim.state.year += 1
            self.sim._return_coreflame(titan, holder, "以自身为后来者留下印记")
            self.sim._resolve_time_authority()
        self.assertEqual(self.sim.state.titans["oronyx"].coreflame_status, "returned")
        self.assertIsNone(self.sim._check_ending())
        for year in range(12, 45, 3):
            self.sim.state.year = year
            self.sim._resolve_worldbearing_authority()
        self.assertEqual(self.sim._recreation_blockers(), [])
        self.assertEqual(self.sim._check_ending(), EndingKind.RECREATION_READY)
        stories = self.sim.state.flame_stories
        self.assertEqual(len([s for s in stories.values() if s.get("returned_event_id")]), 11)
        self.assertGreaterEqual(stories["oronyx"]["returned_year"], max(stories[k]["returned_year"] for k in ORDINARY_FIRES))


if __name__ == "__main__":
    unittest.main()
