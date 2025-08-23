#!/usr/bin/env python3
"""
Azure V2Ray项目主入口点
"""
import sys
import argparse
import logging
import os
import asyncio
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 现在可以导入src模块
from src.app import AzRayApp  # noqa: E402


def setup_logging(verbose: bool = False):
    """设置日志配置"""
    level = logging.DEBUG if verbose else logging.INFO

    # 如果环境变量中有LOG_LEVEL，优先使用
    if "LOG_LEVEL" in os.environ:
        level_str = os.environ["LOG_LEVEL"].upper()
        if level_str == "DEBUG":
            level = logging.DEBUG
        elif level_str == "INFO":
            level = logging.INFO
        elif level_str == "WARNING":
            level = logging.WARNING
        elif level_str == "ERROR":
            level = logging.ERROR

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


async def run_app():
    """运行应用的异步函数"""
    app = AzRayApp()

    try:
        # 设置信号处理
        app.setup_signal_handlers()

        # 初始化并启动
        await app.initialize()
        await app.start()

    except KeyboardInterrupt:
        logging.info("收到中断信号")
    except Exception as e:
        logging.error(f"应用运行失败: {e}")
        sys.exit(1)
    finally:
        await app.stop()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Azure V2Ray自动化部署和健康监控系统"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细日志输出"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="dry run模式，不执行实际操作"
    )

    args = parser.parse_args()

    # 设置日志
    setup_logging(args.verbose)

    # 设置环境变量（如果需要）
    if args.dry_run:
        os.environ["DRY_RUN"] = "true"

    # 运行应用
    try:
        asyncio.run(run_app())
    except KeyboardInterrupt:
        logging.info("收到中断信号，正在退出...")
        sys.exit(0)
    except Exception as e:
        logging.error(f"应用运行时出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
