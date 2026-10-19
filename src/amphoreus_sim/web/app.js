const byId = (id) => document.getElementById(id);
const stageNames = {child: "儿童", youth: "青年", adult: "成人", elder: "长者"};
const factorNames = {destruction: "毁灭", remembrance: "记忆", erudition: "智识", harmony: "同谐", elation: "欢愉", nihility: "虚无", hunt: "巡猎", beauty: "纯美", preservation: "存护", equilibrium: "均衡", order: "秩序", permanence: "不朽"};
const regionStatusNames = {stable: "稳定", strained: "承压", overwhelmed: "避难超载", endangered: "黑潮威胁", lost: "已失陷"};
const coreflameStatusNames = {within_titan: "火种仍在泰坦", held: "火种已被承接", returned: "火种已归还创世涡心"};
const traceNames = {guardianship: "守护", loss: "失去", oath: "誓言", betrayal: "背叛", responsibility: "责任", victory_choice: "胜利后的选择", black_tide_exposure: "黑潮侵蚀", organization_action: "重大组织行为"};
const eventCategories = {
  coreflame_inherited: "逐火承接", coreflame_returned: "火种归还", region_lost: "聚居地变迁",
  gate_rescue: "救援", earth_foundation: "聚居地建立", strife_refuge_founded: "聚居地建立",
  death_candidate_called: "人物历程", death_bond_chosen: "人物历程", strife_challenge_failed: "人物历程",
  sky_healing: "权能归还", trickery_final_truth: "传承交接", time_final_pledge: "岁月见证",
  time_story_witnessed: "岁月见证", worldbearing_flame_integrated: "火种印记", special_candidate_awakened: "人物觉醒",
  organization_exile: "传统流亡", collapse: "世界终局", recreation_ready: "终局准备",
};
let actionInFlight = false;
let selectedPersonId = null;
let personRequestVersion = 0;
let worldRequestVersion = 0;
let worldEnded = false;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[character]);
}

function updateControlState(ended = false) {
  ["step", "advance", "advance-century"].forEach((id) => { byId(id).disabled = actionInFlight || ended; });
  byId("reset").disabled = actionInFlight;
}

function tideClass(value) {
  if (value >= 60) return "danger";
  if (value >= 30) return "warning";
  return "safe";
}

function empty(message) { return `<p class="empty">${esc(message)}</p>`; }
function objectValues(value) { return Object.values(value && typeof value === "object" ? value : {}); }
function list(value) { return Array.isArray(value) ? value : []; }
function numberText(value) { return Number(value || 0).toLocaleString(); }
function personButton(person, className = "inline-person") {
  const id = person?.id ?? person?.person_id ?? person?.target_id;
  if (id === undefined || id === null) return esc(person?.name || "未记录姓名");
  return `<button type="button" class="${className}" data-person-id="${esc(id)}">${esc(person?.name || `人物 ${id}`)}</button>`;
}

function eventMarkup(event, {timeline = false} = {}) {
  const people = list(event.people);
  const causal = list(event.causal_event_ids);
  return `<article class="event-card${timeline ? " timeline-event" : ""}">
    <div class="event-meta"><strong>第 ${esc(event.year)} 年</strong><span>${esc(eventCategories[event.type] || "历史事件")}</span></div>
    <h3>${esc(event.title || "未命名事件")}</h3>
    <p>${esc(event.summary || "没有附加摘要。")}</p>
    ${people.length ? `<div class="event-people"><span>涉及人物：</span>${people.map((person) => personButton(person)).join("、")}</div>` : ""}
    ${causal.length ? `<details class="causal-links"><summary>原始因果引用（${causal.length}）</summary><p>${causal.map(esc).join(" · ")}</p></details>` : ""}
    ${event.type ? `<details class="causal-links"><summary>原始记录</summary><p>记录类型：${esc(event.type)}${event.id ? ` · 事件编号：${esc(event.id)}` : ""}</p></details>` : ""}
  </article>`;
}

function renderObservation(state) {
  const observation = state.observation;
  const chapter = observation?.chapter;
  const complete = Boolean(observation && chapter);
  byId("highlights-label").textContent = complete ? "来自完整事件档案" : "旧版逐火史摘要 · 非完整档案";
  byId("chapter").innerHTML = `<div class="chapter-kicker">${complete ? "世界阶段" : "旧版服务 · 有限观察"}</div>
    <h2>${esc(chapter?.title || (state.ended ? "世界历程已结束" : `第 ${state.year} 年 · 逐火仍在继续`))}</h2>
    <p>${esc(chapter?.summary || "当前服务尚未提供完整 observation 档案。以下旧版降级内容仅参考现有逐火史与近期状态，不代表完整历史或本次推进回顾。")}</p>
    ${complete ? "" : `<p class="fallback-note">历史覆盖范围有限：本页不会把最近日志拼成批次故事。人物详情可能暂不包含真实经历与属性用途说明。</p>`}`;

  if (complete) {
    const metrics = observation.metrics || {};
    const items = [
      ["仍存续地区", metrics.surviving_regions ?? "—"],
      ["已归还常规火种", metrics.ordinary_returned ?? "—"],
      ["当前持火者", metrics.active_bearers ?? "—"],
      ["现存黑潮", metrics.living_tide ?? "—"],
    ];
    byId("metrics").innerHTML = items.map(([label, value]) => `<div class="metric"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("");
    const highlights = list(observation.highlights);
    byId("highlights").innerHTML = highlights.length ? highlights.map((event) => eventMarkup(event)).join("") : empty("本阶段档案没有标记重大事件。");
    const spotlights = list(observation.spotlight);
    byId("spotlight").innerHTML = spotlights.length ? spotlights.map((person) => `<button class="spotlight-card" type="button" data-person-id="${esc(person.person_id)}">
      <span class="spotlight-domain">${esc(person.domain || "人物")}</span><strong>${esc(person.name || "未命名人物")}</strong>
      <span>${esc(person.status || "状态未记录")} · 最近记录第 ${esc(person.latest_year ?? "—")} 年</span><p>${esc(person.summary || "暂无摘要。")}</p>
    </button>`).join("") : empty("本阶段没有需要突出的焦点人物。");
    const recap = observation.recap;
    byId("recap").innerHTML = recap ? `<div class="section-title"><h2>最近一次推进回顾</h2><span>第 ${esc(recap.from_year)}–${esc(recap.to_year)} 年</span></div>
      <p>本批次档案记录 ${esc(recap.important_count ?? list(recap.events).length)} 项重大事件。</p>
      <div class="recap-events scroll-list" tabindex="0" role="region" aria-label="最近一次推进事件列表">${list(recap.events).length ? list(recap.events).map((event) => eventMarkup(event)).join("") : empty("本批次没有记录重大事件。")}</div>
      ${recap.population_delta !== undefined ? `<p class="population-delta">人口变化记录：${esc(typeof recap.population_delta === "object" ? JSON.stringify(recap.population_delta) : recap.population_delta)}</p>` : ""}`
      : `<div class="section-title"><h2>最近一次推进回顾</h2><span>尚无批次数据</span></div><p>首次读取状态不包含本次会话的推进批次；不会从有限日志推断批次故事。</p>`;
    renderEnding(observation.ending);
  } else {
    const regions = objectValues(state.regions);
    const stories = objectValues(state.flame_stories).sort((a, b) => (a.inherited_year || 0) - (b.inherited_year || 0));
    const firesReturned = objectValues(state.titans).filter((titan) => titan.coreflame_status === "returned").length;
    byId("metrics").innerHTML = [["仍存续地区", regions.filter((region) => region.status !== "lost").length], ["已归还火种", firesReturned], ["火种持有者", objectValues(state.titans).filter((titan) => titan.coreflame_holder).length], ["当前年份", state.year]]
      .map(([label, value]) => `<div class="metric"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("");
    byId("highlights").innerHTML = stories.length ? stories.slice(-5).reverse().map((story) => `<article class="event-card"><div class="event-meta"><strong>第 ${esc(story.inherited_year)} 年</strong><span>逐火史 · 档案有限</span></div><h3>${esc(story.domain)} · ${personButton({id: story.holder_id, name: story.holder_name})}</h3><p>承接：${esc(story.trial)}${story.returned_year != null ? `；第 ${esc(story.returned_year)} 年归还：${esc(story.return_reason)}` : "；仍在承担神权，故事尚未结束。"}</p></article>`).join("") : empty("旧版服务未提供逐火史记录。");
    byId("spotlight").innerHTML = empty("旧版服务没有提供阶段人物档案；可在“人物”页查看十二因子焦点名单。");
    byId("recap").innerHTML = `<div class="section-title"><h2>最近一次推进回顾</h2><span>旧版接口不含批次回顾</span></div><p>没有可验证的批次事件档案。下方近期原始日志仍可在“历史”页折叠区域查看。</p>`;
    byId("ending").hidden = true;
  }
  const raw = state.recreation || {};
  const blockers = list(raw.blockers);
  byId("overview-summary").innerHTML = `<p>总人口 ${esc(numberText(state.population?.total_civilians))} · 独立人物样本 ${esc(state.population?.alive_individuals ?? 0)} · 世界劫余 ${esc(state.world_wear ?? 0)}</p>
    <p>已归还常规火种 ${esc(raw.ordinary_fires_returned ?? 0)}/10。${state.ended ? `世界结局：${esc(state.ending_summary || "已结束")}` : "再创世准备状态不表示已生成下一代世界。"}</p>
    <p>当前记录的阻塞条件：${blockers.length ? blockers.map(esc).join("；") : "暂无阻塞条件记录。"}</p>`;
}

function renderEnding(ending) {
  const panel = byId("ending");
  if (!ending) { panel.hidden = true; panel.innerHTML = ""; return; }
  panel.hidden = false;
  panel.innerHTML = `<div class="section-title"><h2>世界结束回顾</h2><span>终局档案</span></div>
    <h3>${esc(ending.title || "世界历程已结束")}</h3><p>${esc(ending.summary || "没有附加结局摘要。")}</p>
    <p>已归还火种：${esc(ending.returned_fires ?? "未记录")}</p>
    ${list(ending.refuge_names).length ? `<p>曾经建立的聚居地（不代表当前仍存续）：${list(ending.refuge_names).map(esc).join("、")}</p>` : ""}
    ${list(ending.missing_roles).length ? `<p>未完成的角色：${list(ending.missing_roles).map(esc).join("、")}</p>` : ""}
    ${list(ending.legacy).length ? `<h4>实际留下的传承</h4><ul>${list(ending.legacy).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>` : ""}`;
}

function render(state) {
  worldEnded = Boolean(state.ended);
  const regions = objectValues(state.regions);
  const titans = objectValues(state.titans);
  const organizations = objectValues(state.organizations);
  const regionNames = Object.fromEntries(regions.map((region) => [region.id, region.name]));
  const titanNames = Object.fromEntries(titans.map((titan) => [titan.id, titan.name]));
  const stories = objectValues(state.flame_stories);
  const personNames = Object.fromEntries([...objectValues(state.historical_focus), ...objectValues(state.historical_archive), ...objectValues(state.factor_paths), ...stories.map((story) => ({id: story.holder_id, name: story.holder_name}))].map((person) => [person.id, person.name]));
  const personName = (id) => personNames[id] || "人物档案";
  const averageTide = regions.length ? Math.round(regions.reduce((sum, region) => sum + Number(region.black_tide || 0), 0) / regions.length) : 0;
  byId("subtitle").textContent = `种子 ${state.seed} · 第 ${state.year} 年 · ${state.ended ? (state.ending_summary || "世界历史已经结束") : "世界仍在演化"}`;
  updateControlState(worldEnded);
  renderObservation(state);

  byId("regions").innerHTML = regions.map((region) => {
    const tide = Math.max(0, Math.min(100, Number(region.black_tide) || 0));
    return `<div class="region-card"><div><strong>${esc(region.name)}</strong><span class="badge ${tideClass(tide)}">黑潮 ${esc(tide)}</span></div>
      <div class="bar"><i class="${tideClass(tide)}" style="width:${tide}%"></i></div>
      <small>居民 ${esc(numberText(region.population))} / 避难容量 ${esc(numberText(region.refuge_capacity))}（上限 ${esc(numberText(region.refuge_capacity_limit))}） · ${esc(regionStatusNames[region.status] || region.status)}</small>
      <small>粮食储备 ${esc(numberText(region.food))} · 秩序 ${esc(region.order)} · 知识 ${esc(region.knowledge)} · 紧张 ${esc(region.tension)}</small>
      <small>主领地 ${esc(titanNames[region.titan_id] || "无")} · 信仰 ${Object.entries(region.titan_faiths || {}).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([id, value]) => `${esc(titanNames[id] || id)} ${esc(value)}`).join(" / ")}</small>
      <small>黑潮残留源 ${esc(region.tide_source)} · 防线 ${esc(region.defense)} · 伤痕 ${esc(region.scars)} · 独立人物 ${esc(region.independent_people)}</small></div>`;
  }).join("") || empty("暂无地区记录。");

  const factorPaths = objectValues(state.factor_paths);
  byId("people").innerHTML = factorPaths.length ? factorPaths.map((person) => `<button class="person-card" data-person-id="${esc(person.id)}">
    <div><strong>${esc(person.name)}</strong><span>${esc(factorNames[person.path_factor] || person.path_factor || "未知因子")}行者 · ${person.golden_status === "demigod" ? "半神" : person.golden_status === "awakened" ? "黄金裔" : "普通人物"} · ${person.alive ? "在世" : "已故"}</span></div>
    <p>${esc(regionNames[person.region_id] || person.region_name || person.region_id || "地区未记录")} · ${esc(person.age)} 岁 · ${esc(stageNames[person.life_stage] || person.life_stage || "阶段未记录")} · 主导因子：${esc(factorNames[person.dominant_factor] || person.dominant_factor)}</p>
    ${!person.alive ? `<p>${person.death_year != null ? `第 ${esc(person.death_year)} 年离世` : "离世年份未记录"}</p>` : ""}
    <small>世界影响 ${esc(person.world_impact)} · 个人影响 ${esc(person.influence)} · 关系 ${esc(person.relationship_count)}</small></button>`).join("") : empty("尚未有人留下足以进入历史焦点的影响。");

  byId("titans").innerHTML = titans.map((titan) => {
    const authority = titan.authority_state || {};
    const authorityText = authority.rescue_charges !== undefined ? `门径救援额度 ${authority.rescue_charges}`
      : authority.storm_burden !== undefined ? `天空预警 ${authority.warnings_issued || 0} · 风暴负担 ${authority.storm_burden} · 治愈 ${authority.healing_used ? "已使用" : "待命"}`
      : authority.anchor_id !== undefined ? `海洋羁绊 ${personName(authority.anchor_id)} · 航行 ${authority.voyages || 0} · 污染负担 ${authority.pollution_burden || 0}`
      : Array.isArray(authority.exposed_organization_ids) ? `守护黎明 ${authority.dawn_years || 0} 年 · ${authority.dawn_active ? "晨光仍在" : "秘密已交接"} · 面具负担 ${authority.mask_burden || 0}`
      : authority.bonded_region_id ? `守土绑定 ${authority.bonded_region_id} · 土地负担 ${authority.land_burden || 0}`
      : authority.bound_organization_id !== undefined ? `律法裁断 ${authority.judgment_count || 0} · 刚性 ${authority.rigidity || 0}`
      : authority.weave_count !== undefined ? `浪漫织结 ${authority.weave_count} · 黄金裔联结 ${authority.heir_links || 0} · 情感负担 ${authority.emotional_burden || 0}`
      : Array.isArray(authority.created_demigod_ids) ? `理性培养 ${authority.created_demigod_ids.length}/3 名半神`
      : authority.in_underworld ? `冥界引渡 ${authority.souls_guided || 0} · 羁绊 ${personName(authority.bond_id)}`
      : Array.isArray(authority.curse_victim_ids) ? `死亡试炼：厄运 ${authority.curse_victim_ids.length}/3 · 等待主动羁绊`
      : authority.journey_years !== undefined ? `纷争行旅 ${authority.journey_years} 年 · 复兴据点 ${authority.refuge_ids?.length || 0}`
      : authority.challenge_count !== undefined ? `正面挑战 ${authority.challenge_count} 次 · 胜负尚未终结`
      : Array.isArray(authority.witnessed_fire_ids) ? `岁月见证 ${authority.witnessed_fire_ids.length}/10 · 记忆负担 ${authority.memory_burden || 0}`
      : Array.isArray(authority.compatible_fire_ids) ? `负世接纳 ${authority.compatible_fire_ids.length}/11 · 世界重量 ${authority.world_burden || 0}`
      : titan.id === "oronyx" ? "等待无暇之灵魂完成忆页三问"
      : titan.id === "kephale" ? "等待完美之容器承担真实灾难" : "等待候选通过专属试炼";
    const flameText = titan.coreflame_status === "returned" ? `${coreflameStatusNames.returned}（第 ${titan.coreflame_returned_year} 年）`
      : titan.coreflame_holder ? `${coreflameStatusNames.held}：${personName(titan.coreflame_holder)}` : coreflameStatusNames[titan.coreflame_status] || "火种状态未知";
    return `<div class="titan-card"><strong>${esc(titan.name)}</strong><span>${esc(titan.domain)} · ${esc(titan.group)}</span>
      <small>因子 ${esc(factorNames[titan.factor] || titan.factor)} · 稳定 ${esc(titan.stability)} · 腐化 ${esc(titan.corruption)}</small>
      <small>${esc(titan.trial_progress ? `试炼进度 ${titan.trial_progress}/100` : "尚未出现满足条件的试炼")}</small><small>${esc(authorityText)}</small><em>${esc(flameText)}</em></div>`;
  }).join("");

  byId("flame-stories").innerHTML = stories.sort((a, b) => a.inherited_year - b.inherited_year || String(a.titan_id).localeCompare(String(b.titan_id))).map((story) => `<div class="event-row"><strong>${esc(story.domain)} · ${personButton({id: story.holder_id, name: story.holder_name})}</strong><span>
    第 ${esc(story.inherited_year)} 年承接：${esc(story.trial)}<br>${story.returned_year != null ? `第 ${esc(story.returned_year)} 年归还：${esc(story.return_reason)}<br>留下：${esc(story.imprint)}` : "仍在承担神权，故事尚未结束"}</span></div>`).join("") || empty("逐火史尚未开始。");

  byId("organizations").innerHTML = organizations.map((organization) => `<div class="organization-card"><strong>${esc(organization.name)}</strong><span>${esc(organization.kind)} · ${esc(organization.region_id)}</span><small>成员 ${esc(organization.member_count)} · 影响力 ${esc(organization.influence)}</small><p>${esc(organization.purpose)}</p></div>`).join("") || empty("暂无组织记录。");
  byId("events").innerHTML = list(state.recent_events).slice().reverse().map((event) => `<div class="event-row"><strong>第 ${esc(event.year)} 年</strong><span>${esc(event.summary)}</span></div>`).join("") || empty("尚无原始日志。");

  const crises = objectValues(state.crises).sort((a, b) => Number(b.active) - Number(a.active) || b.stage - a.stage);
  const strategyNames = {hold: "死守", evacuate: "撤离", research: "研究"};
  byId("crises").innerHTML = crises.map((crisis) => `<div class="event-row"><strong>${crisis.active ? "处理中" : crisis.outcome?.includes("failed") ? "已失败" : "已稳定"}</strong><span>${esc(regionNames[crisis.region_id] || crisis.region_id)} · ${esc(crisis.stage)}级黑潮 · 应对 ${esc(crisis.response_points)} · 参与者 ${esc(crisis.participant_count)}<br>死守 ${esc(crisis.strategy_points?.hold)} / 撤离 ${esc(crisis.strategy_points?.evacuate)} / 研究 ${esc(crisis.strategy_points?.research)}${crisis.outcome ? ` · 结果：${esc(strategyNames[crisis.outcome.replace("_failed", "")] || crisis.outcome)}` : ""}</span></div>`).join("") || empty("尚未发生达到阈值的黑潮危机。");
  const refugeCrises = objectValues(state.refuge_crises).sort((a, b) => Number(b.active) - Number(a.active) || b.started_year - a.started_year);
  const refugeStrategyNames = {welcome: "接纳", ration: "配给", settle: "新聚居地"};
  byId("refuge-crises").innerHTML = refugeCrises.map((crisis) => `<div class="event-row"><strong>${crisis.active ? "处理中" : crisis.outcome?.includes("failed") ? "已失败" : "已安置"}</strong><span>${esc(regionNames[crisis.region_id] || crisis.region_id)} · 应对 ${esc(crisis.response_points)} · 参与者 ${esc(crisis.participant_count)}<br>接纳 ${esc(crisis.strategy_points?.welcome)} / 配给 ${esc(crisis.strategy_points?.ration)} / 新聚居地 ${esc(crisis.strategy_points?.settle)}${crisis.outcome ? ` · 结果：${esc(refugeStrategyNames[crisis.outcome.replace("_failed", "")] || crisis.outcome)}` : ""}</span></div>`).join("") || empty("尚未出现突破避难容量的难民潮。");
  const archive = factorPaths.filter((person) => !person.alive);
  byId("archive").innerHTML = archive.map((person) => `<button class="person-card" data-person-id="${esc(person.id)}"><div><strong>${esc(person.name)}</strong><span>${esc(factorNames[person.path_factor] || person.path_factor)}行者 · 已故</span></div><p>${esc(person.region_id)} · ${person.death_year ? `第 ${esc(person.death_year)} 年离世` : "离世年份不明"}</p><small>世界影响 ${esc(person.world_impact)} · ${esc(person.death_cause || "死因未记录")}</small></button>`).join("") || empty("尚无已故的重要人物。");
  const observation = state.observation;
  byId("timeline").innerHTML = observation ? list(observation.timeline).map((event) => eventMarkup(event, {timeline: true})).join("") || empty("重大事件档案暂为空。")
    : `<p class="fallback-note">此运行中的服务没有 observation 接口，无法提供完整重大时间轴。逐火史摘要见“泰坦”页；下方原始日志只覆盖服务端保留的近期记录。</p>`;
  if (!observation) byId("timeline").innerHTML += stories.slice().sort((a, b) => a.inherited_year - b.inherited_year).map((story) => `<article class="event-card"><div class="event-meta"><strong>第 ${esc(story.inherited_year)} 年</strong><span>逐火史 · 旧版有限档案</span></div><h3>${esc(story.domain)} · ${personButton({id: story.holder_id, name: story.holder_name})}</h3><p>承接：${esc(story.trial)}${story.returned_year != null ? `；归还：${esc(story.return_reason)}。留下：${esc(story.imprint)}` : "；仍在承担神权。"}</p></article>`).join("");
  if (selectedPersonId) showPerson(selectedPersonId);
}

function activatePeopleTab() {
  document.querySelectorAll("[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === "people"));
  document.querySelectorAll(".view-panel").forEach((panel) => panel.classList.toggle("active", panel.id === "people-view"));
}

function renderGuideSection(title, entries, emptyText) {
  return `<section class="guide-section"><h4>${esc(title)}</h4>${entries.length ? `<ul>${entries.map((entry) => `<li><strong>${esc(entry.label || entry.key || "条目")}</strong>：${esc(entry.value ?? entry.count ?? "未记录")}<p>${esc(entry.usage || entry.description || "暂无用途说明。")}</p></li>`).join("")}</ul>` : `<p>${esc(emptyText)}</p>`}</section>`;
}

function personTrialProgress(person) {
  const evidence = person.trial_evidence || {};
  const progress = [];
  const add = (key, label, total, unit) => {
    const value = Number(evidence[key] || 0);
    if (value > 0) progress.push(`${label}：${value}${total ? `/${total}` : ""}${unit}`);
  };
  add("aquila", "艾格勒通道守护", 5, "次");
  add("georios", "吉奥里亚守土", 5, "年");
  add("phagousa", "法古萨引航", 5, "次");
  add("talanton", "塔兰顿守律", 5, "次");
  add("mnestia", "墨涅塔织结", 3, "段");
  add("zagreus", "扎格列斯试炼", 3, "阶段");
  add("oronyx_memory_years", "欧洛尼斯忆页三问", 15, "年");
  add("kephale_burdens", "刻法勒承灾", 10, "次");
  const examIndex = Number(evidence.cerces_exam_index || 0);
  const examYears = Number(evidence.cerces_exam_years || 0);
  const examStarted = examIndex > 0 || examYears > 0 || list(person.memories).includes("cerces_exam_started");
  if (examStarted) progress.push(`瑟希斯四证：已通过 ${examIndex}/4 门；当前科目累计 ${examYears} 年`);
  return progress;
}

async function showPerson(personId) {
  selectedPersonId = String(personId);
  const requestVersion = ++personRequestVersion;
  const worldVersion = worldRequestVersion;
  byId("person-detail").textContent = "正在读取人物档案……";
  let person;
  try {
    person = await request(`/api/person/${encodeURIComponent(personId)}`);
  } catch (error) {
    if (requestVersion === personRequestVersion && worldVersion === worldRequestVersion) byId("person-detail").textContent = `人物档案读取失败：${error.message}`;
    return;
  }
  if (requestVersion !== personRequestVersion || worldVersion !== worldRequestVersion || selectedPersonId !== String(personId)) return;
  const relationships = list(person.relationship_details).slice(0, 12).map((relation) => {
    const targetId = relation.target_id ?? relation.person_id ?? relation.id;
    const target = targetId === undefined ? esc(relation.target_name || "未记录人物") : personButton({id: targetId, name: relation.target_name || `人物 ${targetId}`});
    return `<li>${target} · ${esc(relation.kind || "关系未记录")} · 信任 ${esc(relation.trust ?? "未记录")}${relation.oath ? ` · 誓言：${esc(relation.oath)}` : ""}</li>`;
  }).join("") || "<li>暂无活跃关系。</li>";
  const organization = person.organization ? `${person.organization.name}（${person.organization.kind}）` : "未加入组织";
  const parents = list(person.parents).length ? list(person.parents).map((parent) => esc(parent.name)).join("、") : "无可追溯亲属记录";
  const reasons = list(person.impact_reasons).length ? list(person.impact_reasons).map(esc).join("；") : "尚未形成世界级影响";
  const fate = person.alive ? "仍在世" : `第 ${esc(person.death_year ?? "未知")} 年离世：${esc(person.death_cause || "死因未记录")}`;
  const specialRole = {unblemished_soul: "无暇之灵魂", perfect_vessel: "完美之容器"}[person.special_role];
  const identity = {ordinary: "普通人物", awakened: "黄金裔", demigod: "半神"}[person.golden_status] || "身份未记录";
  const dominantFactor = factorNames[person.dominant_factor] || person.dominant_factor || "未记录";
  const dominantValue = person.factors?.[person.dominant_factor] ?? "未记录";
  const trialProgress = personTrialProgress(person);
  const journey = list(person.journey);
  const guide = person.attribute_guide || {};
  const guideAvailable = Boolean(person.attribute_guide);
  const relationLinks = list(person.relationship_details).map((relation) => ({id: relation.target_id ?? relation.person_id ?? relation.id, name: relation.target_name})).filter((entry) => entry.id !== undefined);
  const journeyPeople = journey.flatMap((event) => list(event.people));
  const related = new Map();
  [...relationLinks, ...journeyPeople].forEach((entry) => { if (entry.id !== undefined && String(entry.id) !== String(person.id)) related.set(String(entry.id), entry); });
  const relationMarkup = [...related.values()].map((entry) => personButton(entry, "related-person")).join("") || "<span class=\"muted\">暂无可跳转的相关人物。</span>";
  byId("person-detail").innerHTML = `<div class="person-heading"><div><strong>${esc(person.name)}${specialRole ? ` · ${esc(specialRole)}` : ""}</strong><p class="person-identity">${esc(identity)} · 主导因子：${esc(dominantFactor)} ${esc(dominantValue)}</p><p>${esc(person.region_name)} · ${esc(person.age)} 岁 · ${esc(stageNames[person.life_stage] || person.life_stage || "阶段未记录")} · ${esc(organization)}</p></div><button type="button" class="close-detail" data-clear-person>关闭详情</button></div>
    <p>出身：${esc(person.origin_region_name || "未记录")} · ${fate}</p><p>亲属：${parents}</p>
    <h3>真实经历</h3>${journey.length ? `<div class="journey-list scroll-list" tabindex="0" role="region" aria-label="${esc(person.name)}的真实经历">${journey.map((event) => eventMarkup(event)).join("")}</div>` : `<p>${guideAvailable ? "完整事件档案中暂无与此人关联的重大节点。" : "旧版服务未提供人物经历档案；不能据此判断其完整经历。"}</p>`}
    ${trialProgress.length ? `<details class="person-facts person-trials"><summary>已记录的试炼进度（${trialProgress.length}）</summary><ul>${trialProgress.map((item) => `<li>${esc(item)}</li>`).join("")}</ul></details>` : ""}
    <h3>相关人物</h3><div class="related-people">${relationMarkup}</div>
    <details class="person-facts"><summary>能力、人格与人生痕迹${guideAvailable ? " · 用途说明" : " · 旧版数据"}</summary>
      ${guideAvailable ? `<p>${esc(guide.note || "数值描述人物当前状态，不单独证明某次选择的真实原因。")}</p>
        ${renderGuideSection("能力", list(guide.abilities), "暂无能力条目。")}
        ${renderGuideSection("人格", list(guide.personality), "暂无人格条目。")}
        ${renderGuideSection("人生痕迹", list(guide.traces), "暂无已记录痕迹。")}`
        : `<p>旧版接口没有属性用途说明。当前属性是状态值，不能单独视为某次选择的真实原因。</p>
          <p>主导因子：${esc(factorNames[person.dominant_factor] || person.dominant_factor)} · 世界影响 ${esc(person.world_impact)}</p>
          <p>候选人特质：勇气 ${esc(person.courage)} · 共情 ${esc(person.empathy)} · 意志 ${esc(person.willpower)} · 克制 ${esc(person.restraint)} · 野心 ${esc(person.ambition)} · 适应力 ${esc(person.adaptability)} · 责任 ${esc(person.responsibility)}</p>
          <p>可说明的累计痕迹：${Object.entries(person.life_traces || {}).filter(([key, value]) => value > 0 && !["loss", "betrayal", "victory_choice"].includes(key)).map(([key, value]) => `${esc(traceNames[key] || key)} ${esc(value)}`).join(" · ") || "暂无可追溯痕迹"}</p>
          <p>旧版“失去/背叛”计数语义不完整，且胜利后的选择尚无生产逻辑，因此不据此声称发生过对应经历。</p>`}
    </details>
    <details class="person-facts"><summary>关系与档案补充</summary><p>泰坦关系：${list(person.titan_relations).map((relation) => `${esc(relation.name)}（${esc(relation.domain)}）${relation.stance >= 0 ? "立场" : "反对"} ${esc(Math.abs(relation.stance))}`).join("、") || "尚未形成明确的泰坦关系"}</p><p>影响来源：${reasons}</p><ul>${relationships}</ul></details>`;
  document.querySelectorAll("[data-person-id]").forEach((card) => card.classList.toggle("selected", card.dataset.personId === String(personId)));
}

function clearPersonSelection() {
  selectedPersonId = null;
  personRequestVersion += 1;
  byId("person-detail").textContent = "点击人物、事件人物或相关人物可查看档案。";
  document.querySelectorAll("[data-person-id]").forEach((card) => card.classList.remove("selected"));
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("X-Amphoreus-View", "compact");
  const response = await fetch(path, {...options, headers});
  if (!response.ok) {
    let message = `请求失败（HTTP ${response.status}）`;
    try { const body = await response.json(); if (body?.error) message = body.error; } catch {}
    throw new Error(message);
  }
  try { return await response.json(); } catch { throw new Error("服务返回了无法解析的数据"); }
}

async function runWorldAction(path, options, clearSelection = false) {
  if (actionInFlight) return;
  actionInFlight = true;
  worldRequestVersion += 1;
  personRequestVersion += 1;
  updateControlState();
  try {
    const state = await request(path, options);
    if (clearSelection) clearPersonSelection();
    render(state);
  } catch (error) {
    byId("subtitle").textContent = `操作失败：${error.message}`;
    if (selectedPersonId !== null) showPerson(selectedPersonId);
  } finally {
    actionInFlight = false;
    updateControlState(worldEnded);
  }
}

byId("step").addEventListener("click", () => runWorldAction("/api/step", {method: "POST"}));
byId("advance").addEventListener("click", () => runWorldAction("/api/advance", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({years: 10})}));
byId("advance-century").addEventListener("click", () => runWorldAction("/api/advance", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({years: 100})}));
byId("reset").addEventListener("click", () => runWorldAction("/api/reset", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({})}, true));
document.addEventListener("click", (event) => {
  const clear = event.target.closest("[data-clear-person]");
  if (clear) { clearPersonSelection(); return; }
  const card = event.target.closest("[data-person-id]");
  if (card) { activatePeopleTab(); showPerson(card.dataset.personId); }
});
document.querySelectorAll("[data-view]").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll("[data-view]").forEach((item) => item.classList.toggle("active", item === tab));
  document.querySelectorAll(".view-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `${tab.dataset.view}-view`));
}));
const initialVersion = worldRequestVersion;
request("/api/state").then((state) => { if (initialVersion === worldRequestVersion) render(state); }).catch((error) => { if (initialVersion === worldRequestVersion) byId("subtitle").textContent = `无法读取世界状态：${error.message}`; });
