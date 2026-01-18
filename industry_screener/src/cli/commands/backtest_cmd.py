"""
回测命令
"""

from datetime import datetime

import click
from loguru import logger

from ...data import get_db_manager
from ...core import BacktestEngine


@click.group()
def backtest():
    """回测命令"""
    pass


@backtest.command()
@click.option(
    "--strategy",
    type=str,
    default="dynamic_adjustment",
    help="策略名称",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="起始日期(YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="结束日期(YYYY-MM-DD),默认为当前日期",
)
@click.option(
    "--top-n",
    type=int,
    default=10,
    help="选择TOP N个行业",
)
@click.option(
    "--min-score",
    type=float,
    default=70.0,
    help="最低评分要求",
)
@click.option(
    "--n-stocks",
    type=int,
    default=3,
    help="每个行业选择的个股数量",
)
@click.option(
    "--weight-method",
    type=click.Choice(["equal", "market_cap", "score"]),
    default="equal",
    help="权重方法",
)
@click.option(
    "--rebalance",
    type=click.Choice(["monthly", "quarterly", "semi_annual", "annual"]),
    default="monthly",
    help="再平衡频率",
)
def run(
    strategy,
    start_date,
    end_date,
    top_n,
    min_score,
    n_stocks,
    weight_method,
    rebalance,
):
    """运行回测"""
    if end_date is None:
        end_date = datetime.now()

    click.echo(f"回测策略: {strategy}")
    click.echo(f"回测期间: {start_date.date()} ~ {end_date.date()}")
    click.echo(f"参数: TOP{top_n}, 最低分{min_score}, "
               f"每行业{n_stocks}只股票, 权重={weight_method}, "
               f"再平衡={rebalance}")
    click.echo()

    if not click.confirm("确认开始回测?"):
        return

    # 运行回测
    db = get_db_manager()
    with db.get_session() as session:
        engine = BacktestEngine(session)

        with click.progressbar(
            length=100,
            label="运行回测",
        ) as bar:
            result = engine.run_backtest(
                strategy_name=strategy,
                start_date=start_date,
                end_date=end_date,
                top_n=top_n,
                min_score=min_score,
                n_stocks=n_stocks,
                weight_method=weight_method,
                rebalance_frequency=rebalance,
            )
            bar.update(100)

        # 显示结果
        click.echo(f"\n{'='*60}")
        click.echo("回测结果:")
        click.echo(f"{'='*60}")
        click.echo(f"总收益:     {result.total_return:>8.2f}%")
        click.echo(f"年化收益:   {result.annual_return:>8.2f}%")
        click.echo(f"夏普比率:   {result.sharpe_ratio:>8.2f}")
        click.echo(f"最大回撤:   {result.max_drawdown:>8.2f}%")
        click.echo(f"胜率:       {result.win_rate:>8.2f}%")
        click.echo(f"")
        click.echo(f"基准收益:   {result.benchmark_return:>8.2f}% ({result.benchmark_code})")
        click.echo(f"超额收益:   {result.excess_return:>8.2f}%")
        click.echo(f"{'='*60}\n")

        click.echo(f"✅ 回测完成: {result.backtest_name}")


@backtest.command()
@click.option(
    "--strategy",
    type=str,
    help="策略名称",
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="显示数量",
)
def list(strategy, limit):
    """列出回测结果"""
    db = get_db_manager()
    with db.get_session() as session:
        from ...data import BacktestResultRepository

        repo = BacktestResultRepository(session)

        if strategy:
            results = repo.get_by_strategy(strategy)
        else:
            results = repo.get_all(limit=limit)

        if not results:
            click.echo("未找到回测结果")
            return

        click.echo(f"\n{'='*80}")
        click.echo(f"回测结果列表 (共 {len(results)} 条):")
        click.echo(f"{'='*80}")

        for i, result in enumerate(results[:limit], start=1):
            click.echo(
                f"{i:2d}. {result.backtest_name:40s}  "
                f"收益: {result.total_return:>7.2f}%  "
                f"夏普: {result.sharpe_ratio:>5.2f}  "
                f"回撤: {result.max_drawdown:>6.2f}%"
            )

        click.echo(f"{'='*80}\n")


@backtest.command()
@click.argument("name")
def show(name):
    """显示回测详情"""
    db = get_db_manager()
    with db.get_session() as session:
        engine = BacktestEngine(session)

        summary = engine.get_backtest_summary(name)

        if summary is None:
            click.echo(f"❌ 未找到回测: {name}", err=True)
            return

        click.echo(f"\n{'='*60}")
        click.echo(f"回测名称: {summary['backtest_name']}")
        click.echo(f"{'='*60}")
        click.echo(f"策略:       {summary['strategy_name']}")
        click.echo(f"期间:       {summary['period']}")
        click.echo(f"")
        click.echo(f"总收益:     {summary['total_return']}")
        click.echo(f"年化收益:   {summary['annual_return']}")
        click.echo(f"夏普比率:   {summary['sharpe_ratio']}")
        click.echo(f"最大回撤:   {summary['max_drawdown']}")
        click.echo(f"胜率:       {summary['win_rate']}")
        click.echo(f"")
        click.echo(f"基准:       {summary['benchmark']}")
        click.echo(f"基准收益:   {summary['benchmark_return']}")
        click.echo(f"超额收益:   {summary['excess_return']}")
        click.echo(f"")
        click.echo(f"交易次数:   {summary['num_trades']}")
        click.echo(f"{'='*60}\n")
