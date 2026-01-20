"""
CLI命令行工具 - 主入口
"""

import sys
from pathlib import Path

import click
from loguru import logger

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils import setup_logger
from .commands import backtest, data, pool, scheduler, stock


@click.group()
@click.option(
    "--debug",
    is_flag=True,
    help="启用调试模式",
)
def cli(debug):
    """Industry Screener - A股行业筛选系统"""
    # 设置日志
    log_level = "DEBUG" if debug else "INFO"
    setup_logger(log_level=log_level)

    if debug:
        logger.debug("调试模式已启用")


@cli.command()
def version():
    """显示版本信息"""
    from src.utils import get_config_value

    app_name = get_config_value("app.name", default="Industry Screener")
    app_version = get_config_value("app.version", default="1.0.0")

    click.echo(f"{app_name} v{app_version}")


# 注册命令组
cli.add_command(data)
cli.add_command(backtest)
cli.add_command(scheduler)
cli.add_command(stock)
cli.add_command(pool)


if __name__ == "__main__":
    cli()
