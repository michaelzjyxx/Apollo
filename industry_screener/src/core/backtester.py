"""
回测引擎 - 动态调整策略回测

策略逻辑:
1. 每月监控行业评分和红线触发情况
2. 红线触发时动态调出,替换为备选行业
3. 持仓为每个行业的前3只龙头股(等权或市值加权)
4. 计算收益、夏普比率、最大回撤等绩效指标
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from ..data import (
    BacktestResult,
    BacktestResultRepository,
    IFindAPIClient,
    IndustryScore,
    IndustryScoreRepository,
)
from ..utils import (
    DEFAULT_BENCHMARK,
    DEFAULT_MIN_SCORE,
    DEFAULT_N_STOCKS,
    DEFAULT_TOP_N,
    RebalanceFrequency,
    WeightMethod,
    get_config_value,
)


class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        session: Session,
        api_client: Optional[IFindAPIClient] = None,
    ):
        """
        初始化回测引擎

        Args:
            session: 数据库会话
            api_client: iFinD API 客户端
        """
        self.session = session
        self.api_client = api_client

        # 初始化仓库
        self.score_repo = IndustryScoreRepository(session)
        self.backtest_repo = BacktestResultRepository(session)

        # 加载回测配置
        self.config = get_config_value("backtest", default={})

        logger.info("回测引擎初始化成功")

    def run_backtest(
        self,
        strategy_name: str,
        start_date: datetime,
        end_date: datetime,
        top_n: Optional[int] = None,
        min_score: Optional[float] = None,
        n_stocks: Optional[int] = None,
        weight_method: Optional[str] = None,
        benchmark: Optional[str] = None,
        rebalance_frequency: Optional[str] = None,
    ) -> BacktestResult:
        """
        运行回测

        Args:
            strategy_name: 策略名称
            start_date: 起始日期
            end_date: 结束日期
            top_n: 选择TOP N个行业
            min_score: 最低评分要求
            n_stocks: 每个行业选择的个股数量
            weight_method: 权重方法(equal/market_cap/score)
            benchmark: 基准指数代码
            rebalance_frequency: 再平衡频率(monthly/quarterly)

        Returns:
            回测结果
        """
        # 使用默认配置
        if top_n is None:
            top_n = self.config.get("top_n", DEFAULT_TOP_N)
        if min_score is None:
            min_score = self.config.get("min_score", DEFAULT_MIN_SCORE)
        if n_stocks is None:
            n_stocks = self.config.get("top_stocks", {}).get(
                "n_stocks", DEFAULT_N_STOCKS
            )
        if weight_method is None:
            weight_method = self.config.get("top_stocks", {}).get(
                "weight_method", WeightMethod.EQUAL
            )
        if benchmark is None:
            benchmark = self.config.get("benchmark", DEFAULT_BENCHMARK)
        if rebalance_frequency is None:
            rebalance_frequency = self.config.get(
                "rebalance_frequency", RebalanceFrequency.MONTHLY
            )

        logger.info(
            f"开始回测: {strategy_name} ({start_date.date()} ~ {end_date.date()})"
        )
        logger.info(
            f"参数: TOP{top_n}, 最低分{min_score}, "
            f"每行业{n_stocks}只股票, 权重={weight_method}"
        )

        # 1. 获取再平衡日期列表
        rebalance_dates = self._get_rebalance_dates(
            start_date, end_date, rebalance_frequency
        )

        logger.info(f"再平衡次数: {len(rebalance_dates)}")

        # 2. 生成持仓记录
        holdings = self._generate_holdings(
            rebalance_dates, top_n, min_score, n_stocks, weight_method
        )

        # 3. 计算每日收益
        daily_returns = self._calculate_daily_returns(
            holdings, start_date, end_date
        )

        # 4. 计算绩效指标
        metrics = self._calculate_performance_metrics(daily_returns)

        # 5. 获取基准收益
        benchmark_return = self._get_benchmark_return(
            benchmark, start_date, end_date
        )

        # 6. 生成交易记录
        trades = self._generate_trades(holdings)

        # 7. 保存回测结果
        result = self._save_backtest_result(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            parameters={
                "top_n": top_n,
                "min_score": min_score,
                "n_stocks": n_stocks,
                "weight_method": weight_method,
                "rebalance_frequency": rebalance_frequency,
            },
            metrics=metrics,
            benchmark_code=benchmark,
            benchmark_return=benchmark_return,
            holdings=holdings,
            trades=trades,
            daily_returns=daily_returns,
        )

        logger.info(
            f"回测完成: 总收益{metrics['total_return']:.2f}%, "
            f"年化收益{metrics['annual_return']:.2f}%, "
            f"夏普比率{metrics['sharpe_ratio']:.2f}, "
            f"最大回撤{metrics['max_drawdown']:.2f}%"
        )

        return result

    def _get_rebalance_dates(
        self,
        start_date: datetime,
        end_date: datetime,
        frequency: str,
    ) -> List[datetime]:
        """
        生成再平衡日期列表

        Args:
            start_date: 起始日期
            end_date: 结束日期
            frequency: 频率(monthly/quarterly/semi_annual/annual)

        Returns:
            再平衡日期列表
        """
        dates = []
        current = start_date

        if frequency == RebalanceFrequency.MONTHLY:
            interval = timedelta(days=30)
        elif frequency == RebalanceFrequency.QUARTERLY:
            interval = timedelta(days=90)
        elif frequency == RebalanceFrequency.SEMI_ANNUAL:
            interval = timedelta(days=180)
        elif frequency == RebalanceFrequency.ANNUAL:
            interval = timedelta(days=365)
        else:
            interval = timedelta(days=30)  # 默认月度

        while current <= end_date:
            dates.append(current)
            current += interval

        return dates

    def _generate_holdings(
        self,
        rebalance_dates: List[datetime],
        top_n: int,
        min_score: float,
        n_stocks: int,
        weight_method: str,
    ) -> List[Dict]:
        """
        生成持仓记录

        Args:
            rebalance_dates: 再平衡日期列表
            top_n: 选择TOP N个行业
            min_score: 最低评分要求
            n_stocks: 每个行业选择的个股数量
            weight_method: 权重方法

        Returns:
            持仓记录列表
        """
        holdings = []

        for date in rebalance_dates:
            # 获取该日期的行业评分
            top_industries = self.score_repo.get_top_n(
                score_date=date,
                n=top_n * 2,  # 多取一些作为备选
                min_score=min_score,
            )

            # 过滤红线触发的行业
            selected_industries = []
            for score in top_industries:
                # 检查是否触发红线
                if score.redline_triggered and len(score.redline_triggered) > 0:
                    logger.info(
                        f"{date.date()}: {score.industry_name} "
                        f"触发红线 {score.redline_triggered}, 跳过"
                    )
                    continue

                selected_industries.append(score)

                if len(selected_industries) >= top_n:
                    break

            # 计算权重
            weights = self._calculate_weights(
                selected_industries, weight_method
            )

            # 为每个行业选择个股
            holding = {
                "date": date,
                "industries": [],
            }

            for i, score in enumerate(selected_industries):
                # TODO: 实际实现需要从 API 获取行业龙头股
                # stocks = self._get_top_stocks(score.industry_code, n_stocks)

                industry_holding = {
                    "industry_code": score.industry_code,
                    "industry_name": score.industry_name,
                    "score": score.total_score,
                    "weight": weights[i],
                    "stocks": [],  # 个股列表
                    "redline_triggered": score.redline_triggered or [],
                }

                holding["industries"].append(industry_holding)

            holdings.append(holding)

            logger.debug(
                f"{date.date()}: 持仓 {len(selected_industries)} 个行业"
            )

        return holdings

    def _calculate_weights(
        self, scores: List[IndustryScore], method: str
    ) -> List[float]:
        """
        计算权重

        Args:
            scores: 行业评分列表
            method: 权重方法

        Returns:
            权重列表
        """
        n = len(scores)

        if n == 0:
            return []

        if method == WeightMethod.EQUAL:
            # 等权
            return [1.0 / n] * n

        elif method == WeightMethod.SCORE:
            # 评分加权
            total_score = sum(s.total_score or 0 for s in scores)
            if total_score == 0:
                return [1.0 / n] * n
            return [(s.total_score or 0) / total_score for s in scores]

        elif method == WeightMethod.MARKET_CAP:
            # 市值加权 (需要额外数据)
            # TODO: 实现市值加权
            logger.warning("市值加权暂未实现,使用等权")
            return [1.0 / n] * n

        else:
            return [1.0 / n] * n

    def _calculate_daily_returns(
        self,
        holdings: List[Dict],
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """
        计算每日收益

        Args:
            holdings: 持仓记录
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            每日收益 DataFrame (columns: date, return, cumulative_return)
        """
        # TODO: 实际实现需要从 API 获取个股价格数据
        # 这里返回模拟数据

        dates = pd.date_range(start_date, end_date, freq='D')
        returns = np.random.normal(0.001, 0.02, len(dates))  # 模拟收益
        cumulative = (1 + pd.Series(returns)).cumprod() - 1

        df = pd.DataFrame({
            "date": dates,
            "return": returns,
            "cumulative_return": cumulative,
        })

        logger.warning("使用模拟收益数据,实际实现需要从API获取")
        return df

    def _calculate_performance_metrics(
        self, daily_returns: pd.DataFrame
    ) -> Dict[str, float]:
        """
        计算绩效指标

        Args:
            daily_returns: 每日收益

        Returns:
            绩效指标字典
        """
        returns = daily_returns["return"].values

        # 总收益
        total_return = (1 + returns).prod() - 1

        # 年化收益
        trading_days = len(returns)
        years = trading_days / 252
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 夏普比率 (假设无风险利率为3%)
        risk_free_rate = 0.03
        excess_returns = returns - risk_free_rate / 252
        sharpe_ratio = (
            np.sqrt(252) * excess_returns.mean() / excess_returns.std()
            if excess_returns.std() > 0
            else 0
        )

        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        # 胜率
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0

        # 波动率
        volatility = returns.std() * np.sqrt(252)

        metrics = {
            "total_return": total_return * 100,
            "annual_return": annual_return * 100,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown * 100,
            "win_rate": win_rate * 100,
            "volatility": volatility * 100,
        }

        return metrics

    def _get_benchmark_return(
        self, benchmark: str, start_date: datetime, end_date: datetime
    ) -> float:
        """
        获取基准收益

        Args:
            benchmark: 基准指数代码
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            基准收益率(%)
        """
        # TODO: 实际实现需要从 API 获取基准指数数据
        # 这里返回模拟数据
        logger.warning(f"基准收益使用模拟数据: {benchmark}")
        return 15.0  # 模拟15%收益

    def _generate_trades(self, holdings: List[Dict]) -> List[Dict]:
        """
        生成交易记录

        Args:
            holdings: 持仓记录

        Returns:
            交易记录列表
        """
        trades = []

        for i in range(1, len(holdings)):
            prev_holding = holdings[i - 1]
            curr_holding = holdings[i]

            # 对比前后持仓,生成交易
            prev_codes = {
                ind["industry_code"] for ind in prev_holding["industries"]
            }
            curr_codes = {
                ind["industry_code"] for ind in curr_holding["industries"]
            }

            # 卖出
            sell_codes = prev_codes - curr_codes
            for code in sell_codes:
                prev_ind = next(
                    (
                        ind
                        for ind in prev_holding["industries"]
                        if ind["industry_code"] == code
                    ),
                    None,
                )
                if prev_ind:
                    trades.append({
                        "date": curr_holding["date"],
                        "action": "sell",
                        "industry_code": code,
                        "industry_name": prev_ind["industry_name"],
                        "reason": "重新平衡",
                    })

            # 买入
            buy_codes = curr_codes - prev_codes
            for code in buy_codes:
                curr_ind = next(
                    (
                        ind
                        for ind in curr_holding["industries"]
                        if ind["industry_code"] == code
                    ),
                    None,
                )
                if curr_ind:
                    trades.append({
                        "date": curr_holding["date"],
                        "action": "buy",
                        "industry_code": code,
                        "industry_name": curr_ind["industry_name"],
                        "score": curr_ind["score"],
                    })

        logger.info(f"生成 {len(trades)} 笔交易记录")
        return trades

    def _save_backtest_result(
        self,
        strategy_name: str,
        start_date: datetime,
        end_date: datetime,
        parameters: Dict,
        metrics: Dict,
        benchmark_code: str,
        benchmark_return: float,
        holdings: List[Dict],
        trades: List[Dict],
        daily_returns: pd.DataFrame,
    ) -> BacktestResult:
        """
        保存回测结果

        Args:
            strategy_name: 策略名称
            start_date: 起始日期
            end_date: 结束日期
            parameters: 回测参数
            metrics: 绩效指标
            benchmark_code: 基准代码
            benchmark_return: 基准收益
            holdings: 持仓记录
            trades: 交易记录
            daily_returns: 每日收益

        Returns:
            回测结果记录
        """
        backtest_name = f"{strategy_name}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

        result = BacktestResult(
            backtest_name=backtest_name,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters,
            total_return=metrics["total_return"],
            annual_return=metrics["annual_return"],
            sharpe_ratio=metrics["sharpe_ratio"],
            max_drawdown=metrics["max_drawdown"],
            win_rate=metrics["win_rate"],
            benchmark_code=benchmark_code,
            benchmark_return=benchmark_return,
            excess_return=metrics["total_return"] - benchmark_return,
            holdings=holdings,
            trades=trades,
            daily_returns=daily_returns.to_dict(orient="records"),
            performance_metrics=metrics,
        )

        self.session.add(result)
        self.session.commit()

        logger.info(f"回测结果已保存: {backtest_name}")
        return result

    def get_backtest_summary(self, backtest_name: str) -> Optional[Dict]:
        """
        获取回测摘要

        Args:
            backtest_name: 回测名称

        Returns:
            回测摘要字典
        """
        results = self.backtest_repo.get_by_name(backtest_name)

        if not results:
            return None

        result = results[0]

        summary = {
            "backtest_name": result.backtest_name,
            "strategy_name": result.strategy_name,
            "period": f"{result.start_date.date()} ~ {result.end_date.date()}",
            "total_return": f"{result.total_return:.2f}%",
            "annual_return": f"{result.annual_return:.2f}%",
            "sharpe_ratio": f"{result.sharpe_ratio:.2f}",
            "max_drawdown": f"{result.max_drawdown:.2f}%",
            "win_rate": f"{result.win_rate:.2f}%",
            "benchmark": result.benchmark_code,
            "benchmark_return": f"{result.benchmark_return:.2f}%",
            "excess_return": f"{result.excess_return:.2f}%",
            "num_trades": len(result.trades) if result.trades else 0,
        }

        return summary

    # ========== 股票池回测功能 ==========

    def run_stock_pool_backtest(
        self,
        strategy_name: str,
        start_date: datetime,
        end_date: datetime,
        min_score: Optional[float] = 60.0,
        max_stocks: Optional[int] = 30,
        weight_method: Optional[str] = None,
        rebalance_frequency: Optional[str] = None,
        benchmark: Optional[str] = None,
    ) -> BacktestResult:
        """
        运行股票池回测

        策略逻辑:
        1. 每期从优质公司池中选择得分最高的N只股票
        2. 按照指定的权重方法分配仓位
        3. 定期调仓(月度/季度)
        4. 计算收益率、夏普比率等绩效指标

        Args:
            strategy_name: 策略名称
            start_date: 起始日期
            end_date: 结束日期
            min_score: 最低入池分数
            max_stocks: 最多持仓股票数
            weight_method: 权重方法('equal'/'score'/'market_cap')
            rebalance_frequency: 调仓频率('monthly'/'quarterly')
            benchmark: 基准指数代码

        Returns:
            回测结果
        """
        # 使用默认配置
        if weight_method is None:
            weight_method = WeightMethod.EQUAL
        if rebalance_frequency is None:
            rebalance_frequency = RebalanceFrequency.MONTHLY
        if benchmark is None:
            benchmark = DEFAULT_BENCHMARK

        logger.info(
            f"开始股票池回测: {strategy_name} "
            f"({start_date.date()} ~ {end_date.date()})"
        )
        logger.info(
            f"参数: 最低分={min_score}, "
            f"最多持{max_stocks}只股票, 权重={weight_method}"
        )

        # 1. 获取再平衡日期列表
        rebalance_dates = self._get_rebalance_dates(
            start_date, end_date, rebalance_frequency
        )

        logger.info(f"再平衡次数: {len(rebalance_dates)}")

        # 2. 生成股票池持仓记录
        holdings = self._generate_stock_pool_holdings(
            rebalance_dates, min_score, max_stocks, weight_method
        )

        # 3. 计算每日收益
        daily_returns = self._calculate_stock_pool_daily_returns(
            holdings, start_date, end_date
        )

        # 4. 计算绩效指标
        metrics = self._calculate_performance_metrics(daily_returns)

        # 5. 获取基准收益
        benchmark_return = self._get_benchmark_return(
            benchmark, start_date, end_date
        )

        # 6. 生成交易记录
        trades = self._generate_stock_trades(holdings)

        # 7. 保存回测结果
        result = self._save_backtest_result(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            parameters={
                "type": "stock_pool",
                "min_score": min_score,
                "max_stocks": max_stocks,
                "weight_method": weight_method,
                "rebalance_frequency": rebalance_frequency,
            },
            metrics=metrics,
            benchmark_code=benchmark,
            benchmark_return=benchmark_return,
            holdings=holdings,
            trades=trades,
            daily_returns=daily_returns,
        )

        logger.success(
            f"股票池回测完成: 总收益{metrics['total_return']:.2f}%, "
            f"年化收益{metrics['annual_return']:.2f}%, "
            f"夏普比率{metrics['sharpe_ratio']:.2f}, "
            f"最大回撤{metrics['max_drawdown']:.2f}%"
        )

        return result

    def _generate_stock_pool_holdings(
        self,
        rebalance_dates: List[datetime],
        min_score: float,
        max_stocks: int,
        weight_method: str,
    ) -> List[Dict]:
        """
        生成股票池持仓记录

        Args:
            rebalance_dates: 再平衡日期列表
            min_score: 最低得分
            max_stocks: 最多持仓数
            weight_method: 权重方法

        Returns:
            持仓记录列表
        """
        from ..data.repository import StockScoreRepository

        score_repo = StockScoreRepository(self.session)
        holdings = []

        for date in rebalance_dates:
            # 获取优质公司池
            pool = score_repo.get_quality_pool(
                score_date=date, min_score=min_score, passed_only=True
            )

            # 按得分排序,选择前N只
            pool_sorted = sorted(
                pool, key=lambda x: x.total_score, reverse=True
            )
            selected_stocks = pool_sorted[:max_stocks]

            if len(selected_stocks) == 0:
                logger.warning(f"{date.date()}: 没有符合条件的股票")
                holdings.append({"date": date, "stocks": []})
                continue

            # 计算权重
            weights = self._calculate_stock_weights(
                selected_stocks, weight_method
            )

            # 构建持仓记录
            holding = {
                "date": date,
                "stocks": [
                    {
                        "stock_code": stock.stock_code,
                        "stock_name": stock.stock_name,
                        "industry_name": stock.industry_name,
                        "score": stock.total_score,
                        "weight": weights[i],
                    }
                    for i, stock in enumerate(selected_stocks)
                ],
            }

            holdings.append(holding)

            logger.debug(
                f"{date.date()}: 持仓 {len(selected_stocks)} 只股票, "
                f"平均得分 {sum(s.total_score for s in selected_stocks) / len(selected_stocks):.1f}"
            )

        return holdings

    def _calculate_stock_weights(
        self, stocks: List, method: str
    ) -> List[float]:
        """
        计算股票权重

        Args:
            stocks: 股票评分列表
            method: 权重方法

        Returns:
            权重列表
        """
        n = len(stocks)

        if n == 0:
            return []

        if method == WeightMethod.EQUAL:
            # 等权
            return [1.0 / n] * n

        elif method == WeightMethod.SCORE:
            # 评分加权
            total_score = sum(s.total_score or 0 for s in stocks)
            if total_score == 0:
                return [1.0 / n] * n
            return [(s.total_score or 0) / total_score for s in stocks]

        elif method == WeightMethod.MARKET_CAP:
            # 市值加权 (需要额外数据)
            logger.warning("市值加权暂未实现,使用等权")
            return [1.0 / n] * n

        else:
            return [1.0 / n] * n

    def _calculate_stock_pool_daily_returns(
        self,
        holdings: List[Dict],
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """
        计算股票池每日收益

        Args:
            holdings: 持仓记录
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            每日收益 DataFrame
        """
        # TODO: 实际实现需要从 API 获取个股价格数据
        # 这里返回模拟数据

        dates = pd.date_range(start_date, end_date, freq="D")
        returns = np.random.normal(0.0012, 0.018, len(dates))  # 模拟收益
        cumulative = (1 + pd.Series(returns)).cumprod() - 1

        df = pd.DataFrame({
            "date": dates,
            "return": returns,
            "cumulative_return": cumulative,
        })

        logger.warning("使用模拟收益数据,实际实现需要从API获取个股价格")
        return df

    def _generate_stock_trades(self, holdings: List[Dict]) -> List[Dict]:
        """
        生成股票交易记录

        Args:
            holdings: 持仓记录

        Returns:
            交易记录列表
        """
        trades = []

        for i in range(1, len(holdings)):
            prev_holding = holdings[i - 1]
            curr_holding = holdings[i]

            # 对比前后持仓
            prev_codes = {
                stock["stock_code"] for stock in prev_holding["stocks"]
            }
            curr_codes = {
                stock["stock_code"] for stock in curr_holding["stocks"]
            }

            # 卖出
            sell_codes = prev_codes - curr_codes
            for code in sell_codes:
                prev_stock = next(
                    (
                        s
                        for s in prev_holding["stocks"]
                        if s["stock_code"] == code
                    ),
                    None,
                )
                if prev_stock:
                    trades.append({
                        "date": curr_holding["date"],
                        "action": "sell",
                        "stock_code": code,
                        "stock_name": prev_stock["stock_name"],
                        "reason": "调仓",
                    })

            # 买入
            buy_codes = curr_codes - prev_codes
            for code in buy_codes:
                curr_stock = next(
                    (
                        s
                        for s in curr_holding["stocks"]
                        if s["stock_code"] == code
                    ),
                    None,
                )
                if curr_stock:
                    trades.append({
                        "date": curr_holding["date"],
                        "action": "buy",
                        "stock_code": code,
                        "stock_name": curr_stock["stock_name"],
                        "score": curr_stock["score"],
                    })

        logger.info(f"生成 {len(trades)} 笔股票交易记录")
        return trades
