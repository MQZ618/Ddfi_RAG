# Production v3 P0 平台限制跟踪

日期：2026-08-29
优先级：**P0（跟踪项）**
状态：**deferred / known limitation**

## 1. 定位

本记录用于在 GitHub 中保留当前 Live 层平台限制的可追溯记录。P0 表示该问题一旦要求生产级连续会话能力，影响范围和验收风险都很高；它不表示本阶段 Goal blocked。

本阶段明确不修复以下平台级项目：

1. cross-turn attachment persistence；
2. Dify Core-level Skill lazy loading；
3. custom Dify backend image；
4. GHCR / multi-arch deployment；
5. 与上述 Core 修改直接绑定的部署工作。

## 2. 已知限制

### 2.1 跨轮附件访问

当下一轮运行时没有重新提供附件引用时，Agent 不能保证访问上一轮的原始附件。当前验收定义为：

- 首轮附件读取必须正确；
- runtime 不再提供附件时，Agent 必须诚实报告不可访问；
- 不得用此前摘要冒充重新读取原文件；
- 本阶段不要求跨轮持续可访问。

项目侧 `SessionFileRegistry` 和 `DifyClient` 的元数据契约可以记录和重组引用，但不能替代 Dify 宿主的附件生命周期管理。

### 2.2 Dify Runtime 固定开销

官方 Dify 1.16.1 Runtime 仍可能向上下文提供固定配置、manifest、CLI help 和可用 Skill 元数据。项目侧可以继续降低 task classification、capability routing、Skill invocation、Tool invocation 和 Prompt 侧的可控开销，但不能把官方 Runtime 的固定开销误记为项目代码已解决。

因此，项目侧验收记录必须区分：

- Agent/application quality：路由、预算、停止策略、输出边界、Skill/Tool 调用、写作质量和安全回归；
- Dify platform limitations：宿主附件生命周期、Core 级 lazy loading、Runtime 固定上下文开销和依赖 Core 的部署形态。

## 3. 当前部署边界

- 官方 API/Web 镜像保持 `langgenius/dify-api:1.16.1`、`langgenius/dify-web:1.16.1`；
- 不修改 Dify Core；
- 不重建或发布自定义 Dify backend 镜像；
- 不修改 `main`；
- 本阶段不实施任何必须依赖上述 Core 修改的 Skill lazy-loading 方案。

完整 Dify 源码位于本机独立目录：

`/Users/mqzzz/Desktop/LLM辅助科研系统/dify-1.16.1-source`

该目录不属于当前 `Ddfi_RAG` 项目提交内容。当前仓库中的项目侧修复、Prompt/DSL、测试和报告仍可独立提交与复现，但不能宣称它们已经改变官方 Dify Runtime 行为。

## 4. 后续解除条件

只有在后续明确授权修改 Dify Core 或采用等价、可复现的宿主层方案后，才重新评估本记录。解除条件至少包括：

- 连续会话附件引用有宿主层证据；
- Skill lazy loading 的上下文与调用开销有运行时证据；
- 自定义镜像或固定镜像来源、版本、digest 和构建流程可复现；
- 部署文档、配置、迁移和回滚路径完整。

在此之前，本记录保持 deferred / known limitation，不阻塞项目侧 hardening 和质量验收。
