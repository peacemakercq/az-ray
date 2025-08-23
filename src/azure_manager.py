import json
import logging
from typing import Optional, Dict, Any
from azure.identity import ClientSecretCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.fileshare import ShareFileClient, ShareClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

from .config import Config

logger = logging.getLogger(__name__)


class AzureManager:
    """Azure资源管理器"""

    def __init__(self, config: Config):
        self.config = config
        self.credential: Optional[ClientSecretCredential] = None
        self.resource_client: Optional[ResourceManagementClient] = None
        self.storage_client: Optional[StorageManagementClient] = None
        self.container_client: Optional[ContainerInstanceManagementClient] = None
        self.storage_account_key: Optional[str] = None

    async def initialize(self):
        """初始化Azure客户端"""
        logger.info("正在初始化Azure客户端...")

        # 抑制Azure SDK的详细日志
        self._suppress_azure_logs()

        # 创建凭据
        self.credential = ClientSecretCredential(
            tenant_id=self.config.azure_tenant_id,
            client_id=self.config.azure_client_id,
            client_secret=self.config.azure_client_secret
        )

        # 获取订阅ID（如果未提供则使用默认）
        if not self.config.azure_subscription_id:
            # 这里可以添加获取默认订阅的逻辑
            raise ValueError("需要提供AZURE_SUBSCRIPTION_ID")

        # 初始化管理客户端
        self.resource_client = ResourceManagementClient(
            self.credential,
            self.config.azure_subscription_id
        )
        self.storage_client = StorageManagementClient(
            self.credential,
            self.config.azure_subscription_id
        )
        self.container_client = ContainerInstanceManagementClient(
            self.credential,
            self.config.azure_subscription_id
        )

        logger.info("Azure客户端初始化完成")

    @staticmethod
    def _suppress_azure_logs():
        """抑制Azure SDK的详细日志"""
        # Azure Core HTTP日志
        logging.getLogger(
            'azure.core.pipeline.policies.http_logging_policy'
        ).setLevel(logging.WARNING)

        # Azure Identity日志
        logging.getLogger('azure.identity').setLevel(logging.WARNING)

        # Azure管理客户端日志
        logging.getLogger('azure.mgmt').setLevel(logging.WARNING)

        # Azure存储日志
        logging.getLogger('azure.storage').setLevel(logging.WARNING)

        # urllib3日志（Azure SDK内部使用）
        logging.getLogger('urllib3').setLevel(logging.WARNING)

        # Azure Core日志
        logging.getLogger('azure.core').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

        # Azure Core日志
        logging.getLogger('azure.core').setLevel(logging.WARNING)

    async def ensure_resources(self):
        """确保所有必需的Azure资源存在"""
        logger.info("正在检查Azure资源...")

        # 确保资源组存在
        await self._ensure_resource_group()

        # 确保存储账户存在
        await self._ensure_storage_account()

        # 确保文件共享存在
        await self._ensure_file_share()

        # 确保V2Ray配置文件存在
        await self._ensure_v2ray_config()

        # 确保容器实例存在
        await self._ensure_container_instance()

        logger.info("所有Azure资源检查完成")

    async def _ensure_resource_group(self):
        """确保资源组存在"""
        try:
            self.resource_client.resource_groups.get(
                self.config.azure_resource_group)
            logger.info(f"资源组 {self.config.azure_resource_group} 已存在")
        except ResourceNotFoundError:
            logger.info(f"正在创建资源组 {self.config.azure_resource_group}...")
            self.resource_client.resource_groups.create_or_update(
                self.config.azure_resource_group,
                {"location": self.config.azure_location}
            )
            logger.info(f"资源组 {self.config.azure_resource_group} 创建完成")

    async def _ensure_storage_account(self):
        """确保存储账户存在"""
        storage_name = self.config.get_unique_storage_name()

        try:
            self.storage_client.storage_accounts.get_properties(
                self.config.azure_resource_group,
                storage_name
            )
            logger.info(f"存储账户 {storage_name} 已存在")
        except ResourceNotFoundError:
            logger.info(f"正在创建存储账户 {storage_name}...")

            # 创建存储账户
            poller = self.storage_client.storage_accounts.begin_create(
                self.config.azure_resource_group,
                storage_name,
                {
                    "sku": {"name": "Standard_LRS"},
                    "kind": "StorageV2",
                    "location": self.config.azure_location,
                    "encryption": {
                        "services": {
                            "file": {"enabled": True}
                        },
                        "key_source": "Microsoft.Storage"
                    }
                }
            )
            poller.wait()
            logger.info(f"存储账户 {storage_name} 创建完成")

        # 获取存储账户密钥
        keys = self.storage_client.storage_accounts.list_keys(
            self.config.azure_resource_group,
            storage_name
        )
        self.storage_account_key = keys.keys[0].value

        # 更新配置中的存储账户名
        self.config.storage_account_name = storage_name

    async def _ensure_file_share(self):
        """确保文件共享存在"""
        try:
            account_url = (
                f"https://{self.config.storage_account_name}"
                f".file.core.windows.net"
            )
            share_client = ShareClient(
                account_url=account_url,
                share_name=self.config.storage_file_share_name,
                credential=self.storage_account_key
            )

            # 创建文件共享（如果不存在）
            try:
                share_client.create_share()
                logger.info(f"文件共享 {self.config.storage_file_share_name} 创建完成")
            except ResourceExistsError:
                logger.info(f"文件共享 {self.config.storage_file_share_name} 已存在")

        except Exception as e:
            logger.error(f"创建文件共享失败: {e}")
            raise

    async def _ensure_v2ray_config(self):
        """确保V2Ray配置文件存在"""
        try:
            account_url = (
                f"https://{self.config.storage_account_name}"
                f".file.core.windows.net"
            )
            file_client = ShareFileClient(
                account_url=account_url,
                share_name=self.config.storage_file_share_name,
                file_path=self.config.storage_file_name,
                credential=self.storage_account_key
            )

            # 检查文件是否存在
            try:
                file_client.get_file_properties()
                logger.info("V2Ray配置文件已存在")
            except ResourceNotFoundError:
                # 生成并上传配置文件
                logger.info("正在生成V2Ray配置文件...")
                config_content = self._generate_v2ray_config()

                file_client.upload_file(
                    data=json.dumps(config_content, indent=2),
                    length=None
                )
                logger.info("V2Ray配置文件上传完成")

        except Exception as e:
            logger.error(f"处理V2Ray配置文件失败: {e}")
            raise

    def _generate_v2ray_config(self) -> Dict[str, Any]:
        """生成V2Ray服务器配置"""
        return {
            "log": {
                "loglevel": "info"
            },
            "inbounds": [
                {
                    "port": self.config.v2ray_port,
                    "protocol": "vmess",
                    "settings": {
                        "clients": [
                            {
                                "id": self.config.v2ray_client_id,
                                "alterId": 0
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "ws",
                        "wsSettings": {
                            "path": self.config.v2ray_path
                        }
                    }
                }
            ],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "settings": {}
                }
            ]
        }

    async def _ensure_container_instance(self):
        """确保容器实例存在"""
        try:
            container_group = self.container_client.container_groups.get(
                self.config.azure_resource_group,
                self.config.container_group_name
            )
            logger.info(f"容器实例 {self.config.container_group_name} 已存在")

            # 检查容器状态
            if container_group.instance_view.state != "Running":
                logger.info("容器实例未运行，正在启动...")
                await self.restart_container()

        except ResourceNotFoundError:
            logger.info(f"正在创建容器实例 {self.config.container_group_name}...")
            await self._create_container_instance()

    async def _create_container_instance(self):
        """创建容器实例"""
        container_group = {
            "location": self.config.azure_location,
            "containers": [
                {
                    "name": self.config.container_name,
                    "image": self.config.container_image,
                    "resources": {
                        "requests": {
                            "cpu": 1,
                            "memory_in_gb": 1
                        }
                    },
                    "ports": [
                        {
                            "port": self.config.v2ray_port,
                            "protocol": "TCP"
                        }
                    ],
                    "volume_mounts": [
                        {
                            "name": "v2ray-config",
                            "mount_path": "/etc/v2ray",
                            "read_only": True
                        }
                    ],
                    "command": ["v2ray", "-config=/etc/v2ray/config.json"]
                }
            ],
            "os_type": "Linux",
            "ip_address": {
                "type": "Public",
                "ports": [
                    {
                        "port": self.config.v2ray_port,
                        "protocol": "TCP"
                    }
                ],
                "dns_name_label": self.config.get_unique_dns_label()
            },
            "volumes": [
                {
                    "name": "v2ray-config",
                    "azure_file": {
                        "share_name": self.config.storage_file_share_name,
                        "storage_account_name": self.config.storage_account_name,
                        "storage_account_key": self.storage_account_key,
                        "read_only": True
                    }
                }
            ],
            "restart_policy": "Always"
        }

        poller = self.container_client.container_groups.begin_create_or_update(
            self.config.azure_resource_group,
            self.config.container_group_name,
            container_group
        )

        result = poller.result()
        fqdn = result.ip_address.fqdn if result.ip_address.fqdn else "未生成"
        ip = result.ip_address.ip if result.ip_address else "未分配"
        logger.info(f"容器实例创建完成，IP: {ip}, FQDN: {fqdn}")
        return result

    async def restart_container(self):
        """重启容器实例"""
        logger.info("正在重启容器实例...")

        try:
            # 停止容器组
            self.container_client.container_groups.stop(
                self.config.azure_resource_group,
                self.config.container_group_name
            )

            # 启动容器组
            self.container_client.container_groups.start(
                self.config.azure_resource_group,
                self.config.container_group_name
            )

            logger.info("容器实例重启完成")

        except Exception as e:
            logger.error(f"重启容器实例失败: {e}")
            raise

    async def get_container_fqdn(self) -> Optional[str]:
        """获取容器的FQDN"""
        try:
            container_group = self.container_client.container_groups.get(
                self.config.azure_resource_group,
                self.config.container_group_name
            )
            return container_group.ip_address.fqdn if container_group.ip_address else None
        except Exception:
            return None

    async def get_container_ip_info(self) -> Dict[str, Optional[str]]:
        """获取容器的IP信息"""
        try:
            container_group = self.container_client.container_groups.get(
                self.config.azure_resource_group,
                self.config.container_group_name
            )
            if container_group.ip_address:
                return {
                    "ip": container_group.ip_address.ip,
                    "fqdn": container_group.ip_address.fqdn,
                    "dns_name_label": getattr(
                        container_group.ip_address, 'dns_name_label', None
                    )
                }
            return {"ip": None, "fqdn": None, "dns_name_label": None}
        except Exception:
            return {"ip": None, "fqdn": None, "dns_name_label": None}
