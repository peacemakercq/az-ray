import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.config import Config
from src.v2ray_manager import V2RayManager
from src.azure_manager import AzureManager


@pytest.fixture
def mock_config():
    """模拟配置"""
    config = Mock(spec=Config)
    config.socks5_port = 1080
    config.v2ray_port = 9088
    config.v2ray_path = "/v2ray"
    config.v2ray_client_id = "550e8400-e29b-41d4-a716-446655440000"
    config.domain_list = ["domain:google.com", "domain:youtube.com"]
    config.domain_file = None
    return config


@pytest.fixture
def mock_azure_manager():
    """模拟Azure管理器"""
    manager = Mock(spec=AzureManager)
    manager.get_container_ip = AsyncMock(
        return_value="20.21.22.23")
    return manager


@pytest.fixture
def v2ray_manager(mock_config, mock_azure_manager):
    """V2Ray管理器实例"""
    return V2RayManager(mock_config, mock_azure_manager)


class TestV2RayManager:
    """V2Ray管理器测试"""

    @pytest.mark.asyncio
    async def test_initialize(self, v2ray_manager):
        """测试初始化"""
        with patch.object(v2ray_manager, '_generate_client_config',
                          new_callable=AsyncMock):
            await v2ray_manager.initialize()
            v2ray_manager._generate_client_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_client_config(self, v2ray_manager):
        """测试客户端配置生成"""
        await v2ray_manager._generate_client_config()

        assert v2ray_manager.config_file is not None

        # 验证配置文件内容
        import json
        with open(v2ray_manager.config_file, 'r') as f:
            config = json.load(f)

        assert "inbounds" in config
        assert "outbounds" in config
        assert "routing" in config
        assert config["inbounds"][0]["port"] == 1080
        assert config["inbounds"][0]["protocol"] == "socks"

    @pytest.mark.asyncio
    async def test_start_stop(self, v2ray_manager):
        """测试启动和停止"""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # 进程运行中
            mock_popen.return_value = mock_process

            # 初始化配置
            await v2ray_manager._generate_client_config()

            # 启动
            await v2ray_manager.start()
            assert v2ray_manager.process is not None

            # 停止
            await v2ray_manager.stop()
            mock_process.terminate.assert_called_once()

    def test_is_running(self, v2ray_manager):
        """测试运行状态检查"""
        # 未运行
        assert not v2ray_manager.is_running()

        # 模拟运行状态
        mock_process = Mock()
        mock_process.poll.return_value = None
        v2ray_manager.process = mock_process
        assert v2ray_manager.is_running()

        # 模拟已停止
        mock_process.poll.return_value = 0
        assert not v2ray_manager.is_running()
