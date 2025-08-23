import pytest
from unittest.mock import Mock, AsyncMock
from src.config import Config
from src.azure_manager import AzureManager


@pytest.fixture
def mock_config():
    """模拟配置"""
    config = Mock(spec=Config)
    config.azure_client_id = "test-client-id"
    config.azure_client_secret = "test-client-secret"
    config.azure_tenant_id = "test-tenant-id"
    config.azure_subscription_id = "test-subscription-id"
    config.azure_resource_group = "test-rg"
    config.azure_location = "eastus"
    config.v2ray_client_id = "550e8400-e29b-41d4-a716-446655440000"
    config.storage_account_name = "teststore"
    config.storage_file_share_name = "test-config"
    config.storage_file_name = "config.json"
    config.container_group_name = "test-container"
    config.container_name = "v2ray"
    config.container_image = "v2fly/v2fly-core:latest"
    config.v2ray_port = 9088
    config.v2ray_path = "/v2ray"
    config.get_unique_name = Mock(side_effect=lambda x: f"{x}-test")
    return config


@pytest.fixture
def mock_azure_manager(mock_config):
    """模拟Azure管理器"""
    manager = AzureManager(mock_config)
    manager.credential = Mock()
    manager.resource_client = Mock()
    manager.storage_client = Mock()
    manager.container_client = Mock()
    manager.storage_account_key = "test-key"
    return manager


class TestAzureManager:
    """Azure管理器测试"""

    @pytest.mark.asyncio
    async def test_initialize(self, mock_config):
        """测试初始化"""
        manager = AzureManager(mock_config)

        # 模拟初始化过程
        with pytest.raises(ValueError, match="需要提供AZURE_SUBSCRIPTION_ID"):
            mock_config.azure_subscription_id = None
            await manager.initialize()

    @pytest.mark.asyncio
    async def test_ensure_resources(self, mock_azure_manager):
        """测试资源确保"""
        # 模拟所有方法
        mock_azure_manager._ensure_resource_group = AsyncMock()
        mock_azure_manager._ensure_storage_account = AsyncMock()
        mock_azure_manager._ensure_file_share = AsyncMock()
        mock_azure_manager._ensure_v2ray_config = AsyncMock()
        mock_azure_manager._ensure_container_instance = AsyncMock()

        await mock_azure_manager.ensure_resources()

        # 验证所有方法都被调用
        mock_azure_manager._ensure_resource_group.assert_called_once()
        mock_azure_manager._ensure_storage_account.assert_called_once()
        mock_azure_manager._ensure_file_share.assert_called_once()
        mock_azure_manager._ensure_v2ray_config.assert_called_once()
        mock_azure_manager._ensure_container_instance.assert_called_once()

    def test_generate_v2ray_config(self, mock_azure_manager):
        """测试V2Ray配置生成"""
        config = mock_azure_manager._generate_v2ray_config()

        assert "log" in config
        assert "inbounds" in config
        assert "outbounds" in config
        assert config["inbounds"][0]["port"] == 9088
        assert config["inbounds"][0]["protocol"] == "vmess"
        client_id = config["inbounds"][0]["settings"]["clients"][0]["id"]
        assert client_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_v2ray_port_env_override(self):
        """测试V2RAY_PORT环境变量override功能"""
        import os
        
        # 保存原始环境变量
        original_port = os.environ.get("V2RAY_PORT")
        
        try:
            # 测试默认端口
            os.environ.pop("V2RAY_PORT", None)
            
            # 设置必需的环境变量
            os.environ["AZURE_CLIENT_ID"] = "test-client"
            os.environ["AZURE_CLIENT_SECRET"] = "test-secret"
            os.environ["AZURE_TENANT_ID"] = "test-tenant"
            os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription"
            os.environ["V2RAY_CLIENT_ID"] = "550e8400-e29b-41d4-a716-446655440000"
            
            config = Config()
            assert config.v2ray_port == 9088, f"期望默认端口9088，实际{config.v2ray_port}"
            
            # 测试环境变量override
            os.environ["V2RAY_PORT"] = "8443"
            config2 = Config()
            assert config2.v2ray_port == 8443, f"期望override端口8443，实际{config2.v2ray_port}"
            
        finally:
            # 恢复环境变量
            if original_port:
                os.environ["V2RAY_PORT"] = original_port
            else:
                os.environ.pop("V2RAY_PORT", None)
                
            # 清理测试用的环境变量
            test_vars = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID",
                         "AZURE_SUBSCRIPTION_ID", "V2RAY_CLIENT_ID"]
            for var in test_vars:
                os.environ.pop(var, None)
