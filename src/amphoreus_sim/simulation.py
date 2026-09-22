"""Annual deterministic slice: regions, Titans, black tide, and people."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from .models import Crisis, EndingKind, Event, Factor, Organization, Person, RefugeCrisis, Region, Relation, Titan, WorldState
from .randomness import RandomStreams


FACTOR_NAMES = {
    Factor.DESTRUCTION: "毁灭", Factor.REMEMBRANCE: "记忆", Factor.ERUDITION: "智识",
    Factor.HARMONY: "同谐", Factor.ELATION: "欢愉", Factor.NIHILITY: "虚无",
    Factor.HUNT: "巡猎", Factor.BEAUTY: "纯美", Factor.PRESERVATION: "存护",
    Factor.EQUILIBRIUM: "均衡", Factor.ORDER: "秩序", Factor.PERMANENCE: "不朽",
}

HISTORICAL_IMPACT_THRESHOLD = 12
GOLDEN_RESONANCE_THRESHOLD = 68
GOLDEN_RESONANCE_YEARS = 2
GOLDEN_INFLUENCE_THRESHOLD = 5
EVACUATION_TIDE_THRESHOLD = 50
GATE_RESCUE_CHARGES = 5
EARTH_STEWARDSHIP_YEARS = 5
EARTH_MIN_HOLDING_YEARS = 5
EARTH_FOUNDATION_CAPACITY = 8_000
REASON_EXAMS = ("辨真", "演绎", "衡世", "择未来")
REASON_GOLDEN_QUOTA = 3
LAW_STEWARDSHIP_YEARS = 5
ROMANCE_WEAVES_REQUIRED = 3
ROMANCE_SACRIFICE_WEAVES = 6
SKY_PASSAGES_REQUIRED = 5
OCEAN_PASSAGES_REQUIRED = 5

TITAN_DATA = (
    ("aquila", "艾格勒", "天空", Factor.PRESERVATION, "支柱", "skyward"),
    ("georios", "吉奥里亚", "大地", Factor.PERMANENCE, "支柱", "okhema"),
    ("phagousa", "法古萨", "海洋", Factor.NIHILITY, "支柱", "styxia"),
    ("oronyx", "欧洛尼斯", "岁月", Factor.REMEMBRANCE, "命运", "janusopolis"),
    ("talanton", "塔兰顿", "律法", Factor.ORDER, "命运", "janusopolis"),
    ("janus", "雅努斯", "门径", Factor.HARMONY, "命运", "janusopolis"),
    ("mnestia", "墨涅塔", "浪漫", Factor.BEAUTY, "生命", "okhema"),
    ("kephale", "刻法勒", "负世", Factor.DESTRUCTION, "生命", "okhema"),
    ("cerces", "瑟希斯", "理性", Factor.ERUDITION, "生命", "grove"),
    ("zagreus", "扎格列斯", "诡计", Factor.ELATION, "灾祸", "styxia"),
    ("nikador", "尼卡多利", "纷争", Factor.HUNT, "灾祸", "swordpeak"),
    ("thanatos", "塞纳托斯", "死亡", Factor.EQUILIBRIUM, "灾祸", "euthyria"),
)

# Cultural starting points for the sandbox. A primary territorial patron is
# still stored on Region.titan_id; this table allows mixed worship and keeps
# the three Fate Titans present in Janusopolis from the first year.
REGION_TITAN_FAITHS = {
    "okhema": {"kephale": 56, "mnestia": 22, "georios": 12, "talanton": 10},
    "janusopolis": {"janus": 36, "oronyx": 32, "talanton": 28, "mnestia": 4},
    "swordpeak": {"nikador": 62, "zagreus": 16, "kephale": 12, "talanton": 10},
    "grove": {"cerces": 64, "oronyx": 18, "mnestia": 10, "talanton": 8},
    "styxia": {"phagousa": 57, "zagreus": 21, "mnestia": 14, "janus": 8},
    "euthyria": {"thanatos": 66, "oronyx": 14, "georios": 12, "mnestia": 8},
    "skyward": {"aquila": 68, "georios": 16, "janus": 10, "oronyx": 6},
}

# Project-original name material. It signals regional culture without claiming
# any of these names are canon characters or canonical local naming rules.
NAME_DATA = {
    "okhema": (("阿洛", "弥娅", "伊安", "卡珊", "诺拉", "德墨", "珀拉", "希娅", "塔恩", "菲洛", "莱娅", "索恩"),
               ("河谷", "晨钟", "桂冠", "金枝", "白石", "日轮", "青藤", "长阶", "月井", "铜门", "灯塔", "丰穗")),
    "janusopolis": (("欧弥", "塔利亚", "雅珀", "缇安", "洛珊", "米涅", "塞昂", "伊芙", "卡戎", "拉弥", "安涅", "珀西"),
                    ("双门", "西风", "远钟", "月阶", "回廊", "神谕", "青铜", "长梦", "曙光", "暮影", "白塔", "星盘")),
    "swordpeak": (("德拉", "卡尔", "弥索", "塔洛", "瑞娅", "赫恩", "珂妲", "伊戈", "芙宁", "索拉", "阿克", "梅妲"),
                  ("断锋", "赤刃", "铁誓", "战痕", "峭壁", "火矛", "裂盾", "风暴", "青刃", "重锤", "旌旗", "猎隼")),
    "grove": (("阿涅", "赛弥", "那芙", "洛恩", "伊丝", "特弥", "珂罗", "密雅", "斐恩", "莱索", "安珀", "朵拉"),
              ("神悟", "书叶", "银枝", "古墨", "星砂", "苔庭", "白羽", "石卷", "静泉", "方碑", "云枝", "林冠")),
    "styxia": (("海雅", "瑟罗", "菲娜", "波恩", "卡娅", "尼洛", "珊弥", "托斯", "伊澜", "洛萨", "弥拉", "泽恩"),
               ("潮歌", "蓝港", "海盐", "远帆", "珍珠", "浪桥", "灯船", "珊瑚", "雾湾", "鲸骨", "白沙", "深锚")),
    "euthyria": (("安缇", "莫尔", "希妲", "塞芙", "伊诺", "卡弥", "露娅", "塔菲", "奈安", "朔恩", "弥冬", "洛冰"),
                 ("雪烛", "静眠", "霜铃", "灰杉", "长夜", "白冢", "北风", "冰原", "冬枝", "安魂", "雾松", "寒星")),
    "skyward": (("艾琳", "弥空", "索雅", "赫洛", "卡恩", "珀霓", "莱图", "伊歌", "诺天", "芙霜", "塔维", "赛伊"),
                ("云脊", "天穹", "风环", "鹰巢", "晴岚", "高塔", "浮石", "晨翼", "白云", "远天", "苍穹", "光羽")),
}


@dataclass(frozen=True, slots=True)
class SimulationResult:
    seed: int
    ending: EndingKind
    years_played: int
    state_hash: str
    history: tuple[Event, ...]
    ending_summary: str
    final_state: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {"seed": self.seed, "ending": self.ending.value, "years_played": self.years_played,
                "state_hash": self.state_hash, "ending_summary": self.ending_summary,
                "final_state": self.final_state, "history": [event.snapshot() for event in self.history]}


class Simulation:
    """One tick is one year; only major events receive individual history logs."""

    def __init__(self, seed: int, max_ticks: int = 100, population: int = 1000) -> None:
        if population < 1:
            raise ValueError("population must be positive")
        self.seed, self.max_ticks, self.population = seed, max_ticks, population
        self.random, self._event_sequence = RandomStreams(seed), 0
        self.state = self._initial_state()

    def _initial_state(self) -> WorldState:
        regions = {
            "okhema": Region("okhema", "奥赫玛", 42000, 18000, 72, 48, 12, 8, 6, ("janusopolis", "grove", "swordpeak"), "kephale"),
            "janusopolis": Region("janusopolis", "雅努萨波利斯", 17000, 7200, 58, 61, 30, 24, 20, ("okhema", "skyward", "euthyria"), "janus"),
            "swordpeak": Region("swordpeak", "悬锋城", 15000, 6000, 43, 28, 48, 40, 34, ("okhema", "styxia"), "nikador"),
            "grove": Region("grove", "神悟树庭", 12000, 5200, 62, 76, 22, 15, 12, ("okhema", "styxia"), "cerces"),
            "styxia": Region("styxia", "斯缇科西亚", 11000, 4800, 50, 43, 35, 27, 22, ("swordpeak", "grove", "euthyria"), "phagousa"),
            "euthyria": Region("euthyria", "哀地里亚", 7000, 3000, 48, 35, 42, 33, 28, ("janusopolis", "styxia"), "thanatos"),
            "skyward": Region("skyward", "高天遗迹", 1500, 550, 26, 20, 60, 46, 40, ("janusopolis",), "aquila"),
        }
        capacities = {
            "okhema": (60000, 66000), "janusopolis": (25000, 27500), "swordpeak": (22000, 24000),
            "grove": (18000, 20500), "styxia": (17000, 19000), "euthyria": (11000, 12500), "skyward": (3000, 3400),
        }
        for region_id, (capacity, limit) in capacities.items():
            regions[region_id].refuge_capacity = capacity
            regions[region_id].refuge_capacity_limit = limit
            regions[region_id].titan_faiths = dict(REGION_TITAN_FAITHS[region_id])
        titans = {ident: Titan(ident, name, domain, factor, group, region, 72 if group != "灾祸" else 55)
                  for ident, name, domain, factor, group, region in TITAN_DATA}
        people = self._create_people(regions)
        self._seed_titan_stances(people, regions)
        self._create_local_relationships(people)
        tribios = people["tribios"]
        tribios.golden_status, tribios.influence, tribios.world_impact = "demigod", 24, 30
        tribios.impact_reasons.append("承接门径火种，并开始传播逐火理念")
        tribios.coreflames.append("janus")
        tribios.memories.append("在黑潮降临时夺取门径火种")
        tribios.titan_stances.update({"janus": 96, "oronyx": 48, "talanton": 36})
        titans["janus"].coreflame_holder, titans["janus"].stability = "tribios", 38
        titans["janus"].coreflame_status = "held"
        titans["janus"].authority_state = {"rescue_charges": GATE_RESCUE_CHARGES, "inherited_year": 0}
        organizations = self._create_organizations(people)
        return WorldState(0, regions, titans, people, organizations)

    def _create_people(self, regions: dict[str, Region]) -> dict[str, Person]:
        rng, ids, people = self.random.get("people_setup"), tuple(regions), {}
        for index in range(self.population):
            region_id = rng.choices(ids, weights=(40, 16, 14, 11, 10, 7, 2))[0]
            factors = {factor: rng.randint(15, 65) for factor in Factor}
            dominant = rng.choice(tuple(Factor))
            factors[dominant] = min(82, factors[dominant] + rng.randint(12, 24))
            self._shape_birthplace_factors(region_id, factors)
            ident = f"person-{index:04d}"
            given_name, family_name = self._person_name(region_id, ident)
            people[ident] = Person(ident, f"{given_name}·{family_name}", region_id,
                                   rng.randint(12, 68), factors, rng.randint(25, 75), rng.randint(25, 75),
                                   rng.randint(25, 75), rng.randint(20, 70),
                                   origin_region_id=region_id,
                                   courage=rng.randint(25, 75), empathy=rng.randint(25, 75),
                                   willpower=rng.randint(25, 75), restraint=rng.randint(25, 75),
                                   ambition=rng.randint(25, 75), adaptability=rng.randint(25, 75),
                                   responsibility=rng.randint(25, 75),
                                   family_name=family_name)
        anchor = people.pop("person-0000")
        factors = dict(anchor.factors)
        factors[Factor.HARMONY], factors[Factor.REMEMBRANCE] = 96, max(78, factors[Factor.REMEMBRANCE])
        people["tribios"] = Person("tribios", "缇里西庇俄丝", "janusopolis", 24, factors, 46, 82, 91, 78,
                                    origin_region_id="janusopolis",
                                    courage=80, empathy=88, willpower=86, restraint=70, ambition=72, adaptability=84,
                                    responsibility=86)
        return people

    def _person_name(self, region_id: str, person_id: str) -> tuple[str, str]:
        given_names, family_names = NAME_DATA.get(region_id, NAME_DATA["okhema"])
        rng = self.random.get(f"name:{person_id}")
        return rng.choice(given_names), rng.choice(family_names)

    @staticmethod
    def _shape_birthplace_factors(region_id: str, factors: dict[Factor, int]) -> None:
        """Apply rare, explicit birthplace legacies without creating a chosen hero."""
        if region_id == "skyward":
            factors[Factor.PRESERVATION] = min(90, max(72, max(factors.values()) + 1))

    def _seed_titan_stances(self, people: dict[str, Person], regions: dict[str, Region]) -> None:
        """Give people a small, mixed religious horizon instead of one assigned god."""
        for person in people.values():
            faiths = regions[person.region_id].titan_faiths
            rng = self.random.get(f"faith:{person.id}")
            stances: dict[str, int] = {}
            for titan_id, local_share in sorted(faiths.items(), key=lambda item: (-item[1], item[0]))[:3]:
                titan_factor = next(factor for ident, _name, _domain, factor, _group, _region in TITAN_DATA if ident == titan_id)
                affinity = 14 if person.dominant_factor() == titan_factor else 0
                stances[titan_id] = max(-35, min(90, local_share + affinity + rng.randint(-28, 22)))
            person.titan_stances = stances

    def _create_local_relationships(self, people: dict[str, Person]) -> None:
        """Give every person a small social horizon, never an all-to-all graph."""
        rng = self.random.get("relationships_setup")
        by_region: dict[str, list[Person]] = {}
        for person in people.values():
            by_region.setdefault(person.region_id, []).append(person)
        for local_people in by_region.values():
            for person in local_people:
                candidates = [other for other in local_people if other.id != person.id]
                for other in rng.sample(candidates, k=min(len(candidates), rng.randint(4, 8))):
                    if other.id in person.relations:
                        continue
                    kind = rng.choice(("同乡", "友人", "师徒", "同业", "旧怨"))
                    trust = rng.randint(-25, 65) if kind == "旧怨" else rng.randint(10, 75)
                    person.relations[other.id] = Relation(other.id, kind, trust, fear=max(0, -trust // 2))
                    other.relations.setdefault(person.id, Relation(person.id, kind, trust, fear=max(0, -trust // 2)))

    def _create_organizations(self, people: dict[str, Person]) -> dict[str, Organization]:
        definitions = (
            ("okhema_council", "奥赫玛议事会", "城邦", "okhema", "协调庇护、资源与法令"),
            ("janus_temple", "雅努斯神殿", "神殿", "janusopolis", "维持门径、神谕与仪式"),
            ("swordpeak_militia", "悬锋民兵团", "民兵", "swordpeak", "守卫城邦并抵抗外敌"),
            ("grove_scholars", "神悟学社", "学社", "grove", "保存知识、研究理性与黑潮"),
            ("styxia_guild", "斯缇科西亚商盟", "商盟", "styxia", "维持贸易、港口与物资流动"),
            ("euthyria_keepers", "哀地守夜人", "葬仪团", "euthyria", "安葬亡者、安抚灵魂"),
            ("flamechase", "逐火传播团", "逐火", "janusopolis", "寻找高共鸣者，传播人可承接神权的希望"),
        )
        organizations = {org_id: Organization(org_id, name, kind, region_id, purpose) for org_id, name, kind, region_id, purpose in definitions}
        for org in organizations.values():
            if org.id == "flamechase":
                org.leader_id, org.member_ids = "tribios", {"tribios"}
                people["tribios"].organization_id = org.id
                continue
            candidates = [person for person in people.values() if person.region_id == org.region_id]
            if not candidates:
                continue
            leader = max(candidates, key=lambda person: (person.leadership + person.social, person.id))
            org.leader_id = leader.id
            for person in sorted(candidates, key=lambda item: (-item.social, item.id))[: min(8, len(candidates))]:
                org.member_ids.add(person.id)
                person.organization_id = org.id
        return organizations

    def run(self) -> SimulationResult:
        ending: EndingKind | None = None
        while self.state.year < self.max_ticks and ending is None:
            ending = self.step()
        if ending is None:
            ending = EndingKind.SURVIVED
            self._emit("era_complete", f"第{self.state.year}年结束，世界仍在演化。", (), ("world:survived",))
        return SimulationResult(self.seed, ending, self.state.year, self.state_hash(), tuple(self.state.events),
                                self._ending_summary(ending), self.world_snapshot())

    def step(self) -> EndingKind | None:
        self.state.year += 1
        self._resolve_environment()
        self._resolve_titans()
        self._resolve_faiths()
        self._resolve_people()
        self._resolve_gate_authority()
        self._maintain_representatives()
        self._resolve_organizations()
        self._resolve_coreflame_trials()
        self._resolve_sky_authority()
        self._resolve_ocean_authority()
        self._resolve_earth_authority()
        self._resolve_law_authority()
        self._resolve_romance_authority()
        self._resolve_reason_authority()
        self._update_historical_focus()
        self._emit_world_status()
        return self._check_ending()

    def _resolve_environment(self) -> None:
        self.state.world_wear += 1
        residents = {region_id: self._residents(region_id) for region_id in self.state.regions}
        for region_id, region in self.state.regions.items():
            people = residents[region_id]
            if region.status == "lost":
                self._resolve_lost_region_remnants(region)
                continue
            # Region population is the actual civilian population. Independent
            # people are only the detailed sample observed by the simulation.
            # Black tide eats into both fields and transport routes. It remains
            # manageable at low levels, but above 50 it can turn a region's
            # normal surplus into a structural shortage.
            production = max(0, region.population * 45 // 100 + self.random.get("harvest").randint(-300, 500)
                             - region.population * region.black_tide // 300)
            region.food += production
            demand = region.population // 3
            if region.food < demand:
                shortage = demand - region.food
                shortage_ratio = shortage / max(1, demand)
                population_loss = max(1, int(region.population * min(0.06, shortage_ratio * 0.04)))
                region.population = max(0, region.population - population_loss)
                region.order = max(0, region.order - min(12, int(shortage_ratio * 20) + 1))
                for person in people:
                    person.hunger = min(100, person.hunger + 5)
                self._emit("shortage", f"{region.name}粮食短缺，约{population_loss}名居民死亡或离散。", (f"region:{region_id}:food",), (f"population:{region_id}:-{population_loss}",))
            else:
                for person in people:
                    person.hunger = max(0, person.hunger - 3)
            region.food = max(0, region.food - demand)
            # Stored food is perishable. A city cannot hoard an unlimited
            # surplus simply because one sampled worker acted this year.
            food_capacity = max(400, region.population * (45 + region.knowledge // 2) // 100)
            if region.food > food_capacity:
                spoiled = region.food - food_capacity
                region.food = food_capacity
                if spoiled > max(250, food_capacity // 8) and self.state.year % 10 == 0:
                    self._emit("food_spoilage", f"{region.name}有约{spoiled}份粮食因储运能力不足而腐坏。", (f"region:{region_id}:storage",), (f"food:{region_id}:-{spoiled}",))
            overcrowding = max(0, region.population - region.refuge_capacity)
            if overcrowding:
                # Refuge is possible, but it creates pressure on food, public
                # order and the local Black Tide defense rather than silently
                # turning one city into an infinite population sink.
                crowd_ratio = overcrowding / max(1, region.refuge_capacity)
                region.food = max(0, region.food - overcrowding // 5)
                region.order = max(0, region.order - max(1, int(crowd_ratio * 5)))
                region.tension = min(100, region.tension + max(1, int(crowd_ratio * 6)))
            # Stable societies still require work to remain stable. At high
            # order, rigidity becomes a source of political strain.
            maintenance = int(self.state.year % 3 == 0) + region.black_tide // 45 + region.tension // 90
            region.order = max(0, region.order - maintenance)
            if region.order >= 85:
                region.tension = min(100, region.tension + 1)
            if region.knowledge >= 85:
                region.tension = min(100, region.tension + 1 + region.black_tide // 45)
            elif region.tension > 8:
                region.tension -= 1
            birth_rate = 0.0105 + region.order / 100000
            if region.black_tide > 45:
                birth_rate *= max(0, 1 - (region.black_tide - 45) / 35)
            death_rate = 0.010 + max(0, region.black_tide - 40) ** 2 / 20_000
            births = int(region.population * birth_rate)
            deaths = int(region.population * death_rate)
            region.population = max(0, region.population + births - deaths)
        next_tide = {}
        for region in self.state.regions.values():
            previous_tide = region.black_tide
            pressure = max((self.state.regions[key].black_tide for key in region.neighbours), default=0)
            titan = self.state.titans[region.titan_id] if region.titan_id else None
            change = int(pressure >= region.black_tide + 8)
            instability = 0 if titan is None else max(0, 55 - titan.stability) // 12 + titan.corruption // 35
            chance = max(0, region.black_tide - 35) + region.tension // 6 + instability * 4 - region.defense * 2
            change += int(self.random.get("black_tide").randint(1, 100) <= chance)
            containment = int(region.order >= 50) + int(region.knowledge >= 60) + int(region.food >= region.population // 6) + region.defense // 8
            # Even a severe tide can be pushed back, but only down to its
            # persistent source. Defensive works make this a lasting regional
            # capability rather than a one-off crisis reward.
            if region.black_tide > region.tide_source and containment:
                retreat_chance = min(80, containment * 12 + region.defense * 2)
                if self.random.get("containment").randint(1, 100) <= retreat_chance:
                    change -= 1 + region.defense // 15
            # Containment can return the tide to its residual source, never
            # erase that source. A severe outbreak permanently worsens the
            # local source until a later, costly cleansing mechanic is added.
            if previous_tide >= 50 and self.random.get(f"tide_scar:{region.id}").randint(1, 100) <= 6:
                region.tide_source = min(55, region.tide_source + 1)
            next_tide[region.id] = min(100, max(region.tide_source, region.black_tide + change))
        for region_id, tide in next_tide.items():
            region = self.state.regions[region_id]
            before = region.black_tide
            region.black_tide = tide
            for threshold, label in ((25, "侵蚀"), (50, "灾变"), (75, "失陷边缘")):
                if before < threshold <= tide and threshold > region.tide_stage:
                    region.tide_stage = threshold
                    self._emit("black_tide_escalation", f"{region.name}的黑潮跨入{label}阶段（{tide}/100）；地区生活与泰坦都将承受更重压力。", (f"black_tide:{region_id}",), (f"region:{region_id}:tide_stage:{threshold}",))
        self._resolve_long_term_decline()
        self._sync_black_tide_crises()
        self._resolve_crisis_deadlines()
        self._resolve_population_migration()
        self._resolve_region_statuses()
        self._sync_refuge_crises()
        self._resolve_refuge_crisis_deadlines()

    def _resolve_lost_region_remnants(self, region: Region) -> None:
        """A fallen city has remnants, not a functioning civilian economy."""
        destinations = [
            self.state.regions[region_id] for region_id in region.neighbours
            if self.state.regions[region_id].status != "lost"
            and self.state.regions[region_id].population < self.state.regions[region_id].refuge_capacity
        ]
        remaining = region.population
        for destination in sorted(destinations, key=lambda item: (item.black_tide, item.population / max(1, item.refuge_capacity), item.id)):
            space = max(0, destination.refuge_capacity - destination.population)
            moved = min(space, max(0, remaining // 3))
            if not moved:
                continue
            region.population -= moved
            destination.population += moved
            remaining -= moved
            self._emit("lost_region_exodus", f"约{moved}名{region.name}残存者逃往{destination.name}。", (f"region:{region.id}:lost",), (f"population:{region.id}:-{moved}", f"population:{destination.id}:+{moved}"))
            break
        attrition = min(region.population, max(1, region.population // 5))
        region.population -= attrition
        region.food, region.order, region.tension = 0, 0, 0
        if self.state.year % 10 == 0 and attrition:
            self._emit("lost_region_attrition", f"{region.name}的残存者无法维持稳定聚居，约{attrition}人死去或失散。", (f"region:{region.id}:lost",), (f"population:{region.id}:-{attrition}",))

    def _resolve_long_term_decline(self) -> None:
        """A world without a new creation slowly loses the ability to endure.

        Earlier disasters, scars and local corruption decide where accumulated
        wear first becomes a deeper Black Tide source or a failing Titan.
        """
        wear = self.state.world_wear
        if wear < 100:
            return
        source_interval = 40 if wear < 220 else 28 if wear < 360 else 20
        for index, region in enumerate(self.state.regions.values()):
            titan = self.state.titans.get(region.titan_id or "")
            erosion_due = (wear + index * 7) % source_interval == 0
            vulnerable = region.scars >= 2 or region.black_tide >= 25 or (titan is not None and titan.corruption >= 65)
            if erosion_due and vulnerable:
                region.tide_source = min(70, region.tide_source + 1)
                if wear % (source_interval * 2) == 0:
                    self._emit("world_wear_erosion", f"漫长劫余侵入{region.name}；黑潮残留源加深，寻常守备已无法完全复原旧日秩序。", (f"world_wear:{wear}",), (f"tide_source:{region.id}:+1",))
            if titan is not None and wear >= 160 and (wear + index * 11) % 24 == 0:
                titan.corruption = min(100, titan.corruption + 1)
                titan.stability = max(0, titan.stability - 1)
        lost_regions = sum(region.status == "lost" for region in self.state.regions.values())
        if lost_regions >= len(self.state.regions) - 2:
            # Two isolated, undersized refuges cannot indefinitely sustain each
            # other. Their watchtowers thin out and the Black Tide finds new
            # seams in the remaining civic fabric.
            for index, region in enumerate(self.state.regions.values()):
                if (
                    region.status == "lost"
                    or region.black_tide < 50
                    or region.population > self._minimum_viable_population(region)
                    or (wear + index) % 2 != 0
                ):
                    continue
                region.tide_source = min(85, region.tide_source + 1)
                region.defense = max(0, region.defense - 1)
                if (wear + index) % 10 == 0:
                    self._emit("isolated_refuge_burden", f"{region.name}与另一座孤城相互隔绝，守备难以轮替；黑潮残留源继续渗入。", (f"lost_regions:{lost_regions}", f"population:{region.id}:{region.population}"), (f"tide_source:{region.id}:+1", f"defense:{region.id}:-1"))
        if wear >= 300 and lost_regions >= len(self.state.regions) - 1:
            # A final refuge is not magically safe. It inherits displaced
            # people, broken routes, memories and pressure from the whole
            # fallen world. This makes its tide source climb slowly, allowing
            # a variable last stand instead of a fixed year-400 ending.
            for index, region in enumerate(self.state.regions.values()):
                if region.status == "lost" or (wear + index) % 5 != 0:
                    continue
                region.tide_source = min(85, region.tide_source + 2)
                region.tension = min(100, region.tension + 1)
                self._emit("last_refuge_burden", f"{region.name}成为残存文明的最后庇护所；失陷城邦的遗民与黑潮压力持续加深此地的残留源。", (f"lost_regions:{lost_regions}", f"world_wear:{wear}"), (f"tide_source:{region.id}:+2",))
        if wear in {100, 220, 360}:
            self._emit("world_wear_era", f"第{wear}年的翁法罗斯仍未迎来再创世；累积的劫余开始使黑潮与泰坦的损伤更难逆转。", (f"world_wear:{wear}",), ("world:long_term_decline",))

    def _sync_black_tide_crises(self) -> None:
        """Turn sustained contamination into events that people can answer."""
        for region in self.state.regions.values():
            stage = 75 if region.black_tide >= 75 else 50 if region.black_tide >= 50 else 25 if region.black_tide >= 25 else 0
            if not stage:
                continue
            crisis_id = f"{region.id}:tide:{stage}"
            crisis = self.state.crises.get(crisis_id)
            if crisis is None:
                for older in self.state.crises.values():
                    if older.region_id == region.id and older.active and older.stage < stage:
                        older.active = False
                        older.resolved_year = self.state.year
                crisis = Crisis(crisis_id, region.id, stage, self.state.year)
                self.state.crises[crisis_id] = crisis
                name = {25: "侵蚀危机", 50: "灾变危机", 75: "失陷危机"}[stage]
                self._emit("black_tide_crisis", f"{region.name}爆发{name}；居民、组织与半神都必须决定是否回应。", (f"black_tide:{region.id}:{region.black_tide}",), (f"crisis:{crisis_id}:started",))
            if not crisis.active:
                continue
            # A crisis is distinct from the base tide number: while it remains
            # unresolved it keeps harming the regional social fabric.
            if stage == 25:
                region.tension = min(100, region.tension + 1)
            elif stage == 50:
                region.order = max(0, region.order - 1)
                region.tension = min(100, region.tension + 2)
            else:
                loss = max(1, region.population // 600)
                region.population = max(0, region.population - loss)
                region.order = max(0, region.order - 2)
                region.tension = min(100, region.tension + 3)
                titan = self.state.titans.get(region.titan_id or "")
                if titan:
                    titan.corruption = min(100, titan.corruption + 2)

    def _resolve_crisis_deadlines(self) -> None:
        """An unanswered emergency eventually becomes a recorded failure."""
        deadlines = {25: 16, 50: 12, 75: 8}
        for crisis in self.state.crises.values():
            if not crisis.active or self.state.year - crisis.started_year < deadlines[crisis.stage]:
                continue
            region = self.state.regions[crisis.region_id]
            strategy = max(crisis.strategy_points, key=lambda name: (crisis.strategy_points[name], name))
            crisis.active, crisis.resolved_year = False, self.state.year
            crisis.outcome = f"{strategy}_failed"
            region.black_tide = min(100, region.black_tide + {25: 3, 50: 6, 75: 10}[crisis.stage])
            region.scars += 1
            region.defense = max(0, region.defense - 2)
            self._emit("black_tide_crisis_failed", f"{region.name}未能在期限内化解黑潮危机；{self._crisis_strategy_name(strategy)}的尝试留下了惨痛代价。", (f"crisis:{crisis.id}",), (f"black_tide:{region.id}:increased",), tuple(sorted(crisis.participant_ids)[:5]))

    def _resolve_population_migration(self) -> None:
        for region in self.state.regions.values():
            if not region.neighbours or region.black_tide < EVACUATION_TIDE_THRESHOLD or region.population <= 0:
                continue
            viable = self._safe_refuges(region)
            if not viable:
                continue
            destination = min(viable, key=lambda candidate: (candidate.black_tide, candidate.population / max(1, candidate.refuge_capacity), candidate.id))
            destination_id = destination.id
            safe_space = max(0, destination.refuge_capacity * 9 // 10 - destination.population)
            pressure = max(12, region.black_tide - destination.black_tide)
            migrants = min(safe_space, region.population // 20, max(20, region.population * pressure // 2000))
            if migrants <= 0:
                continue
            region.population -= migrants
            destination.population += migrants
            if self.state.year - region.last_migration_report_year >= 5:
                region.last_migration_report_year = self.state.year
                self._emit("population_migration", f"约{migrants}名居民逃离{region.name}，迁往{destination.name}。", (f"black_tide:{region.id}",), (f"population:{region.id}:-{migrants}", f"population:{destination.id}:+{migrants}"))

    @staticmethod
    def _minimum_viable_population(region: Region) -> int:
        """Population below which a refuge no longer has a viable civic scale."""
        return max(100, region.refuge_capacity // 100)

    def _safe_refuges(self, region: Region) -> list[Region]:
        """Return destinations shared by civilian, personal and remnant flight."""
        return [
            self.state.regions[region_id] for region_id in region.neighbours
            if self.state.regions[region_id].status != "lost"
            and self.state.regions[region_id].black_tide < EVACUATION_TIDE_THRESHOLD
            and self.state.regions[region_id].population < self.state.regions[region_id].refuge_capacity * 9 // 10
        ]

    def _resolve_region_statuses(self) -> None:
        """Give a city a fate beyond its current population counter."""
        for region in self.state.regions.values():
            # Loss is a terminal world state. A quiet year or zero remaining
            # population cannot silently turn ruins back into a functioning
            # city; revival requires a future explicit reconstruction event.
            if region.status == "lost":
                continue
            other_lost = sum(other.status == "lost" for other in self.state.regions.values() if other.id != region.id)
            last_refuge_tide_threshold = 75 if self.state.world_wear < 500 else 65
            last_refuge_failing = (
                self.state.world_wear >= 300
                and other_lost >= len(self.state.regions) - 1
                and region.black_tide >= last_refuge_tide_threshold
                and region.population <= max(100, region.refuge_capacity // 8)
            )
            catastrophic_tide = (
                region.black_tide >= 85 or last_refuge_failing
            ) and region.population <= max(100, region.refuge_capacity // 8)
            fragile_city = (
                region.black_tide >= 50
                and region.population <= self._minimum_viable_population(region)
            )
            # A city reduced below its civic minimum cannot remain a city just
            # because its tide happens to be below the evacuation threshold.
            # At this scale births round to zero while institutions, food
            # stores and defenses still require a functioning population.
            sparse_city = (
                0 < region.population <= self._minimum_viable_population(region)
                and not fragile_city
            )
            social_failure = region.order <= 15 or region.food < max(1, region.population // 6)
            # A populous city is not safe merely because many people are
            # trapped inside it. Once a severe tide has also broken food or
            # civic order, it accumulates collapse pressure as a failed city.
            civic_collapse = region.black_tide >= 40 and social_failure
            if catastrophic_tide:
                region.collapse_years += 1
            elif fragile_city:
                region.collapse_years += 2 + int(social_failure)
            elif civic_collapse:
                region.collapse_years += 1 + int(region.black_tide >= 45)
            elif sparse_city:
                region.collapse_years += 1 + int(social_failure)
            else:
                region.collapse_years = max(0, region.collapse_years - 1)
            previous = region.status
            if region.collapse_years >= 6:
                if self._trigger_sky_healing(region):
                    continue
                region.status = "lost"
            elif region.black_tide >= 50 or civic_collapse:
                region.status = "endangered"
            elif region.population > region.refuge_capacity:
                region.status = "overwhelmed"
            elif region.population > region.refuge_capacity * 9 // 10:
                region.status = "strained"
            else:
                region.status = "stable"
            if region.status == "lost" and previous != "lost":
                region.scars += 1
                region.defense = max(0, region.defense - 5)
                if region.id == "skyward":
                    for descendant in self.state.people.values():
                        if descendant.alive and descendant.origin_region_id == "skyward":
                            if "witnessed_skyward_fall" not in descendant.memories:
                                descendant.memories.append("witnessed_skyward_fall")
                                self._record_life_trace(descendant, "loss")
                self._emit("region_lost", f"{region.name}在黑潮中失陷；幸存者、遗产与火种去向将成为后续历史的争夺。", (f"black_tide:{region.id}", f"population:{region.id}:{region.population}"), (f"region:{region.id}:lost",))
            elif region.status == "overwhelmed" and previous != "overwhelmed":
                self._emit("refuge_overwhelmed", f"{region.name}的避难容量被突破，难民安置开始反噬粮食与秩序。", (f"population:{region.id}:{region.population}",), (f"region:{region.id}:overcrowded",))

    def _sync_refuge_crises(self) -> None:
        """Make overcrowding an answerable civic event, not a permanent UI warning."""
        for region in self.state.regions.values():
            if region.population <= region.refuge_capacity:
                continue
            waves = [crisis for crisis in self.state.refuge_crises.values() if crisis.region_id == region.id]
            if any(crisis.active for crisis in waves):
                continue
            latest = max(waves, key=lambda item: (item.started_year, item.id), default=None)
            # A successful response needs room to take effect. Later population
            # growth can, however, create a genuinely new wave with its own
            # participants and historical outcome.
            if latest is not None and latest.resolved_year is not None and self.state.year - latest.resolved_year < 5:
                continue
            crisis_id = f"{region.id}:refuge:{self.state.year}"
            crisis = RefugeCrisis(crisis_id, region.id, self.state.year)
            self.state.refuge_crises[crisis_id] = crisis
            overflow = region.population - region.refuge_capacity
            self._emit("refuge_crisis", f"{region.name}收容能力被超出约{overflow}人；接纳、配给或开辟新聚居地成为迫切选择。", (f"population:{region.id}:{region.population}",), (f"refuge_crisis:{crisis_id}:started",))

    def _resolve_refuge_crisis_deadlines(self) -> None:
        """Unanswered housing pressure becomes famine, division, and displacement."""
        for crisis in self.state.refuge_crises.values():
            if not crisis.active or self.state.year - crisis.started_year < 12:
                continue
            region = self.state.regions[crisis.region_id]
            strategy = max(crisis.strategy_points, key=lambda name: (crisis.strategy_points[name], name))
            crisis.active, crisis.resolved_year, crisis.outcome = False, self.state.year, f"{strategy}_failed"
            loss = max(30, min(region.population // 80, max(30, region.population - region.refuge_capacity)))
            region.population = max(0, region.population - loss)
            region.food = max(0, region.food - loss)
            region.order = max(0, region.order - 5)
            region.tension = min(100, region.tension + 12)
            region.scars += 1
            self._emit("refuge_crisis_failed", f"{region.name}未能安置涌入的人群；{self._refuge_strategy_name(strategy)}的尝试失败，约{loss}人离散或死于匮乏。", (f"refuge_crisis:{crisis.id}",), (f"population:{region.id}:-{loss}",), tuple(sorted(crisis.participant_ids)[:5]))

    def _resolve_titans(self) -> None:
        for titan in self.state.titans.values():
            region = self.state.regions[titan.region_id]
            titan.corruption = min(100, titan.corruption + region.black_tide // 30 + region.tension // 70)
            titan.stability = max(0, titan.stability - titan.corruption // 40 - region.tension // 90)
            if titan.id == "kephale" and titan.coreflame_holder is None:
                # The world-bearing Titan gives refuge; it does not provide
                # free annual purification. At most it holds the tide above
                # the enduring source and transfers part of the burden into
                # social strain.
                if region.black_tide > region.tide_source:
                    region.black_tide = max(region.tide_source, region.black_tide - 1)
                    region.tension = min(100, region.tension + 1)
            if titan.id == "cerces":
                if region.knowledge < 84:
                    region.knowledge += 1
                else:
                    region.tension = min(100, region.tension + 2)
            if titan.id == "talanton":
                if region.order < 82:
                    region.order += 1
                else:
                    region.tension = min(100, region.tension + 2)
            if titan.id == "nikador" and titan.corruption >= 35:
                region.tension = min(100, region.tension + 2)
                region.order = max(0, region.order - 1)
            if titan.id == "thanatos" and region.black_tide >= 45:
                region.population = max(0, region.population - max(1, region.population // 250))
            if titan.id == "zagreus" and titan.corruption >= 40:
                region.tension = min(100, region.tension + 1)
        if self.state.titans["janus"].coreflame_holder == "tribios":
            janusopolis = self.state.regions["janusopolis"]
            if janusopolis.knowledge < 82:
                janusopolis.knowledge += 1
            else:
                janusopolis.tension = min(100, janusopolis.tension + 1)

    def _resolve_faiths(self) -> None:
        """Faith is a regional culture and a personal relationship, not a static label."""
        for region in self.state.regions.values():
            if region.status == "lost" or not region.titan_faiths:
                continue
            faiths = region.titan_faiths
            if self.state.year % 5 == 0:
                weakened = [titan_id for titan_id in faiths if self.state.titans[titan_id].corruption >= 65]
                for titan_id in weakened:
                    if faiths[titan_id] <= 2:
                        continue
                    faiths[titan_id] -= 1
                    alternatives = [
                        candidate for candidate in faiths
                        if candidate != titan_id and self.state.titans[candidate].corruption < 65
                    ]
                    if alternatives:
                        successor = max(alternatives, key=lambda candidate: (faiths[candidate], candidate))
                        faiths[successor] += 1
            for person in self._residents(region.id):
                for titan_id, local_share in faiths.items():
                    if titan_id not in person.titan_stances:
                        continue
                    target = local_share + (12 if person.dominant_factor() == self.state.titans[titan_id].factor else 0)
                    current = person.titan_stances[titan_id]
                    if current < target:
                        person.titan_stances[titan_id] += 1
                    elif current > target:
                        person.titan_stances[titan_id] -= 1

    def _resolve_people(self) -> None:
        notable = 0
        self._people_by_region = {region_id: self._residents(region_id) for region_id in self.state.regions}
        for person in tuple(self.state.people.values()):
            if not person.alive:
                continue
            person.age += 1
            region = self.state.regions[person.region_id]
            if region.status == "lost":
                self._resolve_lost_person(person, region)
                continue
            # Low and medium contamination damages society first. Direct yearly
            # mortality begins only once a region is deeply lost to the tide.
            person.health -= max(0, (region.black_tide - 50) // 10) + person.hunger // 35
            if region.black_tide >= 25:
                self._record_life_trace(person, "black_tide_exposure")
            if region.black_tide < 25 and person.hunger < 20:
                person.health = min(100, person.health + 1)
            if person.health <= 0 and self._is_demigod(person):
                # A coreflame bearer may suffer, but cannot quietly die to the
                # ordinary health counter used for sampled civilians.
                person.health = 1
            elif person.health <= 0:
                self._record_death(person, "未能从黑潮、伤病或饥饿中幸存")
                continue
            if person.age > 78 and not self._is_demigod(person):
                self._record_death(person, "因年老而自然离世")
                continue
            if person.life_stage() == "child":
                # Children grow inside a household and social network; they do
                # not yet accumulate public influence through adult actions.
                person.insight = min(100, person.insight + 1 + int(region.knowledge >= 60))
                continue
            action = self._choose_action(person, region)
            event = self._act(person, region, action)
            self._record_earth_stewardship(person, region, action)
            self._resolve_relationships(person, action)
            self._record_sky_passage(person, region, action)
            self._record_ocean_passage(person, region, action)
            self._record_law_stewardship(person, region, action)
            self._record_romance_weaving(person, region, action)
            self._form_social_ties(person)
            if event and notable < 12:
                self._emit(*event)
                notable += 1
            peak = person.factors[person.dominant_factor()]
            person.resonance_years = person.resonance_years + 1 if peak >= GOLDEN_RESONANCE_THRESHOLD else max(0, person.resonance_years - 1)
            if (person.life_stage() == "adult" and person.golden_status == "ordinary"
                    and person.resonance_years >= GOLDEN_RESONANCE_YEARS
                    and person.influence >= GOLDEN_INFLUENCE_THRESHOLD):
                person.golden_status = "awakened"
                self._emit("golden_awakening", f"{person.name}在{FACTOR_NAMES[person.dominant_factor()]}上形成稳定共鸣，成为黄金裔候选。", (f"factor:{person.dominant_factor().value}",), (f"person:{person.id}:awakened",), (person.id,))
        self._resolve_births()

    def _resolve_births(self) -> None:
        """Create children from existing relationships, not anonymous population tokens."""
        for region in self.state.regions.values():
            if region.status == "lost":
                continue
            adults = [person for person in self._residents(region.id) if 20 <= person.age <= 42]
            pairs = self._family_pairs(adults)
            total_population = sum(item.population for item in self.state.regions.values())
            sample_capacity = min(region.population, round(self.population * region.population / max(1, total_population)))
            births = min(len(pairs) // 35, max(0, sample_capacity - len(self._residents(region.id))))
            for birth_index in range(births):
                ident = f"birth-{self.state.year:05d}-{region.id}-{birth_index:03d}"
                if ident in self.state.people:
                    continue
                rng = self.random.get(f"birth:{ident}")
                parent_a, parent_b = pairs[birth_index % len(pairs)]
                factors = {
                    factor: max(10, min(90, (parent_a.factors[factor] + parent_b.factors[factor]) // 2 + rng.randint(-10, 10)))
                    for factor in Factor
                }
                self._shape_birthplace_factors(region.id, factors)
                given_name, fallback_family = self._person_name(region.id, ident)
                family_name = self.random.get(f"family:{ident}").choice(
                    (parent_a.family_name, parent_a.family_name, parent_b.family_name, parent_b.family_name, fallback_family)
                )
                child = Person(
                    ident, f"{given_name}·{family_name}", region.id, 0, factors,
                    rng.randint(20, 50), rng.randint(20, 50), rng.randint(20, 50), rng.randint(15, 40),
                    origin_region_id=region.id,
                    courage=self._inherited_trait(parent_a.courage, parent_b.courage, rng),
                    empathy=self._inherited_trait(parent_a.empathy, parent_b.empathy, rng),
                    willpower=self._inherited_trait(parent_a.willpower, parent_b.willpower, rng),
                    restraint=self._inherited_trait(parent_a.restraint, parent_b.restraint, rng),
                    ambition=self._inherited_trait(parent_a.ambition, parent_b.ambition, rng),
                    adaptability=self._inherited_trait(parent_a.adaptability, parent_b.adaptability, rng),
                    responsibility=self._inherited_trait(parent_a.responsibility, parent_b.responsibility, rng),
                    family_name=family_name, parent_ids=(parent_a.id, parent_b.id),
                )
                self.state.people[ident] = child
                child.titan_stances = {
                    titan_id: (parent_a.titan_stances.get(titan_id, 0) + parent_b.titan_stances.get(titan_id, 0)) // 2
                    for titan_id in set(parent_a.titan_stances) | set(parent_b.titan_stances)
                }
                self._link_family(child, parent_a, parent_b)

    def _family_pairs(self, adults: list[Person]) -> list[tuple[Person, Person]]:
        pairs: list[tuple[Person, Person]] = []
        adult_ids = {person.id for person in adults}
        for person in adults:
            for relation in person.relations.values():
                if relation.target_id <= person.id or relation.target_id not in adult_ids:
                    continue
                other = self.state.people[relation.target_id]
                counterpart = other.relations.get(person.id)
                if (counterpart and relation.kind != "亲属" and not self._share_parent(person, other)
                        and relation.trust >= 45 and counterpart.trust >= 45 and relation.fear < 30 and counterpart.fear < 30):
                    pairs.append((person, other))
        return pairs

    def _link_family(self, child: Person, parent_a: Person, parent_b: Person) -> None:
        for parent in (parent_a, parent_b):
            child.relations[parent.id] = Relation(parent.id, "亲属", 90, oath="抚养", last_interaction_year=self.state.year)
            parent.relations[child.id] = Relation(child.id, "亲属", 90, oath="守护", last_interaction_year=self.state.year)
        # A child also knows a few trusted adults in the household's social circle.
        inherited_contacts = list(parent_a.relations.values()) + list(parent_b.relations.values())
        for relation in inherited_contacts:
            if relation.target_id in child.parent_ids or relation.trust < 55 or relation.target_id not in self.state.people:
                continue
            guardian = self.state.people[relation.target_id]
            if guardian.alive and guardian.region_id == child.region_id and len(child.relations) < 5:
                child.relations[guardian.id] = Relation(guardian.id, "家族友人", relation.trust // 2, last_interaction_year=self.state.year)
                guardian.relations.setdefault(child.id, Relation(child.id, "家族友人", relation.trust // 2, last_interaction_year=self.state.year))

    @staticmethod
    def _inherited_trait(first: int, second: int, rng) -> int:
        return max(10, min(90, (first + second) // 2 + rng.randint(-10, 10)))

    def _action_weights(self, person: Person, region: Region) -> dict[str, int]:
        f = person.factors
        flee_weight = 0 if region.black_tide < EVACUATION_TIDE_THRESHOLD else 2 + region.black_tide * 2 + person.hunger
        if person.golden_status == "awakened":
            # Responsibility does not forbid escape, but makes an awakened
            # person more likely to stay and answer the danger around them.
            flee_weight = max(1, flee_weight * max(20, 120 - person.responsibility) // 100)
        weights: dict[str, int] = {
            "work": 25 + person.body // 3 + person.hunger + person.willpower // 4 + person.responsibility // 3,
            "aid": 4 + f[Factor.HARMONY] + f[Factor.PRESERVATION] + region.black_tide + person.empathy // 2 + person.responsibility // 3,
            "organize": 3 + person.leadership + f[Factor.ORDER] + f[Factor.HARMONY] + person.restraint // 3 + person.responsibility // 2,
            "study": 3 + person.insight + f[Factor.ERUDITION] + f[Factor.REMEMBRANCE] + region.knowledge,
            "seek": 1 + max(0, f[person.dominant_factor()] - 65) * 2 + person.resonance_years * 4 + person.ambition // 3,
            "flee": flee_weight,
            "conflict": max(1, 2 + f[Factor.HUNT] + f[Factor.DESTRUCTION] + person.courage // 3 + person.ambition // 4 - f[Factor.HARMONY] - person.restraint // 3),
        }
        if person.golden_status == "demigod":
            weights["organize"] += 50
            weights["aid"] += 30
        elif self._is_earth_candidate(person) and self._earth_stewardship_pressure(region):
            # Georios calls a candidate to visible, repeated care only once
            # their own city faces a real civic burden. Daily work in a safe
            # city is not a fire trial.
            weights["work"] += 35
            weights["aid"] += 12
            weights["organize"] += 8
        if self._is_sky_candidate(person) and region.black_tide >= 25:
            weights["aid"] += 30
            weights["organize"] += 18
        if self._is_ocean_candidate(person) and region.id == "styxia" and region.black_tide >= 25:
            # Phagousa answers detached people who nevertheless choose to
            # guide others through the polluted sea rather than withdraw.
            weights["aid"] += 36
            weights["flee"] += 12
        if self._is_law_candidate(person) and (region.tension >= 25 or region.black_tide >= 25):
            weights["organize"] += 30
            weights["aid"] += 10
        if self._is_romance_candidate(person):
            weights["aid"] += 30
            weights["organize"] += 18
        if person.life_stage() == "youth":
            weights["study"] += 50
            weights["work"] = max(1, weights["work"] // 3)
            weights["conflict"] = max(1, weights["conflict"] // 4)
        return weights

    def _choose_action(self, person: Person, region: Region) -> str:
        weights = self._action_weights(person, region)
        names = tuple(weights)
        return self.random.get(f"decision:{person.id}").choices(names, weights=tuple(weights[name] for name in names))[0]

    def _act(self, person: Person, region: Region, action: str):
        # A potential bearer of the Earth flame does not abandon a land that
        # still stands. Choosing to remain turns an attempted flight into the
        # practical work through which stewardship can be proven.
        if action == "flee" and self._is_earth_candidate(person) and region.status != "lost":
            action = "work"
        if action == "conflict" and "talanton" in person.coreflames:
            # The law-holder cannot exempt themself from the rule used to judge others.
            action = "organize"
        if action == "work":
            region.food += 1 + person.body // 45
            if region.black_tide >= 25:
                self._record_life_trace(person, "guardianship", responsibility=1)
            if region.population > region.refuge_capacity and person.body >= 55:
                self._support_refuge_crisis(person, region, 1, "参与搭建难民安置设施")
        elif action == "aid":
            person.influence += 1
            if region.black_tide >= 25:
                self._record_life_trace(person, "guardianship", responsibility=1)
            if region.black_tide >= 30 and person.social >= 65:
                region.tension = max(0, region.tension - 1)
                self._credit_impact(person, 1, "在黑潮压力下组织了救援")
                self._support_crisis(person, region, 2, "组织黑潮救援")
            if region.population > region.refuge_capacity and person.social >= 60:
                self._support_refuge_crisis(person, region, 2, "为难民争取安置与援助")
            if person.id == "tribios":
                self._credit_impact(person, 1, "在危机中传播逐火理念")
                return ("flamechase_preached", "缇里西庇俄丝以门径火种为证，向难民宣讲逐火的可能。", ("coreflame:janus",), ("idea:flame_chase:spread",), ("tribios",))
        elif action == "organize":
            person.influence += 1
            if region.black_tide >= 25:
                self._record_life_trace(person, "organization_action", responsibility=1)
            if person.leadership >= 70 and region.tension >= 45:
                region.tension = max(0, region.tension - 1)
                self._credit_impact(person, 1, "缓和了地区的派系紧张")
                self._support_crisis(person, region, 3, "协调黑潮危机")
            if region.population > region.refuge_capacity and person.leadership >= 60:
                self._support_refuge_crisis(person, region, 3, "协调难民安置与配给")
        elif action == "study":
            person.influence += int(region.black_tide >= 25)
            if region.black_tide >= 35 and person.insight >= 70:
                self._credit_impact(person, 1, "留下了关于黑潮的研究")
                self._support_crisis(person, region, 2, "研究黑潮防线")
            if region.population > region.refuge_capacity and person.insight >= 65:
                self._support_refuge_crisis(person, region, 2, "规划新的聚居地与供给路线")
        elif action == "seek":
            person.influence += 1
        elif action == "flee" and region.black_tide >= EVACUATION_TIDE_THRESHOLD:
            destinations = self._safe_refuges(region)
            if destinations:
                destination = min(destinations, key=lambda item: (item.black_tide, item.population / max(1, item.refuge_capacity)))
                person.region_id = destination.id
            elif person.golden_status == "awakened":
                person.gate_stranded_year = self.state.year
        elif action == "conflict":
            self._record_life_trace(person, "betrayal")
            # Most conflicts remain within a person's small social horizon.
            # Only a rare, capable agitator alters a whole region this year.
            person.influence += 1
            if person.leadership >= 75 and self.random.get(f"escalation:{person.id}").randint(1, 100) <= 5:
                region.order = max(0, region.order - 1)
                region.tension = min(100, region.tension + 2)
                self._credit_impact(person, 2, "煽动的冲突升级为地区危机")
        return None

    @staticmethod
    def _record_life_trace(person: Person, trace: str, responsibility: int = 0) -> None:
        person.life_traces[trace] = person.life_traces.get(trace, 0) + 1
        if responsibility:
            person.life_traces["responsibility"] = person.life_traces.get("responsibility", 0) + responsibility
            person.responsibility = min(100, person.responsibility + responsibility)

    def _credit_impact(self, person: Person, amount: int, reason: str) -> None:
        """Record causal world impact separately from repeated private actions."""
        person.world_impact += amount
        if reason not in person.impact_reasons:
            person.impact_reasons.append(reason)
            person.impact_reasons[:] = person.impact_reasons[-5:]

    def _record_earth_stewardship(self, person: Person, region: Region, action: str) -> None:
        """Turn repeated, local care during hardship into evidence for Georios."""
        if (not self._is_earth_candidate(person)
                or region.status == "lost" or not self._earth_stewardship_pressure(region)
                or action not in {"work", "aid", "organize"}):
            return
        if person.stewardship_region_id not in {None, region.id}:
            person.trial_evidence["georios"] = 0
        person.stewardship_region_id = region.id
        previous_evidence = person.trial_evidence.get("georios", 0)
        evidence = min(EARTH_STEWARDSHIP_YEARS, previous_evidence + 1)
        person.trial_evidence["georios"] = evidence
        self._credit_impact(person, 1, f"在{region.name}守土并修复土地")
        if previous_evidence < EARTH_STEWARDSHIP_YEARS == evidence:
            self._emit("earth_trial_ready", f"{person.name}在{region.name}持续守土，吉奥里亚的试炼开始回应。", (f"person:{person.id}:stewardship"), ("trial:georios:ready",), (person.id,))

    def _record_sky_passage(self, person: Person, region: Region, action: str) -> None:
        """Record a Skyward descendant keeping a refuge route open under real pressure."""
        if (not self._is_sky_candidate(person) or region.status == "lost"
                or region.black_tide < 25 or action not in {"aid", "organize", "flee"}):
            return
        if "aquila_passage_started" not in person.memories:
            person.memories.append("aquila_passage_started")
            self._emit("sky_trial_started", f"{person.name}以高天遗迹后裔的身份，在{region.name}开始维持风暴中的避难通道。", ("origin:skyward", f"black_tide:{region.id}"), ("trial:aquila:started",), (person.id,))
        previous = person.trial_evidence.get("aquila", 0)
        evidence = min(SKY_PASSAGES_REQUIRED, previous + 1)
        person.trial_evidence["aquila"] = evidence
        self._record_life_trace(person, "guardianship", responsibility=1)
        self._credit_impact(person, 1, f"在{region.name}的风暴与黑潮中维持避难通道")
        if previous < SKY_PASSAGES_REQUIRED == evidence:
            self._emit("sky_trial_ready", f"{person.name}五次守住风暴中的避难通道，艾格勒的血脉试炼开始回应。", (f"person:{person.id}:sky_passage"), ("trial:aquila:ready",), (person.id,))

    def _record_ocean_passage(self, person: Person, region: Region, action: str) -> None:
        """Record a detached guide repeatedly leading people through Styxia's polluted sea."""
        if (not self._is_ocean_candidate(person) or self.state.year < 50
                or region.id != "styxia" or region.status == "lost"
                or region.black_tide < 25 or action not in {"aid", "flee"}):
            return
        if "phagousa_passage_started" not in person.memories:
            person.memories.append("phagousa_passage_started")
            self._emit("ocean_trial_started", f"{person.name}在斯缇科西亚的污海中第一次为陌生人引航。", ("factor:nihility", "region:styxia:black_tide"), ("trial:phagousa:started",), (person.id,))
        previous = person.trial_evidence.get("phagousa", 0)
        evidence = min(OCEAN_PASSAGES_REQUIRED, previous + 1)
        person.trial_evidence["phagousa"] = evidence
        self._record_life_trace(person, "guardianship", responsibility=1)
        self._credit_impact(person, 1, "在斯缇科西亚的污海中为幸存者引航")
        if previous < OCEAN_PASSAGES_REQUIRED == evidence:
            self._emit("ocean_trial_ready", f"{person.name}五次穿过污海引导幸存者，法古萨的试炼开始回应。", (f"person:{person.id}:ocean_passage",), ("trial:phagousa:ready",), (person.id,))

    def _record_law_stewardship(self, person: Person, region: Region, action: str) -> None:
        """Talanton answers to a rule freely kept when keeping it is difficult."""
        if not self._is_law_candidate(person) or region.status == "lost":
            return
        under_pressure = region.tension >= 25 or region.black_tide >= 25
        if self.state.year < 50 or not under_pressure:
            return
        if "talanton_law_started" not in person.memories:
            if action != "organize":
                return
            person.memories.append("talanton_law_started")
            self._record_life_trace(person, "oath", responsibility=1)
            self._emit("law_trial_started", f"{person.name}在{region.name}立下约束自己与众人的守望之律。", ("factor:order",), ("trial:talanton:started",), (person.id,))
        previous = person.trial_evidence.get("talanton", 0)
        if action in {"organize", "aid"}:
            evidence = min(LAW_STEWARDSHIP_YEARS, previous + 1)
            person.trial_evidence["talanton"] = evidence
            self._record_life_trace(person, "organization_action", responsibility=1)
            self._credit_impact(person, 1, f"在{region.name}危机中遵守并执行共同之律")
            if previous < LAW_STEWARDSHIP_YEARS == evidence:
                self._emit("law_trial_ready", f"{person.name}在危机中五次守住自己立下的律法，塔兰顿开始审判。", (f"person:{person.id}:law"), ("trial:talanton:ready",), (person.id,))
        elif action == "conflict":
            person.trial_evidence["talanton"] = max(0, previous - 1)

    def _record_romance_weaving(self, person: Person, region: Region, action: str) -> None:
        """Mnestia counts distinct mutual bonds created through care, never possession."""
        real_burden = region.black_tide >= 25 or region.tension >= 35 or region.population > region.refuge_capacity
        if (not self._is_romance_candidate(person) or region.status == "lost" or action not in {"aid", "organize"}
                or self.state.year < 50 or not real_burden):
            return
        candidates = [
            relation for relation in person.relations.values()
            if relation.target_id != person.id
            and (target := self.state.people.get(relation.target_id)) is not None
            and target.alive and target.region_id == region.id and relation.trust >= 55
        ]
        if not candidates:
            return
        relation = max(candidates, key=lambda item: (item.trust, item.target_id))
        weave_memory = f"mnestia_wove:{relation.target_id}"
        if weave_memory in person.memories:
            return
        person.memories.append(weave_memory)
        previous = person.trial_evidence.get("mnestia", 0)
        person.trial_evidence["mnestia"] = min(ROMANCE_WEAVES_REQUIRED, previous + 1)
        self._record_life_trace(person, "guardianship", responsibility=1)
        self._credit_impact(person, 2, f"在{region.name}重新织起一段彼此承认的关系")
        self._emit("romance_weave", f"{person.name}在{region.name}以守护而非占有，织起一段新的相互承认。", (f"person:{relation.target_id}:relation"), ("trial:mnestia:weave"), (person.id, relation.target_id))

    @staticmethod
    def _earth_stewardship_pressure(region: Region) -> bool:
        """A land trial begins only when the city has something real to lose."""
        return (
            region.black_tide >= 50
            or (region.black_tide >= 35 and region.tension >= 50)
            or region.population > region.refuge_capacity
        )

    @staticmethod
    def _is_demigod(person: Person) -> bool:
        return person.golden_status == "demigod" or bool(person.coreflames)

    @staticmethod
    def _matches_coreflame_factor(person: Person, titan: Titan) -> bool:
        """A golden's single possible flame is fixed by their highest factor."""
        return person.dominant_factor() == titan.factor

    def _is_earth_candidate(self, person: Person) -> bool:
        """Every adult Permanence golden can begin Georios's stewardship path."""
        return (
            person.life_stage() == "adult"
            and person.golden_status == "awakened"
            and self._matches_coreflame_factor(person, self.state.titans["georios"])
        )

    def _is_sky_candidate(self, person: Person) -> bool:
        return (
            person.alive
            and person.golden_status == "awakened"
            and person.origin_region_id == "skyward"
            and self._matches_coreflame_factor(person, self.state.titans["aquila"])
            and (person.life_stage() == "adult" or "aquila_passage_started" in person.memories)
        )

    def _is_ocean_candidate(self, person: Person) -> bool:
        return (
            person.alive
            and person.golden_status == "awakened"
            and person.empathy <= 35
            and self._matches_coreflame_factor(person, self.state.titans["phagousa"])
            and (person.life_stage() == "adult" or "phagousa_passage_started" in person.memories)
        )

    def _is_law_candidate(self, person: Person) -> bool:
        return (
            person.alive
            and person.golden_status == "awakened"
            and self._matches_coreflame_factor(person, self.state.titans["talanton"])
            and (person.life_stage() == "adult" or "talanton_law_started" in person.memories)
        )

    def _is_romance_candidate(self, person: Person) -> bool:
        return (
            person.alive
            and person.golden_status == "awakened"
            and self._matches_coreflame_factor(person, self.state.titans["mnestia"])
            and person.life_stage() == "adult"
        )

    def _record_death(self, person: Person, cause: str) -> None:
        """Death remains in the world as history, rather than deleting a person."""
        if not person.alive:
            return
        person.alive = False
        person.death_year = self.state.year
        person.death_cause = cause
        if person.world_impact >= HISTORICAL_IMPACT_THRESHOLD or person.coreflames or person.golden_status != "ordinary":
            self._emit("historical_death", f"{person.name}于第{self.state.year}年离世：{cause}。", tuple(person.impact_reasons[-2:]), (f"person:{person.id}:legacy",), (person.id,))

    def _support_crisis(self, person: Person, region: Region, points: int, reason: str) -> None:
        """People choose a distinct response path inside a multi-year crisis."""
        active = [crisis for crisis in self.state.crises.values() if crisis.active and crisis.region_id == region.id]
        if not active:
            return
        crisis = max(active, key=lambda item: item.stage)
        strategy = self._choose_crisis_strategy(person, crisis)
        crisis.response_points += points
        crisis.strategy_points[strategy] += points
        crisis.participant_ids.add(person.id)
        self._credit_impact(person, 1, reason)
        required = {25: 30, 50: 70, 75: 120}[crisis.stage]
        if crisis.response_points < required:
            return
        self._settle_crisis(crisis, region, person)

    def _choose_crisis_strategy(self, person: Person, crisis: Crisis) -> str:
        factors = person.factors
        weights = {
            "hold": factors[Factor.PRESERVATION] + factors[Factor.ORDER] + person.leadership + person.body,
            "evacuate": factors[Factor.HARMONY] + factors[Factor.EQUILIBRIUM] + person.social + crisis.stage,
            "research": factors[Factor.ERUDITION] + factors[Factor.REMEMBRANCE] + person.insight + crisis.stage // 2,
        }
        if self._is_demigod(person):
            weights["hold"] += 35
        names = tuple(weights)
        return self.random.get(f"crisis_choice:{crisis.id}:{person.id}").choices(names, weights=tuple(weights[name] for name in names))[0]

    @staticmethod
    def _crisis_strategy_name(strategy: str) -> str:
        return {"hold": "死守防线", "evacuate": "撤离与分流", "research": "研究与封锁"}[strategy]

    def _settle_crisis(self, crisis: Crisis, region: Region, decisive_person: Person) -> None:
        strategy = max(crisis.strategy_points, key=lambda name: (crisis.strategy_points[name], name))
        crisis.active, crisis.resolved_year, crisis.outcome = False, self.state.year, strategy
        tide_drop = {25: 4, 50: 8, 75: 12}[crisis.stage]
        defense_gain = {25: 3, 50: 6, 75: 10}[crisis.stage]
        if strategy == "hold":
            defense_gain += 3
            region.order = min(100, region.order + 3)
        elif strategy == "evacuate":
            self._evacuate_crisis_population(region, crisis.stage)
            region.tension = max(0, region.tension - 14)
        else:
            region.knowledge = min(100, region.knowledge + 5)
            tide_drop += 4
        region.black_tide = max(region.tide_source, region.black_tide - tide_drop)
        region.tension = max(0, region.tension - 10)
        region.defense = min(40, region.defense + defense_gain)
        region.scars += 1
        self._credit_impact(decisive_person, 5, f"以{self._crisis_strategy_name(strategy)}稳定{region.name}的黑潮危机")
        self._emit("black_tide_crisis_stabilized", f"{region.name}以“{self._crisis_strategy_name(strategy)}”暂时稳定黑潮危机，留下防线与伤痕。", (f"crisis:{crisis.id}",), (f"black_tide:{region.id}:reduced", f"defense:{region.id}:+{defense_gain}"), tuple(sorted(crisis.participant_ids)[:5]))

    def _evacuate_crisis_population(self, region: Region, stage: int) -> None:
        """Evacuation preserves people only where another city can truly house them."""
        remaining = min(region.population // 3, max(50, region.population * stage // 500))
        for destination in sorted(
            (self.state.regions[key] for key in region.neighbours),
            key=lambda item: (item.black_tide, item.population / max(1, item.refuge_capacity), item.id),
        ):
            space = max(0, destination.refuge_capacity - destination.population)
            moved = min(remaining, space)
            if not moved:
                continue
            region.population -= moved
            destination.population += moved
            remaining -= moved
            if not remaining:
                break

    def _support_refuge_crisis(self, person: Person, region: Region, points: int, reason: str) -> None:
        """Contribute to a single overcrowding wave through a civic strategy."""
        active = [crisis for crisis in self.state.refuge_crises.values() if crisis.active and crisis.region_id == region.id]
        if not active:
            return
        crisis = max(active, key=lambda item: (item.started_year, item.id))
        strategy = self._choose_refuge_strategy(person, region)
        crisis.response_points += points
        crisis.strategy_points[strategy] += points
        crisis.participant_ids.add(person.id)
        self._credit_impact(person, 1, reason)
        if crisis.response_points >= 36:
            self._settle_refuge_crisis(crisis, region, person)

    def _choose_refuge_strategy(self, person: Person, region: Region) -> str:
        factors = person.factors
        overflow = max(0, region.population - region.refuge_capacity)
        weights = {
            "welcome": factors[Factor.HARMONY] + factors[Factor.PRESERVATION] + person.social + overflow // 200,
            "ration": factors[Factor.ORDER] + factors[Factor.EQUILIBRIUM] + person.leadership + person.insight,
            "settle": factors[Factor.PERMANENCE] + factors[Factor.ERUDITION] + person.body + person.leadership,
        }
        if self._is_demigod(person):
            weights["welcome"] += 25
        names = tuple(weights)
        return self.random.get(f"refuge_choice:{region.id}:{person.id}").choices(names, weights=tuple(weights[name] for name in names))[0]

    @staticmethod
    def _refuge_strategy_name(strategy: str) -> str:
        return {"welcome": "接纳与共居", "ration": "配给与重整", "settle": "开辟新聚居地"}[strategy]

    def _settle_refuge_crisis(self, crisis: RefugeCrisis, region: Region, decisive_person: Person) -> None:
        strategy = max(crisis.strategy_points, key=lambda name: (crisis.strategy_points[name], name))
        crisis.active, crisis.resolved_year, crisis.outcome = False, self.state.year, strategy
        overflow = max(0, region.population - region.refuge_capacity)
        if strategy == "welcome":
            expansion = 0
            region.food = max(0, region.food - max(40, overflow // 5))
            region.tension = max(0, region.tension - 10)
            region.order = min(100, region.order + 2)
        elif strategy == "ration":
            expansion = 0
            region.food += max(60, region.population // 30)
            region.tension = max(0, region.tension - 6)
            region.order = min(100, region.order + 7)
        else:
            available = max(0, region.refuge_capacity_limit - region.refuge_capacity)
            expansion = min(available, max(0, min(max(280, overflow // 2), region.refuge_capacity // 20)))
            region.food = max(0, region.food - max(80, expansion // 3))
            region.knowledge = min(100, region.knowledge + 3)
            region.tension = min(100, region.tension + 2)
            region.scars += 1
        region.refuge_capacity += expansion
        self._credit_impact(decisive_person, 5, f"以{self._refuge_strategy_name(strategy)}化解{region.name}的难民危机")
        capacity_result = f"新增约{expansion}人的庇护能力" if expansion else "未增加固定庇护容量"
        self._emit("refuge_crisis_stabilized", f"{region.name}以“{self._refuge_strategy_name(strategy)}”应对难民潮，{capacity_result}。", (f"refuge_crisis:{crisis.id}",), (f"refuge_capacity:{region.id}:+{expansion}",), tuple(sorted(crisis.participant_ids)[:5]))

    def _resolve_relationships(self, person: Person, action: str) -> None:
        """Actions alter only known, nearby people; this remains linear at 1000 people."""
        nearby = [relation for relation in person.relations.values()
                  if (target := self.state.people.get(relation.target_id)) and target.alive and target.region_id == person.region_id]
        if not nearby:
            return
        relation = self.random.get(f"relationship:{person.id}").choice(nearby)
        target = self.state.people[relation.target_id]
        counterpart = target.relations.get(person.id)
        trust_change = {"aid": 5, "organize": 3, "study": 1, "work": 1, "seek": 0, "flee": -2, "conflict": -8}[action]
        relation.trust = max(-100, min(100, relation.trust + trust_change))
        relation.last_interaction_year = self.state.year
        if counterpart:
            counterpart.trust = max(-100, min(100, counterpart.trust + trust_change))
            counterpart.last_interaction_year = self.state.year
        if action == "aid":
            relation.debt = min(100, relation.debt + 1)
        elif action == "conflict":
            relation.fear = min(100, relation.fear + 4)
        elif action == "organize" and relation.trust >= 65 and relation.oath is None:
            relation.oath = "共同守望"
            self._record_life_trace(person, "oath", responsibility=1)
            if counterpart:
                counterpart.oath = "共同守望"
                self._record_life_trace(target, "oath", responsibility=1)

    def _form_social_ties(self, person: Person) -> None:
        """Young and adult people form local ties as older networks disappear."""
        if person.life_stage() not in {"youth", "adult"} or len(person.relations) >= 16:
            return
        rng = self.random.get(f"socialize:{person.id}")
        if rng.randint(1, 100) > min(45, 8 + person.social // 2):
            return
        candidates = [
            other for other in self._people_by_region.get(person.region_id, ())
            if other.id != person.id and other.id not in person.relations
            and other.life_stage() in {"youth", "adult"} and len(other.relations) < 16
            and abs(other.age - person.age) <= 12 and not self._share_parent(person, other)
        ]
        if not candidates:
            return
        other = max(candidates, key=lambda candidate: (candidate.social + candidate.factors[Factor.HARMONY], candidate.id))
        partner_score = person.social + other.social + person.factors[Factor.HARMONY] + other.factors[Factor.HARMONY]
        if person.life_stage() == other.life_stage() == "adult" and partner_score >= 150 and rng.randint(1, 100) <= 25:
            kind, trust, oath = "伴侣", rng.randint(55, 80), "共度危机"
        else:
            kind = "同窗" if person.life_stage() == "youth" else rng.choice(("友人", "同业", "同行者"))
            trust, oath = rng.randint(25, 55), None
        person.relations[other.id] = Relation(other.id, kind, trust, oath=oath, last_interaction_year=self.state.year)
        other.relations[person.id] = Relation(person.id, kind, trust, oath=oath, last_interaction_year=self.state.year)

    @staticmethod
    def _share_parent(first: Person, second: Person) -> bool:
        return bool(set(first.parent_ids) & set(second.parent_ids))

    def _resolve_organizations(self) -> None:
        """Organizations recruit locally; their members turn individual action into social force."""
        for organization in self.state.organizations.values():
            region = self.state.regions[organization.region_id]
            if region.status == "lost":
                for person_id in organization.member_ids:
                    person = self.state.people.get(person_id)
                    if person and person.organization_id == organization.id:
                        person.organization_id = None
                organization.member_ids, organization.leader_id, organization.influence = set(), None, 0
                continue
            members = [self.state.people[person_id] for person_id in organization.member_ids if self.state.people[person_id].alive]
            organization.member_ids = {person.id for person in members}
            if not members:
                organization.influence = max(0, organization.influence - 1)
                continue
            if organization.leader_id not in organization.member_ids:
                organization.leader_id = max(members, key=lambda person: (person.leadership, person.influence, person.id)).id
            organization.influence = min(100, organization.influence + max(0, len(members) // 8))
            # Institutions act once at the group scale, and their benefits are
            # bounded by the stress that they also have to maintain.
            if organization.kind in {"城邦", "神殿", "民兵"} and organization.influence >= 20 and region.order < 82:
                region.order += 1
            if organization.kind == "学社" and organization.influence >= 25 and region.knowledge < 84:
                region.knowledge += 1
            if organization.kind == "商盟" and organization.influence >= 20:
                region.food += max(10, region.population // 2000)
            if organization.kind == "民兵" and region.black_tide >= 35:
                region.tension = max(0, region.tension - 1)
            candidates = [person for person in self._residents(organization.region_id)
                          if person.organization_id is None and person.life_stage() != "child"]
            if not candidates:
                continue
            leader = self.state.people[organization.leader_id]
            def appeal(candidate: Person) -> int:
                base = candidate.social + candidate.leadership + candidate.relations.get(leader.id, Relation(leader.id, "陌生", 0)).trust
                if organization.id == "flamechase":
                    base += candidate.factors[Factor.HARMONY] + candidate.factors[Factor.REMEMBRANCE]
                return base
            recruit = max(candidates, key=lambda person: (appeal(person), person.id))
            if appeal(recruit) >= 70:
                recruit.organization_id = organization.id
                organization.member_ids.add(recruit.id)
                recruit.influence += 2
                if organization.id == "flamechase":
                    self._credit_impact(leader, 2, "使新的追随者加入逐火传播团")
                    self._emit("flamechase_recruitment", f"{recruit.name}响应缇里西庇俄丝的逐火宣讲，加入逐火传播团。", ("idea:flame_chase",), (f"organization:{organization.id}:+1",), ("tribios", recruit.id))

    def _resolve_coreflame_trials(self) -> None:
        """Resolve the implemented trials; a fire is never granted from a stat alone."""
        self._resolve_sky_trial()
        self._resolve_ocean_trial()
        self._resolve_earth_trial()
        self._resolve_law_trial()
        self._resolve_romance_trial()
        self._resolve_reason_trial()
        definitions = {
            "nikador": ("纷争火种试炼", lambda r: r.tension >= 58 and r.black_tide >= 20, Factor.HUNT),
            "thanatos": ("死亡火种试炼", lambda r: r.black_tide >= 48 and r.population > 0, Factor.EQUILIBRIUM),
        }
        for titan_id, (trial_name, condition, factor) in definitions.items():
            titan = self.state.titans[titan_id]
            if titan.coreflame_holder is not None:
                continue
            region = self.state.regions[titan.region_id]
            if region.status == "lost":
                titan.trial_progress = max(0, titan.trial_progress - 1)
                continue
            if not condition(region):
                titan.trial_progress = max(0, titan.trial_progress - 1)
                continue
            candidates = [p for p in self._residents(region.id)
                          if p.life_stage() == "adult" and p.golden_status in {"awakened", "demigod"}
                          and p.factors[factor] >= 70 and self._matches_coreflame_factor(p, titan)]
            if not candidates:
                continue
            candidate = max(candidates, key=lambda p: (p.factors[factor] + p.resonance_years * 3 + p.world_impact, p.id))
            gain = 3 + candidate.resonance_years // 2 + candidate.factors[factor] // 20
            titan.trial_progress = min(100, titan.trial_progress + gain)
            self._credit_impact(candidate, 1, f"推进{trial_name}")
            if titan.trial_progress < 100:
                continue
            self._inherit_coreflame(titan, candidate, trial_name)

    def _resolve_sky_trial(self) -> None:
        titan = self.state.titans["aquila"]
        if titan.coreflame_status != "within_titan":
            return
        candidates = [
            person for person in self.state.people.values()
            if self._is_sky_candidate(person)
            and person.trial_evidence.get("aquila", 0) >= SKY_PASSAGES_REQUIRED
            and "witnessed_skyward_fall" in person.memories
            and self.state.regions[person.region_id].status != "lost"
        ]
        if not candidates:
            titan.trial_progress = max(0, titan.trial_progress - 1)
            return
        candidate = max(candidates, key=lambda person: (
            person.courage + person.body + person.leadership
            + person.life_traces.get("guardianship", 0) + person.world_impact,
            person.id,
        ))
        titan.trial_progress = min(100, titan.trial_progress + 6)
        self._credit_impact(candidate, 1, "推进艾格勒的高天血脉试炼")
        if titan.trial_progress >= 100:
            titan.authority_state = {"storm_burden": 0, "warnings_issued": 0, "healing_used": 0}
            self._inherit_coreflame(titan, candidate, "高天血脉与避难通道试炼")

    def _resolve_ocean_trial(self) -> None:
        titan = self.state.titans["phagousa"]
        if titan.coreflame_status != "within_titan":
            return
        candidates = [
            person for person in self.state.people.values()
            if self._is_ocean_candidate(person)
            and person.trial_evidence.get("phagousa", 0) >= OCEAN_PASSAGES_REQUIRED
            and self.state.regions[person.region_id].status != "lost"
        ]
        if not candidates:
            titan.trial_progress = max(0, titan.trial_progress - 1)
            return
        candidate = max(candidates, key=lambda person: (
            100 - person.empathy + person.adaptability + person.willpower
            + person.life_traces.get("guardianship", 0) + person.world_impact,
            person.id,
        ))
        titan.trial_progress = min(100, titan.trial_progress + 7)
        self._credit_impact(candidate, 1, "推进法古萨的污海引航试炼")
        if titan.trial_progress >= 100:
            titan.authority_state = {"anchor_id": "", "voyages": 0, "pollution_burden": 0}
            self._inherit_coreflame(titan, candidate, "污海引航与无情之心试炼")

    def _resolve_law_trial(self) -> None:
        titan = self.state.titans["talanton"]
        if titan.coreflame_status != "within_titan":
            return
        candidates = [
            person for person in self.state.people.values()
            if self._is_law_candidate(person)
            and person.trial_evidence.get("talanton", 0) >= LAW_STEWARDSHIP_YEARS
            and self.state.regions[person.region_id].status != "lost"
        ]
        if not candidates:
            titan.trial_progress = max(0, titan.trial_progress - 1)
            return
        candidate = max(candidates, key=lambda person: (
            person.leadership + person.insight + person.restraint + person.world_impact, person.id,
        ))
        titan.trial_progress = min(100, titan.trial_progress + 8)
        self._credit_impact(candidate, 1, "推进塔兰顿的自律审判")
        if titan.trial_progress >= 100:
            titan.authority_state = {"bound_organization_id": candidate.organization_id or "", "rigidity": 0}
            self._inherit_coreflame(titan, candidate, "受自身之法审判")

    def _resolve_romance_trial(self) -> None:
        titan = self.state.titans["mnestia"]
        if titan.coreflame_status != "within_titan":
            return
        candidates = [
            person for person in self.state.people.values()
            if self._is_romance_candidate(person)
            and person.trial_evidence.get("mnestia", 0) >= ROMANCE_WEAVES_REQUIRED
            and self.state.regions[person.region_id].status != "lost"
        ]
        if not candidates:
            titan.trial_progress = max(0, titan.trial_progress - 1)
            return
        candidate = max(candidates, key=lambda person: (
            person.empathy + person.social + person.life_traces.get("guardianship", 0) + person.world_impact, person.id,
        ))
        titan.trial_progress = min(100, titan.trial_progress + 9)
        self._credit_impact(candidate, 1, "推进墨涅塔的编织试炼")
        if titan.trial_progress >= 100:
            titan.authority_state = {"weave_count": 0, "emotional_burden": 0}
            self._inherit_coreflame(titan, candidate, "为他人编织、而非占有")

    @staticmethod
    def _reason_exam_years(person: Person) -> int:
        """Map wisdom to 20..5 years per exam on an exponential curve."""
        wisdom = (person.factors[Factor.ERUDITION] + person.insight) / 2
        normalized = max(0.0, min(1.0, (wisdom - 40) / 60))
        return max(5, min(20, round(20 * (0.25 ** normalized))))

    def _is_reason_candidate(self, person: Person) -> bool:
        return (
            person.alive
            and person.golden_status == "awakened"
            and self._matches_coreflame_factor(person, self.state.titans["cerces"])
            and (person.life_stage() == "adult" or "cerces_exam_started" in person.memories)
        )

    def _resolve_reason_trial(self) -> None:
        """Run the four deterministic Cerces examinations for every candidate."""
        titan = self.state.titans["cerces"]
        if titan.coreflame_status != "within_titan":
            return
        candidates = sorted(
            (person for person in self.state.people.values() if self._is_reason_candidate(person)),
            key=lambda person: person.id,
        )
        for candidate in candidates:
            if "cerces_exam_started" not in candidate.memories:
                candidate.memories.append("cerces_exam_started")
                self._emit("reason_exam_started", f"{candidate.name}开始参加瑟希斯四证。", ("factor:erudition",), ("trial:cerces:started",), (candidate.id,))
            exam_index = candidate.trial_evidence.get("cerces_exam_index", 0)
            if exam_index >= len(REASON_EXAMS):
                continue
            years = candidate.trial_evidence.get("cerces_exam_years", 0) + 1
            required = self._reason_exam_years(candidate)
            candidate.trial_evidence["cerces_exam_years"] = years
            if years >= required:
                exam_name = REASON_EXAMS[exam_index]
                exam_index += 1
                candidate.trial_evidence["cerces_exam_index"] = exam_index
                candidate.trial_evidence["cerces_exam_years"] = 0
                self._credit_impact(candidate, 2, f"通过瑟希斯四证·{exam_name}")
                self._emit("reason_exam_passed", f"{candidate.name}通过瑟希斯四证的“{exam_name}”。", (f"wisdom:{round((candidate.factors[Factor.ERUDITION] + candidate.insight) / 2)}",), (f"trial:cerces:exam:{exam_index}",), (candidate.id,))
            completed = candidate.trial_evidence.get("cerces_exam_index", 0)
            current_years = candidate.trial_evidence.get("cerces_exam_years", 0)
            progress = (completed + current_years / max(1, required)) / len(REASON_EXAMS)
            titan.trial_progress = max(titan.trial_progress, min(100, round(progress * 100)))
            if completed >= len(REASON_EXAMS):
                titan.authority_state = {"created_demigod_ids": []}
                self._inherit_coreflame(titan, candidate, "瑟希斯四证")
                return

    def _resolve_earth_trial(self) -> None:
        titan = self.state.titans["georios"]
        if titan.coreflame_status != "within_titan":
            return
        candidates = [
            person for person in self.state.people.values()
            if person.alive and self._is_earth_candidate(person)
            and person.trial_evidence.get("georios", 0) >= EARTH_STEWARDSHIP_YEARS
            and person.stewardship_region_id == person.region_id
            and self.state.regions[person.region_id].status != "lost"
        ]
        if not candidates:
            titan.trial_progress = max(0, titan.trial_progress - 1)
            return
        candidate = max(candidates, key=lambda person: (
            person.trial_evidence["georios"], person.factors[Factor.PERMANENCE], person.body, person.world_impact, person.id,
        ))
        gain = 4 + candidate.trial_evidence["georios"] // 2
        titan.trial_progress = min(100, titan.trial_progress + gain)
        self._credit_impact(candidate, 1, "推进吉奥里亚的守土者试炼")
        if titan.trial_progress >= 100:
            candidate.bound_region_id = candidate.region_id
            titan.authority_state = {"bonded_region_id": candidate.region_id, "land_burden": 0}
            self._inherit_coreflame(titan, candidate, "大地火种试炼")

    def _inherit_coreflame(self, titan: Titan, candidate: Person, trial_name: str) -> None:
        """Apply the shared state change for a successful fire trial."""
        was_awakened = candidate.golden_status == "awakened"
        titan.coreflame_holder = candidate.id
        titan.coreflame_status = "held"
        titan.coreflame_returned_year = None
        titan.authority_state["inherited_year"] = self.state.year
        if titan.id not in candidate.coreflames:
            candidate.coreflames.append(titan.id)
        candidate.golden_status = "demigod"
        titan.stability = min(100, titan.stability + 18)
        titan.corruption = max(0, titan.corruption - 15)
        self._credit_impact(candidate, 25, f"通过{trial_name}并承接{titan.domain}火种")
        self._emit("coreflame_inherited", f"{candidate.name}通过{trial_name}，承接了{titan.name}的{titan.domain}火种。", (f"titan:{titan.id}", f"factor:{titan.factor.value}"), (f"coreflame:{titan.id}:inherited",), (candidate.id,))
        reason = self.state.titans["cerces"]
        if titan.id != "cerces" and was_awakened and reason.coreflame_status == "held":
            created_ids = list(reason.authority_state.get("created_demigod_ids", []))
            if candidate.id not in created_ids:
                created_ids.append(candidate.id)
                reason.authority_state["created_demigod_ids"] = created_ids
                holder = self.state.people.get(reason.coreflame_holder or "")
                if holder is not None and holder.alive:
                    self._credit_impact(holder, 8, f"以理性权能培养出半神{candidate.name}")
                    self._emit("reason_demigod_created", f"{candidate.name}在{holder.name}的理性教导下通过{titan.name}火种试炼，成为半神；权能已完成 {len(created_ids)}/{REASON_GOLDEN_QUOTA}。", ("coreflame:cerces", f"coreflame:{titan.id}:inherited"), (f"person:{candidate.id}:demigod",), (holder.id, candidate.id))

    def _return_coreflame(self, titan: Titan, holder: Person, reason: str) -> None:
        """Return a fire to the world without erasing the holder's history."""
        if titan.id in holder.coreflames:
            holder.coreflames.remove(titan.id)
        if titan.id not in holder.returned_coreflames:
            holder.returned_coreflames.append(titan.id)
        titan.coreflame_holder = None
        titan.coreflame_status = "returned"
        titan.coreflame_returned_year = self.state.year
        self._emit("coreflame_returned", f"{holder.name}将{titan.name}的{titan.domain}火种归还创世涡心：{reason}。", (f"coreflame:{titan.id}:held"), (f"coreflame:{titan.id}:returned",), (holder.id,))
        if titan.id != "phagousa":
            self._follow_ocean_anchor_sacrifice(holder)

    def _follow_ocean_anchor_sacrifice(self, anchor: Person) -> None:
        """The Ocean holder follows only when their chosen demi-god returns a fire."""
        ocean = self.state.titans["phagousa"]
        if (ocean.coreflame_status != "held" or ocean.coreflame_holder is None
                or ocean.authority_state.get("anchor_id") != anchor.id):
            return
        holder = self.state.people.get(ocean.coreflame_holder)
        if holder is None or not holder.alive or holder.id == anchor.id:
            return
        for region in self.state.regions.values():
            if region.status == "lost":
                continue
            region.tide_source = max(0, region.tide_source - 2)
            region.black_tide = max(region.tide_source, region.black_tide - 2)
        self._return_coreflame(ocean, holder, f"唯一羁绊{anchor.name}主动献祭后，选择与其同行")
        self._record_death(holder, f"唯一羁绊{anchor.name}献祭后，随其归还海洋火种")
        self._emit("ocean_anchor_sacrifice", f"{anchor.name}主动献祭后，{holder.name}循唯一羁绊而去，与海洋火种一同归还；幸存城邦的黑潮残留源随之减弱。", (f"person:{anchor.id}:sacrifice", "coreflame:phagousa"), ("sacrifice:phagousa:followed_anchor", "black_tide_sources:reduced"), (anchor.id, holder.id))

    def _resolve_gate_authority(self) -> None:
        """Janus opens a final route for an awakened person stranded while fleeing."""
        titan = self.state.titans["janus"]
        if titan.coreflame_status != "held" or titan.coreflame_holder is None:
            return
        holder = self.state.people.get(titan.coreflame_holder)
        charges = int(titan.authority_state.get("rescue_charges", 0))
        okhema = self.state.regions["okhema"]
        if holder is None or not holder.alive or charges <= 0 or okhema.status == "lost":
            return
        candidates = [
            person for person in self.state.people.values()
            if person.alive and person.golden_status == "awakened"
            and person.region_id != "okhema" and person.gate_stranded_year == self.state.year
        ]
        if not candidates:
            return
        rescued = min(candidates, key=lambda person: (person.health, -self.state.regions[person.region_id].black_tide, person.id))
        origin = self.state.regions[rescued.region_id]
        rescued.region_id = "okhema"
        rescued.health = max(35, rescued.health)
        titan.authority_state["rescue_charges"] = charges - 1
        self._credit_impact(holder, 5, f"以门径火种救回濒死的黄金裔候选{rescued.name}")
        rescued.gate_stranded_year = None
        self._emit("gate_rescue", f"{rescued.name}试图逃离{origin.name}却发现道路断绝；{holder.name}打开门径，将其送回奥赫玛；剩余额度 {charges - 1}。", (f"region:{origin.id}:black_tide", f"person:{rescued.id}:stranded"), (f"person:{rescued.id}:relocated:okhema", "authority:janus:rescue"), (holder.id, rescued.id))
        if charges - 1 == 0:
            self._return_coreflame(titan, holder, "门径额度在最后一次救援中耗尽")
            self._record_death(holder, "门径火种额度耗尽后，为最后的通路献祭")

    def _resolve_sky_authority(self) -> None:
        """Aquila warns the most threatened surviving city and reinforces its refuge route."""
        titan = self.state.titans["aquila"]
        if titan.coreflame_status != "held" or titan.coreflame_holder is None:
            return
        holder = self.state.people.get(titan.coreflame_holder)
        if holder is None or not holder.alive:
            return
        threatened = [
            region for region in self.state.regions.values()
            if region.status != "lost" and region.black_tide >= 25
        ]
        if not threatened:
            return
        region = max(threatened, key=lambda item: (item.black_tide + item.tension, item.population, item.id))
        before_defense = region.defense
        region.defense = min(40, region.defense + 1)
        titan.authority_state["warnings_issued"] = int(titan.authority_state.get("warnings_issued", 0)) + 1
        if region.black_tide >= 50:
            titan.authority_state["storm_burden"] = int(titan.authority_state.get("storm_burden", 0)) + 1
            holder.health = max(1, holder.health - 1)
        if self.state.year % 5 == 0:
            defense_gain = region.defense - before_defense
            self._emit("sky_warning", f"{holder.name}预见{region.name}上空的黑潮风暴，提前维持避难通道与防线。", ("coreflame:aquila", f"black_tide:{region.id}"), (f"defense:{region.id}:+{defense_gain}", "authority:aquila:warning"), (holder.id,))

    def _resolve_ocean_authority(self) -> None:
        """Phagousa creates sea routes and binds its holder to one non-Worldbearer demi-god."""
        titan = self.state.titans["phagousa"]
        if titan.coreflame_status != "held" or titan.coreflame_holder is None:
            return
        holder = self.state.people.get(titan.coreflame_holder)
        if holder is None or not holder.alive:
            return

        anchor_id = str(titan.authority_state.get("anchor_id", ""))
        if not anchor_id:
            worldbearer_id = self.state.titans["kephale"].coreflame_holder
            candidates = [
                person for person in self.state.people.values()
                if person.alive and person.id != holder.id and person.id != worldbearer_id
                and person.golden_status == "demigod" and bool(person.coreflames)
            ]
            if candidates:
                anchor = min(candidates, key=lambda person: (person.region_id != holder.region_id, person.id))
                titan.authority_state["anchor_id"] = anchor.id
                holder.relations[anchor.id] = Relation(anchor.id, "唯一羁绊", 70, oath="污海同行", last_interaction_year=self.state.year)
                anchor.relations[holder.id] = Relation(holder.id, "唯一羁绊", 70, oath="污海同行", last_interaction_year=self.state.year)
                self._emit("ocean_anchor", f"{holder.name}第一次真正看见了{anchor.name}，并将这名半神视作唯一羁绊。", ("coreflame:phagousa", f"person:{anchor.id}:demigod"), (f"relation:{holder.id}:{anchor.id}:unique_anchor",), (holder.id, anchor.id))

        if self.state.year % 3 != 0:
            return
        sources = [
            region for region in self.state.regions.values()
            if region.status != "lost" and region.black_tide >= 35 and region.population > 0
        ]
        if not sources:
            return
        source = max(sources, key=lambda region: (region.black_tide, region.population, region.id))
        destinations = [
            region for region in self.state.regions.values()
            if region.id != source.id and region.status != "lost"
            and region.black_tide < source.black_tide
            and region.population < region.refuge_capacity * 9 // 10
        ]
        if not destinations:
            return
        destination = min(destinations, key=lambda region: (region.black_tide, region.population / max(1, region.refuge_capacity), region.id))
        safe_space = max(0, destination.refuge_capacity * 9 // 10 - destination.population)
        passengers = min(source.population, safe_space, 120, max(20, source.population // 500))
        if passengers <= 0:
            return
        source.population -= passengers
        destination.population += passengers

        supplies = min(40, max(0, destination.food - destination.population // 5))
        destination.food -= supplies
        source.food += supplies
        if source.black_tide > source.tide_source:
            source.black_tide -= 1
        burden_region = self.state.regions.get(holder.region_id)
        if burden_region is not None and burden_region.id != source.id and burden_region.status != "lost":
            burden_region.black_tide = min(100, burden_region.black_tide + 1)
        titan.authority_state["voyages"] = int(titan.authority_state.get("voyages", 0)) + 1
        titan.authority_state["pollution_burden"] = int(titan.authority_state.get("pollution_burden", 0)) + 1
        holder.health = max(1, holder.health - 1)
        self._credit_impact(holder, 2, f"开辟从{source.name}到{destination.name}的污海航路")
        self._emit("ocean_voyage", f"{holder.name}开辟污海航路，将{passengers}名居民从{source.name}送往{destination.name}，并逆向运回{supplies}份补给。", ("coreflame:phagousa", f"black_tide:{source.id}"), (f"population:{source.id}:-{passengers}", f"population:{destination.id}:+{passengers}", "authority:phagousa:pollution_transfer"), (holder.id,))

    def _trigger_sky_healing(self, region: Region) -> bool:
        """Spend Aquila once to cancel Okhema's otherwise irreversible fall."""
        titan = self.state.titans["aquila"]
        if (region.id != "okhema" or titan.coreflame_status != "held"
                or titan.coreflame_holder is None or int(titan.authority_state.get("healing_used", 0))):
            return False
        holder = self.state.people.get(titan.coreflame_holder)
        if holder is None or not holder.alive:
            return False
        before_tide = region.black_tide
        titan.authority_state["healing_used"] = 1
        region.tide_source = max(5, region.tide_source - 20)
        region.black_tide = max(region.tide_source, min(35, region.black_tide - 40))
        region.collapse_years = 0
        region.order = min(100, region.order + 20)
        region.tension = max(0, region.tension - 20)
        region.defense = min(40, region.defense + 12)
        region.food = max(region.food, region.population // 2)
        region.scars = max(0, region.scars - 2)
        region.status = "endangered" if region.black_tide >= 50 else "stable"
        self._return_coreflame(titan, holder, "在奥赫玛不可逆坠落前发动唯一一次天空治愈")
        self._record_death(holder, "以自身与天空火种治愈奥赫玛，为旧世界争取新的存续期")
        self._emit("sky_healing", f"奥赫玛即将不可逆失陷时，{holder.name}献祭自身发动天空治愈；黑潮由 {before_tide} 降至 {region.black_tide}，城邦避免了这次坠落。", ("region:okhema:collapse_imminent", "coreflame:aquila"), ("region:okhema:fall_prevented", f"black_tide:okhema:{region.black_tide}"), (holder.id,))
        return True

    def _resolve_earth_authority(self) -> None:
        """A Georios holder heals their bonded land, then founds a final refuge."""
        titan = self.state.titans["georios"]
        if titan.coreflame_status != "held" or titan.coreflame_holder is None:
            return
        holder = self.state.people.get(titan.coreflame_holder)
        if holder is None or not holder.alive:
            return
        region_id = holder.bound_region_id or str(titan.authority_state.get("bonded_region_id", ""))
        region = self.state.regions.get(region_id)
        if region is not None and region.status != "lost":
            food_restored = max(100, region.population // 100)
            region.food += food_restored
            region.defense = min(40, region.defense + 1)
            if region.black_tide > region.tide_source:
                region.black_tide -= 1
            if region.scars:
                region.scars -= 1
                titan.authority_state["land_burden"] = int(titan.authority_state.get("land_burden", 0)) + 1
            if self.state.year % 5 == 0:
                self._emit("earth_restoration", f"{holder.name}与{region.name}的土地共同承受伤痕，恢复了粮食、工事与生机。", (f"coreflame:georios",), (f"food:{region.id}:+{food_restored}", f"defense:{region.id}:+1"), (holder.id,))
        lost_regions = sum(item.status == "lost" for item in self.state.regions.values())
        inherited_year = int(titan.authority_state.get("inherited_year", self.state.year))
        holding_years = self.state.year - inherited_year
        if (lost_regions >= 5 and holding_years >= EARTH_MIN_HOLDING_YEARS
                and self.state.regions["okhema"].status != "lost"
                and "georios_foundation" not in self.state.regions):
            self._found_earth_foundation(holder, titan)

    def _resolve_law_authority(self) -> None:
        """Talanton makes a city governable, while accumulated rigidity has a cost."""
        titan = self.state.titans["talanton"]
        if titan.coreflame_status != "held" or titan.coreflame_holder is None:
            return
        holder = self.state.people.get(titan.coreflame_holder)
        if holder is None or not holder.alive:
            return
        region = self.state.regions.get(holder.region_id)
        if region is not None and region.status != "lost":
            region.order = min(100, region.order + 2)
            region.tension = max(0, region.tension - 1)
            rigidity = int(titan.authority_state.get("rigidity", 0)) + 1
            titan.authority_state["rigidity"] = rigidity
            if rigidity >= 12 and rigidity % 4 == 0:
                region.tension = min(100, region.tension + 1)
                self._emit("law_rigidity", f"{holder.name}维持的律法在{region.name}过于严密，秩序之外开始积累新的紧张。", ("coreflame:talanton",), (f"tension:{region.id}:+1",), (holder.id,))
        returned_count = sum(item.coreflame_status == "returned" for item in self.state.titans.values())
        if returned_count >= 10:
            self._return_coreflame(titan, holder, "在诸火归还后放弃一切特权，使律法同样约束自己")
            self._record_death(holder, "放弃律法赋予的一切例外，为共同之律献祭")

    def _resolve_romance_authority(self) -> None:
        """Mnestia reconnects isolated survivors and spends its holder's emotional strength."""
        titan = self.state.titans["mnestia"]
        if titan.coreflame_status != "held" or titan.coreflame_holder is None:
            return
        holder = self.state.people.get(titan.coreflame_holder)
        if holder is None or not holder.alive:
            return
        region = self.state.regions.get(holder.region_id)
        if region is not None and region.status != "lost":
            residents = [person for person in self._residents(region.id) if person.id != holder.id]
            pairs = [
                (first, second) for index, first in enumerate(residents)
                for second in residents[index + 1:]
                if second.id not in first.relations
            ]
            if pairs:
                first, second = min(pairs, key=lambda pair: (len(pair[0].relations) + len(pair[1].relations), pair[0].id, pair[1].id))
                first.relations[second.id] = Relation(second.id, "相识者", 45, oath="互相扶持", last_interaction_year=self.state.year)
                second.relations[first.id] = Relation(first.id, "相识者", 45, oath="互相扶持", last_interaction_year=self.state.year)
                titan.authority_state["weave_count"] = int(titan.authority_state.get("weave_count", 0)) + 1
                self._credit_impact(holder, 2, f"令{first.name}与{second.name}在{region.name}相互扶持")
                self._emit("romance_authority_weave", f"{holder.name}令{first.name}与{second.name}在{region.name}相识并互相扶持。", ("coreflame:mnestia",), ("relation:mutual_aid:created",), (holder.id, first.id, second.id))
            region.tension = max(0, region.tension - 1)
            if self.state.year % 3 == 0:
                burden = int(titan.authority_state.get("emotional_burden", 0)) + 1
                titan.authority_state["emotional_burden"] = burden
                self._record_life_trace(holder, "loss")
        lost_regions = sum(item.status == "lost" for item in self.state.regions.values())
        weave_count = int(titan.authority_state.get("weave_count", 0))
        cherished = [relation for relation in holder.relations.values() if relation.trust >= 70]
        if lost_regions >= 5 and weave_count >= ROMANCE_SACRIFICE_WEAVES and cherished:
            cherished_relation = max(cherished, key=lambda relation: (relation.trust, relation.target_id))
            counterpart = self.state.people.get(cherished_relation.target_id)
            if counterpart is not None and holder.id in counterpart.relations:
                counterpart.relations[holder.id].oath = "永恒纪念"
            self._return_coreflame(titan, holder, "将最珍视的情感编入幸存者彼此相认的纽带")
            self._record_death(holder, "将最珍视的情感织入众人的纽带，为浪漫火种献祭")

    def _resolve_reason_authority(self) -> None:
        """Cerces strengthens Golden Ones until the third demi-god exhausts the fire."""
        titan = self.state.titans["cerces"]
        if titan.coreflame_status != "held" or titan.coreflame_holder is None:
            return
        holder = self.state.people.get(titan.coreflame_holder)
        if holder is None or not holder.alive:
            return

        # Every living Golden candidate benefits from the holder's teaching,
        # regardless of which fire they may eventually pursue.
        for golden in self.state.people.values():
            if not golden.alive or golden.golden_status != "awakened":
                continue
            for attribute in (
                "body", "insight", "social", "leadership", "courage", "empathy",
                "willpower", "restraint", "ambition", "adaptability", "responsibility",
            ):
                setattr(golden, attribute, min(100, getattr(golden, attribute) + 1))

        created_ids = list(titan.authority_state.get("created_demigod_ids", []))
        if len(created_ids) >= REASON_GOLDEN_QUOTA:
            self._return_coreflame(titan, holder, "培养出三名半神后，理性权能耗尽")
            self._record_death(holder, "理性权能在培养三名半神后耗尽，为完成教导而献祭")

    def _found_earth_foundation(self, holder: Person, titan: Titan) -> None:
        """Leave a real, fallible place for survivors to rebuild beside Okhema."""
        foundation_id = "georios_foundation"
        okhema = self.state.regions["okhema"]
        settlers = min(okhema.population, max(400, min(2_400, okhema.population // 20)))
        foundation = Region(
            foundation_id, "磐生城", settlers, 2_400, 46, 34, 8, 12, 8, ("okhema",),
            refuge_capacity=EARTH_FOUNDATION_CAPACITY,
            refuge_capacity_limit=EARTH_FOUNDATION_CAPACITY,
            defense=12,
            titan_faiths={"georios": 80, "mnestia": 12, "janus": 8},
        )
        self.state.regions[foundation_id] = foundation
        okhema.population -= settlers
        okhema.neighbours = tuple((*okhema.neighbours, foundation_id))
        total_population = sum(region.population for region in self.state.regions.values())
        sample_size = max(1, round(self.population * settlers / max(1, total_population))) if settlers else 0
        volunteers = sorted(
            (person for person in self._residents("okhema") if not self._is_demigod(person)),
            key=lambda person: (person.adaptability + person.responsibility, person.world_impact, person.id),
            reverse=True,
        )[:sample_size]
        for person in volunteers:
            person.region_id = foundation_id
            self._record_life_trace(person, "organization_action", responsibility=1)
        self._return_coreflame(titan, holder, "以自身与火种在奥赫玛附近扎根，留下新城基址")
        self._record_death(holder, "以自身与大地火种扎根，化为新城基址")
        self._emit("earth_foundation", f"{holder.name}在奥赫玛附近扎根，磐生城携{settlers}名首批居民诞生，可容纳最多{EARTH_FOUNDATION_CAPACITY}名幸存者重建家园。", ("world:five_regions_lost", "coreflame:georios"), (f"region:{foundation_id}:created", f"population:{foundation_id}:{settlers}", f"refuge_capacity:{foundation_id}:{EARTH_FOUNDATION_CAPACITY}"), (holder.id, *tuple(person.id for person in volunteers[:4])))

    def _update_historical_focus(self) -> None:
        for person in self.state.people.values():
            if (person.alive and person.life_stage() != "child" and person.world_impact >= HISTORICAL_IMPACT_THRESHOLD
                    and person.impact_reasons and self.state.regions[person.region_id].status != "lost"
                    and "historical_focus" not in person.memories):
                person.memories.append("historical_focus")
                self._emit("historical_focus", f"{person.name}的行动开始持续影响{self.state.regions[person.region_id].name}的历史。", tuple(person.impact_reasons[-2:]), (f"person:{person.id}:focus",), (person.id,))

    def _residents(self, region_id: str) -> list[Person]:
        return [p for p in self.state.people.values() if p.alive and p.region_id == region_id]

    def _resolve_lost_person(self, person: Person, region: Region) -> None:
        """Detailed remnants either flee, fade, or endure as a demi-god."""
        destinations = self._safe_refuges(region)
        if destinations:
            destination = min(destinations, key=lambda item: (item.black_tide, item.population / max(1, item.refuge_capacity), item.id))
            person.region_id = destination.id
            return
        if person.golden_status == "awakened":
            # A fallen city with no remaining exit is the same broken-route
            # moment as a failed voluntary flight. Mark it before ordinary
            # remnant attrition so Janus can answer during this year's turn.
            person.gate_stranded_year = self.state.year
        self._record_life_trace(person, "loss")
        if self._is_demigod(person):
            person.health = max(1, person.health)
            return
        person.health -= 18
        if person.health <= 0:
            self._record_death(person, "在失陷地区的黑潮中消亡")

    def _maintain_representatives(self) -> None:
        """Keep a detailed sample for living population groups without treating it as all people."""
        total_population = sum(region.population for region in self.state.regions.values())
        if total_population <= 0:
            return
        sample_budget = min(self.population, total_population)
        for region in self.state.regions.values():
            protected_people = [person for person in self._residents(region.id) if self._is_demigod(person)]
            if region.population < len(protected_people):
                region.population = len(protected_people)
            target = max(len(protected_people), min(region.population, round(sample_budget * region.population / total_population)))
            residents = self._residents(region.id)
            if len(residents) > target:
                removable = sorted(
                    (person for person in residents if not self._is_demigod(person)),
                    key=lambda person: (person.golden_status != "ordinary", person.world_impact, person.influence, person.id),
                )
                for person in removable[:max(0, len(residents) - target)]:
                    self._record_death(person, "在地区人口缩减的混乱中失散")
                residents = self._residents(region.id)
            if region.status == "lost":
                continue
            missing = max(0, target - len(residents))
            for index in range(missing):
                ident = f"resident-{self.state.year:05d}-{region.id}-{index:03d}"
                if ident in self.state.people:
                    continue
                rng = self.random.get(f"representative:{ident}")
                factors = {factor: rng.randint(18, 68) for factor in Factor}
                dominant = rng.choice(tuple(Factor))
                factors[dominant] = min(85, factors[dominant] + rng.randint(8, 20))
                self._shape_birthplace_factors(region.id, factors)
                given_name, family_name = self._person_name(region.id, ident)
                person = Person(
                    ident, f"{given_name}·{family_name}", region.id, rng.randint(16, 55), factors,
                    rng.randint(25, 75), rng.randint(25, 75), rng.randint(25, 75), rng.randint(20, 70),
                    origin_region_id=region.id,
                    courage=rng.randint(25, 75), empathy=rng.randint(25, 75),
                    willpower=rng.randint(25, 75), restraint=rng.randint(25, 75),
                    ambition=rng.randint(25, 75), adaptability=rng.randint(25, 75),
                    responsibility=rng.randint(25, 75),
                    family_name=family_name,
                )
                self.state.people[ident] = person
                self._seed_titan_stances({ident: person}, self.state.regions)
                neighbours = [other for other in self._residents(region.id) if other.id != ident and len(other.relations) < 16]
                for other in sorted(neighbours, key=lambda item: (item.social, item.id), reverse=True)[:4]:
                    person.relations[other.id] = Relation(other.id, "同乡", 35, last_interaction_year=self.state.year)
                    other.relations.setdefault(person.id, Relation(person.id, "同乡", 35, last_interaction_year=self.state.year))

    def _check_ending(self) -> EndingKind | None:
        if sum(region.population for region in self.state.regions.values()) <= 0:
            self._emit("collapse", "所有区域的居民总人口归零，世界失去可延续的社会。", (), ("world:collapse",))
            return EndingKind.COLLAPSE
        if all(region.status == "lost" for region in self.state.regions.values()):
            self._emit("collapse", "所有城邦均已失陷，幸存者失去维持文明的共同根基。", (), ("world:collapse",))
            return EndingKind.COLLAPSE
        # Re-creation is not a collection threshold. The ten ordinary fires
        # must have been returned, Oronyx must return penultimately, and only
        # then may the Worldbearer hold Kephale as the final fire.
        other_fires_returned = all(
            titan.coreflame_status == "returned"
            for titan_id, titan in self.state.titans.items()
            if titan_id != "kephale"
        )
        worldbearer = self.state.titans["kephale"]
        if (other_fires_returned and worldbearer.coreflame_status == "held"
                and worldbearer.coreflame_holder is not None):
            self._emit("recreation_ready", "十一枚火种已经归还；负世者承担全部火种与旧世界，再创世准备完成。", ("coreflames:eleven:returned", "coreflame:kephale:held"), ("world:recreation_ready",))
            return EndingKind.RECREATION_READY
        return None

    def _emit_world_status(self) -> None:
        alive = sum(p.alive for p in self.state.people.values())
        golden = sum(p.alive and p.golden_status != "ordinary" for p in self.state.people.values())
        tide = round(sum(r.black_tide for r in self.state.regions.values()) / len(self.state.regions))
        civilians = sum(region.population for region in self.state.regions.values())
        lost = sum(region.status == "lost" for region in self.state.regions.values())
        self._emit("world_status", f"第{self.state.year}年｜居民总数 {civilians}；独立人物 {alive}；黄金裔/候选 {golden}；平均黑潮 {tide}/100；失陷城邦 {lost}；世界劫余 {self.state.world_wear}。", (), ())

    def _factor_path_leaders(self) -> dict[str, dict[str, object]]:
        """Expose one meaningful life journey for each factor, never a crowd."""
        titan_for_factor = {titan.factor: titan.id for titan in self.state.titans.values()}
        leaders: dict[str, dict[str, object]] = {}
        for factor in Factor:
            titan_id = titan_for_factor[factor]
            candidates: list[tuple[int, Person]] = []
            for person in self.state.people.values():
                has_matching_fire = titan_id in person.coreflames or titan_id in person.returned_coreflames
                has_matching_evidence = person.trial_evidence.get(titan_id, 0) > 0
                if person.dominant_factor() != factor and not has_matching_fire and not has_matching_evidence:
                    continue
                if (person.world_impact < HISTORICAL_IMPACT_THRESHOLD and person.golden_status == "ordinary"
                        and not has_matching_fire and not has_matching_evidence):
                    continue
                score = person.factors[factor] + person.resonance_years * 6 + person.world_impact * 3
                score += 100 if person.golden_status == "awakened" else 250 if person.golden_status == "demigod" else 0
                score += 400 if has_matching_fire else person.trial_evidence.get(titan_id, 0) * 30
                candidates.append((score, person))
            if not candidates:
                continue
            _score, leader = max(candidates, key=lambda item: (item[0], item[1].alive, item[1].id))
            leaders[factor.value] = {**leader.snapshot(), "path_factor": factor.value}
        return leaders

    def world_snapshot(self, include_events: bool = False) -> dict[str, object]:
        alive = [p for p in self.state.people.values() if p.alive]
        focus = sorted(
            (p for p in alive if p.world_impact >= HISTORICAL_IMPACT_THRESHOLD or p.coreflames or p.golden_status != "ordinary"),
            key=lambda p: (-p.world_impact, -p.influence, p.id),
        )[:30]
        archive = sorted(
            (p for p in self.state.people.values()
             if not p.alive and (p.world_impact >= HISTORICAL_IMPACT_THRESHOLD or p.coreflames or p.golden_status != "ordinary")),
            key=lambda p: (-(p.death_year or 0), -p.world_impact, p.id),
        )
        regions = {
            key: {**value.snapshot(), "independent_people": len(self._residents(key))}
            for key, value in sorted(self.state.regions.items())
        }
        data: dict[str, object] = {
            "year": self.state.year,
            "world_wear": self.state.world_wear,
            "population": {
                "total_civilians": sum(region.population for region in self.state.regions.values()),
                "initial_individuals": self.population,
                "alive_individuals": len(alive),
            },
            "regions": regions,
            "titans": {key: value.snapshot() for key, value in sorted(self.state.titans.items())},
            "organizations": {key: value.snapshot() for key, value in sorted(self.state.organizations.items())},
            "historical_focus": {p.id: p.snapshot() for p in focus},
            "historical_archive": {p.id: p.snapshot() for p in archive},
            "factor_paths": self._factor_path_leaders(),
            "crises": {key: value.snapshot() for key, value in sorted(self.state.crises.items())},
            "refuge_crises": {key: value.snapshot() for key, value in sorted(self.state.refuge_crises.items())},
            "recent_events": [event.snapshot() for event in self.state.events[-25:]],
        }
        if include_events:
            data["events"] = [event.snapshot() for event in self.state.events]
        return data

    def state_hash(self) -> str:
        encoded = json.dumps(self.world_snapshot(True), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode("utf-8")).hexdigest()

    def _emit(self, kind: str, summary: str, causes: tuple[str, ...], effects: tuple[str, ...], witnesses: tuple[str, ...] = ()) -> None:
        self._event_sequence += 1
        self.state.events.append(Event(f"E-{self.state.year:05d}-{self._event_sequence:05d}", self.state.year, kind, summary, causes, effects, witnesses))

    def _ending_summary(self, ending: EndingKind) -> str:
        if ending is EndingKind.COLLAPSE:
            return "独立人物全部消失；世界未能维持可延续的社会。"
        if ending is EndingKind.RECREATION_READY:
            return "足够火种已被承接；世界具备尝试再创世的条件。"
        return f"第{self.state.year}年结束；世界仍在黑潮、泰坦与人物选择中演化。"
