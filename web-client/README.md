# 智慧科研工作台

这是科研助手 Production v3 的项目侧 Web 工作台。它提供研究任务入口、材料上传、对话流式显示和真实工具文件下载，不修改 Dify Core 或官方 Dify 镜像。

## 启动

需要 Node.js 18+（当前开发环境使用 Node 24）。

```bash
cd web-client
cp .env.example .env
# 在 .env 中填写 Dify App API Key 和 Dify SECRET_KEY
npm test
npm start
```

浏览器打开 `http://127.0.0.1:3000/`。服务端只监听本机回环地址；如需通过反向代理对外提供，应由部署层负责 TLS、鉴权和访问控制。

## 配置

| 变量 | 用途 |
| --- | --- |
| `PORT` | 工作台监听端口，默认 `3000` |
| `DIFY_API_BASE_URL` | Dify Service API 的外部可达根地址，默认 `http://localhost`；可填带 `/v1` 的地址 |
| `DIFY_FILE_BASE_URL` | Dify 文件下载外部可达根地址，默认跟随 API 地址 |
| `DIFY_API_KEY` | 服务端使用的 Dify App API Key，不进入浏览器 |
| `DIFY_SECRET_KEY` | Dify 文件签名密钥，不进入浏览器 |
| `DIFY_USER_ID` | 上传和会话使用的稳定用户标识 |
| `DIFY_APP_ID` | 仅用于部署记录，不参与鉴权 |

`DIFY_API_BASE_URL` 和 `DIFY_FILE_BASE_URL` 必须是从运行 Node 服务的环境可达的地址。不要把 Docker 内部地址 `api:5001` 配给浏览器；它只能作为服务端到 Dify 的内部网络地址使用。

## 项目侧接口

- `GET /api/health`：返回代理是否同时具备 API Key 和文件签名密钥，不返回密钥。
- `POST /api/chat`：服务端固定使用 Dify `streaming` 模式，只转发已校验字段。
- `POST /api/files/upload`：接收单个研究材料并转发到 Dify `/v1/files/upload`，限制请求体为 50 MiB。
- `GET /api/artifacts/:id.:ext`：校验 UUID 和扩展名后现场签名，再把 Dify 工具文件字节代理给浏览器。

Markdown 中的 `/files/tools/...` 或 `http://api:5001/files/tools/...` 只有在文件 ID 和扩展名合法时才会重写为同源 `/api/artifacts/...`。普通链接不会被当作下载文件。

## 设计边界

- 页面没有虚构的项目统计、论文结果或证据结论；空状态会明确显示“待上传 / 待定 / 暂无数据”。
- 只有收到真实 Dify 文件 ID 才显示交付文件卡片和下载按钮。
- API Key、`SECRET_KEY`、签名 URL 和上传内容不写入前端脚本或日志。
- 当前实现不承诺附件跨轮次持续可访问。如果下一轮运行时不再提供附件，Agent 应诚实报告不可访问；这是已记录的平台限制。
- 内置 Dify Web App 仍可作为回退入口，本工作台不改变现有 Agent Prompt、Live DSL、Skill Registry 或 Tool 配置。
