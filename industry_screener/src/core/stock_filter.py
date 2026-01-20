"""
股票筛选器 - 三关卡筛选优质股票

筛选流程：
1. 第一关：基础资格筛选（Pass/Fail）
2. 第二关：排除项过滤（一票否决）
3. 第三关：质量评分（≥60分入池）
4. 行业分散度控制（单一行业≤35%）
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import yaml
from loguru import logger
from sqlalchemy.orm import Session

from ..data.models import Stock, StockCalculated, StockScore
from ..data.repository import (
    StockCalculatedRepository,
    StockRepository,
    StockScoreRepository,
)
from .calculator import IndicatorCalculator
from .stock_scorer import StockScorer


from ..utils.config_loader import get_config

from .base import BaseFilter

class StockFilter(BaseFilter):
    """股票筛选器"""

    def __init__(self, session: Session, config_path: Optional[str] = None):
        """
        初始化筛选器

        Args:
            session: 数据库会话
            config_path: 配置文件名（不含扩展名），默认为 'stock_scoring_weights'
        """
        # 加载配置
        if config_path is None:
            config_name = "stock_scoring_weights"
        else:
            # 如果传入了路径，尝试提取文件名作为配置名
            config_name = config_path.replace(".yaml", "").replace("config/", "")

        config = get_config(config_name)
        
        # 加载业务规则配置
        try:
            business_rules = get_config("business_rules")
            # 合并配置
            config.update(business_rules)
            logger.info("已加载业务规则配置 (business_rules.yaml)")
        except Exception as e:
            logger.warning(f"加载业务规则配置失败: {e}")

        super().__init__(session, config)
        
        self.stock_repo = StockRepository(session)
        self.calc_repo = StockCalculatedRepository(session)
        self.score_repo = StockScoreRepository(session)

        self.calculator = IndicatorCalculator()
        # 注意：这里我们使用已经加载的配置，而不是让 StockScorer 再次加载
        # 但 StockScorer 目前的设计是接收 config_path，所以暂时保持原样，
        # 后续可以重构 StockScorer 接收 config 字典
        # 修正：现在 StockScorer 也支持 config_name 逻辑，传入 config_name 即可
        self.scorer = StockScorer(session, config_name)

        logger.info(f"股票筛选器初始化完成，配置名: {config_name}")

    def filter(
        self,
        industries: List[str],
        calc_date: datetime,
        **kwargs
    ) -> Dict[str, any]:
        """
        执行三关卡筛选

        Args:
            industries: 优质行业列表（申万二级行业代码）
            calc_date: 筛选基准日期
            **kwargs: 
                min_score: 最低得分（默认60分）

        Returns:
            筛选结果字典
        """
        min_score = kwargs.get("min_score")
        if min_score is None:
            min_score = self.config.get("pass_threshold", 60)

        logger.info(f"开始股票筛选: {len(industries)} 个行业, 日期={calc_date}")

        # 步骤1：获取行业成分股
        candidates = self._get_industry_stocks(industries)
        logger.info(f"[1/7] 获取行业成分股: {len(candidates)} 只")

        # 步骤2：计算行业集中度
        industry_cr3 = self._calculate_industry_cr3(candidates, calc_date)
        logger.info(f"[2/7] 计算行业集中度: {len(industry_cr3)} 个行业")

        # 步骤3：基础资格筛选
        passed_basic = self._basic_qualification(candidates, calc_date, industry_cr3)
        logger.info(f"[3/7] 基础资格筛选: {len(passed_basic)} 只通过")

        # 步骤4：排除项过滤
        passed_exclusion, exclusion_reasons = self._exclusion_filter(
            passed_basic, calc_date
        )
        logger.info(f"[4/7] 排除项过滤: {len(passed_exclusion)} 只通过")

        # 步骤5：质量评分
        scored = self._quality_scoring(passed_exclusion, calc_date)
        logger.info(f"[5/7] 质量评分: {len(scored)} 只完成评分")

        # 步骤6：筛选入池
        pool = [s for s in scored if s.total_score >= min_score]
        pool.sort(key=lambda x: x.total_score, reverse=True)
        logger.info(f"[6/7] 筛选入池: {len(pool)} 只（≥{min_score}分）")

        # 步骤7：行业分散度控制
        final_pool = self._apply_diversification(pool)
        logger.info(f"[7/7] 行业分散度控制: {len(final_pool)} 只最终入池")

        # 统计信息
        result = {
            "date": calc_date,
            "industries": industries,
            "total_candidates": len(candidates),
            "passed_basic": len(passed_basic),
            "passed_exclusion": len(passed_exclusion),
            "scored": len(scored),
            "pool_before_diversification": len(pool),
            "final_pool": len(final_pool),
            "min_score": min_score,
            "pool": final_pool,
            "exclusion_reasons": exclusion_reasons,
        }

        logger.success(
            f"筛选完成: {len(final_pool)} 只股票入池 "
            f"(候选{len(candidates)} → 基础{len(passed_basic)} → "
            f"排除{len(passed_exclusion)} → 评分{len(pool)} → 最终{len(final_pool)})"
        )

        return result

    def _get_industry_stocks(self, industries: List[str]) -> List[Stock]:
        """获取行业成分股"""
        stocks = []

        for industry_code in industries:
            industry_stocks = self.stock_repo.get_by_industry(
                industry_code, active_only=True
            )
            stocks.extend(industry_stocks)

        # 去重
        unique_stocks = {s.stock_code: s for s in stocks}.values()

        return list(unique_stocks)

    def _calculate_industry_cr3(
        self, stocks: List[Stock], calc_date: datetime
    ) -> Dict[str, float]:
        """计算各行业的CR3集中度"""
        industry_revenues = defaultdict(list)

        # 按行业分组收集营收数据
        for stock in stocks:
            calc_data = self.calc_repo.get_by_stock_and_date(
                stock.stock_code, calc_date
            )
            if calc_data and calc_data.revenue:
                industry_revenues[stock.industry_code].append(calc_data.revenue)

        # 计算CR3
        industry_cr3 = {}
        for industry_code, revenues in industry_revenues.items():
            cr3 = self.calculator.calculate_cr3(revenues)
            if cr3:
                industry_cr3[industry_code] = cr3

        return industry_cr3

    def _basic_qualification(
        self,
        stocks: List[Stock],
        calc_date: datetime,
        industry_cr3: Dict[str, float],
    ) -> List[Stock]:
        """第一关：基础资格筛选"""
        config = self.config["basic_qualification"]
        passed = []

        for stock in stocks:
            calc_data = self.calc_repo.get_by_stock_and_date(
                stock.stock_code, calc_date
            )
            if not calc_data:
                continue

            # 1. 盈利能力
            if not self._check_profitability(calc_data, config["profitability"]):
                continue

            # 2. 财务安全
            if not self._check_financial_safety(calc_data, config["financial_safety"]):
                continue

            # 3. 龙头地位
            cr3 = industry_cr3.get(stock.industry_code, 0)
            if not self._check_leader_position(calc_data, cr3, config):
                continue

            passed.append(stock)

        return passed

    def _check_profitability(
        self, calc_data: StockCalculated, config: Dict
    ) -> bool:
        """检查盈利能力"""
        roe_min = config["roe_3y_avg_min"]
        roic_min = config["roic_3y_avg_min"]

        if calc_data.roe_3y_avg is None or calc_data.roe_3y_avg < roe_min:
            return False

        if calc_data.roic_3y_avg is None or calc_data.roic_3y_avg < roic_min:
            return False

        return True

    def _check_financial_safety(
        self, calc_data: StockCalculated, config: Dict
    ) -> bool:
        """检查财务安全"""
        if calc_data.debt_ratio is None or calc_data.debt_ratio > config["debt_ratio_max"]:
            return False

        if (
            calc_data.current_ratio is None
            or calc_data.current_ratio < config["current_ratio_min"]
        ):
            return False

        if (
            calc_data.quick_ratio is None
            or calc_data.quick_ratio < config["quick_ratio_min"]
        ):
            return False

        return True

    def _check_leader_position(
        self, calc_data: StockCalculated, cr3: float, config: Dict
    ) -> bool:
        """检查龙头地位"""
        if calc_data.revenue_rank is None:
            return False

        # 根据CR3确定龙头标准
        concentration_config = self.config["industry_concentration"]

        if cr3 >= concentration_config["high"]["cr3_threshold"]:
            # 高集中度：前3名
            top_n = concentration_config["high"]["top_n"]
        elif cr3 >= concentration_config["medium"]["cr3_threshold"]:
            # 中集中度：前2名
            top_n = concentration_config["medium"]["top_n"]
        else:
            # 低集中度：仅第1名
            top_n = concentration_config["low"]["top_n"]

        return calc_data.revenue_rank <= top_n

    def _exclusion_filter(
        self, stocks: List[Stock], calc_date: datetime
    ) -> Tuple[List[Stock], Dict[str, List[str]]]:
        """第二关：排除项过滤"""
        config = self.config["exclusion"]
        passed = []
        exclusion_reasons = defaultdict(list)

        for stock in stocks:
            reasons = []

            # 1. ST股票
            if config["st_stocks"]["enabled"] and stock.is_st:
                reasons.append("ST股票")

            # 2. 营收排名持续下降
            calc_data = self.calc_repo.get_by_stock_and_date(
                stock.stock_code, calc_date
            )
            if calc_data:
                if self._check_revenue_rank_decline(calc_data, config):
                    reasons.append("营收排名持续下降")

                # 3. 估值陷阱
                if self._check_valuation_trap(stock, calc_data, config):
                    reasons.append("估值陷阱")

                # 4. 治理风险
                if self._check_governance_risk(calc_data, config):
                    reasons.append("治理风险")

                # 5. 商誉地雷
                if self._check_goodwill_risk(calc_data, config):
                    reasons.append("商誉地雷")

                # 6. 连续业绩下滑
                if self._check_profit_decline(calc_data, config):
                    reasons.append("连续业绩下滑")

            if reasons:
                exclusion_reasons[stock.stock_code] = reasons
            else:
                passed.append(stock)

        return passed, dict(exclusion_reasons)

    def _check_revenue_rank_decline(
        self, calc_data: StockCalculated, config: Dict
    ) -> bool:
        """检查营收排名是否持续下降"""
        if not config["revenue_rank_decline"]["enabled"]:
            return False

        current_rank = calc_data.revenue_rank
        past_rank = calc_data.revenue_rank_3y_ago

        if current_rank is None or past_rank is None:
            return False

        # 排名数字越大表示排名越靠后
        return current_rank > past_rank

    def _check_valuation_trap(
        self, stock: Stock, calc_data: StockCalculated, config: Dict
    ) -> bool:
        """检查估值陷阱"""
        if not config["valuation_trap"]["enabled"]:
            return False

        # 判断是否为周期行业
        cyclical_industries = self.config.get("cyclical_industries", [])
        is_cyclical = stock.industry_name in cyclical_industries

        if is_cyclical:
            # 周期股：允许ROE波动，但近3年ROE最低值不能太低
            roe_min_threshold = config["valuation_trap"]["cyclical"]["roe_min"]
            if calc_data.roe_min_3y is not None and calc_data.roe_min_3y < roe_min_threshold:
                return True
        else:
            # 非周期股：PE很低但ROE持续下降（斜率为负）
            roe_slope_threshold = config["valuation_trap"]["non_cyclical"]["roe_slope_threshold"]
            if calc_data.roe_slope is not None and calc_data.roe_slope < roe_slope_threshold:
                return True

        return False

    def _check_governance_risk(
        self, calc_data: StockCalculated, config: Dict
    ) -> bool:
        """检查治理风险"""
        if not config["governance_risk"]["enabled"]:
            return False

        # 质押比例
        if (
            calc_data.pledge_ratio is not None
            and calc_data.pledge_ratio > config["governance_risk"]["pledge_ratio_max"]
        ):
            return True

        # 关联交易
        if (
            calc_data.related_transaction_ratio is not None
            and calc_data.related_transaction_ratio
            > config["governance_risk"]["related_transaction_ratio_max"]
        ):
            return True

        return False

    def _check_goodwill_risk(self, calc_data: StockCalculated, config: Dict) -> bool:
        """检查商誉地雷"""
        if not config["goodwill_risk"]["enabled"]:
            return False

        if (
            calc_data.goodwill_ratio is not None
            and calc_data.goodwill_ratio > config["goodwill_risk"]["goodwill_ratio_max"]
        ):
            return True

        return False

    def _check_profit_decline(self, calc_data: StockCalculated, config: Dict) -> bool:
        """检查连续业绩下滑"""
        if not config["profit_decline"]["enabled"]:
            return False

        # TODO: 需要历史净利润数据
        # 这里简化处理
        return False

    def _quality_scoring(
        self, stocks: List[Stock], calc_date: datetime
    ) -> List[StockScore]:
        """第三关：质量评分"""
        stock_codes = [s.stock_code for s in stocks]
        scores = self.scorer.batch_score(stock_codes, calc_date)

        # 更新筛选状态
        for score in scores:
            score.passed_basic = True
            score.passed_exclusion = True
            score.passed_scoring = score.total_score >= self.config.get(
                "pass_threshold", 60
            )

        return scores

    def _apply_diversification(self, pool: List[StockScore]) -> List[StockScore]:
        """行业分散度控制"""
        config = self.config["diversification"]

        if not config["enabled"]:
            return pool

        if len(pool) < config["min_pool_size_for_diversification"]:
            return pool

        max_ratio = config["max_industry_ratio"]
        max_count = int(len(pool) * max_ratio)

        # 按行业分组
        industry_stocks = defaultdict(list)
        for score in pool:
            industry_stocks[score.industry_code].append(score)

        # 应用分散度控制
        final_pool = []
        for industry_code, stocks in industry_stocks.items():
            if len(stocks) <= config["small_industry_threshold"]:
                # 小行业不受限制
                final_pool.extend(stocks)
            else:
                # 按得分排序，取前max_count只
                stocks.sort(key=lambda x: x.total_score, reverse=True)
                final_pool.extend(stocks[:max_count])

        # 重新排序
        final_pool.sort(key=lambda x: x.total_score, reverse=True)

        return final_pool

    def save_results(self, result: Dict) -> int:
        """保存筛选结果到数据库"""
        pool = result["pool"]
        count = self.scorer.save_scores(pool)

        logger.info(f"筛选结果已保存: {count} 条记录")

        return count
