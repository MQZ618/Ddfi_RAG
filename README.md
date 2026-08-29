# LLM辅助科研系统

基于 Dify 的 RAG（检索增强生成）科研辅助平台。

## 当前快照分支

本分支 `snapshot/dify-agent-2026-08-29` 用于保存 2026-08-29 的科研助手项目状态，基于远程 `main` 创建。它记录了当前工作区中的 Skill 包、Dify 配置导出、研究工作产物，以及本地 Dify Docker 配置修复。

### Dify Agent 当前状态

当前 Agent：`科研助手`（Agent ID：`01a03d42-d538-7604-9fde-741e04f0af2c`）

- 当前页面状态：已发布
- 模型：`deepseek-v4-flash`
- 已挂载 Skill：`academic-writing-review`、`evidence-audit`、`paper-comparison`、`paper-deep-read`、`research-retrieval`、`nature-polishing`、`nature-writing`、`nature-response`、`nature-shared`
- 已配置工具：GitHub、网页抓取、MinerU、JSON 处理、Markdown 转换器、时间、Dify 文本提取器、代码解释器、Audio
- 知识检索：`Retrieval 1`
- Agent 文件区：暂无文件

当前导出的 Dify DSL 保存在 [agentDSL/科研助手-current-2026-08-29.yml](agentDSL/科研助手-current-2026-08-29.yml)。原来的 [agentDSL/科研助手.yml](agentDSL/科研助手.yml) 保留，便于比较，不应误认为是最新配置。

### 本次保存的改动

1. 新增 `skills/`：保存已打包的科研写作、论文分析、证据审查、引用核验和路由 Skill。
2. 新增当前 Dify 配置 DSL 快照，避免旧 DSL 覆盖当前 Agent 配置。
3. 同步 `dify-main/docker/` 中当前的本地修复：
   - 示例配置中不再默认使用容器内部 `INTERNAL_FILES_URL`；
   - Agent Backend PDF 下载镜像补充工作区临时目录规则，避免依赖受限的 `/tmp`；
   - 文件映射和容器内文件 URL 测试改为当前 Agent Backend 容器检查方式。
4. 保留 `outputs/researchwrite/` 中的论文工作产物和 `drone_agent_min.py`。
5. 更新本 README，说明快照来源、配置状态和排除范围。

### 有意排除的内容

以下内容没有提交到 GitHub：

- `dify-main/docker/.env`：可能包含本地密钥和环境配置；
- `dify-main/docker/volumes/`：运行时数据库、上传文件、模型和其他服务数据；
- 缓存、`.DS_Store`、Python 字节码和临时验证目录；
- 嵌套的 `ponytail` 独立 Git 仓库。

因此，本分支保存的是**可复现的项目配置和工作产物快照**，不是 Dify 运行时数据库或完整 Docker 数据备份。

### 恢复提示

如需恢复 Agent 配置，应优先使用当前 DSL 快照导入 Dify，并在导入前确认目标 Agent。导入 DSL 可能覆盖现有配置；Skill ZIP 仍需在目标 Dify 实例中实际上传或挂载。

## 项目结构

```text
LLM辅助科研系统/
├── dify-main/                  # Dify 底座（RAG 平台）
├── llm-model-collaboration/    # LLM 调用专业模型
├── rag-prompt-engineering/     # RAG 与提示词工程
└── 开发守则.md                  # 开发规范
```

## 快速开始

### 环境要求

- Docker >= 20.10
- Docker Compose >= 2.0
- 至少 4GB 可用内存

### 一键启动

```bash
# 1. 克隆仓库
git clone git@github.com:MQZ618/Ddfi_RAG.git
cd Ddfi_RAG/dify-main/docker

# 2. 复制环境配置
cp .env.example .env

# 3. 启动所有服务
docker compose up --build -d
```

启动后访问：http://localhost

### 聊天上传 PDF/DOC 读取修复

使用 Dify 1.16.1 Agent Backend 时，按 [dify-main/docker/README.pdf-upload-fix.md](dify-main/docker/README.pdf-upload-fix.md) 启用附件下载修复。

### 默认配置

| 配置项 | 默认值 |
|--------|--------|
| 数据库 | PostgreSQL 15 |
| 缓存 | Redis 6 |
| 向量库 | Weaviate |
| Web 端口 | 80 |
| 数据库密码 | difyai123456 |

### 首次访问

1. 打开 http://localhost
2. 注册管理员账号
3. 开始使用 Dify 平台

## 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f api

# 停止所有服务
docker compose down

# 停止并删除数据
docker compose down -v

# 重启服务
docker compose restart
```

## 开发指南

详见 [开发守则.md](开发守则.md)

两条开发线独立完成：

1. **LLM＋专业模型线** — 负责专业任务识别、参数提取、模型调用
2. **RAG＋提示词线** — 负责文档解析、检索、基于证据回答

两条线只通过稳定 HTTP 接口通信，不直接共享代码。

## 注意事项

- 不要修改 `dify-main/` 内的代码，需要扩展时通过 API 或插件
- 不要提交真实密钥到 Git，只提交 `.env.example`
- 每个工程必须能独立运行和测试

## License

See [LICENSE](LICENSE) for details.
