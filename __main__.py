#!/usr/bin/env python3
"""
Azure V2Ray项目主入口点
"""
import asyncio
import sys
import argparse
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 现在可以导入src模块
from src.main import AzRayApp


def setup_logging(verbose: bool = False):
    """设置日志配置"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


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
    
    # 创建并运行应用
    app = AzRayApp()
    
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logging.info("收到中断信号，正在退出...")
        sys.exit(0)
    except Exception as e:
        logging.error(f"应用运行时出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
