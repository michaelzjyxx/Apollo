"""
调度器命令
"""

import time

import click
from loguru import logger

from ...data import IFindAPIClient
from ...core import DataScheduler


@click.group()
def scheduler():
    """调度器命令"""
    pass


@scheduler.command()
@click.option(
    "--daemon",
    is_flag=True,
    help="后台运行",
)
def start(daemon):
    """启动调度器"""
    click.echo("启动调度器...")

    api_client = IFindAPIClient()
    sched = DataScheduler(api_client)

    sched.start()

    if daemon:
        click.echo("✅ 调度器已在后台启动")
        click.echo("提示: 使用 Ctrl+C 停止调度器")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n正在停止调度器...")
            sched.stop()
            click.echo("✅ 调度器已停止")
    else:
        click.echo("✅ 调度器已启动(非守护进程模式)")


@scheduler.command()
def status():
    """查看调度器状态"""
    click.echo("调度器状态:")
    # TODO: 实现状态查询
    click.echo("暂未实现")


@scheduler.command()
@click.option(
    "--task",
    type=click.Choice(["quarterly", "monthly", "weekly", "annual"]),
    required=True,
    help="任务类型",
)
def trigger(task):
    """手动触发任务"""
    click.echo(f"手动触发任务: {task}")

    api_client = IFindAPIClient()
    sched = DataScheduler(api_client)

    if task == "quarterly":
        sched.trigger_quarterly_update()
    elif task == "monthly":
        sched.trigger_monthly_update()
    elif task == "weekly":
        sched.trigger_weekly_update()
    elif task == "annual":
        sched.trigger_annual_update()

    click.echo(f"✅ 任务 {task} 执行完成")
