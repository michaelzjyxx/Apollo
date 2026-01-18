"""
数据服务 - 封装数据获取、计算、评分的业务逻辑
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from ..data import (
    CalculatedIndicator,
    CalculatedIndicatorRepository,
    IFindAPIClient,
    IndustryScore,
    IndustryScoreRepository,
    QualitativeScoreRepository,
    RawData,
    RawDataRepository,
)
from ..utils import (
    SHENWAN_L1_INDUSTRIES,
    IndicatorType,
    get_current_quarter,
    get_quarter_dates,
)
from .calculator import IndicatorCalculator
from .scorer import ScoringEngine


class DataService:
    """数据服务 - 统一的数据处理接口"""

    def __init__(self, session: Session):
        """
        初始化数据服务

        Args:
            session: 数据库会话
        """
        self.session = session

        # 初始化仓库
        self.raw_repo = RawDataRepository(session)
        self.calc_repo = CalculatedIndicatorRepository(session)
        self.score_repo = IndustryScoreRepository(session)
        self.qual_repo = QualitativeScoreRepository(session)

        # 初始化引擎
        self.calculator = IndicatorCalculator()
        self.scorer = ScoringEngine()

        logger.info("数据服务初始化成功")

    def fetch_and_store_raw_data(
        self,
        api_client: IFindAPIClient,
        industry_codes: Optional[List[str]] = None,
        indicators: Optional[List[IndicatorType]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        从 iFinD 获取原始数据并存储到数据库

        Args:
            api_client: iFinD API 客户端
            industry_codes: 行业代码列表,为 None 则使用全部
            indicators: 指标列表,为 None 则使用全部
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            存储的记录数
        """
        if industry_codes is None:
            industry_codes = list(SHENWAN_L1_INDUSTRIES.keys())

        if indicators is None:
            indicators = [
                IndicatorType.ROE,
                IndicatorType.GROSS_MARGIN,
                IndicatorType.REVENUE_GROWTH,
                IndicatorType.PROFIT_GROWTH,
                # ... 其他指标
            ]

        total_records = 0

        for industry_code in industry_codes:
            industry_name = SHENWAN_L1_INDUSTRIES[industry_code]

            for indicator in indicators:
                try:
                    # 从 API 获取数据
                    df = api_client.get_industry_data(
                        industry_code=industry_code,
                        indicator=indicator.value,
                        start_date=start_date,
                        end_date=end_date,
                        frequency="quarterly",
                    )

                    # 存储到数据库
                    for _, row in df.iterrows():
                        record = {
                            "industry_code": industry_code,
                            "industry_name": industry_name,
                            "indicator_name": indicator.value,
                            "indicator_value": row["value"],
                            "report_date": row["date"],
                            "data_date": row["date"],
                            "frequency": "quarterly",
                            "source": "ifind",
                        }

                        self.raw_repo.upsert(record)
                        total_records += 1

                    logger.info(
                        f"获取数据: {industry_name} - {indicator.value}, "
                        f"{len(df)} 条记录"
                    )

                except Exception as e:
                    logger.error(
                        f"获取数据失败: {industry_name} - {indicator.value}, "
                        f"错误: {e}"
                    )

        self.session.commit()
        logger.info(f"数据获取完成,共存储 {total_records} 条记录")
        return total_records

    def calculate_indicators(
        self,
        industry_code: str,
        report_date: datetime,
        calc_date: Optional[datetime] = None,
    ) -> CalculatedIndicator:
        """
        计算单个行业的所有指标

        Args:
            industry_code: 行业代码
            report_date: 报告期
            calc_date: 计算日期,为 None 则使用当前日期

        Returns:
            计算指标记录
        """
        if calc_date is None:
            calc_date = datetime.now()

        industry_name = SHENWAN_L1_INDUSTRIES.get(industry_code, "未知")

        logger.info(f"开始计算指标: {industry_name} ({report_date.date()})")

        # 创建计算指标记录
        calculated = CalculatedIndicator(
            industry_code=industry_code,
            industry_name=industry_name,
            report_date=report_date,
            calc_date=calc_date,
        )

        # TODO: 实际计算逻辑需要从 raw_data 读取数据并调用 calculator

        # 示例: 计算 ROE 水平
        # roe_data = self._get_raw_data(industry_code, IndicatorType.ROE)
        # calculated.roe_level = self.calculator.calculate_roe_level(
        #     roe=roe_data.latest,
        #     historical_data=roe_data.historical
        # )

        # 存储到数据库
        record = {
            "industry_code": calculated.industry_code,
            "industry_name": calculated.industry_name,
            "report_date": calculated.report_date,
            "calc_date": calculated.calc_date,
            # ... 其他字段
        }

        result = self.calc_repo.upsert(record)
        self.session.commit()

        logger.info(f"指标计算完成: {industry_name}")
        return result

    def calculate_scores(
        self,
        report_date: datetime,
        score_date: Optional[datetime] = None,
        industry_codes: Optional[List[str]] = None,
    ) -> List[IndustryScore]:
        """
        计算所有行业的评分

        Args:
            report_date: 报告期
            score_date: 评分日期,为 None 则使用当前日期
            industry_codes: 行业代码列表,为 None 则使用全部

        Returns:
            行业评分列表
        """
        if score_date is None:
            score_date = datetime.now()

        if industry_codes is None:
            industry_codes = list(SHENWAN_L1_INDUSTRIES.keys())

        scores = []

        for industry_code in industry_codes:
            try:
                # 获取计算指标
                indicator = self.calc_repo.get_by_industry_and_date(
                    industry_code=industry_code,
                    report_date=report_date,
                )

                if indicator is None:
                    logger.warning(
                        f"未找到计算指标: {industry_code}, {report_date}"
                    )
                    continue

                # 获取定性评分
                qualitative = self.qual_repo.get_by_industry_code(industry_code)

                if qualitative is None:
                    logger.warning(f"未找到定性评分: {industry_code}")
                    continue

                # 计算各维度评分
                competition = self.scorer.score_competition(indicator)
                profitability = self.scorer.score_profitability(indicator)
                growth = self.scorer.score_growth(indicator)
                cashflow = self.scorer.score_cashflow(indicator)
                valuation = self.scorer.score_valuation(indicator)
                sentiment = self.scorer.score_sentiment(
                    indicator, indicator.industry_name
                )
                cycle = self.scorer.score_cycle(indicator)
                qual_score = self.scorer.score_qualitative(qualitative)

                # 检测红线
                historical = []  # TODO: 获取历史指标
                redline = self.scorer.check_redlines(indicator, historical)

                # 汇总总分
                total_score = (
                    competition["score"]
                    + profitability["score"]
                    + growth["score"]
                    + cashflow["score"]
                    + valuation["score"]
                    + sentiment["score"]
                    + cycle["score"]
                    + qual_score["score"]
                    + redline["penalty"]
                )

                # 创建评分记录
                score_record = {
                    "industry_code": industry_code,
                    "industry_name": indicator.industry_name,
                    "report_date": report_date,
                    "score_date": score_date,
                    "competition_score": competition["score"],
                    "profitability_score": profitability["score"],
                    "growth_score": growth["score"],
                    "cashflow_score": cashflow["score"],
                    "valuation_score": valuation["score"],
                    "sentiment_score": sentiment["score"],
                    "cycle_score": cycle["score"],
                    "qualitative_score": qual_score["score"],
                    "policy_score": qualitative.policy_score,
                    "business_model_score": qualitative.business_model_score,
                    "barrier_score": qualitative.barrier_score,
                    "moat_score": qualitative.moat_score,
                    "redline_penalty": redline["penalty"],
                    "redline_triggered": json.dumps(redline["triggered"]),
                    "total_score": total_score,
                    "score_details": json.dumps({
                        "competition": competition["details"],
                        "profitability": profitability["details"],
                        "growth": growth["details"],
                        "cashflow": cashflow["details"],
                        "valuation": valuation["details"],
                        "sentiment": sentiment["details"],
                        "cycle": cycle["details"],
                        "qualitative": qual_score["details"],
                    }),
                }

                result = self.score_repo.upsert(score_record)
                scores.append(result)

                logger.info(
                    f"评分完成: {indicator.industry_name}, 总分={total_score:.1f}"
                )

            except Exception as e:
                logger.error(f"评分失败: {industry_code}, 错误: {e}")

        # 提交事务
        self.session.commit()

        # 更新排名
        self._update_rankings(score_date)

        logger.info(f"所有行业评分完成,共 {len(scores)} 个行业")
        return scores

    def _update_rankings(self, score_date: datetime):
        """
        更新行业排名

        Args:
            score_date: 评分日期
        """
        scores = self.score_repo.get_by_date(score_date, order_by_rank=False)

        # 按总分降序排序
        sorted_scores = sorted(
            scores, key=lambda x: x.total_score or 0, reverse=True
        )

        # 更新排名
        for rank, score in enumerate(sorted_scores, start=1):
            score.rank = rank

        self.session.commit()
        logger.info(f"排名更新完成: {score_date.date()}")

    def get_top_industries(
        self,
        score_date: datetime,
        n: int = 10,
        min_score: Optional[float] = None,
    ) -> List[IndustryScore]:
        """
        获取评分最高的N个行业

        Args:
            score_date: 评分日期
            n: 数量
            min_score: 最低分数要求

        Returns:
            行业评分列表
        """
        return self.score_repo.get_top_n(score_date, n, min_score)

    def get_industry_score_history(
        self, industry_code: str, limit: int = 20
    ) -> List[IndustryScore]:
        """
        获取行业的历史评分

        Args:
            industry_code: 行业代码
            limit: 返回数量

        Returns:
            历史评分列表
        """
        # TODO: 实现历史评分查询
        return []
