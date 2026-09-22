import unittest

from amphoreus_sim.models import Crisis, EndingKind, Factor, RefugeCrisis, Relation
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

    def test_people_have_candidate_traits_and_life_traces(self) -> None:
        simulation = Simulation(42, population=100)
        person = simulation.state.people["person-0001"]
        self.assertTrue(all(10 <= getattr(person, trait) <= 90 for trait in (
            "courage", "empathy", "willpower", "restraint", "ambition", "adaptability",
        )))
        region = simulation.state.regions[person.region_id]
        region.black_tide = 60
        before = person.responsibility
        simulation._act(person, region, "work")
        self.assertEqual(person.life_traces["guardianship"], 1)
        self.assertEqual(person.life_traces["responsibility"], 1)
        self.assertEqual(person.responsibility, before + 1)

    def test_responsibility_reduces_an_awakened_persons_flee_weight(self) -> None:
        simulation = Simulation(42, population=100)
        cautious, responsible = simulation.state.people["person-0001"], simulation.state.people["person-0002"]
        for person in (cautious, responsible):
            person.golden_status, person.region_id = "awakened", "skyward"
            person.hunger, person.responsibility = 0, 20
        responsible.responsibility = 90
        region = simulation.state.regions["skyward"]
        region.black_tide = 60
        self.assertLess(simulation._action_weights(responsible, region)["flee"], simulation._action_weights(cautious, region)["flee"])

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

    def test_golden_awakening_uses_the_calibrated_resonance_threshold(self) -> None:
        simulation = Simulation(42, population=100)
        person = simulation.state.people["person-0001"]
        for factor in Factor:
            person.factors[factor] = 20
        person.factors[Factor.HARMONY] = 68
        person.age, person.influence, person.resonance_years = 30, 5, 1

        simulation._resolve_people()

        self.assertEqual(person.golden_status, "awakened")

    def test_factor_paths_show_at_most_one_meaningful_life_per_factor(self) -> None:
        simulation = Simulation(42, population=100)
        first = simulation.state.people["person-0001"]
        second = simulation.state.people["person-0002"]
        for person, score in ((first, 14), (second, 22)):
            for factor in Factor:
                person.factors[factor] = 20
            person.factors[Factor.PERMANENCE] = 80
            person.golden_status, person.world_impact = "awakened", score

        paths = simulation.world_snapshot()["factor_paths"]

        self.assertLessEqual(len(paths), len(Factor))
        self.assertEqual(paths["permanence"]["id"], second.id)
        self.assertTrue(all(path["path_factor"] == factor for factor, path in paths.items()))

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

    def test_lost_region_cannot_silently_recover_when_pressure_fades(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["skyward"]
        region.status, region.population = "lost", 0
        region.black_tide, region.collapse_years = 0, 6

        for _ in range(10):
            simulation._resolve_region_statuses()

        self.assertEqual(region.status, "lost")
        self.assertEqual(region.collapse_years, 6)

    def test_small_high_tide_city_falls_from_compound_pressure(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["grove"]
        region.black_tide = 57
        region.population = simulation._minimum_viable_population(region) - 1
        region.order, region.food, region.collapse_years = 0, 0, 0
        simulation._resolve_region_statuses()
        simulation._resolve_region_statuses()
        self.assertEqual(region.status, "lost")

    def test_small_city_without_a_high_tide_cannot_linger_indefinitely(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["grove"]
        region.black_tide = 20
        region.population = simulation._minimum_viable_population(region) - 1
        region.order, region.food, region.collapse_years = 50, 500, 0

        for _ in range(6):
            simulation._resolve_region_statuses()

        self.assertEqual(region.status, "lost")

    def test_large_city_with_severe_tide_and_civic_failure_can_fall(self) -> None:
        simulation = Simulation(42, population=100)
        region = simulation.state.regions["grove"]
        region.black_tide = 45
        region.population = region.refuge_capacity
        region.order, region.food, region.collapse_years = 0, 0, 0

        for _ in range(3):
            simulation._resolve_region_statuses()

        self.assertEqual(region.status, "lost")

    def test_two_isolated_small_refuges_accumulate_burden(self) -> None:
        simulation = Simulation(42, population=100)
        okhema = simulation.state.regions["okhema"]
        grove = simulation.state.regions["grove"]
        for region in simulation.state.regions.values():
            if region.id not in {okhema.id, grove.id}:
                region.status = "lost"
        for region in (okhema, grove):
            region.black_tide = 57
            region.population = simulation._minimum_viable_population(region) - 1
        okhema.defense = 10
        simulation.state.world_wear = 400
        old_source, old_defense = okhema.tide_source, okhema.defense
        simulation._resolve_long_term_decline()
        # At year 400 the pre-existing long-term erosion and the new isolated
        # refuge burden are both due, so their tide-source pressure stacks.
        self.assertEqual(okhema.tide_source, old_source + 2)
        self.assertEqual(okhema.defense, old_defense - 1)

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

    def test_gate_rescues_an_awakened_candidate_stranded_on_a_broken_route(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.golden_status, candidate.health, candidate.region_id = "awakened", 20, "skyward"
        candidate.gate_stranded_year = simulation.state.year

        simulation._resolve_gate_authority()

        janus = simulation.state.titans["janus"]
        self.assertEqual(candidate.region_id, "okhema")
        self.assertGreaterEqual(candidate.health, 35)
        self.assertEqual(janus.authority_state["rescue_charges"], 4)
        self.assertTrue(any(event.type == "gate_rescue" for event in simulation.state.events))

    def test_gate_rescues_a_healthy_stranded_awakened_candidate(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.golden_status, candidate.health, candidate.region_id = "awakened", 100, "skyward"
        candidate.gate_stranded_year = simulation.state.year

        simulation._resolve_gate_authority()

        self.assertEqual(candidate.region_id, "okhema")
        self.assertEqual(simulation.state.titans["janus"].authority_state["rescue_charges"], 4)

    def test_gate_rescue_is_not_blocked_by_okhema_macro_capacity(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.golden_status, candidate.region_id = "awakened", "skyward"
        candidate.gate_stranded_year = simulation.state.year
        okhema = simulation.state.regions["okhema"]
        okhema.population = okhema.refuge_capacity + 1

        simulation._resolve_gate_authority()

        self.assertEqual(candidate.region_id, "okhema")
        self.assertEqual(simulation.state.titans["janus"].authority_state["rescue_charges"], 4)

    def test_failed_flight_marks_an_awakened_candidate_for_gate_rescue(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.golden_status, candidate.region_id = "awakened", "skyward"
        skyward = simulation.state.regions["skyward"]
        skyward.black_tide, skyward.status = 60, "endangered"
        for neighbour_id in skyward.neighbours:
            neighbour = simulation.state.regions[neighbour_id]
            neighbour.status = "lost"

        simulation._act(candidate, skyward, "flee")

        self.assertEqual(candidate.region_id, "skyward")
        self.assertEqual(candidate.gate_stranded_year, simulation.state.year)

    def test_people_do_not_flee_before_the_shared_evacuation_threshold(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.region_id = "skyward"
        skyward = simulation.state.regions["skyward"]
        skyward.black_tide = 49
        destination = simulation.state.regions[skyward.neighbours[0]]
        destination.status, destination.black_tide = "stable", 0
        destination.population = 0

        simulation._act(candidate, skyward, "flee")

        self.assertEqual(candidate.region_id, "skyward")

    def test_a_lost_city_without_an_exit_marks_an_awakened_candidate_for_gate_rescue(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.golden_status, candidate.region_id = "awakened", "skyward"
        skyward = simulation.state.regions["skyward"]
        skyward.status = "lost"
        for neighbour_id in skyward.neighbours:
            simulation.state.regions[neighbour_id].status = "lost"

        simulation._resolve_lost_person(candidate, skyward)

        self.assertEqual(candidate.gate_stranded_year, simulation.state.year)

    def test_gate_does_not_spend_a_charge_on_a_demigod(self) -> None:
        simulation = Simulation(42, population=100)
        tribios = simulation.state.people["tribios"]
        tribios.health, tribios.region_id = 1, "skyward"
        tribios.gate_stranded_year = simulation.state.year

        simulation._resolve_gate_authority()

        self.assertEqual(tribios.region_id, "skyward")
        self.assertEqual(simulation.state.titans["janus"].authority_state["rescue_charges"], 5)

    def test_gate_returns_its_fire_after_the_last_rescue(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.golden_status, candidate.health, candidate.region_id = "awakened", 20, "skyward"
        candidate.gate_stranded_year = simulation.state.year
        janus = simulation.state.titans["janus"]
        janus.authority_state["rescue_charges"] = 1

        simulation._resolve_gate_authority()

        tribios = simulation.state.people["tribios"]
        self.assertFalse(tribios.alive)
        self.assertIsNone(janus.coreflame_holder)
        self.assertEqual(janus.coreflame_status, "returned")
        self.assertEqual(janus.coreflame_returned_year, simulation.state.year)
        self.assertNotIn("janus", tribios.coreflames)

    def test_earth_trial_requires_stewardship_and_binds_the_holder_to_land(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.region_id, candidate.golden_status = "okhema", "awakened"
        candidate.factors[Factor.PERMANENCE], candidate.body = 90, 80
        candidate.titan_stances["georios"] = 55
        candidate.trial_evidence["georios"] = 5
        candidate.stewardship_region_id = "okhema"

        for _ in range(20):
            simulation._resolve_earth_trial()
            if simulation.state.titans["georios"].coreflame_holder:
                break

        georios = simulation.state.titans["georios"]
        self.assertEqual(georios.coreflame_holder, candidate.id)
        self.assertEqual(georios.coreflame_status, "held")
        self.assertEqual(candidate.bound_region_id, "okhema")
        self.assertIn("georios", candidate.coreflames)

    def test_people_keep_their_birthplace_after_migration(self) -> None:
        simulation = Simulation(42, population=100)
        skyward_people = [person for person in simulation.state.people.values() if person.origin_region_id == "skyward"]
        self.assertTrue(skyward_people)
        self.assertTrue(all(person.dominant_factor() is Factor.PRESERVATION for person in skyward_people))
        person = simulation.state.people["person-0001"]
        birthplace = person.origin_region_id
        person.region_id = "okhema" if birthplace != "okhema" else "grove"
        self.assertEqual(person.origin_region_id, birthplace)

    def test_sky_trial_requires_skyward_origin_and_repeated_passage_guardianship(self) -> None:
        simulation = Simulation(42, population=100)
        for person in simulation.state.people.values():
            person.golden_status = "ordinary"
        candidate = simulation.state.people["person-0001"]
        candidate.age, candidate.golden_status = 25, "awakened"
        candidate.origin_region_id, candidate.region_id = "skyward", "janusopolis"
        for factor in Factor:
            candidate.factors[factor] = 20
        candidate.factors[Factor.PRESERVATION] = 90
        region = simulation.state.regions["janusopolis"]
        region.black_tide = 35

        for year in range(50, 55):
            simulation.state.year = year
            simulation._record_sky_passage(candidate, region, "aid")
        candidate.memories.append("witnessed_skyward_fall")
        for year in range(55, 72):
            simulation.state.year = year
            simulation._resolve_sky_trial()

        aquila = simulation.state.titans["aquila"]
        self.assertEqual(candidate.trial_evidence["aquila"], 5)
        self.assertEqual(aquila.coreflame_holder, candidate.id)
        self.assertIn("aquila", candidate.coreflames)

        outsider = simulation.state.people["person-0002"]
        outsider.age, outsider.golden_status, outsider.origin_region_id = 25, "awakened", "okhema"
        for factor in Factor:
            outsider.factors[factor] = 20
        outsider.factors[Factor.PRESERVATION] = 90
        self.assertFalse(simulation._is_sky_candidate(outsider))

    def test_sky_authority_warns_and_reinforces_the_most_threatened_city(self) -> None:
        simulation = Simulation(42, population=100)
        holder = simulation.state.people["person-0001"]
        simulation._inherit_coreflame(simulation.state.titans["aquila"], holder, "测试高天试炼")
        for region in simulation.state.regions.values():
            region.black_tide = 10
        threatened = simulation.state.regions["styxia"]
        threatened.black_tide, threatened.tension, threatened.defense = 65, 70, 4

        simulation._resolve_sky_authority()

        aquila = simulation.state.titans["aquila"]
        self.assertEqual(threatened.defense, 5)
        self.assertEqual(aquila.authority_state["warnings_issued"], 1)
        self.assertEqual(aquila.authority_state["storm_burden"], 1)

    def test_sky_healing_prevents_okhemas_first_irreversible_fall(self) -> None:
        simulation = Simulation(42, population=100)
        holder = simulation.state.people["person-0001"]
        aquila = simulation.state.titans["aquila"]
        simulation._inherit_coreflame(aquila, holder, "测试高天试炼")
        okhema = simulation.state.regions["okhema"]
        okhema.population, okhema.food, okhema.order = 1_000, 0, 0
        okhema.black_tide, okhema.tide_source = 90, 60
        okhema.collapse_years, okhema.scars = 5, 3

        simulation._resolve_region_statuses()

        self.assertNotEqual(okhema.status, "lost")
        self.assertEqual(okhema.collapse_years, 0)
        self.assertLess(okhema.black_tide, 90)
        self.assertFalse(holder.alive)
        self.assertEqual(aquila.coreflame_status, "returned")
        self.assertEqual(aquila.authority_state["healing_used"], 1)
        self.assertTrue(any(event.type == "sky_healing" for event in simulation.state.events))

        okhema.black_tide, okhema.food, okhema.order = 90, 0, 0
        okhema.collapse_years = 5
        simulation._resolve_region_statuses()
        self.assertEqual(okhema.status, "lost")

    def test_earth_trial_rejects_a_golden_whose_highest_factor_is_not_permanence(self) -> None:
        simulation = Simulation(42, population=100)
        for person in simulation.state.people.values():
            person.golden_status = "ordinary"
        candidate = simulation.state.people["person-0001"]
        candidate.region_id, candidate.golden_status = "okhema", "awakened"
        candidate.factors[Factor.PERMANENCE], candidate.factors[Factor.HARMONY] = 90, 95
        candidate.body, candidate.titan_stances["georios"] = 80, 55
        candidate.trial_evidence["georios"], candidate.stewardship_region_id = 5, "okhema"

        for _ in range(20):
            simulation._resolve_earth_trial()

        self.assertIsNone(simulation.state.titans["georios"].coreflame_holder)

    def test_every_adult_permanence_golden_can_begin_earth_stewardship(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.age, candidate.golden_status = 25, "awakened"
        candidate.body, candidate.titan_stances["georios"] = 20, 0
        for factor in Factor:
            candidate.factors[factor] = 20
        candidate.factors[Factor.PERMANENCE] = 68

        self.assertTrue(simulation._is_earth_candidate(candidate))

    def test_earth_stewardship_requires_a_real_local_burden(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.age, candidate.golden_status = 25, "awakened"
        for factor in Factor:
            candidate.factors[factor] = 20
        candidate.factors[Factor.PERMANENCE] = 68
        region = simulation.state.regions[candidate.region_id]
        region.black_tide, region.tension = 0, 0

        simulation._record_earth_stewardship(candidate, region, "work")

        self.assertNotIn("georios", candidate.trial_evidence)
        region.black_tide = 50
        simulation._record_earth_stewardship(candidate, region, "work")
        self.assertEqual(candidate.trial_evidence["georios"], 1)

    def test_earth_candidate_stays_to_work_instead_of_fleeing(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.region_id, candidate.golden_status = "skyward", "awakened"
        for factor in Factor:
            candidate.factors[factor] = 20
        candidate.factors[Factor.PERMANENCE] = 90
        candidate.body, candidate.titan_stances["georios"] = 80, 55
        skyward = simulation.state.regions["skyward"]
        skyward.black_tide = 60
        before_food = skyward.food

        simulation._act(candidate, skyward, "flee")

        self.assertEqual(candidate.region_id, "skyward")
        self.assertGreater(skyward.food, before_food)

    def test_earth_authority_restores_its_bonded_region(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.region_id, candidate.bound_region_id = "okhema", "okhema"
        simulation._inherit_coreflame(simulation.state.titans["georios"], candidate, "测试守土试炼")
        region = simulation.state.regions["okhema"]
        region.food, region.defense, region.black_tide, region.tide_source, region.scars = 0, 4, 40, 10, 2

        simulation._resolve_earth_authority()

        self.assertGreater(region.food, 0)
        self.assertEqual(region.defense, 5)
        self.assertEqual(region.black_tide, 39)
        self.assertEqual(region.scars, 1)

    def test_reason_exam_speed_uses_a_five_to_twenty_year_exponential_curve(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.factors[Factor.ERUDITION], candidate.insight = 100, 100
        self.assertEqual(simulation._reason_exam_years(candidate), 5)

        candidate.factors[Factor.ERUDITION], candidate.insight = 40, 40
        self.assertEqual(simulation._reason_exam_years(candidate), 20)

    def test_reason_candidate_completes_the_four_examinations_without_random_failure(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.age, candidate.golden_status = 25, "awakened"
        for factor in Factor:
            candidate.factors[factor] = 20
        candidate.factors[Factor.ERUDITION], candidate.insight = 100, 100

        for year in range(1, 21):
            simulation.state.year = year
            simulation._resolve_reason_trial()

        cerces = simulation.state.titans["cerces"]
        self.assertEqual(cerces.coreflame_holder, candidate.id)
        self.assertEqual(candidate.trial_evidence["cerces_exam_index"], 4)

    def test_reason_holder_dies_and_returns_the_fire_after_three_guided_demigods(self) -> None:
        simulation = Simulation(42, population=100)
        holder = simulation.state.people["person-0004"]
        cerces = simulation.state.titans["cerces"]
        simulation._inherit_coreflame(cerces, holder, "测试瑟希斯四证")
        cerces.authority_state["created_demigod_ids"] = ["person-0001", "person-0002", "person-0003"]

        simulation._resolve_reason_authority()

        self.assertFalse(holder.alive)
        self.assertEqual(cerces.coreflame_status, "returned")
        self.assertEqual(len(cerces.authority_state["created_demigod_ids"]), 3)

    def test_reason_authority_records_a_golden_becoming_a_demigod(self) -> None:
        simulation = Simulation(42, population=100)
        holder = simulation.state.people["person-0004"]
        simulation._inherit_coreflame(simulation.state.titans["cerces"], holder, "测试瑟希斯四证")
        candidate = simulation.state.people["person-0001"]
        candidate.golden_status = "awakened"

        simulation._inherit_coreflame(simulation.state.titans["georios"], candidate, "测试守土试炼")

        self.assertEqual(simulation.state.titans["cerces"].authority_state["created_demigod_ids"], [candidate.id])
        self.assertTrue(any(event.type == "reason_demigod_created" for event in simulation.state.events))

    def test_law_trial_requires_repeated_self_bound_crisis_stewardship(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.age, candidate.golden_status, candidate.region_id = 25, "awakened", "janusopolis"
        for factor in Factor:
            candidate.factors[factor] = 20
        candidate.factors[Factor.ORDER] = 90
        region = simulation.state.regions["janusopolis"]
        simulation.state.year = 50
        candidate.life_traces["oath"] = 1
        region.tension, region.black_tide = 50, 35

        for _ in range(5):
            simulation._record_law_stewardship(candidate, region, "organize")
        for _ in range(13):
            simulation._resolve_law_trial()

        talanton = simulation.state.titans["talanton"]
        self.assertEqual(candidate.trial_evidence["talanton"], 5)
        self.assertEqual(talanton.coreflame_holder, candidate.id)
        self.assertIn("talanton", candidate.coreflames)

    def test_law_authority_stabilizes_a_region_but_accumulates_rigidity(self) -> None:
        simulation = Simulation(42, population=100)
        holder = simulation.state.people["person-0001"]
        holder.region_id = "janusopolis"
        simulation._inherit_coreflame(simulation.state.titans["talanton"], holder, "测试律法试炼")
        region = simulation.state.regions["janusopolis"]
        region.order, region.tension = 50, 30

        simulation._resolve_law_authority()

        self.assertEqual((region.order, region.tension), (52, 29))
        self.assertEqual(simulation.state.titans["talanton"].authority_state["rigidity"], 1)

    def test_romance_trial_weaves_three_distinct_mutual_bonds(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.age, candidate.golden_status, candidate.region_id = 25, "awakened", "okhema"
        for factor in Factor:
            candidate.factors[factor] = 20
        candidate.factors[Factor.BEAUTY] = 90
        simulation.state.year = 50
        candidate.world_impact = 5
        simulation.state.regions["okhema"].black_tide = 25
        for index, target_id in enumerate(("person-0002", "person-0003", "person-0004")):
            target = simulation.state.people[target_id]
            target.region_id = "okhema"
            candidate.relations[target.id] = Relation(target.id, "友人", 70)
            target.relations[candidate.id] = Relation(candidate.id, "友人", 70)
            simulation._record_romance_weaving(candidate, simulation.state.regions["okhema"], "aid")
        for _ in range(12):
            simulation._resolve_romance_trial()

        mnestia = simulation.state.titans["mnestia"]
        self.assertEqual(candidate.trial_evidence["mnestia"], 3)
        self.assertEqual(mnestia.coreflame_holder, candidate.id)
        self.assertIn("mnestia", candidate.coreflames)

    def test_romance_authority_makes_mutual_aid_and_can_complete_sacrifice(self) -> None:
        simulation = Simulation(42, population=100)
        holder = simulation.state.people["person-0001"]
        holder.region_id = "okhema"
        beloved = simulation.state.people["person-0002"]
        beloved.region_id = "okhema"
        holder.relations[beloved.id] = Relation(beloved.id, "伴侣", 80)
        beloved.relations[holder.id] = Relation(holder.id, "伴侣", 80)
        mnestia = simulation.state.titans["mnestia"]
        simulation._inherit_coreflame(mnestia, holder, "测试浪漫试炼")

        simulation._resolve_romance_authority()
        self.assertGreaterEqual(mnestia.authority_state["weave_count"], 1)
        self.assertTrue(any(event.type == "romance_authority_weave" for event in simulation.state.events))
        for region_id, region in simulation.state.regions.items():
            if region_id not in {"okhema", "janusopolis"}:
                region.status = "lost"
        mnestia.authority_state["weave_count"] = 6

        simulation._resolve_romance_authority()

        self.assertFalse(holder.alive)
        self.assertEqual(mnestia.coreflame_status, "returned")
        self.assertEqual(beloved.relations[holder.id].oath, "永恒纪念")

    def test_earth_sacrifice_creates_a_fallible_new_city_foundation(self) -> None:
        simulation = Simulation(42, population=100)
        candidate = simulation.state.people["person-0001"]
        candidate.region_id, candidate.bound_region_id = "okhema", "okhema"
        georios = simulation.state.titans["georios"]
        simulation._inherit_coreflame(georios, candidate, "测试守土试炼")
        for region_id, region in simulation.state.regions.items():
            if region_id not in {"okhema", "janusopolis"}:
                region.status = "lost"

        simulation._resolve_earth_authority()
        self.assertNotIn("georios_foundation", simulation.state.regions)

        simulation.state.year += 5
        okhema_population = simulation.state.regions["okhema"].population
        simulation._resolve_earth_authority()

        foundation = simulation.state.regions["georios_foundation"]
        self.assertEqual(foundation.name, "磐生城")
        self.assertEqual(foundation.refuge_capacity, 8000)
        self.assertGreater(foundation.population, 0)
        self.assertLess(simulation.state.regions["okhema"].population, okhema_population)
        self.assertTrue(simulation._residents("georios_foundation"))
        self.assertIn("georios_foundation", simulation.state.regions["okhema"].neighbours)
        self.assertFalse(candidate.alive)
        self.assertEqual(georios.coreflame_status, "returned")
        self.assertTrue(any(event.type == "earth_foundation" for event in simulation.state.events))

        simulation.step()
        self.assertIn("georios_foundation", simulation.state.regions)
