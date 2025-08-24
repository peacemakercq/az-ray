import os
import uuid
import logging
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
    # Azure存储配置
    storage_account_name: str = "azraystore"
    storage_file_share_name: str = "v2ray-config"
    storage_file_name: str = "config.json"
    # Azure容器实例配置
    container_group_name: str = "azraycontainer"
    container_name: str = "azray"
    container_image: str = "v2fly/v2fly-core:latest"

    # V2Ray配置
    v2ray_client_id: Optional[str] = None
    v2ray_port: int = 443  # WebSocket端口
    v2ray_path: str = "/azrayws"  # WebSocket路径

    # 本地配置
    socks5_port: int = 1080
    health_check_interval: int = 600  # 10分钟

    # 转发域名列表
    domain_list: Optional[list[str]] = None

    # 额外转发域名文件路径
    domain_file: Optional[str] = None

    def __init__(self):
        # 存储域名文件路径
        self.domain_file = os.getenv("DOMAIN_FILE")
        
        # 从环境变量读取必需配置
        self.azure_client_id = self._get_env_required("AZURE_CLIENT_ID")
        self.azure_client_secret = self._get_env_required(
            "AZURE_CLIENT_SECRET")
        self.azure_tenant_id = self._get_env_required("AZURE_TENANT_ID")
        self.azure_subscription_id = self._get_env_required("AZURE_SUBSCRIPTION_ID")
        self.v2ray_client_id = self._get_env_required("V2RAY_CLIENT_ID")

        # 可选配置
        self.azure_resource_group = os.getenv("AZURE_RESOURCE_GROUP", self.azure_resource_group)
        self.azure_location = os.getenv("AZURE_LOCATION", self.azure_location)

        self.v2ray_port = int(os.getenv("V2RAY_PORT", self.v2ray_port))
        self.socks5_port = int(os.getenv("SOCKS5_PORT", self.socks5_port))
        self.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", self.health_check_interval))

        # 初始化转发域名列表
        self._initialize_domain_list()

        # 验证V2Ray客户端ID格式
        try:
            uuid.UUID(self.v2ray_client_id)
        except ValueError:
            raise ValueError(f"无效的V2RAY_CLIENT_ID格式: {self.v2ray_client_id}")

    def _initialize_domain_list(self):
        """初始化转发域名列表"""

        # 默认列表
        domain_list = [
            "google.com",
            "youtube.com",
            "facebook.com",
            "twitter.com",
            "instagram.com",
            "github.com",
            "docker.com",
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

        # 从文件读取额外(如果指定了文件)
        if self.domain_file:
            domain_list.extend(self._load_domains_from_file(self.domain_file))

        # google.com -> domain:google.com以匹配所有子域名
        self.domain_list = [f"domain:{d}" for d in domain_list]

    def reload_domain_list(self):
        """重新加载域名列表"""
        logging.info("重新加载域名列表...")
        old_count = len(self.domain_list) if self.domain_list else 0
        self._initialize_domain_list()
        new_count = len(self.domain_list)
        logging.info(f"域名列表重新加载完成: {old_count} -> {new_count}")
        return self.domain_list

    def _load_domains_from_file(self, filepath: str) -> list[str]:
        """从文件加载域名列表"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                domains = []
                for line_num, line in enumerate(f, 1):
                    # 去除空白字符
                    domain = line.strip()
                    # 跳过空行和注释行
                    if not domain or domain.startswith('#'):
                        continue
                    # 简单的域名格式验证
                    if self._is_valid_domain(domain):
                        domains.append(domain)
                    else:
                        logging.warning(
                            f"跳过无效域名 (行 {line_num}): {domain}"
                        )
                
                logging.info(f"从文件 {filepath} 加载了 {len(domains)} 个域名")
                return domains
                
        except Exception as e:
            raise ValueError(f"读取域名文件失败: {e}")

    def _is_valid_domain(self, domain: str) -> bool:
        """简单的域名格式验证"""
        import re
        # 基本的域名格式检查
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(domain_pattern, domain)) and len(domain) <= 253

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
        """生成唯一的资源名称（不使用连字符）"""
        suffix = self.v2ray_client_id.replace('-', '')[:8].lower()
        return f"{base_name.lower()}{suffix}"

    def get_unique_dns_label(self) -> str:
        """生成唯一的DNS标签名称（适用于Container Instance）"""
        return self.get_unique_name(self.container_group_name)

    def get_unique_storage_name(self) -> str:
        """
        生成全局唯一的存储账户名

        注意：此方法通过在 storage_account_name 后附加 v2ray_client_id 的前8位（去除连字符）来保证唯一性。
        请确保 v2ray_client_id 在不同部署间唯一，否则可能导致存储账户名冲突。
        """
        return self.get_unique_name(self.storage_account_name)
