#!/bin/bash

# V2Ray GeoIP/GeoSite 数据更新脚本
# 使用方法: ./scripts/update-geo-data.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/data"

echo "🔄 开始更新 V2Ray GeoIP/GeoSite 数据..."

# 创建数据目录
mkdir -p "$DATA_DIR"

# 备份现有文件
if [ -f "$DATA_DIR/geoip.dat" ]; then
    echo "📦 备份现有 geoip.dat..."
    cp "$DATA_DIR/geoip.dat" "$DATA_DIR/geoip.dat.backup"
fi

if [ -f "$DATA_DIR/geosite.dat" ]; then
    echo "📦 备份现有 geosite.dat..."
    cp "$DATA_DIR/geosite.dat" "$DATA_DIR/geosite.dat.backup"
fi

# 下载 GeoIP 数据
echo "⬇️  下载 GeoIP 数据..."
if command -v curl >/dev/null 2>&1; then
    curl -L -o "$DATA_DIR/geoip.dat.tmp" "https://github.com/v2fly/geoip/releases/latest/download/geoip.dat"
elif command -v wget >/dev/null 2>&1; then
    wget -O "$DATA_DIR/geoip.dat.tmp" "https://github.com/v2fly/geoip/releases/latest/download/geoip.dat"
else
    echo "❌ 错误: 需要安装 curl 或 wget"
    exit 1
fi

# 下载 GeoSite 数据
echo "⬇️  下载 GeoSite 数据..."
if command -v curl >/dev/null 2>&1; then
    curl -L -o "$DATA_DIR/geosite.dat.tmp" "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"
elif command -v wget >/dev/null 2>&1; then
    wget -O "$DATA_DIR/geosite.dat.tmp" "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"
fi

# 验证文件大小
geoip_size=$(stat -c%s "$DATA_DIR/geoip.dat.tmp" 2>/dev/null || stat -f%z "$DATA_DIR/geoip.dat.tmp" 2>/dev/null || echo 0)
geosite_size=$(stat -c%s "$DATA_DIR/geosite.dat.tmp" 2>/dev/null || stat -f%z "$DATA_DIR/geosite.dat.tmp" 2>/dev/null || echo 0)

if [ "$geoip_size" -lt 1000000 ]; then  # 小于1MB可能是错误页面
    echo "❌ 错误: geoip.dat 文件大小异常 ($geoip_size bytes)"
    echo "可能的原因:"
    echo "  1. GitHub releases 被封锁"
    echo "  2. 网络连接问题"
    echo ""
    echo "🔧 手动下载方法:"
    echo "  1. 使用代理访问: https://github.com/v2fly/geoip/releases/latest"
    echo "  2. 下载 geoip.dat 文件到 $DATA_DIR/"
    echo "  3. 下载 dlc.dat 文件并重命名为 geosite.dat 到 $DATA_DIR/"
    echo ""
    echo "🌐 备用下载地址:"
    echo "  - https://raw.githubusercontent.com/v2fly/geoip/release/geoip.dat"
    echo "  - https://raw.githubusercontent.com/v2fly/domain-list-community/release/dlc.dat"
    
    # 清理临时文件
    rm -f "$DATA_DIR/geoip.dat.tmp" "$DATA_DIR/geosite.dat.tmp"
    exit 1
fi

if [ "$geosite_size" -lt 100000 ]; then  # 小于100KB可能是错误页面
    echo "❌ 错误: geosite.dat 文件大小异常 ($geosite_size bytes)"
    rm -f "$DATA_DIR/geoip.dat.tmp" "$DATA_DIR/geosite.dat.tmp"
    exit 1
fi

# 移动文件到正式位置
mv "$DATA_DIR/geoip.dat.tmp" "$DATA_DIR/geoip.dat"
mv "$DATA_DIR/geosite.dat.tmp" "$DATA_DIR/geosite.dat"

echo "✅ 更新完成!"
echo "📊 文件信息:"
echo "  - geoip.dat: $(du -h "$DATA_DIR/geoip.dat" | cut -f1)"
echo "  - geosite.dat: $(du -h "$DATA_DIR/geosite.dat" | cut -f1)"
echo ""
echo "🔄 请运行以下命令提交更新:"
echo "  git add data/"
echo "  git commit -m \"update: refresh GeoIP/GeoSite data\""
echo ""
echo "🚀 重启应用以使用新数据:"
echo "  python __main__.py"
