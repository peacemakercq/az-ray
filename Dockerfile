FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装V2Ray
RUN wget -O /tmp/v2ray.zip https://github.com/v2fly/v2ray-core/releases/latest/download/v2ray-linux-64.zip \
    && unzip /tmp/v2ray.zip -d /tmp/v2ray \
    && mv /tmp/v2ray/v2ray /usr/local/bin/ \
    && chmod +x /usr/local/bin/v2ray \
    && rm -rf /tmp/v2ray*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/

# 创建非root用户
RUN useradd -m -u 1000 azray && chown -R azray:azray /app
USER azray

# 暴露SOCKS5端口
EXPOSE 1080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f --socks5 127.0.0.1:1080 http://www.google.com || exit 1

# 启动应用
CMD ["python", "-m", "src.main"]
