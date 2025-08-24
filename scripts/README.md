# Scripts Directory

本目录包含项目的各种脚本工具。

## 📁 脚本列表

### `update-geo-data.sh`
更新 V2Ray 的 GeoIP 和 GeoSite 数据文件。

```bash
# 运行更新
./scripts/update-geo-data.sh

# 或使用 Makefile
make update-geo
```

### `deploy.sh`
部署脚本，用于部署应用到生产环境。

```bash
# 直接运行
./scripts/deploy.sh

# 或使用 Makefile  
make deploy
```

## 🔧 使用说明

所有脚本都可以通过项目根目录的 `Makefile` 来调用，推荐使用 `make` 命令：

```bash
# 查看所有可用命令
make help

# 更新 GeoIP 数据
make update-geo

# 部署到 Azure
make deploy
```

这样更方便记忆和使用。
