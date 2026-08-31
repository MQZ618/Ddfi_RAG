# LLM 辅助科研系统

基于 Dify 的 RAG（检索增强生成）科研辅助平台，配套可验证的 Skill Registry、Skill Runtime、科研写作 Agent 配置，以及项目侧 Web 工作台。

本仓库保存的是**可复现的项目配置、代码、Skill 包和验证记录**，不是 Dify 运行时数据库或完整 Docker 数据备份。Dify 的数据库、向量库、上传文件、密钥和运行时状态不随仓库同步。

## 目录

- [项目定位](#项目定位)
- [当前 Agent 与配置文件](#当前-agent-与配置文件)
- [仓库结构](#仓库结构)
- [快速开始](#快速开始)
- [Dify Agent DSL 导入与验证](#dify-agent-dsl-导入与验证)
- [Skill Registry 与 Skill 包](#skill-registry-与-skill-包)
- [科研写作 Agent](#科研写作-agent)
- [项目侧 Web 工作台](#项目侧-web-工作台)
- [PDF/DOC 附件读取修复](#pdfdoc-附件读取修复)
- [测试与验证](#测试与验证)
- [提交边界与安全要求](#提交边界与安全要求)
- [相关文档](#相关文档)

## 项目定位

本项目由四部分组成：

1. **Dify 底座**：`dify-main/` 保存本地 Dify 部署和必要的附件链路修复。
2. **Agent 配置**：`agentDSL/` 和 `prompts/` 保存 Dify Agent 的 DSL 快照、Prompt 版本和候选配置。
3. **Skill Runtime**：`skills/`、`skill_runtime/` 和 `skill-registry/` 负责 Skill 的发现、登记、路由、执行收据和 Artifact 血缘。
4. **项目侧 Web 工作台**：`web-client/` 提供科研任务入口、材料上传、Dify 流式对话和工具文件下载代理。

两条主要业务线保持独立：

- **LLM + 专业模型线**：负责专业任务识别、参数提取和模型调用；
- **RAG + 提示词线**：负责文档解析、检索和基于证据的回答。

两条线只通过稳定 HTTP 接口通信，不直接共享实现代码。Web 工作台位于项目侧，不修改 Dify Core 或官方 Dify 镜像。

## 当前 Agent 与配置文件

仓库中的 Agent 文件分为“已发布快照”和“候选配置”，用途不同，导入前必须确认文件名：

| 文件 | 状态/用途 |
|---|---|
| `agentDSL/科研助手-current-2026-08-29.yml` | 2026-08-29 的当前配置快照，用于恢复或生成候选 DSL |
| `agentDSL/科研助手-production-v3-live.yml` | Prompt v3 发布后的 Dify 宿主导出快照 |
| `agentDSL/科研助手-production-v4-candidate.yml` | v4 候选配置，不能直接当作线上已发布状态 |
| `agentDSL/科研助手-production-v4-naturalness-candidate.yml` | v4 naturalness 候选配置；如果只存在于本地，说明尚未进入远端版本 |
| `agentDSL/科研助手.yml` | 旧配置，保留用于比较，不默认视为最新配置 |

Dify 导出的 DSL 通常不会携带 Skill 二进制文件的真实 `file_id`。因此，导入 DSL 后仍需在目标 Dify 实例中检查 Skill 是否已上传、是否绑定到目标 Agent，并在配置页确认工具和知识检索状态。

当前工作区记录过的 Agent 信息包括：

- Agent 名称：`科研助手`；
- 2026-08-29 快照中的模型：`deepseek-v4-flash`；
- 已记录的能力：科研写作、论文分析、证据审查、引用核验和相关路由 Skill；
- 线上/宿主状态以 Dify 配置页和实际 API 预检为准，仓库文件不能替代宿主状态。

## 仓库结构

```text
Ddfi_RAG/
├── agentDSL/                         # Dify Agent DSL 快照和候选配置
├── prompts/                          # 生产 Prompt 与候选 Prompt
├── skills/                           # Skill manifest 和可上传 ZIP 包
├── skill-registry/                   # 生成的 Skill Registry
├── skill_runtime/                    # Registry、Router、Dispatcher、Receipt、Artifact 实现
├── scripts/
│   ├── build_agent_dsl.py            # 从基准 DSL 和 Prompt 生成候选 DSL
│   ├── validate_agent_dsl.py         # 离线校验 Agent DSL 结构和凭据字段
│   ├── build_skill_registry.py       # 构建或检查 Skill Registry
│   └── dify_agent_preflight.py       # 只读检查 Dify API 基本状态
├── tests/
│   ├── skill_runtime/                # 离线 Skill Runtime 测试
│   ├── dify_workflow/                # 需要真实 Dify 的在线测试
│   └── writing_eval/                 # 写作评估脚本
├── web-client/                       # 项目侧科研工作台
├── dify-main/                        # 本地 Dify 部署与 Docker 配置
├── reports/                          # E2E、回归和运行验证记录
├── artifacts/                        # 本地评估原始产物，提交前需单独审查
├── PDF/                              # 示例材料和论文材料
├── outputs/                          # 研究写作工作产物
├── pyproject.toml                    # Python 包和测试配置
├── 开发守则.md                        # 项目开发规范
└── README.md
```

## 快速开始

### 环境要求

- Docker 20.10 或更高版本；
- Docker Compose 2.0 或更高版本；
- Python 3.11 或更高版本；
- Node.js 18 或更高版本（Web 工作台）；
- 至少 4 GB 可用内存；
- 如运行在线 Dify 测试，还需要一个可访问的 Dify 实例和 App API Key。

### 1. 克隆仓库

```bash
git clone git@github.com:MQZ618/Ddfi_RAG.git
cd Ddfi_RAG
```

### 2. 启动本地 Dify

```bash
cd dify-main/docker
cp .env.example .env
docker compose up --build -d
```

启动后访问 `http://localhost`。首次使用时先完成管理员账号和模型供应商配置，再导入 Agent DSL 或上传 Skill 包。

### 3. 安装并检查 Python Runtime

回到仓库根目录：

```bash
cd ../..
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/build_skill_registry.py
.venv/bin/python scripts/build_skill_registry.py --check
.venv/bin/python -m pytest -q tests/skill_runtime
```

`build_skill_registry.py --check` 用于发现 Registry 漂移；如果 Skill manifest 或 ZIP 已更新而 Registry 没有重新生成，检查应报告失败。

### 4. 启动项目侧 Web 工作台（可选）

```bash
cd web-client
cp .env.example .env
# 在 .env 中填写 Dify API Key、SECRET_KEY 和可达地址
npm ci
npm test
npm start
```

浏览器访问 `http://127.0.0.1:3000/`。工作台默认只监听本机回环地址；如果通过反向代理对外提供，部署层还必须负责 TLS、鉴权和访问控制。

## Dify Agent DSL 导入与验证

### 从现有快照恢复

建议顺序：

1. 在目标 Dify 实例中先导出现有 Agent DSL，作为回滚副本；
2. 选择 `agentDSL/科研助手-current-2026-08-29.yml` 或明确标注为 live 的 DSL；
3. 导入前确认目标 Agent，避免覆盖错误应用；
4. 导入后检查模型、工具、知识检索、Skill 和文件能力；
5. 用一条最小问题和一条文件读取问题做宿主验证；
6. 只有配置页、API 预检和实际运行结果都符合预期，才把该配置标为已发布。

导入 DSL 可能覆盖现有应用配置；Skill ZIP 和运行时数据库不会因为 DSL 导入自动恢复。

### 生成并校验新的 DSL 候选

以当前快照和 Prompt v3 为例：

```bash
python3 -m pip install -e '.[dev,dify]'
python3 scripts/build_agent_dsl.py \
  --base agentDSL/科研助手-current-2026-08-29.yml \
  --prompt prompts/科研助手-production-v3.md \
  --output /tmp/科研助手-production-v3.yml
python3 scripts/validate_agent_dsl.py /tmp/科研助手-production-v3.yml
```

验证器只做离线结构检查，重点包括：

- 根节点是否为 Dify Agent 应用；
- Agent 包、system prompt、Skill 列表、知识库和工具结构是否存在；
- 缺失 Skill 是否被明确标为待上传；
- 是否混入 API Key、Token、Authorization、密码等凭据字段。

它不会连接 Dify，也不会把本地 ZIP 文件名伪装成目标实例中的 `file_id`。

### Dify API 只读预检

设置环境变量后运行：

```bash
export DIFY_BASE_URL=http://localhost
export DIFY_API_KEY=你的_Dify_App_API_Key
python3 scripts/dify_agent_preflight.py
```

该脚本只访问 Dify 的基本信息和参数接口，不执行上传、导入、保存、发布或删除操作。API Key 不要写入仓库、README、日志或 DSL。

## Skill Registry 与 Skill 包

Skill 的来源和运行时登记分为三层：

1. `skills/<skill-id>/manifest.json`：Skill 元数据源；
2. `skills/<skill-id>.zip`：可上传到 Dify 或其他宿主的定义包；
3. `skill-registry/skill-registry.json`：由脚本生成的登记结果和文件哈希。

常用命令：

```bash
# 构建 Registry
python3 scripts/build_skill_registry.py

# 检查 Registry 是否与 manifest/ZIP 漂移
python3 scripts/build_skill_registry.py --check

# 运行离线 Runtime 测试
python3 -m pytest -q tests/skill_runtime
```

Registry 生成物不应手工编辑。新增 Skill 时，先添加 manifest，再让 `definition.path` 指向已有 ZIP，运行构建、漂移检查和测试。当前 Runtime 测试证明的是登记、路由、输入校验、授权门禁、收据和 Artifact 血缘，不把读取 `SKILL.md` 冒充成大模型语义执行。

## 科研写作 Agent

科研写作 Agent 的生产 Prompt、候选 Prompt 和契约分别位于：

- [Prompt v3](prompts/科研助手-production-v3.md)
- `prompts/科研助手-production-v4.md`（本地候选，提交前确认）
- [研究写作 Agent v3 规范](docs/specs/research-writing-agent-v3.md)
- `docs/specs/research-writing-naturalness-v4.md`（本地候选，提交前确认）
- `DIFY_WRITING_EVALUATION.md`（本地评估说明，提交前确认）

v4 相关文件如果尚未进入远端分支，只能视为本地候选，不应在 README 或发布说明中称为线上版本。候选 Prompt 的修改、DSL 生成、Dify 导入、保存和发布应分开记录，避免把本地文件状态和宿主发布状态混为一谈。

## 项目侧 Web 工作台

详细说明见 [web-client/README.md](web-client/README.md)。工作台提供：

- 研究任务入口和文字草稿恢复；
- 单文件材料上传并转发到 Dify；
- Dify streaming 对话显示；
- 工具生成文件的同源下载代理；
- 失败重试、停止生成和附件状态管理；
- 长 Markdown 的标题、列表、表格、引用块和代码块渲染。

主要接口：

| 接口 | 作用 |
|---|---|
| `GET /api/health` | 返回代理是否具备 API Key 和文件签名密钥，不返回密钥 |
| `POST /api/chat` | 以 streaming 模式转发 Dify 对话请求 |
| `POST /api/files/upload` | 上传单个研究材料到 Dify，限制请求体为 50 MiB |
| `GET /api/artifacts/:id.:ext` | 校验文件 ID 和扩展名后代理工具文件 |

关键配置在 `web-client/.env.example`：

| 变量 | 作用 |
|---|---|
| `PORT` | 工作台端口，默认 `3000` |
| `DIFY_API_BASE_URL` | Dify API 的外部可达根地址 |
| `DIFY_FILE_BASE_URL` | Dify 文件下载的外部可达根地址 |
| `DIFY_API_KEY` | 服务端使用的 App API Key |
| `DIFY_SECRET_KEY` | 文件签名密钥 |
| `DIFY_USER_ID` | 上传和会话使用的稳定用户标识 |
| `DIFY_APP_ID` | 部署记录字段，不参与鉴权 |

`api:5001` 这类 Docker 内部地址不能直接填给浏览器；地址必须从运行 Node 服务的环境可达。API Key、SECRET_KEY、签名 URL 和上传内容不写入前端脚本或普通日志。

## PDF/DOC 附件读取修复

Dify 1.16.1 的 Agent Backend 在本地 Sandbox 场景下可能生成缺少协议和主机名的文件下载地址，导致 PDF、DOC/DOCX 无法进入解析链路。仓库提供了对应说明和 Docker override：

- [附件读取修复说明](dify-main/docker/README.pdf-upload-fix.md)
- [Docker override](dify-main/docker/docker-compose.override.yaml)
- [附件下载测试](dify-main/docker/tests/test_agent_backend_internal_file_urls.py)

修复验证应至少覆盖一个 PDF 和一个 DOC/DOCX，并确认 Agent 能获得文件正文。修复前先备份 `.env` 和当前 Docker 配置；`.env` 本身不提交到 Git。

## 测试与验证

### 默认离线测试

```bash
python3 -m pytest -q tests/skill_runtime
```

### Web 工作台测试

```bash
cd web-client
npm test
```

测试包含 Node 契约测试和可用时的本机 Chrome 浏览器回归；不会为测试自动下载浏览器。

### Dify 在线测试

`tests/dify_workflow/` 需要真实 Dify、App API Key 和额外依赖，不属于默认 pytest 收集范围。运行前先阅读目录内的客户端和环境变量要求，使用独立测试用户和测试材料，不要将在线返回内容、Token 或 `.env` 直接提交。

### 验证记录

`reports/` 保存可审计的测试与运行记录，包括：

- Dify Agent v3 宿主验证；
- Skill Runtime 与 Registry 检查；
- Web 工作台 E2E 和窄屏验证；
- Dify 输出契约回归；
- 文件读取、数据库提示和平台限制记录。

报告中的指标和结论只适用于记录所对应的运行配置、时间和版本，不应扩展成未验证的线上结论。

## 提交边界与安全要求

### 不提交

- `dify-main/docker/.env` 或任何包含真实密钥的文件；
- `dify-main/docker/volumes/` 中的数据库、向量库、上传文件和运行时数据；
- `.DS_Store`、`__pycache__/`、`.pytest_cache/`、本地虚拟环境和构建缓存；
- 未审查的原始 API 返回、SSE、用户材料和大体积 `artifacts/`；
- 嵌套的独立 Git 仓库，例如本地 `ponytail` 仓库。

### 可以提交但要审查

- Dify DSL 快照和候选配置：确认不含凭据，并标明 live/candidate；
- Skill ZIP：确认 ZIP 内只有预期定义和文档；
- `reports/`：确认内容不含 API Key、个人材料和未脱敏响应；
- `artifacts/`：确认是否需要长期保存、体积是否合理、是否包含敏感输入或输出；
- 生成的 Registry：必须通过 `build_skill_registry.py --check`。

### 发布前检查

```bash
git status --short
git diff --check
python3 scripts/build_skill_registry.py --check
python3 -m pytest -q tests/skill_runtime
cd web-client && npm test
```

不要使用 `git add .` 代替文件审查。应按目录和用途分批查看，再决定哪些文件进入同一个提交。Dify 导入、Skill 上传、保存、发布和远端推送都需要明确的目标与回滚点。

## 相关文档

- [开发守则](开发守则.md)
- [Skill 包说明](skills/README.md)
- [Dify Agent v3 线上验证](reports/dify_agent_v3_live_verification.md)
- `reports/dify-output-contract-regression.md`（本地工作区报告，提交前确认）
- [研究工作台 E2E](reports/research_workbench_product_e2e.md)
- [Dify 1.16.1 附件修复](dify-main/docker/README.pdf-upload-fix.md)
- [Web 工作台说明](web-client/README.md)

## 许可证与第三方边界

`dify-main/` 中包含上游 Dify 源码，其许可证以 [Dify 官方仓库的 LICENSE](https://github.com/langgenius/dify/blob/main/LICENSE) 为准。仓库根目录当前没有单独的项目级 `LICENSE` 文件；新增的项目代码、配置和文档应遵循各自文件中的版权与许可证说明。
