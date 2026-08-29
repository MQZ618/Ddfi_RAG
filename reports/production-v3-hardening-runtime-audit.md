# Production v3 Hardening Runtime Audit

日期：2026-08-29
代码起点：97da6bec
当前 Runtime checkpoint：91cc7c3a
当前 Prompt/DSL checkpoint：462d305c

## 1. Project Runtime selected-loading trace

静态代码证据：

- skill_runtime/core.py:322-334 的 SkillRegistry.select_all 过滤启用且匹配 capability/mode 的 Skill，并按 skill_id 排序。
- skill_runtime/core.py:336-338 的 SkillRegistry.select 返回 select_all 的第一个稳定匹配。
- skill_runtime/core.py:487-506 的 ProceduralSkillAdapter 只读取传入 Skill 的 definition_path，并校验该定义包哈希。
- skill_runtime/core.py:571 的 SkillDispatcher 使用 self.registry.select(capability, mode)，随后只把该 Skill 传给 adapter.execute。
- tests/skill_runtime/test_skill_runtime.py 的 real_router_skill_is_loaded_by_dispatcher 通过真实 writing-agent-router ZIP 验证了选中定义可加载。

结论：项目侧 Dispatcher 的实际调用路径是 selected-only；它不会在一次 dispatch 中把其他 Registry 定义交给 ProceduralSkillAdapter。该结论只覆盖本仓库 Runtime，不覆盖 Dify Agent 的隐藏 Skill loading、上下文拼接或模型内部过程。

### 1.1 Project-side Dify client session-file rebinding

- `tests/dify_workflow/dify_client.py` 支持注入 metadata-only file registry，并在 `conversation_id` 已知且调用方未显式提供 `files` 时，将该会话已登记文件转换为 Dify `files` payload。
- 显式传入 `files=[]` 保持为空，不触发隐式重绑定。
- `tests/skill_runtime/test_dify_client.py` 覆盖了上述续读与显式空列表边界。

该修复只改变项目侧 API client 的请求组装，不等于当前 Dify Web App 已调用该 client，也不修改 Dify Core 的 Agent prompt file mapping 持久化行为。

## 2. Registry and package size evidence

以下为本轮命令直接读取的文件字节数，不是 Token 数：

| 文件/集合 | 原始值 |
|---|---:|
| prompts/科研助手-production-v3.md | 8,098 bytes |
| agentDSL/科研助手-production-v3-live.yml | 43,120 bytes |
| skill-registry/skill-registry.json | 3,164 bytes |
| Registry registered Skill count | 3 |
| Registered ZIP total | 7,433 bytes |
| All skills/*.zip total | 532,712 bytes |

当前 Registry hash：5e1b3bbc5985aebd61d3b4a3d76e80ddbcb233f42acc79d97cef8cc025d3d009。
Registered IDs：academic-writing-review、evidence-audit、writing-agent-router。

注意：DSL validator 本轮仍报告 9 个 Dify Skill asset requires upload warning；这些资产的 is_missing/file_id 状态不是已绑定证据。

## 3. Existing raw usage evidence

来源一：reports/research-writing-agent-v3-web-e2e-evaluation.md。以下是上一轮真实 Dify Web 页面显示值，本轮没有把它们当作修复后结果：

| 用例 | 页面耗时 | 页面 Token |
|---|---:|---:|
| E03 | 36.25 s | 252,328 |
| E04 | 79.35 s | 214,293 |
| E05 | 31.02 s | 34,219 |
| E06 | 25.34 s | 74,328 |
| E08 | 8.31 s | 39,605 |
| E10-1 | 14.50 s | 41,731 |
| E10-2 | 3.30 s | 42,100 |
| E10-3 | 4.49 s | 42,321 |

来源二：reports/runs/all_results.json。该原始 JSON 中有 usage 的 case 如下：

| case | prompt_tokens | completion_tokens | total_tokens | latency |
|---|---:|---:|---:|---:|
| case_01 | 2,825 | 400 | 3,225 | 17.865 s |
| case_02 | 1,269 | 108 | 1,377 | 4.654 s |
| case_03 | 2,464 | 471 | 2,935 | 23.837 s |
| case_04 | 2,509 | 478 | 2,987 | 22.322 s |
| case_05 | 5,568 | 1,243 | 6,811 | 44.339 s |
| case_06 | 4,174 | 625 | 4,799 | 40.118 s |
| case_07 | 8,230 | 2,023 | 10,253 | 66.341 s |
| case_08 | 4,018 | 1,196 | 5,214 | 45.529 s |
| case_09 | 2,475 | 496 | 2,971 | 21.802 s |
| case_10 | 8,174 | 1,812 | 9,986 | 57.828 s |
| case_16 | 1,272 | 112 | 1,384 | 4.915 s |

case_11 至 case_15 的 usage 字段在该 JSON 中未记录。

## 4. Cost attribution boundary

已证实：

- Production Prompt 当前文件大小为 8,098 bytes；其 system prompt 在 Live DSL 生成结果中为 4,006 个字符。
- 历史 Web 页面短任务和写作任务存在较高页面 Token/耗时。
- 历史 E01 包含多轮文件读取、扫描、生成和上传尝试。
- 项目侧当前增加了确定性 ExecutionBudget，但它只有被宿主或适配层实际接入时才会限制 Dify 工具调用。

仍 unknown：

- Dify 页面 Token 中 System Prompt、Skill definitions、Registry、Tool outputs、Conversation history、附件正文和隐藏 reasoning 的精确分解。
- Dify Agent 是否每轮加载所有完整 Skill definition。
- Dify UI 是否把 reasoning/tool trace 作为独立展示层而非最终答案。
- 本地 ExecutionBudget 是否已被当前 Live Agent 运行时调用；本仓库没有该连接器或 API 证据。

因此本报告不宣称已完成 Dify lazy loading 或页面 Token 降低，只记录项目侧可验证的 selected-only 和预算契约。

## 5. Secrets protection

- `tests/dify_workflow/test_workflow.py` 原先包含一个真实 Dify API token 作为回退值；本轮已移除，脚本现在只从 `DIFY_API_KEY` 环境变量读取，缺省为空值。
- `CLAUDE.md`、`rag-prompt-engineering/README.md` 和导入/导出脚本中的 `app-xxxxxxxxxxxx` 均为占位符，没有作为凭据使用。
- 新增静态回归测试，禁止手工 Dify harness 再出现长格式 `app-...` token；测试通过。

## 6. Offline verification at audit time

本轮审计前后实际通过：

- ./.venv/bin/python scripts/build_skill_registry.py --check：OK
- ./.venv/bin/python -m pytest -q：44 passed
- ./.venv/bin/python -m compileall -q .：exit 0
- git diff --check：exit 0

原始数据、训练配置、数据集、checkpoint、日志和已有结果未修改。

## 7. 本轮继续执行的项目侧收口

基于上一节审计结论，本轮只做了不依赖 Dify Core 的最小修改：

- `ExecutionBudget` 新增 `file_upload` 动作，并要求文件、搜索和上传授权参数为严格布尔值；未明确授权时上传仍被拒绝。
- `ExecutionGuard` 持久化最近一次 `StopDecision`；Dispatcher 在预算阻断和正常完成路径都把停止证据写入 Receipt。
- Manifest 的 mutation 标志要求为布尔值；review 模式拒绝变更型 Skill，非 review 模式必须显式传入 `mutation_authorized=True`。
- Artifact 持久化失败时 Receipt 落为 `failed`，不遗留 `running` 状态。
- Prompt/Live DSL 将 Capability 路由明确为 selected-only：每个 capability 默认最多选择一个稳定排序的 Skill，除非用户明确要求多方案比较；并禁止用内部任务分解、工具状态等过程说明代替正式结果。

当前新鲜离线结果：`.venv/bin/python -m pytest -q` 为 `57 passed in 0.09s`；Registry check 为 `OK`；DSL validator 为 `OK`，仍有 9 个未绑定 Skill asset warning。上述修改只证明项目侧契约，不证明当前 Live App 已绑定该 Prompt/DSL 或接入该 Dispatcher。
