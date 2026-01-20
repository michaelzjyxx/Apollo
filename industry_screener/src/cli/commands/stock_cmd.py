"""
股票筛选CLI命令

命令组：
- stock: 股票筛选相关命令
- pool: 优质公司池管理命令
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from ...data.database import get_session
from ...core.stock_filter import StockFilter
from ...core.stock_scorer import StockScorer
from ...data.repository import StockScoreRepository
from ...data.models import StockScore

console = Console()


@click.group()
def stock():
    """股票筛选命令"""
    pass


@stock.command()
@click.option("--date", help="筛选基准日期 (YYYY-MM-DD)", default=None)
@click.option("--industries", help="指定行业列表（逗号分隔）", default=None)
@click.option("--min-score", help="最低得分", type=float, default=60.0)
@click.option("--output", help="输出文件路径", default=None)
@click.option("-v", "--verbose", is_flag=True, help="详细输出")
def screen(date, industries, min_score, output, verbose):
    """执行股票质量筛选"""
    console.print("\n[cyan]🔍 股票质量筛选[/cyan]")
    console.print("=" * 60)

    # 解析日期
    if date:
        calc_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        calc_date = datetime.now()

    console.print(f"筛选日期: {calc_date.strftime('%Y-%m-%d')}")

    # 解析行业列表
    if industries:
        industry_list = [i.strip() for i in industries.split(",")]
    else:
        # TODO: 从数据库获取优质行业列表
        console.print("[red]错误: 请指定行业列表[/red]")
        return

    console.print(f"筛选行业: {len(industry_list)} 个")
    console.print(f"最低得分: {min_score}")
    console.print()

    # 执行筛选
    with get_session() as session:
        stock_filter = StockFilter(session)

        try:
            result = stock_filter.filter(industry_list, calc_date, min_score)

            # 显示结果
            _display_filter_result(result)

            # 保存结果
            stock_filter.save_results(result)

            # 导出文件
            if output:
                _export_pool(result["pool"], output)
                console.print(f"\n[green]✓[/green] 结果已导出到: {output}")

        except Exception as e:
            console.print(f"\n[red]✗ 筛选失败: {e}[/red]")
            if verbose:
                logger.exception(e)


@stock.command()
@click.argument("stock_code")
@click.option("--date", help="评分基准日期 (YYYY-MM-DD)", default=None)
@click.option("--detail", is_flag=True, help="显示详细评分")
def score(stock_code, date, detail):
    """计算单只股票的质量得分"""
    console.print(f"\n[cyan]📊 股票评分: {stock_code}[/cyan]")
    console.print("=" * 60)

    # 解析日期
    if date:
        calc_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        calc_date = datetime.now()

    # 计算评分
    with get_session() as session:
        scorer = StockScorer(session)

        try:
            stock_score = scorer.score(stock_code, calc_date)

            if not stock_score:
                console.print(f"[red]未找到股票 {stock_code} 的数据[/red]")
                return

            # 显示评分
            _display_stock_score(stock_score, detail)

        except Exception as e:
            console.print(f"[red]✗ 评分失败: {e}[/red]")
            logger.exception(e)


@click.group()
def pool():
    """优质公司池管理命令"""
    pass


@pool.command()
@click.option("--date", help="查询日期 (YYYY-MM-DD)", default=None)
@click.option("--industry", help="筛选行业", default=None)
@click.option("--min-score", help="最低得分", type=float, default=None)
@click.option("--sort-by", help="排序字段", default="score")
@click.option("--limit", help="显示数量", type=int, default=50)
def list(date, industry, min_score, sort_by, limit):
    """列出优质公司池"""
    console.print("\n[cyan]📊 优质公司池[/cyan]")
    console.print("=" * 60)

    # 解析日期
    if date:
        score_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        score_date = datetime.now()

    console.print(f"查询日期: {score_date.strftime('%Y-%m-%d')}\n")

    # 查询公司池
    with get_session() as session:
        score_repo = StockScoreRepository(session)

        try:
            pool = score_repo.get_quality_pool(
                score_date, min_score=min_score, passed_only=True
            )

            # 筛选行业
            if industry:
                pool = [s for s in pool if s.industry_name == industry]

            # 限制数量
            pool = pool[:limit]

            # 显示结果
            _display_pool_table(pool)

        except Exception as e:
            console.print(f"[red]✗ 查询失败: {e}[/red]")
            logger.exception(e)


@pool.command()
@click.argument("stock_code")
@click.option("--date", help="查询日期 (YYYY-MM-DD)", default=None)
def show(stock_code, date):
    """查看股票详细信息"""
    console.print(f"\n[cyan]📊 {stock_code} 详细信息[/cyan]")
    console.print("=" * 60)

    # 解析日期
    if date:
        score_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        score_date = datetime.now()

    # 查询评分
    with get_session() as session:
        score_repo = StockScoreRepository(session)

        try:
            stock_score = score_repo.get_by_stock_and_date(stock_code, score_date)

            if not stock_score:
                console.print(f"[red]未找到股票 {stock_code} 的评分数据[/red]")
                return

            # 显示详细信息
            _display_stock_detail(stock_score)

        except Exception as e:
            console.print(f"[red]✗ 查询失败: {e}[/red]")
            logger.exception(e)


@pool.command()
@click.option("--output", help="输出文件路径", required=True)
@click.option("--format", help="输出格式", type=click.Choice(["csv", "excel", "json"]), default="csv")
@click.option("--date", help="查询日期 (YYYY-MM-DD)", default=None)
def export(output, format, date):
    """导出优质公司池"""
    console.print("\n[cyan]💾 导出优质公司池[/cyan]")
    console.print("=" * 60)

    # 解析日期
    if date:
        score_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        score_date = datetime.now()

    # 查询公司池
    with get_session() as session:
        score_repo = StockScoreRepository(session)

        try:
            pool = score_repo.get_quality_pool(score_date, passed_only=True)

            # 导出
            _export_pool(pool, output, format)

            console.print(f"\n[green]✓[/green] 已导出 {len(pool)} 只股票到: {output}")

        except Exception as e:
            console.print(f"[red]✗ 导出失败: {e}[/red]")
            logger.exception(e)


# ========== 辅助函数 ==========


def _display_filter_result(result: Dict):
    """显示筛选结果"""
    console.print("\n[cyan]📊 筛选结果[/cyan]")
    console.print("=" * 60)

    console.print(f"候选股票: {result['total_candidates']} 只")
    console.print(f"通过基础资格: {result['passed_basic']} 只")
    console.print(f"通过排除项: {result['passed_exclusion']} 只")
    console.print(f"完成评分: {result['scored']} 只")
    console.print(f"入池（≥{result['min_score']}分）: {result['pool_before_diversification']} 只")
    console.print(f"最终入池: {result['final_pool']} 只")

    # 显示行业分布
    if result["final_pool"] > 0:
        console.print("\n[cyan]行业分布:[/cyan]")
        industry_dist = defaultdict(int)
        for score in result["pool"]:
            industry_dist[score.industry_name] += 1

        for industry, count in sorted(
            industry_dist.items(), key=lambda x: x[1], reverse=True
        ):
            ratio = count / result["final_pool"] * 100
            console.print(f"  {industry}: {count} 只 ({ratio:.1f}%)")


def _display_stock_score(stock_score: StockScore, detail: bool = False):
    """显示股票评分"""
    console.print(f"\n股票名称: {stock_score.stock_name}")
    console.print(f"所属行业: {stock_score.industry_name}")
    console.print(f"\n总分: [bold green]{stock_score.total_score:.1f}[/bold green] / 100")

    console.print(f"\n财务质量: {stock_score.financial_score:.1f} / 50")
    if detail:
        console.print(f"  ROE稳定性: {stock_score.roe_stability_score:.1f} / 15")
        console.print(f"  ROIC水平: {stock_score.roic_level_score:.1f} / 15")
        console.print(f"  现金流质量: {stock_score.cashflow_quality_score:.1f} / 12")
        console.print(f"  负债率: {stock_score.leverage_score:.1f} / 8")

    console.print(f"\n竞争优势: {stock_score.competitive_score:.1f} / 50")
    if detail:
        console.print(f"  龙头地位: {stock_score.leader_position_score:.1f} / 15")
        console.print(f"  龙头趋势: {stock_score.leader_trend_score:.1f} / 10")
        console.print(f"  盈利优势: {stock_score.profit_margin_score:.1f} / 15")
        console.print(f"  成长性: {stock_score.growth_score:.1f} / 10")


def _display_pool_table(pool: List[StockScore]):
    """显示公司池表格"""
    console.print(f"共 {len(pool)} 只股票\n")

    table = Table(title="优质公司池")

    table.add_column("股票代码", style="cyan")
    table.add_column("股票名称", style="magenta")
    table.add_column("行业", style="blue")
    table.add_column("得分", justify="right", style="green")
    table.add_column("ROE", justify="right")
    table.add_column("ROIC", justify="right")

    for score in pool:
        table.add_row(
            score.stock_code,
            score.stock_name,
            score.industry_name,
            f"{score.total_score:.1f}",
            "-",  # TODO: 从calc_data获取
            "-",
        )

    console.print(table)


def _display_stock_detail(stock_score: StockScore):
    """显示股票详细信息"""
    console.print(f"\n股票名称: {stock_score.stock_name}")
    console.print(f"股票代码: {stock_score.stock_code}")
    console.print(f"所属行业: {stock_score.industry_name}")
    console.print(f"评分日期: {stock_score.score_date.strftime('%Y-%m-%d')}")

    console.print(f"\n[bold]质量评分: {stock_score.total_score:.1f} / 100[/bold]")

    # 财务质量
    console.print("\n[cyan]财务质量 ({:.1f} / 50)[/cyan]".format(stock_score.financial_score))
    console.print(f"  ROE稳定性: {stock_score.roe_stability_score:.1f} / 15")
    console.print(f"  ROIC水平: {stock_score.roic_level_score:.1f} / 15")
    console.print(f"  现金流质量: {stock_score.cashflow_quality_score:.1f} / 12")
    console.print(f"  负债率: {stock_score.leverage_score:.1f} / 8")

    # 竞争优势
    console.print("\n[cyan]竞争优势 ({:.1f} / 50)[/cyan]".format(stock_score.competitive_score))
    console.print(f"  龙头地位: {stock_score.leader_position_score:.1f} / 15")
    console.print(f"  龙头趋势: {stock_score.leader_trend_score:.1f} / 10")
    console.print(f"  盈利优势: {stock_score.profit_margin_score:.1f} / 15")
    console.print(f"  成长性: {stock_score.growth_score:.1f} / 10")

    # 入池理由
    if stock_score.pool_reason:
        console.print(f"\n[cyan]入池理由:[/cyan]")
        console.print(f"  {stock_score.pool_reason}")


def _export_pool(pool: List[StockScore], output: str, format: str = "csv"):
    """导出公司池"""
    import pandas as pd

    # 转换为DataFrame
    data = []
    for score in pool:
        data.append(
            {
                "股票代码": score.stock_code,
                "股票名称": score.stock_name,
                "行业": score.industry_name,
                "总分": score.total_score,
                "财务质量": score.financial_score,
                "竞争优势": score.competitive_score,
                "ROE稳定性": score.roe_stability_score,
                "ROIC水平": score.roic_level_score,
                "现金流质量": score.cashflow_quality_score,
                "负债率": score.leverage_score,
                "龙头地位": score.leader_position_score,
                "龙头趋势": score.leader_trend_score,
                "盈利优势": score.profit_margin_score,
                "成长性": score.growth_score,
                "排名": score.rank,
            }
        )

    df = pd.DataFrame(data)

    # 导出
    if format == "csv":
        df.to_csv(output, index=False, encoding="utf-8-sig")
    elif format == "excel":
        df.to_excel(output, index=False)
    elif format == "json":
        df.to_json(output, orient="records", force_ascii=False, indent=2)
