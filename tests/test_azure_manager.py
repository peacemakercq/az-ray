import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
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
    config.v2ray_port = 443
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
        assert config["inbounds"][0]["port"] == 443
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
            # 测试默认端口为443（WebSocket）
            assert config.v2ray_port == 443, f"期望默认端口443（WebSocket），实际{config.v2ray_port}"
            
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


class TestAzureManagerContainerOperations:
    """测试新的容器管理操作"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """测试前设置"""
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-rg"
        os.environ["V2RAY_CLIENT_ID"] = "550e8400-e29b-41d4-a716-446655440000"
        
        self.config = Config()
        self.azure_manager = AzureManager(self.config)
        
        # Cleanup after test
        yield
        test_vars = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID",
                     "AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "V2RAY_CLIENT_ID"]
        for var in test_vars:
            os.environ.pop(var, None)
    
    @patch('src.azure_manager.ContainerInstanceManagementClient')
    @pytest.mark.asyncio
    async def test_find_existing_containers(self, mock_client_class):
        """测试查找现有容器"""
        # 模拟客户端
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        self.azure_manager.container_client = mock_client
        
        # 模拟容器列表 - 使用正确的前缀
        mock_container1 = Mock()
        mock_container1.name = "azraycontainer-20240101120000"
        mock_container1.location = "eastus"
        mock_container1.instance_view.current_state.state = "Running"
        
        mock_container2 = Mock()
        mock_container2.name = "azraycontainer-20240101130000"
        mock_container2.location = "eastus"
        mock_container2.instance_view.current_state.state = "Succeeded"
        
        mock_container3 = Mock()
        mock_container3.name = "other-container"
        mock_container3.location = "eastus"
        mock_container3.instance_view.current_state.state = "Running"
        
        mock_client.container_groups.list_by_resource_group.return_value = [
            mock_container1, mock_container2, mock_container3
        ]
        
        # 测试查找
        containers = await self.azure_manager._find_existing_containers()
        
        # 验证结果
        assert len(containers) == 2
        assert containers[0].name == "azraycontainer-20240101120000"
        assert containers[1].name == "azraycontainer-20240101130000"
    
    @patch('src.azure_manager.ContainerInstanceManagementClient')
    @pytest.mark.asyncio
    async def test_cleanup_old_containers(self, mock_client_class):
        """测试清理旧容器"""
        # 模拟客户端
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        self.azure_manager.container_client = mock_client
        
        # 模拟容器
        mock_container1 = Mock()
        mock_container1.name = "azraycontainer-old"
        
        mock_container2 = Mock()
        mock_container2.name = "azraycontainer-current"
        
        # 模拟查找方法
        async def mock_find():
            return [mock_container1, mock_container2]
        
        self.azure_manager._find_existing_containers = mock_find
        
        # 测试清理，保留当前容器
        await self.azure_manager._cleanup_old_containers(keep_current="azraycontainer-current")
        
        # 验证只删除了旧容器
        mock_client.container_groups.begin_delete.assert_called_once_with(
            self.config.azure_resource_group, "azraycontainer-old"
        )
    
    @patch('src.azure_manager.ContainerInstanceManagementClient')
    @pytest.mark.asyncio
    async def test_create_new_container_instance(self, mock_client_class):
        """测试创建新容器实例"""
        # 模拟客户端
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        self.azure_manager.container_client = mock_client
        
        # 模拟配置方法
        self.config.get_unique_container_name = Mock(return_value="azraycontainer-20240101140000")
        
        # 模拟创建操作
        mock_operation = Mock()
        mock_operation.result.return_value = Mock(name="azraycontainer-20240101140000")
        mock_client.container_groups.begin_create_or_update.return_value = mock_operation
        
        # 测试创建
        container_name = await self.azure_manager._create_new_container_instance()
        
        # 验证调用
        mock_client.container_groups.begin_create_or_update.assert_called_once()
        assert container_name == "azraycontainer-20240101140000"
