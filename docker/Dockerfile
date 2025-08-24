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

# 下载GeoIP和GeoSite数据
RUN wget -O /usr/local/bin/geoip.dat https://github.com/v2fly/geoip/releases/latest/download/geoip.dat \
    && wget -O /usr/local/bin/geosite.dat https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/
COPY __main__.py ./

# 创建非root用户
RUN useradd -m -u 1000 azray && chown -R azray:azray /app
USER azray

# 暴露SOCKS5和HTTP端口
EXPOSE 1080 1081

# 启动应用
CMD ["python", "__main__.py"]
