const byId = (id) => document.getElementById(id);
const stageNames = {child: "儿童", youth: "青年", adult: "成人", elder: "长者"};
const factorNames = {destruction: "毁灭", remembrance: "记忆", erudition: "智识", harmony: "同谐", elation: "欢愉", nihility: "虚无", hunt: "巡猎", beauty: "纯美", preservation: "存护", equilibrium: "均衡", order: "秩序", permanence: "不朽"};
const regionStatusNames = {stable: "稳定", strained: "承压", overwhelmed: "避难超载", endangered: "黑潮威胁", lost: "已失陷"};
const coreflameStatusNames = {within_titan: "火种仍在泰坦", held: "火种已被承接", returned: "火种已归还创世涡心"};
let actionInFlight = false;
let selectedPersonId = null;
let personRequestVersion = 0;
let worldEnded = false;

function updateControlState(ended = false) {
  byId("step").disabled = actionInFlight || ended;
  byId("advance").disabled = actionInFlight || ended;
  byId("reset").disabled = actionInFlight;
}

function tideClass(value) {
  if (value >= 60) return "danger";
  if (value >= 30) return "warning";
  return "safe";
}

function render(state) {
  worldEnded = Boolean(state.ended);
  const regions = Object.values(state.regions);
  const averageTide = Math.round(regions.reduce((sum, region) => sum + region.black_tide, 0) / regions.length);
  const worldStatus = state.ended ? (state.ending_summary || "世界历史已经结束") : "世界仍在演化";
  byId("subtitle").textContent = `种子 ${state.seed} · 第 ${state.year} 年 · ${worldStatus}`;
  updateControlState(state.ended);
  byId("metrics").innerHTML = [
    ["地区居民总数", state.population.total_civilians.toLocaleString()],
    ["独立人物样本", state.population.alive_individuals],
    ["因子行者", Object.keys(state.factor_paths || {}).length],
    ["平均黑潮", `${averageTide} / 100`],
    ["世界劫余", state.world_wear],
    ["区域数量", regions.length],
    ["火种持有", Object.values(state.titans).filter((titan) => titan.coreflame_holder).length],
    ["活跃组织", Object.values(state.organizations).filter((org) => org.member_count > 0).length],
  ].map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join("");
  const unstable = regions.slice().sort((a, b) => (b.black_tide + b.tension) - (a.black_tide + a.tension))[0];
  const fires = Object.values(state.titans).filter((titan) => titan.coreflame_holder);
  const titanNames = Object.fromEntries(Object.values(state.titans).map((titan) => [titan.id, titan.name]));
  byId("overview-summary").innerHTML = `<div class="section-title"><h2>本年世界判断</h2><span>由系统状态自动归纳</span></div>
    <p>${unstable ? `最需要关注的是<strong>${unstable.name}</strong>：黑潮 ${unstable.black_tide}，社会紧张 ${unstable.tension}。` : "正在等待地区数据。"}</p>
    <p>世界劫余为 ${state.world_wear}：它代表尚未再创世而累积的不可逆损伤，会在长期抬高黑潮残留源并削弱泰坦。</p>
    <p>已被承接的火种：${fires.length ? fires.map((titan) => `${titan.name}（${titan.domain}）`).join("、") : "尚无"}。</p>
    <p>人物栏只显示十二因子中各自走得最远的一人；完整人物档案仍保留在世界历史中，不会因重复动作挤占观察面板。</p>`;

  byId("regions").innerHTML = regions.map((region) => `
    <div class="region-card">
      <div><strong>${region.name}</strong><span class="badge ${tideClass(region.black_tide)}">黑潮 ${region.black_tide}</span></div>
      <div class="bar"><i class="${tideClass(region.black_tide)}" style="width:${region.black_tide}%"></i></div>
      <small>居民 ${region.population.toLocaleString()} / 避难容量 ${region.refuge_capacity.toLocaleString()}（上限 ${region.refuge_capacity_limit.toLocaleString()}） · ${regionStatusNames[region.status] || region.status}</small>
      <small>粮食储备 ${region.food.toLocaleString()} · 秩序 ${region.order} · 知识 ${region.knowledge} · 紧张 ${region.tension}</small>
      <small>主领地 ${titanNames[region.titan_id] || "无"} · 信仰 ${Object.entries(region.titan_faiths).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([id, value]) => `${titanNames[id] || id} ${value}`).join(" / ")}</small>
      <small>黑潮残留源 ${region.tide_source} · 防线 ${region.defense} · 伤痕 ${region.scars} · 独立人物 ${region.independent_people}</small>
    </div>`).join("");

  const factorPaths = Object.values(state.factor_paths || {});
  const people = factorPaths.filter((person) => person.alive);
  byId("people").innerHTML = people.length ? people.map((person) => `
    <button class="person-card" data-person-id="${person.id}">
      <div><strong>${person.name}</strong><span>${factorNames[person.path_factor]}行者 · ${person.golden_status === "demigod" ? "半神" : person.golden_status === "awakened" ? "黄金裔" : "人物"}</span></div>
      <p>${person.region_id} · ${person.age} 岁 · ${stageNames[person.life_stage]} · 主导因子：${factorNames[person.dominant_factor]}</p>
      <small>世界影响 ${person.world_impact} · 个人影响 ${person.influence} · 关系 ${person.relationship_count}</small>
    </button>`).join("") : "<p class='empty'>尚未有人留下足以进入历史焦点的影响。</p>";

  byId("titans").innerHTML = Object.values(state.titans).map((titan) => {
    const authority = titan.authority_state || {};
    const authorityText = authority.rescue_charges !== undefined ? `门径救援额度 ${authority.rescue_charges}`
      : authority.storm_burden !== undefined ? `天空预警 ${authority.warnings_issued || 0} · 风暴负担 ${authority.storm_burden} · 治愈 ${authority.healing_used ? "已使用" : "待命"}`
      : authority.anchor_id !== undefined ? `海洋羁绊 ${authority.anchor_id || "尚未相遇"} · 航行 ${authority.voyages || 0} · 污染负担 ${authority.pollution_burden || 0}`
      : authority.bonded_region_id ? `守土绑定 ${authority.bonded_region_id} · 土地负担 ${authority.land_burden || 0}`
      : authority.bound_organization_id !== undefined ? `律法刚性 ${authority.rigidity || 0} · 绑定组织 ${authority.bound_organization_id || "无"}`
      : authority.weave_count !== undefined ? `浪漫织结 ${authority.weave_count} · 情感负担 ${authority.emotional_burden || 0}`
      : Array.isArray(authority.created_demigod_ids) ? `理性培养 ${authority.created_demigod_ids.length}/3 名半神`
      : "尚无已实现的专属权能";
    const flameText = titan.coreflame_status === "returned"
      ? `${coreflameStatusNames.returned}（第 ${titan.coreflame_returned_year} 年）`
      : titan.coreflame_holder ? `${coreflameStatusNames.held}：${titan.coreflame_holder}`
      : coreflameStatusNames[titan.coreflame_status] || "火种状态未知";
    return `
    <div class="titan-card">
      <strong>${titan.name}</strong><span>${titan.domain} · ${titan.group}</span>
      <small>因子 ${factorNames[titan.factor]} · 稳定 ${titan.stability} · 腐化 ${titan.corruption}</small>
      <small>${titan.trial_progress ? `试炼进度 ${titan.trial_progress}/100` : "尚未出现满足条件的试炼"}</small>
      <small>${authorityText}</small>
      <em>${flameText}</em>
    </div>`;
  }).join("");

  byId("organizations").innerHTML = Object.values(state.organizations).map((organization) => `
    <div class="organization-card">
      <strong>${organization.name}</strong><span>${organization.kind} · ${organization.region_id}</span>
      <small>成员 ${organization.member_count} · 影响力 ${organization.influence}</small>
      <p>${organization.purpose}</p>
    </div>`).join("");

  byId("events").innerHTML = state.recent_events.slice().reverse().map((event) => `
    <div class="event-row"><strong>第 ${event.year} 年</strong><span>${event.summary}</span></div>`).join("") || "<p class='empty'>尚无事件。</p>";

  const regionNames = Object.fromEntries(regions.map((region) => [region.id, region.name]));
  const crises = Object.values(state.crises).sort((a, b) => Number(b.active) - Number(a.active) || b.stage - a.stage);
  const strategyNames = {hold: "死守", evacuate: "撤离", research: "研究"};
  byId("crises").innerHTML = crises.map((crisis) => `
    <div class="event-row"><strong>${crisis.active ? "处理中" : crisis.outcome?.includes("failed") ? "已失败" : "已稳定"}</strong><span>${regionNames[crisis.region_id] || crisis.region_id} · ${crisis.stage}级黑潮 · 应对 ${crisis.response_points} · 参与者 ${crisis.participant_count}<br>死守 ${crisis.strategy_points.hold} / 撤离 ${crisis.strategy_points.evacuate} / 研究 ${crisis.strategy_points.research}${crisis.outcome ? ` · 结果：${strategyNames[crisis.outcome.replace("_failed", "")] || crisis.outcome}` : ""}</span></div>`).join("") || "<p class='empty'>尚未发生达到阈值的黑潮危机。</p>";

  const refugeCrises = Object.values(state.refuge_crises || {}).sort((a, b) => Number(b.active) - Number(a.active) || b.started_year - a.started_year);
  const refugeStrategyNames = {welcome: "接纳", ration: "配给", settle: "新聚居地"};
  byId("refuge-crises").innerHTML = refugeCrises.map((crisis) => `
    <div class="event-row"><strong>${crisis.active ? "处理中" : crisis.outcome?.includes("failed") ? "已失败" : "已安置"}</strong><span>${regionNames[crisis.region_id] || crisis.region_id} · 应对 ${crisis.response_points} · 参与者 ${crisis.participant_count}<br>接纳 ${crisis.strategy_points.welcome} / 配给 ${crisis.strategy_points.ration} / 新聚居地 ${crisis.strategy_points.settle}${crisis.outcome ? ` · 结果：${refugeStrategyNames[crisis.outcome.replace("_failed", "")] || crisis.outcome}` : ""}</span></div>`).join("") || "<p class='empty'>尚未出现突破避难容量的难民潮。</p>";

  const archive = factorPaths.filter((person) => !person.alive);
  byId("archive").innerHTML = archive.map((person) => `
    <button class="person-card" data-person-id="${person.id}">
      <div><strong>${person.name}</strong><span>${factorNames[person.path_factor]}行者 · 已故</span></div>
      <p>${person.region_id} · ${person.death_year ? `第 ${person.death_year} 年离世` : "离世年份不明"}</p>
      <small>世界影响 ${person.world_impact} · ${person.death_cause || "死因未记录"}</small>
    </button>`).join("") || "<p class='empty'>尚无已故的重要人物。</p>";
  if (selectedPersonId && factorPaths.some((person) => person.id === selectedPersonId)) {
    showPerson(selectedPersonId);
  } else if (selectedPersonId) {
    clearPersonSelection();
  }
}

async function showPerson(personId) {
  selectedPersonId = personId;
  const requestVersion = ++personRequestVersion;
  let person;
  try {
    person = await request(`/api/person/${personId}`);
  } catch (error) {
    if (requestVersion === personRequestVersion) byId("person-detail").textContent = error.message;
    return;
  }
  if (requestVersion !== personRequestVersion || selectedPersonId !== personId) return;
  const relationships = person.relationship_details.slice(0, 8).map((relation) =>
    `<li>${relation.target_name} · ${relation.kind} · 信任 ${relation.trust}${relation.oath ? ` · 誓言：${relation.oath}` : ""}</li>`).join("") || "<li>暂无活跃关系</li>";
  const organization = person.organization ? `${person.organization.name}（${person.organization.kind}）` : "未加入组织";
  const parents = person.parents.length ? person.parents.map((parent) => parent.name).join("、") : "无可追溯亲属记录";
  const reasons = person.impact_reasons.length ? person.impact_reasons.join("；") : "尚未形成世界级影响";
  const fate = person.alive ? "仍在世" : `第 ${person.death_year} 年离世：${person.death_cause || "死因未记录"}`;
  const titanRelations = person.titan_relations.map((relation) => `${relation.name}（${relation.domain}）${relation.stance >= 0 ? "虔诚" : "反抗"} ${Math.abs(relation.stance)}`).join("、") || "尚未形成明确的泰坦关系";
  const traits = [["勇气", person.courage], ["共情", person.empathy], ["意志", person.willpower], ["克制", person.restraint], ["野心", person.ambition], ["适应力", person.adaptability], ["责任", person.responsibility]]
    .map(([name, value]) => `${name} ${value}`).join(" · ");
  const traceNames = {
    guardianship: "守护", loss: "失去", oath: "誓言", betrayal: "背叛", responsibility: "责任",
    victory_choice: "胜利后的选择", black_tide_exposure: "黑潮侵蚀", organization_action: "重大组织行为",
  };
  const lifeTraces = Object.entries(person.life_traces || {}).filter(([, value]) => value > 0)
    .map(([trace, value]) => `${traceNames[trace] || trace} ${value}`).join(" · ") || "尚未留下可追溯的人生痕迹";
  const reasonExam = person.trial_evidence?.cerces_exam_index !== undefined
    ? `瑟希斯四证：已通过 ${person.trial_evidence.cerces_exam_index}/4 · 当前科目累计 ${person.trial_evidence.cerces_exam_years || 0} 年`
    : "瑟希斯四证：尚未参加";
  const flameTrials = [
    reasonExam,
    person.trial_evidence?.aquila !== undefined ? `艾格勒通道：${person.trial_evidence.aquila}/5 次风暴守护` : "艾格勒通道：尚未开始",
    person.trial_evidence?.phagousa !== undefined ? `法古萨引航：${person.trial_evidence.phagousa}/5 次污海引航` : "法古萨引航：尚未开始",
    person.trial_evidence?.talanton !== undefined ? `塔兰顿守律：${person.trial_evidence.talanton}/5 次危机中的自我约束` : "塔兰顿守律：尚未立律",
    person.trial_evidence?.mnestia !== undefined ? `墨涅塔编织：${person.trial_evidence.mnestia}/3 段相互承认的关系` : "墨涅塔编织：尚未织结",
  ].join("<br>");
  byId("person-detail").innerHTML = `<strong>${person.name}</strong><p>${person.region_name} · ${person.age} 岁 · ${stageNames[person.life_stage]} · ${organization}</p><p>出身：${person.origin_region_name}</p><p>${fate}</p><p>亲属：${parents}</p><p>主导因子：${factorNames[person.dominant_factor]} · 世界影响 ${person.world_impact}</p><p>候选人特质：${traits}</p><p>人生痕迹：${lifeTraces}</p><p>${flameTrials}</p><p>泰坦关系：${titanRelations}</p><p>影响来源：${reasons}</p><ul>${relationships}</ul>`;
  document.querySelectorAll("[data-person-id]").forEach((card) => card.classList.toggle("selected", card.dataset.personId === personId));
}

function clearPersonSelection() {
  selectedPersonId = null;
  personRequestVersion += 1;
  byId("person-detail").textContent = "点击人物可查看其关系、誓言与组织。";
  document.querySelectorAll("[data-person-id]").forEach((card) => card.classList.remove("selected"));
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error("无法读取世界状态");
  return response.json();
}

async function runWorldAction(path, options, clearSelection = false) {
  if (actionInFlight) return;
  actionInFlight = true;
  updateControlState();
  try {
    const state = await request(path, options);
    if (clearSelection) clearPersonSelection();
    render(state);
  } catch (error) {
    byId("subtitle").textContent = error.message;
  } finally {
    actionInFlight = false;
    updateControlState(worldEnded);
  }
}

byId("step").addEventListener("click", () => runWorldAction("/api/step", {method: "POST"}));
byId("advance").addEventListener("click", () => runWorldAction("/api/advance", {
  method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({years: 10}),
}));
byId("reset").addEventListener("click", () => runWorldAction("/api/reset", {
  method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({}),
}, true));
document.addEventListener("click", (event) => {
  const card = event.target.closest("[data-person-id]");
  if (card) showPerson(card.dataset.personId);
});
document.querySelectorAll("[data-view]").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll("[data-view]").forEach((item) => item.classList.toggle("active", item === tab));
  document.querySelectorAll(".view-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `${tab.dataset.view}-view`));
}));
request("/api/state").then(render).catch((error) => { byId("subtitle").textContent = error.message; });
