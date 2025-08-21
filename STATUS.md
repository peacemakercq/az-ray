# AZ-Ray项目状态

## ✅ 已完成的功能

### 核心应用架构
- [x] Python主应用程序 (`src/main.py`)
- [x] 配置管理系统 (`src/config.py`)
- [x] Azure资源管理器 (`src/azure_manager.py`)
- [x] V2Ray代理管理器 (`src/v2ray_manager.py`)
- [x] 健康监控系统 (`src/health_monitor.py`)

### 容器化部署
- [x] 标准Dockerfile
- [x] 多架构Dockerfile (支持ARM64)
- [x] Docker Compose配置
- [x] 环境变量配置

### 开发环境
- [x] Dev Container配置
- [x] Python依赖管理 (requirements.txt, pyproject.toml)
- [x] 代码质量工具配置 (Black, Flake8, MyPy)
- [x] 单元测试框架 (pytest)

### CI/CD
- [x] GitHub Actions工作流
- [x] 自动Docker镜像构建和推送
- [x] 多平台支持 (amd64, arm64)
- [x] 代码质量检查

### 部署指南
- [x] 群晖NAS部署文档
- [x] Azure配置指南
- [x] 快速部署脚本
- [x] 环境变量模板

## 🔄 工作流程实现

### 1. Azure资源管理 ✅
- 自动创建资源组
- 自动创建存储账户和文件共享
- 自动生成V2Ray服务器配置
- 自动创建和管理Azure Container Instance

### 2. V2Ray代理服务 ✅
- 本地SOCKS5代理服务器
- 智能路由 (仅代理被墙域名)
- 与Azure V2Ray服务器的WebSocket连接
- 自动配置文件生成

### 3. 健康监控 ✅
- 每10分钟检查连接质量
- Google连通性测试
- 自动重启失效的容器
- 连续失败处理机制

### 4. 容器化部署 ✅
- Docker镜像自动构建
- 群晖Container Manager支持
- 环境变量配置
- 日志管理

## 📋 使用说明

### 快速开始
1. 按照 `docs/azure-setup.md` 配置Azure资源
2. 设置环境变量 (参考 `.env.example`)
3. 运行部署脚本: `./deploy.sh`
4. 配置客户端使用SOCKS5代理 (127.0.0.1:1080)

### 群晖NAS部署
详见 `docs/synology-deployment.md`

### 开发环境
```bash
# 使用Dev Container (推荐)
code .
# 选择 "Reopen in Container"

# 或本地开发
pip install -r requirements.txt
python -m src.main
```

## 🛠️ 架构设计

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   本地客户端     │    │   群晖NAS       │    │     Azure       │
│                │    │                │    │                │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │  应用程序  │──┼────┼─→│ AZ-Ray    │──┼────┼─→│    ACI     │  │
│  └───────────┘  │    │  │ (SOCKS5)  │  │    │  │ (V2Ray)   │  │
│                │    │  └───────────┘  │    │  └───────────┘  │
│                │    │                │    │                │
│                │    │  ┌───────────┐  │    │  ┌───────────┐  │
│                │    │  │健康监控器  │  │    │  │  Storage  │  │
│                │    │  └───────────┘  │    │  │   File    │  │
│                │    │                │    │  └───────────┘  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ⚙️ 环境要求

- Python 3.11+
- Docker (用于部署)
- Azure订阅账户
- 群晖NAS (可选，用于容器部署)

## 📦 依赖包

### 核心依赖
- `azure-identity`: Azure身份认证
- `azure-mgmt-*`: Azure资源管理
- `azure-storage-file-share`: Azure文件存储
- `aiohttp`: 异步HTTP客户端
- `aiohttp-socks`: SOCKS代理支持

### 开发依赖
- `pytest`: 单元测试
- `black`: 代码格式化
- `flake8`: 代码检查
- `mypy`: 类型检查

## 🔐 安全考虑

- 使用Azure服务主体进行身份认证
- 客户端密码定期轮换
- 容器以非root用户运行
- 敏感信息通过环境变量传递
- 不在代码中硬编码凭据

## 📝 许可证

MIT License - 详见 `LICENSE` 文件

## 🤝 贡献

欢迎提交Issue和Pull Request！

开发流程:
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📞 支持

如有问题，请在GitHub上提交Issue。
