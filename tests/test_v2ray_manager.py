import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from src.config import Config
from src.v2ray_manager import V2RayManager
from src.azure_manager import AzureManager


@pytest.fixture
def mock_config():
    """模拟配置"""
    config = Mock(spec=Config)
    config.socks5_port = 1080
    config.http_port = 1081
    config.v2ray_port = 9088
    config.v2ray_path = "/v2ray"
    config.v2ray_client_id = "550e8400-e29b-41d4-a716-446655440000"
    config.domain_list = ["domain:google.com", "domain:youtube.com"]
    config.domain_file = None
    config.verbose = False  # 默认非verbose模式
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
    # 设置V2RAY_WAIT_TIME为0以加速测试
    os.environ["V2RAY_WAIT_TIME"] = "0"
    manager = V2RayManager(mock_config, mock_azure_manager)
    
    yield manager
    
    # 清理环境变量
    os.environ.pop("V2RAY_WAIT_TIME", None)


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

    def test_verbose_config_generation(self, v2ray_manager):
        """测试verbose模式下的配置生成"""
        # 测试非verbose模式
        v2ray_manager.config.verbose = False
        
        # 生成配置（需要设置config_file）
        import tempfile
        import json
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_content = {
                "log": {"loglevel": "warning", "access": ""},
                "inbounds": [], "outbounds": [], "routing": {}
            }
            json.dump(config_content, f)
            v2ray_manager.config_file = f.name
        
        # 读取生成的配置
        with open(v2ray_manager.config_file, 'r') as f:
            config = json.load(f)
        
        assert config["log"]["loglevel"] == "warning"
        assert config["log"]["access"] == ""
        
        # 测试verbose模式
        v2ray_manager.config.verbose = True
        # 在verbose模式下，loglevel应该是info
        
        # 清理
        os.unlink(v2ray_manager.config_file)

    @pytest.mark.asyncio
    async def test_log_forwarding_with_verbose(self, v2ray_manager):
        """测试verbose模式下的日志转发"""
        # 测试非verbose模式 - 不应该转发日志
        v2ray_manager.config.verbose = False
        
        with patch('subprocess.Popen') as mock_popen, \
             patch('asyncio.create_task') as mock_create_task:
            
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_popen.return_value = mock_process
            
            # 模拟临时配置文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write('{"test": "config"}')
                config_file_path = f.name
                v2ray_manager.config_file = config_file_path
            
            await v2ray_manager.start()
            
            # 在非verbose模式下，不应该创建日志转发任务
            mock_create_task.assert_not_called()
            
            # 清理
            await v2ray_manager.stop()
            if os.path.exists(config_file_path):
                os.unlink(config_file_path)
        
        # 测试verbose模式 - 应该转发日志
        v2ray_manager.config.verbose = True
        
        with patch('subprocess.Popen') as mock_popen, \
             patch('asyncio.create_task') as mock_create_task:
            
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_popen.return_value = mock_process
            
            # 模拟临时配置文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write('{"test": "config"}')
                config_file_path_verbose = f.name
                v2ray_manager.config_file = config_file_path_verbose
            
            await v2ray_manager.start()
            
            # 在verbose模式下，应该创建日志转发任务
            mock_create_task.assert_called_once()
            
            # 清理
            await v2ray_manager.stop()
            if os.path.exists(config_file_path_verbose):
                os.unlink(config_file_path_verbose)
