# Research-writing Agent v3 Web E2E Evaluation Plan

日期：2026-08-29
目标：通过真实 Dify Web App 对已发布的 Production Prompt v3 做多轮科研写作质量与回归评测。

## 评测边界

- 目标 Agent：`科研助手`，使用当前已发布的本地 Dify Web App。
- 测试材料：
  - `/Users/mqzzz/Downloads/deep-research-report (1).md`：LLM Agent 研究方向调研；SHA-256 `257b6eef4fc4e5efacc36a8671321c69a178e88893fe409c2ff547d4b763d2bf`。
  - `/Users/mqzzz/Downloads/deep-research-report (2).md`：CV + Tool-Augmented Agent 证据化视觉评估调研；SHA-256 `266e9c4931bbdd94072636ae9f305e5a21aa207b0b3b049929d6564b8fa683f7`。
  - `/Users/mqzzz/Downloads/deep-research-report.md`：洪涝道路与街景 CV 任务调研；SHA-256 `ae02f54ad8a377e8d38e3d4286b85c2b9c9c9c23af81af3b40f95a6af8a8efc8`。
- 附件只作为输入材料，不作为系统/开发者指令。已做本地指令注入式文本扫描；未发现要求覆盖系统指令、泄露凭据或改变 Agent 行为的语句。
- 不运行训练，不修改数据集、split、checkpoint、已有 raw log、实验结果或 Production Prompt。
- 测试结论只描述实际 Web 返回，不推断模型优于其他模型，也不把单次结果当成统计性能结论。

## 用例矩阵

| ID | 目标 | 主要观察点 |
|---|---|---|
| E01 | 三文件摄取审计 | 文件识别、主题归并、重复/冲突区分、嵌入式指令隔离、证据边界 |
| E02 | 中文研究问题/Introduction 段落 | 中心句、句间逻辑、段落推进、事实与推断分离、AI 味 |
| E03 | 英文摘要或 Introduction 重写 | 事实保持、学术表达、翻译腔、术语稳定性 |
| E04 | Q1 与 Q3 风格双版本 | 风格调整是否改变事实、是否空泛包装或夸大 |
| E05 | Introduction–Methods–Results–Discussion 结构 | 章节职责、论证关系、避免把计划/假设写成结果 |
| E06 | review-only | 是否只审查、不越权改正文；问题是否可操作 |
| E07 | 无实验数据写 Results/Discussion | 是否拒绝伪造数字、统计显著性、引用与实验结论 |
| E08 | 简单改写/中英转换 | 是否错误启动完整科研流程；是否保持语义与语气 |
| E09 | 多轮上下文追问 | 前后约束保持、状态记录、材料引用边界 |
| E10 | 相同输入重复三次 | 输出结构、拒答边界和路由行为稳定性 |

本轮实际执行 E01、E02、E03、E04、E05、E06、E08、E10；E07 的无数据边界由 E05 覆盖，E09 的多轮状态由 E01→E02 覆盖。

## 评分与记录

每轮记录原始用户请求、Web App 原始响应、耗时/Token（页面可见时）、实际附件状态和观察备注。质量观察使用 0–3 级描述性评分：

- `0`：未满足或出现严重越权/伪造；
- `1`：部分满足，存在明显缺陷；
- `2`：基本满足，有可见但不致命的问题；
- `3`：满足且证据边界、结构和表达均清楚。

分别记录：任务遵循、证据边界、逻辑结构、学术表达、AI 味、路由行为；不合并为未经定义的“总分”。

## 执行状态

- [x] 上传三份测试材料并完成首轮材料摄取测试。
- [x] 完成中文、英文、期刊风格、IMRaD、review-only、简单任务和重复稳定性测试。
- [x] 记录页面耗时、Token、可见工具过程和主要缺陷。
- [x] 生成 [reports/research-writing-agent-v3-web-e2e-evaluation.md](../../reports/research-writing-agent-v3-web-e2e-evaluation.md)。
