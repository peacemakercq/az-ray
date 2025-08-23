import asyncio
import json
import logging
import os
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

        # 如果指定了重新创建选项，先删除现有资源组
        if os.getenv("RECREATE_RESOURCES") == "true":
            await self._clean_existing_resources()

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

    async def _clean_existing_resources(self):
        """删除现有的资源组及其所有资源（用于重新创建）"""
        try:
            # 检查资源组是否存在
            self.resource_client.resource_groups.get(
                self.config.azure_resource_group)

            logger.warning(f"正在删除资源组 {self.config.azure_resource_group} "
                           f"及其所有资源...")

            # 删除资源组（这会自动删除其中的所有资源）
            poller = self.resource_client.resource_groups.begin_delete(
                self.config.azure_resource_group
            )

            logger.info("等待资源组删除完成...")
            poller.wait()
            logger.info(f"资源组 {self.config.azure_resource_group} 删除完成")

        except ResourceNotFoundError:
            logger.info(f"资源组 {self.config.azure_resource_group} 不存在，无需删除")
        except Exception as e:
            logger.error(f"删除资源组失败: {e}")
            raise

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

        logger.info(f"检查存储账户: {storage_name} (资源组: {self.config.azure_resource_group})")

        try:
            # 检查存储账户是否存在
            self.storage_client.storage_accounts.get_properties(
                self.config.azure_resource_group,
                storage_name
            )
            logger.info(f"存储账户 {storage_name} 已存在")

        except ResourceNotFoundError:
            logger.info(f"存储账户 {storage_name} 不存在，正在创建...")

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

            # 等待存储账户创建完成并获取结果
            poller.result()
            logger.info(f"存储账户 {storage_name} 创建完成")

            # 额外等待确保存储账户完全可用
            await asyncio.sleep(10)
            logger.info("等待存储账户完全就绪...")

        except Exception as e:
            logger.error(f"存储账户操作失败: {e}")
            logger.error(f"存储账户名: {storage_name}")
            logger.error(f"资源组: {self.config.azure_resource_group}")
            logger.error(f"位置: {self.config.azure_location}")
            raise

        # 获取存储账户密钥
        try:
            logger.info("正在获取存储账户访问密钥...")
            keys = self.storage_client.storage_accounts.list_keys(
                self.config.azure_resource_group,
                storage_name
            )
            self.storage_account_key = keys.keys[0].value
            logger.info("存储账户密钥获取成功")

        except Exception as e:
            logger.error(f"获取存储账户密钥失败: {e}")
            logger.error(f"存储账户名: {storage_name}")
            logger.error(f"资源组: {self.config.azure_resource_group}")
            raise

        # 更新配置中的存储账户名（用于后续操作）
        self.config.storage_account_name = storage_name
        logger.debug(f"存储账户名已更新为: {storage_name}")

    async def _ensure_file_share(self):
        """确保文件共享存在"""
        if not self.storage_account_key:
            raise ValueError("存储账户密钥未初始化，请先调用 _ensure_storage_account()")

        if not self.config.storage_account_name:
            raise ValueError("存储账户名未设置")

        account_url = (
            f"https://{self.config.storage_account_name}"
            f".file.core.windows.net"
        )

        logger.info("准备操作文件共享:")
        logger.info(f"  存储账户: {self.config.storage_account_name}")
        logger.info(f"  文件共享名: {self.config.storage_file_share_name}")
        logger.info(f"  账户URL: {account_url}")
        logger.info(f"  资源组: {self.config.azure_resource_group}")

        # 确保存储账户完全就绪（在某些情况下需要额外等待）
        await asyncio.sleep(5)
        logger.info("等待存储账户完全就绪...")

        try:
            # 验证存储账户是否确实存在
            logger.info("验证存储账户状态...")
            try:
                storage_props = self.storage_client.storage_accounts.get_properties(
                    self.config.azure_resource_group,
                    self.config.storage_account_name
                )
                logger.info(f"存储账户状态: {storage_props.provisioning_state}")

            except Exception as verify_error:
                logger.error(f"验证存储账户失败: {verify_error}")
                raise ValueError(f"存储账户 {self.config.storage_account_name} 不可访问: {verify_error}")

            # 创建ShareClient
            share_client = ShareClient(
                account_url=account_url,
                share_name=self.config.storage_file_share_name,
                credential=self.storage_account_key
            )

            # 先尝试获取文件共享属性来检查是否存在
            try:
                properties = share_client.get_share_properties()
                logger.info(f"文件共享 {self.config.storage_file_share_name} 已存在")
                logger.debug(f"文件共享配额: {properties.quota}GB")

            except ResourceNotFoundError:
                # 文件共享不存在，创建它
                logger.info(f"文件共享 {self.config.storage_file_share_name} 不存在，正在创建...")

                try:
                    # 设置1GB配额（只存放config.json文件）
                    share_client.create_share(quota=1)
                    logger.info(f"文件共享 {self.config.storage_file_share_name} 创建完成 (配额: 1GB)")

                except ResourceExistsError:
                    # 在检查和创建之间，文件共享被其他进程创建了
                    logger.info(f"文件共享 {self.config.storage_file_share_name} 已存在（并发创建）")

                except Exception as create_error:
                    logger.error(f"创建文件共享失败: {create_error}")
                    logger.error(f"错误类型: {type(create_error).__name__}")

                    # 提供详细的错误诊断
                    if "ResourceNotFound" in str(create_error):
                        logger.error("可能的原因:")
                        logger.error("1. 存储账户尚未完全创建完成")
                        logger.error("2. 存储账户名称不正确")
                        logger.error("3. 访问密钥无效或过期")
                        logger.error("4. 网络连接问题")

                        # 建议重试
                        logger.info("尝试等待后重试...")
                        import asyncio
                        await asyncio.sleep(15)

                        try:
                            share_client.create_share(quota=1)
                            logger.info(f"重试成功，文件共享 {self.config.storage_file_share_name} 创建完成")
                        except Exception as retry_error:
                            logger.error(f"重试也失败: {retry_error}")
                            raise
                    else:
                        raise create_error

            except Exception as check_error:
                logger.error(f"检查文件共享属性失败: {check_error}")
                logger.error(f"错误类型: {type(check_error).__name__}")

                # 如果是认证相关错误，不要尝试创建
                if "AuthenticationFailed" in str(check_error):
                    logger.error("认证失败，请检查存储账户密钥和系统时间")
                    raise

                # 如果检查失败但不是认证问题，尝试直接创建
                logger.info("尝试直接创建文件共享...")
                try:
                    share_client.create_share(quota=1)
                    logger.info(f"文件共享 {self.config.storage_file_share_name} 创建完成")
                except ResourceExistsError:
                    logger.info(f"文件共享 {self.config.storage_file_share_name} 已存在")
                except Exception as fallback_error:
                    logger.error(f"备用创建方法也失败: {fallback_error}")
                    raise

        except Exception as e:
            logger.error(f"文件共享操作失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"存储账户名: {self.config.storage_account_name}")
            logger.error(f"文件共享名: {self.config.storage_file_share_name}")
            logger.error(f"资源组: {self.config.azure_resource_group}")
            logger.error(f"账户URL: {account_url}")

            # 如果是认证相关的错误，提供调试信息
            if "AuthenticationFailed" in str(e) or "authentication" in str(e).lower():
                logger.error("认证错误调试信息:")
                logger.error(f"存储账户密钥长度: {len(self.storage_account_key) if self.storage_account_key else 0}")

                # 检查时间同步
                from datetime import datetime, timezone
                current_time = datetime.now(timezone.utc)
                logger.error(f"当前UTC时间: {current_time.isoformat()}")

            raise

    async def _ensure_v2ray_config(self):
        """确保V2Ray配置文件存在"""
        if not self.storage_account_key:
            raise ValueError("存储账户密钥未初始化，请先调用 _ensure_storage_account()")

        if not self.config.storage_account_name:
            raise ValueError("存储账户名未设置")

        account_url = (
            f"https://{self.config.storage_account_name}"
            f".file.core.windows.net"
        )

        logger.info("检查V2Ray配置文件:")
        logger.info(f"  存储账户: {self.config.storage_account_name}")
        logger.info(f"  文件共享: {self.config.storage_file_share_name}")
        logger.info(f"  文件路径: {self.config.storage_file_name}")
        logger.info(f"  账户URL: {account_url}")

        try:
            # 先验证文件共享是否存在
            logger.info("验证文件共享状态...")
            share_client = ShareClient(
                account_url=account_url,
                share_name=self.config.storage_file_share_name,
                credential=self.storage_account_key
            )

            try:
                share_props = share_client.get_share_properties()
                logger.info(f"文件共享状态正常，配额: {share_props.quota}GB")
            except Exception as share_error:
                logger.error(f"文件共享不可访问: {share_error}")
                logger.error(f"错误类型: {type(share_error).__name__}")

                # 提供详细的诊断信息
                logger.error("诊断信息:")
                logger.error(f"  存储账户名: {self.config.storage_account_name}")
                logger.error(f"  文件共享名: {self.config.storage_file_share_name}")
                logger.error(f"  账户URL: {account_url}")
                logger.error(f"  密钥长度: {len(self.storage_account_key) if self.storage_account_key else 0}")

                # 如果是ResourceNotFound错误，可能文件共享真的不存在
                if "ResourceNotFound" in str(share_error) or "NotFound" in str(share_error):
                    logger.error("文件共享似乎不存在，尝试重新创建...")
                    try:
                        # 尝试重新创建文件共享
                        await self._ensure_file_share()
                        # 重新获取属性
                        share_props = share_client.get_share_properties()
                        logger.info(f"重新创建后文件共享状态正常，配额: {share_props.quota}GB")
                    except Exception as recreate_error:
                        logger.error(f"重新创建文件共享也失败: {recreate_error}")
                        raise ValueError(f"文件共享 {self.config.storage_file_share_name} 创建失败: {recreate_error}")
                else:
                    raise ValueError(f"文件共享 {self.config.storage_file_share_name} 访问失败: {share_error}")

            # 创建文件客户端
            file_client = ShareFileClient(
                account_url=account_url,
                share_name=self.config.storage_file_share_name,
                file_path=self.config.storage_file_name,
                credential=self.storage_account_key
            )

            # 检查文件是否存在
            try:
                properties = file_client.get_file_properties()
                logger.info("V2Ray配置文件已存在")
                logger.debug(f"文件大小: {properties.size} bytes")

            except ResourceNotFoundError:
                # 文件不存在，生成并上传配置文件
                logger.info("V2Ray配置文件不存在，正在生成并上传...")

                try:
                    config_content = self._generate_v2ray_config()
                    config_json = json.dumps(config_content, indent=2)
                    config_bytes = config_json.encode('utf-8')

                    logger.info(f"配置文件大小: {len(config_bytes)} bytes")

                    # 上传文件
                    file_client.upload_file(
                        data=config_bytes,
                        length=len(config_bytes)
                    )

                    logger.info("V2Ray配置文件上传完成")

                    # 验证上传结果
                    try:
                        verify_props = file_client.get_file_properties()
                        logger.info(f"上传验证成功，文件大小: {verify_props.size} bytes")
                    except Exception as verify_error:
                        logger.warning(f"上传验证失败: {verify_error}")

                except Exception as upload_error:
                    logger.error(f"上传配置文件失败: {upload_error}")
                    logger.error(f"错误类型: {type(upload_error).__name__}")

                    if "ResourceNotFound" in str(upload_error):
                        logger.error("可能的原因:")
                        logger.error("1. 文件共享不存在或不可访问")
                        logger.error("2. 存储账户密钥无效")
                        logger.error("3. 网络连接问题")

                        # 重新检查文件共享状态
                        try:
                            share_client.get_share_properties()
                            logger.error("文件共享存在，但文件操作失败")
                        except Exception:
                            logger.error("文件共享也不可访问了")

                    raise upload_error

            except Exception as check_error:
                logger.error(f"检查配置文件失败: {check_error}")
                logger.error(f"错误类型: {type(check_error).__name__}")

                # 如果是认证错误，不要尝试上传
                if "AuthenticationFailed" in str(check_error):
                    logger.error("认证失败，请检查存储账户密钥和系统时间")
                    raise

                # 如果是ResourceNotFound，可能是文件不存在，尝试创建
                if "ResourceNotFound" in str(check_error):
                    logger.info("可能是文件不存在，尝试创建...")
                    try:
                        config_content = self._generate_v2ray_config()
                        config_json = json.dumps(config_content, indent=2)
                        config_bytes = config_json.encode('utf-8')

                        file_client.upload_file(
                            data=config_bytes,
                            length=len(config_bytes)
                        )
                        logger.info("V2Ray配置文件创建完成")
                    except Exception as create_error:
                        logger.error(f"创建配置文件也失败: {create_error}")
                        raise
                else:
                    raise check_error

        except Exception as e:
            logger.error(f"处理V2Ray配置文件失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"存储账户名: {self.config.storage_account_name}")
            logger.error(f"文件共享名: {self.config.storage_file_share_name}")
            logger.error(f"文件名: {self.config.storage_file_name}")
            logger.error(f"账户URL: {account_url}")

            # 如果是认证相关的错误，提供调试信息
            if "AuthenticationFailed" in str(e) or "authentication" in str(e).lower():
                logger.error("认证错误调试信息:")
                logger.error(f"存储账户密钥长度: {len(self.storage_account_key) if self.storage_account_key else 0}")

                # 检查时间同步
                from datetime import datetime, timezone
                current_time = datetime.now(timezone.utc)
                logger.error(f"当前UTC时间: {current_time.isoformat()}")

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
                    "command": ["v2ray", "run", "-c", "/etc/v2ray/config.json"]
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
