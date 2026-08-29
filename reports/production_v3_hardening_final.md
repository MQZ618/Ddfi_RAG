# 科研助手 Production v3 Hardening 最终验收报告

日期：2026-08-29
验收结论：**Not Production-ready（有条件通过离线层，Live 层未闭环）**

## 1. 版本与范围

- 本地仓库：`/Users/mqzzz/Desktop/LLM辅助科研系统/Ddfi_RAG-github-snapshot`
- 分支：`snapshot/dify-agent-2026-08-29`
- 远端：`origin git@github.com:MQZ618/Ddfi_RAG.git`
- 本轮代码起点：`97da6bec`
- 功能性 checkpoint（本报告提交前）：`91cc7c3a`
- Live App：`http://localhost/agent/ZiPt7tBpABi0NX9n`
- 本地 Prompt：`prompts/科研助手-production-v3.md`
- 本地 Live DSL：`agentDSL/科研助手-production-v3-live.yml`

本轮只修改项目侧 Runtime、Prompt/DSL、测试和报告；没有修改 Dify Core、数据集、训练配置、checkpoint、原始日志或既有结果。

## 2. 已交付改动

| 层 | 交付 | 验证边界 |
|---|---|---|
| Attachment Runtime | metadata-only `SessionFileRegistry`，记录 session/file identity、hash、大小、名称、类型和宿主引用；冲突和同名歧义拒绝。 | 不复制附件正文；跨轮是否可用仍取决于宿主提供 live reference。 |
| Execution Runtime | `ExecutionBudget`、`ExecutionGuard`、`RunUsage`、`StopDecision`；Dispatcher 在 Skill load 前执行门控，并把预算证据写入 Receipt。 | 只对接入本仓库 Dispatcher 的调用有效；没有 Dify 隐藏工具链的运行时证明。 |
| Prompt/Transform | 增加任务类型预算、停止策略、附件生命周期、附件正文不可信、`closed_world` 默认、minimal edit、不得新增/删除/强化命题和正式输出边界。 | 已同步到 DSL；尚无 Live App 绑定证明。 |
| Security | 移除手工 Dify harness 中的硬编码 API token 回退值；改为读取 `DIFY_API_KEY` 环境变量。 | 历史 Git 提交仍保留旧历史内容，未重写历史。 |
| Dify client binding | `DifyClient` 支持把同一 conversation 的已登记文件元数据重新组装为 Dify `files` payload；显式传入 `files=[]` 时不自动重绑。 | 只覆盖项目侧 API client；不能修复当前 Dify Web/Core 丢失 Agent prompt file mappings 的宿主行为。 |
| Runtime audit | 记录项目侧 selected-only Skill loading、Registry/package 大小、历史 raw usage 和 Dify 隐藏上下文分解未知项。 | 不把项目侧证据外推为 Dify 平台证据。 |

对应提交：

- `3a9f8c29` baseline evidence
- `72b15d3b` session and execution policies
- `686eb12d` Prompt/DSL hardening
- `30ec57c2` Dispatcher execution guard
- `462d305c` closed-world claim protection and token removal
- `ecd6acc8` runtime/Web audit reports
- `91cc7c3a` Dify client session-file rebinding and regression tests

## 3. 离线验收

最终新鲜验证结果：

| 命令 | 结果 |
|---|---|
| `./.venv/bin/python scripts/build_skill_registry.py --check` | `OK` |
| `./.venv/bin/python -m pytest -q` | `44 passed in 0.06s` |
| `./.venv/bin/python -m compileall -q .` | exit 0 |
| `python3 scripts/validate_agent_dsl.py agentDSL/科研助手-production-v3-live.yml` | `OK`；9 个未绑定 Dify Skill asset warning |
| `git diff --check` | exit 0 |
| `git status --short` | clean（报告提交后复核） |

当前 Registry hash：`5e1b3bbc5985aebd61d3b4a3d76e80ddbcb233f42acc79d97cef8cc025d3d009`。

## 4. 真实 Web 证据

本轮向 Web App 上传了以下三份材料：

| 文件 | SHA-256 |
|---|---|
| `deep-research-report.md` | `ae02f54ad8a377e8d38e3d4286b85c2b9c9c9c23af81af3b40f95a6af8a8efc8` |
| `deep-research-report (1).md` | `257b6eef4fc4e5efacc36a8671321c69a178e88893fe409c2ff547d4b763d2bf` |
| `deep-research-report (2).md` | `266e9c4931bbdd94072636ae9f305e5a21aa207b0b3b049929d6564b8fa683f7` |

已观察到：

- 三文件均被 Web App 识别，并按文件名完成摘要。
- Agent 能区分附件正文与用户指令，并指出文件一/三在首选任务定义、cross-event segmentation 优先级上的冲突。
- 同一会话下一轮不重新上传时，仍能引用三份附件并准确定位冲突。
- 空白会话的简单压缩两次均在 30 字以内；输出事实关系稳定，措辞有轻微随机变化。
- 英文转换保持了“研究线索—统一任务缺口—单图像局限—跨事件验证”的论证关系，并给出五个术语映射。
- 已有附件会话续读完成了一轮四段 Introduction 写作（E17），以及仅修改第二段的 closed-world 回归（E18）；DOM 核对显示第一、三、四段逐字保留。

页面原始资源字段：

| 用例 | 页面耗时 | 页面 Token | 结论 |
|---|---:|---:|---|
| 三文件首轮读取 | 56.00 s | 514,685 | 内容通过；过程有多次“已运行命令”和“下载到工作区”痕迹。 |
| 同会话冲突定位 | 9.27 s | 65,378 | 附件延续通过。 |
| 长会话简单压缩 | 3.92 s | 65,837 | 结果通过；上下文成本偏高。 |
| 空白会话简单压缩 1 | 4.84 s | 12,593 | 通过。 |
| 空白会话简单压缩 2 | 3.82 s | 12,453 | 通过；行为稳定。 |
| 英文科研转换 | 51.95 s | 147,186 | 语言和事实边界基本通过；过程显式加载 Skill/manifest，存在 Agent 腔和过程超预算风险。 |
| 同会话 Introduction 写作 | 62.07 s | 73,247 | 结构和证据边界通过；属于已有附件会话续读。 |
| 同会话第二段定点修改 | 15.46 s | 75,358 | 目标段落修改通过；其余三段逐字保留；属于已有附件会话续读。 |

## 5. 关键未闭环项

### P0：本地 Hardening 尚未证明已部署到 Live App

Web 页面没有提供可验证的 Prompt/DSL 绑定版本。页面思考过程仍出现 capability check、Skill 加载、manifest 和核心片段读取。因此不能宣称 `462d305c`、`ecd6acc8` 或项目侧 `91cc7c3a` 已上线，也不能宣称页面 Token 已降低。

### P1：长会话上下文污染

空白会话短任务约 12.5k tokens；同一长会话中约 65.8k tokens。该差异来自页面字段，不能拆解成 System Prompt、Skill、历史、附件或隐藏 reasoning 的单独成本，但已足以作为上下文预算风险记录。

### P1：附件续读只在同一会话得到证明

同会话续读通过；此前新会话观察到 `files=[]` 并要求重新上传。SessionFileRegistry 只提供项目侧元数据契约，不能单独修复 Dify 宿主生命周期。

### P1：全新上传序列的三轮附件写作尚未完成

原计划要求“上传一次后连续执行：概括研究问题 → 基于上述附件写 Introduction → 只修改 Introduction 第二段”。本轮在已有附件会话中完成了 E17/E18，并核对了定点修改范围；但重新上传阶段的浏览器文件选择器自动化连续超时并重置会话，因此不能把这两条证据记为全新上传序列已通过。

### P2：正式输出仍有过程漂移

英文转换的正式结果额外加入 `Revision notes`，虽然没有改变主要事实，但超出“正文 + 五个术语映射”的最小格式；Live UI 也展示了部分内部过程。正式生产版本仍需验证过程层与最终答案层是否隔离。

## 6. Dify 源码定位

完整 Dify 源码已找到：

`/Users/mqzzz/Desktop/LLM辅助科研系统/dify-1.16.1-source`

该目录是 Git 仓库，版本/标签为 `1.16.1`，包含 API、Web 和 Agent 相关源码。项目目录内的 `dify-main` 只是 Docker/配置快照。已读取 Dify Agent 文件映射实现，但本轮没有修改 Dify Core。

当前 Live 部署实际使用 `/Users/mqzzz/Desktop/LLM辅助科研系统/Ddfi_RAG/dify-main/docker` 下的 Compose 配置：API/Web 使用官方 `langgenius/dify-api:1.16.1`、`langgenius/dify-web:1.16.1` 镜像且未挂载完整源码；Agent backend 使用本地 override 镜像。故源码定位不等于当前 Web 已加载该源码。

## 7. 最终判定

- 离线层：**通过**。Registry、Dispatcher、Receipt、Session Registry、Execution Guard、Prompt/DSL 和安全回归均有代码或测试证据。
- Web 内容层：**部分通过**。多文件读取、冲突识别、同会话引用、中文短任务和英文转换均得到真实页面证据。
- Web 运行时层：**未通过验收**。Live 绑定、lazy loading、页面 Token/工具预算和完整三轮附件写作尚未闭环。
- 生产标签：**Not Production-ready**，不是代码失败，而是 Live 宿主绑定和必需的连续写作回归仍缺少可验证证据。

重新验收门槛：先让 Live App 提供可验证的 Prompt/DSL 绑定信号，并在 Dify Core 或等价宿主层恢复同一会话的 Agent prompt file mappings；再完成三轮附件写作回归，并复测简单任务是否不再加载 Skill/manifest、长会话是否有明确预算和停止证据。项目侧 `DifyClient` 重绑定已具备，但当前 Web App 尚无调用它的证据。
