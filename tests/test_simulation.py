import unittest

from amphoreus_sim.models import Crisis, EndingKind, Factor, RefugeCrisis
from amphoreus_sim.simulation import Simulation


class SimulationTests(unittest.TestCase):
    def test_same_seed_produces_same_result(self) -> None:
        self.assertEqual(Simulation(42, 10).run().as_dict(), Simulation(42, 10).run().as_dict())

    def test_different_seeds_produce_different_histories(self) -> None:
        self.assertNotEqual(Simulation(1, 10).run().state_hash, Simulation(2, 10).run().state_hash)

    def test_initial_world_has_twelve_titans_and_all_factors(self) -> None:
        simulation = Simulation(42, population=100)
        self.assertEqual(len(simulation.state.titans), 12)
        self.assertEqual(set(simulation.state.people["tribios"].factors), set(Factor))

    def test_regions_have_mixed_titan_faiths_and_people_have_stances(self) -> None:
        simulation = Simulation(42, population=100)
        janusopolis = simulation.state.regions["janusopolis"]
        self.assertTrue({"janus", "oronyx", "talanton"}.issubset(janusopolis.titan_faiths))
        self.assertGreater(simulation.state.people["tribios"].titan_stances["janus"], 90)

    def test_corrupted_titan_loses_regional_faith_to_an_alternative(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["janusopolis"]
        simulation.state.year = 5
        simulation.state.titans["janus"].corruption = 80
        before = region.titan_faiths["janus"]
        simulation._resolve_faiths()
        self.assertLess(region.titan_faiths["janus"], before)

    def test_starts_after_tribios_takes_gate_coreflame(self) -> None:
        simulation = Simulation(42, population=100)
        self.assertEqual(simulation.state.people["tribios"].golden_status, "demigod")
        self.assertEqual(simulation.state.titans["janus"].coreflame_holder, "tribios")

    def test_people_have_sparse_local_relationships_and_starting_organizations(self) -> None:
        simulation = Simulation(42, population=100)
        self.assertTrue(all(len(person.relations) <= 16 for person in simulation.state.people.values()))
        self.assertEqual(simulation.state.people["tribios"].organization_id, "flamechase")
        self.assertIn("tribios", simulation.state.organizations["flamechase"].member_ids)

    def test_flamechase_can_recruit_from_the_local_population(self) -> None:
        simulation = Simulation(42, max_ticks=10, population=200)
        initial_members = len(simulation.state.organizations["flamechase"].member_ids)
        simulation.run()
        self.assertGreaterEqual(len(simulation.state.organizations["flamechase"].member_ids), initial_members)

    def test_children_have_parents_and_family_relationships(self) -> None:
        simulation = Simulation(42, population=1000)
        simulation.step()
        children = [person for person in simulation.state.people.values() if person.parent_ids]

        self.assertTrue(children)
        child = children[0]
        self.assertEqual(child.life_stage(), "child")
        self.assertEqual(len(child.parent_ids), 2)
        self.assertTrue(all(parent_id in child.relations for parent_id in child.parent_ids))
        self.assertNotIn("新生儿", child.name)

    def test_initial_people_receive_seeded_regional_names(self) -> None:
        simulation = Simulation(42, population=100)
        names = [person.name for person_id, person in simulation.state.people.items() if person_id != "tribios"]

        self.assertTrue(all("居民" not in name and "·" in name for name in names))
        self.assertEqual(Simulation(42, population=100).state.people["person-0001"].name, simulation.state.people["person-0001"].name)

    def test_later_generations_form_new_ties_and_continue_family_lines(self) -> None:
        simulation = Simulation(42, max_ticks=120, population=1000)
        simulation.run()
        descendants = [
            person for person in simulation.state.people.values()
            if person.parent_ids and any(simulation.state.people[parent_id].parent_ids for parent_id in person.parent_ids)
        ]

        self.assertTrue(descendants)
        self.assertGreater(simulation.world_snapshot()["population"]["total_civilians"], 0)
        self.assertTrue(simulation.world_snapshot()["historical_focus"])
        self.assertTrue(any(
            relation.kind == "伴侣"
            for person in simulation.state.people.values() for relation in person.relations.values()
        ))

    def test_annual_turns_have_visible_world_status(self) -> None:
        result = Simulation(42, 5, population=100).run()
        self.assertEqual({event.year for event in result.history if event.type == "world_status"}, set(range(1, 6)))

    def test_one_thousand_people_runs_and_keeps_focus_snapshot_small(self) -> None:
        result = Simulation(42, 5, population=1000).run()
        self.assertEqual(result.final_state["population"]["initial_individuals"], 1000)
        self.assertLessEqual(len(result.final_state["historical_focus"]), 30)

    def test_focus_requires_world_impact_or_a_golden_status(self) -> None:
        snapshot = Simulation(42, max_ticks=20, population=300).run().final_state
        self.assertTrue(all(
            person["world_impact"] >= 12 or person["coreflames"] or person["golden_status"] != "ordinary"
            for person in snapshot["historical_focus"].values()
        ))

    def test_regions_expose_tension_as_a_separate_social_pressure(self) -> None:
        snapshot = Simulation(42, population=100).world_snapshot()
        self.assertTrue(all("tension" in region for region in snapshot["regions"].values()))

    def test_world_wear_accumulates_and_erodes_a_vulnerable_region(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["skyward"]
        region.black_tide, region.scars = 45, 2
        initial_source = region.tide_source
        simulation.state.world_wear = 157
        simulation.step()
        self.assertEqual(simulation.state.world_wear, 158)
        self.assertGreater(region.tide_source, initial_source)

    def test_last_refuge_is_eroded_but_not_ended_by_a_fixed_year(self) -> None:
        simulation = Simulation(42, population=100)
        remaining = simulation.state.regions["okhema"]
        for region in simulation.state.regions.values():
            if region.id != remaining.id:
                region.status = "lost"
        simulation.state.world_wear = 399
        old_source = remaining.tide_source
        simulation.step()
        self.assertEqual(simulation.state.world_wear, 400)
        self.assertGreater(remaining.tide_source, old_source)
        self.assertNotEqual(simulation._check_ending(), EndingKind.COLLAPSE)

    def test_demigod_does_not_die_from_the_normal_age_limit(self) -> None:
        simulation = Simulation(42, population=100)
        tribios = simulation.state.people["tribios"]
        tribios.age, tribios.health = 90, 100
        simulation.step()
        self.assertTrue(tribios.alive)

    def test_notable_death_is_preserved_in_historical_archive(self) -> None:
        simulation = Simulation(42, population=100)
        person = simulation.state.people["person-0001"]
        person.age, person.health, person.world_impact = 90, 100, 12
        person.impact_reasons.append("曾组织区域救援")
        simulation.step()
        archived = simulation.world_snapshot()["historical_archive"]
        self.assertIn(person.id, archived)
        self.assertEqual(archived[person.id]["death_cause"], "因年老而自然离世")

    def test_black_tide_creates_an_active_crisis(self) -> None:
        simulation = Simulation(42, population=100)
        simulation.state.regions["skyward"].black_tide = 55
        simulation.step()
        self.assertTrue(any(crisis.active and crisis.region_id == "skyward" for crisis in simulation.state.crises.values()))

    def test_regions_have_refuge_capacity(self) -> None:
        simulation = Simulation(42, population=100)
        self.assertTrue(all(region.refuge_capacity >= region.population for region in simulation.state.regions.values()))

    def test_lost_region_is_a_world_state_not_just_zero_population(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["skyward"]
        region.black_tide, region.population, region.collapse_years = 90, 100, 7
        simulation._resolve_region_statuses()
        self.assertEqual(region.status, "lost")

    def test_lost_region_becomes_remnants_not_a_normal_city(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["skyward"]
        region.status, region.population, region.food, region.order = "lost", 90, 999, 50
        simulation._resolve_environment()
        self.assertLess(region.population, 90)
        self.assertEqual((region.food, region.order), (0, 0))

    def test_last_refuge_can_fall_before_tide_reaches_eighty_five(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["okhema"]
        simulation.state.world_wear = 400
        for other in simulation.state.regions.values():
            if other.id != region.id:
                other.status = "lost"
        region.black_tide, region.population, region.collapse_years = 76, 100, 7
        simulation._resolve_region_statuses()
        self.assertEqual(region.status, "lost")

    def test_late_last_refuge_falls_at_the_lowered_tide_threshold(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["okhema"]
        simulation.state.world_wear = 500
        for other in simulation.state.regions.values():
            if other.id != region.id:
                other.status = "lost"
        region.black_tide, region.population, region.collapse_years = 65, 100, 7
        simulation._resolve_region_statuses()
        self.assertEqual(region.status, "lost")

    def test_demigod_does_not_die_from_ordinary_environmental_health_loss(self) -> None:
        simulation = Simulation(42, population=100)
        tribios = simulation.state.people["tribios"]
        tribios.health = 1
        simulation.state.regions[tribios.region_id].black_tide = 100
        simulation._resolve_people()
        self.assertTrue(tribios.alive)

    def test_crisis_records_a_multi_year_response_strategy(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["janusopolis"]
        crisis = Crisis("test-crisis", region.id, 25, simulation.state.year)
        simulation.state.crises[crisis.id] = crisis
        simulation._support_crisis(simulation.state.people["tribios"], region, 30, "测试危机响应")
        self.assertFalse(crisis.active)
        self.assertIn(crisis.outcome, {"hold", "evacuate", "research"})
        self.assertEqual(sum(crisis.strategy_points.values()), 30)

    def test_overcrowding_creates_a_refuge_crisis(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["okhema"]
        region.population = region.refuge_capacity + 1000
        simulation._sync_refuge_crises()
        crisis = next(iter(simulation.state.refuge_crises.values()))
        self.assertTrue(crisis.active)
        self.assertEqual(crisis.region_id, "okhema")

    def test_refuge_crisis_expands_capacity_when_resolved(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["janusopolis"]
        region.population = region.refuge_capacity + 500
        crisis = RefugeCrisis("janusopolis:refuge", region.id, simulation.state.year)
        simulation.state.refuge_crises[crisis.id] = crisis
        old_capacity = region.refuge_capacity
        crisis.response_points = 36
        crisis.strategy_points["settle"] = 36
        simulation._settle_refuge_crisis(crisis, region, simulation.state.people["tribios"])
        self.assertFalse(crisis.active)
        self.assertEqual(crisis.outcome, "settle")
        self.assertGreater(region.refuge_capacity, old_capacity)
        self.assertLessEqual(region.refuge_capacity, region.refuge_capacity_limit)

    def test_independent_people_never_outnumber_the_civilian_population(self) -> None:
        simulation = Simulation(42, population=100)
        for region in simulation.state.regions.values():
            region.population = 0
        simulation.state.regions["okhema"].population = 3
        simulation._maintain_representatives()
        snapshot = simulation.world_snapshot()
        self.assertLessEqual(snapshot["population"]["alive_individuals"], snapshot["population"]["total_civilians"])
