"""文件监控模块"""

import asyncio
import logging
import os
from typing import Callable, Union, Optional, Awaitable

logger = logging.getLogger(__name__)


class FileWatcher:
    """文件变更监控器"""
    
    def __init__(self, file_path: str, callback: Union[Callable[[], None], Callable[[], Awaitable[None]]]):
        self.file_path = file_path
        self.callback = callback
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_modified = None
        
    async def start(self):
        """开始监控文件"""
        if self._running:
            return
            
        if not os.path.exists(self.file_path):
            logger.warning(f"监控的文件不存在: {self.file_path}")
            return
            
        self._running = True
        self._last_modified = os.path.getmtime(self.file_path)
        self._task = asyncio.create_task(self._watch_loop())
        logger.info(f"开始监控文件: {self.file_path}")
        
    async def stop(self):
        """停止监控"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info(f"停止监控文件: {self.file_path}")
        
    async def _watch_loop(self):
        """监控循环"""
        while self._running:
            try:
                if os.path.exists(self.file_path):
                    current_modified = os.path.getmtime(self.file_path)
                    if current_modified != self._last_modified:
                        logger.info(f"检测到文件变更: {self.file_path}")
                        self._last_modified = current_modified
                        try:
                            # 判断callback是否为async函数
                            if asyncio.iscoroutinefunction(self.callback):
                                await self.callback()
                            else:
                                await asyncio.to_thread(self.callback)
                        except Exception as e:
                            logger.error(f"处理文件变更回调失败: {e}")
                else:
                    logger.warning(f"监控的文件已删除: {self.file_path}")
                    
                await asyncio.sleep(2)  # 每2秒检查一次
                
            except Exception as e:
                logger.error(f"文件监控异常: {e}")
                await asyncio.sleep(5)  # 出错时等待更长时间
