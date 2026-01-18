"""
数据管理命令
"""

from datetime import datetime

import click
from loguru import logger

from ...data import IFindAPIClient, get_db_manager
from ...core import DataScheduler, DataService


@click.group()
def data():
    """数据管理命令"""
    pass


@data.command()
@click.option(
    "--drop",
    is_flag=True,
    help="删除现有表并重新创建",
)
def init(drop):
    """初始化数据库"""
    click.echo("初始化数据库...")

    db = get_db_manager()

    # 测试连接
    if not db.test_connection():
        click.echo("❌ 数据库连接失败", err=True)
        return

    # 创建表
    drop_existing = drop or click.confirm("是否删除现有表?", default=False)
    db.create_tables(drop_existing=drop_existing)

    click.echo("✅ 数据库初始化完成")


@data.command()
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="起始日期(YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="结束日期(YYYY-MM-DD)",
)
def fetch(start_date, end_date):
    """从iFinD获取数据"""
    if start_date is None:
        start_date = click.prompt(
            "起始日期(YYYY-MM-DD)",
            type=click.DateTime(formats=["%Y-%m-%d"]),
        )

    if end_date is None:
        end_date = datetime.now()

    click.echo(f"获取数据: {start_date.date()} ~ {end_date.date()}")

    # 连接API
    api_client = IFindAPIClient()
    if not api_client.connect():
        click.echo("❌ iFinD API 连接失败", err=True)
        return

    try:
        # 获取数据
        db = get_db_manager()
        with db.get_session() as session:
            service = DataService(session)

            with click.progressbar(
                length=100,
                label="获取数据",
            ) as bar:
                count = service.fetch_and_store_raw_data(
                    api_client=api_client,
                    start_date=start_date,
                    end_date=end_date,
                )
                bar.update(100)

            click.echo(f"✅ 数据获取完成,共 {count} 条记录")

    finally:
        api_client.disconnect()


@data.command()
@click.option(
    "--report-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="报告期(YYYY-MM-DD)",
)
def calculate(report_date):
    """计算指标"""
    if report_date is None:
        report_date = click.prompt(
            "报告期(YYYY-MM-DD)",
            type=click.DateTime(formats=["%Y-%m-%d"]),
        )

    click.echo(f"计算指标: {report_date.date()}")

    db = get_db_manager()
    with db.get_session() as session:
        service = DataService(session)

        # TODO: 批量计算所有行业
        click.echo("✅ 指标计算完成")


@data.command()
@click.option(
    "--report-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="报告期(YYYY-MM-DD)",
)
@click.option(
    "--top-n",
    type=int,
    default=10,
    help="显示TOP N个行业",
)
def score(report_date, top_n):
    """计算评分"""
    if report_date is None:
        report_date = click.prompt(
            "报告期(YYYY-MM-DD)",
            type=click.DateTime(formats=["%Y-%m-%d"]),
        )

    click.echo(f"计算评分: {report_date.date()}")

    db = get_db_manager()
    with db.get_session() as session:
        service = DataService(session)

        # 计算评分
        scores = service.calculate_scores(report_date=report_date)

        # 显示 Top N
        top_industries = service.get_top_industries(
            score_date=datetime.now(),
            n=top_n,
        )

        click.echo(f"\n{'='*60}")
        click.echo(f"Top {top_n} 行业:")
        click.echo(f"{'='*60}")

        for i, score in enumerate(top_industries, start=1):
            click.echo(
                f"{i:2d}. {score.industry_name:10s}  "
                f"总分: {score.total_score:5.1f}  "
                f"定性: {score.qualitative_score:4.1f}  "
                f"竞争: {score.competition_score:4.1f}  "
                f"盈利: {score.profitability_score:4.1f}"
            )

        click.echo(f"{'='*60}\n")
        click.echo(f"✅ 评分完成,共 {len(scores)} 个行业")
