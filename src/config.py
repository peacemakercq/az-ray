import os
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """应用配置类"""

    # Azure配置
    azure_client_id: str
    azure_client_secret: str
    azure_tenant_id: str
    azure_subscription_id: Optional[str] = None
    azure_resource_group: str = "az-ray-rg"
    azure_location: str = "southeastasia"

    # V2Ray配置
    v2ray_client_id: Optional[str] = None
    v2ray_port: int = 443
    v2ray_path: str = "/v2ray"

    # 本地配置
    socks5_port: int = 1080
    health_check_interval: int = 600  # 10分钟

    # Azure存储配置
    storage_account_name: str = "azraystore"
    storage_file_share_name: str = "v2ray-config"
    storage_file_name: str = "config.json"

    # Azure容器实例配置
    container_group_name: str = "azraycg"
    container_name: str = "azrayci"
    container_image: str = "v2fly/v2fly-core:latest"

    # 被墙域名列表
    blocked_domains: Optional[list[str]] = None

    def __init__(self):
        # 从环境变量读取必需配置
        self.azure_client_id = self._get_env_required("AZURE_CLIENT_ID")
        self.azure_client_secret = self._get_env_required(
            "AZURE_CLIENT_SECRET")
        self.azure_tenant_id = self._get_env_required("AZURE_TENANT_ID")
        self.v2ray_client_id = self._get_env_required("V2RAY_CLIENT_ID")

        # 可选配置
        self.azure_subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        self.azure_resource_group = os.getenv(
            "AZURE_RESOURCE_GROUP", self.azure_resource_group)
        self.azure_location = os.getenv("AZURE_LOCATION", self.azure_location)

        self.socks5_port = int(os.getenv("SOCKS5_PORT", self.socks5_port))
        self.health_check_interval = int(os.getenv(
            "HEALTH_CHECK_INTERVAL", self.health_check_interval))

        # 验证V2Ray客户端ID格式
        try:
            uuid.UUID(self.v2ray_client_id)
        except ValueError:
            raise ValueError(f"无效的V2RAY_CLIENT_ID格式: {self.v2ray_client_id}")

        # 默认被墙域名列表
        if self.blocked_domains is None:
            self.blocked_domains = [
                "google.com",
                "youtube.com",
                "facebook.com",
                "twitter.com",
                "instagram.com",
                "github.com",
                "gmail.com",
                "blogspot.com",
                "wikipedia.org",
                "t.co",
                "bit.ly",
                "dropbox.com",
                "pinterest.com",
                "tumblr.com",
                "reddit.com",
                "vimeo.com",
                "dailymotion.com",
                "wordpress.com",
                "flickr.com",
                "imgur.com"
            ]

    def _get_env_required(self, key: str) -> str:
        """获取必需的环境变量"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"环境变量 {key} 是必需的")
        return value

    @property
    def v2ray_config_url(self) -> str:
        """获取V2Ray配置的Azure Storage URL"""
        return (
            f"https://{self.storage_account_name}.file.core.windows.net/"
            f"{self.storage_file_share_name}/{self.storage_file_name}"
        )

    def get_unique_name(self, base_name: str) -> str:
        """生成唯一的资源名称"""
        # 使用客户端ID的前8位作为后缀确保唯一性
        suffix = self.v2ray_client_id.replace('-', '')[:8].lower()
        return f"{base_name}-{suffix}"
