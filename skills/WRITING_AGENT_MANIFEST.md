# Writing Agent Bundle Manifest

本清单记录本次新增包的来源、用途和打包策略。所有来源文件均为只读复制；源 skill 未被修改。

| 包名 | 来源 | 作用 | 包含辅助资源 |
|---|---|---|---|
| `writing-agent-router.zip` | 本项目新增 | 任务拆解、全量命中调用、阶段重路由、调用账本 | 否 |
| `research-writing-skill.zip` | `/Users/mqzzz/.codex/skills/research-writing-skill` | 科研论文写作与修订 | references |
| `researchwrite.zip` | `/Users/mqzzz/.agents/skills/researchwrite` | 研究写作工作流、提案和修订模式 | references、templates、scripts |
| `scientific-writing.zip` | `/Users/mqzzz/.codex/skills/scientific-writing` | 科学论文段落、IMRAD、引用和报告规范 | references |
| `manuscript-optimizer.zip` | `/Users/mqzzz/.codex/skills/manuscript-optimizer` | 论点、证据链、图表和术语同步审查 | 否 |
| `results-section-revision.zip` | `/Users/mqzzz/.codex/skills/results-section-revision` | Results 章节结构和论证推进 | 否 |
| `nature-writing.zip` | `/Users/mqzzz/.agents/skills/nature-writing` | Nature 风格论文组织 | references、static、templates |
| `nature-polishing.zip` | `/Users/mqzzz/.agents/skills/nature-polishing` | Nature 风格英文润色和结构调整 | references、static |
| `remove-ai-flavor.zip` | `/Users/mqzzz/.codex/skills/remove-ai-flavor` | 去除模板腔、AI 味和元话语 | references |
| `raw-data-first.zip` | `/Users/mqzzz/.agents/skills/raw-data-first` | 防止编造实验数字和结果 | 否 |
| `citation-verifier.zip` | `/Users/mqzzz/.codex/skills/citation-verifier` | 引用、BibTeX、DOI 和占位符检查 | scripts |
| `submission-audit.zip` | `/Users/mqzzz/.codex/skills/submission-audit` | 投稿前的论点、图表、方法和术语审计 | scripts |

## 未纳入项

`documents:documents` 暂未打包，因为它依赖 Codex 专用文档运行时；Superpowers 的编程流程 skills 也没有原样打包，因为它们的触发条件和内容面向软件开发，而不是科研写作。写作 Agent 需要的是本清单中的 `writing-agent-router` 控制层。
