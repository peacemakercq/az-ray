import pytest
import os
import json
import hashlib
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
        mock_azure_manager._ensure_v2ray_config = AsyncMock(return_value=False)  # 返回布尔值
        mock_azure_manager._ensure_container_instance = AsyncMock()

        await mock_azure_manager.ensure_resources()

        # 验证所有方法都被调用
        mock_azure_manager._ensure_resource_group.assert_called_once()
        mock_azure_manager._ensure_storage_account.assert_called_once()
        mock_azure_manager._ensure_file_share.assert_called_once()
        mock_azure_manager._ensure_v2ray_config.assert_called_once()
        mock_azure_manager._ensure_container_instance.assert_called_once_with(False)  # 传入配置更新状态

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


class TestAzureManagerConfigValidation:
    """Azure管理器配置验证测试"""

    @pytest.fixture
    def azure_manager(self, mock_config):
        """Azure管理器实例"""
        manager = AzureManager(mock_config)
        manager.storage_account_key = "test-key"
        return manager

    @pytest.mark.asyncio
    async def test_ensure_v2ray_config_no_update_needed(self, azure_manager):
        """测试配置文件无需更新的情况"""
        # 模拟当前配置与期望配置一致
        expected_config = {"test": "config"}
        azure_manager._generate_v2ray_config = Mock(return_value=expected_config)
        azure_manager._get_current_config_from_storage = AsyncMock(return_value=expected_config)

        with patch('src.azure_manager.ShareFileClient'):
            result = await azure_manager._ensure_v2ray_config()

        assert result is False  # 无更新
        azure_manager._get_current_config_from_storage.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_v2ray_config_update_needed(self, azure_manager):
        """测试配置文件需要更新的情况"""
        # 模拟当前配置与期望配置不一致
        current_config = {"test": "old_config"}
        expected_config = {"test": "new_config"}
        
        azure_manager._generate_v2ray_config = Mock(return_value=expected_config)
        azure_manager._get_current_config_from_storage = AsyncMock(return_value=current_config)

        with patch('src.azure_manager.ShareFileClient') as mock_file_client:
            mock_client = Mock()
            mock_file_client.return_value = mock_client
            
            result = await azure_manager._ensure_v2ray_config()

        assert result is True  # 有更新
        mock_client.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_v2ray_config_file_not_exists(self, azure_manager):
        """测试配置文件不存在的情况"""
        expected_config = {"test": "config"}
        azure_manager._generate_v2ray_config = Mock(return_value=expected_config)
        azure_manager._get_current_config_from_storage = AsyncMock(return_value=None)

        with patch('src.azure_manager.ShareFileClient') as mock_file_client:
            mock_client = Mock()
            mock_file_client.return_value = mock_client
            
            result = await azure_manager._ensure_v2ray_config()

        assert result is True  # 需要创建文件
        mock_client.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_config_from_storage_success(self, azure_manager):
        """测试成功获取存储配置"""
        config_data = {"test": "config"}
        config_json = json.dumps(config_data)

        with patch('src.azure_manager.ShareFileClient') as mock_file_client:
            mock_client = Mock()
            mock_file_client.return_value = mock_client
            
            # 模拟下载流
            mock_stream = Mock()
            mock_stream.readall.return_value = config_json.encode('utf-8')
            mock_client.download_file.return_value = mock_stream
            
            result = await azure_manager._get_current_config_from_storage()

        assert result == config_data

    @pytest.mark.asyncio
    async def test_get_current_config_from_storage_not_found(self, azure_manager):
        """测试配置文件不存在"""
        from azure.core.exceptions import ResourceNotFoundError

        with patch('src.azure_manager.ShareFileClient') as mock_file_client:
            mock_client = Mock()
            mock_file_client.return_value = mock_client
            mock_client.download_file.side_effect = ResourceNotFoundError("File not found")
            
            result = await azure_manager._get_current_config_from_storage()

        assert result is None

    @pytest.mark.asyncio
    async def test_is_container_location_valid(self, azure_manager):
        """测试容器位置验证"""
        # 模拟容器对象
        container = Mock()
        container.location = "eastus"
        
        # 测试位置匹配
        azure_manager.config.azure_location = "eastus"
        result = await azure_manager._is_container_location_valid(container)
        assert result is True
        
        # 测试位置不匹配
        azure_manager.config.azure_location = "westus"
        result = await azure_manager._is_container_location_valid(container)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_active_container_with_config_updated(self, azure_manager):
        """测试配置更新时的容器检查"""
        # 模拟容器列表
        container = Mock()
        container.name = "test-container"
        container.location = "eastus"
        
        azure_manager._find_existing_containers = AsyncMock(return_value=[container])
        azure_manager._is_container_location_valid = AsyncMock(return_value=True)
        
        # 测试配置已更新的情况
        result = await azure_manager._get_active_container(config_updated=True)
        assert result is None  # 应该返回None，需要重新创建
        
        # 测试配置未更新的情况
        result = await azure_manager._get_active_container(config_updated=False)
        assert result == container  # 应该返回容器对象
