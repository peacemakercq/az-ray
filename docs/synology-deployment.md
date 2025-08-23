# 群晖DSM Container Manager部署指南

## 准备工作

1. **启用SSH**（可选，用于命令行操作）
   - 控制面板 → 终端机和SNMP → 启动SSH服务

2. **安装Container Manager**
   - 套件中心 → 搜索"Container Manager" → 安装

## 部署步骤

### 方法1: 通过Docker Hub拉取（推荐）

1. **打开Container Manager**
   - 主菜单 → Container Manager

2. **配置注册表**
   - 左侧菜单 → 注册表
   - 搜索: `your_dockerhub_username/az-ray`
   - 双击下载最新镜像

3. **创建容器**
   - 左侧菜单 → 容器
   - 点击"新增" → "从镜像创建"
   - 选择 `az-ray:latest` 镜像

4. **配置容器**
   
   **常规设置:**
   - 容器名称: `az-ray`
   - 启用自动重新启动

   **端口设置:**
   - 本机端口: `1080`
   - 容器端口: `1080`
   - 类型: TCP

   **环境变量:**
   ```
   AZURE_CLIENT_ID=your_azure_client_id
   AZURE_CLIENT_SECRET=your_azure_client_secret
   AZURE_TENANT_ID=your_azure_tenant_id
   AZURE_SUBSCRIPTION_ID=your_azure_subscription_id
   V2RAY_CLIENT_ID=your_v2ray_uuid
   AZURE_RESOURCE_GROUP=az-ray-rg
   AZURE_LOCATION=southeastasia
   V2RAY_PORT=9088
   SOCKS5_PORT=1080
   HEALTH_CHECK_INTERVAL=600
   DOMAIN_FILE=/app/config/domains.txt  # 可选：自定义域名文件
   ```

   **存储空间:**
   - 添加文件夹挂载（日志）
   - 主机路径: `/volume1/docker/az-ray/logs`
   - 容器路径: `/app/logs`
   
   - 添加文件夹挂载（配置，可选）
   - 主机路径: `/volume1/docker/az-ray/config`
   - 容器路径: `/app/config`

5. **启动容器**
   - 点击"完成"创建容器
   - 启动容器

### 方法2: 使用Docker Compose

1. **SSH连接到群晖**
   ```bash
   ssh admin@your_synology_ip
   ```

2. **创建项目目录**
   ```bash
   sudo mkdir -p /volume1/docker/az-ray
   cd /volume1/docker/az-ray
   ```

3. **创建环境文件**
   ```bash
   sudo nano .env
   ```
   
   内容如下:
   ```env
   AZURE_CLIENT_ID=your_azure_client_id
   AZURE_CLIENT_SECRET=your_azure_client_secret
   AZURE_TENANT_ID=your_azure_tenant_id
   AZURE_SUBSCRIPTION_ID=your_azure_subscription_id
   V2RAY_CLIENT_ID=your_v2ray_uuid
   AZURE_LOCATION=southeastasia
   SOCKS5_PORT=1080
   HEALTH_CHECK_INTERVAL=600
   DOMAIN_FILE=/app/config/domains.txt
   ```

4. **创建docker-compose.yml**
   ```bash
   sudo nano docker-compose.yml
   ```
   
   内容如下:
   ```yaml
   version: '3.8'
   
   services:
     az-ray:
       image: your_dockerhub_username/az-ray:latest
       container_name: az-ray
       ports:
         - "1080:1080"
       environment:
         - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
         - AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
         - AZURE_TENANT_ID=${AZURE_TENANT_ID}
         - AZURE_SUBSCRIPTION_ID=${AZURE_SUBSCRIPTION_ID}
         - V2RAY_CLIENT_ID=${V2RAY_CLIENT_ID}
         - AZURE_RESOURCE_GROUP=${AZURE_RESOURCE_GROUP}
         - AZURE_LOCATION=${AZURE_LOCATION}
         - SOCKS5_PORT=${SOCKS5_PORT}
         - HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL}
         - DOMAIN_FILE=${DOMAIN_FILE}
       restart: unless-stopped
       volumes:
         - ./logs:/app/logs
         - ./config:/app/config  # 用于存放自定义域名文件
   ```

5. **启动服务**
   ```bash
   sudo docker-compose up -d
   ```

## 自定义域名列表

默认情况下，系统会代理常见的被墙网站。你可以通过自定义域名文件来添加或修改需要代理的域名列表。

### 创建域名文件

1. **创建配置目录**
   ```bash
   sudo mkdir -p /volume1/docker/az-ray/config
   ```

2. **创建域名文件**
   ```bash
   sudo nano /volume1/docker/az-ray/config/domains.txt
   ```

3. **编辑域名文件内容**
   ```txt
   # 自定义域名文件
   # 每行一个域名，以#开头的行为注释行
   
   # Google 服务
   google.com
   youtube.com
   gmail.com
   
   # 社交媒体
   facebook.com
   twitter.com
   instagram.com
   
   # 开发相关
   github.com
   stackoverflow.com
   
   # 其他服务
   wikipedia.org
   dropbox.com
   ```

### 配置Container Manager使用域名文件

如果使用Container Manager GUI创建容器：

1. **添加存储空间挂载**
   - 主机路径: `/volume1/docker/az-ray/config`
   - 容器路径: `/app/config`

2. **添加环境变量**
   - 变量名: `DOMAIN_FILE`
   - 值: `/app/config/domains.txt`

### 域名文件格式说明

- **每行一个域名**：如 `google.com`
- **注释行**：以 `#` 开头的行会被忽略
- **空行**：空行会被忽略
- **域名验证**：无效格式的域名会被跳过并记录警告
- **追加模式**：文件中的域名会**追加**到默认域名列表中

### 重启生效

修改域名文件后，应用会自动检测文件变更并重新加载：

- **自动热重载**：应用每2秒检查一次域名文件，发现变更后自动重新加载并重启V2Ray
- **手动重启**：如需要立即生效，也可以重启容器：

```bash
sudo docker restart az-ray
```

或通过Container Manager界面重启容器。

## 网络配置

### 配置路由器

1. **设置自定义DNS**
   - 路由器管理界面 → 网络设置 → DNS设置
   - 主DNS: `8.8.8.8`
   - 备用DNS: `1.1.1.1`

2. **配置代理路由**（高级用户）
   - 某些路由器支持基于域名的代理规则
   - 将被墙域名指向 `群晖IP:1080` SOCKS5代理

### 配置客户端设备

**Windows:**
1. 设置 → 网络和Internet → 代理
2. 使用代理服务器: 开启
3. 地址: `群晖IP`
4. 端口: `1080`
5. 协议: SOCKS5

**macOS:**
1. 系统偏好设置 → 网络
2. 高级 → 代理 → SOCKS代理
3. 服务器: `群晖IP:1080`

**Android/iOS:**
使用支持SOCKS5的代理应用

## 监控和维护

### 查看日志
```bash
# Container Manager界面
容器 → az-ray → 详细信息 → 日志

# 或通过SSH
sudo docker logs az-ray -f
```

### 检查状态
```bash
sudo docker ps | grep az-ray
```

### 重启服务
```bash
sudo docker restart az-ray
```

### 更新镜像
```bash
sudo docker pull your_dockerhub_username/az-ray:latest
sudo docker-compose down
sudo docker-compose up -d
```

## 故障排除

### 常见问题

1. **容器无法启动**
   - 检查环境变量是否正确设置
   - 查看容器日志获取错误信息

2. **代理连接失败**
   - 确认Azure资源已创建
   - 检查网络连接
   - 查看健康监控日志

3. **性能问题**
   - 调整 `HEALTH_CHECK_INTERVAL` 降低检查频率
   - 选择更近的Azure区域

4. **域名文件相关问题**
   - 确认域名文件路径正确，容器内路径为 `/app/config/domains.txt`
   - 检查域名文件格式，确保每行一个域名
   - 查看容器日志确认域名文件是否成功加载
   - 修改域名文件后需要重启容器生效

### 日志位置
- 容器日志: Container Manager → 容器详情 → 日志
- 应用日志: `/volume1/docker/az-ray/logs/`
- 配置文件: `/volume1/docker/az-ray/config/`

### 联系支持
如遇到问题，请访问项目GitHub页面提交Issue。
