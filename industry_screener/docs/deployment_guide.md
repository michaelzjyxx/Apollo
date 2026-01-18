# Industry Screener 部署指南

本文档介绍如何部署和运行 Industry Screener 系统。

## 目录

- [系统要求](#系统要求)
- [安装步骤](#安装步骤)
- [配置说明](#配置说明)
- [数据初始化](#数据初始化)
- [运行系统](#运行系统)
- [常见问题](#常见问题)

## 系统要求

### 硬件要求

- CPU: 2核及以上
- 内存: 4GB 及以上
- 硬盘: 20GB 可用空间(用于存储历史数据)

### 软件要求

- **操作系统**: Linux / macOS / Windows
- **Python**: 3.10 或更高版本
- **MySQL**: 8.0 或更高版本
- **iFinD账号**: 同花顺 iFinD API 访问权限

### 可选组件

- Redis: 用于缓存(可选)
- Docker: 用于容器化部署(可选)

## 安装步骤

### 1. 克隆项目

```bash
cd /path/to/your/workspace
git clone <repository_url>
cd industry_screener
```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 安装 MySQL

#### macOS (使用 Homebrew)

```bash
brew install mysql
brew services start mysql
```

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
```

#### Windows

下载并安装 [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)

### 5. 创建数据库

```bash
mysql -u root -p
```

```sql
CREATE DATABASE industry_screener CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'screener_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON industry_screener.* TO 'screener_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 配置说明

### 1. 环境变量配置

复制环境变量模板:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USERNAME=screener_user
DB_PASSWORD=your_password
DB_DATABASE=industry_screener
DB_CHARSET=utf8mb4

# iFinD API配置
IFIND_USERNAME=your_ifind_username
IFIND_PASSWORD=your_ifind_password

# 应用配置
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=INFO

# Streamlit配置
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
```

### 2. 主配置文件

复制主配置模板:

```bash
cp config/config.yaml.example config/config.yaml
```

根据需要修改 `config/config.yaml`,主要配置项:

```yaml
# 数据库连接池
database:
  pool_size: 10
  max_overflow: 20

# iFinD API 限流
ifind_api:
  rate_limit: 1  # 每秒最多请求次数
  max_retries: 3

# 调度器
scheduler:
  enabled: true
  timezone: 'Asia/Shanghai'
```

### 3. 评分权重配置(可选)

如需调整评分权重,编辑 `config/scoring_weights.yaml`。

所有权重都可参数化调整,无需修改代码。

## 数据初始化

### 1. 初始化数据库表

```bash
python scripts/init_database.py
```

此命令会:
- 创建所有数据库表
- 导入31个行业的定性评分预设

### 2. 获取历史数据(重要)

首次部署需要获取历史数据用于回测和计算历史分位数:

```bash
# 方式1: 使用CLI工具
python main.py data fetch \
    --start-date 2018-01-01 \
    --end-date 2024-12-31

# 方式2: 使用初始化脚本(如果提供)
# python scripts/fetch_historical_data.py
```

**注意**: 历史数据获取可能需要较长时间(取决于数据量和API限流),建议:
- 先获取最近2-3年的数据进行测试
- 确认无误后再获取完整历史数据
- 可以分批次获取(按年份)

### 3. 计算初始指标和评分

```bash
# 计算最近一个季度的指标
python main.py data calculate --report-date 2024-09-30

# 计算评分
python main.py data score --report-date 2024-09-30
```

## 运行系统

### 1. 测试CLI命令

```bash
# 查看版本
python main.py version

# 查看帮助
python main.py --help
```

### 2. 启动定时调度器

```bash
# 前台运行(测试用)
python main.py scheduler start

# 后台运行(生产环境)
nohup python main.py scheduler start --daemon > scheduler.log 2>&1 &
```

### 3. 启动Web界面(Streamlit)

```bash
streamlit run src/ui/streamlit_app.py
```

访问: http://localhost:8501

### 4. 运行回测

```bash
python main.py backtest run \
    --strategy dynamic_adjustment \
    --start-date 2020-01-01 \
    --end-date 2024-12-31 \
    --top-n 10 \
    --min-score 70
```

## 生产环境部署

### 使用 Systemd (Linux)

创建服务文件 `/etc/systemd/system/industry-screener.service`:

```ini
[Unit]
Description=Industry Screener Scheduler
After=network.target mysql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/industry_screener
Environment="PATH=/path/to/industry_screener/venv/bin"
ExecStart=/path/to/industry_screener/venv/bin/python main.py scheduler start --daemon
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
sudo systemctl daemon-reload
sudo systemctl start industry-screener
sudo systemctl enable industry-screener
sudo systemctl status industry-screener
```

### 使用 Docker(可选)

```bash
# 构建镜像
docker build -t industry-screener:latest .

# 运行容器
docker run -d \
    --name industry-screener \
    --env-file .env \
    -p 8501:8501 \
    -v $(pwd)/data:/app/data \
    industry-screener:latest
```

## 常见问题

### 1. 数据库连接失败

**问题**: `数据库连接失败,请检查配置`

**解决**:
- 检查 MySQL 服务是否启动: `systemctl status mysql`
- 检查 `.env` 文件中的数据库配置是否正确
- 测试连接: `mysql -h localhost -u screener_user -p`

### 2. iFinD API连接失败

**问题**: `iFinD API 连接失败`

**解决**:
- 确认 iFinD 账号密码正确
- 检查 iFinD SDK 是否安装: `pip show iFinDPy`
- 确认账号有API访问权限

### 3. 缺少依赖

**问题**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:
```bash
pip install -r requirements.txt
```

### 4. 日志文件过大

**问题**: `data/logs/` 目录占用空间过大

**解决**:
- 日志自动轮转: 默认100MB轮转,保留30天
- 手动清理: `rm -rf data/logs/*.log.*`
- 调整配置: 修改 `config.yaml` 中的 `logging.retention`

### 5. 调度器任务未执行

**问题**: 定时任务没有按时执行

**解决**:
- 检查调度器是否运行: `ps aux | grep scheduler`
- 查看日志: `tail -f data/logs/app.log`
- 检查 `config.yaml` 中的 `scheduler.enabled` 是否为 `true`
- 检查 cron 表达式是否正确

## 维护建议

### 数据库备份

```bash
# 每日备份
mysqldump -u screener_user -p industry_screener > backup_$(date +%Y%m%d).sql

# 恢复
mysql -u screener_user -p industry_screener < backup_20240101.sql
```

### 日志监控

```bash
# 实时查看日志
tail -f data/logs/app.log

# 查看错误日志
tail -f data/logs/error.log
```

### 定期审核

- **定性评分**: 每半年审核一次 `config/industry_qualitative.yaml`
- **评分权重**: 根据回测结果调整 `config/scoring_weights.yaml`
- **数据质量**: 定期检查数据完整性和时效性

## 联系支持

如遇到其他问题,请:
- 查看技术文档: `docs/技术设计文档.md`
- 提交Issue: [GitHub Issues](https://github.com/your/repo/issues)
- 联系开发团队

---

最后更新: 2026-01-18
