"""
数据库模型定义
使用 SQLAlchemy 2.0+ ORM
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """ORM 基类"""

    pass


class RawData(Base):
    """原始数据表 - 存储从 iFinD 获取的原始数据"""

    __tablename__ = "raw_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    industry_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="行业代码"
    )
    industry_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="行业名称"
    )
    industry_level: Mapped[str] = mapped_column(
        String(10), nullable=False, default="L2", comment="行业分类级别(L1/L2/L3)"
    )
    parent_industry_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="父级行业代码(L2对应L1)"
    )
    indicator_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="指标名称"
    )
    indicator_value: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="指标值"
    )

    # 时间信息
    report_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="报告期"
    )
    data_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="数据日期"
    )
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="数据频率(daily/weekly/monthly/quarterly/yearly)"
    )

    # 元数据
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ifind", comment="数据来源"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 索引
    __table_args__ = (
        Index(
            "idx_industry_indicator_date",
            "industry_code",
            "indicator_name",
            "data_date",
        ),
        Index("idx_report_date", "report_date"),
        Index("idx_data_date", "data_date"),
        UniqueConstraint(
            "industry_code",
            "indicator_name",
            "data_date",
            "frequency",
            name="uq_raw_data",
        ),
    )


class CalculatedIndicator(Base):
    """计算指标表 - 存储经过计算的指标"""

    __tablename__ = "calculated_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    industry_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="行业代码"
    )
    industry_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="行业名称"
    )
    industry_level: Mapped[str] = mapped_column(
        String(10), nullable=False, default="L2", comment="行业分类级别(L1/L2/L3)"
    )
    parent_industry_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="父级行业代码(L2对应L1)"
    )

    # 时间信息
    report_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="报告期"
    )
    calc_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="计算日期"
    )

    # 竞争格局指标 (5个)
    cr5: Mapped[Optional[float]] = mapped_column(Float, comment="CR5集中度")
    leader_share: Mapped[Optional[float]] = mapped_column(Float, comment="龙头市占率")
    leader_share_change: Mapped[Optional[float]] = mapped_column(
        Float, comment="龙头市占率变化(pct/年)"
    )
    price_volatility: Mapped[Optional[float]] = mapped_column(
        Float, comment="价格波动率(%)"
    )
    capacity_utilization: Mapped[Optional[float]] = mapped_column(
        Float, comment="产能利用率(%)"
    )

    # 盈利能力指标 (4个)
    roe: Mapped[Optional[float]] = mapped_column(Float, comment="加权ROE(%)")
    roe_level: Mapped[Optional[str]] = mapped_column(
        String(20), comment="ROE水平(优秀/良好/一般)"
    )
    roe_trend: Mapped[Optional[str]] = mapped_column(
        String(20), comment="ROE趋势(improving/stable/declining)"
    )
    gross_margin: Mapped[Optional[float]] = mapped_column(Float, comment="毛利率(%)")
    gross_margin_level: Mapped[Optional[str]] = mapped_column(
        String(20), comment="毛利率水平"
    )
    gross_margin_trend: Mapped[Optional[str]] = mapped_column(
        String(20), comment="毛利率趋势(rising/stable/falling)"
    )

    # 成长性指标 (3个)
    revenue_growth: Mapped[Optional[float]] = mapped_column(
        Float, comment="营收增速(%)"
    )
    profit_growth: Mapped[Optional[float]] = mapped_column(Float, comment="利润增速(%)")
    profit_elasticity: Mapped[Optional[float]] = mapped_column(
        Float, comment="利润弹性"
    )

    # 现金流指标 (2个)
    ocf_ni_ratio: Mapped[Optional[float]] = mapped_column(
        Float, comment="经营现金流/净利润(%)"
    )
    capex_intensity: Mapped[Optional[float]] = mapped_column(
        Float, comment="资本开支强度(capex/折旧)"
    )

    # 估值指标 (5个)
    pe_ttm: Mapped[Optional[float]] = mapped_column(Float, comment="滚动市盈率")
    pb: Mapped[Optional[float]] = mapped_column(Float, comment="市净率")
    pe_percentile: Mapped[Optional[float]] = mapped_column(
        Float, comment="PE历史分位数(%)"
    )
    pb_percentile: Mapped[Optional[float]] = mapped_column(
        Float, comment="PB历史分位数(%)"
    )
    peg: Mapped[Optional[float]] = mapped_column(Float, comment="PEG")

    # 景气度指标 (6个)
    pmi: Mapped[Optional[float]] = mapped_column(Float, comment="PMI指数")
    new_order: Mapped[Optional[float]] = mapped_column(Float, comment="新订单指数")
    m2: Mapped[Optional[float]] = mapped_column(Float, comment="M2增速(%)")
    social_financing: Mapped[Optional[float]] = mapped_column(
        Float, comment="社融增速(%)"
    )
    ppi: Mapped[Optional[float]] = mapped_column(Float, comment="PPI同比(%)")
    cpi: Mapped[Optional[float]] = mapped_column(Float, comment="CPI同比(%)")

    # 周期位置指标 (3个)
    inventory_yoy: Mapped[Optional[float]] = mapped_column(Float, comment="库存同比(%)")
    inventory_turnover: Mapped[Optional[float]] = mapped_column(
        Float, comment="存货周转天数"
    )
    inventory_cycle_position: Mapped[Optional[str]] = mapped_column(
        String(50), comment="库存周期位置"
    )

    # 资金流向指标 (2个)
    northbound_flow: Mapped[Optional[float]] = mapped_column(
        Float, comment="北向资金流向(百万)"
    )
    main_fund_flow: Mapped[Optional[float]] = mapped_column(
        Float, comment="主力资金流向(百万)"
    )

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 索引
    __table_args__ = (
        Index("idx_calc_industry_date", "industry_code", "calc_date"),
        Index("idx_calc_report_date", "report_date"),
        UniqueConstraint(
            "industry_code", "report_date", "calc_date", name="uq_calculated"
        ),
    )


class IndustryScore(Base):
    """行业评分表 - 存储行业综合评分"""

    __tablename__ = "industry_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    industry_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="行业代码"
    )
    industry_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="行业名称"
    )
    industry_level: Mapped[str] = mapped_column(
        String(10), nullable=False, default="L2", comment="行业分类级别(L1/L2/L3)"
    )
    parent_industry_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="父级行业代码(L2对应L1)"
    )

    # 时间信息
    report_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="报告期"
    )
    score_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="评分日期"
    )

    # 分维度评分 (7个维度,共70分)
    competition_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="竞争格局得分(15分)"
    )
    profitability_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="盈利能力得分(15分)"
    )
    growth_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="成长性得分(10分)"
    )
    cashflow_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="现金流得分(10分)"
    )
    valuation_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="估值得分(10分)"
    )
    sentiment_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="景气度得分(5分)"
    )
    cycle_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="周期位置得分(5分)"
    )

    # 定性评分 (4个因素,共20分)
    qualitative_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="定性评分总分(20分)"
    )
    policy_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="政策环境得分(5分)"
    )
    business_model_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="商业模式得分(5分)"
    )
    barrier_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="进入壁垒得分(5分)"
    )
    moat_score: Mapped[Optional[float]] = mapped_column(Float, comment="护城河得分(5分)")

    # 红线扣分
    redline_penalty: Mapped[Optional[float]] = mapped_column(
        Float, default=0, comment="红线扣分(最多-10分)"
    )
    redline_triggered: Mapped[Optional[str]] = mapped_column(
        JSON, comment="触发的红线(JSON数组)"
    )

    # 宏观调整(可选)
    macro_adjustment: Mapped[Optional[float]] = mapped_column(
        Float, default=0, comment="宏观调整分(±5分)"
    )

    # 总分
    total_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="总分(100分制)"
    )

    # 排名
    rank: Mapped[Optional[int]] = mapped_column(Integer, comment="排名")

    # 评分详情(JSON存储)
    score_details: Mapped[Optional[str]] = mapped_column(
        JSON, comment="评分详情(JSON)"
    )

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 索引
    __table_args__ = (
        Index("idx_score_industry_date", "industry_code", "score_date"),
        Index("idx_score_date", "score_date"),
        Index("idx_total_score", "total_score"),
        Index("idx_rank", "rank"),
        UniqueConstraint(
            "industry_code", "report_date", "score_date", name="uq_score"
        ),
    )


class QualitativeScore(Base):
    """定性评分预设库 - 存储人工审核的定性评分"""

    __tablename__ = "qualitative_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    industry_code: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, comment="行业代码"
    )
    industry_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="行业名称"
    )
    industry_level: Mapped[str] = mapped_column(
        String(10), nullable=False, default="L2", comment="行业分类级别(L1/L2/L3)"
    )
    parent_industry_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="父级行业代码(L2对应L1)"
    )

    # 定性评分
    policy_score: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="政策环境得分(1-5分)"
    )
    policy_reason: Mapped[Optional[str]] = mapped_column(
        Text, comment="政策环境评分理由"
    )

    business_model_score: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="商业模式得分(1-5分)"
    )
    business_model_reason: Mapped[Optional[str]] = mapped_column(
        Text, comment="商业模式评分理由"
    )

    barrier_score: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="进入壁垒得分(1-5分)"
    )
    barrier_reason: Mapped[Optional[str]] = mapped_column(Text, comment="进入壁垒评分理由")

    moat_score: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="护城河得分(1-5分)"
    )
    moat_reason: Mapped[Optional[str]] = mapped_column(Text, comment="护城河评分理由")

    # 审核信息
    last_review: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="最后审核日期"
    )
    reviewer: Mapped[Optional[str]] = mapped_column(String(50), comment="审核人")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 索引
    __table_args__ = (Index("idx_last_review", "last_review"),)


class BacktestResult(Base):
    """回测结果表 - 存储回测结果"""

    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 回测信息
    backtest_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="回测名称"
    )
    strategy_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="策略名称"
    )
    start_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="回测起始日期"
    )
    end_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="回测结束日期"
    )

    # 回测参数(JSON)
    parameters: Mapped[Optional[str]] = mapped_column(JSON, comment="回测参数")

    # 回测结果
    total_return: Mapped[Optional[float]] = mapped_column(Float, comment="总收益率(%)")
    annual_return: Mapped[Optional[float]] = mapped_column(Float, comment="年化收益率(%)")
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float, comment="夏普比率")
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float, comment="最大回撤(%)")
    win_rate: Mapped[Optional[float]] = mapped_column(Float, comment="胜率(%)")

    # 基准对比
    benchmark_code: Mapped[Optional[str]] = mapped_column(
        String(20), comment="基准指数代码"
    )
    benchmark_return: Mapped[Optional[float]] = mapped_column(
        Float, comment="基准收益率(%)"
    )
    excess_return: Mapped[Optional[float]] = mapped_column(Float, comment="超额收益率(%)")

    # 详细结果(JSON)
    holdings: Mapped[Optional[str]] = mapped_column(JSON, comment="持仓记录(JSON)")
    trades: Mapped[Optional[str]] = mapped_column(JSON, comment="交易记录(JSON)")
    daily_returns: Mapped[Optional[str]] = mapped_column(JSON, comment="每日收益(JSON)")
    performance_metrics: Mapped[Optional[str]] = mapped_column(
        JSON, comment="绩效指标(JSON)"
    )

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_backtest_name", "backtest_name"),
        Index("idx_strategy_name", "strategy_name"),
        Index("idx_backtest_date", "start_date", "end_date"),
    )


# ========== 股票相关表（新增） ==========


class Stock(Base):
    """股票基础信息表"""

    __tablename__ = "stocks"

    # 基本信息
    stock_code: Mapped[str] = mapped_column(
        String(20), primary_key=True, comment="股票代码"
    )
    stock_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="股票名称"
    )
    list_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="上市日期"
    )
    delist_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="退市日期"
    )

    # 行业分类（复用行业字段结构）
    industry_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="行业代码"
    )
    industry_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="行业名称"
    )
    industry_level: Mapped[str] = mapped_column(
        String(10), nullable=False, default="L2", comment="行业分类级别(L1/L2/L3)"
    )
    parent_industry_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="父级行业代码(L2对应L1)"
    )

    # 状态
    is_st: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否ST股票"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否有效"
    )

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 索引
    __table_args__ = (
        Index("idx_stock_industry", "industry_code"),
        Index("idx_stock_list_date", "list_date"),
        Index("idx_stock_is_active", "is_active"),
    )


class StockFinancial(Base):
    """股票财务数据表（复用RawData结构）"""

    __tablename__ = "stock_financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    stock_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="股票代码"
    )
    stock_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="股票名称"
    )

    # 指标信息（复用RawData结构）
    indicator_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="指标名称"
    )
    indicator_value: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="指标值"
    )

    # 时间信息
    report_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="报告期"
    )
    announce_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="公告日期"
    )
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="数据频率(quarterly/yearly)"
    )

    # 元数据
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ifind", comment="数据来源"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 索引
    __table_args__ = (
        Index(
            "idx_stock_fin_indicator_date",
            "stock_code",
            "indicator_name",
            "report_date",
        ),
        Index("idx_stock_fin_report_date", "report_date"),
        Index("idx_stock_fin_announce_date", "announce_date"),
        UniqueConstraint(
            "stock_code",
            "indicator_name",
            "report_date",
            "frequency",
            name="uq_stock_financial",
        ),
    )


class StockMarket(Base):
    """股票行情数据表"""

    __tablename__ = "stock_market"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    stock_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="股票代码"
    )
    trade_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="交易日期"
    )

    # 行情数据
    open_price: Mapped[Optional[float]] = mapped_column(Float, comment="开盘价")
    close_price: Mapped[Optional[float]] = mapped_column(Float, comment="收盘价")
    high_price: Mapped[Optional[float]] = mapped_column(Float, comment="最高价")
    low_price: Mapped[Optional[float]] = mapped_column(Float, comment="最低价")
    volume: Mapped[Optional[float]] = mapped_column(Float, comment="成交量")
    amount: Mapped[Optional[float]] = mapped_column(Float, comment="成交额")

    # 市值数据
    total_market_cap: Mapped[Optional[float]] = mapped_column(Float, comment="总市值")
    circulating_market_cap: Mapped[Optional[float]] = mapped_column(
        Float, comment="流通市值"
    )

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_stock_market_date", "stock_code", "trade_date"),
        Index("idx_trade_date", "trade_date"),
        UniqueConstraint("stock_code", "trade_date", name="uq_stock_market"),
    )


class StockCalculated(Base):
    """股票计算指标表"""

    __tablename__ = "stock_calculated"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    stock_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="股票代码"
    )
    stock_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="股票名称"
    )

    # 行业信息
    industry_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="行业代码"
    )
    industry_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="行业名称"
    )

    # 时间信息
    report_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="报告期"
    )
    calc_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="计算日期"
    )

    # 财务质量指标
    roe: Mapped[Optional[float]] = mapped_column(Float, comment="ROE")
    roe_3y_avg: Mapped[Optional[float]] = mapped_column(Float, comment="ROE 3年平均")
    roic: Mapped[Optional[float]] = mapped_column(Float, comment="ROIC")
    roic_3y_avg: Mapped[Optional[float]] = mapped_column(Float, comment="ROIC 3年平均")
    debt_ratio: Mapped[Optional[float]] = mapped_column(Float, comment="资产负债率")
    current_ratio: Mapped[Optional[float]] = mapped_column(Float, comment="流动比率")
    quick_ratio: Mapped[Optional[float]] = mapped_column(Float, comment="速动比率")
    ocf_ni_ratio: Mapped[Optional[float]] = mapped_column(
        Float, comment="经营现金流/净利润"
    )

    # 竞争优势指标
    revenue: Mapped[Optional[float]] = mapped_column(Float, comment="营业收入")
    revenue_rank: Mapped[Optional[int]] = mapped_column(Integer, comment="营收排名")
    revenue_rank_3y_ago: Mapped[Optional[int]] = mapped_column(
        Integer, comment="3年前营收排名"
    )
    gross_margin: Mapped[Optional[float]] = mapped_column(Float, comment="毛利率")
    gross_margin_vs_industry: Mapped[Optional[float]] = mapped_column(
        Float, comment="毛利率相对行业优势(%)"
    )
    revenue_cagr_3y: Mapped[Optional[float]] = mapped_column(
        Float, comment="营收3年CAGR"
    )

    # 治理指标
    pledge_ratio: Mapped[Optional[float]] = mapped_column(Float, comment="股东质押比例")
    related_transaction_ratio: Mapped[Optional[float]] = mapped_column(
        Float, comment="关联交易占比"
    )
    goodwill_ratio: Mapped[Optional[float]] = mapped_column(
        Float, comment="商誉/净资产"
    )

    # 其他指标
    net_profit: Mapped[Optional[float]] = mapped_column(Float, comment="净利润")
    net_profit_growth: Mapped[Optional[float]] = mapped_column(
        Float, comment="净利润增长率"
    )

    # 连续排名下降判断所需字段
    revenue_rank_1y_ago: Mapped[Optional[int]] = mapped_column(
        Integer, comment="1年前营收排名"
    )
    revenue_rank_2y_ago: Mapped[Optional[int]] = mapped_column(
        Integer, comment="2年前营收排名"
    )

    # 估值陷阱判断所需字段
    roe_slope: Mapped[Optional[float]] = mapped_column(
        Float, comment="ROE斜率(近3年)"
    )
    roe_min_3y: Mapped[Optional[float]] = mapped_column(
        Float, comment="近3年ROE最低值"
    )
    pe_ttm: Mapped[Optional[float]] = mapped_column(Float, comment="滚动市盈率")

    # 连续业绩下滑判断所需字段
    net_profit_growth_1y_ago: Mapped[Optional[float]] = mapped_column(
        Float, comment="1年前净利润增长率"
    )

    # 竞争优势判断所需字段
    revenue_vs_leader_ratio: Mapped[Optional[float]] = mapped_column(
        Float, comment="营收占行业龙头比例"
    )
    industry_gross_margin_median: Mapped[Optional[float]] = mapped_column(
        Float, comment="行业毛利率中位数"
    )

    # 经营性现金流
    operating_cashflow: Mapped[Optional[float]] = mapped_column(
        Float, comment="经营性现金流(TTM)"
    )

    # 龙头评分所需字段
    revenue_vs_second_ratio: Mapped[Optional[float]] = mapped_column(
        Float, comment="营收占第二名比例"
    )

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 索引
    __table_args__ = (
        Index("idx_stock_calc_date", "stock_code", "calc_date"),
        Index("idx_stock_calc_report_date", "report_date"),
        Index("idx_stock_calc_industry", "industry_code", "calc_date"),
        UniqueConstraint(
            "stock_code", "report_date", "calc_date", name="uq_stock_calculated"
        ),
    )


class StockScore(Base):
    """股票评分表（复用IndustryScore结构）"""

    __tablename__ = "stock_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    stock_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="股票代码"
    )
    stock_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="股票名称"
    )

    # 行业信息
    industry_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="行业代码"
    )
    industry_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="行业名称"
    )

    # 时间信息
    report_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="报告期"
    )
    score_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="评分日期"
    )

    # 评分（50+50结构）
    financial_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="财务质量得分(50分)"
    )
    competitive_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="竞争优势得分(50分)"
    )
    total_score: Mapped[Optional[float]] = mapped_column(Float, comment="总分(100分)")

    # 财务质量明细
    roe_stability_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="ROE稳定性得分(15分)"
    )
    roic_level_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="ROIC水平得分(15分)"
    )
    cashflow_quality_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="现金流质量得分(12分)"
    )
    leverage_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="负债率得分(8分)"
    )

    # 竞争优势明细
    leader_position_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="龙头地位得分(15分)"
    )
    leader_trend_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="龙头趋势得分(10分)"
    )
    profit_margin_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="盈利优势得分(15分)"
    )
    growth_score: Mapped[Optional[float]] = mapped_column(
        Float, comment="成长性得分(10分)"
    )

    # 排名
    rank: Mapped[Optional[int]] = mapped_column(Integer, comment="排名")

    # 评分详情(JSON)
    score_details: Mapped[Optional[str]] = mapped_column(JSON, comment="评分详情")

    # 筛选状态
    passed_basic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否通过基础资格筛选"
    )
    passed_exclusion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否通过排除项过滤"
    )
    passed_scoring: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否通过评分筛选"
    )
    exclusion_reasons: Mapped[Optional[str]] = mapped_column(
        JSON, comment="排除原因(JSON数组)"
    )

    # 入池理由
    pool_reason: Mapped[Optional[str]] = mapped_column(Text, comment="入池理由")

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 索引
    __table_args__ = (
        Index("idx_stock_score_date", "stock_code", "score_date"),
        Index("idx_stock_score_industry", "industry_code", "score_date"),
        Index("idx_stock_total_score", "total_score"),
        Index("idx_stock_rank", "rank"),
        Index("idx_stock_passed", "passed_scoring"),
        UniqueConstraint(
            "stock_code", "report_date", "score_date", name="uq_stock_score"
        ),
    )
