import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.config import Config
from src.health_monitor import HealthMonitor
from src.azure_manager import AzureManager
from src.v2ray_manager import V2RayManager


@pytest.fixture
def mock_config():
    """模拟配置"""
    config = Mock(spec=Config)
    config.health_check_interval = 1  # 1秒用于测试
    config.socks5_port = 1080
    return config


@pytest.fixture
def mock_azure_manager():
    """模拟Azure管理器"""
    manager = Mock(spec=AzureManager)
    manager.restart_container = AsyncMock()
    return manager


@pytest.fixture
def mock_v2ray_manager():
    """模拟V2Ray管理器"""
    manager = Mock(spec=V2RayManager)
    manager.is_running.return_value = True
    manager.restart = AsyncMock()
    return manager


@pytest.fixture
def health_monitor(mock_config, mock_azure_manager, mock_v2ray_manager):
    """健康监控实例"""
    return HealthMonitor(mock_config, mock_azure_manager, mock_v2ray_manager)


class TestHealthMonitor:
    """健康监控测试"""

    @pytest.mark.asyncio
    async def test_start_stop(self, health_monitor):
        """测试启动和停止"""
        assert not health_monitor.running

        # 启动
        await health_monitor.start()
        assert health_monitor.running
        assert health_monitor.monitor_task is not None

        # 停止
        await health_monitor.stop()
        assert not health_monitor.running
        assert health_monitor.monitor_task is None

    @pytest.mark.asyncio
    async def test_health_check_success(self, health_monitor):
        """测试健康检查成功"""
        with patch.object(health_monitor, '_test_proxy_connection', return_value=True):
            await health_monitor._perform_health_check()
            assert health_monitor.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_health_check_failure(self, health_monitor):
        """测试健康检查失败"""
        with patch.object(health_monitor, '_test_proxy_connection',
                          return_value=False), \
            patch.object(health_monitor, '_handle_connection_failure',
                         new_callable=AsyncMock) as mock_handle_failure:
            # 模拟连续失败
            for i in range(3):
                await health_monitor._perform_health_check()

            # 第3次失败时应该调用_handle_connection_failure
            mock_handle_failure.assert_called_once()
            # 在调用_handle_connection_failure之前，consecutive_failures应该是3
            assert health_monitor.consecutive_failures == 3

    @pytest.mark.asyncio
    async def test_v2ray_not_running(self, health_monitor, mock_v2ray_manager):
        """测试V2Ray未运行的情况"""
        mock_v2ray_manager.is_running.return_value = False

        await health_monitor._perform_health_check()
        mock_v2ray_manager.restart.assert_called_once()

    def test_get_status(self, health_monitor):
        """测试状态获取"""
        status = health_monitor.get_status()

        assert "running" in status
        assert "last_check_time" in status
        assert "consecutive_failures" in status
        assert "v2ray_running" in status
