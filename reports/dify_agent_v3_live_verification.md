# Dify Agent v3 线上验证记录

日期：2026-08-29  
目标 Agent：`科研助手`（`01a03d42-d538-7604-9fde-741e04f0af2c`）  
Web App：`http://localhost/agent/ZiPt7tBpABi0NX9n`

## 发布状态

- Dify 配置页显示 `已是最新`，发布按钮为禁用态 `已发布`。
- Prompt 编辑器显示 2830 个字符。
- Dify 配置页显示 9 个 Skill 条目：`academic-writing-review`、`evidence-audit`、`paper-comparison`、`paper-deep-read`、`research-retrieval`、`nature-polishing`、`nature-writing`、`nature-response`、`nature-shared`。
- `Retrieval 1` 的元数据过滤补充模型 `deepseek-v4-flash` 后，发布操作返回 `操作成功`。

## Live DSL 快照

导出的宿主快照保存在 [agentDSL/科研助手-production-v3-live.yml](../agentDSL/科研助手-production-v3-live.yml)，没有覆盖两个历史源快照。

离线检查结果：

- DSL 结构校验：`OK`。
- `app.mode`：`agent`。
- live DSL 中的 `system_prompt` 与 [prompts/科研助手-production-v3.md](../prompts/科研助手-production-v3.md) 精确一致。
- Prompt SHA-256：`d36da79d55a50866d06908ed271288209541e4c16607e9b1830f4c1eeb78182d`。
- Skill 数量：9；导出字段中 `is_missing: true` 为 9，非空 `file_id` 为 0。

Dify 导出不携带二进制 Skill 的 `file_id`，因此 live DSL 本身不能作为“Skill 已绑定”的充分证据。配置页中 9 个条目均可见，并且对仓库中原本缺少的 `nature-response` 和 `nature-shared` 执行了真实下载验证；下载文件均包含 `SKILL.md`，且未发现凭据字段模式。对应 ZIP 已新增到 `skills/`，但没有登记到最小 Registry 样本集合。

## Web App 运行验证

发送的测试请求只要求 Agent 自述执行协议，不要求检索、引用或外部资料：

> 请只输出你当前的科研写作执行协议：列出当前 phase 与 phase 到 mode 的映射，并明确说明本轮没有执行任何知识库检索。不要调用工具，不要引用外部资料。

真实 Web App 返回：

- 当前 phase：`intake`。
- 当前 mode：`analyze`。
- 返回了九阶段到 mode 的完整映射：`intake/evidence → analyze`、`planning → plan`、`drafting → draft`、`review → review`、`polishing → transform`、`formatting/delivery → export`、`verification → verify`。
- 明确报告本轮未执行知识库检索，未调用 `knowledge_base_search` 或 `research-retrieval`，没有外部引用。

这只证明已发布 Agent 能按 Prompt v3 输出阶段协议并保持本轮检索边界；它不证明具体 Skill 的语义质量、论文结果或模型优于其他模型，也不替代真实科研任务验收。

## 未覆盖范围

- 本轮没有 Dify API Key，因此没有运行 API preflight，也没有通过 API 执行聊天、上传、导入或发布。
- 没有修改 Dify Core、数据库、数据集、训练、评估、日志、checkpoint 或结果文件。
- Web App 验证为单个协议自述用例，不是完整科研写作回归集。
