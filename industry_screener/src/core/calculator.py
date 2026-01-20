"""
计算引擎 - 负责计算23个核心指标

包含:
- 竞争格局指标 (5个)
- 盈利能力指标 (6个)
- 成长性指标 (3个)
- 现金流指标 (2个)
- 估值指标 (5个)
- 景气度指标 (宏观数据,直接使用)
- 周期位置指标 (3个)
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from ..utils import InventoryCyclePosition, Trend


class IndicatorCalculator:
    """指标计算器"""

    def __init__(self):
        """初始化计算器"""
        pass

    # ========== 竞争格局指标 ==========

    def calculate_cr5(
        self, market_shares: List[float]
    ) -> Optional[float]:
        """
        计算 CR5 集中度 (前5家市占率之和)

        Args:
            market_shares: 市场份额列表(降序)

        Returns:
            CR5 值(%)
        """
        if not market_shares or len(market_shares) == 0:
            return None

        # 取前5家
        top_5 = sorted(market_shares, reverse=True)[:5]
        cr5 = sum(top_5)

        logger.debug(f"CR5 = {cr5:.2f}%")
        return cr5

    def calculate_leader_share_change(
        self,
        current_share: float,
        previous_share: float,
        years: float = 1.0,
    ) -> Optional[float]:
        """
        计算龙头市占率变化 (百分点/年)

        Args:
            current_share: 当前市占率(%)
            previous_share: 之前市占率(%)
            years: 时间间隔(年)

        Returns:
            市占率变化(百分点/年)
        """
        if current_share is None or previous_share is None or years <= 0:
            return None

        change = (current_share - previous_share) / years
        logger.debug(f"龙头市占率变化 = {change:.2f} pct/年")
        return change

    def calculate_price_volatility(
        self, prices: pd.Series
    ) -> Optional[float]:
        """
        计算价格波动率 (标准差/均值)

        Args:
            prices: 价格序列

        Returns:
            波动率(%)
        """
        if prices is None or len(prices) < 2:
            return None

        mean = prices.mean()
        std = prices.std()

        if mean == 0:
            return None

        volatility = (std / mean) * 100
        logger.debug(f"价格波动率 = {volatility:.2f}%")
        return volatility

    # ========== 盈利能力指标 ==========

    def calculate_roe_level(
        self,
        roe: float,
        market_median: float = 8.0,
        historical_data: Optional[pd.Series] = None,
    ) -> str:
        """
        判断 ROE 水平

        Args:
            roe: 当前 ROE(%)
            market_median: 市场中位数
            historical_data: 历史 ROE 数据

        Returns:
            水平描述: '优秀水平' / '良好水平' / '一般水平'
        """
        if roe is None:
            return "一般水平"

        above_market = roe > market_median
        above_hist = False

        if historical_data is not None and len(historical_data) > 0:
            hist_50pct = historical_data.quantile(0.5)
            above_hist = roe > hist_50pct

        if above_market and above_hist:
            return "优秀水平"
        elif above_market or above_hist:
            return "良好水平"
        else:
            return "一般水平"

    def calculate_roe_trend(
        self,
        current_roe: float,
        previous_roe: float,
        threshold: float = 0.5,
    ) -> str:
        """
        判断 ROE 趋势

        Args:
            current_roe: 当前 ROE(%)
            previous_roe: 之前 ROE(%)
            threshold: 平稳阈值(pct)

        Returns:
            趋势: 'improving' / 'stable' / 'declining'
        """
        if current_roe is None or previous_roe is None:
            return Trend.STABLE

        change = current_roe - previous_roe

        if change > threshold:
            return Trend.IMPROVING
        elif change < -threshold:
            return Trend.DECLINING
        else:
            return Trend.STABLE

    def calculate_gross_margin_level(
        self,
        current_margin: float,
        historical_data: Optional[pd.Series] = None,
    ) -> str:
        """
        判断毛利率水平

        Args:
            current_margin: 当前毛利率(%)
            historical_data: 5年历史数据

        Returns:
            水平描述
        """
        if current_margin is None:
            return "低于5年均值"

        if historical_data is not None and len(historical_data) > 0:
            avg_5y = historical_data.mean()
            if current_margin > avg_5y:
                return "高于5年均值"

        return "低于5年均值"

    def calculate_gross_margin_trend(
        self, margins: pd.Series, threshold: float = 1.0
    ) -> str:
        """
        判断毛利率趋势

        Args:
            margins: 毛利率序列(至少2个点)
            threshold: 平稳阈值(pct)

        Returns:
            趋势: 'rising' / 'stable' / 'falling'
        """
        if margins is None or len(margins) < 2:
            return Trend.STABLE

        # 线性回归判断趋势
        x = np.arange(len(margins))
        slope = np.polyfit(x, margins.values, 1)[0]

        if slope > threshold:
            return Trend.RISING
        elif slope < -threshold:
            return Trend.FALLING
        else:
            return Trend.STABLE

    # ========== 成长性指标 ==========

    def calculate_growth_rate(
        self, current: float, previous: float
    ) -> Optional[float]:
        """
        计算增长率

        Args:
            current: 当前值
            previous: 之前值

        Returns:
            增长率(%)
        """
        if current is None or previous is None or previous == 0:
            return None

        growth = ((current - previous) / abs(previous)) * 100
        return growth

    def calculate_profit_elasticity(
        self, profit_growth: float, revenue_growth: float
    ) -> Optional[float]:
        """
        计算利润弹性 (利润增速 / 营收增速)

        Args:
            profit_growth: 利润增速(%)
            revenue_growth: 营收增速(%)

        Returns:
            利润弹性
        """
        if (
            profit_growth is None
            or revenue_growth is None
            or revenue_growth == 0
        ):
            return None

        elasticity = profit_growth / revenue_growth
        logger.debug(f"利润弹性 = {elasticity:.2f}")
        return elasticity

    # ========== 现金流指标 ==========

    def calculate_ocf_ni_ratio(
        self, ocf: float, net_income: float
    ) -> Optional[float]:
        """
        计算经营现金流/净利润比率

        Args:
            ocf: 经营现金流
            net_income: 净利润

        Returns:
            比率(%)
        """
        if ocf is None or net_income is None or net_income == 0:
            return None

        ratio = (ocf / abs(net_income)) * 100
        logger.debug(f"OCF/NI 比率 = {ratio:.2f}%")
        return ratio

    def calculate_capex_intensity(
        self, capex: float, depreciation: float
    ) -> Optional[float]:
        """
        计算资本开支强度 (资本开支 / 折旧)

        Args:
            capex: 资本开支
            depreciation: 折旧

        Returns:
            强度倍数
        """
        if capex is None or depreciation is None or depreciation == 0:
            return None

        intensity = capex / depreciation
        logger.debug(f"资本开支强度 = {intensity:.2f}")
        return intensity

    # ========== 估值指标 ==========

    def calculate_percentile(
        self, current_value: float, historical_data: pd.Series
    ) -> Optional[float]:
        """
        计算历史分位数

        Args:
            current_value: 当前值
            historical_data: 历史数据序列

        Returns:
            分位数(0-100)
        """
        if (
            current_value is None
            or historical_data is None
            or len(historical_data) < 2
        ):
            return None

        # 计算当前值在历史数据中的百分位
        percentile = (
            (historical_data < current_value).sum() / len(historical_data)
        ) * 100

        logger.debug(f"历史分位数 = {percentile:.1f}%")
        return percentile

    def calculate_peg(
        self, pe: float, profit_growth_forecast: float
    ) -> Optional[float]:
        """
        计算 PEG (PE / 利润增速预测)

        Args:
            pe: 市盈率
            profit_growth_forecast: 利润增速预测(%)

        Returns:
            PEG 值
        """
        if (
            pe is None
            or profit_growth_forecast is None
            or profit_growth_forecast <= 0
        ):
            return None

        peg = pe / profit_growth_forecast
        logger.debug(f"PEG = {peg:.2f}")
        return peg

    # ========== 周期位置指标 ==========

    def determine_inventory_cycle_position(
        self,
        inventory_yoy: float,
        revenue_yoy: float,
        thresholds: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> str:
        """
        判断库存周期位置

        库存周期四象限:
        - 被动补库存: 库存↑ + 收入↑ (景气上行)
        - 主动补库存: 库存↑ + 收入↓ (景气高位)
        - 被动去库存: 库存↓ + 收入↓ (景气下行)
        - 主动去库存: 库存↓ + 收入↑ (景气底部)

        Args:
            inventory_yoy: 库存同比(%)
            revenue_yoy: 收入同比(%)
            thresholds: 阈值配置

        Returns:
            周期位置
        """
        if inventory_yoy is None or revenue_yoy is None:
            return InventoryCyclePosition.TRANSITION

        # 默认阈值
        if thresholds is None:
            thresholds = {
                "inventory_yoy": {"rising": 5, "falling": -5},
                "revenue_yoy": {"high": 10, "low": -5},
            }

        # 判断库存是否上升
        inventory_rising = (
            inventory_yoy > thresholds["inventory_yoy"]["rising"]
        )
        inventory_falling = (
            inventory_yoy < thresholds["inventory_yoy"]["falling"]
        )

        # 判断收入是否高增长
        revenue_high = revenue_yoy > thresholds["revenue_yoy"]["high"]
        revenue_low = revenue_yoy < thresholds["revenue_yoy"]["low"]

        # 四象限判断
        if inventory_rising:
            if revenue_high:
                return InventoryCyclePosition.PASSIVE_RESTOCKING
            elif revenue_low:
                return InventoryCyclePosition.ACTIVE_RESTOCKING
        elif inventory_falling:
            if revenue_low:
                return InventoryCyclePosition.PASSIVE_DESTOCKING
            elif revenue_high:
                return InventoryCyclePosition.ACTIVE_DESTOCKING

        return InventoryCyclePosition.TRANSITION

    def calculate_inventory_turnover_change(
        self, current_days: float, previous_days: float
    ) -> Tuple[str, float]:
        """
        计算存货周转天数变化

        Args:
            current_days: 当前周转天数
            previous_days: 之前周转天数

        Returns:
            (描述, 变化率%)
        """
        if current_days is None or previous_days is None or previous_days == 0:
            return "正常波动", 0.0

        change_pct = (
            (current_days - previous_days) / previous_days
        ) * 100

        if change_pct < 0:
            desc = "去库顺畅"
        elif abs(change_pct) < 10:
            desc = "正常波动"
        elif 10 <= abs(change_pct) < 20:
            desc = "库存积压"
        else:
            desc = "严重积压"

        logger.debug(f"存货周转变化: {desc}, {change_pct:.1f}%")
        return desc, change_pct

    # ========== 辅助方法 ==========

    def validate_data(self, data: pd.Series, min_points: int = 2) -> bool:
        """
        验证数据有效性

        Args:
            data: 数据序列
            min_points: 最少数据点数

        Returns:
            是否有效
        """
        if data is None or len(data) < min_points:
            return False

        # 检查缺失值比例
        missing_ratio = data.isna().sum() / len(data)
        if missing_ratio > 0.5:  # 缺失超过50%
            logger.warning(f"数据缺失率过高: {missing_ratio:.1%}")
            return False

        return True

    def handle_outliers(
        self, data: pd.Series, method: str = "winsorize", percentile: float = 0.05
    ) -> pd.Series:
        """
        处理异常值

        Args:
            data: 数据序列
            method: 处理方法 ('winsorize' / 'clip')
            percentile: 百分位阈值

        Returns:
            处理后的数据
        """
        if method == "winsorize":
            lower = data.quantile(percentile)
            upper = data.quantile(1 - percentile)
            return data.clip(lower, upper)
        elif method == "clip":
            # 使用 3 倍标准差
            mean = data.mean()
            std = data.std()
            return data.clip(mean - 3 * std, mean + 3 * std)
        else:
            return data

    # ========== 股票指标计算（新增） ==========

    def calculate_roe(
        self, net_profit: float, equity: float
    ) -> Optional[float]:
        """
        计算ROE
        
        Args:
            net_profit: 净利润
            equity: 股东权益
            
        Returns:
            ROE值(%)
        """
        if equity is None or equity == 0:
            return None
        return (net_profit / equity) * 100

    def calculate_roe_3y_avg(self, roe_values: List[float]) -> Optional[float]:
        """
        计算3年平均ROE

        Args:
            roe_values: ROE值列表（至少3个）

        Returns:
            3年平均ROE
        """
        if not roe_values or len(roe_values) < 3:
            return None
        return sum(roe_values[-3:]) / 3

    def calculate_roic(
        self,
        net_profit: float,
        interest_expense: float,
        tax_rate: float,
        equity: float,
        interest_bearing_debt: float,
    ) -> Optional[float]:
        """
        计算ROIC (投入资本回报率)

        Args:
            net_profit: 净利润
            interest_expense: 利息费用
            tax_rate: 税率
            equity: 股东权益
            interest_bearing_debt: 有息负债

        Returns:
            ROIC值
        """
        # NOPAT = 净利润 + 利息费用 × (1 - 税率)
        nopat = net_profit + interest_expense * (1 - tax_rate)

        # 投入资本 = 股东权益 + 有息负债
        invested_capital = equity + interest_bearing_debt

        if invested_capital == 0:
            return None

        return nopat / invested_capital

    def calculate_roic_3y_avg(self, roic_values: List[float]) -> Optional[float]:
        """
        计算3年平均ROIC

        Args:
            roic_values: ROIC值列表（至少3个）

        Returns:
            3年平均ROIC
        """
        if not roic_values or len(roic_values) < 3:
            return None
        return sum(roic_values[-3:]) / 3

    def calculate_cr3(self, revenues: List[float]) -> Optional[float]:
        """
        计算行业集中度CR3

        Args:
            revenues: 行业内所有公司的营收列表

        Returns:
            CR3值（前3名营收占比）
        """
        if not revenues or len(revenues) == 0:
            return None

        total_revenue = sum(revenues)
        if total_revenue == 0:
            return None

        top_3 = sorted(revenues, reverse=True)[:3]
        cr3 = sum(top_3) / total_revenue

        logger.debug(f"CR3 = {cr3:.2%}")
        return cr3

    def calculate_revenue_rank(
        self, stock_code: str, industry_revenues: Dict[str, float]
    ) -> Optional[int]:
        """
        计算营收排名

        Args:
            stock_code: 股票代码
            industry_revenues: 行业内所有公司的营收字典 {股票代码: 营收}

        Returns:
            排名（1表示第一名）
        """
        if not industry_revenues or stock_code not in industry_revenues:
            return None

        sorted_stocks = sorted(
            industry_revenues.items(), key=lambda x: x[1], reverse=True
        )

        for rank, (code, _) in enumerate(sorted_stocks, 1):
            if code == stock_code:
                return rank

        return None

    def calculate_cagr(
        self, start_value: float, end_value: float, years: int
    ) -> Optional[float]:
        """
        计算复合年均增长率 (CAGR)

        Args:
            start_value: 起始值
            end_value: 结束值
            years: 年数

        Returns:
            CAGR值
        """
        if start_value is None or end_value is None or years <= 0:
            return None

        if start_value <= 0:
            return None

        cagr = (end_value / start_value) ** (1 / years) - 1
        logger.debug(f"CAGR = {cagr:.2%}")
        return cagr

    def calculate_debt_ratio(
        self, total_liabilities: float, total_assets: float
    ) -> Optional[float]:
        """
        计算资产负债率

        Args:
            total_liabilities: 总负债
            total_assets: 总资产

        Returns:
            负债率
        """
        if total_assets is None or total_assets == 0:
            return None
        return total_liabilities / total_assets

    def calculate_current_ratio(
        self, current_assets: float, current_liabilities: float
    ) -> Optional[float]:
        """
        计算流动比率

        Args:
            current_assets: 流动资产
            current_liabilities: 流动负债

        Returns:
            流动比率
        """
        if current_liabilities is None or current_liabilities == 0:
            return None
        return current_assets / current_liabilities

    def calculate_quick_ratio(
        self,
        current_assets: float,
        inventory: float,
        current_liabilities: float,
    ) -> Optional[float]:
        """
        计算速动比率

        Args:
            current_assets: 流动资产
            inventory: 存货
            current_liabilities: 流动负债

        Returns:
            速动比率
        """
        if current_liabilities is None or current_liabilities == 0:
            return None

        quick_assets = current_assets - inventory
        return quick_assets / current_liabilities

    def calculate_ocf_ni_ratio(
        self, operating_cashflow: float, net_income: float
    ) -> Optional[float]:
        """
        计算经营现金流/净利润比率

        Args:
            operating_cashflow: 经营性现金流
            net_income: 净利润

        Returns:
            现金流/净利润比率
        """
        if net_income is None or net_income == 0:
            return None
        return operating_cashflow / net_income

    def calculate_gross_margin(
        self, revenue: float, cost_of_revenue: float
    ) -> Optional[float]:
        """
        计算毛利率
        
        Args:
            revenue: 营业收入
            cost_of_revenue: 营业成本
            
        Returns:
            毛利率(%)
        """
        if revenue is None or revenue == 0:
            return None
            
        gross_profit = revenue - cost_of_revenue
        return (gross_profit / revenue) * 100

    def calculate_gross_margin_vs_industry(
        self, company_margin: float, industry_median: float
    ) -> Optional[float]:
        """
        计算毛利率相对行业优势

        Args:
            company_margin: 公司毛利率
            industry_median: 行业中位数毛利率

        Returns:
            相对优势百分比
        """
        if industry_median is None or industry_median == 0:
            return None

        return (company_margin - industry_median) / industry_median

    def calculate_roe_slope(self, roe_values: List[float]) -> Optional[float]:
        """
        计算ROE斜率（用于判断趋势）

        Args:
            roe_values: ROE值列表（按时间顺序）

        Returns:
            斜率值
        """
        if not roe_values or len(roe_values) < 2:
            return None

        # 简单线性回归
        n = len(roe_values)
        x = list(range(n))
        y = roe_values

        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return None

        slope = numerator / denominator
        return slope
