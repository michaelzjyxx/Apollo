"""
评分引擎 - 基于YAML配置的参数化评分系统

功能:
1. 加载评分权重配置
2. 计算各维度评分
3. 检测红线触发
4. 汇总总分并排名
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from ..data import (
    CalculatedIndicator,
    IndustryScore,
    QualitativeScore,
    QualitativeScoreRepository,
)
from ..utils import (
    CONSUMER_INDUSTRIES,
    CYCLICAL_INDUSTRIES,
    InventoryCyclePosition,
    Trend,
    get_config,
)


from .base import BaseScorer

class IndustryScorer(BaseScorer):
    """行业评分引擎"""

    def __init__(self):
        """初始化评分引擎"""
        # 加载评分权重配置
        config = get_config("scoring_weights")
        super().__init__(config)
        self.weights = config  # 兼容旧代码使用 self.weights
        self.total_score = self.weights.get("total_score", 100)

        logger.info("行业评分引擎初始化成功")

    def score(self, entity_id: str, date: Any) -> Any:
        # TODO: 实现统一的score接口，目前保留原有的分维度评分方法供外部调用
        # 这里暂时作为占位符，因为实际调用是分步骤的
        pass

    # ========== 竞争格局评分 (15分) ==========

    def score_competition(self, indicator: CalculatedIndicator) -> Dict[str, Any]:
        """
        竞争格局评分

        Args:
            indicator: 计算指标

        Returns:
            评分详情字典
        """
        config = self.weights["competition"]
        total_weight = config["total_weight"]
        score = 0.0
        details = {}

        # 1. CR5 集中度 (5分)
        cr5_score = self._apply_rules(
            indicator.cr5, config["cr5"]["rules"]
        )
        score += cr5_score
        details["cr5"] = {"value": indicator.cr5, "score": cr5_score}

        # 2. 龙头市占率变化 (5分)
        leader_change_score = self._apply_rules(
            indicator.leader_share_change,
            config["leader_share_change"]["rules"],
        )
        score += leader_change_score
        details["leader_share_change"] = {
            "value": indicator.leader_share_change,
            "score": leader_change_score,
        }

        # 3. 价格波动率 (3分)
        volatility_score = self._apply_rules(
            indicator.price_volatility,
            config["price_volatility"]["rules"],
        )
        score += volatility_score
        details["price_volatility"] = {
            "value": indicator.price_volatility,
            "score": volatility_score,
        }

        # 4. 产能利用率 (2分)
        capacity_score = self._apply_rules(
            indicator.capacity_utilization,
            config["capacity_utilization"]["rules"],
        )
        score += capacity_score
        details["capacity_utilization"] = {
            "value": indicator.capacity_utilization,
            "score": capacity_score,
        }

        logger.debug(f"竞争格局评分: {score}/{total_weight}")
        return {"score": score, "details": details}

    # ========== 盈利能力评分 (15分) ==========

    def score_profitability(self, indicator: CalculatedIndicator) -> Dict[str, Any]:
        """
        盈利能力评分

        Args:
            indicator: 计算指标

        Returns:
            评分详情字典
        """
        config = self.weights["profitability"]
        total_weight = config["total_weight"]
        score = 0.0
        details = {}

        # 1. ROE 水平 (8分)
        roe_level_score = self._score_roe_level(
            indicator.roe, indicator.roe_level, config["roe_level"]
        )
        score += roe_level_score
        details["roe_level"] = {
            "value": indicator.roe,
            "level": indicator.roe_level,
            "score": roe_level_score,
        }

        # 2. ROE 趋势 (3分)
        roe_trend_score = self._score_trend(
            indicator.roe_trend, config["roe_trend"]["rules"]
        )
        score += roe_trend_score
        details["roe_trend"] = {
            "trend": indicator.roe_trend,
            "score": roe_trend_score,
        }

        # 3. 毛利率水平 (2分)
        margin_level_score = self._score_by_condition(
            indicator.gross_margin_level,
            config["gross_margin_level"]["rules"],
        )
        score += margin_level_score
        details["gross_margin_level"] = {
            "level": indicator.gross_margin_level,
            "score": margin_level_score,
        }

        # 4. 毛利率趋势 (2分)
        margin_trend_score = self._score_trend(
            indicator.gross_margin_trend,
            config["gross_margin_trend"]["rules"],
        )
        score += margin_trend_score
        details["gross_margin_trend"] = {
            "trend": indicator.gross_margin_trend,
            "score": margin_trend_score,
        }

        logger.debug(f"盈利能力评分: {score}/{total_weight}")
        return {"score": score, "details": details}

    # ========== 成长性评分 (10分) ==========

    def score_growth(self, indicator: CalculatedIndicator) -> Dict[str, Any]:
        """
        成长性评分

        Args:
            indicator: 计算指标

        Returns:
            评分详情字典
        """
        config = self.weights["growth"]
        total_weight = config["total_weight"]
        gdp_growth = config["gdp_growth_rate"]
        score = 0.0
        details = {}

        # 1. 营收增速 (5分)
        revenue_score = self._score_revenue_growth(
            indicator.revenue_growth, gdp_growth, config["revenue_growth"]
        )
        score += revenue_score
        details["revenue_growth"] = {
            "value": indicator.revenue_growth,
            "score": revenue_score,
        }

        # 2. 利润增速 (3分)
        profit_score = self._score_profit_growth(
            indicator.profit_growth,
            indicator.revenue_growth,
            config["profit_growth"],
        )
        score += profit_score
        details["profit_growth"] = {
            "value": indicator.profit_growth,
            "score": profit_score,
        }

        # 3. 利润弹性 (2分)
        elasticity_score = self._apply_rules(
            indicator.profit_elasticity,
            config["profit_elasticity"]["rules"],
        )
        score += elasticity_score
        details["profit_elasticity"] = {
            "value": indicator.profit_elasticity,
            "score": elasticity_score,
        }

        logger.debug(f"成长性评分: {score}/{total_weight}")
        return {"score": score, "details": details}

    # ========== 现金流评分 (10分) ==========

    def score_cashflow(self, indicator: CalculatedIndicator) -> Dict[str, Any]:
        """
        现金流评分

        Args:
            indicator: 计算指标

        Returns:
            评分详情字典
        """
        config = self.weights["cashflow"]
        total_weight = config["total_weight"]
        score = 0.0
        details = {}

        # 1. OCF/NI 比率 (6分)
        ocf_score = self._apply_rules(
            indicator.ocf_ni_ratio, config["ocf_ni_ratio"]["rules"]
        )
        score += ocf_score
        details["ocf_ni_ratio"] = {
            "value": indicator.ocf_ni_ratio,
            "score": ocf_score,
        }

        # 2. 资本开支强度 (4分)
        capex_score = self._apply_rules(
            indicator.capex_intensity,
            config["capex_intensity"]["rules"],
        )
        score += capex_score
        details["capex_intensity"] = {
            "value": indicator.capex_intensity,
            "score": capex_score,
        }

        logger.debug(f"现金流评分: {score}/{total_weight}")
        return {"score": score, "details": details}

    # ========== 估值评分 (10分) ==========

    def score_valuation(self, indicator: CalculatedIndicator) -> Dict[str, Any]:
        """
        估值评分

        Args:
            indicator: 计算指标

        Returns:
            评分详情字典
        """
        config = self.weights["valuation"]
        total_weight = config["total_weight"]
        score = 0.0
        details = {}

        # 1. PE 分位数 (4分)
        pe_score = self._apply_rules(
            indicator.pe_percentile,
            config["pe_percentile"]["rules"],
        )
        score += pe_score
        details["pe_percentile"] = {
            "value": indicator.pe_percentile,
            "score": pe_score,
        }

        # 2. PB 分位数 (3分)
        pb_score = self._apply_rules(
            indicator.pb_percentile,
            config["pb_percentile"]["rules"],
        )
        score += pb_score
        details["pb_percentile"] = {
            "value": indicator.pb_percentile,
            "score": pb_score,
        }

        # 3. PEG (3分)
        peg_score = self._apply_rules(
            indicator.peg, config["peg"]["rules"]
        )
        score += peg_score
        details["peg"] = {"value": indicator.peg, "score": peg_score}

        logger.debug(f"估值评分: {score}/{total_weight}")
        return {"score": score, "details": details}

    # ========== 景气度评分 (5分) ==========

    def score_sentiment(
        self, indicator: CalculatedIndicator, industry_name: str
    ) -> Dict[str, Any]:
        """
        景气度评分

        Args:
            indicator: 计算指标
            industry_name: 行业名称

        Returns:
            评分详情字典
        """
        config = self.weights["sentiment"]
        total_weight = config["total_weight"]
        score = 0.0
        details = {}

        # 1. PMI & 新订单 (2分)
        pmi_score = self._score_pmi(
            indicator.pmi, indicator.new_order, config["pmi_new_order"]
        )
        score += pmi_score
        details["pmi_new_order"] = {
            "pmi": indicator.pmi,
            "new_order": indicator.new_order,
            "score": pmi_score,
        }

        # 2. M2 & 社融 (1.5分)
        m2_score = self._apply_rules(
            indicator.m2, config["m2_social_financing"]["rules"]
        )
        score += m2_score
        details["m2_social_financing"] = {
            "m2": indicator.m2,
            "social_financing": indicator.social_financing,
            "score": m2_score,
        }

        # 3. PPI/CPI (1.5分) - 根据行业类型
        price_score = self._score_ppi_cpi(
            indicator.ppi,
            indicator.cpi,
            industry_name,
            config["ppi_cpi"],
        )
        score += price_score
        details["ppi_cpi"] = {
            "ppi": indicator.ppi,
            "cpi": indicator.cpi,
            "score": price_score,
        }

        logger.debug(f"景气度评分: {score}/{total_weight}")
        return {"score": score, "details": details}

    # ========== 周期位置评分 (5分) ==========

    def score_cycle(self, indicator: CalculatedIndicator) -> Dict[str, Any]:
        """
        周期位置评分

        Args:
            indicator: 计算指标

        Returns:
            评分详情字典
        """
        config = self.weights["cycle"]
        total_weight = config["total_weight"]
        score = 0.0
        details = {}

        # 1. 库存周期位置 (3分)
        cycle_score = self._score_inventory_cycle(
            indicator.inventory_cycle_position,
            config["inventory_cycle"]["rules"],
        )
        score += cycle_score
        details["inventory_cycle"] = {
            "position": indicator.inventory_cycle_position,
            "score": cycle_score,
        }

        # 2. 存货周转 (2分) - 需要额外数据支持
        # 暂时占位
        turnover_score = 0.0
        details["inventory_turnover"] = {
            "days": indicator.inventory_turnover,
            "score": turnover_score,
        }

        logger.debug(f"周期位置评分: {score}/{total_weight}")
        return {"score": score, "details": details}

    # ========== 定性评分 (20分) ==========

    def score_qualitative(
        self, qualitative: QualitativeScore
    ) -> Dict[str, Any]:
        """
        定性评分 (从预设库读取)

        Args:
            qualitative: 定性评分记录

        Returns:
            评分详情字典
        """
        config = self.weights["qualitative"]
        total_weight = config["total_weight"]

        score = (
            qualitative.policy_score
            + qualitative.business_model_score
            + qualitative.barrier_score
            + qualitative.moat_score
        )

        details = {
            "policy": {
                "score": qualitative.policy_score,
                "reason": qualitative.policy_reason,
            },
            "business_model": {
                "score": qualitative.business_model_score,
                "reason": qualitative.business_model_reason,
            },
            "barrier": {
                "score": qualitative.barrier_score,
                "reason": qualitative.barrier_reason,
            },
            "moat": {
                "score": qualitative.moat_score,
                "reason": qualitative.moat_reason,
            },
        }

        logger.debug(f"定性评分: {score}/{total_weight}")
        return {"score": score, "details": details}

    # ========== 红线检测 ==========

    def check_redlines(
        self,
        indicator: CalculatedIndicator,
        historical_indicators: List[CalculatedIndicator],
    ) -> Dict[str, Any]:
        """
        检测红线触发

        Args:
            indicator: 当前指标
            historical_indicators: 历史指标列表

        Returns:
            红线检测结果
        """
        config = self.weights["redline"]
        max_penalty = config["max_penalty"]
        triggered = []
        total_penalty = 0.0

        # 1. 毛利率连续下滑
        if config["gross_margin_decline"]["enabled"]:
            if self._check_gross_margin_decline(
                historical_indicators,
                config["gross_margin_decline"]["conditions"],
            ):
                triggered.append("gross_margin_decline")
                total_penalty += config["gross_margin_decline"]["penalty"]

        # 2. 收入连续下滑
        if config["revenue_decline"]["enabled"]:
            if self._check_revenue_decline(
                historical_indicators,
                config["revenue_decline"]["conditions"],
            ):
                triggered.append("revenue_decline")
                total_penalty += config["revenue_decline"]["penalty"]

        # 3. 估值极端高位
        if config["valuation_extreme"]["enabled"]:
            if self._check_valuation_extreme(
                indicator, config["valuation_extreme"]["conditions"]
            ):
                triggered.append("valuation_extreme")
                total_penalty += config["valuation_extreme"]["penalty"]

        # 限制最大扣分
        total_penalty = max(total_penalty, max_penalty)

        logger.debug(f"红线检测: 触发{len(triggered)}条, 扣分{total_penalty}")
        return {"triggered": triggered, "penalty": total_penalty}

    # ========== 辅助方法 ==========

    def _apply_rules(
        self, value: Optional[float], rules: List[Dict[str, Any]]
    ) -> float:
        """
        应用数值规则

        Args:
            value: 数值
            rules: 规则列表

        Returns:
            得分
        """
        if value is None:
            return 0.0

        for rule in rules:
            min_val = rule.get("min")
            max_val = rule.get("max")

            # 检查是否在范围内
            if min_val is not None and value < min_val:
                continue
            if max_val is not None and value >= max_val:
                continue

            return rule.get("score", 0.0)

        return 0.0

    def _score_by_condition(
        self, condition: str, rules: List[Dict[str, Any]]
    ) -> float:
        """根据条件评分"""
        for rule in rules:
            if rule.get("condition") == condition:
                return rule.get("score", 0.0)
        return 0.0

    def _score_trend(self, trend: str, rules: List[Dict[str, Any]]) -> float:
        """根据趋势评分"""
        if trend is None:
            return 0.0

        for rule in rules:
            if rule.get("condition") == trend:
                return rule.get("score", 0.0)
        return 0.0

    def _score_roe_level(
        self, roe: float, level: str, config: Dict[str, Any]
    ) -> float:
        """ROE水平评分"""
        for rule in config["rules"]:
            if level in rule.get("desc", ""):
                return rule.get("score", 0.0)
        return 0.0

    def _score_revenue_growth(
        self, revenue_growth: float, gdp_growth: float, config: Dict[str, Any]
    ) -> float:
        """营收增速评分"""
        if revenue_growth is None:
            return 0.0

        for rule in config["rules"]:
            condition = rule.get("condition")

            if condition == "> gdp + 3" and revenue_growth > gdp_growth + 3:
                return rule.get("score", 0.0)
            elif condition == "> gdp" and revenue_growth > gdp_growth:
                return rule.get("score", 0.0)
            elif condition == "> 0" and revenue_growth > 0:
                return rule.get("score", 0.0)
            elif condition == "<= 0" and revenue_growth <= 0:
                return rule.get("score", 0.0)

        return 0.0

    def _score_profit_growth(
        self,
        profit_growth: float,
        revenue_growth: float,
        config: Dict[str, Any],
    ) -> float:
        """利润增速评分"""
        if profit_growth is None or revenue_growth is None:
            return 0.0

        sync_threshold = config["sync_threshold"]

        for rule in config["rules"]:
            condition = rule.get("condition")

            if (
                condition == "> revenue_growth"
                and profit_growth > revenue_growth
            ):
                return rule.get("score", 0.0)
            elif (
                condition == "approximately_equal"
                and abs(profit_growth - revenue_growth) <= sync_threshold
            ):
                return rule.get("score", 0.0)
            elif (
                condition == "< revenue_growth"
                and profit_growth < revenue_growth
            ):
                return rule.get("score", 0.0)

        return 0.0

    def _score_pmi(
        self, pmi: float, new_order: float, config: Dict[str, Any]
    ) -> float:
        """PMI & 新订单评分"""
        if pmi is None or new_order is None:
            return 0.0

        for rule in config["rules"]:
            condition = rule.get("condition")

            if condition == "pmi > 50 and new_order > 51":
                if pmi > 50 and new_order > 51:
                    return rule.get("score", 0.0)
            elif condition == "pmi > 50 or new_order > 51":
                if pmi > 50 or new_order > 51:
                    return rule.get("score", 0.0)
            elif condition == "else":
                return rule.get("score", 0.0)

        return 0.0

    def _score_ppi_cpi(
        self,
        ppi: float,
        cpi: float,
        industry_name: str,
        config: Dict[str, Any],
    ) -> float:
        """PPI/CPI 评分 - 根据行业类型"""
        is_cyclical = industry_name in CYCLICAL_INDUSTRIES
        is_consumer = industry_name in CONSUMER_INDUSTRIES

        for rule in config["rules"]:
            condition = rule.get("condition", "")

            # 周期行业看 PPI
            if is_cyclical and "cyclical" in condition:
                if "ppi > 5" in condition and ppi is not None and ppi > 5:
                    return rule.get("score", 0.0)
                elif (
                    "ppi between -2 and 2" in condition
                    and ppi is not None
                    and -2 <= ppi <= 2
                ):
                    return rule.get("score", 0.0)
                elif "ppi < -2" in condition and ppi is not None and ppi < -2:
                    return rule.get("score", 0.0)

            # 消费行业看 CPI
            elif is_consumer and "consumer" in condition:
                if (
                    "cpi between 2 and 3" in condition
                    and cpi is not None
                    and 2 <= cpi <= 3
                ):
                    return rule.get("score", 0.0)
                elif "cpi > 3" in condition and cpi is not None and cpi > 3:
                    return rule.get("score", 0.0)
                elif "cpi < 1" in condition and cpi is not None and cpi < 1:
                    return rule.get("score", 0.0)

        return 0.0

    def _score_inventory_cycle(
        self, position: str, rules: List[Dict[str, Any]]
    ) -> float:
        """库存周期位置评分"""
        if position is None:
            return 0.0

        for rule in rules:
            if rule.get("position") == position:
                return rule.get("score", 0.0)

        return 0.0

    def _check_gross_margin_decline(
        self, indicators: List[CalculatedIndicator], conditions: Dict[str, Any]
    ) -> bool:
        """检查毛利率连续下滑"""
        consecutive_quarters = conditions["consecutive_quarters"]
        total_decline_pct = conditions["total_decline_pct"]

        if len(indicators) < consecutive_quarters:
            return False

        # 取最近N个季度
        recent = indicators[-consecutive_quarters:]
        margins = [ind.gross_margin for ind in recent if ind.gross_margin]

        if len(margins) < consecutive_quarters:
            return False

        # 检查是否连续下滑
        decline = margins[0] - margins[-1]
        return decline > total_decline_pct

    def _check_revenue_decline(
        self, indicators: List[CalculatedIndicator], conditions: Dict[str, Any]
    ) -> bool:
        """检查收入连续下滑"""
        consecutive_quarters = conditions["consecutive_quarters"]
        decline_pct = conditions["decline_pct"]

        if len(indicators) < consecutive_quarters:
            return False

        recent = indicators[-consecutive_quarters:]
        for ind in recent:
            if ind.revenue_growth is None or ind.revenue_growth > -decline_pct:
                return False

        return True

    def _check_valuation_extreme(
        self, indicator: CalculatedIndicator, conditions: Dict[str, Any]
    ) -> bool:
        """检查估值极端高位"""
        percentile = conditions["percentile"]

        pe_extreme = (
            indicator.pe_percentile is not None
            and indicator.pe_percentile > percentile
        )
        pb_extreme = (
            indicator.pb_percentile is not None
            and indicator.pb_percentile > percentile
        )

        return pe_extreme or pb_extreme


# 兼容旧代码
ScoringEngine = IndustryScorer
