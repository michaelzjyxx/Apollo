# 数据库设计文档

## 文档信息

**文档类型**：数据库设计
**版本**：v1.1
**创建日期**：2026-01-19
**更新日期**：2026-01-19
**变更说明**：改用MySQL，复用行业筛选模块的数据库

---

## 1. 数据库概述

### 1.1 数据库选型

**选择**：MySQL 8.0+

**理由**：
- 与行业筛选模块统一，共享数据库
- 支持更大数据量和并发
- 更强大的查询优化器
- 支持复杂事务
- 生产环境成熟稳定

### 1.2 ORM框架

**选择**：SQLAlchemy 2.0+

**理由**：
- 与行业筛选模块统一
- Python最成熟的ORM框架
- 支持声明式模型定义
- 强大的查询API
- 良好的类型提示支持

### 1.3 数据库架构

**数据库名称**：`industry_screener`（复用行业筛选模块的数据库）

**表分类**：
- **行业相关表**（已存在，复用）：
  - `raw_data`：原始数据
  - `calculated_indicator`：计算指标
  - `industry_score`：行业评分
  - `qualitative_score`：定性评分
  - `backtest_result`：回测结果

- **股票相关表**（新增）：
  - `stock`：股票基本信息
  - `stock_financial`：股票财务数据
  - `stock_market`：股票行情数据
  - `quality_score`：质量评分
  - `quality_pool`：优质公司池
  - `industry_metrics`：行业指标（聚合）

---

## 2. 新增表结构设计

### 2.1 Stock（股票基本信息表）

**用途**：存储股票基本信息

**SQLAlchemy模型**：
```python
class Stock(Base):
    """股票基本信息表"""

    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, comment="股票代码")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="股票名称")

    # 行业分类
    industry_l1_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="申万一级行业代码")
    industry_l1_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="申万一级行业名称")
    industry_l2_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="申万二级行业代码")
    industry_l2_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="申万二级行业名称")

    # 基本信息
    listing_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="上市日期")
    is_st: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否ST股票")
    is_delisted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否退市")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index('idx_stock_code', 'code'),
        Index('idx_stock_industry_l2', 'industry_l2_code'),
        Index('idx_stock_st_delisted', 'is_st', 'is_delisted'),
    )
```

**字段说明**：

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| code | VARCHAR(10) | UNIQUE, NOT NULL | 股票代码（如600519） |
| name | VARCHAR(50) | NOT NULL | 股票名称 |
| industry_l1_code | VARCHAR(20) | NOT NULL | 申万一级行业代码 |
| industry_l1_name | VARCHAR(50) | NOT NULL | 申万一级行业名称 |
| industry_l2_code | VARCHAR(20) | NOT NULL | 申万二级行业代码 |
| industry_l2_name | VARCHAR(50) | NOT NULL | 申万二级行业名称 |
| listing_date | DATETIME | NULL | 上市日期 |
| is_st | TINYINT(1) | DEFAULT 0 | 是否ST股票 |
| is_delisted | TINYINT(1) | DEFAULT 0 | 是否退市 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |
| updated_at | DATETIME | DEFAULT NOW ON UPDATE NOW | 更新时间 |

---

### 2.2 StockFinancial（股票财务数据表）

**用途**：存储股票财务数据

**SQLAlchemy模型**：
```python
class StockFinancial(Base):
    """股票财务数据表"""

    __tablename__ = "stock_financial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="股票代码")
    report_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="报告期")
    report_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="报告类型(Q1/Q2/Q3/Q4)")

    # 盈利能力指标
    roe: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="ROE(%)")
    roic: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="ROIC(%)")
    revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="营业收入(元)")
    net_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="净利润(元)")
    gross_margin: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="毛利率(%)")

    # 现金流指标
    ocf: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="经营现金流(元)")

    # 资产负债指标
    total_assets: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="总资产(元)")
    total_liabilities: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="总负债(元)")
    equity: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="股东权益(元)")
    current_assets: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="流动资产(元)")
    current_liabilities: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="流动负债(元)")
    quick_assets: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="速动资产(元)")

    # ROIC计算相关
    interest_expense: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="利息费用(元)")
    tax_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="税率(%)")

    # 风险指标
    goodwill: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="商誉(元)")
    pledge_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="大股东质押比例(%)")
    related_transaction_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="关联交易占比(%)")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_stock_financial_code', 'stock_code'),
        Index('idx_stock_financial_date', 'report_date'),
        UniqueConstraint('stock_code', 'report_date', name='uq_stock_financial'),
    )
```

**计算字段**（在应用层计算）：
- 负债率 = total_liabilities / total_assets
- 流动比率 = current_assets / current_liabilities
- 速动比率 = quick_assets / current_liabilities
- 商誉/净资产 = goodwill / equity
- OCF/净利润 = ocf / net_profit

---

### 2.3 其他表结构

由于篇幅限制，其他表（StockMarket、QualityScore、QualityPool、IndustryMetrics）的结构请参考完整文档。

---

## 3. 与行业筛选模块的集成

### 3.1 复用的表

**直接复用**（不需要修改）：
- `raw_data`：原始数据
- `calculated_indicator`：计算指标
- `industry_score`：行业评分
- `qualitative_score`：定性评分
- `backtest_result`：回测结果

### 3.2 数据关联

**行业到股票**：
```python
# 通过 industry_l2_code 关联
# Stock.industry_l2_code -> IndustryScore.industry_code
```

**优质行业列表获取**：
```python
# 从 industry_score 表获取评分≥70的行业
# 作为 Stock 筛选的输入
```

---

## 4. 数据库配置

### 4.1 连接配置

```yaml
# config/data_sources.yaml
database:
  type: mysql
  host: localhost
  port: 3306
  database: industry_screener
  username: ${DB_USER}
  password: ${DB_PASSWORD}
  charset: utf8mb4
  pool_size: 10
  max_overflow: 20
  pool_recycle: 3600
```

---

**相关文档**：
- [概述](./01_overview.md)
- [质量筛选模块](./03_quality_screening.md)
