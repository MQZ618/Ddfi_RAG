# Dify New Agent 无法正常读取聊天上传 PDF 问题记录

## 1. 问题概述

当前项目基于 **Dify 1.16.1 Self-hosted New Agent**。

在 New Agent 的实际聊天过程中，用户可以在界面上传 PDF，但 Agent 无法稳定地将该聊天附件作为可读取的完整文件使用。

问题不是“用户无法选择或上传 PDF”，而是：

> PDF 已进入 Dify，但在 New Agent 后续的内部文件引用、Agent Backend 与 Sandbox 文件访问链路中失败，导致 Agent 无法真正读取聊天中上传的 PDF 内容。

---

## 2. 已观察到的现象

典型操作流程：

1. 用户在 New Agent Web App 中上传 PDF；
2. 用户要求 Agent 阅读、分析或处理该 PDF；
3. Agent 尝试访问上传文件；
4. 文件没有被正常转换为 Agent / Sandbox 可访问的本地文件；
5. 最终无法取得 PDF 正文。

在部分运行中，模型还会输出类似工具调用意图的文本，但实际文件读取并未完成。

---

## 3. 已确认的错误表现

### 3.1 `dify-file-ref` 被错误按远程 URL 处理

运行日志中出现内部文件引用：

```text
dify-file-ref:...
```

后续该引用进入远程 URL 请求路径，并出现：

```text
Request URL is missing an 'http://' or 'https://' protocol.
```

随后发生重试，最终出现类似：

```text
MaxRetriesExceededError:
Reached maximum retries (...) for URL dify-file-ref:...
```

这说明内部的 `dify-file-ref` 没有在预期文件链路中被正常解析，而是进入了要求 `http://` 或 `https://` 的远程 URL 请求逻辑。

---

### 3.2 `ToolFile` 查找失败

同一类文件访问过程中还出现：

```text
ValueError: ToolFile <file-id> not found
```

表现为：

- 文件引用中存在具体文件记录 ID；
- 但后续文件构建或读取阶段无法找到对应 `ToolFile`；
- Agent 因此无法取得实际文件内容。

---

## 4. 当前问题边界

目前能够确认：

- 聊天界面可以接收 PDF；
- PDF 上传动作本身并非完全失败；
- New Agent 可以正常运行普通对话；
- Knowledge Base 检索可以独立工作；
- Sandbox / local_sandbox 并非整体不可用；
- 问题集中在 **聊天上传文件进入 New Agent 后的内部文件桥接链路**。

当前问题可概括为：

```text
Chat PDF Upload
↓
内部文件记录 / dify-file-ref
↓
Agent Backend
↓
文件解析 / ToolFile / FileRequest
↓
Sandbox
↓
失败
```

---

## 5. 与 Knowledge Base 的区别

该问题只针对：

> **用户在当前聊天中直接上传 PDF，然后要求 New Agent 读取。**

它不等同于 Knowledge Base 检索问题。

Knowledge Base 中的论文经过解析、切分和索引后，可以通过 Retrieval 返回相关文本片段。

但聊天附件路径需要把用户本轮上传的文件真正转换为 Agent / Sandbox 可访问的文件资源，两者属于不同的数据链路。

---

## 6. 对项目功能的影响

该问题导致当前 Agent 无法可靠支持以下交互：

- 用户临时上传一篇 PDF 后立即要求全文阅读；
- 基于当前上传 PDF 做逐页或逐段分析；
- 对当前聊天附件做全文翻译；
- 对用户刚上传但尚未进入 Knowledge Base 的论文做完整精读；
- 直接基于聊天附件核验表格、附录、公式等内容。

因此，“聊天直接上传 PDF 并由 New Agent 读取”目前不能视为稳定可用功能。

---

## 7. 当前问题状态

**状态：未解决。**

当前已经确认存在真实运行时错误，但本记录不包含修复方案、代码修改方案或替代架构设计。

需要保留的核心问题描述为：

> Dify 1.16.1 Self-hosted New Agent 中，聊天上传 PDF 后，内部 `dify-file-ref` / `ToolFile` 到 Agent Backend / Sandbox 的文件访问桥接存在异常，导致 Agent 无法可靠获取并读取上传 PDF 的实际内容。
