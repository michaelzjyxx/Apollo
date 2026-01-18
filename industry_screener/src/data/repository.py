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
