"""测试Config类的域名文件功能"""

import pytest
import tempfile
import os
from src.config import Config


class TestConfigDomainFile:
    """测试Config类的域名文件功能"""

    def test_default_domain_list(self):
        """测试默认转发域名列表"""
        # 模拟环境变量
        os.environ["AZURE_CLIENT_ID"] = "test-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-secret"
        os.environ["AZURE_TENANT_ID"] = "test-tenant"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription"
        os.environ["V2RAY_CLIENT_ID"] = "550e8400-e29b-41d4-a716-446655440000"
        
        try:
            config = Config()
            assert config.domain_list is not None
            assert len(config.domain_list) == 0
        finally:
            # 清理环境变量
            keys = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID",
                    "AZURE_SUBSCRIPTION_ID", "V2RAY_CLIENT_ID"]
            for key in keys:
                os.environ.pop(key, None)

    def test_load_domains_from_file(self):
        """测试从文件加载域名列表"""
        # 创建临时域名文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("""# 测试域名文件
google.com
youtube.com

# 注释行
facebook.com
# 另一个注释
twitter.com
invalid-domain-
""")
            temp_file = f.name

        try:
            # 模拟环境变量
            os.environ["AZURE_CLIENT_ID"] = "test-id"
            os.environ["AZURE_CLIENT_SECRET"] = "test-secret"
            os.environ["AZURE_TENANT_ID"] = "test-tenant"
            os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription"
            os.environ["V2RAY_CLIENT_ID"] = "550e8400-e29b-41d4-a716-446655440000"
            os.environ["DOMAIN_FILE"] = temp_file
            
            config = Config()
            
            # 验证加载的域名
            # 文件中4个有效域名（不再有默认列表）
            assert len(config.domain_list) == 4
            assert "domain:google.com" in config.domain_list
            assert "domain:youtube.com" in config.domain_list
            assert "domain:facebook.com" in config.domain_list
            assert "domain:twitter.com" in config.domain_list
            assert "invalid-domain-" not in config.domain_list  # 无效域名被跳过
            
        finally:
            # 清理
            os.unlink(temp_file)
            keys = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID",
                    "AZURE_SUBSCRIPTION_ID", "V2RAY_CLIENT_ID", "DOMAIN_FILE"]
            for key in keys:
                os.environ.pop(key, None)

    def test_domain_file_not_found(self):
        """测试域名文件不存在的情况"""
        # 模拟环境变量
        os.environ["AZURE_CLIENT_ID"] = "test-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-secret"
        os.environ["AZURE_TENANT_ID"] = "test-tenant"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription"
        os.environ["V2RAY_CLIENT_ID"] = "550e8400-e29b-41d4-a716-446655440000"
        os.environ["DOMAIN_FILE"] = "/non/existent/file.txt"
        
        try:
            with pytest.raises(ValueError, match="读取域名文件失败"):
                Config()
        finally:
            # 清理环境变量
            keys = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID",
                    "AZURE_SUBSCRIPTION_ID", "V2RAY_CLIENT_ID", "DOMAIN_FILE"]
            for key in keys:
                os.environ.pop(key, None)

    def test_domain_validation(self):
        """测试域名格式验证"""
        # 模拟环境变量
        os.environ["AZURE_CLIENT_ID"] = "test-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-secret"
        os.environ["AZURE_TENANT_ID"] = "test-tenant"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription"
        os.environ["V2RAY_CLIENT_ID"] = "550e8400-e29b-41d4-a716-446655440000"
        
        try:
            config = Config()
            
            # 测试有效域名
            assert config._is_valid_domain("google.com")
            assert config._is_valid_domain("sub.example.com")
            assert config._is_valid_domain("a.b.c.d.com")
            
            # 测试无效域名
            assert not config._is_valid_domain("")
            assert not config._is_valid_domain("invalid-")
            assert not config._is_valid_domain("-invalid")
            assert not config._is_valid_domain("too.long." + "a" * 250)
            
        finally:
            # 清理环境变量
            keys = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID",
                    "AZURE_SUBSCRIPTION_ID", "V2RAY_CLIENT_ID"]
            for key in keys:
                os.environ.pop(key, None)
