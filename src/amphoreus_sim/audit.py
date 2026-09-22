"""Long-horizon audit report for deterministic world simulations."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

from .simulation import Simulation


def run_audit(seed: int, ticks: int = 1_000, population: int = 1_000) -> dict[str, Any]:
    simulation = Simulation(seed, max_ticks=ticks, population=population)
    result = simulation.run()
    events = simulation.state.events
    inherited: dict[str, list[int]] = {titan_id: [] for titan_id in simulation.state.titans}
    returned: dict[str, list[int]] = {titan_id: [] for titan_id in simulation.state.titans}
    lost_regions: list[tuple[str, int]] = []
    anomalies: list[str] = []

    for event in events:
        for effect in event.effects:
            parts = effect.split(":")
            if len(parts) >= 3 and parts[0] == "coreflame" and parts[1] in inherited:
                if parts[2] == "inherited":
                    inherited[parts[1]].append(event.year)
                elif parts[2] == "returned":
                    returned[parts[1]].append(event.year)
            if len(parts) >= 3 and parts[0] == "region" and parts[2] == "lost":
                lost_regions.append((parts[1], event.year))

    lost_counts = Counter(region_id for region_id, _year in lost_regions)
    anomalies.extend(
        f"地区 {region_id} 被重复记录失陷 {count} 次"
        for region_id, count in lost_counts.items() if count > 1
    )
    for titan_id, years in returned.items():
        if len(years) > 1:
            anomalies.append(f"火种 {titan_id} 被重复记录归还 {len(years)} 次")
        if years and not inherited[titan_id] and titan_id != "janus":
            anomalies.append(f"火种 {titan_id} 有归还记录但没有承接记录")
        if years and inherited[titan_id] and min(years) < min(inherited[titan_id]):
            anomalies.append(f"火种 {titan_id} 在承接之前归还")

    foundation_events = [event for event in events if event.type == "earth_foundation"]
    for event in foundation_events:
        population_effects = [effect for effect in event.effects if effect.startswith("population:georios_foundation:")]
        if not population_effects or int(population_effects[0].rsplit(":", 1)[1]) <= 0:
            anomalies.append("磐生城建立时没有首批居民")

    fire_journeys = {}
    for titan_id, titan in simulation.state.titans.items():
        fire_journeys[titan_id] = {
            "name": titan.name,
            "status": titan.coreflame_status,
            "holder": titan.coreflame_holder,
            "inherited_years": inherited[titan_id],
            "returned_years": returned[titan_id],
            "authority_state": titan.authority_state,
        }

    return {
        "seed": seed,
        "ending": result.ending.value,
        "ending_year": simulation.state.year,
        "population": {
            "civilians": sum(region.population for region in simulation.state.regions.values()),
            "generated_people": len(simulation.state.people),
            "alive_people": sum(person.alive for person in simulation.state.people.values()),
            "golden_or_demigod": sum(person.golden_status != "ordinary" for person in simulation.state.people.values()),
        },
        "lost_regions": [{"region_id": region_id, "year": year} for region_id, year in lost_regions],
        "gate_rescues": [
            {"year": event.year, "summary": event.summary}
            for event in events if event.type == "gate_rescue"
        ],
        "reason_milestones": [
            {"year": event.year, "type": event.type, "summary": event.summary}
            for event in events if event.type.startswith("reason_")
        ],
        "fire_journeys": fire_journeys,
        "anomalies": anomalies,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run long-horizon Amphoreus audits.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42])
    parser.add_argument("--ticks", type=int, default=1_000)
    parser.add_argument("--population", type=int, default=1_000)
    args = parser.parse_args()
    reports = [run_audit(seed, args.ticks, args.population) for seed in args.seeds]
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
