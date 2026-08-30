# P0：Dify Agent 思考强度发布后无法持久化

## 1. 问题概述

当前 Dify 1.16.1 的原生 Agent **科研助手 Production v3** 在配置页选择模型思考强度后，发布并退出配置页，再次进入时选择值会恢复为 `high`。

典型表现：

```text
配置页选择：max
点击发布：成功
退出后重新进入：high
```

这导致 UI 显示的模型配置与用户最后发布的配置不一致。当前问题记录为 P0 配置一致性问题。

## 2. 影响范围

- Agent：`科研助手 Production v3`
- Agent ID：`01a04e0b-1c05-7baf-a41a-cffac221515b`
- 模型：`deepseek-v4-pro`
- 受影响参数：
  - `thinking`
  - `reasoning_effort`
- 当前可见选项：`low`、`high`、`max`
- 当前默认值：`high`

问题不影响普通文本请求、文件上传或服务启动，但会影响推理强度这一模型运行参数是否按照用户选择生效。

## 3. 复现步骤

1. 打开 Dify Agent 配置页：

   ```text
   /agents/01a04e0b-1c05-7baf-a41a-cffac221515b/configure
   ```

2. 进入模型设置，选择 `deepseek-v4-pro`。
3. 开启思考模式。
4. 将思考强度改为 `max`。
5. 点击发布/构建并确认发布成功。
6. 退出当前配置页，再次进入同一个 Agent 的配置页。
7. 观察思考强度恢复为 `high`。

## 4. 运行时证据

### 4.1 DeepSeek 插件支持该参数

已安装的 DeepSeek 插件模型定义为 `deepseek-v4-pro` 提供：

```text
thinking: boolean
reasoning_effort: low | high | max
default: high
```

插件运行逻辑也会读取 `reasoning_effort`，因此 `max` 并非插件层未知参数。

### 4.2 已发布 Agent 快照没有保存该参数

当前数据库中 `科研助手 Production v3` 的 active snapshot 的 `model_settings` 仅包含：

```text
temperature
top_p
max_tokens
stop
presence_penalty
frequency_penalty
response_format
```

其中没有：

```text
thinking
reasoning_effort
```

### 4.3 Dify Agent 配置模型会丢弃未知字段

Dify Agent 配置模型 `AgentSoulModelSettings` 当前定义为：

```python
class AgentSoulModelSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
```

该模型没有声明 `thinking` 和 `reasoning_effort` 字段，并且会忽略未声明字段。因此配置请求即使从前端携带了 `reasoning_effort: "max"`，在保存/重新加载 Agent Soul 时也会被丢弃。

## 5. 根因判断

问题发生在 Dify Agent 配置持久化边界，而不是 DeepSeek API 是否支持 `max`：

```text
Dify UI 选择 max
        ↓
Agent 配置保存
        ↓
AgentSoulModelSettings 未声明该字段
        ↓
extra="ignore" 丢弃 reasoning_effort
        ↓
发布快照不包含该字段
        ↓
重新进入页面显示默认 high
```

因此当前看到的 `high` 不是“max 被模型自动改成 high”，而是 `max` 没有被持久化。

## 6. 当前状态

- 状态：`confirmed / deferred`
- 复现：已确认
- DeepSeek 插件：支持 `low / high / max`
- 当前服务：可正常运行
- 文件上传和普通对话：已验证可用
- 当前 Agent 的思考强度选择：不能可靠持久化
- 未执行强制 `high` 插件补丁；该补丁不能解决自由切换问题

## 7. 在当前约束下的处理

当前项目约束为：

- 不修改 Dify Core；
- 不重建自定义 Dify API/backend 镜像；
- 官方 Dify 1.16.1 镜像保持不变。

在这些约束下，无法让原生 Dify Agent 同时满足：

1. 用户可在 `high` 与 `max` 之间自由切换；
2. 发布后重新进入仍保留选择；
3. 运行时把选择值传递给 DeepSeek 插件。

当前安全 workaround 是使用插件默认的 `high`，但这不等价于实现了自由切换。

## 8. 完整修复所需工作

若解除“不修改 Dify Core / 不重建 backend”约束，建议：

1. 在 `AgentSoulModelSettings` 中增加：

   ```python
   thinking: bool | None = None
   reasoning_effort: Literal["low", "high", "max"] | None = None
   ```

2. 确认 Agent draft、publish、active snapshot 的 round-trip 都保留这两个字段。
3. 确认 Agent runtime request builder 将两个字段传给 plugin daemon。
4. 增加 `high → max → reload` 和 `max → high → reload` 回归测试。
5. 构建并部署包含该修复的 Dify API 镜像。
6. 通过 Dify UI 和真实 DeepSeek 请求验证实际生效值。

## 9. 安全边界

- 不在本记录中写入 API Key、Secret Key 或完整 Prompt。
- 不直接修改 active snapshot 绕过配置模型校验。
- 不通过强制插件默认值冒充实现了 UI 自由切换。
- 本问题与附件跨轮次生命周期限制无关。
