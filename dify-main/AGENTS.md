# CLAUDE.md

本文件为 Claude Code 在此仓库中工作时提供指导。

## 项目概述

Dify 是开源 LLM 应用开发平台，核心能力：可视化工作流、RAG 知识库、Agent 工具调用、模型管理。

## 快速启动

```bash
# Docker 一键部署
cd docker && cp .env.example .env && docker compose up -d
# 访问 http://localhost/install 初始化

# 源码开发环境
./dev/setup                      # 安装依赖 + 复制 env
./dev/start-docker-compose       # 启动 PostgreSQL/Redis/Weaviate
./dev/start-api                  # 启动后端（含数据库迁移）
./dev/start-worker               # 启动 Celery 异步任务
./dev/start-web                  # 启动前端
```

## 常用开发命令

### 后端

```bash
uv run --project api <command>   # 执行任意 Python 命令
make lint                        # 格式化 + 检查
make test                        # 单元测试
make test TARGET_TESTS=./api/tests/unit_tests/core/rag  # 跑指定目录的测试
make type-check                  # 类型检查
```

### 前端

```bash
pnpm install                     # 安装依赖（仓库根目录执行）
pnpm -C web run dev:vinext       # 启动前端开发服务器
pnpm check                       # 代码检查（Oxlint + ESLint + TypeScript）
vp test run                      # 跑前端测试（在 web/ 目录执行）
```

## 关键代码位置（二次开发必读）

### RAG 知识库管道

| 功能 | 路径 |
|------|------|
| PDF 解析 | `api/core/rag/extractor/pdf_extractor.py` |
| 文本分割 | `api/core/rag/splitter/` |
| 向量嵌入 | `api/core/rag/embedding/` |
| 检索逻辑 | `api/core/rag/retrieval/` |
| 重排序 | `api/core/rag/rerank/` |
| 数据集管理 | `api/controllers/console/datasets/` |
| 文档摄入入口 | `api/core/indexing_runner.py` |

**自定义 PDF 解析示例**（如需集成 GROBID 等论文专用解析器）：

```python
# api/core/rag/extractor/paper_extractor.py
from core.rag.extractor.extractor_base import BaseExtractor
from core.rag.models.document import Document

class PaperExtractor(BaseExtractor):
    """论文专用解析器，可调用 GROBID API 提取结构化内容"""

    def __init__(self, file_path: str, grobid_url: str = "http://localhost:8070"):
        self._file_path = file_path
        self._grobid_url = grobid_url

    def extract(self) -> list[Document]:
        # 调用 GROBID 解析论文
        # 返回 Document 列表，每个 Document 包含 page_content 和 metadata
        ...
```

### 自定义工具（接入你的专业模型）

| 功能 | 路径 |
|------|------|
| 自定义工具 Provider | `api/core/tools/custom_tool/provider.py` |
| 工具执行引擎 | `api/core/tools/tool_engine.py` |
| MCP 工具支持 | `api/core/tools/mcp_tool/` |
| 工具实体定义 | `api/core/tools/entities/` |
| 工具管理 API | `api/controllers/console/app/` |

**通过 OpenAPI Schema 注册自定义工具**（推荐方式，无需改代码）：

1. 把你的模型服务封装为 FastAPI 并暴露 OpenAPI 文档
2. Dify 后台 → 工具 → 自定义工具 → 导入 OpenAPI Schema
3. 在工作流中作为工具节点调用

### 工作流引擎

| 功能 | 路径 |
|------|------|
| 工作流入口 | `api/core/workflow/workflow_entry.py` |
| 节点工厂 | `api/core/workflow/node_factory.py` |
| 知识检索节点 | `api/core/workflow/nodes/knowledge_retrieval/` |
| Agent 节点 | `api/core/workflow/nodes/agent/` |
| 人工输入节点 | `api/core/workflow/nodes/human_input/` |
| 数据源节点 | `api/core/workflow/nodes/datasource/` |

### 模型接入

| 功能 | 路径 |
|------|------|
| Provider 管理 | `api/core/provider_manager.py` |
| 模型运行时 | `api/core/model_runtime/`（如存在） |
| 模型管理 | `api/core/model_manager.py` |

**接入 OpenAI 兼容模型**：Dify 后台 → 设置 → 模型供应商 → 添加 OpenAI Compatible，填入 API Base URL 和 Key。

### LLM 生成与 Prompt

| 功能 | 路径 |
|------|------|
| LLM 生成器 | `api/core/llm_generator/` |
| Prompt 模板 | `api/core/prompt/` |
| Agent 策略 | `api/core/agent/strategy/` |

## 项目架构

```
api/
├── controllers/          # API 路由层（解析请求、返回响应）
│   ├── console/          # 控制台 API（用户操作）
│   ├── service_api/      # 对外服务 API（应用调用）
│   └── web/              # Web 页面 API
├── services/             # 业务编排层
├── core/                 # 核心领域逻辑
│   ├── rag/              # RAG 知识库管道
│   ├── workflow/         # 工作流引擎
│   ├── tools/            # 工具系统
│   ├── agent/            # Agent 运行器
│   ├── llm_generator/    # LLM 调用
│   └── prompt/           # Prompt 管理
├── models/               # SQLAlchemy 数据模型
├── libs/                 # 通用工具库
└── configs/              # 配置管理
```

## 环境变量

```bash
# 后端 api/.env（从 api/.env.example 复制）
SECRET_KEY=xxx              # openssl rand -base64 42 生成
DB_USERNAME=postgres
DB_PASSWORD=difyai
REDIS_HOST=redis
VECTOR_STORE=weaviate       # 向量数据库类型

# 前端 web/.env.local（从 web/.env.example 复制）
NEXT_PUBLIC_API_PREFIX=http://localhost:5001/api
```

## 测试

```bash
# 后端单元测试
make test

# 后端指定测试
make test TARGET_TESTS=./api/tests/unit_tests/core/rag

# 前端测试
cd web && vp test run
cd web && vp test run path/to/spec.spec.ts   # 指定文件
```
