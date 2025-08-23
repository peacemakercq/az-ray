import asyncio
import logging
import signal
import sys
from typing import Optional

from .azure_manager import AzureManager
from .v2ray_manager import V2RayManager
from .health_monitor import HealthMonitor
from .config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class AzRayApp:
    """主应用程序类"""

    def __init__(self):
        self.config = Config()
        self.azure_manager: Optional[AzureManager] = None
        self.v2ray_manager: Optional[V2RayManager] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.running = False

    async def initialize(self):
        """初始化所有组件"""
        logger.info("正在初始化AZ-Ray应用...")

        try:
            # 初始化Azure管理器
            self.azure_manager = AzureManager(self.config)
            await self.azure_manager.initialize()

            # 确保Azure资源存在
            await self.azure_manager.ensure_resources()

            # 初始化V2Ray管理器
            self.v2ray_manager = V2RayManager(self.config, self.azure_manager)
            await self.v2ray_manager.initialize()

            # 初始化健康监控
            self.health_monitor = HealthMonitor(
                self.config,
                self.azure_manager,
                self.v2ray_manager
            )

            logger.info("所有组件初始化完成")

        except Exception as e:
            logger.error(f"初始化失败: {e}")
            raise

    async def start(self):
        """启动应用"""
        if self.running:
            logger.warning("应用已在运行")
            return

        logger.info("正在启动AZ-Ray应用...")
        self.running = True

        try:
            # 启动V2Ray代理
            await self.v2ray_manager.start()

            # 启动健康监控
            await self.health_monitor.start()

            logger.info(f"AZ-Ray应用已启动，SOCKS5代理监听端口: {self.config.socks5_port}")

            # 保持运行
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"运行时错误: {e}")
            raise

    async def stop(self):
        """停止应用"""
        if not self.running:
            return

        logger.info("正在停止AZ-Ray应用...")
        self.running = False

        # 停止健康监控
        if self.health_monitor:
            await self.health_monitor.stop()

        # 停止V2Ray
        if self.v2ray_manager:
            await self.v2ray_manager.stop()

        logger.info("AZ-Ray应用已停止")

    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，正在优雅关闭...")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """主入口函数"""
    app = AzRayApp()

    try:
        # 设置信号处理
        app.setup_signal_handlers()

        # 初始化并启动
        await app.initialize()
        await app.start()

    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"应用运行失败: {e}")
        sys.exit(1)
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
