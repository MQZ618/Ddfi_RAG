# LLM辅助科研系统 - Claude Code 指南

## 项目结构

```text
LLM辅助科研系统/
├── dify-main/                  # Dify 底座（RAG 平台）
├── llm-model-collaboration/    # LLM 调用专业模型
├── rag-prompt-engineering/     # RAG 与提示词工程
├── 开发守则.md                  # 开发规范
└── README.md                   # 快速开始指南
```

## Docker 一键启动

```bash
cd dify-main/docker
cp .env.example .env
docker compose up -d
# 访问 http://localhost
```

## DSL Workflow 架构

Dify 的 Workflow 通过 YAML DSL 文件定义，整体流程：

```
DSL YAML → 后端解析 → 存入数据库 (Workflow 表) → API 返回 → 前端渲染
```

### 后端（Python）

| 文件 | 职责 |
|------|------|
| `dify-main/api/services/app_dsl_service.py` | DSL 导入/导出核心逻辑 |
| `api/services/workflow_service.py` | Workflow CRUD |
| `api/models/workflow.py` | 数据库模型，存储 graph JSON |
| `api/constants/dsl_version.py` | DSL 版本号 |

关键方法：
- `AppDslService.import_app()` — 解析 YAML，创建/更新 App 和 Workflow
- `AppDslService.export_dsl()` — 从数据库导出 YAML DSL
- `WorkflowService.sync_draft_workflow()` — 将 graph 写入数据库

### 前端（TypeScript/React）

| 文件 | 职责 |
|------|------|
| `web/app/components/workflow-app/index.tsx` | Workflow 编辑器入口 |
| `web/app/components/workflow/` | React Flow 渲染组件 |

渲染流程：API 返回 `graph` → `initialNodes()` / `initialEdges()` → React Flow 可视化

### DSL 文件格式

```yaml
version: 0.3.1
kind: app
app:
  name: My Workflow
  mode: advanced-chat  # 或 workflow
  icon: 🔬
  description: ...

workflow:
  graph:
    nodes:
      - id: start
        type: custom
        data:
          type: start
          title: 开始
      - id: llm
        type: custom
        data:
          type: llm
          model:
            provider: openai
            name: gpt-4
          prompt_template:
            - role: system
              text: "..."
    edges:
      - source: start
        target: llm
```

### DSL 导出/导入脚本

位于 `rag-prompt-engineering/scripts/`：

```bash
# 导出
export DIFY_API_KEY=app-xxxxxxxxxxxx
python scripts/export-workflow.py --app-id <id> --output dsl/my-workflow.yml

# 导入
python scripts/import-workflow.py --input dsl/my-workflow.yml
```

### 现有 DSL 文件

| 文件 | 说明 |
|------|------|
| `rag-prompt-engineering/dsl/research-assistant.yml` | 科研辅助 V0 |
| `rag-prompt-engineering/dsl/base-export.yml` | 基础导出模板 |

## 开发规范摘要

详见 [开发守则.md](开发守则.md)

- **Dify 代码不准改动**，扩展通过 API/插件
- **两条线独立**：LLM+专业模型、RAG+提示词
- **只通过 HTTP 接口通信**，不直接共享代码
- **不提交密钥**，只提交 `.env.example`
