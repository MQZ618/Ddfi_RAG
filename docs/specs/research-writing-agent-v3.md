# 科研写作 Agent v3 实施契约

## 目标与边界

本契约把科研写作 Agent 的“能力选择”和“阶段选择”从自然语言约定变成可验证的本地运行时接口，并为 Dify Agent 生成一份独立的生产 Prompt 与可导入 DSL。

本里程碑只修改项目仓库中的运行时、Prompt、验证器和生成脚本。`agentDSL/科研助手.yml` 与 `agentDSL/科研助手-current-2026-08-29.yml` 是历史快照，保持不变；不修改 Dify Core，不直接写 Dify 数据库，不自动导入或发布，不触碰数据集、训练、评估、日志、checkpoint 或结果文件。

## Phase 契约

Phase 采用现有 `writing-agent-router` Skill 已声明的顺序和名称：

```text
intake -> evidence -> planning -> drafting -> review -> polishing -> formatting -> verification -> delivery
```

每个 Phase 映射到 Registry Runtime 的一个执行 mode：

| Phase | mode |
|---|---|
| `intake` | `analyze` |
| `evidence` | `analyze` |
| `planning` | `plan` |
| `drafting` | `draft` |
| `review` | `review` |
| `polishing` | `transform` |
| `formatting` | `export` |
| `verification` | `verify` |
| `delivery` | `export` |

Phase Router 只接受上述显式 Phase，不根据用户文字猜测 Phase。未识别 Phase 必须以结构化错误拒绝。

## Capability Routing 契约

Capability 必须来自调用方显式提供的 capability ID，并由已加载的 `SkillRegistry` 解析。Router 不维护第二份 Skill 名单、不按关键词匹配、不把“名称存在”当作执行结果。

```python
CapabilityRouter.route(
    capabilities: Sequence[str],
    mode: str,
) -> tuple[CapabilityRoute, ...]

PhaseRouter.route(
    phase: str,
    capabilities: Sequence[str],
) -> PhaseRoute
```

规则：

1. capability 为空、重复项或非字符串项均拒绝；重复项不能静默改变请求语义。
2. 每个 capability 必须由 Registry 中启用且支持该 mode 的 Skill 命中。
3. 一个 capability 命中多个 Skill 时全部返回，Skill ID 按字典序稳定排列；不能退化为只取第一个。
4. 调用方的 capability 顺序保留在 route 顺序中，便于 Receipt 和审计追踪。
5. `PhaseRouter` 使用上表映射 mode，再调用 Capability Router；显式 Phase 与 mode 不允许脱钩。

返回对象的可序列化形态为：

```json
{
  "phase": "review",
  "mode": "review",
  "capabilities": ["review.academic_prose", "review.evidence"],
  "routes": [
    {"capability": "review.academic_prose", "mode": "review", "skill_ids": ["academic-writing-review"]},
    {"capability": "review.evidence", "mode": "review", "skill_ids": ["evidence-audit"]}
  ]
}
```

## Dify 接入契约

Dify 采用 Agent DSL（当前快照 `kind: app`、`app.mode: agent`），不是 `rag-prompt-engineering` 中的 Workflow V0。生成器读取当前 Agent DSL 快照，只替换 `agent_packages.<package>.soul.prompt.system_prompt`，其余配置原样保留，并且拒绝覆盖输入文件。

生成的 DSL 必须通过以下离线检查：YAML 可解析、Agent package 引用存在、Agent 模式正确、System Prompt 非空、Skill/knowledge/tools 结构可识别、没有 API key 字面量。由于 Dify 导出的 Skill 资产可能是 `is_missing: true`，验证器必须将它列为待上传资产，而不是把本地 ZIP 自动伪装成已绑定。

真实 Dify 运行验证分为两层：

- 只读 preflight：使用 `GET /v1/info` 与 `GET /v1/parameters` 验证目标 App API 凭据和基本配置；
- 写入验证：Skill 上传、DSL 导入、保存或发布必须由用户显式授权并提供有效的 Dify Console/API 凭据，本里程碑不自动执行。

## Prompt v3 约束

Prompt v3 必须：

- 要求 Agent 在每个新 Phase 前重新识别可用 Skill/Tool/Knowledge；
- 把 capability、phase、mode、Skill 状态、输入/输出 Artifact 和证据状态作为内部路由记录；
- 区分 `matched`、`activated`、`executed`、`verified`、`unavailable`、`failed`，不得把计划写成已执行；
- 对检索、文件、引用和实验数字保持证据边界；
- 不在 Prompt 中写死本地 Skill 名称，不生成“伪工具调用”或“伪 Skill 执行”；
- 当宿主未提供某项能力、文件或凭据时明确报告缺口，不绕过宿主限制；
- 正式科研输出中不混入内部路由账本、工具日志或审计字段，除非用户明确要求。
