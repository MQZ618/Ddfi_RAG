# 科研写作 Agent Skills

本目录保存“科研写作 Agent”可上传的 skill 压缩包。每个 zip 包含一个 skill 目录及其 `SKILL.md`；需要支持的 references、static、templates 和 scripts 也随相应 skill 保留。

## 已有包

以下 5 个包是原有内容，本次未修改：

- `academic-writing-review.zip`
- `evidence-audit.zip`
- `paper-comparison.zip`
- `paper-deep-read.zip`
- `research-retrieval.zip`

## 本次新增包

### 总控路由

- `writing-agent-router.zip`

负责需求拆解、阶段性重新路由、命中 skill 全部调用、调用状态记录和最终验收。

### 科研写作与审查

- `research-writing-skill.zip`
- `researchwrite.zip`
- `scientific-writing.zip`
- `manuscript-optimizer.zip`
- `results-section-revision.zip`
- `nature-writing.zip`
- `nature-polishing.zip`
- `remove-ai-flavor.zip`
- `raw-data-first.zip`
- `citation-verifier.zip`
- `submission-audit.zip`

### Dify 宿主导出资产

- `nature-response.zip`
- `nature-shared.zip`

这两个包由本地 Dify Agent 配置页真实下载并保存，用于补齐当前宿主配置中的 Skill 资产；它们暂不登记到最小 Registry 样本集合。

## 使用边界

- 本次不修改原有 5 个 zip。
- 本次不修改 `agentDSL/科研助手.yml`。其中的 Dify `file_id`、hash 和上传状态应在实际上传 skill 后由 Dify 重新生成或更新。
- `documents:documents` 没有放入本包。它依赖 Codex 容器中的文档运行时、渲染器和工作区依赖；当前 Dify 配置不能仅凭上传一个 `SKILL.md` 就可靠完成 Word 生成和页面级验收。
- `research-writing-skill`、`scientific-writing`、`nature-writing`、`nature-polishing` 和 `researchwrite` 包含各自的辅助 references 或 templates；Agent 应按当前任务按需读取，不应一次性把全部内容塞进上下文。
- `citation-verifier` 和 `submission-audit` 包含辅助脚本，但脚本是否能在宿主平台执行，仍取决于该平台是否提供相应运行时。

## Agent v3 宿主层

`writing-agent-router.zip` 的 phase 顺序和本地 `skill_runtime/routing.py` 的显式路由契约保持一致。生产 Prompt 位于仓库根目录的 `prompts/科研助手-production-v3.md`；它要求 Agent 在每个阶段边界重新发现当前资源，并把真实执行状态与计划、失败、不可用状态区分开。

Dify Agent DSL 由 `scripts/build_agent_dsl.py` 从当前快照生成到新路径，`scripts/validate_agent_dsl.py` 负责离线结构检查。Dify 导出的 `is_missing: true` Skill 资产必须结合 Dify 配置页或真实下载/运行证据判断；仓库中的 ZIP、快照 hash 或空 `file_id` 都不能单独替代宿主绑定证据。`scripts/dify_agent_preflight.py` 只做 `/v1/info` 和 `/v1/parameters` 的只读检查，不执行聊天、上传、导入或发布。

## Registry Runtime

每个已登记 Skill 使用自己的 `skills/<skill-id>/manifest.json` 保存元数据；ZIP 内的 `SKILL.md` 仍是 Skill 定义正文。当前里程碑只登记三个结构清楚、无复杂外部依赖的样本：

- `academic-writing-review/manifest.json`
- `evidence-audit/manifest.json`
- `writing-agent-router/manifest.json`

其余 ZIP 暂不写入 Manifest，也不会进入本轮 Registry。从项目根目录执行以下命令构建或检查生成的 Registry：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/build_skill_registry.py
.venv/bin/python scripts/build_skill_registry.py --check
.venv/bin/python -m pytest -q tests/skill_runtime
```

构建命令会发现并校验 Manifest；`--check` 用于检查 Manifest 与生成物之间的 Drift。`skill-registry/skill-registry.json` 是生成物，不应手工编辑。Dispatcher 只按已登记且启用的 `capability + mode` 选择 Skill，运行时生成 Receipt 和输出 Artifact。当前 `procedural_skill` 适配器只加载真实 ZIP 定义并产生可审计证据；要执行具体 LLM 语义工作，需要由 Dify 或其他宿主提供真实适配器。

新增 Skill 的最小流程是：创建 `skills/<skill-id>/manifest.json`，在 `definition` 中声明可验证的 ZIP 路径和 `SKILL.md` 条目，运行 Registry 构建、`--check` 和离线测试。Manifest 中的 `skill_id` 不得包含路径遍历片段，定义必须位于 `skills/` 根目录内。

## 推荐上传顺序

1. 先上传 `writing-agent-router.zip`；
2. 再上传科研写作和证据审查包；
3. 上传后重新导出或保存 Agent 配置，使 Dify 生成新的 skill 文件引用；
4. 用“无实验数据写论文”“结构审查”“英文润色”“生成 Word”四类任务进行验证。
