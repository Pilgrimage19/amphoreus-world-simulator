# P-0005：从开发者观察台到逐火年代记

日期：2026-10-19
状态：观察层、人物层已实现并验收；后续机制/数值调整不混入本轮。

## 产品目标

玩家每次推进后能回答：发生了什么、涉及谁、留下什么。默认页面强调重大变化与人物经历，不要求用户拼接五页原始数据。原始数值和全部事实仍可检查。

## 三个阶段

1. 观察层：世界阶段、重大事件时间轴、每次推进回顾和结局回顾。重要事件从完整事件档案筛选，不依赖最后 25 条日志。
2. 人物层：基于真实事件的人物经历、可点击相关人物，能力/人格/人生痕迹分层及用途说明。默认十二因子名单仍不超过十二人。
3. 后续平衡：审计属性饱和、普通冲突等于背叛、共同门槛集中献祭及长寿命等问题，再分别修改与验证。当前不改既定试炼、候选概率和权能参数。

## 本轮实现与角色分工

- 协调者：只读观察数据接口、独立后端测试、代码审查、集成、浏览器验收和 Git 提交。
- Luna（gpt-6-luna）：只修改静态页面 HTML/JS/CSS，以及独立前端测试；不得修改模拟内核、提交 Git、重启主服务或推进/重置用户世界。
- 所有 Python 使用项目专属 Conda 环境。每个可用阶段验收后提交并推送 GitHub。

## 后端契约（只增量扩展）

`GET /api/state` 以及推进/重置响应继续保留现有所有字段，新增 `observation`：

```text
chapter: {title, summary}
metrics: {surviving_regions, ordinary_returned, active_bearers, living_tide}
spotlight: [{person_id, name, domain, status, summary, latest_year}]
highlights: [EventCard]                 # 默认至多五个，重要性优先
timeline: [EventCard]                   # 全档案重大节点，年序排列
recap: null | {from_year, to_year, important_count, events:[EventCard], population_delta}
ending: null | {title, summary, returned_fires, refuge_names, missing_roles, legacy:[string]}
last_event_id: string | null
```

`EventCard` 为 `{id, year, type, title, summary, people:[{id,name}], causal_event_ids:[string]}`。`people` 是事件记录涉及的人物，不能一概称为决策者；因果引用只展示确实指向原始事件的引用，不从性格或相同年份推断因果。重复事实按事件 ID 去重。

`GET /api/person/<id>` 保留已有字段，新增：

网页请求额外携带 `X-Amphoreus-View: compact`，历史人物列表仅投影焦点及逐火关联人物，完整档案仍可按人物 ID 查询。无此请求头的旧客户端保留完整快照；所有投影只读，不消费随机数。

```text
journey: [EventCard]                   # 完整事件中确实涉及此人的重大节点
attribute_guide: {
  abilities:[{key,label,value,usage}],
  personality:[{key,label,value,usage}],
  traces:[{key,label,count,description}],
  note:string
}
```

生命痕迹是当前累计机制，不将普通冲突计数解释为确实背叛某人，不将一年失陷区停留解释为确实失去亲友；胜利后的选择没有生产逻辑，不显示成已完成内容。

## 页面要求

- 首页先显示阶段、仍存续地区与本阶段重点；突出重要事件、人物入口及最近一次推进回顾。结束时有独立回顾，不只是缺项清单。
- 历史页重大时间轴与原始日志分层，列表保持内部滚动。用户可以从重大事件打开相关人物详情。
- 人物详情优先经历、相关人物，再展示属性用途；不为每条无关试炼生成一大串“尚未开始”。支持从关系/事件查看不在十二人名单中的人物，但不扩充默认名单。
- 保留一年/十年/百年推进、并发锁、终局禁用、重置和已有五个页签；不得用浏览器持久缓存把不同世界的故事混在一起。
- 新响应到达后，若用户已切换人物或重置，旧详情不得覆盖新世界；新增文字必须正确转义。
- 若连接仍在运行的旧版服务而暂时没有 `observation`，页面应降级使用已有逐火史并明确历史覆盖范围，不白屏或伪造批次故事。

## 验收标准

1. 百年推进仍能看到本批次发生的重要事件，即使后面已有超过 25 条普通日志。
2. 展示的人物/年份/关系和因果均能追溯原始事件；没有事件证据时不编造动机、救援或牺牲收益。
3. 详情可解释现有能力和人格用途，至少清楚区分能力、人格、人生痕迹。
4. 结局既说明未完成条件，也回顾实际产生的庇护所、献祭与传承；不得称准备终局已生成下一世界。
5. 观察接口不写世界、不调用随机流；相同模拟状态哈希不因读取而改变。
6. 完整测试、独立前端回归和真实浏览器验收通过；保留用户当前世界，部署时先预览和核对。
