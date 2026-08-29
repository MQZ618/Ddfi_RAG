# Production v3 Hardening Baseline

日期：2026-08-29
项目仓库：/Users/mqzzz/Desktop/LLM辅助科研系统/Ddfi_RAG-github-snapshot
起始 HEAD：97da6bec
分支：snapshot/dify-agent-2026-08-29
远端：origin git@github.com:MQZ618/Ddfi_RAG.git

## 1. 原始基线命令

以下结果来自本轮实际命令输出：

| 检查 | 结果 |
|---|---|
| 工作树 | clean；仅显示当前分支，无未提交文件 |
| Registry drift | OK |
| pytest | 28 passed in 0.05s |
| compileall | exit 0，无输出 |
| git diff --check | exit 0 |

HEAD 前十条历史从新到旧：

- 97da6bec style: clean web evaluation report formatting
- 5aad9cd1 test: record production v3 web e2e evaluation
- 0dee1db4 docs: record live Dify agent v3 verification
- 0be30aff docs: close writing agent v3 verification plan
- ccfaded4 feat: add writing agent routing and dify v3 tooling
- e4cdacd4 feat: add discoverable skill registry manifests
- 9211df21 feat: add verifiable skill runtime MVP
- 574e9882 chore: snapshot current Dify agent state
- 9e017086 fix: make agent chat file downloads use internal URLs
- 2ce0704b docs: add PDF upload root cause analysis and project assets

## 2. 现有能力边界

仓库当前已包含：

- Manifest discovery、deterministic Registry hash 和 drift check；
- Capability/Phase routing；
- Skill Dispatcher、Invocation Receipt、Artifact persistence 和 lineage；
- Agent DSL 构建/结构校验；
- Production v3 Prompt 与上一轮 Web E2E 评测报告；
- 三份历史 Web 测试材料的摘要与原始 JSON 运行记录。

当前仓库不包含完整 Dify API、Agent Backend、Web 或 session_snapshot 实现。dify-main 目录在本快照中只有 Docker/部署配置和少量测试文件。因此不能在本仓库内直接证明或修改 Dify 的 Conversation file binding、session persistence race 或隐藏 token 组成。

## 3. 已观察缺陷与归属

| 优先级 | 事实 | 归属层 | 本轮可执行边界 |
|---|---|---|---|
| P0 | 上一轮首轮上传文件可读，后续轮次出现 files=[] | Dify/Attachment Runtime | 实现项目侧元数据 Registry；Live 结果仍需实测，平台限制必须保留 |
| P1 | 简洁审计扩张为多轮读取、生成和上传尝试 | Prompt/Execution Budget/Model behavior | 实现确定性预算与停止门控，并压缩 Prompt 契约 |
| P1 | Q3 版本增加输入未明示的应用背景句 | Prompt/Transform policy | 明确 closed-world 与 minimal edit |
| P2 | 短任务显示较高页面 Token，内部来源未分解 | Dify Runtime/Host unknown | 只保留原始页面/JSON 数字，内部组成标为 unknown |
| P2 | UI 可能显示路由或工具过程 | Dify UI presentation | 正式输出隔离规则可在项目 Prompt/DSL 加强；不删除审计记录 |

## 4. 不可推断的内容

- 不能仅凭页面 Token 数字分解 System Prompt、Skill definition、tool output、history 和附件各自贡献。
- 不能仅凭本地 DSL 或 ZIP 文件声称 Skill 已绑定到 Dify；当前 DSL 中仍有 is_missing 资产。
- 不能仅凭项目侧 SessionFileRegistry 声称 Dify Web 的后续请求会自动携带同一附件引用。
- 不能把历史 Web 评测的页面耗时、Token 或质量分数当作本轮修复后的结果。

## 5. 下一步验收顺序

1. 先对项目侧 SessionFileRegistry 和 ExecutionBudget 写失败测试。
2. 以最小实现通过 focused tests，再跑现有 28 项回归。
3. 压缩式修改 Production v3 Prompt，并使用既有 DSL 构建/验证流程。
4. 重新运行离线 Registry、pytest、compileall、diff check。
5. 使用真实 Dify Web 做 bounded E01、A1/A2/A3 和核心质量回归。
6. 根据真实结果给出 Beta、Usable with minor limitations、Production-ready 或 Not ready。

本报告只记录基线和边界，没有修改数据集、原始日志、checkpoint 或结果文件。

