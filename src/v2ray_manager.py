import asyncio
import json
import logging
import subprocess
import tempfile
import os
from pathlib import Path
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
        
        # 设置GeoIP文件路径（项目内置）
        project_root = Path(__file__).parent.parent
        self.geoip_file = str(project_root / "data" / "geoip.dat")
        self.geosite_file = str(project_root / "data" / "geosite.dat")

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
                        "network": "ws",
                        "wsSettings": {
                            "path": self.config.v2ray_path
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
                        "domain": self.config.domain_list,  # 用户自定义域名
                        "outboundTag": "proxy"
                    },
                    {
                        "type": "field",
                        "ip": [
                            "geoip:private",      # 私有网络
                            "geoip:cn"            # 中国大陆IP
                        ],
                        "outboundTag": "direct"
                    },
                    {
                        "type": "field",
                        "outboundTag": "proxy"  # 默认走代理
                    }
                ]
            }
        }

        # 如果GeoIP和GeoSite文件存在，添加到配置中
        if os.path.exists(self.geoip_file) and os.path.exists(self.geosite_file):
            client_config["asset"] = {
                "geoip_file": self.geoip_file,
                "geosite_file": self.geosite_file
            }
            logger.info(f"使用本地GeoIP文件: {self.geoip_file}")
            logger.info(f"使用本地GeoSite文件: {self.geosite_file}")
        else:
            logger.warning("GeoIP/GeoSite文件不存在，请运行 ./scripts/update-geo-data.sh 下载")

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
