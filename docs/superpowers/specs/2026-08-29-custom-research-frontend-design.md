# 自定义智慧科研工作台与文件交付设计

## 目标

为现有科研助手 Production v3 增加一个项目侧 Web 工作台，解决两个相互关联的问题：

1. 让研究者以“课题—证据—写作—审查”的工作流使用 Agent，而不是面对通用聊天页；
2. 将 Agent 返回的 Dify 工具文件转换为同源、可验证、可重新签名的下载入口，避免把 Docker 内部地址或已过期签名直接暴露给用户。

本设计只改项目侧新增代码和文档，不修改 Dify Core、官方 Dify 镜像、Prompt、DSL、数据库、数据集、实验日志或 `main` 分支。

## 用户界面

- 顶部品牌：智慧科研工作台；当前 Agent 显示为科研助手 Production v3。
- 左侧导航：研究总览、我的课题、文献库、论文写作、证据审查。导航用于表达工作域，不在本阶段伪造后端页面或统计数据。
- 主区：研究状态、快捷任务、对话区和文件卡片。快捷任务包括论文精读、文献对比、Introduction 润色、实验设计、引用核验。
- 右侧证据栏：显示“待核验 / 已接地 / 证据不足”等语义状态；没有真实数据时显示待上传或暂无数据。
- 颜色语义：深海军蓝承载工作台，暖白承载内容，青绿色表示已接地，琥珀色表示待核验，红色只表示错误或拒答。
- 交互必须可访问：键盘可操作、表单有 label、按钮有明确名称、窄屏时侧栏可折叠为横向区域。

## 运行架构

```text
Browser
  -> project-side Node server (/api/*)
       -> Dify Service API (/v1/chat-messages, /v1/files/upload)
       -> Dify file endpoint (/files/tools/<id>.<ext>)
```

浏览器永远不接触 Dify App API key 或 `SECRET_KEY`。服务端保存配置，转发聊天 SSE，并在下载请求时用 Dify 的签名格式生成短时 URL。默认上游地址可指向本机反向代理；`api:5001` 等容器内部主机名不得进入浏览器响应。

## API 契约

### `GET /api/health`

返回服务状态和是否已配置 Dify 的布尔信息，不返回任何密钥。

### `POST /api/chat`

请求体只允许项目侧需要的字段：

```json
{
  "query": "请精读这篇论文",
  "inputs": {},
  "user": "research-web-user",
  "conversation_id": "",
  "files": []
}
```

服务端固定使用 `response_mode=streaming`，只转发已校验的 `query`、`inputs`、`user`、`conversation_id` 和 `files`。Dify 的其他控制字段不由浏览器任意注入。

### `POST /api/files/upload`

接收单个 multipart 文件，限制大小，转发给 Dify `/v1/files/upload`，返回 Dify 的上传元数据。上传只表示材料已进入当前会话上下文；不承诺下一轮仍可重新读取原文件。

### `GET /api/artifacts/:id.:ext`

只接受 UUID 形式的工具文件 ID 和小写扩展名白名单。服务端用：

```text
file-preview|<tool_file_id>|<timestamp>|<nonce>
```

按 Dify 当前 HMAC-SHA256/URL-safe Base64 规则签名，访问外部文件入口后把字节流转发给浏览器。失败时返回不泄露上游地址的错误。下载代理不会从普通 Markdown 中盲信任任意 URL。

## 安全与证据边界

- 服务端不记录 API key、secret、完整签名 URL 或用户文件内容。
- Markdown 渲染只支持有限安全子集；HTML 先转义，普通外链使用安全的 `noopener` 属性。
- 从 Agent 返回的 `http://api:5001/files/tools/...`、相对 `/files/tools/...` 和同格式链接，只有在 ID/扩展名通过校验后才重写为 `/api/artifacts/...`。
- 不生成不存在的文件卡片，不把“已生成”写成“可下载”；只有收到真实 Dify 文件 ID 或真实上传响应才展示对应状态。
- 跨轮附件生命周期继续作为已知平台限制记录，不通过项目侧伪造持久化结果。

## 非目标

- 不修改 `/Users/mqzzz/Desktop/LLM辅助科研系统/dify-1.16.1-source` 或仓库内 `dify-main/`。
- 不重建或发布自定义 Dify 镜像。
- 不替换 Prompt v3、Live DSL、Skill Registry 或工具实现。
- 不加入虚假的项目、论文、指标、证据或生产统计。

## 验收标准

1. `npm test` 覆盖配置读取、签名、ID/扩展名校验、聊天 SSE 转发、文件代理和安全 Markdown 重写。
2. `GET /api/health` 在 Dify 未配置时仍能明确报告未配置，不伪造在线。
3. 文件代理返回真实上游字节和下载响应头，且响应体、错误和页面均不泄露密钥或内部 Docker 地址。
4. 快捷任务和对话页面在无后端数据时保持诚实的空状态。
5. 仅新增 `web-client/`、相关设计/计划文档和为纳入 `.env.example` 所需的最小 `.gitignore` 规则。
