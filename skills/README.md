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

## 使用边界

- 本次不修改原有 5 个 zip。
- 本次不修改 `agentDSL/科研助手.yml`。其中的 Dify `file_id`、hash 和上传状态应在实际上传 skill 后由 Dify 重新生成或更新。
- `documents:documents` 没有放入本包。它依赖 Codex 容器中的文档运行时、渲染器和工作区依赖；当前 Dify 配置不能仅凭上传一个 `SKILL.md` 就可靠完成 Word 生成和页面级验收。
- `research-writing-skill`、`scientific-writing`、`nature-writing`、`nature-polishing` 和 `researchwrite` 包含各自的辅助 references 或 templates；Agent 应按当前任务按需读取，不应一次性把全部内容塞进上下文。
- `citation-verifier` 和 `submission-audit` 包含辅助脚本，但脚本是否能在宿主平台执行，仍取决于该平台是否提供相应运行时。

## Registry Runtime

`registry-manifests.json` 是本目录 Skill 的元数据源；它不替代 ZIP 内的 `SKILL.md`。从项目根目录执行以下命令构建或检查生成的 Registry：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/build_skill_registry.py
.venv/bin/python scripts/build_skill_registry.py --check
```

Dispatcher 只按已登记且启用的 `capability + mode` 选择 Skill，运行时生成 Receipt 和输出 Artifact。当前 `procedural_skill` 适配器只加载真实 ZIP 定义并产生可审计证据；要执行具体 LLM 语义工作，需要由 Dify 或其他宿主提供真实适配器。

## 推荐上传顺序

1. 先上传 `writing-agent-router.zip`；
2. 再上传科研写作和证据审查包；
3. 上传后重新导出或保存 Agent 配置，使 Dify 生成新的 skill 文件引用；
4. 用“无实验数据写论文”“结构审查”“英文润色”“生成 Word”四类任务进行验证。
