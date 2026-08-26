# Dify 1.16.1 聊天附件读取修复

适用于 Dify 1.16.1 的 Agent Backend 与本地 Sandbox。修复聊天上传文件下载地址缺少协议和主机名，导致 PDF、DOC 等附件无法进入 Sandbox 或解析插件的问题。

在本仓库的 `dify-main/docker` 目录执行：

```bash
docker compose build agent_backend
docker compose up -d --force-recreate agent_backend api worker worker_beat api_websocket
pytest -q tests/test_agent_backend_internal_file_urls.py
```

`.env.example` 已包含 `INTERNAL_FILES_URL=http://api:5001`；首次启动时复制它为 `.env`。`docker-compose.override.yaml` 会自动让 `agent_backend` 使用本仓库提供的自定义镜像。不要将真实 `.env` 提交到 Git。

验证时上传一个 PDF 和一个 DOC/DOCX，分别要求 Agent 读取；两者都能获得正文即表示文件下载与解析链路正常。

## 回滚

删除 `docker-compose.override.yaml`，从 `.env` 删除 `INTERNAL_FILES_URL`，然后执行：

```bash
docker compose up -d --force-recreate agent_backend api worker worker_beat api_websocket
```
