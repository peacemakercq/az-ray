"""测试文件监控功能"""

import pytest
import asyncio
import tempfile
import os
from src.file_watcher import FileWatcher


class TestFileWatcher:
    """测试文件监控器"""

    @pytest.mark.asyncio
    async def test_file_watcher_detect_change(self):
        """测试文件变更检测"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("initial content")
            temp_file = f.name

        try:
            change_detected = asyncio.Event()
            
            def on_change():
                change_detected.set()

            # 创建文件监控器
            watcher = FileWatcher(temp_file, on_change)
            
            # 启动监控
            await watcher.start()
            
            # 等待一下让监控器稳定
            await asyncio.sleep(0.5)
            
            # 修改文件
            with open(temp_file, 'w') as f:
                f.write("modified content")
            
            # 等待变更检测
            try:
                await asyncio.wait_for(change_detected.wait(), timeout=5.0)
                assert True, "文件变更被正确检测"
            except asyncio.TimeoutError:
                assert False, "文件变更未被检测到"
            
            # 停止监控
            await watcher.stop()
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_file_watcher_nonexistent_file(self):
        """测试监控不存在的文件"""
        change_detected = False
        
        def on_change():
            nonlocal change_detected
            change_detected = True

        # 监控不存在的文件
        watcher = FileWatcher("/non/existent/file.txt", on_change)
        
        # 启动监控（应该不会出错，只是记录警告）
        await watcher.start()
        await asyncio.sleep(0.1)
        await watcher.stop()
        
        assert not change_detected, "不存在的文件不应该触发变更事件"

    @pytest.mark.asyncio
    async def test_file_watcher_start_stop(self):
        """测试文件监控器的启动和停止"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_file = f.name

        try:
            def on_change():
                pass

            watcher = FileWatcher(temp_file, on_change)
            
            # 测试启动
            assert not watcher._running
            await watcher.start()
            assert watcher._running
            
            # 测试重复启动
            await watcher.start()  # 应该不会出错
            assert watcher._running
            
            # 测试停止
            await watcher.stop()
            assert not watcher._running
            
            # 测试重复停止
            await watcher.stop()  # 应该不会出错
            assert not watcher._running
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
