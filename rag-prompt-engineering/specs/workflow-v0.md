# 科研辅助 Workflow V0 设计说明

## 1. 目标

在 Dify v1.16.1 上建立一个可验证的科研辅助 Workflow V0，验证以下最小闭环：

1. 将用户自然语言请求解析为单一结构化任务；
2. 将任务路由到知识库检索、翻译、一般问答或澄清分支；
3. 知识库分支在无检索结果时停止，不生成确定性科研结论；
4. 所有有效分支均产生明确的用户输出；
5. DSL、Prompt、校验脚本和测试案例均保存在外部独立工程中，且可追踪、可验证。

本阶段不实现专业模型、AutoDL、Human Input、异步任务、OCR、Vision、Agent、多 Agent、多任务并发或自动科研规划。

## 2. 目录与修改边界

- Dify 源码目录：`../dify-main`
- 本工程目录：`../rag-prompt-engineering`
- 专业模型独立工程：`../llm-model-collaboration`

所有路径在工程文件和脚本中使用相对路径。不得在 Dify 源码目录中新增项目辅助文件。

允许通过 Dify UI、DSL 导入与导出、官方 CLI 和 Dify 正常配置机制，修改本项目所需的 Workflow、节点、参数和授权；不得绕过 Dify 正常机制直接修改数据库。

修改 Dify 核心源码前，必须单独论证必要性、可替代方案、影响范围和回退方式，并获得用户明确批准。

本轮只修改 `rag-prompt-engineering`。不调用或依赖 `llm-model-collaboration`，两条开发线保持独立。

## 3. DSL 真值来源

DSL 字段按以下顺序确认：

1. 当前 Dify v1.16.1 实例实际导出的 Workflow DSL；
2. Dify v1.16.1 实际源码；
3. Dify 官方文档。

禁止根据其他版本、模型记忆或经验猜测节点 schema。若现有导出 DSL 缺少某类节点，并且查看 5～6 个关键源码文件后仍无法确认，则停止实现该字段，请用户在 Dify UI 创建最小模板节点并重新导出。

`dsl/base-export.yml` 是只读真值模板；后续只修改其副本 `dsl/research-assistant.yml`。

## 4. 总体流程

```text
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

Task Parser 已负责分类，V0 不再叠加 Question Classifier。路由统一使用 If/Else，根据结构化输出中的 `task_type` 判断。

## 5. Task Parser

Task Parser 只负责把用户请求转换为结构化任务，不回答问题、不翻译、不检索、不执行专业计算。

输入优先使用实际 DSL 中的 `sys.query`；如果真实导出 DSL 使用自定义查询变量，则沿用实际变量。禁止把 `sys.conversation_id` 当作任务内容。

输出字段：

```json
{
  "task_type": "knowledge_search",
  "normalized_query": "",
  "needs_knowledge": true,
  "needs_clarification": false,
  "is_compound_request": false,
  "reason": ""
}
```

`task_type` 仅允许：

- `knowledge_search`
- `translation`
- `general_qa`
- `clarification`

复合请求只选择主要任务，同时设置 `is_compound_request=true`，不并发执行。

## 6. 分支设计

### 6.1 knowledge_search

Knowledge Retrieval 的 Query 使用 `normalized_query`。知识库 ID 必须来自真实导出 DSL或用户明确提供的实际 ID；没有真实 ID 时停止该字段修改。

Evidence Gate 只做最小工程判断：

- Retrieval `result` 为空或不存在：FAIL；
- Retrieval `result` 非空：PASS。

PASS 仅表示检索到了上下文，不代表证据已经科学充分。FAIL 固定返回：

> 当前知识库未检索到足以支持回答的相关证据，暂不形成确定性结论。

RAG Answer LLM 只能使用检索上下文，按“已有资料支持、合理推断、尚需验证、来源”组织可支持的内容，不编造论文、作者、参数、实验结果或引用。

### 6.2 translation

只翻译用户明确提供的文本。保持术语、公式、变量、参数、单位、缩写和引用编号；不总结、不评价、不补充背景，不改变原文不确定性。

### 6.3 general_qa

允许使用 LLM 自身知识回答，但不得声称内容来自知识库。遇到需要科研资料出处的问题，应建议使用知识库检索，不编造来源。

### 6.4 clarification

不进入长篇 LLM 回答，直接要求用户补充研究对象、待查询或翻译内容、具体问题。若 `normalized_query` 已指出缺失项，可在简短回复中带出。

## 7. 模型与凭据边界

所有 LLM 节点复用 `base-export.yml` 中已运行的模型配置。Embedding、Rerank、Provider 和模型 ID均不在 DSL 中自行更换或猜测。

任何 API Key 均不得写入 DSL、Prompt、脚本、测试或文档。凭据继续由 Dify 的模型供应商配置管理。

## 8. 错误处理与停止条件

- 无真实 Workflow：不从零手写 DSL；
- 多个 App 且无法确定目标：列出名称、ID 和 mode，请用户选择；
- 无真实知识库 ID：停止知识库字段修改；
- 缺少节点模板且源码无法确认：请用户在 UI 建立最小节点后重新导出；
- validator 失败：禁止导入；
- 证据为空：停止 RAG 回答；
- 本轮结束：只报告验证结果和差异，不自动导入或发布。

## 9. 本地验证

`scripts/validate-workflow.py` 至少验证：

1. YAML 可解析；
2. `workflow.graph`、`nodes` 和 `edges` 存在；
3. 节点 ID 不重复；
4. edge 的 source 和 target 均存在；
5. Start 节点存在；
6. 不存在明显孤立节点；
7. 每条业务分支最终存在 Answer 或 End 出口。

只有在可从真实 DSL 可靠解析 variable selector 时，才检查变量引用；不实现完整 Dify parser。

测试案例覆盖知识库检索、翻译、一般问答、澄清、无证据和复合请求。DSL 校验通过不等于 Workflow 功能已验证；只有导入后真实运行测试通过，才能宣称相应功能已验证。

## 10. 第一轮交付边界

第一轮完成以下产物：

- 真实导出的 `dsl/base-export.yml`；
- 仅在副本上修改的 `dsl/research-assistant.yml`；
- Task Parser、RAG、翻译和一般问答 Prompt；
- DSL validator；
- 手动导入、导出脚本；
- Workflow 测试案例与工程日志；
- validator 结果和 DSL diff 摘要。

第一轮不执行 import，不发布 Workflow，不修改知识库，不实现专业模型分支。
