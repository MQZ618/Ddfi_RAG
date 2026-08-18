# Dify 1.16.1 New Agent 多轮对话上下文暂时丢失问题记录

## 1. 问题概述

当前项目基于 **Dify 1.16.1 Self-hosted New Agent**。

在同一个 Conversation 中，New Agent 通常能够正常使用前文上下文，但在某些长耗时、多工具调用的 Run 之后，如果用户很快发起下一轮请求，下一轮可能加载到过期的 `session_snapshot`，从而暂时缺失最近一轮对话历史。

该问题表现为：

> 同一 Conversation 中，Agent 在某一轮突然无法理解“这个论文”“它”“上面的方法”等本应能够从上一轮解析的指代；稍后再次提问时又恢复正常。

该问题不是永久性历史丢失，而是一次明显的时序 / 并发窗口问题。

---

## 2. 典型复现案例

前序对话持续围绕 VMamba / SS2D 展开。

20:22 轮：

- 用户继续追问 SS2D 的参数共享、Cross-Merge、S6 内部维度等问题；
- Agent 进行了长时间、多工具、多来源检索；
- 该轮耗时约 265 秒；
- `prompt_tokens` 约为 2,324,877；
- 运行结束后包含大量 Tool Call 相关事件。

紧接着 20:27 轮：

用户询问：

```text
用给外行都能听懂的语言，讲解这个论文到底干了啥，解决了什么问题
```

按当前 Conversation 历史，“这个论文”应自然指向 VMamba。

但 Agent 回答：

```text
目前我这边还没有看到“这篇论文”的具体信息——当前对话里没有出现论文标题、链接或文件……
```

说明该轮没有正确利用最近一轮及相关历史上下文。

随后 20:29 再次明确询问 VMamba 时，Agent 恢复正常。

---

## 3. 运行时证据

### 3.1 Session 时序

已确认的关键时序如下：

```text
12:17:49
Session 01a00f9e-8f6 保存
Run: 00d106ca
历史消息数量：44
Snapshot 长度约：195 KB

12:22:23
20:22 轮开始
Run: cc72e71e
用户继续询问 SS2D 细节

12:26:48
20:22 轮消息持久化完成
latency ≈ 265 s
prompt_tokens ≈ 2,324,877

此时：
新的 session_snapshot 尚未完成保存

12:27:57
20:27 轮开始
Run: aab3198d

该轮加载的仍然是：
Session 01a00f9e-8f6
历史消息数量：44

该 snapshot 不包含刚完成的 20:22 轮完整历史

12:28:06
20:27 轮完成
回答出现上下文缺失

12:28:06
20:22 轮对应的新 Session Snapshot 才最终保存
Session: 01a00fa8-195
历史消息数量：110
Snapshot 长度约：323 KB

12:29:05
下一轮开始

此时加载：
Session 01a00fa8-195
历史消息数量：110

上下文恢复正常
```

---

## 4. 核心证据对比

| 项目 | 20:22 轮 | 20:27 轮 | 20:29 轮 |
|---|---|---|---|
| Run ID | cc72e71e | aab3198d | 4366054a |
| 加载 Session | 01a00f9e（44 msgs） | 01a00f9e（44 msgs） | 01a00fa8（110 msgs） |
| Prompt Tokens | 约 2,324,877 | 约 17,529 | 正常 |
| 上下文表现 | 正常 | 异常 | 恢复正常 |
| Session 状态 | 新 snapshot 延迟保存 | 使用旧 snapshot | 使用最新 snapshot |

其中：

- `session_id`
- `snapshot` 消息数量
- `session` 保存时间
- 新一轮启动时间

构成直接证据。

`prompt_tokens` 大幅下降属于强旁证，说明 20:27 轮实际获得的上下文规模明显小于前一轮。

---

## 5. 已确认的机制

Dify 1.16.1 New Agent 的同一 Conversation 历史并不是传统 Agent 的普通 TokenBufferMemory 机制。

New Agent 使用：

```text
Conversation
↓
agent_runtime_sessions
↓
session_snapshot
↓
History Layer
↓
runtime_state.messages
↓
Agent Backend
↓
message_history
↓
LLM
```

每一轮 Run 完成后，新的历史状态需要写入 `session_snapshot`。

下一轮 Run 启动时，通过 `load_active_session()` 加载当前 Conversation 对应的 Session Snapshot。

---

## 6. 问题发生位置

此次问题发生在：

```text
Run N
↓
用户可见回答 / Message 已经持久化
↓
最新 session_snapshot 尚未完成保存

此时 Run N+1 启动
↓
load_active_session()
↓
读取上一版本的旧 snapshot
↓
最近一轮上下文缺失
```

因此该问题并不是：

- New Agent 不支持多轮历史；
- Conversation ID 丢失；
- 用户切换了新会话；
- 模型本身“不具备记忆”；
- Prompt 没有要求使用上下文；
- 所有历史永久丢失。

而是：

> 新一轮 Run 在上一轮最新 `session_snapshot` 尚未保存完成时启动，读取到了过期 Session Snapshot。

---

## 7. 代码层面观察

当前调查显示，`app_runner.py` 中存在类似以下执行顺序：

```text
先发布 / 持久化终端答案
↓
再保存 Agent Session Snapshot
```

即：

```text
_publish_terminal_answer(...)
↓
_save_session(...)
```

在普通短 Run 中，两步之间的时间窗口通常很小，因此用户几乎感知不到问题。

但在长耗时、多 Tool Call、多事件处理的 Run 中，Session 最终保存可能明显滞后。

本次实际案例中：

```text
消息持久化完成：
12:26:48

新 Session Snapshot 保存完成：
12:28:06
```

存在约 78 秒的延迟窗口。

而用户下一轮恰好在：

```text
12:27:57
```

开始，因此加载到了旧 Snapshot。

---

## 8. 触发条件

当前案例表明，该问题更可能在以下条件下出现：

- 同一个 Conversation；
- 上一轮 Agent Run 很长；
- 上一轮包含大量 Knowledge / Tool / Shell / 外部检索等操作；
- Stream Event 数量较多；
- Session Snapshot 最终保存耗时明显；
- 用户在上一轮回答显示后很快继续提问；
- 下一轮启动时间早于上一轮最新 Snapshot 保存完成时间。

该问题并非每轮必现。

普通短对话中，多轮上下文通常表现正常。

---

## 9. 对用户体验的影响

该问题可能导致：

- “这个论文”“这个方法”“它”等上下文指代解析失败；
- Agent 突然要求用户重新提供论文标题；
- 前一轮刚确认的研究对象、术语或结论暂时不可见；
- 连续论文精读过程中出现短暂上下文断裂；
- 长工具链科研任务结束后，下一轮追问表现异常；
- 用户误以为 Agent 完全没有多轮记忆。

由于后续 Snapshot 保存完成后可能自动恢复，因此该问题容易表现为：

```text
上一轮正常
↓
某一轮突然失忆
↓
下一轮又恢复
```

具有明显的间歇性和时序相关性。

---

## 10. 当前问题状态

**状态：已定位根因，暂不修复。**

当前已确认：

- New Agent 多轮历史机制本身存在并正常工作；
- 当前 Conversation 历史通常可以正常使用；
- 本次异常与过期 `session_snapshot` 被下一轮加载有关；
- 最新 Snapshot 在上一轮长 Run 后存在明显保存延迟；
- 下一轮在保存窗口内启动，从而缺失最近一轮历史；
- 最新 Snapshot 保存完成后，后续对话恢复正常。

---

## 11. 当前问题定义

建议统一记录为：

> **Dify 1.16.1 New Agent 同一 Conversation 相邻 Run 重叠时加载过期 Session Snapshot，导致最近一轮上下文暂时缺失。**

代码/架构层面的简化描述：

> **Agent App Session Snapshot Persistence Race Condition / Stale Session Snapshot Read**

---

## 12. 本记录范围

本文档仅记录：

- 问题现象；
- 复现案例；
- 运行时证据；
- 已确认的时序关系；
- 当前根因判断；
- 影响范围。

**本文档不包含修复方案、Patch、架构修改或临时规避措施。**
