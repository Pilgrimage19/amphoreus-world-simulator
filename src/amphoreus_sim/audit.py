"""Long-horizon audit report for deterministic world simulations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import Counter
from typing import Any

from .simulation import Simulation
from .flamechase import ORDINARY_FIRES


def state_anomalies(simulation: Simulation) -> list[str]:
    """Check live invariants, not just whether event counts look plausible."""
    state = simulation.state
    errors = []
    residents = Counter(p.region_id for p in state.people.values() if p.alive)
    for region in state.regions.values():
        if region.population < 0 or region.food < 0:
            errors.append(f"地区 {region.id} 出现负人口或负粮食")
        if residents[region.id] > region.population:
            errors.append(f"地区 {region.id} 独立人物超过居民总数")
    for titan in state.titans.values():
        holder = state.people.get(titan.coreflame_holder or "")
        if titan.coreflame_status == "held":
            if holder is None or not holder.alive or titan.id not in holder.coreflames:
                errors.append(f"火种 {titan.id} 持有状态与人物不一致")
        elif titan.coreflame_holder is not None:
            errors.append(f"火种 {titan.id} 非持有状态仍保留持有者")
        if titan.coreflame_status == "returned" and not state.flame_stories.get(titan.id, {}).get("returned_event_id"):
            errors.append(f"火种 {titan.id} 归还但缺少逐火史")
    for person in state.people.values():
        for key in person.coreflames:
            titan = state.titans.get(key)
            if titan is None or titan.coreflame_status != "held" or titan.coreflame_holder != person.id:
                errors.append(f"人物 {person.id} 的火种 {key} 与泰坦不一致")
    if state.pending_souls < 0 or state.ferried_souls < 0:
        errors.append("亡者计数出现负数")
    return errors


def run_audit(seed: int, ticks: int = 1_000, population: int = 1_000) -> dict[str, Any]:
    simulation = Simulation(seed, max_ticks=ticks, population=population)
    live_anomalies: set[str] = set()
    lost_ids: set[str] = set()
    for _ in range(ticks):
        ending = simulation.step()
        live_anomalies.update(state_anomalies(simulation))
        live_anomalies.update(f"地区 {key} 未经重建自行复活" for key in lost_ids if simulation.state.regions[key].status != "lost")
        lost_ids.update(r.id for r in simulation.state.regions.values() if r.status == "lost")
        if ending is not None:
            break
    events = simulation.state.events
    inherited: dict[str, list[int]] = {titan_id: [] for titan_id in simulation.state.titans}
    returned: dict[str, list[int]] = {titan_id: [] for titan_id in simulation.state.titans}
    lost_regions: list[tuple[str, int]] = []
    anomalies: list[str] = sorted(live_anomalies)

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
    time_returns = returned["oronyx"]
    if time_returns and (any(not returned[k] for k in ORDINARY_FIRES)
                         or any(returned[k][0] > time_returns[0] for k in ORDINARY_FIRES if returned[k])):
        anomalies.append("岁月火种未按倒数第二顺序归还")

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
        "ending": simulation.ending.value if simulation.ending else "survived",
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
        "flame_stories": simulation.state.flame_stories,
        "recreation_blockers": simulation._recreation_blockers(),
        "special_candidates": [{"id": p.id, "role": p.special_role, "alive": p.alive}
                               for p in simulation.state.people.values() if p.special_role],
        "anomalies": anomalies,
        "trial_evidence_counts": {
            key: sum(person.trial_evidence.get(key, 0) > 0 for person in simulation.state.people.values())
            for key in ("aquila", "georios", "phagousa", "talanton", "mnestia", "zagreus", "cerces_exam_index",
                        "oronyx_memory_years", "kephale_burdens")
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run long-horizon Amphoreus audits.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42])
    parser.add_argument("--ticks", type=int, default=1_000)
    parser.add_argument("--population", type=int, default=1_000)
    parser.add_argument("--output", type=Path, help="Save the complete generated audit as JSON")
    parser.add_argument("--summary", action="store_true", help="Print compact per-seed results")
    args = parser.parse_args()
    reports = []
    for seed in args.seeds:
        report = run_audit(seed, args.ticks, args.population)
        reports.append(report)
        if args.summary:
            print(json.dumps({"seed": seed, "ending": report["ending"], "year": report["ending_year"],
                              "population": report["population"],
                              "fires": {key: value["status"] for key, value in report["fire_journeys"].items()},
                              "anomalies": report["anomalies"]}, ensure_ascii=False), flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.summary:
        print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
