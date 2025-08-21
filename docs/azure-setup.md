# Azure配置指南

本指南将帮助你在Azure中创建必要的资源和权限，以便AZ-Ray应用正常运行。

## 先决条件

- Azure订阅账户
- Azure CLI 或 Azure Portal 访问权限
- PowerShell 或 Bash 终端

## 步骤1: 创建Azure Active Directory应用

### 使用Azure Portal

1. **登录Azure Portal**
   - 访问 [portal.azure.com](https://portal.azure.com)
   - 使用你的Azure账户登录

2. **创建应用注册**
   - 搜索并选择 "Azure Active Directory"
   - 左侧菜单 → 应用注册 → 新注册
   - 应用名称: `az-ray-app`
   - 支持的账户类型: 仅此组织目录中的账户
   - 点击"注册"

3. **获取应用信息**
   - 在应用概述页面记录:
     - 应用程序(客户端) ID → `AZURE_CLIENT_ID`
     - 目录(租户) ID → `AZURE_TENANT_ID`

4. **创建客户端密码**
   - 左侧菜单 → 证书和密码 → 新客户端密码
   - 描述: `az-ray-secret`
   - 过期时间: 24个月
   - 记录生成的值 → `AZURE_CLIENT_SECRET`

### 使用Azure CLI

```bash
# 登录Azure
az login

# 创建服务主体
az ad sp create-for-rbac --name "az-ray-app" --role contributor --scopes /subscriptions/{subscription-id}

# 输出示例:
# {
#   "appId": "your-client-id",           # AZURE_CLIENT_ID
#   "displayName": "az-ray-app",
#   "password": "your-client-secret",    # AZURE_CLIENT_SECRET
#   "tenant": "your-tenant-id"           # AZURE_TENANT_ID
# }
```

## 步骤2: 分配权限

应用需要以下Azure权限:

### 必需权限
- **贡献者** (Contributor): 创建和管理资源
- **存储帐户参与者** (Storage Account Contributor): 管理存储账户
- **容器实例参与者** (Container Instance Contributor): 管理容器实例

### 分配权限 (Azure Portal)

1. **订阅级别权限**
   - 搜索 "订阅" → 选择你的订阅
   - 左侧菜单 → 访问控制 (IAM) → 添加角色分配
   - 角色: 贡献者
   - 成员: 选择创建的应用 `az-ray-app`

2. **验证权限**
   - 确保应用在订阅的"角色分配"中显示为"贡献者"

### 分配权限 (Azure CLI)

```bash
# 获取订阅ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# 获取应用的对象ID
APP_ID="your-client-id"
OBJECT_ID=$(az ad sp show --id $APP_ID --query id -o tsv)

# 分配贡献者角色
az role assignment create \
  --assignee $APP_ID \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"
```

## 步骤3: 获取订阅ID

### Azure Portal
- 搜索 "订阅" → 选择你的订阅
- 记录订阅ID → `AZURE_SUBSCRIPTION_ID`

### Azure CLI
```bash
az account show --query id -o tsv
```

## 步骤4: 生成V2Ray客户端ID

V2Ray需要一个UUID作为客户端标识:

### 在线生成
访问 [uuidgenerator.net](https://www.uuidgenerator.net/) 生成UUID

### 命令行生成

**Linux/macOS:**
```bash
uuidgen
```

**Windows (PowerShell):**
```powershell
[System.Guid]::NewGuid()
```

**Python:**
```python
import uuid
print(str(uuid.uuid4()))
```

记录生成的UUID → `V2RAY_CLIENT_ID`

## 步骤5: 环境变量配置

将获取的值配置为环境变量:

```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export V2RAY_CLIENT_ID="your-uuid"

# 可选配置
export AZURE_RESOURCE_GROUP="az-ray-rg"
export AZURE_LOCATION="southeastasia"
export SOCKS5_PORT="1080"
export HEALTH_CHECK_INTERVAL="600"
```

## 步骤6: 测试配置

使用Azure CLI验证配置:

```bash
# 使用服务主体登录
az login --service-principal \
  --username $AZURE_CLIENT_ID \
  --password $AZURE_CLIENT_SECRET \
  --tenant $AZURE_TENANT_ID

# 列出资源组（验证权限）
az group list

# 退出登录
az logout
```

## 安全注意事项

1. **保护凭据**
   - 不要将凭据提交到代码仓库
   - 使用安全的密码管理器存储
   - 定期轮换客户端密码

2. **最小权限原则**
   - 仅分配必要的权限
   - 考虑使用资源组级别的权限而不是订阅级别

3. **监控使用情况**
   - 定期检查Azure活动日志
   - 监控资源使用和费用

## 故障排除

### 常见错误

1. **认证失败**
   ```
   AuthenticationError: The credentials provided are invalid
   ```
   - 检查客户端ID、密码和租户ID是否正确
   - 确认应用注册未过期

2. **权限不足**
   ```
   AuthorizationError: The client does not have authorization to perform action
   ```
   - 检查角色分配是否正确
   - 确认权限范围包含目标资源

3. **订阅不存在**
   ```
   SubscriptionNotFound: The subscription could not be found
   ```
   - 检查订阅ID是否正确
   - 确认应用有权访问该订阅

### 验证步骤

```bash
# 1. 检查环境变量
echo "Client ID: $AZURE_CLIENT_ID"
echo "Tenant ID: $AZURE_TENANT_ID"
echo "Subscription ID: $AZURE_SUBSCRIPTION_ID"
echo "V2Ray Client ID: $V2RAY_CLIENT_ID"

# 2. 测试Azure连接
python -c "
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
import os

credential = ClientSecretCredential(
    tenant_id=os.environ['AZURE_TENANT_ID'],
    client_id=os.environ['AZURE_CLIENT_ID'],
    client_secret=os.environ['AZURE_CLIENT_SECRET']
)

client = ResourceManagementClient(credential, os.environ['AZURE_SUBSCRIPTION_ID'])
print('✅ Azure连接成功')
print('订阅:', client.config.subscription_id)
"
```

## 下一步

配置完成后，你可以:
1. 使用提供的环境变量部署AZ-Ray应用
2. 参考 [群晖部署指南](synology-deployment.md) 在NAS上运行
3. 配置客户端设备使用SOCKS5代理
