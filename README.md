# 翁法罗斯世界模拟器（暂定名）

一个以“泰坦权柄、文明演化、逐火与轮回”为核心的开源同人世界模拟项目。

当前处于设计与技术验证阶段。项目首先验证：**少量确定性规则能否生成可追溯、可复现，并具有情感重量的跨轮回历史。**

> 本项目为非官方、非商业同人项目。不会收录或提取原作贴图、模型、音乐、语音、代码等资产。翁法罗斯内容将与通用模拟内核分离，以便将来替换为原创内容包。

## 文档入口

- [项目愿景与边界](docs/00-vision.md)
- [初步游戏设计文档](docs/01-game-design.md)
- [开发顺序与里程碑](docs/02-roadmap.md)
- [技术架构](docs/03-architecture.md)
- [Python 原型实现说明](docs/05-python-prototype.md)
- [开发环境约定](docs/06-development-environment.md)
- [当前假设、风险与待决问题](docs/04-open-questions.md)
- [设定考据库](docs/lore/README.md)
- [首轮纸面原型：双城与三权柄](docs/prototypes/P-0001-two-cities-three-authorities.md)
- [设计决策记录](docs/decisions/README.md)
- [设计变更日志](docs/CHANGELOG.md)

## 当前原型（2026-10-03）

七个初始地区、十二泰坦的年度模拟已经接入全部火种的专属试炼、权能与终局条件。居民总人口、独立人物样本、组织、迁徙、黑潮和城邦失陷共同生成历史；相同种子可复现相同结果。

网页是观察面板：可以推进年度、查看十二因子行者、逐火史、泰坦权能与再创世尚未满足的条件；世界结束后停止推进。

十枚常规火种先归还，稀有的岁月持有者见证其故事并倒数第二归还，稀有的负世者最后接纳十一枚印记。当前终局是“再创世准备完成”；下一代世界生成和跨世界轮回尚未实现。

当前规则优先阅读 [HANDOFF](docs/HANDOFF.md) 和 [P-0004](docs/prototypes/P-0004-complete-flamechase-and-story-links.md)，本轮考据与原创机制的区分见 [L-0003](docs/lore/L-0003-flamechase-canon-adaptation.md)。

只能使用项目专属 Conda 环境：

```powershell
$env:PYTHONPATH = 'src'
conda run --no-capture-output -n amphoreus-world-simulator python -m unittest discover -s tests -v
conda run --no-capture-output -n amphoreus-world-simulator python -m amphoreus_sim.web --seed 42
```

网页地址：`http://127.0.0.1:8000`。

长程审计：

```powershell
conda run --no-capture-output -n amphoreus-world-simulator python -m amphoreus_sim.audit --seeds 42 7 2026 --ticks 2000 --population 1000 --summary --output simulation-output/audit.json
```
