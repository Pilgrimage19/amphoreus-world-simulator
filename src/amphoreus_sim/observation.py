"""Read-only product projections of recorded history, never a narrative RNG."""

from __future__ import annotations

from .flamechase import ORDINARY_FIRES
from .models import Event, Person, WorldState


EVENT_TITLES = {
    "coreflame_inherited": "火种承接", "coreflame_returned": "火种归还",
    "region_lost": "聚居地失陷", "gate_rescue": "门径救援",
    "earth_foundation": "磐生城诞生", "strife_refuge_founded": "余烬营地建立",
    "death_candidate_called": "冥河的呼唤", "death_bond_chosen": "渡厄之心",
    "strife_challenge_failed": "挑战者倒下", "sky_healing": "天空最后的治愈",
    "trickery_final_truth": "黎明秘密的交接", "time_final_pledge": "岁月最后的承诺",
    "time_story_witnessed": "岁月保存故事", "worldbearing_flame_integrated": "负世接纳印记",
    "special_candidate_awakened": "特殊候选觉醒", "organization_exile": "传统随幸存者流亡",
    "collapse": "文明终结", "recreation_ready": "再创世准备完成",
}
PERSON_EVENT_TITLES = {
    **EVENT_TITLES,
    "golden_awakening": "黄金共鸣觉醒", "historical_death": "人物离世",
    "reason_exam_started": "开始瑟希斯四证", "reason_exam_passed": "通过一门四证",
    "reason_demigod_created": "理性教导留下成果", "death_bond_visit": "跨越厄运赴约",
    "romance_heirs_connected": "金线连接逐火者", "trickery_lie_confessed": "坦白最后的谎言",
}

ABILITY_GUIDE = (
    ("body", "体魄", "影响劳动、难民安置、守备与纷争挑战；不等于半神的不死资格。"),
    ("insight", "洞察", "影响研究与危机规划；与智识因子共同决定四证考试速度。"),
    ("social", "社交", "影响结交关系、组织招募、救援和难民安置的实际参与资格。"),
    ("leadership", "领导", "影响组织领导者选择、协调危机、配给与新聚居地策略。"),
)
PERSONALITY_GUIDE = (
    ("courage", "勇气", "参与纷争挑战资格和胜率、死亡羁绊资格，也提高冲突倾向；不是单纯越高越好。"),
    ("empathy", "共情", "提高援助倾向，参与浪漫候选排序；海洋试炼起始要求低共情。"),
    ("willpower", "意志", "影响劳动倾向、渡厄羁绊资格与死亡半神的引渡效率。"),
    ("restraint", "克制", "提高组织倾向、降低冲突倾向，参与律法候选排序。"),
    ("ambition", "野心", "提高寻求力量和冲突的倾向，不保证成为半神。"),
    ("adaptability", "适应力", "参与诡计试炼与候选排序，以及磐生城首批迁入人选；不是通用免伤。"),
    ("responsibility", "责任", "提高劳动、援助和组织倾向；降低黄金裔逃离权重，但不禁止逃离。"),
)
TRACE_GUIDE = {
    "guardianship": ("守护", "危机中的劳动、援助或专属试炼累计；计数不等于救援人数。"),
    "loss": ("失去", "厄运、失陷地区停留或神权负担等累计；不能据此推断失去亲友。"),
    "oath": ("誓言", "立律、关系或试炼中的誓言相关记录；具体对象以事件和关系档案为准。"),
    "betrayal": ("背叛（旧计数）", "当前包括普通冲突和面具试炼；不代表确实背叛了某个具体人物。"),
    "responsibility": ("承担", "承担行为的累计痕迹，不等于责任属性值或独立事件数。"),
    "black_tide_exposure": ("黑潮侵蚀", "处于黑潮压力中的累计经历，不是永久伤害数值。"),
    "organization_action": ("组织行为", "组织、试炼与迁居等累计经历，具体影响需查看对应事件。"),
}


def _event_card(event: Event, state: WorldState, positions: dict[str, int], *, personal: bool = False) -> dict:
    title = (PERSON_EVENT_TITLES if personal else EVENT_TITLES).get(event.type, "历史记录")
    for effect in event.effects:
        parts = effect.split(":")
        if len(parts) >= 3 and parts[0] == "coreflame" and parts[1] in state.titans:
            if event.type in {"coreflame_inherited", "coreflame_returned"}:
                title = f"{state.titans[parts[1]].domain}{title}"
            break
    references = []
    for cause in event.causes:
        candidate = cause.removeprefix("event:")
        if candidate in positions and positions[candidate] < positions[event.id] and candidate not in references:
            references.append(candidate)
    return {
        "id": event.id, "year": event.year, "type": event.type, "title": title,
        "summary": event.summary,
        "people": [{"id": key, "name": state.people[key].name}
                   for key in dict.fromkeys(event.witnesses) if key in state.people],
        "causal_event_ids": references,
    }


def person_observation(person: Person, state: WorldState) -> dict:
    positions = {event.id: index for index, event in enumerate(state.events)}
    prefix = f"person:{person.id}:"
    journey = [_event_card(event, state, positions, personal=True) for event in state.events
               if event.type in PERSON_EVENT_TITLES and (
                   person.id in event.witnesses
                   or any(value.startswith(prefix) for value in (*event.causes, *event.effects)))]
    traces = []
    for key, count in person.life_traces.items():
        if count <= 0:
            continue
        label, description = TRACE_GUIDE.get(key, (key, "当前仅有累计记录，尚不能解释为独立故事事件。"))
        if key == "victory_choice":
            description = "胜利后的选择尚未接入生产逻辑；不能解释为已发生的具体选择。"
        traces.append({"key": key, "label": label, "count": count, "description": description})
    return {
        "journey": journey,
        "attribute_guide": {
            "abilities": [{"key": key, "label": label, "value": getattr(person, key), "usage": usage}
                          for key, label, usage in ABILITY_GUIDE],
            "personality": [{"key": key, "label": label, "value": getattr(person, key), "usage": usage}
                            for key, label, usage in PERSONALITY_GUIDE],
            "traces": traces,
            "note": "属性影响倾向或资格，不是某次行动的已确认动机。人生痕迹是累计计数，具体经历以事件档案为准。",
        },
    }


def build_observation(state: WorldState, *, ending: str | None = None,
                      ending_summary: str | None = None, last_advance: dict | None = None) -> dict:
    positions = {event.id: index for index, event in enumerate(state.events)}
    important = [event for event in state.events if event.type in EVENT_TITLES]
    timeline = [_event_card(event, state, positions) for event in important]
    surviving = [region for region in state.regions.values() if region.status != "lost"]
    returned = sum(state.titans[key].coreflame_status == "returned" for key in ORDINARY_FIRES)
    holders = [titan for titan in state.titans.values() if titan.coreflame_status == "held"]
    if ending == "collapse":
        chapter_title = "旧世界的余烬"
    elif ending == "recreation_ready":
        chapter_title = "再创世前夜"
    elif len(surviving) <= 2 or returned >= 8:
        chapter_title = "最后的庇护"
    elif sum(region.status == "lost" for region in state.regions.values()) >= 2:
        chapter_title = "城邦离散的年代"
    elif len(state.flame_stories) >= 3:
        chapter_title = "逐火者相继登场"
    else:
        chapter_title = "逐火初曙"
    chapter_summary = (f"仍有{len(surviving)}处未失陷聚居地，{len(holders)}位持火者，"
                       f"十枚常规火种已归还{returned}枚。")
    if ending:
        chapter_summary = ending_summary or ("城邦文明已经终结。" if ending == "collapse" else "再创世准备完成，下一代世界尚未生成。")

    spotlight = []
    seen = set()
    stories = sorted(state.flame_stories.values(), key=lambda story: (
        state.titans[str(story["titan_id"])].coreflame_status == "held",
        story.get("returned_year") if story.get("returned_year") is not None else story.get("inherited_year", 0)), reverse=True)
    for story in stories:
        person = state.people.get(str(story.get("holder_id", "")))
        if person is None or person.id in seen:
            continue
        seen.add(person.id)
        titan = state.titans[str(story["titan_id"])]
        status = "仍在承担神权" if titan.coreflame_status == "held" else "留下了归还印记"
        summary = str(story.get("return_reason") or story.get("trial") or "承接记录仍保存在档案中")
        spotlight.append({"person_id": person.id, "name": person.name, "domain": titan.domain,
                          "status": status, "summary": summary,
                          "latest_year": story.get("returned_year") if story.get("returned_year") is not None else story.get("inherited_year", 0)})
        if len(spotlight) >= 3:
            break

    recap = None
    if last_advance is not None:
        start = int(last_advance["event_index"])
        batch = [card for card in timeline if positions[card["id"]] >= start]
        recap = {"from_year": last_advance["from_year"], "to_year": state.year,
                 "important_count": len(batch), "events": batch,
                 "population_delta": sum(r.population for r in state.regions.values()) - last_advance["population"]}

    ending_card = None
    if ending:
        legacy = []
        for story in stories:
            if story.get("returned_event_id") in positions and story.get("imprint"):
                legacy.append(f"{story['holder_name']}留下：{story['imprint']}")
        founded = []
        for event in important:
            if event.type not in {"earth_foundation", "strife_refuge_founded"}:
                continue
            for effect in event.effects:
                parts = effect.split(":")
                if len(parts) >= 3 and parts[0] == "region" and parts[2] == "created" and parts[1] in state.regions:
                    name = state.regions[parts[1]].name
                    if name not in founded:
                        founded.append(name)
        missing = []
        for key, description in (("oronyx", "岁月尚未完成完整见证并归还"), ("kephale", "负世尚未完成最后承载")):
            if key == "oronyx" and state.titans[key].coreflame_status != "returned":
                missing.append(description)
            elif key == "kephale" and ending != "recreation_ready":
                missing.append(description)
        ending_card = {"title": chapter_title, "summary": chapter_summary,
                       "returned_fires": sum(t.coreflame_status == "returned" for t in state.titans.values()),
                       "refuge_names": founded, "missing_roles": missing, "legacy": legacy}
    return {
        "chapter": {"title": chapter_title, "summary": chapter_summary},
        "metrics": {"surviving_regions": len(surviving), "ordinary_returned": returned,
                    "active_bearers": len(holders), "living_tide": round(sum(r.black_tide for r in surviving) / len(surviving)) if surviving else None},
        "spotlight": spotlight, "highlights": list(reversed(timeline[-5:])), "timeline": timeline,
        "recap": recap, "ending": ending_card, "last_event_id": state.events[-1].id if state.events else None,
    }
