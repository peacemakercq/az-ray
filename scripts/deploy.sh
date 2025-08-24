#!/bin/bash

# AZ-Ray 快速部署脚本

set -e

echo "🚀 AZ-Ray 快速部署脚本"
echo "=========================="

# 检查环境变量
required_vars=("AZURE_CLIENT_ID" "AZURE_CLIENT_SECRET" "AZURE_TENANT_ID" "V2RAY_CLIENT_ID")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ 错误: 环境变量 $var 未设置"
        echo "请设置所有必需的环境变量后重试"
        exit 1
    fi
done

echo "✅ 环境变量检查通过"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装"
    echo "请先安装Docker后重试"
    exit 1
fi

echo "✅ Docker 检查通过"

# 拉取最新镜像
echo "📦 正在拉取最新镜像..."
docker pull ${DOCKER_IMAGE:-your_dockerhub_username/az-ray:latest}

# 停止并删除旧容器（如果存在）
if docker ps -a | grep -q az-ray; then
    echo "🛑 停止旧容器..."
    docker stop az-ray || true
    docker rm az-ray || true
fi

# 创建日志目录
mkdir -p ./logs

# 启动新容器
echo "🚀 启动容器..."
docker run -d \
    --name az-ray \
    --restart unless-stopped \
    -p ${SOCKS5_PORT:-1080}:1080 \
    -e AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
    -e AZURE_CLIENT_SECRET="$AZURE_CLIENT_SECRET" \
    -e AZURE_TENANT_ID="$AZURE_TENANT_ID" \
    -e AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}" \
    -e V2RAY_CLIENT_ID="$V2RAY_CLIENT_ID" \
    -e AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-az-ray-rg}" \
    -e AZURE_LOCATION="${AZURE_LOCATION:-eastus}" \
    -e SOCKS5_PORT="${SOCKS5_PORT:-1080}" \
    -e HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-600}" \
    -v "$(pwd)/logs:/app/logs" \
    ${DOCKER_IMAGE:-your_dockerhub_username/az-ray:latest}

echo "✅ 容器启动成功"

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查容器状态
if docker ps | grep -q az-ray; then
    echo "✅ AZ-Ray 部署成功!"
    echo "📋 服务信息:"
    echo "   - SOCKS5 代理端口: ${SOCKS5_PORT:-1080}"
    echo "   - 容器名称: az-ray"
    echo "   - 日志目录: ./logs"
    echo ""
    echo "📝 使用说明:"
    echo "   - 查看日志: docker logs az-ray"
    echo "   - 停止服务: docker stop az-ray"
    echo "   - 重启服务: docker restart az-ray"
    echo ""
    echo "🌐 代理设置:"
    echo "   - 协议: SOCKS5"
    echo "   - 地址: 127.0.0.1"
    echo "   - 端口: ${SOCKS5_PORT:-1080}"
else
    echo "❌ 容器启动失败，请查看日志:"
    docker logs az-ray
    exit 1
fi
