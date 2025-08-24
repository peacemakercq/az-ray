# Docker Directory

本目录包含项目的所有 Docker 相关文件。

## 📁 文件说明

### `Dockerfile`
单架构 Docker 镜像构建文件（Linux x64）。

### `Dockerfile.multi`
多架构 Docker 镜像构建文件（支持 amd64 和 arm64）。

### `docker-compose.yml`
Docker Compose 配置文件，用于本地开发和测试。

### `.dockerignore`
Docker 构建时忽略的文件列表。

## 🚀 使用方法

### 本地开发

```bash
# 使用 Makefile（推荐）
make docker-build    # 构建镜像
make docker-run      # 运行容器
make docker-stop     # 停止容器
make docker-logs     # 查看日志

# 或直接使用 docker-compose
cd docker/
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### 生产部署

```bash
# 构建多架构镜像
docker buildx build -f docker/Dockerfile.multi \
  --platform linux/amd64,linux/arm64 \
  -t your-registry/az-ray:latest \
  --push .
```

## 🔧 环境配置

容器需要以下环境变量：

- `AZURE_CLIENT_ID` - Azure 应用客户端ID
- `AZURE_CLIENT_SECRET` - Azure 应用客户端密钥  
- `AZURE_TENANT_ID` - Azure 租户ID
- `AZURE_SUBSCRIPTION_ID` - Azure 订阅ID
- `V2RAY_CLIENT_ID` - V2Ray 客户端UUID
- `SOCKS5_PORT` - SOCKS5 代理端口（默认1080）

参考项目根目录的 `.env.example` 文件。
