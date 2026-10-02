"""Final four trials and the shared, causal record of the Flame-Chase.

Rules here are sandbox adaptations, not a replay of named canon characters.
The mixin uses Simulation's world, random streams, population and event helpers.
"""

from collections import deque

from .models import Factor, Organization, Person, Region, Relation, Titan


ORDINARY_FIRES = frozenset({
    "aquila", "georios", "phagousa", "talanton", "janus", "mnestia",
    "cerces", "zagreus", "nikador", "thanatos",
})
SPECIAL_FACTOR_THRESHOLD = 96
SPECIAL_TAIL_DENOMINATOR = 4_000
DEATH_CURSE_VICTIMS = 3
STRIFE_MIN_JOURNEY_YEARS = 20


class FlamechaseMixin:
    def _seed_special_role(self, person: Person) -> None:
        factor = person.dominant_factor()
        if factor not in {Factor.REMEMBRANCE, Factor.DESTRUCTION}:
            return
        rng = self.random.get(f"special_destiny:{person.id}")
        # A rare factor tail and an independent destiny judgment, both drawn
        # once at creation. Age, study and repeated ticks never reroll destiny.
        if rng.randrange(SPECIAL_TAIL_DENOMINATOR) != 0:
            return
        person.factors[factor] = rng.randint(SPECIAL_FACTOR_THRESHOLD, 100)
        if rng.randrange(4) != 0:
            return
        person.special_role = "unblemished_soul" if factor == Factor.REMEMBRANCE else "perfect_vessel"
        person.willpower = max(85, person.willpower)
        if factor == Factor.REMEMBRANCE:
            person.empathy = max(80, person.empathy)
        else:
            person.body = max(85, person.body)
            person.courage = max(85, person.courage)

    def _flame_story(self, titan: Titan, holder: Person, trial: str) -> None:
        self.state.flame_stories[titan.id] = {
            "titan_id": titan.id, "domain": titan.domain,
            "holder_id": holder.id, "holder_name": holder.name,
            "trial": trial, "inherited_year": self.state.year,
            "inherited_event_id": self.state.events[-1].id,
            "returned_year": None, "return_reason": None,
            "returned_event_id": None,
            "supporter_ids": sorted({
                relation.target_id for relation in holder.relations.values()
                if relation.trust >= 55 and relation.target_id in self.state.people
            }),
            "imprint": None,
        }

    def _record_flame_return(self, titan: Titan, holder: Person, reason: str) -> None:
        story = self.state.flame_stories.setdefault(titan.id, {
            "titan_id": titan.id, "domain": titan.domain,
            "holder_id": holder.id, "holder_name": holder.name,
            "trial": "逐火时代开始前的承接", "inherited_year": 0,
            "inherited_event_id": None, "supporter_ids": [],
        })
        imprints = {
            "aquila": "为脆弱者撑起的天空", "georios": "可以重新扎根的土地",
            "phagousa": "不被孤独截断的海路", "janus": "最后一扇为他人打开的门",
            "talanton": "约束掌权者的共同之律", "mnestia": "让分离者彼此相认的金线",
            "cerces": "传给后来者而不被垄断的知识", "zagreus": "替真实黎明争取时间的谎言",
            "nikador": "在废墟中仍敢迎接新生的勇气", "thanatos": "生死互不奴役的边界",
            "oronyx": "十位逐火者未被抹去的故事",
        }
        story.update({"returned_year": self.state.year, "return_reason": reason,
                      "returned_event_id": self.state.events[-1].id,
                      "imprint": imprints.get(titan.id, "承担旧世界的意志")})

    def _resolve_death_trial(self) -> None:
        titan = self.state.titans["thanatos"]
        if titan.coreflame_status != "within_titan" or self.state.year < 50:
            return
        candidates = [p for p in self.state.people.values()
                      if p.alive and p.golden_status == "awakened" and p.age >= 20
                      and p.dominant_factor() == Factor.EQUILIBRIUM
                      and self.state.regions[p.region_id].status != "lost"]
        if not candidates:
            return
        # No personality, faith or accomplishments influence who is called.
        current_id = titan.authority_state.get("candidate_id")
        candidate = max(candidates, key=lambda p: (p.factors[Factor.EQUILIBRIUM], p.id == current_id, p.id))
        if titan.authority_state.get("candidate_id") != candidate.id:
            titan.authority_state = {"candidate_id": candidate.id, "curse_victim_ids": []}
            self._emit("death_candidate_called", f"{candidate.name}因当世最高的死亡天赋听见冥河呼唤。",
                       ("factor:equilibrium:highest",), ("trial:thanatos:called",), (candidate.id,))
        victims = list(titan.authority_state.get("curse_victim_ids", []))
        if self.state.year % 3 == 0 and len(victims) < DEATH_CURSE_VICTIMS:
            nearby = [p for p in self._residents(candidate.region_id)
                      if p.id != candidate.id and not self._is_demigod(p) and p.id not in victims]
            if nearby:
                victim = min(nearby, key=lambda p: (p.id not in candidate.relations, p.id))
                victims.append(victim.id)
                titan.authority_state["curse_victim_ids"] = victims
                victim.health = max(1, victim.health - 12)
                self._record_life_trace(candidate, "loss")
                if victim.id in candidate.relations:
                    candidate.relations[victim.id].trust -= 5
                self._emit("death_ill_fortune", f"{victim.name}遭遇厄运，{candidate.name}开始被周围人疏远。",
                           ("trial:thanatos:curse",), (f"person:{victim.id}:misfortune",), (candidate.id, victim.id))
        titan.trial_progress = min(75, len(victims) * 25)
        if len(victims) < DEATH_CURSE_VICTIMS:
            return
        # The other person must choose closeness; the candidate cannot award
        # themselves a bond. Demigods and brave, resolute people can endure it.
        companions = [self.state.people[r.target_id] for r in candidate.relations.values()
                      if r.target_id in self.state.people and r.trust >= 55
                      and self.state.people[r.target_id].alive
                      and (self.state.people[r.target_id].region_id == candidate.region_id
                           or (self._is_demigod(self.state.people[r.target_id])
                               and self.state.people[r.target_id].bound_region_id is None))
                      and candidate.id in self.state.people[r.target_id].relations
                      and self.state.people[r.target_id].relations[candidate.id].trust >= 55
                      and (self._is_demigod(self.state.people[r.target_id])
                           or self.state.people[r.target_id].courage + self.state.people[r.target_id].willpower >= 140)]
        if not companions:
            return
        companion = max(companions, key=lambda p: (self._is_demigod(p), p.empathy + p.willpower, p.id))
        if companion.region_id != candidate.region_id:
            route = self._next_region_toward(companion.region_id, candidate.region_id)
            if route is None or not self._move_demigod(companion, route):
                return
            self._emit("death_bond_visit", f"{companion.name}沿道路前往{candidate.name}身边，跨越世人畏惧的厄运。", ("relation:mutual_trust", "trial:thanatos:curse"), (f"person:{companion.id}:relocated:{route}",), (companion.id, candidate.id))
            if companion.region_id != candidate.region_id:
                return
        companion.relations[candidate.id].oath = "渡厄之心"
        candidate.relations[companion.id].oath = "渡厄之心"
        self._emit("death_bond_chosen", f"{companion.name}主动跨过厄运，选择与{candidate.name}结下渡厄之心。",
                   ("trial:thanatos:three_misfortunes",), ("trial:thanatos:bond",), (companion.id, candidate.id))
        titan.authority_state = {"bond_id": companion.id, "souls_guided": 0, "in_underworld": 1}
        titan.trial_progress = 100
        self._inherit_coreflame(titan, candidate, "有人主动跨过厄运的冥河试炼")

    def _resolve_death_authority(self) -> None:
        titan = self.state.titans["thanatos"]
        holder = self.state.people.get(titan.coreflame_holder or "")
        if titan.coreflame_status != "held" or holder is None or not holder.alive:
            return
        guided = min(self.state.pending_souls, 20 + holder.willpower // 2)
        self.state.pending_souls -= guided
        self.state.ferried_souls += guided
        titan.authority_state["souls_guided"] = int(titan.authority_state.get("souls_guided", 0)) + guided
        titan.corruption = max(0, titan.corruption - 2)
        if guided and self.state.year % 10 == 0:
            self._emit("death_souls_guided", f"{holder.name}在冥界为{guided}位已登记亡者引渡，未让死亡重新侵入人世。",
                       ("souls:waiting",), (f"souls:guided:{guided}",), (holder.id,))
        threshold = max(1_000, self.initial_civilian_population // 10)
        held_years = self.state.year - int(titan.authority_state.get("inherited_year", self.state.year))
        if held_years >= 5 and sum(r.population for r in self.state.regions.values()) <= threshold:
            # The final crossing takes every remaining registered soul once.
            titan.authority_state["souls_guided"] += self.state.pending_souls
            self.state.ferried_souls += self.state.pending_souls
            self.state.pending_souls = 0
            self._return_coreflame(titan, holder, "为凋零旧世界划定生死边界，完成最后一次引渡")
            self._record_death(holder, "留在冥河彼岸，以自身封闭死亡回流")

    def _resolve_strife_trial(self) -> None:
        titan = self.state.titans["nikador"]
        if titan.coreflame_status != "within_titan" or self.state.year < 50 or self.state.year % 5:
            return
        candidates = [p for p in self.state.people.values()
                      if p.alive and p.golden_status == "awakened" and p.age >= 20
                      and p.dominant_factor() == Factor.HUNT and p.courage >= 60 and p.body >= 55
                      and self.state.regions[p.region_id].status != "lost"]
        if not candidates:
            return
        candidate = max(candidates, key=lambda p: (p.courage + p.body, p.id))
        chance = max(0.03, min(0.30, 0.03 + (candidate.courage + candidate.body - 115) * 0.003))
        titan.authority_state["challenge_count"] = int(titan.authority_state.get("challenge_count", 0)) + 1
        if self.random.get(f"strife_challenge:{candidate.id}").random() >= chance:
            self._emit("strife_challenge_failed", f"{candidate.name}正面挑战尼卡多利，倒在神躯之前；后来者记住了这次挑战。",
                       (f"trial:nikador:success_probability:{chance:.3f}",), ("trial:nikador:failed",), (candidate.id,))
            self._record_death(candidate, "正面挑战纷争泰坦失败")
            return
        titan.trial_progress = 100
        titan.authority_state.update({"journey_years": 0, "refuge_ids": [], "battle_count": 0})
        self._inherit_coreflame(titan, candidate, "正面击碎纷争泰坦神躯")

    def _resolve_strife_authority(self) -> None:
        titan = self.state.titans["nikador"]
        holder = self.state.people.get(titan.coreflame_holder or "")
        if titan.coreflame_status != "held" or holder is None or not holder.alive:
            return
        ruins = [r for r in self.state.regions.values() if r.status == "lost" and not r.id.startswith("nikador_refuge_")]
        if not ruins:
            return
        journey = int(titan.authority_state.get("journey_years", 0)) + 1
        titan.authority_state["journey_years"] = journey
        if journey % 5:
            return
        titan.authority_state["battle_count"] = int(titan.authority_state.get("battle_count", 0)) + 1
        refuge_ids = list(titan.authority_state.get("refuge_ids", []))
        ruins.sort(key=lambda r: (f"nikador_refuge_{r.id}" in refuge_ids, -r.population, r.id))
        ruin = ruins[0]
        sources = [r for r in self.state.regions.values() if r.status != "lost" and r.population >= 1_000]
        if len(refuge_ids) < 3 and sources and f"nikador_refuge_{ruin.id}" not in self.state.regions:
            source = max(sources, key=lambda r: (r.population, r.id))
            refuge_id = f"nikador_refuge_{ruin.id}"
            settlers = min(300, source.population // 10)
            source.population -= settlers
            refuge = Region(refuge_id, f"{ruin.name}·余烬营地", settlers, 600, 45, 30, 15, 30, 25,
                            (source.id, ruin.id), refuge_capacity=1_500, refuge_capacity_limit=2_000,
                            defense=18, titan_faiths={"nikador": 60, "mnestia": 20, "janus": 20})
            self.state.regions[refuge_id] = refuge
            source.neighbours = tuple(dict.fromkeys((*source.neighbours, refuge_id)))
            ruin.neighbours = tuple(dict.fromkeys((*ruin.neighbours, refuge_id)))
            refuge_ids.append(refuge_id)
            titan.authority_state["refuge_ids"] = refuge_ids
            volunteers = [p for p in self._residents(source.id) if not self._is_demigod(p)]
            for volunteer in sorted(volunteers, key=lambda p: (-p.courage, p.id))[:max(1, round(self.population * settlers / max(1, sum(r.population for r in self.state.regions.values()))))]:
                volunteer.region_id = refuge_id
            org_id = f"{refuge_id}_guard"
            members = {p.id for p in self._residents(refuge_id)}
            self.state.organizations[org_id] = Organization(org_id, f"{ruin.name}余烬守望", "民兵", refuge_id,
                                                          "护持废墟旁的新生与聚落", influence=20, member_ids=members)
            for person_id in members:
                previous = self.state.people[person_id].organization_id
                if previous in self.state.organizations:
                    self.state.organizations[previous].member_ids.discard(person_id)
                    if self.state.organizations[previous].leader_id == person_id:
                        self.state.organizations[previous].leader_id = None
                self.state.people[person_id].organization_id = org_id
            self._emit("strife_refuge_founded", f"{holder.name}护送{settlers}名志愿者，在{ruin.name}废墟旁建立余烬营地；旧城并未复活。",
                       (f"region:{ruin.id}:lost", "coreflame:nikador"), (f"region:{refuge_id}:created",), (holder.id,))
        self._move_demigod(holder, ruin.id)
        self._record_life_trace(holder, "guardianship")
        self._emit("strife_black_tide_journey", f"{holder.name}再入{ruin.name}黑潮，为身后的新生聚落抵挡战祸。",
                   ("coreflame:nikador",), (f"authority:nikador:journey:{journey}",), (holder.id,))
        risk = min(0.65, 0.05 + max(0, journey - STRIFE_MIN_JOURNEY_YEARS) / 100)
        if journey >= STRIFE_MIN_JOURNEY_YEARS and self.random.get(f"strife_journey:{holder.id}").random() < risk:
            self._return_coreflame(titan, holder, "在黑潮行旅中战至最后，为废墟中的新生留下反抗的火")
            self._record_death(holder, "在保护复兴据点的黑潮战斗中阵亡")

    def _move_demigod(self, person: Person, destination_id: str) -> bool:
        if person.region_id == destination_id:
            return True
        origin = self.state.regions[person.region_id]
        if origin.population <= 0:
            return False
        origin.population -= 1
        self.state.regions[destination_id].population += 1
        person.region_id = destination_id
        return True

    def _next_region_toward(self, origin_id: str, destination_id: str) -> str | None:
        queue = deque([(origin_id, None)])
        visited = {origin_id}
        while queue:
            region_id, first_hop = queue.popleft()
            if region_id == destination_id:
                return first_hop
            for neighbor in self.state.regions[region_id].neighbours:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, first_hop or neighbor))
        return None

    def _special_candidates(self, titan_id: str, role: str) -> list[Person]:
        titan = self.state.titans[titan_id]
        return [p for p in self.state.people.values()
                if p.alive and p.golden_status == "awakened" and p.age >= 20
                and p.special_role == role and p.dominant_factor() == titan.factor
                and p.factors[titan.factor] >= SPECIAL_FACTOR_THRESHOLD
                and self.state.regions[p.region_id].status != "lost"]

    def _resolve_time_trial(self) -> None:
        titan = self.state.titans["oronyx"]
        if titan.coreflame_status != "within_titan":
            return
        for candidate in sorted(self._special_candidates("oronyx", "unblemished_soul"), key=lambda p: p.id):
            stories = [s for key, s in self.state.flame_stories.items() if key in ORDINARY_FIRES]
            if len(stories) < 3:
                continue
            candidate.trial_evidence["oronyx_memory_years"] = candidate.trial_evidence.get("oronyx_memory_years", 0) + 1
            years = candidate.trial_evidence["oronyx_memory_years"]
            if years in {1, 5, 10, 15}:
                self._emit("time_memory_trial", f"{candidate.name}在忆页三问中辨认过去、承认失去，并拒绝删改逐火者的选择。",
                           ("candidate:unblemished_soul", "flame_stories:three"), (f"trial:oronyx:years:{years}",), (candidate.id,))
            titan.trial_progress = max(titan.trial_progress, min(100, years * 100 // 15))
            if years >= 15:
                titan.authority_state = {"witnessed_fire_ids": [], "memory_burden": 0}
                self._inherit_coreflame(titan, candidate, "不删改任何人的忆页三问")
                return

    def _resolve_time_authority(self) -> None:
        titan = self.state.titans["oronyx"]
        holder = self.state.people.get(titan.coreflame_holder or "")
        if titan.coreflame_status != "held" or holder is None or not holder.alive:
            return
        witnessed = list(titan.authority_state.get("witnessed_fire_ids", []))
        ocean = self.state.titans["phagousa"]
        ocean_holder = self.state.people.get(ocean.coreflame_holder or "")
        preceding = ORDINARY_FIRES - {"phagousa"}
        if (ocean.coreflame_status == "held" and ocean_holder is not None
                and ocean_holder.alive and ocean.authority_state.get("anchor_id") == holder.id
                and all(self.state.titans[key].coreflame_status == "returned"
                        and self.state.flame_stories.get(key, {}).get("returned_event_id")
                        for key in preceding)):
            # The two sacrifices commit in one resolution: Time chooses first,
            # Ocean returns tenth, Time witnesses that real event and returns
            # eleventh. Neither a premature return nor a dead anchor suffices.
            self._emit("time_final_pledge", f"{holder.name}开始不可撤回的最后献祭，等待污海同行者留下第十段故事。",
                       ("flame_stories:nine_returned", "relation:ocean_anchor"),
                       ("sacrifice:oronyx:committed",), (holder.id, ocean_holder.id))
            self._follow_ocean_anchor_sacrifice(holder)
        for titan_id in sorted(ORDINARY_FIRES):
            story = self.state.flame_stories.get(titan_id)
            if titan_id in witnessed or not story or not story.get("returned_event_id"):
                continue
            witnessed.append(titan_id)
            self._emit("time_story_witnessed", f"{holder.name}保存了{story['holder_name']}归还{story['domain']}火种的选择：{story['return_reason']}。",
                       (f"event:{story['returned_event_id']}",), (f"memory:oronyx:{titan_id}",), (holder.id, str(story["holder_id"])))
        titan.authority_state["witnessed_fire_ids"] = witnessed
        if self.state.year % 10 == 0:
            titan.authority_state["memory_burden"] = int(titan.authority_state.get("memory_burden", 0)) + 1
            self._record_life_trace(holder, "loss")
            # A record keeps knowledge alive, but never rewinds deaths/city loss.
            for region in self.state.regions.values():
                if region.status != "lost":
                    region.knowledge = min(100, region.knowledge + 1)
        if set(witnessed) == ORDINARY_FIRES and all(self.state.titans[key].coreflame_status == "returned" for key in ORDINARY_FIRES):
            self._return_coreflame(titan, holder, "完整见证十位逐火者，将自身记忆留给最后的承载者")
            self._record_death(holder, "以自身为最后一页，保存十段完整的逐火故事")

    def _record_worldbearing(self, person: Person, region: Region, action: str) -> None:
        if (person.special_role == "perfect_vessel" and person.golden_status == "awakened"
                and person.age >= 20 and action in {"aid", "organize", "work"}
                and (region.black_tide >= 35 or region.population > region.refuge_capacity)):
            person.trial_evidence["kephale_burdens"] = person.trial_evidence.get("kephale_burdens", 0) + 1
            self._record_life_trace(person, "responsibility", responsibility=1)

    def _resolve_worldbearing_trial(self) -> None:
        titan = self.state.titans["kephale"]
        if titan.coreflame_status != "within_titan":
            return
        known_fires = sum(self.state.titans[k].coreflame_status != "within_titan" for k in ORDINARY_FIRES)
        if known_fires < 5:
            return
        for candidate in sorted(self._special_candidates("kephale", "perfect_vessel"), key=lambda p: p.id):
            evidence = candidate.trial_evidence.get("kephale_burdens", 0)
            titan.trial_progress = max(titan.trial_progress, min(100, evidence * 10))
            if evidence >= 10:
                titan.authority_state = {"world_burden": 0, "compatible_fire_ids": []}
                self._inherit_coreflame(titan, candidate, "在不可独力解决的灾难中承担而不转嫁")
                return

    def _resolve_worldbearing_authority(self) -> None:
        titan = self.state.titans["kephale"]
        holder = self.state.people.get(titan.coreflame_holder or "")
        if titan.coreflame_status != "held" or holder is None or not holder.alive:
            return
        burden = int(titan.authority_state.get("world_burden", 0)) + 1
        titan.authority_state["world_burden"] = burden
        surviving = [r for r in self.state.regions.values() if r.status != "lost"]
        if surviving:
            refuge = max(surviving, key=lambda r: (r.population, r.id))
            refuge.black_tide = max(refuge.tide_source, refuge.black_tide - 1)
            refuge.defense = min(35, refuge.defense + 1)
        compatible = list(titan.authority_state.get("compatible_fire_ids", []))
        if self.state.year % 3 == 0:
            for key in sorted(self.state.flame_stories):
                story = self.state.flame_stories[key]
                if key != "kephale" and key not in compatible and story.get("returned_event_id"):
                    compatible.append(key)
                    self._emit("worldbearing_flame_integrated", f"{holder.name}接纳{story['holder_name']}留下的{story['domain']}印记，承担其未完成的未来。",
                               (f"event:{story['returned_event_id']}",), (f"compatibility:kephale:{key}",), (holder.id, str(story["holder_id"])))
                    break
        titan.authority_state["compatible_fire_ids"] = compatible

    def _recreation_blockers(self) -> list[str]:
        blockers = [f"{self.state.titans[key].domain}火种尚未归还" for key in sorted(ORDINARY_FIRES)
                    if self.state.titans[key].coreflame_status != "returned"]
        time = self.state.titans["oronyx"]
        if time.coreflame_status != "returned":
            blockers.append("岁月尚未完整见证十段故事并归还")
        elif set(time.authority_state.get("witnessed_fire_ids", [])) != ORDINARY_FIRES:
            blockers.append("岁月缺少可追溯的十段见证")
        if any(self.state.titans[key].coreflame_status == "returned"
               and not self.state.flame_stories.get(key, {}).get("returned_event_id")
               for key in ORDINARY_FIRES | {"oronyx"}):
            blockers.append("部分逐火者的归还故事尚未被记下")
        bearer = self.state.titans["kephale"]
        holder = self.state.people.get(bearer.coreflame_holder or "")
        if bearer.coreflame_status != "held" or holder is None or not holder.alive or holder.special_role != "perfect_vessel":
            blockers.append("仍缺少存活的完美之容器负世者")
        if set(bearer.authority_state.get("compatible_fire_ids", [])) != ORDINARY_FIRES | {"oronyx"}:
            blockers.append("负世者尚未接纳十一枚火种印记")
        return blockers
