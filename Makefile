# Az-Ray V2Ray Azure 自动化代理项目
# Makefile for common development and deployment tasks

.PHONY: help install test lint clean run deploy docker-build docker-run update-geo setup-env

# 默认目标
help: ## 显示帮助信息
	@echo "Az-Ray V2Ray Azure 自动化代理项目"
	@echo ""
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# 开发环境设置
install: ## 安装项目依赖
	@echo "🔧 安装Python依赖..."
	pip install -r requirements.txt
	pip install pytest pytest-asyncio mypy flake8

setup-env: ## 设置环境变量（复制.env.example到.env）
	@if [ ! -f .env ]; then \
		echo "📝 创建环境配置文件..."; \
		cp .env.example .env; \
		echo "✅ 已创建 .env 文件，请编辑配置"; \
	else \
		echo "ℹ️  .env 文件已存在"; \
	fi

# 代码质量检查
test: ## 运行所有测试
	@echo "🧪 运行测试..."
	python -m pytest tests/ -v

lint: ## 运行代码风格检查
	@echo "🔍 运行代码风格检查..."
	python -m flake8 src/ tests/ __main__.py
	python -m mypy src/

check: test lint ## 运行测试和代码检查

# 应用运行
run: ## 运行主应用
	@echo "🚀 启动Az-Ray应用..."
	python __main__.py

clean: ## 清理临时文件和缓存
	@echo "🧹 清理缓存文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache/ .mypy_cache/ 2>/dev/null || true

# GeoIP数据管理
update-geo: ## 更新GeoIP/GeoSite数据
	@echo "🌐 更新GeoIP数据..."
	./scripts/update-geo-data.sh

# Docker操作
docker-build: ## 构建Docker镜像
	@echo "🐳 构建Docker镜像..."
	docker build -f docker/Dockerfile.multi -t az-ray:latest .

docker-run: ## 运行Docker容器
	@echo "🐳 运行Docker容器..."
	docker-compose -f docker/docker-compose.yml up -d

docker-stop: ## 停止Docker容器
	@echo "🛑 停止Docker容器..."
	docker-compose -f docker/docker-compose.yml down

docker-logs: ## 查看Docker容器日志
	@echo "📋 查看容器日志..."
	docker-compose -f docker/docker-compose.yml logs -f

# 部署操作
deploy: ## 部署到Azure
	@echo "☁️  部署到Azure..."
	./scripts/deploy.sh

deploy-local: ## 本地测试部署
	@echo "🏠 本地测试部署..."
	$(MAKE) check
	$(MAKE) docker-build
	$(MAKE) docker-run

# 开发工具
dev-setup: install setup-env update-geo ## 完整开发环境设置
	@echo "✅ 开发环境设置完成"
	@echo "📝 请编辑 .env 文件配置Azure凭据"
	@echo "🚀 运行 'make run' 启动应用"

format: ## 格式化代码（如果安装了black）
	@if command -v black >/dev/null 2>&1; then \
		echo "🎨 格式化代码..."; \
		black src/ tests/ __main__.py; \
	else \
		echo "ℹ️  black未安装，跳过代码格式化"; \
	fi

commit-geo: ## 提交GeoIP数据更新
	@echo "📦 提交GeoIP数据更新..."
	git add data/
	git commit -m "update: refresh GeoIP/GeoSite data"

# 发布相关
release: ## 创建新版本发布
	@echo "🏷️  创建版本发布..."
	@read -p "输入版本号 (例如: v1.0.0): " version; \
	git tag -a $$version -m "Release $$version"; \
	git push origin $$version; \
	echo "✅ 版本 $$version 已发布"

# 监控和调试
status: ## 检查应用状态
	@echo "📊 检查应用状态..."
	@if pgrep -f "python.*__main__.py" > /dev/null; then \
		echo "✅ Az-Ray应用正在运行"; \
		echo "🔍 进程信息:"; \
		pgrep -f "python.*__main__.py" | xargs ps -p; \
	else \
		echo "❌ Az-Ray应用未运行"; \
	fi
	@if pgrep -f "v2ray" > /dev/null; then \
		echo "✅ V2Ray进程正在运行"; \
	else \
		echo "❌ V2Ray进程未运行"; \
	fi

logs: ## 查看应用日志（如果使用systemd或docker）
	@echo "📋 查看应用日志..."
	@if [ -f /tmp/az-ray.log ]; then \
		tail -f /tmp/az-ray.log; \
	else \
		echo "ℹ️  未找到日志文件"; \
	fi

# 完整工作流
ci: check docker-build ## CI流程：测试+构建
	@echo "✅ CI流程完成"

all: dev-setup ci ## 完整设置：开发环境+CI
	@echo "🎉 完整设置完成"
