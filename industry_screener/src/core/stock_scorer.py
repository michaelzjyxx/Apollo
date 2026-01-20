"""
股票评分器 - 计算股票质量评分

评分体系：
- 财务质量（50分）：ROE稳定性、ROIC水平、现金流质量、负债率
- 竞争优势（50分）：龙头地位、龙头趋势、盈利优势、成长性
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger
from sqlalchemy.orm import Session

from ..data.models import StockCalculated, StockScore
from ..data.repository import StockCalculatedRepository, StockRepository
from ..utils.config_loader import get_config

from .base import BaseScorer

class StockScorer(BaseScorer):
    """股票评分器"""

    def __init__(self, session: Session, config_path: Optional[str] = None):
        """
        初始化评分器

        Args:
            session: 数据库会话
            config_path: 配置文件名（不含扩展名），默认为 'stock_scoring_weights'
        """
        self.session = session
        self.stock_repo = StockRepository(session)
        self.calc_repo = StockCalculatedRepository(session)

        # 加载配置
        if config_path is None:
            config_name = "stock_scoring_weights"
        else:
            # 如果传入了路径，尝试提取文件名作为配置名，或者直接使用
            # 这里为了简化，假设传入的是配置名
            config_name = config_path.replace(".yaml", "").replace("config/", "")

        config = get_config(config_name)
        
        super().__init__(config)

        logger.info(f"股票评分器初始化完成，配置名: {config_name}")

    def score(self, stock_code: str, calc_date: datetime) -> Optional[StockScore]:
        """
        计算股票质量评分

        Args:
            stock_code: 股票代码
            calc_date: 计算日期

        Returns:
            股票评分对象
        """
        # 获取股票基础信息
        stock = self.stock_repo.get_by_code(stock_code)
        if not stock:
            logger.warning(f"股票 {stock_code} 不存在")
            return None

        # 获取计算指标
        calc_data = self.calc_repo.get_by_stock_and_date(stock_code, calc_date)
        if not calc_data:
            logger.warning(f"股票 {stock_code} 在 {calc_date} 没有计算指标")
            return None

        # 计算财务质量得分
        financial_score, financial_details = self._score_financial_quality(calc_data)

        # 计算竞争优势得分
        competitive_score, competitive_details = self._score_competitive_advantage(
            calc_data
        )

        # 总分
        total_score = financial_score + competitive_score

        # 创建评分对象
        score = StockScore(
            stock_code=stock_code,
            stock_name=stock.stock_name,
            industry_code=stock.industry_code,
            industry_name=stock.industry_name,
            report_date=calc_data.report_date,
            score_date=calc_date,
            # 总分
            financial_score=financial_score,
            competitive_score=competitive_score,
            total_score=total_score,
            # 财务质量明细
            roe_stability_score=financial_details["roe_stability"],
            roic_level_score=financial_details["roic_level"],
            cashflow_quality_score=financial_details["cashflow_quality"],
            leverage_score=financial_details["leverage"],
            # 竞争优势明细
            leader_position_score=competitive_details["leader_position"],
            leader_trend_score=competitive_details["leader_trend"],
            profit_margin_score=competitive_details["profit_margin"],
            growth_score=competitive_details["growth"],
            # 评分详情
            score_details={
                "financial": financial_details,
                "competitive": competitive_details,
            },
        )

        logger.info(
            f"股票 {stock_code} 评分完成: 总分={total_score:.1f}, "
            f"财务质量={financial_score:.1f}, 竞争优势={competitive_score:.1f}"
        )

        return score

    def _score_financial_quality(
        self, calc_data: StockCalculated
    ) -> tuple[float, Dict[str, float]]:
        """
        计算财务质量得分（50分）

        Args:
            calc_data: 计算指标数据

        Returns:
            (总分, 明细字典)
        """
        config = self.config["financial_quality"]

        # ROE稳定性（15分）
        roe_score = self._apply_rules(
            calc_data.roe_3y_avg, config["roe_stability"]["rules"]
        )

        # ROIC水平（15分）
        roic_score = self._apply_rules(
            calc_data.roic_3y_avg, config["roic_level"]["rules"]
        )

        # 现金流质量（12分）
        cashflow_score = self._apply_rules(
            calc_data.ocf_ni_ratio, config["cashflow_quality"]["rules"]
        )

        # 负债率（8分，值越小得分越高）
        # 注意：BaseScorer._apply_rules 不支持 reverse 参数，
        # 但 YAML 配置中的 min/max 已覆盖了数值区间逻辑。
        # 如果需要特殊反向逻辑，应在 YAML 中定义合适的区间。
        leverage_score = self._apply_rules(
            calc_data.debt_ratio, config["leverage"]["rules"]
        )

        total = roe_score + roic_score + cashflow_score + leverage_score

        details = {
            "roe_stability": roe_score,
            "roic_level": roic_score,
            "cashflow_quality": cashflow_score,
            "leverage": leverage_score,
        }

        return total, details

    def _score_competitive_advantage(
        self, calc_data: StockCalculated
    ) -> tuple[float, Dict[str, float]]:
        """
        计算竞争优势得分（50分）

        Args:
            calc_data: 计算指标数据

        Returns:
            (总分, 明细字典)
        """
        config = self.config["competitive_advantage"]

        # 龙头地位（15分）
        leader_score = self._score_leader_position(calc_data, config["leader_position"])

        # 龙头趋势（10分）
        trend_score = self._score_leader_trend(calc_data, config["leader_trend"])

        # 盈利优势（15分）
        margin_score = self._apply_rules(
            calc_data.gross_margin_vs_industry, config["profit_margin"]["rules"]
        )

        # 成长性（10分）
        growth_score = self._apply_rules(
            calc_data.revenue_cagr_3y, config["growth"]["rules"]
        )

        total = leader_score + trend_score + margin_score + growth_score

        details = {
            "leader_position": leader_score,
            "leader_trend": trend_score,
            "profit_margin": margin_score,
            "growth": growth_score,
        }

        return total, details

    def _score_leader_position(
        self, calc_data: StockCalculated, config: Dict[str, Any]
    ) -> float:
        """
        计算龙头地位得分（15分）

        Args:
            calc_data: 计算指标数据
            config: 配置

        Returns:
            得分
        """
        rank = calc_data.revenue_rank
        if rank is None:
            return 0.0

        # 获取行业内其他公司的营收数据（需要查询）
        # 这里简化处理，根据排名直接评分
        rules = config["rules"]

        for rule in rules:
            condition = rule.get("condition", "")

            if "rank == 1" in condition:
                if rank == 1:
                    # TODO: 检查营收比例条件
                    # 暂时简化为：第1名给10-15分
                    return float(rule["score"])
            elif "rank == 2" in condition:
                if rank == 2:
                    return float(rule["score"])
            elif "rank in [2, 3]" in condition:
                if rank in [2, 3]:
                    return float(rule["score"])

        return 0.0

    def _score_leader_trend(
        self, calc_data: StockCalculated, config: Dict[str, Any]
    ) -> float:
        """
        计算龙头趋势得分（10分）

        Args:
            calc_data: 计算指标数据
            config: 配置

        Returns:
            得分
        """
        current_rank = calc_data.revenue_rank
        past_rank = calc_data.revenue_rank_3y_ago

        if current_rank is None or past_rank is None:
            return 0.0

        # 排名变化（负数表示上升）
        rank_change = current_rank - past_rank

        rules = config["rules"]
        for rule in rules:
            change_threshold = rule.get("change")

            if change_threshold is None:
                continue

            if change_threshold < 0:
                # 上升
                if rank_change <= change_threshold:
                    return float(rule["score"])
            elif change_threshold > 0:
                # 下降
                if rank_change >= change_threshold:
                    return float(rule["score"])
            else:
                # 不变
                if rank_change == 0:
                    return float(rule["score"])

        return 0.0

    def batch_score(
        self, stock_codes: List[str], calc_date: datetime
    ) -> List[StockScore]:
        """
        批量计算股票评分

        Args:
            stock_codes: 股票代码列表
            calc_date: 计算日期

        Returns:
            评分列表
        """
        scores = []

        for stock_code in stock_codes:
            try:
                score = self.score(stock_code, calc_date)
                if score:
                    scores.append(score)
            except Exception as e:
                logger.error(f"股票 {stock_code} 评分失败: {e}")

        logger.info(f"批量评分完成: {len(scores)}/{len(stock_codes)} 只股票")

        return scores

    def save_scores(self, scores: List[StockScore]) -> int:
        """
        保存评分到数据库

        Args:
            scores: 评分列表

        Returns:
            保存的数量
        """
        count = 0

        for score in scores:
            try:
                self.session.add(score)
                count += 1
            except Exception as e:
                logger.error(f"保存评分失败 {score.stock_code}: {e}")

        self.session.commit()
        logger.info(f"保存评分完成: {count} 条记录")

        return count
