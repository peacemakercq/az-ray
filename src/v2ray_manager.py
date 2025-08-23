import asyncio
import json
import logging
import subprocess
import tempfile
import os
from typing import Optional

from .config import Config
from .azure_manager import AzureManager

logger = logging.getLogger(__name__)


class V2RayManager:
    """V2Ray代理管理器"""

    def __init__(self, config: Config, azure_manager: AzureManager):
        self.config = config
        self.azure_manager = azure_manager
        self.process: Optional[subprocess.Popen] = None
        self.config_file: Optional[str] = None

    async def initialize(self):
        """初始化V2Ray管理器"""
        logger.info("正在初始化V2Ray管理器...")

        # 生成本地V2Ray客户端配置
        await self._generate_client_config()

        logger.info("V2Ray管理器初始化完成")

    async def _generate_client_config(self):
        """生成V2Ray客户端配置"""
        # 获取Azure容器的IP地址（优先使用IP，避免DNS封锁）
        server_ip = await self.azure_manager.get_container_ip()
        if not server_ip:
            # 如果IP不可用，fallback到FQDN
            server_address = await self.azure_manager.get_container_fqdn()
            if not server_address:
                raise RuntimeError("无法获取Azure容器的IP地址或FQDN")
            logger.warning("IP地址不可用，使用FQDN作为fallback")
        else:
            server_address = server_ip
            logger.info(f"使用容器IP地址: {server_ip}")

        # 生成客户端配置
        client_config = {
            "log": {
                "loglevel": "info"
            },
            "inbounds": [
                {
                    "tag": "socks-in",
                    "port": self.config.socks5_port,
                    "protocol": "socks",
                    "settings": {
                        "auth": "noauth",
                        "udp": True
                    }
                }
            ],
            "outbounds": [
                {
                    "tag": "proxy",
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": server_address,
                                "port": self.config.v2ray_port,
                                "users": [
                                    {
                                        "id": self.config.v2ray_client_id,
                                        "alterId": 0
                                    }
                                ]
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "tcpSettings": {
                            "header": {
                                "type": "http",
                                "request": {
                                    "version": "1.1",
                                    "method": "GET",
                                    "path": ["/"],
                                    "headers": {
                                        "Host": ["www.baidu.com", "www.bing.com"],
                                        "User-Agent": [
                                            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                                            "(KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36",
                                            "Mozilla/5.0 (iPhone; CPU iPhone OS 10_0_2 like Mac OS X) "
                                            "AppleWebKit/601.1 (KHTML, like Gecko) CriOS/53.0.2785.109 "
                                            "Mobile/14A456 Safari/601.1.46"
                                        ],
                                        "Accept-Encoding": ["gzip, deflate"],
                                        "Connection": ["keep-alive"],
                                        "Pragma": "no-cache"
                                    }
                                }
                            }
                        },
                        "security": "none"
                    }
                },
                {
                    "tag": "direct",
                    "protocol": "freedom",
                    "settings": {}
                }
            ],
            "routing": {
                "domainStrategy": "IPOnDemand",
                "rules": [
                    {
                        "type": "field",
                        "domain": self.config.domain_list,
                        "outboundTag": "proxy"
                    },
                    {
                        "type": "field",
                        "network": "udp,tcp",
                        "outboundTag": "direct"
                    }
                ]
            }
        }

        # 保存配置到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(client_config, f, indent=2)
            self.config_file = f.name

        logger.info(f"V2Ray客户端配置已生成: {self.config_file}")

    async def start(self):
        """启动V2Ray代理"""
        if self.process and self.process.poll() is None:
            logger.warning("V2Ray已在运行")
            return

        logger.info(f"正在启动V2Ray代理，监听端口: {self.config.socks5_port}")

        try:
            # 启动V2Ray进程
            self.process = subprocess.Popen(
                ["v2ray", "run", "-c", self.config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # 等待一下确保进程启动
            await asyncio.sleep(2)

            # 检查进程是否正常运行
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise RuntimeError(f"V2Ray启动失败: {stderr}")

            logger.info("V2Ray代理启动成功")

        except FileNotFoundError:
            logger.error("V2Ray可执行文件未找到，请确保已安装V2Ray")
            raise
        except Exception as e:
            logger.error(f"启动V2Ray失败: {e}")
            raise

    async def stop(self):
        """停止V2Ray代理"""
        if self.process:
            logger.info("正在停止V2Ray代理...")
            self.process.terminate()

            try:
                # 等待进程结束
                await asyncio.wait_for(
                    asyncio.to_thread(self.process.wait),
                    timeout=10
                )
            except asyncio.TimeoutError:
                logger.warning("V2Ray进程未响应，强制终止")
                self.process.kill()
                await asyncio.to_thread(self.process.wait)

            self.process = None
            logger.info("V2Ray代理已停止")

        # 清理临时配置文件
        if self.config_file and os.path.exists(self.config_file):
            os.unlink(self.config_file)
            self.config_file = None

    async def restart(self):
        """重启V2Ray代理"""
        logger.info("正在重启V2Ray代理...")
        await self.stop()

        # 重新生成配置（可能domains或者FQDN已变化）
        await self._generate_client_config()

        await self.start()
        logger.info("V2Ray代理重启完成")

    def is_running(self) -> bool:
        """检查V2Ray是否正在运行"""
        return self.process is not None and self.process.poll() is None
