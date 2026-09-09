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

## 当前第一目标

构建一个无画面、确定性的 `微型轮回`：两座城邦、三位规则型泰坦、少量关键人物、一种末日威胁。给定相同种子与玩家操作，模拟结果必须一致；运行结束后能解释世界为何走向该结局。

当前已有 Python 命令行原型；运行方式见[实现说明](docs/05-python-prototype.md)。
