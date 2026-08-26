# LLM辅助科研系统

基于 Dify 的 RAG（检索增强生成）科研辅助平台。

## 项目结构

```text
LLM辅助科研系统/
├── dify-main/                  # Dify 底座（RAG 平台）
├── llm-model-collaboration/    # LLM 调用专业模型
├── rag-prompt-engineering/     # RAG 与提示词工程
└── 开发守则.md                  # 开发规范
```

## 快速开始

### 环境要求

- Docker >= 20.10
- Docker Compose >= 2.0
- 至少 4GB 可用内存

### 一键启动

```bash
# 1. 克隆仓库
git clone git@github.com:MQZ618/Ddfi_RAG.git
cd Ddfi_RAG/dify-main/docker

# 2. 复制环境配置
cp .env.example .env

# 3. 启动所有服务
docker compose up --build -d
```

启动后访问：http://localhost

### 聊天上传 PDF/DOC 读取修复

使用 Dify 1.16.1 Agent Backend 时，按 [dify-main/docker/README.pdf-upload-fix.md](dify-main/docker/README.pdf-upload-fix.md) 启用附件下载修复。

### 默认配置

| 配置项 | 默认值 |
|--------|--------|
| 数据库 | PostgreSQL 15 |
| 缓存 | Redis 6 |
| 向量库 | Weaviate |
| Web 端口 | 80 |
| 数据库密码 | difyai123456 |

### 首次访问

1. 打开 http://localhost
2. 注册管理员账号
3. 开始使用 Dify 平台

## 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f api

# 停止所有服务
docker compose down

# 停止并删除数据
docker compose down -v

# 重启服务
docker compose restart
```

## 开发指南

详见 [开发守则.md](开发守则.md)

两条开发线独立完成：

1. **LLM＋专业模型线** — 负责专业任务识别、参数提取、模型调用
2. **RAG＋提示词线** — 负责文档解析、检索、基于证据回答

两条线只通过稳定 HTTP 接口通信，不直接共享代码。

## 注意事项

- 不要修改 `dify-main/` 内的代码，需要扩展时通过 API 或插件
- 不要提交真实密钥到 Git，只提交 `.env.example`
- 每个工程必须能独立运行和测试

## License

See [LICENSE](LICENSE) for details.
