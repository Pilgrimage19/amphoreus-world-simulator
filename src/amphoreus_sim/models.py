"""Data models for the first annual, population-scale world slice."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class Factor(StrEnum):
    DESTRUCTION = "destruction"
    REMEMBRANCE = "remembrance"
    ERUDITION = "erudition"
    HARMONY = "harmony"
    ELATION = "elation"
    NIHILITY = "nihility"
    HUNT = "hunt"
    BEAUTY = "beauty"
    PRESERVATION = "preservation"
    EQUILIBRIUM = "equilibrium"
    ORDER = "order"
    PERMANENCE = "permanence"


class EndingKind(StrEnum):
    SURVIVED = "survived"
    RECREATION_READY = "recreation_ready"
    COLLAPSE = "collapse"


@dataclass(slots=True)
class Region:
    id: str
    name: str
    population: int
    food: int
    order: int
    knowledge: int
    # Social strain: rigidity, factional friction and unmet expectations.
    # It is deliberately separate from black tide, which is an external
    # existential threat rather than ordinary political pressure.
    tension: int
    black_tide: int
    # Persistent contamination. Ordinary civic capacity can contain black
    # tide down to this level but cannot erase its source.
    tide_source: int
    neighbours: tuple[str, ...]
    titan_id: str | None = None
    tide_stage: int = 0
    # Capacity describes beds, stores, walls and public services rather than
    # an arbitrary population cap. Overcrowding is survivable but costly.
    refuge_capacity: int = 0
    # A city can build outward only so far in the current world generation.
    refuge_capacity_limit: int = 0
    defense: int = 0
    scars: int = 0
    collapse_years: int = 0
    status: str = "stable"
    last_migration_report_year: int = 0
    # Local worship/hostility shares. These are cultural influence values, not
    # a claim that every resident worships only one Titan.
    titan_faiths: dict[str, int] = field(default_factory=dict)

    def snapshot(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class Titan:
    id: str
    name: str
    domain: str
    factor: Factor
    group: str
    region_id: str
    stability: int
    corruption: int = 0
    coreflame_holder: str | None = None
    trial_progress: int = 0
    # A fire may still rest in its Titan, be carried by a demi-god, or have
    # been returned through a meaningful sacrifice.
    coreflame_status: str = "within_titan"
    coreflame_returned_year: int | None = None
    # Titan-specific authority values remain structured and visible without
    # making every future authority a bespoke WorldState field.
    authority_state: dict[str, int | str | list[str]] = field(default_factory=dict)

    def snapshot(self) -> dict[str, object]:
        return {**asdict(self), "factor": self.factor.value}


@dataclass(slots=True)
class Relation:
    """A directed, sparse relationship. People do not know the whole world."""

    target_id: str
    kind: str
    trust: int
    debt: int = 0
    fear: int = 0
    oath: str | None = None
    last_interaction_year: int = 0

    def snapshot(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class Organization:
    id: str
    name: str
    kind: str
    region_id: str
    purpose: str
    leader_id: str | None = None
    influence: int = 1
    member_ids: set[str] = field(default_factory=set)

    def snapshot(self) -> dict[str, object]:
        return {
            "id": self.id, "name": self.name, "kind": self.kind, "region_id": self.region_id,
            "purpose": self.purpose, "leader_id": self.leader_id, "influence": self.influence,
            "member_count": len(self.member_ids),
        }


@dataclass(slots=True)
class Crisis:
    """A persistent regional emergency created by a Black Tide threshold."""

    id: str
    region_id: str
    stage: int
    started_year: int
    response_points: int = 0
    strategy_points: dict[str, int] = field(default_factory=lambda: {"hold": 0, "evacuate": 0, "research": 0})
    participant_ids: set[str] = field(default_factory=set)
    active: bool = True
    resolved_year: int | None = None
    outcome: str | None = None

    def snapshot(self) -> dict[str, object]:
        return {
            "id": self.id, "region_id": self.region_id, "stage": self.stage,
            "started_year": self.started_year, "response_points": self.response_points,
            "strategy_points": dict(self.strategy_points), "participant_count": len(self.participant_ids),
            "active": self.active, "resolved_year": self.resolved_year, "outcome": self.outcome,
        }


@dataclass(slots=True)
class RefugeCrisis:
    """A multi-year civic emergency caused by a city receiving more people than it can house."""

    id: str
    region_id: str
    started_year: int
    response_points: int = 0
    strategy_points: dict[str, int] = field(default_factory=lambda: {"welcome": 0, "ration": 0, "settle": 0})
    participant_ids: set[str] = field(default_factory=set)
    active: bool = True
    resolved_year: int | None = None
    outcome: str | None = None

    def snapshot(self) -> dict[str, object]:
        return {
            "id": self.id, "region_id": self.region_id, "started_year": self.started_year,
            "response_points": self.response_points, "strategy_points": dict(self.strategy_points),
            "participant_count": len(self.participant_ids), "active": self.active,
            "resolved_year": self.resolved_year, "outcome": self.outcome,
        }


@dataclass(slots=True)
class Person:
    id: str
    name: str
    region_id: str
    age: int
    factors: dict[Factor, int]
    body: int
    insight: int
    social: int
    leadership: int
    courage: int = 50
    empathy: int = 50
    willpower: int = 50
    restraint: int = 50
    ambition: int = 50
    adaptability: int = 50
    responsibility: int = 50
    family_name: str = ""
    health: int = 100
    hunger: int = 0
    influence: int = 0
    # Unlike personal influence, this records a verified change to a world
    # system: a fire, organisation, crisis, population, or regional rule.
    world_impact: int = 0
    impact_reasons: list[str] = field(default_factory=list)
    resonance_years: int = 0
    golden_status: str = "ordinary"
    organization_id: str | None = None
    parent_ids: tuple[str, ...] = field(default_factory=tuple)
    relations: dict[str, Relation] = field(default_factory=dict)
    coreflames: list[str] = field(default_factory=list)
    returned_coreflames: list[str] = field(default_factory=list)
    # Lasting, cumulative evidence for future fire trials. Keys are created
    # only when a life actually leaves that kind of mark.
    life_traces: dict[str, int] = field(default_factory=dict)
    # Trial evidence is earned through visible world actions, rather than
    # being inferred from a character sheet at the moment of inheritance.
    trial_evidence: dict[str, int] = field(default_factory=dict)
    # Set only in the year an awakened person tried to flee a disaster zone
    # but found no ordinary route to safety. Janus may answer that dead end.
    gate_stranded_year: int | None = None
    stewardship_region_id: str | None = None
    bound_region_id: str | None = None
    # -100 means active rejection, +100 is a life-defining devotion.
    titan_stances: dict[str, int] = field(default_factory=dict)
    memories: list[str] = field(default_factory=list)
    alive: bool = True
    death_year: int | None = None
    death_cause: str | None = None

    def dominant_factor(self) -> Factor:
        return max(self.factors, key=self.factors.__getitem__)

    def life_stage(self) -> str:
        if self.age < 15:
            return "child"
        if self.age < 20:
            return "youth"
        if self.age < 60:
            return "adult"
        return "elder"

    def snapshot(self) -> dict[str, object]:
        data = asdict(self)
        data["factors"] = {factor.value: value for factor, value in self.factors.items()}
        data["relations"] = {target_id: relation.snapshot() for target_id, relation in self.relations.items()}
        data["relationship_count"] = len(self.relations)
        data["dominant_factor"] = self.dominant_factor().value
        data["life_stage"] = self.life_stage()
        return data


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    year: int
    type: str
    summary: str
    causes: tuple[str, ...]
    effects: tuple[str, ...]
    witnesses: tuple[str, ...] = ()

    def snapshot(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class WorldState:
    year: int
    regions: dict[str, Region]
    titans: dict[str, Titan]
    people: dict[str, Person]
    organizations: dict[str, Organization]
    # Irreversible damage accumulated by a world that has not yet found a way
    # to recreate itself. It changes other systems; it is not a countdown.
    world_wear: int = 0
    crises: dict[str, Crisis] = field(default_factory=dict)
    refuge_crises: dict[str, RefugeCrisis] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
