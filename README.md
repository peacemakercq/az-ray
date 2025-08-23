# AZ-Ray: Azure V2Ray Proxy Solution

一款基于Azure和V2Ray的智能翻墙应用，专为家庭群晖NAS Container Manager设计。

## 功能特性

- 🌐 自动创建和管理Azure资源（Storage File + Container Instance）
- 🔄 智能代理路由（仅代理被墙域名）
- 📊 连接质量监控和自动重启
- 🐳 Docker容器化部署
- ⚙️ 开发容器支持

## 架构概述

```
家庭网络 → 群晖NAS(本应用) → Azure Container Instance(V2Ray) → 目标网站
```

## 工作流程

1. **启动时**：确保Azure资源存在（Storage File + ACI）
2. **配置管理**：自动生成或更新V2Ray配置文件
3. **本地代理**：启动SOCKS5代理服务
4. **智能路由**：仅代理配置的域名请求
5. **健康监控**：每10分钟检测连接质量，必要时重启

## 环境变量

```bash
# Azure认证
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_TENANT_ID=your_tenant_id

# V2Ray配置
V2RAY_CLIENT_ID=your_uuid

# 可选配置
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_RESOURCE_GROUP=az-ray-rg
AZURE_LOCATION=southeastasia
SOCKS5_PORT=1080
HEALTH_CHECK_INTERVAL=600  # 秒
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

# 使用自定义域名文件
python __main__.py --domainfile domains.txt

# 启用详细日志
python __main__.py -v

# 重新创建Azure资源
python __main__.py --recreate
```

### 自定义域名列表

默认情况下，系统会代理一些常见的被墙网站。你也可以通过域名文件自定义需要代理的域名列表：

1. **创建域名文件**（如 `domains.txt`）：
   ```
   # 这是注释行
   google.com
   youtube.com
   facebook.com
   
   # 你也可以添加更多域名
   github.com
   twitter.com
   ```

2. **使用域名文件启动**：
   ```bash
   python __main__.py --domainfile domains.txt
   ```

**域名文件格式说明：**
- 每行一个域名
- 以 `#` 开头的行为注释行
- 空行会被忽略
- 无效格式的域名会被跳过并记录警告

## 配置路由器

将路由器的DNS或特定域名的请求指向群晖NAS的IP:1080作为SOCKS5代理。

## 许可证

MIT License
