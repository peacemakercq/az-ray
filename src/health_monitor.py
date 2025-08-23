import asyncio
import logging
import aiohttp
import time
from typing import Optional

from .config import Config
from .azure_manager import AzureManager
from .v2ray_manager import V2RayManager

logger = logging.getLogger(__name__)


class HealthMonitor:
    """健康监控器"""

    def __init__(self, config: Config, azure_manager: AzureManager,
                 v2ray_manager: V2RayManager):
        self.config = config
        self.azure_manager = azure_manager
        self.v2ray_manager = v2ray_manager
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.last_check_time = 0
        self.consecutive_failures = 0
        self.max_failures = 3  # 连续失败3次后重启

    async def start(self):
        """启动健康监控"""
        if self.running:
            logger.warning("健康监控已在运行")
            return

        logger.info(f"正在启动健康监控，检查间隔: {self.config.health_check_interval}秒")
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """停止健康监控"""
        if not self.running:
            return

        logger.info("正在停止健康监控...")
        self.running = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None

        logger.info("健康监控已停止")

    async def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查过程中出现错误: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟再继续

    async def _perform_health_check(self):
        """执行健康检查"""
        logger.info("正在执行健康检查...")
        self.last_check_time = time.time()

        # 检查本地V2Ray是否运行
        if not self.v2ray_manager.is_running():
            logger.warning("本地V2Ray未运行，正在重启...")
            await self.v2ray_manager.restart()
            return

        # 测试代理连接
        connection_ok = await self._test_proxy_connection()

        if connection_ok:
            logger.info("健康检查通过")
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            logger.warning(
                f"健康检查失败 (连续失败: "
                f"{self.consecutive_failures}/{self.max_failures})"
            )

            if self.consecutive_failures >= self.max_failures:
                logger.error("连续健康检查失败，正在重启Azure容器...")
                await self._handle_connection_failure()

    async def _test_proxy_connection(self) -> bool:
        """测试代理连接"""
        try:
            # 配置SOCKS5代理
            connector = aiohttp.SocksConnector.from_url(
                f"socks5://127.0.0.1:{self.config.socks5_port}"
            )

            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                # 尝试访问Google
                async with session.get("https://www.google.com") as response:
                    if response.status == 200:
                        logger.debug("代理连接测试成功")
                        return True
                    else:
                        logger.warning(f"代理连接测试失败，状态码: {response.status}")
                        return False

        except asyncio.TimeoutError:
            logger.warning("代理连接测试超时")
            return False
        except Exception as e:
            logger.warning(f"代理连接测试失败: {e}")
            return False

    async def _handle_connection_failure(self):
        """处理连接失败"""
        try:
            # 重启Azure容器
            await self.azure_manager.restart_container()

            # 等待容器启动
            await asyncio.sleep(30)

            # 重启本地V2Ray（以获取新的FQDN）
            await self.v2ray_manager.restart()

            # 重置失败计数
            self.consecutive_failures = 0

            logger.info("连接故障恢复处理完成")

        except Exception as e:
            logger.error(f"处理连接故障时出现错误: {e}")

    def get_status(self) -> dict:
        """获取监控状态"""
        return {
            "running": self.running,
            "last_check_time": self.last_check_time,
            "consecutive_failures": self.consecutive_failures,
            "v2ray_running": self.v2ray_manager.is_running()
        }
