# AZ-Ray: Azure V2Ray Proxy Solution

一款基于Azure和V2Ray的智能翻墙应用，专为家庭群晖NAS Container Manager设计。

## 功能特性

- 🌐 自动创建和管理Azure资源（Storage File + Container Instance）
- 🔄 智能代理路由（使用GeoIP智能分流）
- 📊 连接质量监控和自动重启
- 🐳 Docker容器化部署
- ⚙️ 开发容器支持
- 🛠️ Makefile 自动化工具

## 架构概述

```
家庭网络 → 群晖NAS(本应用) → Azure Container Instance(V2Ray) → 目标网站
```

## 工作流程

1. **启动时**：确保Azure资源存在（Storage File + ACI）
2. **配置管理**：自动生成或更新V2Ray配置文件
3. **本地代理**：启动SOCKS5代理服务
4. **智能路由**：使用GeoIP数据库智能分流
5. **健康监控**：每10分钟检测连接质量，必要时重启

## 🚀 快速开始

### 1. 设置开发环境

```bash
# 克隆项目
git clone https://github.com/your-username/az-ray.git
cd az-ray

# 完整环境设置（推荐）
make dev-setup
```

### 2. 配置环境变量

编辑 `.env` 文件：

```bash
# Azure认证
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_TENANT_ID=your_tenant_id

# V2Ray配置
V2RAY_CLIENT_ID=your_uuid
V2RAY_PORT=443  # WebSocket端口，默认443

# 可选配置
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_RESOURCE_GROUP=az-ray-rg
AZURE_LOCATION=southeastasia
SOCKS5_PORT=1080
HEALTH_CHECK_INTERVAL=600  # 秒

# 域名文件路径（可选）
DOMAIN_FILE=/path/to/domains.txt
```

### 3. 下载 GeoIP 数据

```bash
# 自动下载（需要网络可达GitHub）
make update-geo

# 或手动下载到 data/ 目录
# - geoip.dat from https://github.com/v2fly/geoip/releases/latest
# - geosite.dat from https://github.com/v2fly/domain-list-community/releases/latest
```

## 🛠️ 开发工具

项目使用 Makefile 提供便捷的开发命令：

```bash
make help          # 显示所有可用命令
make install       # 安装依赖
make test          # 运行测试
make lint          # 代码检查
make run           # 运行应用
make docker-build  # 构建Docker镜像
make deploy        # 部署到Azure
```

## 快速开始

### Docker运行

```bash
docker run -d \
  --name az-ray \
  -p 1080:1080 \
  -e AZURE_CLIENT_ID=your_client_id \
  -e AZURE_CLIENT_SECRET=your_client_secret \
  -e AZURE_TENANT_ID=your_tenant_id \
  -e V2RAY_CLIENT_ID=your_uuid \
  your_dockerhub_username/az-ray:latest
```

### 群晖Container Manager

1. 在Container Manager中搜索镜像：`your_dockerhub_username/az-ray`
2. 创建容器，设置端口映射：`1080:1080`
3. 添加环境变量（见上方列表）
4. 启动容器

## 开发

### 使用Dev Container

1. 克隆仓库
2. 在VS Code中打开
3. 选择"Reopen in Container"
4. 开始开发

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python __main__.py

# 启用详细日志
python __main__.py -v

# 重新创建Azure资源
python __main__.py --recreate

# 使用自定义域名文件
export DOMAIN_FILE=domains.txt
python __main__.py
```

### 自定义域名列表

默认情况下，系统会代理一些常见的被墙网站。你也可以通过环境变量自定义需要代理的域名列表：

#### 使用环境变量

```bash
export DOMAIN_FILE=/path/to/domains.txt
python __main__.py
```

#### 在Docker中使用

```bash
docker run -d \
  --name az-ray \
  -p 1080:1080 \
  -e DOMAIN_FILE=/app/domains.txt \
  -v /host/path/domains.txt:/app/domains.txt \
  your_dockerhub_username/az-ray:latest
```

**域名文件格式说明：**
- 每行一个域名
- 以 `#` 开头的行为注释行
- 空行会被忽略
- 无效格式的域名会被跳过并记录警告
- 文件中的域名会**追加**到默认域名列表中
- **自动热重载**：应用会监控域名文件变化，自动重新加载并重启V2Ray代理（约2秒检测间隔）

## 配置路由器

将路由器的DNS或特定域名的请求指向群晖NAS的IP:1080作为SOCKS5代理。

## 许可证

MIT License
