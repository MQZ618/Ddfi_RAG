# 智慧科研工作台产品化 E2E 记录

日期：2026-08-30

## 范围

本报告记录项目侧 Web 工作台的实现和真实验证结果。Dify Core、官方 Dify 1.16.1 镜像、Prompt、DSL、Skill、Tool 配置和密钥均未修改。

## 自动化结果

```text
web-client npm test
35 tests
35 passed
0 failed
```

覆盖内容包括：

- 请求停止、重试和新建会话；
- 上传失败重试；
- 真实交付物去重和下载；
- 草稿刷新恢复；
- 手机菜单和 Enter 发送；
- Agent 增量消息与累计消息去重；
- Markdown 有序列表、引用块、表格和代码块；
- Dify 健康探测；
- 客户端断开后的上游流取消；
- 原有 API、上传、签名下载和导航契约。

## 真实项目侧验证

### 通过

- 项目侧服务启动成功：`http://127.0.0.1:3000/`；
- 健康探测返回 `difyConfigured=true`、`difyReachable=true`；
- 首页返回 200；
- 1440px 桌面截图无明显布局破坏；
- 390px 手机截图无横向溢出；
- 真实 Dify 纯文本任务完成；
- 页面显示单次 `连接正常。`，没有重复拼接；
- 会话 ID、请求状态和 Trace 在最终态一致；
- 停止和重试在本地真实浏览器中可用；
- 真实工具文件在本地 E2E 中只显示一次并可下载真实字节。
- 真实 Dify 文件生成任务返回 `delivery_check.md`；交付区计数为 1，浏览器实际下载 21 字节，回答中没有暴露 `api:5001`。
- 第二次真实文件生成任务返回 `交付链路正常.md`；交付区计数为 1，浏览器实际下载 21 字节，回答中仍没有暴露内部 Dify 地址。
- 用户未要求文件的纯文本任务没有生成交付物。

### 部分交付 / 未通过

- 三份真实科研报告已进入上传和 Agent 处理流程，但长任务未能完成；
- Dify API 日志出现 PostgreSQL 物理文件缺失：

```text
psycopg2.errors.UndefinedFile:
could not open file "base/16384/16785": No such file or directory
```

详细记录见：[Dify_Postgres_Physical_File_Missing.md](../bug记录/Dify_Postgres_Physical_File_Missing.md)。

因此三份材料比较不能标记为通过。

三份材料的最小确认任务已通过：三份文件均显示为已上传，实际提交后 Agent 返回“三份材料已收到”，右侧状态为“回答已返回”。这证明多文件上传和提交链路正常；长文比较失败属于后续 Agent 运行阶段的数据库错误。

## 已知限制

- 附件跨轮次持续可访问不作保证；
- Dify Agent `reasoning_effort=max` 发布后持久化问题仍是平台限制；
- Dify PostgreSQL 物理文件缺失需要独立数据库运维处理；
- 本轮内置浏览器控制入口不可用，真实页面验证使用本机 Chrome 的测试期控制方式完成；
- 未执行任何 Dify Core 级修改或自定义镜像构建。

## Readiness 判定

```text
项目侧 P0 交互链路：通过
项目侧自动化回归：通过（35/35）
真实纯文本 Web E2E：通过
真实单文件附件 Web E2E：通过
真实三文件上传/最小确认 Web E2E：通过
真实文件生成与下载 Web E2E：通过
真实三份长文 E2E：未通过，受 Dify 数据库运行时阻塞
整体 production-ready：暂不能宣布
```

当前问题不应归因于前端上传按钮或项目侧代理；在 Dify 数据库运行时恢复前，长文科研任务只能判定为部分可用。
