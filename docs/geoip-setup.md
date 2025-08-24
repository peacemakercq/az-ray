# GeoIP/GeoSite 数据管理

本项目使用 V2Ray 的 GeoIP 和 GeoSite 数据来实现智能路由。

## 📁 文件位置

- `data/geoip.dat` - GeoIP 数据库，用于IP地址地理位置匹配
- `data/geosite.dat` - GeoSite 数据库，用于域名分类匹配

## 🔄 首次设置

由于 GitHub releases 可能被封锁，请手动下载并放置文件：

### 方法1: 使用更新脚本（推荐）

```bash
# 如果网络可达 GitHub
./scripts/update-geo-data.sh
```

### 方法2: 手动下载

如果脚本失败或网络被封锁，请：

1. **下载 GeoIP 数据**：
   - 主地址: https://github.com/v2fly/geoip/releases/latest/download/geoip.dat
   - 备用地址: https://raw.githubusercontent.com/v2fly/geoip/release/geoip.dat
   - 保存为: `data/geoip.dat`

2. **下载 GeoSite 数据**：
   - 主地址: https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat
   - 备用地址: https://raw.githubusercontent.com/v2fly/domain-list-community/release/dlc.dat
   - 保存为: `data/geosite.dat` (注意重命名)

### 方法3: 使用代理或镜像

```bash
# 使用代理
export https_proxy=http://127.0.0.1:1080
./scripts/update-geo-data.sh

# 或者使用镜像站（如果有）
curl -L -o data/geoip.dat "https://mirror.example.com/geoip.dat"
curl -L -o data/geosite.dat "https://mirror.example.com/dlc.dat"
```

## 🔄 定期更新

建议每月更新一次 GeoIP/GeoSite 数据：

```bash
# 更新数据
./scripts/update-geo-data.sh

# 提交到仓库
git add data/
git commit -m "update: refresh GeoIP/GeoSite data"

# 重启应用
python __main__.py
```

## 📊 文件大小参考

- `geoip.dat`: 约 3-5MB
- `geosite.dat`: 约 1-2MB

## 🎯 路由规则

当前配置的路由逻辑：

1. **GeoSite 规则** - 知名网站全家桶走代理：
   - `geosite:google` - Google 生态系统
   - `geosite:youtube` - YouTube 相关域名
   - `geosite:facebook` - Facebook 生态系统
   - `geosite:twitter` - Twitter 相关域名
   - `geosite:telegram` - Telegram 相关域名
   - `geosite:github` - GitHub 相关域名

2. **用户域名规则** - 自定义域名列表走代理

3. **GeoIP 规则** - 内网和国内IP直连：
   - `geoip:private` - 私有网络地址
   - `geoip:cn` - 中国大陆IP段

4. **默认规则** - 其他所有流量走代理

## ⚠️ 注意事项

- 确保 V2Ray 版本支持 GeoIP/GeoSite 功能
- 文件损坏会导致路由失效，请保持备份
- 更新后需要重启 V2Ray 进程以生效
