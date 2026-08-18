# Dify 1.16.1 New Agent 聊天上传 PDF 读取失败 — 源码根因分析

> 对应问题记录：`bug记录/Dify_New_Agent_PDF_Upload_Issue.md`
> 分析对象：`dify-1.16.1` 源码（api / dify-agent / dify-agent-runtime / web）
> 分析方式：纯静态源码追踪（未运行实例、未修改任何代码）

---

## 一、正常链路（设计意图）

```
前端聊天上传 PDF
  → UploadFile 记录（transfer_method = local_file）
  → POST /chat-messages  files=[{transfer_method:"local_file", upload_file_id:"<id>"}]
  → AgentAppGenerator.generate()            api/core/app/apps/agent_app/app_generator.py
      prompt_file_mappings = args["files"]
      _append_prompt_file_mappings()        # 把定位符 JSON 追加到 user query 文本
      → query = "...\nUser provided files: use dify-agent file download with the
                  listed transfer_method and reference/url to get the files..."
                 + [{"transfer_method":"local_file","reference":"dify-file-ref:<base64>"}]
  → AgentAppRunner → AgentAppRuntimeRequestBuilder.build()
      user_prompt = query                    # ⚠️ 文件仅以纯文本进入后端，无结构化字段
  → Agent Backend（dify-agent）→ LLM
  → LLM 在 sandbox 内执行:  dify-agent file download local_file 'dify-file-ref:...'
  → dify-agent-runtime (Go CLI)              dify-agent-runtime/internal/agentcli/file.go
      RunFileDownload → CreateFileDownloadURL → agent stub（HTTP/gRPC /files/download-request）
  → agent stub server                        dify-agent/src/dify_agent/agent_stub/server/*
      DifyApiAgentStubFileRequestHandler.create_download_request
      → Dify API  /inner/api/download/file/request
  → FileRequestService.request_download_url  api/services/file_request_service.py
      → build_from_mapping(local_file)       api/factories/file_factory/builders.py
          → UploadFile 查询（tenant + user 过滤）
      → resolve_file_url → 签名 /files/{id}/file-preview URL
  → sandbox CLI DownloadFromURL → 写回 sandbox 本地 → LLM 读取
```

关键事实：**New Agent 路径没有任何结构化的文件传递通道**。`AgentBackendAgentAppRunInput`
（`api/clients/agent_backend/request_builder.py`）没有 files 字段；文件定位符只以 JSON 文本
追加进 user prompt，文件能否被读取**完全取决于 LLM 是否正确解析该 JSON 并正确调用
`dify-agent file download <transfer_method> <reference>`**。Workflow Agent v2 节点同理
（仅有 `sys.files` 文本摘要）。

---

## 二、错误 1：`dify-file-ref:` 被当作远程 URL 请求（逐字匹配）

日志：

```text
Request URL is missing an 'http://' or 'https://' protocol.
MaxRetriesExceededError: Reached maximum retries (...) for URL dify-file-ref:...
```

### 精确代码位置

`api/core/helper/ssrf_proxy.py::make_request()`（163–273 行）：

```python
while retries <= max_retries:
    try:
        request = client.build_request(method=method, url=url, **kwargs)   # httpx 对 dify-file-ref:... 抛
        ...                                                                 # httpx.UnsupportedProtocol
    except httpx.RequestError as e:                                          # "Request URL is missing
        ...                                                                 #  an 'http://' or 'https://' protocol."
        retries += 1
        ...
raise MaxRetriesExceededError(f"Reached maximum retries ({max_retries}) for URL {url}")   # ← 逐字匹配
```

- `"Request URL is missing an 'http://' or 'https://' protocol."` 是 **httpx** 的
  `UnsupportedProtocol`（`httpx.RequestError` 子类）异常消息；
- `MaxRetriesExceededError ... for URL dify-file-ref:...` 是 **ssrf_proxy.py:273** 的
  原文，重试耗尽后抛出。两条消息与问题记录 3.1 完全一致，因此该错误一定发生在
  **Dify API 进程内、经过 ssrf_proxy 的请求路径**上。

### 触发链

`dify-file-ref:` 值作为 `remote_url` 的 `url` 进入文件映射：

```
mapping = {"transfer_method": "remote_url", "url": "dify-file-ref:<...>"}
  → FileRequestService.request_download_url()
  → build_from_mapping() → _build_from_remote_url()        api/factories/file_factory/builders.py:237
      url = mapping.get("url") or mapping.get("remote_url")   # 只检查 truthy，无协议校验
  → get_remote_file_info(url)                               api/factories/file_factory/remote.py:76
  → remote_fetcher.make_request("HEAD", "dify-file-ref:...", follow_redirects=True)
  → _resolve_dify_signed_file_url() 不匹配（非 http 签名 URL）→ 回落
  → ssrf_proxy.make_request() → httpx UnsupportedProtocol → 重试 → MaxRetriesExceededError
```

`_build_from_remote_url`（builders.py:284-306）只做 `if not url: raise`，
**没有校验 url 必须以 http:// 或 https:// 开头**；`get_remote_file_info` 直接把该值交给
SSRF 客户端。dify-agent 侧同样存在未校验透传点：
`dify-agent/src/dify_agent/layers/dify_plugin/tools_layer.py::_normalize_plugin_file_parameter`
（517-533 行）对 `{"url": "dify-file-ref:..."}` 不校验协议即透传（只有
`_plugin_file_parameter_from_mapping` 的 remote_url 分支做了 `_is_remote_url` 校验，
模型直接把字符串/url 字段传工具时会绕过）。

### 结论

**`dify-file-ref:` 不是 URL，却在某处被当作 `remote_url` 的 url 提交**。最可能来源：
LLM 看到 prompt 中追加的定位符 JSON 后，没有调用 `dify-agent file download`，而是把
`reference` 值当作 URL 塞进了文件参数（插件 FILE 工具参数、或直接 HTTP 请求），
最终以 `remote_url` mapping 到达 FileRequestService，触发 ssrf_proxy 重试耗尽。

---

## 三、错误 2：`ValueError: ToolFile <file-id> not found`（逐字匹配）

### 精确代码位置

`api/factories/file_factory/builders.py::_build_from_tool_file`（309–328 行）：

```python
tool_file_id = resolve_mapping_file_id(mapping, "tool_file_id")   # 解析 reference/related_id
if not tool_file_id:
    raise ValueError(f"ToolFile {tool_file_id} not found")        # ← 319 行
stmt = select(ToolFile).where(ToolFile.id == tool_file_id, ToolFile.tenant_id == tenant_id)
...
tool_file = session.scalar(access_controller.apply_tool_file_filters(stmt))
if tool_file is None:
    raise ValueError(f"ToolFile {tool_file_id} not found")        # ← 328 行
```

### 触发条件

- mapping 的 `transfer_method = tool_file`，且 reference 解析出的 record_id 在
  `ToolFile` 表中不存在，或不在当前租户/用户访问范围内
  （`api/core/app/file_access/controller.py::apply_tool_file_filters`：
  强制 `tenant_id` 匹配；end-user 场景额外要求 `ToolFile.user_id == user_id`）。

### 结论

**聊天上传的文件是 `UploadFile`（应使用 `local_file`），却以 `tool_file` 方式请求**。
`dify-file-ref:` 中包的是 UploadFile 的 record_id，查 `ToolFile` 表必然不存在 →
精确的 `ValueError: ToolFile <id> not found`。即：LLM 在 `dify-agent file download`
中把 transfer_method 传错（`tool_file` ↔ `local_file`），或把 `dify-file-ref`
与其他 transfer_method 错误组合。

（旁证：`dify-agent/src/dify_agent/agent_stub/protocol/agent_stub.py::AgentStubFileMapping.
validate_locator` 要求非 remote 引用必须是 canonical `dify-file-ref:`，一旦 LLM 转录
reference 出错，还会得到 "reference must be a canonical Dify file reference"。）

---

## 四、根因总结

两条错误是**同一设计缺陷的两种表现**：

> **Dify 1.16.1 New Agent 的聊天文件读取完全依赖 LLM 行为**：
> 文件定位符（canonical `dify-file-ref:` + transfer_method）只以 JSON 文本追加进
> user prompt（`app_generator.py::_append_prompt_file_mappings`），没有结构化字段、
> 没有程序化注入、没有失败兜底。LLM 一旦（a）把 reference 当 URL 使用，或
> （b）把 transfer_method 传错（tool_file↔local_file），文件桥接即失败，且错误
> 以难以诊断的底层异常（ssrf_proxy 重试耗尽 / ToolFile not found）形式暴露。

放大因素：

1. **reference 是 base64url 长字符串**，LLM 转录极易出错；agent_stub 协议校验严格
   （`is_canonical_dify_file_reference`），任何偏差直接失败。
2. **transfer_method 与文件类型强绑定**：聊天上传 = `local_file`/UploadFile，
   sandbox 产物上传 = `tool_file`/ToolFile；LLM 混用即 ToolFile not found。
3. **API 侧缺协议校验**：`_build_from_remote_url` 未拒绝非 http(s) url，
   `remote_fetcher` 把任意字符串交给 ssrf_proxy 重试，产生误导性错误。
4. **prompt 指引弱**：`_append_prompt_file_mappings` 只有一句话 + JSON，
   未给出示例命令、未禁止把 reference 当 URL、未说明 transfer_method 语义。
5. **无失败兜底**：下载失败后没有重试策略、没有把错误映射为可读提示、
   没有降级为“请重新上传/使用知识库”的路径。

---

## 五、修复建议（按改动范围分级）

### 5.1 不改 Dify 代码（工程侧，可立即做）

- 在 Agent Soul 系统提示中注入明确文件操作指引：
  - 必须使用 `dify-agent file download local_file '<reference>'`；
  - 禁止把 `dify-file-ref:` 当作 URL 请求；
  - 禁止更改 `transfer_method`（聊天附件一律 `local_file`）；
  - 下载后先 `dify-agent file` / 本地读取验证再回答。
- 记录每次上传的文件与定位符，便于排查 LLM 是否转录错误。

### 5.2 Dify 源码级最小修复（需按开发守则报备批准）

- `api/factories/file_factory/builders.py::_build_from_remote_url`：
  对 `url` 增加协议校验（`http://`/`https://`），拒绝后抛可读
  `ValueError("remote_url must start with http:// or https://")`，避免进入 ssrf 重试。
- `api/core/file/remote_fetcher.py` / `ssrf_proxy.make_request`：
  对非 http(s) URL 直接拒绝（快速失败），而不是重试后抛 MaxRetriesExceededError。
- `dify-agent .../tools_layer.py::_normalize_plugin_file_parameter`：
  与 `_plugin_file_parameter_from_url` 一致地校验协议。
- `app_generator.py::_append_prompt_file_mappings`：强化提示文本
  （示例命令、禁止行为、transfer_method 说明）。

### 5.3 结构性修复（根治）

- 让 Agent App 把 `prompt_file_mappings` 作为**结构化字段**随
  `CreateRunRequest` 传给 agent backend（如 workflow 的 `sys.files`），由 runtime
  在 sandbox 启动时**程序化落盘**，LLM 只需按文件名读取，不再依赖解析 JSON 定位符
  与 CLI 调用。
- 或：为 `dify-agent file download` 增加按 `record_id` 直接解析的容错
  （`local_file` 缺失时自动尝试 UploadFile 反向查询），减少 LLM 出错面。

---

## 六、结论

问题记录中的两条运行时错误均已定位到精确源码位置：

| 日志现象 | 精确代码位置 | 直接原因 |
|---|---|---|
| `Request URL is missing an 'http://' or 'https://' protocol.` + `MaxRetriesExceededError ... for URL dify-file-ref:...` | `api/core/helper/ssrf_proxy.py:273`（触发于 `factories/file_factory/remote.py:84` 经 `_build_from_remote_url`） | `dify-file-ref:` 被当作 `remote_url` 的 url 提交，httpx 协议校验失败后重试耗尽 |
| `ValueError: ToolFile <file-id> not found` | `api/factories/file_factory/builders.py:319/328` | 聊天上传的 UploadFile 被以 `tool_file` 方式请求，ToolFile 表查无 |

**本质**：New Agent 聊天文件桥接没有结构化、程序化的传递通道，读取成功依赖 LLM
正确使用 `dify-agent file download` CLI；API 侧又缺少协议/类型校验与失败兜底，
导致 LLM 出错时暴露为上述底层异常。

**状态**：根因已定位（源码级），未修改任何代码。
