# P0：Dify PostgreSQL 物理文件缺失导致长文 Agent 运行失败

## 状态

- 状态：confirmed / deferred platform-runtime blocker
- 发现时间：2026-08-30
- 影响范围：真实 Dify 长文任务、Agent thought 持久化、三份材料比较
- 项目侧是否可修复：否；需要运行数据恢复或 Dify/数据库运维修复

## 复现

1. 启动当前项目侧 Web 工作台和 Dify 官方服务。
2. 在 Web 工作台上传三份科研报告。
3. 提交三份材料比较任务。
4. 等待 Agent 处理。

## 观察到的证据

项目侧健康探测仍返回：

```text
{"ok":true,"difyConfigured":true,"difyReachable":true}
```

Dify API 日志出现：

```text
psycopg2.errors.UndefinedFile:
could not open file "base/16384/16785": No such file or directory
```

失败发生在 Dify API 写入 `message_agent_thoughts` 时：

```text
UPDATE message_agent_thoughts SET thought=... WHERE message_agent_thoughts.id=...
```

只读 PostgreSQL 系统目录进一步确认：

```text
message_agent_thoughts|16780|toast=16785|pg_toast_16780|16785
```

数据库目录中 `base/16384/16785` 不存在，但 `16785_fsm` 和 `16785_vm` 存在；因此缺失的是 `message_agent_thoughts` 对应 Toast 关系的数据文件，而不是前端上传路径或 API 路由。

因此“API 可达”不能等价于“长文 Agent 可完成”。

## 影响

- 简单纯文本任务可以完成；
- 三份长文任务已进入 Dify Agent，但本轮无法证明正常完成；
- 不能把三份材料比较标记为 E2E 通过；
- 不能通过项目侧前端绕过数据库物理文件缺失；
- 继续重复提交只会制造额外运行记录，不能视为修复。

## 当前处理

- 已停止本轮长任务；
- 未修改 PostgreSQL 数据、Docker volume、Dify Core 或镜像；
- 未尝试删除、重建或覆盖数据库文件；
- 项目侧已提供真实失败/重试路径；
- 后续验收将把简单任务、附件链路、错误态与长文任务分开记录。

## 解除条件

需要在独立运维窗口完成数据库物理文件恢复或一致性修复，并重新执行三份材料 E2E。该动作不属于当前项目侧前端 Goal，不能由前端代码替代。
