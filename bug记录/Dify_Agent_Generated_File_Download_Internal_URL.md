# P2：New Agent 生成文件的下载链接使用 Docker 内部地址

## 状态

- 状态：confirmed / deferred
- 发现时间：2026-09-02
- 影响范围：Dify 1.16.1 Self-hosted New Agent 的生成文件交付
- 主回答是否受影响：否
- 文件是否实际生成：已观察到文件落盘

## 现象

Agent 可以在 Sandbox 中生成文件，但回答中的下载链接类似：

```text
http://api:5001/files/tools/<file-id>.<ext>?timestamp=...&nonce=...&sign=...
```

用户在浏览器中点击后无法正常下载。`api:5001` 是 Docker 网络内部的 API 服务名和端口，不是浏览器可达的外部地址。

## 运行时证据

历史 Dify 消息记录中出现了如下内部下载地址：

```text
http://api:5001/files/tools/<tool-file-id>.md?timestamp=...&nonce=...&sign=...
```

宿主机工具存储中可以找到实际生成文件，例如：

```text
dify-main/docker/volumes/app/storage/tools/<tenant-id>/88c9fd96133e4c14a037bfbfb6dde3a7.pdf
size = 2098959 bytes
```

当前 Docker 配置使用：

```text
INTERNAL_FILES_URL=http://api:5001
```

本机 Dify 1.16.1 源码中，Sandbox 的 `dify-agent file upload` 在获取上传产物下载地址时固定传入：

```text
dify-agent-runtime/internal/agentcli/file.go:71-81
CreateFileDownloadURL(..., false)
```

同一 CLI 的 `file download` 用于 Sandbox 读取输入文件，也使用内部访问语义。API 的 `FileRequestService` 已支持根据 `for_external` 选择内部或外部 URL。

## 根因

输入文件读取和输出文件交付共用了下载请求接口，但没有区分消费方：

```text
Sandbox 读取用户上传文件
  → for_external = false
  → INTERNAL_FILES_URL
  → api:5001

Agent 上传生成文件并交给用户
  → 当前同样使用 for_external = false
  → 生成内部 URL
  → 浏览器无法访问
```

此前为修复 PDF/DOC 进入 Sandbox 的内部地址问题，配置了 `INTERNAL_FILES_URL=http://api:5001`。该设置对 Sandbox 输入读取是必要的，但被错误地复用于生成文件的用户下载链接。

## 影响边界

- 文件本身通常已经生成并保存在工具存储中；
- 普通文本回答不受影响；
- 用户无法通过 Dify Web UI 正常下载 Agent 生成的 PDF、DOC/DOCX、Markdown 等文件；
- 已生成的错误链接可能在签名过期后失效，需要修复后重新生成；
- 不属于数据库删除或文件内容丢失问题。

## 正确修复方向

只修改输出交付路径：

```text
file upload → for_external = true
file download → for_external = false
```

因此不应把 `INTERNAL_FILES_URL` 改成公网地址，也不应把所有 Sandbox 下载请求统一改成外部 URL。落地修复需要构建包含该 CLI 改动的自定义 `local_sandbox` 镜像，并在 Docker Compose 中固定引用该镜像。

## 当前处理

- 状态：P2，暂缓完整镜像修复；
- 未删除或覆盖生成文件；
- 未修改数据库、`.env` 或正在运行的容器；
- 当前仓库已有的 Agent backend 附件读取修复不能自动修复 local_sandbox 的输出下载语义；
- 其他用户若直接拉取官方 `langgenius/dify-agent-local-sandbox:1.16.1`，仍会复现该问题。

## 证据边界

本记录不包含完整签名 URL、API Key、Secret Key 或用户文件内容。源码定位来自本机 Dify 1.16.1 源码快照；源码快照不等于当前官方容器已加载该修改。
