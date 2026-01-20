"""
数据仓库基类和通用仓库实现
使用 Repository 模式封装数据访问逻辑
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from loguru import logger
from sqlalchemy import and_, delete, desc, func, select, update
from sqlalchemy.orm import Session

from .models import (
    BacktestResult,
    Base,
    CalculatedIndicator,
    IndustryScore,
    QualitativeScore,
    RawData,
    Stock,
    StockCalculated,
    StockFinancial,
    StockMarket,
    StockScore,
)

# 泛型类型
T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """数据仓库基类"""

    def __init__(self, session: Session, model: Type[T]):
        """
        初始化仓库

        Args:
            session: 数据库会话
            model: 模型类
        """
        self.session = session
        self.model = model

    def get_by_id(self, id: int) -> Optional[T]:
        """
        根据 ID 获取记录

        Args:
            id: 记录 ID

        Returns:
            模型实例或 None
        """
        stmt = select(self.model).where(self.model.id == id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_all(self, limit: Optional[int] = None) -> List[T]:
        """
        获取所有记录

        Args:
            limit: 限制返回数量

        Returns:
            模型实例列表
        """
        stmt = select(self.model)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, **kwargs) -> T:
        """
        创建新记录

        Args:
            **kwargs: 字段值

        Returns:
            创建的模型实例
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()
        return instance

    def bulk_create(self, records: List[Dict[str, Any]]) -> int:
        """
        批量创建记录

        Args:
            records: 记录字典列表

        Returns:
            创建的记录数量
        """
        instances = [self.model(**record) for record in records]
        self.session.add_all(instances)
        self.session.flush()
        return len(instances)

    def update(self, id: int, **kwargs) -> Optional[T]:
        """
        更新记录

        Args:
            id: 记录 ID
            **kwargs: 更新的字段值

        Returns:
            更新后的模型实例或 None
        """
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .execution_options(synchronize_session="fetch")
        )
        result = self.session.execute(stmt)

        if result.rowcount > 0:
            return self.get_by_id(id)
        return None

    def delete(self, id: int) -> bool:
        """
        删除记录

        Args:
            id: 记录 ID

        Returns:
            是否删除成功
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def count(self) -> int:
        """
        统计记录数量

        Returns:
            记录总数
        """
        stmt = select(func.count()).select_from(self.model)
        return self.session.execute(stmt).scalar_one()


class RawDataRepository(BaseRepository[RawData]):
    """原始数据仓库"""

    def __init__(self, session: Session):
        super().__init__(session, RawData)

    def get_by_industry_and_indicator(
        self,
        industry_code: str,
        indicator_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[RawData]:
        """
        根据行业和指标获取数据

        Args:
            industry_code: 行业代码
            indicator_name: 指标名称
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            原始数据列表
        """
        conditions = [
            RawData.industry_code == industry_code,
            RawData.indicator_name == indicator_name,
        ]

        if start_date:
            conditions.append(RawData.data_date >= start_date)
        if end_date:
            conditions.append(RawData.data_date <= end_date)

        stmt = select(RawData).where(and_(*conditions)).order_by(RawData.data_date)
        return list(self.session.execute(stmt).scalars().all())

    def upsert(self, record: Dict[str, Any]) -> RawData:
        """
        插入或更新记录(如果唯一键冲突则更新)

        Args:
            record: 记录字典

        Returns:
            创建或更新的记录
        """
        # 查找是否存在相同的记录
        existing = (
            self.session.query(RawData)
            .filter(
                RawData.industry_code == record["industry_code"],
                RawData.indicator_name == record["indicator_name"],
                RawData.data_date == record["data_date"],
                RawData.frequency == record["frequency"],
            )
            .first()
        )

        if existing:
            # 更新现有记录
            for key, value in record.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now()
            self.session.flush()
            return existing
        else:
            # 创建新记录
            return self.create(**record)

    def get_latest_data_date(
        self, industry_code: str, indicator_name: str
    ) -> Optional[datetime]:
        """
        获取最新数据日期

        Args:
            industry_code: 行业代码
            indicator_name: 指标名称

        Returns:
            最新数据日期或 None
        """
        stmt = (
            select(func.max(RawData.data_date))
            .where(
                RawData.industry_code == industry_code,
                RawData.indicator_name == indicator_name,
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()


class CalculatedIndicatorRepository(BaseRepository[CalculatedIndicator]):
    """计算指标仓库"""

    def __init__(self, session: Session):
        super().__init__(session, CalculatedIndicator)

    def get_by_industry_and_date(
        self,
        industry_code: str,
        report_date: Optional[datetime] = None,
        calc_date: Optional[datetime] = None,
    ) -> Optional[CalculatedIndicator]:
        """
        根据行业和日期获取计算指标

        Args:
            industry_code: 行业代码
            report_date: 报告期
            calc_date: 计算日期

        Returns:
            计算指标或 None
        """
        conditions = [CalculatedIndicator.industry_code == industry_code]

        if report_date:
            conditions.append(CalculatedIndicator.report_date == report_date)
        if calc_date:
            conditions.append(CalculatedIndicator.calc_date == calc_date)

        stmt = select(CalculatedIndicator).where(and_(*conditions))
        return self.session.execute(stmt).scalar_one_or_none()

    def get_latest(self, industry_code: str) -> Optional[CalculatedIndicator]:
        """
        获取最新的计算指标

        Args:
            industry_code: 行业代码

        Returns:
            最新的计算指标或 None
        """
        stmt = (
            select(CalculatedIndicator)
            .where(CalculatedIndicator.industry_code == industry_code)
            .order_by(desc(CalculatedIndicator.calc_date))
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert(self, record: Dict[str, Any]) -> CalculatedIndicator:
        """插入或更新记录"""
        existing = (
            self.session.query(CalculatedIndicator)
            .filter(
                CalculatedIndicator.industry_code == record["industry_code"],
                CalculatedIndicator.report_date == record["report_date"],
                CalculatedIndicator.calc_date == record["calc_date"],
            )
            .first()
        )

        if existing:
            for key, value in record.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now()
            self.session.flush()
            return existing
        else:
            return self.create(**record)


class IndustryScoreRepository(BaseRepository[IndustryScore]):
    """行业评分仓库"""

    def __init__(self, session: Session):
        super().__init__(session, IndustryScore)

    def get_by_date(
        self, score_date: datetime, order_by_rank: bool = True
    ) -> List[IndustryScore]:
        """
        获取指定日期的所有行业评分

        Args:
            score_date: 评分日期
            order_by_rank: 是否按排名排序

        Returns:
            行业评分列表
        """
        stmt = select(IndustryScore).where(IndustryScore.score_date == score_date)

        if order_by_rank:
            stmt = stmt.order_by(IndustryScore.rank)

        return list(self.session.execute(stmt).scalars().all())

    def get_top_n(
        self, score_date: datetime, n: int, min_score: Optional[float] = None
    ) -> List[IndustryScore]:
        """
        获取评分前N的行业

        Args:
            score_date: 评分日期
            n: 数量
            min_score: 最低分数要求

        Returns:
            前N个行业评分
        """
        conditions = [IndustryScore.score_date == score_date]

        if min_score is not None:
            conditions.append(IndustryScore.total_score >= min_score)

        stmt = (
            select(IndustryScore)
            .where(and_(*conditions))
            .order_by(desc(IndustryScore.total_score))
            .limit(n)
        )

        return list(self.session.execute(stmt).scalars().all())

    def upsert(self, record: Dict[str, Any]) -> IndustryScore:
        """插入或更新记录"""
        existing = (
            self.session.query(IndustryScore)
            .filter(
                IndustryScore.industry_code == record["industry_code"],
                IndustryScore.report_date == record["report_date"],
                IndustryScore.score_date == record["score_date"],
            )
            .first()
        )

        if existing:
            for key, value in record.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now()
            self.session.flush()
            return existing
        else:
            return self.create(**record)


class QualitativeScoreRepository(BaseRepository[QualitativeScore]):
    """定性评分仓库"""

    def __init__(self, session: Session):
        super().__init__(session, QualitativeScore)

    def get_by_industry_code(self, industry_code: str) -> Optional[QualitativeScore]:
        """
        根据行业代码获取定性评分

        Args:
            industry_code: 行业代码

        Returns:
            定性评分或 None
        """
        stmt = select(QualitativeScore).where(
            QualitativeScore.industry_code == industry_code,
            QualitativeScore.is_active == True,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_all_active(self) -> List[QualitativeScore]:
        """
        获取所有启用的定性评分

        Returns:
            定性评分列表
        """
        stmt = select(QualitativeScore).where(QualitativeScore.is_active == True)
        return list(self.session.execute(stmt).scalars().all())


class BacktestResultRepository(BaseRepository[BacktestResult]):
    """回测结果仓库"""

    def __init__(self, session: Session):
        super().__init__(session, BacktestResult)

    def get_by_name(self, backtest_name: str) -> List[BacktestResult]:
        """
        根据回测名称获取结果

        Args:
            backtest_name: 回测名称

        Returns:
            回测结果列表
        """
        stmt = (
            select(BacktestResult)
            .where(BacktestResult.backtest_name == backtest_name)
            .order_by(desc(BacktestResult.created_at))
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_strategy(self, strategy_name: str) -> List[BacktestResult]:
        """
        根据策略名称获取结果

        Args:
            strategy_name: 策略名称

        Returns:
            回测结果列表
        """
        stmt = (
            select(BacktestResult)
            .where(BacktestResult.strategy_name == strategy_name)
            .order_by(desc(BacktestResult.created_at))
        )
        return list(self.session.execute(stmt).scalars().all())


# ========== 股票相关仓库（新增） ==========


class StockRepository(BaseRepository[Stock]):
    """股票基础信息仓库"""

    def __init__(self, session: Session):
        super().__init__(session, Stock)

    def get_by_code(self, stock_code: str) -> Optional[Stock]:
        """
        根据股票代码获取股票信息

        Args:
            stock_code: 股票代码

        Returns:
            股票实例或None
        """
        stmt = select(Stock).where(Stock.stock_code == stock_code)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_industry(
        self, industry_code: str, active_only: bool = True
    ) -> List[Stock]:
        """
        获取行业成分股

        Args:
            industry_code: 行业代码
            active_only: 是否只返回有效股票

        Returns:
            股票列表
        """
        stmt = select(Stock).where(Stock.industry_code == industry_code)

        if active_only:
            stmt = stmt.where(Stock.is_active == True)

        return list(self.session.execute(stmt).scalars().all())

    def get_active_stocks(self, exclude_st: bool = True) -> List[Stock]:
        """
        获取所有有效股票

        Args:
            exclude_st: 是否排除ST股票

        Returns:
            股票列表
        """
        stmt = select(Stock).where(Stock.is_active == True)

        if exclude_st:
            stmt = stmt.where(Stock.is_st == False)

        return list(self.session.execute(stmt).scalars().all())

    def bulk_upsert(self, stocks: List[Dict[str, Any]]) -> int:
        """
        批量插入或更新股票信息

        Args:
            stocks: 股票信息字典列表

        Returns:
            处理的记录数
        """
        count = 0
        for stock_data in stocks:
            stock_code = stock_data.get("stock_code")
            existing = self.get_by_code(stock_code)

            if existing:
                # 更新
                for key, value in stock_data.items():
                    if key != "stock_code":
                        setattr(existing, key, value)
                existing.updated_at = datetime.now()
            else:
                # 插入
                new_stock = Stock(**stock_data)
                self.session.add(new_stock)

            count += 1

        self.session.flush()
        return count


class StockFinancialRepository(BaseRepository[StockFinancial]):
    """股票财务数据仓库"""

    def __init__(self, session: Session):
        super().__init__(session, StockFinancial)

    def get_by_stock_and_date(
        self,
        stock_code: str,
        report_date: datetime,
        indicator_name: Optional[str] = None,
    ) -> List[StockFinancial]:
        """
        获取股票在特定报告期的财务数据

        Args:
            stock_code: 股票代码
            report_date: 报告期
            indicator_name: 指标名称（可选）

        Returns:
            财务数据列表
        """
        stmt = select(StockFinancial).where(
            and_(
                StockFinancial.stock_code == stock_code,
                StockFinancial.report_date == report_date,
            )
        )

        if indicator_name:
            stmt = stmt.where(StockFinancial.indicator_name == indicator_name)

        return list(self.session.execute(stmt).scalars().all())

    def get_latest_by_stock(
        self, stock_code: str, as_of_date: datetime
    ) -> List[StockFinancial]:
        """
        获取股票截至某日期的最新财务数据（考虑公告日期）

        Args:
            stock_code: 股票代码
            as_of_date: 截至日期

        Returns:
            财务数据列表
        """
        # 查询最新的已公告财报
        subquery = (
            select(func.max(StockFinancial.report_date))
            .where(
                and_(
                    StockFinancial.stock_code == stock_code,
                    StockFinancial.announce_date <= as_of_date,
                )
            )
            .scalar_subquery()
        )

        stmt = select(StockFinancial).where(
            and_(
                StockFinancial.stock_code == stock_code,
                StockFinancial.report_date == subquery,
            )
        )

        return list(self.session.execute(stmt).scalars().all())


class StockMarketRepository(BaseRepository[StockMarket]):
    """股票行情数据仓库"""

    def __init__(self, session: Session):
        super().__init__(session, StockMarket)

    def get_by_stock_and_date_range(
        self, stock_code: str, start_date: datetime, end_date: datetime
    ) -> List[StockMarket]:
        """
        获取股票在日期范围内的行情数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            行情数据列表
        """
        stmt = (
            select(StockMarket)
            .where(
                and_(
                    StockMarket.stock_code == stock_code,
                    StockMarket.trade_date >= start_date,
                    StockMarket.trade_date <= end_date,
                )
            )
            .order_by(StockMarket.trade_date)
        )

        return list(self.session.execute(stmt).scalars().all())

    def get_latest_price(
        self, stock_code: str, as_of_date: datetime
    ) -> Optional[StockMarket]:
        """
        获取股票截至某日期的最新价格

        Args:
            stock_code: 股票代码
            as_of_date: 截至日期

        Returns:
            行情数据或None
        """
        stmt = (
            select(StockMarket)
            .where(
                and_(
                    StockMarket.stock_code == stock_code,
                    StockMarket.trade_date <= as_of_date,
                )
            )
            .order_by(desc(StockMarket.trade_date))
            .limit(1)
        )

        return self.session.execute(stmt).scalar_one_or_none()


class StockCalculatedRepository(BaseRepository[StockCalculated]):
    """股票计算指标仓库"""

    def __init__(self, session: Session):
        super().__init__(session, StockCalculated)

    def get_by_stock_and_date(
        self, stock_code: str, calc_date: datetime
    ) -> Optional[StockCalculated]:
        """
        获取股票在特定日期的计算指标

        Args:
            stock_code: 股票代码
            calc_date: 计算日期

        Returns:
            计算指标或None
        """
        stmt = select(StockCalculated).where(
            and_(
                StockCalculated.stock_code == stock_code,
                StockCalculated.calc_date == calc_date,
            )
        )

        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_industry_and_date(
        self, industry_code: str, calc_date: datetime
    ) -> List[StockCalculated]:
        """
        获取行业内所有股票在特定日期的计算指标

        Args:
            industry_code: 行业代码
            calc_date: 计算日期

        Returns:
            计算指标列表
        """
        stmt = select(StockCalculated).where(
            and_(
                StockCalculated.industry_code == industry_code,
                StockCalculated.calc_date == calc_date,
            )
        )

        return list(self.session.execute(stmt).scalars().all())

    def get_latest_by_stock(
        self, stock_code: str
    ) -> Optional[StockCalculated]:
        """
        获取股票的最新计算指标

        Args:
            stock_code: 股票代码

        Returns:
            计算指标或None
        """
        stmt = (
            select(StockCalculated)
            .where(StockCalculated.stock_code == stock_code)
            .order_by(desc(StockCalculated.calc_date))
            .limit(1)
        )

        return self.session.execute(stmt).scalar_one_or_none()


class StockScoreRepository(BaseRepository[StockScore]):
    """股票评分仓库"""

    def __init__(self, session: Session):
        super().__init__(session, StockScore)

    def get_by_stock_and_date(
        self, stock_code: str, score_date: datetime
    ) -> Optional[StockScore]:
        """
        获取股票在特定日期的评分

        Args:
            stock_code: 股票代码
            score_date: 评分日期

        Returns:
            评分或None
        """
        stmt = select(StockScore).where(
            and_(
                StockScore.stock_code == stock_code,
                StockScore.score_date == score_date,
            )
        )

        return self.session.execute(stmt).scalar_one_or_none()

    def get_quality_pool(
        self,
        score_date: datetime,
        min_score: Optional[float] = None,
        passed_only: bool = True,
    ) -> List[StockScore]:
        """
        获取优质公司池

        Args:
            score_date: 评分日期
            min_score: 最低得分
            passed_only: 是否只返回通过筛选的股票

        Returns:
            评分列表
        """
        stmt = select(StockScore).where(StockScore.score_date == score_date)

        if passed_only:
            stmt = stmt.where(StockScore.passed_scoring == True)

        if min_score is not None:
            stmt = stmt.where(StockScore.total_score >= min_score)

        stmt = stmt.order_by(desc(StockScore.total_score))

        return list(self.session.execute(stmt).scalars().all())

    def get_by_industry(
        self, industry_code: str, score_date: datetime
    ) -> List[StockScore]:
        """
        获取行业内所有股票的评分

        Args:
            industry_code: 行业代码
            score_date: 评分日期

        Returns:
            评分列表
        """
        stmt = (
            select(StockScore)
            .where(
                and_(
                    StockScore.industry_code == industry_code,
                    StockScore.score_date == score_date,
                )
            )
            .order_by(desc(StockScore.total_score))
        )

        return list(self.session.execute(stmt).scalars().all())

    def get_top_n(
        self, score_date: datetime, n: int = 100
    ) -> List[StockScore]:
        """
        获取得分最高的N只股票

        Args:
            score_date: 评分日期
            n: 数量

        Returns:
            评分列表
        """
        stmt = (
            select(StockScore)
            .where(
                and_(
                    StockScore.score_date == score_date,
                    StockScore.passed_scoring == True,
                )
            )
            .order_by(desc(StockScore.total_score))
            .limit(n)
        )

        return list(self.session.execute(stmt).scalars().all())
