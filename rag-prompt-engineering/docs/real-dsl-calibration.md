# 真实 DSL 校准报告

## 一、真实 Dify 实例信息

### App 信息
- **App ID**: `1fa6c3ab-59c5-4675-a3e4-7f56f6ca132e`
- **App Name**: 问题分类 + 知识库 + 聊天机器人
- **App Mode**: `advanced-chat`
- **Workflow Version**: `draft`

### DSL 文件
- **真实 DSL**: `dsl/real-base-export.yml`
- **源码推测 DSL**: `dsl/base-export.yml`
- **校准目标**: `dsl/research-assistant.yml`

---

## 二、真实 DSL 关键配置

### 1. Dify DSL Version
```
version: 0.1.5
```

### 2. 模型配置 (LLM)
```yaml
model:
  provider: langgenius/mimo/mimo
  name: mimo-v2.5-pro
  mode: chat
  completion_params:
    temperature: 0.7
    top_p: 1
```

**所有 LLM 节点使用相同模型配置**

### 3. Knowledge Retrieval 配置
```yaml
dataset_ids:
  - 6084ed3f-d100-4df2-a277-b40d639ea7c6
  - 9a3d1ad0-80a1-4924-9ed4-b4b4713a2feb
  - cb0758fe-c7db-4e69-b44d-cc41ed9f2453
retrieval_mode: multiple
multiple_retrieval_config:
  top_k: 4
  reranking_enable: true
  reranking_mode: reranking_model
  reranking_model:
    model: Qwen/Qwen3-Reranker-8B
    provider: langgenius/siliconflow/siliconflow
  score_threshold: null
```

### 4. Start 节点变量
```yaml
query_variable_selector:
  - '1711528708197'
  - sys.query
```

**真实变量引用形式**: `['节点ID', 'sys.query']`

### 5. Variable Selector 形式
- Knowledge Retrieval query: `['1711528708197', 'sys.query']`
- LLM context: `['1711528770201', 'result']`
- Question Classifier: `['sys', 'conversation_id']` (注意：这是当前配置，可能不是最优)

---

## 三、真实节点结构

### 节点列表
| 节点 ID | 类型 | 标题 | 用途 |
|---------|------|------|------|
| 1711528708197 | start | 开始 | 用户输入 |
| 1786697327609 | llm | LLM 2 | Task Parser |
| 1786697138262 | question-classifier | 问题分类器 | 路由 |
| 1711528770201 | knowledge-retrieval | 知识检索 | 知识库检索 |
| 1711528815414 | llm | LLM | RAG Answer |
| 1786696743906 | answer | 直接回复 | 输出结果 |
| 1786697395538 | llm | LLM 3 | 未配置 |
| 1786697408909 | answer | 直接回复 2 | 无法回答 |

### 边列表
| Source | Target | Source Handle | 说明 |
|--------|--------|---------------|------|
| 1711528708197 (start) | 1786697327609 (LLM 2) | source | Start → Task Parser |
| 1786697327609 (LLM 2) | 1786697138262 (question-classifier) | source | Task Parser → Classifier |
| 1786697138262 (question-classifier) | 1711528770201 (knowledge-retrieval) | 1 | Classifier → Knowledge (CLASS 1) |
| 1786697138262 (question-classifier) | 1786697395538 (LLM 3) | 2 | Classifier → LLM 3 (CLASS 2) |
| 1711528770201 (knowledge-retrieval) | 1711528815414 (LLM) | source | Knowledge → RAG Answer |
| 1711528815414 (LLM) | 1786696743906 (answer) | source | RAG Answer → Output |

---

## 四、三个 DSL 差异比较

### 1. 节点类型差异

| 特性 | 源码推测版 | 真实版 | 差异 |
|------|-----------|--------|------|
| 路由节点 | if-else | question-classifier | **重大差异** |
| 节点 type 字段 | 直接类型名 | `custom` | **重大差异** |
| Evidence Gate | code 节点 | 不存在 | 真实版无此节点 |

### 2. 节点结构差异

| 特性 | 源码推测版 | 真实版 |
|------|-----------|--------|
| 节点外层 type | 直接类型 (如 `llm`) | `custom` |
| 节点内层 data.type | 不存在 | 实际类型 (如 `llm`) |
| 节点 ID | 语义化 (如 `task-parser`) | 时间戳 (如 `1786697327609`) |
| 节点尺寸 | 无 | width/height 字段 |
| 位置信息 | 简化 | positionAbsolute + position |

### 3. Edge 结构差异

| 特性 | 源码推测版 | 真实版 |
|------|-----------|--------|
| sourceHandle | `source` / `true` / `false` / `else` | `source` / `1` / `2` |
| data 字段 | 简化 | 包含 sourceType, targetType, isInIteration 等 |
| id 格式 | 语义化 | 自动生成 |

### 4. LLM 节点差异

| 特性 | 源码推测版 | 真实版 |
|------|-----------|--------|
| prompt_template | 包含 id 字段 | 包含 id 字段 |
| context | 使用 variable_selector | 使用 variable_selector |
| memory | 无 | 有 role_prefix 和 window |
| variables | 无 | 有 variables 字段 |

### 5. Knowledge Retrieval 差异

| 特性 | 源码推测版 | 真实版 |
|------|-----------|--------|
| query_variable_selector | 简化 | 完整形式 |
| metadata_filtering_mode | 无 | `automatic` |
| metadata_model_config | 无 | 有配置 |
| single_retrieval_config | 无 | 有配置 |

### 6. Answer 节点差异

| 特性 | 源码推测版 | 真实版 |
|------|-----------|--------|
| answer 字段 | 使用变量引用 | 直接文本 |
| variables | 无 | 有 variables 字段 |

---

## 五、关键发现

### 1. 节点类型命名
- **真实版**: 外层 `type: custom`，内层 `data.type: llm`
- **源码推测版**: 外层 `type: llm`
- **影响**: 需要修正所有节点的 type 字段

### 2. 路由机制
- **真实版**: 使用 `question-classifier` 节点
- **源码推测版**: 使用 `if-else` 节点
- **影响**: 需要完全重写路由逻辑

### 3. Variable Selector
- **真实版**: `['节点ID', '变量名']` 形式
- **源码推测版**: 简化形式
- **影响**: 需要修正所有变量引用

### 4. Edge Source Handle
- **真实版**: 使用数字 `1`, `2` 表示分类
- **源码推测版**: 使用 `true`, `false`, `else`
- **影响**: 需要修正边的 sourceHandle

---

## 六、校准计划

### 需要修正的字段
1. 所有节点的 `type` 字段改为 `custom`
2. 所有节点添加 `data.type` 字段
3. 路由节点从 `if-else` 改为 `question-classifier`
4. 所有变量引用改为真实形式
5. 所有边的 `sourceHandle` 改为真实形式
6. 添加节点尺寸和位置信息
7. 注入真实模型配置
8. 注入真实 dataset_ids
9. 注入真实 rerank 配置

### 不需要修改的字段
1. Prompt 内容（保持 V0 设计）
2. 整体流程结构（保持 V0 设计）

---

## 七、API Key 安全

**已确认**:
- ✅ 未打印任何 API Key
- ✅ 未复制任何 secret
- ✅ 未写入任何 credential 到日志
- ✅ DSL 文件中不包含敏感信息

---

## 八、Dify 源码目录状态

**已确认**:
- ✅ 未修改 Dify 源码
- ✅ 未在 Dify 目录创建文件
- ✅ 未修改 docker-compose
- ✅ 未修改 .env
- ✅ 未修改数据库（仅读取）
