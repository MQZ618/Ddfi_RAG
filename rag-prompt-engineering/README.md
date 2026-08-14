# 科研辅助 Workflow V0

在 Dify v1.16.1 上建立的可验证科研辅助 Workflow。

## 项目目标

验证以下最小闭环：

1. 将用户自然语言请求解析为单一结构化任务
2. 将任务路由到知识库检索、翻译、一般问答或澄清分支
3. 知识库分支在无检索结果时停止，不生成确定性科研结论
4. 所有有效分支均产生明确的用户输出

## 目录结构

```
rag-prompt-engineering/
├── dsl/                          # DSL 文件
│   ├── base-export.yml          # 只读真值模板
│   └── research-assistant.yml   # 修改后的副本
├── prompts/                      # Prompt 文件
│   ├── task-parser.md           # Task Parser Prompt
│   ├── rag-answer.md            # RAG Answer Prompt
│   ├── translation.md           # Translation Prompt
│   ├── general-qa.md            # General QA Prompt
│   └── clarification.md         # Clarification Prompt
├── scripts/                      # 工具脚本
│   ├── validate-workflow.py     # DSL Validator
│   ├── export-workflow.py       # 导出脚本
│   ├── import-workflow.py       # 导入脚本
│   └── diff-dsl.py              # DSL 比较脚本
├── tests/                        # 测试文件
│   └── test-workflow.py         # 测试案例
├── logs/                         # 日志文件
│   └── workflow-v0-log.md       # 开发日志
└── README.md                     # 本文档
```

## 快速开始

### 1. 验证 DSL 文件

```bash
python scripts/validate-workflow.py dsl/research-assistant.yml
```

### 2. 运行测试

```bash
python tests/test-workflow.py
```

### 3. 比较 DSL 差异

```bash
python scripts/diff-dsl.py dsl/base-export.yml dsl/research-assistant.yml
```

### 4. 导出 Workflow（需要 Dify 实例）

```bash
export DIFY_API_URL=http://localhost:80/v1
export DIFY_API_KEY=app-xxxxxxxxxxxx
python scripts/export-workflow.py --app-id xxx-xxx-xxx --output dsl/base-export.yml
```

### 5. 导入 Workflow（需要 Dify 实例）

```bash
export DIFY_API_URL=http://localhost:80/v1
export DIFY_API_KEY=app-xxxxxxxxxxxx
python scripts/import-workflow.py --dsl-file dsl/research-assistant.yml
```

## 流程设计

```
Start
  ↓
Task Parser LLM
  ↓
If/Else Router
  ├─ knowledge_search
  │    ↓
  │  Knowledge Retrieval
  │    ↓
  │  Evidence Gate
  │    ↓
  │  If/Else
  │    ├─ PASS → RAG Answer LLM → Answer
  │    └─ FAIL → Answer（证据不足）
  ├─ translation → Translation LLM → Answer
  ├─ general_qa → General QA LLM → Answer
  └─ clarification → Answer（请求补充信息）
```

## 当前状态

### 第二阶段完成项（真实 DSL 校准）

- [x] 从真实 Dify 实例获取 App 信息
- [x] 导出真实 DSL (`dsl/real-base-export.yml`)
- [x] 分析真实节点结构和配置
- [x] 校准 `research-assistant.yml` 使用真实 schema
- [x] 注入真实模型配置 (mimo-v2.5-pro)
- [x] 注入真实 dataset_ids
- [x] 注入真实 rerank 配置
- [x] Validator 通过

### 验证结果

```
✅ DSL 本地结构验证通过（0 错误，0 警告）
✅ DSL 本地规则测试 8/8 通过
```

**注意**：上述测试仅为 DSL 本地结构与规则测试，不等于 Workflow 功能验证。
真正验证需要：
- 导入到真实 Dify 实例
- 实际运行
- 调用真实模型
- 调用真实知识库
- 验证真实分支

### 后续工作

- [ ] 在 Dify UI 中测试导入
- [ ] 手动运行测试案例验证功能
- [ ] 根据测试结果调整 Prompt

## 参考资料

- Dify 官方文档: https://docs.dify.ai/
- Dify v1.16.1 源码: ../dify-main
- 开发守则: ../开发守则.md
