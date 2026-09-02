# P2：New Agent 回答结束后错误弹出 Suggested Questions disabled

## 状态

- 状态：confirmed / deferred
- 发现时间：2026-09-02
- 影响范围：Dify 1.16.1 Self-hosted New Agent 的 Web UI
- 目标 Agent：科研助手 Production v3
- 主回答是否受影响：否

## 现象

每次 Agent 正常完成回答后，Web UI 弹出：

```text
The 'Suggested Questions After Answer' feature is disabled. Please refresh your page.
```

刷新后问题仍会重复出现。

## 运行时证据

Nginx 日志记录了回答完成后对推荐问题接口的 403 请求：

```text
GET /api/messages/b4feb171-814c-40da-be79-7fc568325433/suggested-questions 403
GET /api/messages/edc94f41-9dbc-451d-bee4-79e681c53d28/suggested-questions 403
GET /api/messages/67b98297-5202-4a39-a0ca-9eb0f916c936/suggested-questions 403
GET /api/messages/544f0ff5-0627-4476-9535-6e42bfb2faef/suggested-questions 403
```

数据库中的配置存在不一致：

```text
Agent active snapshot version 12:
app_features.suggested_questions_after_answer.enabled = true

Backing app app_model_configs:
suggested_questions_after_answer = null
```

## 根因

当前 Dify 1.16.1 源码的两条配置链路不一致：

```text
Agent Web 参数接口
  → 读取已发布 Agent snapshot
  → enabled = true
  → 前端发起 suggested-questions 请求

推荐问题后端接口
  → 读取 legacy backing app AppModelConfig
  → 配置为空
  → 返回 app_suggested_questions_after_answer_disabled / HTTP 403
  → 全局请求层弹出错误 toast
```

相关源码位置（本机 Dify 1.16.1 源码快照，不属于当前项目提交内容）：

- `web/app/components/base/chat/chat/hooks.ts:451-465`：回答完成且配置为 enabled 时发起请求；
- `api/services/message_service.py:304-325`：非 Advanced Chat 路径从 legacy AppModelConfig 读取开关；
- `api/controllers/web/error.py:76-79`：定义截图中的错误文案。

## 影响边界

- 普通回答、知识库检索和主对话链路仍可完成；
- 回答后的推荐问题不可用；
- 每次回答结束都会产生一次失败的附加请求和错误提示；
- 不属于全站不可用，也没有发现主回答数据丢失。

## 当前处理与修复方向

短期处理：在 Agent 配置中关闭“回答后推荐问题”，保存并重新发布，然后刷新页面。

前端静默请求只能隐藏提示，不能修复推荐问题功能。完整修复需要让 `AppMode.AGENT` 的后端推荐问题接口读取已发布 Agent snapshot，并增加配置一致性回归测试。

## 证据边界

本记录不把静态源码定位当作线上代码已修改的证据，也不包含 API Key、Secret Key、签名 URL 或完整用户回答。
