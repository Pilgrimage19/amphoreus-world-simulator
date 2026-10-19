const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const appSource = fs.readFileSync(path.join(__dirname, "..", "src", "amphoreus_sim", "web", "app.js"), "utf8");
const htmlSource = fs.readFileSync(path.join(__dirname, "..", "src", "amphoreus_sim", "web", "index.html"), "utf8");

function element() {
  const listeners = {};
  const classes = new Set();
  return {
    innerHTML: "", textContent: "", disabled: false, hidden: false, dataset: {}, listeners,
    addEventListener(name, callback) { listeners[name] = callback; },
    classList: {toggle(name, force) { if (force) classes.add(name); else classes.delete(name); }, add(name) { classes.add(name); }, remove(name) { classes.delete(name); }, contains(name) { return classes.has(name); }},
  };
}

function response(value, {ok = true, status = 200} = {}) {
  return {ok, status, json: async () => value};
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => { resolve = resolvePromise; reject = rejectPromise; });
  return {promise, resolve, reject};
}

function harness({state, person, pendingInitial = false, fetchOverride = null}) {
  const elements = new Map();
  const ids = ["subtitle", "step", "advance", "advance-century", "reset", "chapter", "metrics", "highlights", "highlights-label", "spotlight", "recap", "ending", "overview-summary", "regions", "people", "person-detail", "titans", "flame-stories", "organizations", "events", "crises", "refuge-crises", "archive", "timeline"];
  ids.forEach((id) => elements.set(id, element()));
  const tabs = ["overview", "regions", "people", "titans", "history"].map((view) => Object.assign(element(), {dataset: {view}}));
  const panels = tabs.map(({dataset}) => Object.assign(element(), {id: `${dataset.view}-view`}));
  let delegatedClick;
  let resolveInitial;
  const requests = [];
  const personCards = ["1", "999", "1000"].map((personId) => Object.assign(element(), {dataset: {personId}}));
  const document = {
    getElementById(id) { return elements.get(id); },
    querySelectorAll(selector) {
      if (selector === "[data-view]") return tabs;
      if (selector === ".view-panel") return panels;
      if (selector === "[data-person-id]") return personCards;
      return [];
    },
    addEventListener(name, callback) { if (name === "click") delegatedClick = callback; },
  };
  const fetch = (url, options = {}) => {
    requests.push([url, options]);
    if (fetchOverride) return fetchOverride(url, options);
    if (url === "/api/state" && pendingInitial) return new Promise((resolve) => { resolveInitial = resolve; });
    const value = url.startsWith("/api/person/") ? person : state;
    return Promise.resolve(response(value));
  };
  vm.runInNewContext(appSource, {document, fetch, console, URLSearchParams, Headers, setTimeout, clearTimeout, Promise, JSON, Object, String, Number, Math, Map, Array, Error});
  return {
    elements, tabs, panels, requests, personCards,
    clickPerson(id) {
      delegatedClick({target: {closest(selector) { return selector === "[data-clear-person]" ? null : selector === "[data-person-id]" ? {dataset: {personId: String(id)}} : null; }}});
    },
    resolveInitial(value) { resolveInitial({ok: true, status: 200, json: async () => value}); },
  };
}

function baseState(observation) {
  const state = {
    seed: 42, year: 100, ended: false, ending_summary: null, world_wear: 12,
    population: {total_civilians: 10000, alive_individuals: 2}, regions: {}, titans: {}, organizations: {},
    flame_stories: {}, recent_events: [], crises: {}, refuge_crises: {}, factor_paths: {}, historical_focus: {}, historical_archive: {},
  };
  if (observation !== undefined) state.observation = observation;
  return state;
}

test("factor roster keeps living and deceased heroes together and escapes labels", async () => {
  for (const alive of [true, false]) {
    const state = baseState();
    state.factor_paths = {
      harmony: {id: "1", name: "<hero>", path_factor: "harmony", dominant_factor: "harmony", alive, region_id: "<region>"},
      erudition: {id: "2", name: "逝去行者", path_factor: "erudition", dominant_factor: "erudition", alive: false, death_year: 73},
    };
    const ui = harness({state});
    await new Promise(setImmediate);
    const roster = ui.elements.get("people").innerHTML;
    assert.equal((roster.match(/class="person-card"/g) || []).length, 2);
    assert.match(roster, /&lt;hero&gt;/);
    assert.match(roster, /&lt;region&gt;/);
    assert.match(roster, /第 73 年离世/);
    assert.match(roster, /已故/);
    assert.equal(roster.includes("在世"), alive);
  }
});

test("observation draws the full batch/timeline, escapes text, and opens related off-roster people", async () => {
  const observation = {
    chapter: {title: "阶段 <unsafe>", summary: "此阶段摘要"},
    metrics: {surviving_regions: 4, ordinary_returned: 2, active_bearers: 3, living_tide: 41},
    highlights: [{id: "e100", year: 100, type: "coreflame_inherited", title: "<script>alert(1)</script>", summary: "摘要 & 内容", people: [{id: 999, name: "<img src=x>"}], causal_event_ids: ["e99"]}],
    timeline: Array.from({length: 101}, (_, index) => ({id: `event-${index}`, year: index, type: "记录", title: `节点 ${index}`, summary: "档案事件", people: [], causal_event_ids: []})),
    spotlight: [{person_id: 1, name: "焦点人物", domain: "记忆", status: "仍在世", summary: "摘要", latest_year: 100}],
    recap: {from_year: 1, to_year: 100, important_count: 101, events: Array.from({length: 101}, (_, index) => ({id: `batch-${index}`, year: index, title: `批次节点 ${index}`, summary: "真实档案", people: [], causal_event_ids: []})), population_delta: -10},
    ending: {title: "历程结束", summary: "终局摘要", returned_fires: 10, refuge_names: ["磐生城"], missing_roles: ["完美之容器"], legacy: ["一段传承"]},
    last_event_id: "e100",
  };
  const person = {
    id: 999, name: "档案外人物", region_name: "奥赫玛", origin_region_name: "斯缇科西亚", age: 30, life_stage: "adult", alive: true,
    golden_status: "awakened", dominant_factor: "remembrance", factors: {remembrance: 93},
    parents: [], relationship_details: [{target_id: 1000, target_name: "另一人物", kind: "信任", trust: 70}], impact_reasons: [], titan_relations: [],
    trial_evidence: {cerces_exam_index: 1, cerces_exam_years: 2, oronyx_memory_years: 5, kephale_burdens: 4}, memories: ["cerces_exam_started"],
    journey: [{id: "j1", year: 90, type: "见证", title: "相关经历", summary: "已记录经历", people: [{id: 1000, name: "另一人物"}], causal_event_ids: []}],
    attribute_guide: {note: "只描述记录，不证明原因", abilities: [{key: "insight", label: "洞察", value: 75, usage: "影响观察与判断。"}], personality: [], traces: [{key: "oath", label: "誓言", count: 1, description: "记录过的誓言。"}]},
  };
  const ui = harness({state: baseState(observation), person});
  await new Promise(setImmediate);
  assert.match(ui.elements.get("chapter").innerHTML, /&lt;unsafe&gt;/);
  assert.match(ui.elements.get("highlights").innerHTML, /&lt;script&gt;/);
  assert.match(ui.elements.get("highlights").innerHTML, /<span>逐火承接<\/span>/);
  assert.match(ui.elements.get("highlights").innerHTML, /<summary>原始记录<\/summary><p>记录类型：coreflame_inherited/);
  assert.doesNotMatch(ui.elements.get("highlights").innerHTML, /<script>/);
  assert.equal((ui.elements.get("timeline").innerHTML.match(/class="event-card timeline-event"/g) || []).length, 101);
  assert.equal((ui.elements.get("recap").innerHTML.match(/class="event-card"/g) || []).length, 101);
  assert.match(ui.elements.get("ending").innerHTML, /曾经建立的聚居地/);
  assert.match(ui.elements.get("ending").innerHTML, /不代表当前仍存续/);
  ui.clickPerson(999);
  await new Promise(setImmediate);
  assert.match(ui.elements.get("person-detail").innerHTML, /相关经历/);
  assert.match(ui.elements.get("person-detail").innerHTML, /class="journey-list scroll-list" tabindex="0" role="region" aria-label="档案外人物的真实经历"/);
  assert.match(ui.elements.get("person-detail").innerHTML, /洞察/);
  assert.match(ui.elements.get("person-detail").innerHTML, /另一人物/);
  assert.match(ui.elements.get("person-detail").innerHTML, /黄金裔 · 主导因子：记忆 93/);
  assert.match(ui.elements.get("person-detail").innerHTML, /瑟希斯四证：已通过 1\/4 门/);
  assert.match(ui.elements.get("person-detail").innerHTML, /欧洛尼斯忆页三问：5\/15年/);
  assert.match(ui.elements.get("person-detail").innerHTML, /刻法勒承灾：4\/10次/);
  assert.doesNotMatch(ui.elements.get("person-detail").innerHTML, /艾格勒通道守护/);
  assert.ok(ui.requests.some(([url]) => url === "/api/person/999"));
  assert.equal(ui.requests.find(([url]) => url === "/api/person/999")[1].headers.get("X-Amphoreus-View"), "compact");
  assert.equal(ui.personCards.find((card) => card.dataset.personId === "999").classList.contains("selected"), true);
  assert.equal(ui.personCards.find((card) => card.dataset.personId === "1").classList.contains("selected"), false);
  ui.elements.get("advance").listeners.click();
  await new Promise(setImmediate);
  assert.equal(ui.requests.filter(([url]) => url === "/api/person/999").length, 2);
  assert.equal(ui.personCards.find((card) => card.dataset.personId === "999").classList.contains("selected"), true);
});

test("long observation lists and overview entrances remain keyboard-scrollable", () => {
  assert.match(htmlSource, /id="highlights" class="events scroll-list" tabindex="0" role="region" aria-label="本阶段重大事件"/);
  assert.match(htmlSource, /id="spotlight" class="spotlight-list scroll-list" tabindex="0" role="region" aria-label="逐火档案人物"/);
  assert.match(appSource, /class="recap-events scroll-list" tabindex="0" role="region" aria-label="最近一次推进事件列表"/);
  assert.match(appSource, /class="journey-list scroll-list" tabindex="0" role="region" aria-label=/);
  assert.match(htmlSource, /本阶段人物<\/h2><span>从逐火档案选取<\/span>/);
});

test("legacy service clearly limits coverage and uses flame stories without inventing a batch recap", async () => {
  const state = baseState();
  state.flame_stories = {one: {titan_id: "t1", domain: "记忆", holder_id: 8, holder_name: "持火者", inherited_year: 20, trial: "真实试炼", returned_year: null}};
  const ui = harness({state, person: {}});
  await new Promise(setImmediate);
  assert.match(ui.elements.get("chapter").innerHTML, /有限观察/);
  assert.match(ui.elements.get("chapter").innerHTML, /不代表完整历史/);
  assert.match(ui.elements.get("recap").innerHTML, /旧版接口不含批次回顾/);
  assert.match(ui.elements.get("highlights").innerHTML, /真实试炼/);
  assert.match(ui.elements.get("highlights-label").textContent, /非完整档案/);
  assert.match(ui.elements.get("timeline").innerHTML, /无法提供完整重大时间轴/);
});

test("one, ten, and one hundred year controls keep the request lock", async () => {
  const observation = {chapter: {title: "阶段", summary: "摘要"}, metrics: {}, highlights: [], timeline: [], spotlight: [], recap: null, ending: null};
  const ui = harness({state: baseState(observation), person: {}});
  await new Promise(setImmediate);
  const stateRequest = ui.requests.find(([url]) => url === "/api/state");
  assert.equal(stateRequest[1].headers.get("X-Amphoreus-View"), "compact");
  assert.equal(stateRequest[1].method, undefined);
  assert.equal(stateRequest[1].body, undefined);
  ui.elements.get("advance").listeners.click();
  ui.elements.get("advance-century").listeners.click();
  assert.equal(ui.requests.filter(([url]) => url === "/api/advance").length, 1);
  const tenYearRequest = ui.requests.find(([url]) => url === "/api/advance")[1];
  assert.equal(tenYearRequest.headers.get("X-Amphoreus-View"), "compact");
  assert.equal(tenYearRequest.headers.get("Content-Type"), "application/json");
  assert.equal(tenYearRequest.method, "POST");
  assert.equal(JSON.parse(tenYearRequest.body).years, 10);
  await new Promise(setImmediate);
  ui.elements.get("advance-century").listeners.click();
  const hundredYearRequest = ui.requests.filter(([url]) => url === "/api/advance")[1][1];
  assert.equal(hundredYearRequest.headers.get("X-Amphoreus-View"), "compact");
  assert.equal(hundredYearRequest.headers.get("Content-Type"), "application/json");
  assert.equal(hundredYearRequest.method, "POST");
  assert.equal(JSON.parse(hundredYearRequest.body).years, 100);
  await new Promise(setImmediate);
  ui.elements.get("step").listeners.click();
  assert.ok(ui.requests.some(([url, options]) => url === "/api/step" && options.method === "POST"));
});

test("failed world action reports the error and reloads the selected off-roster person", async () => {
  const state = baseState({chapter: {title: "当前世界", summary: "当前状态"}, metrics: {}, highlights: [], timeline: [], spotlight: [], recap: null, ending: null});
  const person = {id: 999, name: "关系人物", alive: true, parents: [], relationship_details: [], impact_reasons: [], titan_relations: [], journey: [], attribute_guide: {note: "真实人物档案", abilities: [], personality: [], traces: []}};
  const stalePerson = deferred();
  let personCalls = 0;
  const ui = harness({state, person, fetchOverride(url) {
    if (url === "/api/state") return Promise.resolve(response(state));
    if (url.startsWith("/api/person/")) {
      personCalls += 1;
      return personCalls === 1 ? stalePerson.promise : Promise.resolve(response(person));
    }
    if (url === "/api/step") return Promise.reject(new Error("simulated world action failure"));
    throw new Error(`Unexpected request: ${url}`);
  }});
  await new Promise(setImmediate);
  ui.clickPerson(999);
  ui.elements.get("step").listeners.click();
  await new Promise(setImmediate);
  stalePerson.resolve(response({...person, name: "过期人物详情"}));
  await new Promise(setImmediate);
  assert.match(ui.elements.get("subtitle").textContent, /操作失败：simulated world action failure/);
  assert.match(ui.elements.get("person-detail").innerHTML, /关系人物/);
  assert.doesNotMatch(ui.elements.get("person-detail").innerHTML, /过期人物详情|正在读取人物档案/);
  assert.equal(ui.personCards.find((card) => card.dataset.personId === "999").classList.contains("selected"), true);
});

test("a person response finishing during reset cannot overwrite the new world's cleared detail", async () => {
  const oldState = baseState({chapter: {title: "旧世界", summary: "旧状态"}, metrics: {}, highlights: [], timeline: [], spotlight: [], recap: null, ending: null});
  const newState = baseState({chapter: {title: "新世界", summary: "重置完成"}, metrics: {}, highlights: [], timeline: [], spotlight: [], recap: null, ending: null});
  const oldPerson = {id: 999, name: "旧世界人物", alive: true, parents: [], relationship_details: [], impact_reasons: [], titan_relations: [], journey: [], attribute_guide: {note: "旧档案", abilities: [], personality: [], traces: []}};
  const personRequest = deferred();
  const resetRequest = deferred();
  const ui = harness({state: oldState, person: oldPerson, fetchOverride(url) {
    if (url === "/api/state") return Promise.resolve(response(oldState));
    if (url.startsWith("/api/person/")) return personRequest.promise;
    if (url === "/api/reset") return resetRequest.promise;
    throw new Error(`Unexpected request: ${url}`);
  }});
  await new Promise(setImmediate);
  ui.clickPerson(999);
  ui.elements.get("reset").listeners.click();
  personRequest.resolve(response(oldPerson));
  await new Promise(setImmediate);
  assert.doesNotMatch(ui.elements.get("person-detail").innerHTML, /旧世界人物/);
  resetRequest.resolve(response(newState));
  await new Promise(setImmediate);
  assert.match(ui.elements.get("chapter").innerHTML, /新世界/);
  assert.doesNotMatch(ui.elements.get("chapter").innerHTML, /旧世界/);
  assert.doesNotMatch(ui.elements.get("person-detail").innerHTML, /旧世界人物/);
  assert.equal(ui.elements.get("person-detail").textContent, "点击人物、事件人物或相关人物可查看档案。");
  assert.equal(ui.personCards.find((card) => card.dataset.personId === "999").classList.contains("selected"), false);
});

test("late response for person A cannot replace the newer selection of person B", async () => {
  const state = baseState({chapter: {title: "当前世界", summary: "当前状态"}, metrics: {}, highlights: [], timeline: [], spotlight: [], recap: null, ending: null});
  const personARequest = deferred();
  const personB = {id: 1000, name: "人物乙", alive: true, parents: [], relationship_details: [], impact_reasons: [], titan_relations: [], journey: [], attribute_guide: {note: "B", abilities: [], personality: [], traces: []}};
  const ui = harness({state, fetchOverride(url) {
    if (url === "/api/state") return Promise.resolve(response(state));
    if (url === "/api/person/999") return personARequest.promise;
    if (url === "/api/person/1000") return Promise.resolve(response(personB));
    throw new Error(`Unexpected request: ${url}`);
  }});
  await new Promise(setImmediate);
  ui.clickPerson(999);
  ui.clickPerson(1000);
  await new Promise(setImmediate);
  assert.match(ui.elements.get("person-detail").innerHTML, /人物乙/);
  personARequest.resolve(response({id: 999, name: "迟到的人物甲", alive: true, parents: [], relationship_details: [], impact_reasons: [], titan_relations: [], journey: [], attribute_guide: {note: "A", abilities: [], personality: [], traces: []}}));
  await new Promise(setImmediate);
  assert.match(ui.elements.get("person-detail").innerHTML, /人物乙/);
  assert.doesNotMatch(ui.elements.get("person-detail").innerHTML, /迟到的人物甲/);
  assert.equal(ui.personCards.find((card) => card.dataset.personId === "1000").classList.contains("selected"), true);
  assert.equal(ui.personCards.find((card) => card.dataset.personId === "999").classList.contains("selected"), false);
});

test("failed world request restores controls while active, and a resulting ending keeps advance disabled", async () => {
  const active = baseState({chapter: {title: "进行中", summary: "继续"}, metrics: {}, highlights: [], timeline: [], spotlight: [], recap: null, ending: null});
  const ended = {...baseState({chapter: {title: "余烬", summary: "世界终结"}, metrics: {}, highlights: [], timeline: [], spotlight: [], recap: null, ending: {title: "终局", summary: "终结"}}), ended: true, ending_summary: "世界终结"};
  const failedRequest = deferred();
  let stepCount = 0;
  const ui = harness({state: active, fetchOverride(url) {
    if (url === "/api/state") return Promise.resolve(response(active));
    if (url === "/api/step") {
      stepCount += 1;
      return stepCount === 1 ? failedRequest.promise : Promise.resolve(response(ended));
    }
    throw new Error(`Unexpected request: ${url}`);
  }});
  await new Promise(setImmediate);
  ui.elements.get("step").listeners.click();
  assert.equal(ui.elements.get("step").disabled, true);
  assert.equal(ui.elements.get("advance").disabled, true);
  failedRequest.reject(new Error("network unavailable"));
  await new Promise(setImmediate);
  assert.match(ui.elements.get("subtitle").textContent, /操作失败：network unavailable/);
  assert.equal(ui.elements.get("step").disabled, false);
  assert.equal(ui.elements.get("advance").disabled, false);
  assert.equal(ui.elements.get("advance-century").disabled, false);
  assert.equal(ui.elements.get("reset").disabled, false);
  ui.elements.get("step").listeners.click();
  await new Promise(setImmediate);
  assert.equal(ui.elements.get("step").disabled, true);
  assert.equal(ui.elements.get("advance").disabled, true);
  assert.equal(ui.elements.get("advance-century").disabled, true);
  assert.equal(ui.elements.get("reset").disabled, false);
});

test("stale initial state cannot overwrite the state returned by reset", async () => {
  const oldState = baseState({chapter: {title: "旧世界", summary: "旧记录"}, metrics: {}, highlights: [], timeline: [], spotlight: [], recap: null, ending: null});
  const resetState = baseState({chapter: {title: "新世界", summary: "重置后"}, metrics: {}, highlights: [], timeline: [], spotlight: [], recap: null, ending: null});
  const ui = harness({state: resetState, person: {}, pendingInitial: true});
  ui.elements.get("reset").listeners.click();
  await new Promise(setImmediate);
  ui.resolveInitial(oldState);
  await new Promise(setImmediate);
  assert.match(ui.elements.get("chapter").innerHTML, /新世界/);
  assert.doesNotMatch(ui.elements.get("chapter").innerHTML, /旧世界/);
});
