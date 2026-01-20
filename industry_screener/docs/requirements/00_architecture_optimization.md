# 架构优化方案 - 行业筛选与股票筛选统一

## 文档信息

**文档类型**：架构设计文档
**版本**：v1.0
**创建日期**：2026-01-19
**状态**：待评审

---

## 1. 优化目标

### 1.1 核心问题

当前系统存在两个筛选模块：
1. **行业筛选**：已实现，筛选优质行业
2. **股票筛选**（质量筛选）：待实现，从优质行业中筛选优质股票

两个模块存在大量可复用的代码和逻辑，需要统一架构。

### 1.2 优化原则

1. **代码复用**：共享数据模型、计算逻辑、评分框架
2. **配置驱动**：所有参数可配置，便于调整和优化
3. **模块解耦**：清晰的模块边界，便于维护和扩展
4. **统一接口**：一致的API设计，降低学习成本

---

## 2. 架构对比分析

### 2.1 行业筛选 vs 股票筛选

| 维度 | 行业筛选 | 股票筛选 | 可复用性 |
|------|---------|---------|---------|
| **数据源** | iFinD行业数据 | iFinD股票数据 | ✅ 共享IFindClient |
| **数据模型** | RawData, CalculatedIndicator | 需要Stock相关表 | ✅ 扩展现有模型 |
| **计算引擎** | IndicatorCalculator | 需要股票指标计算 | ✅ 扩展Calculator |
| **评分框架** | Scorer (7维度) | QualityScorer (2维度) | ✅ 统一评分框架 |
| **筛选逻辑** | 红线+评分 | 三关卡(资格+排除+评分) | ⚠️ 需要抽象 |
| **配置文件** | scoring_weights.yaml | quality_*.yaml | ✅ 统一配置结构 |
| **CLI命令** | 已实现 | 待实现 | ✅ 扩展现有CLI |
| **回测引擎** | Backtester | 需要股票回测 | ✅ 共享回测框架 |

### 2.2 可复用模块识别

#### ✅ 完全复用
- `IFindClient`: iFinD API客户端
- `Database`: 数据库连接和会话管理
- `ConfigLoader`: 配置加载器
- `Logger`: 日志系统
- `DateUtils`: 日期工具
- `CLI框架`: Click命令结构

#### ✅ 扩展复用
- `models.py`: 扩展添加Stock相关表
- `IndicatorCalculator`: 扩展添加股票指标计算
- `Scorer`: 抽象为通用评分框架
- `Backtester`: 支持行业和股票两种回测

#### ⚠️ 需要重构
- 筛选逻辑：抽象为通用Filter框架
- 评分逻辑：统一评分接口

---

## 3. 统一架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    CLI 命令行界面                         │
│  industry | stock | pool | backtest | data | config     │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                    核心业务层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 通用筛选器   │  │ 通用评分器   │  │ 回测引擎     │  │
│  │ BaseFilter   │  │ BaseScorer   │  │ Backtester   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         ↓                  ↓                             │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │ 行业筛选器   │  │ 股票筛选器   │                    │
│  │IndustryFilter│  │ StockFilter  │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                    数据访问层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 通用仓库     │  │ 行业仓库     │  │ 股票仓库     │  │
│  │ BaseRepo     │  │ IndustryRepo │  │ StockRepo    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                    数据源层                               │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │ iFinD Client │  │ SQLite DB    │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 统一数据模型

#### 3.2.1 扩展现有模型

```python
# 在 models.py 中添加股票相关表

class Stock(Base):
    """股票基础信息表"""
    __tablename__ = "stocks"

    stock_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)
    list_date: Mapped[datetime] = mapped_column(DateTime)
    delist_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # 行业分类（复用现有字段结构）
    industry_code: Mapped[str] = mapped_column(String(20), nullable=False)
    industry_name: Mapped[str] = mapped_column(String(50), nullable=False)
    industry_level: Mapped[str] = mapped_column(String(10), default="L2")
    parent_industry_code: Mapped[Optional[str]] = mapped_column(String(20))

    # 状态
    is_st: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockFinancial(Base):
    """股票财务数据表（复用RawData结构）"""
    __tablename__ = "stock_financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)

    # 复用RawData的字段结构
    indicator_name: Mapped[str] = mapped_column(String(50), nullable=False)
    indicator_value: Mapped[Optional[float]] = mapped_column(Float)

    report_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    announce_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)

    # 索引
    __table_args__ = (
        Index("idx_stock_indicator_date", "stock_code", "indicator_name", "report_date"),
        UniqueConstraint("stock_code", "indicator_name", "report_date", "frequency"),
    )


class StockCalculated(Base):
    """股票计算指标表（复用CalculatedIndicator结构）"""
    __tablename__ = "stock_calculated"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # 行业信息
    industry_code: Mapped[str] = mapped_column(String(20), nullable=False)
    industry_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # 时间信息
    report_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    calc_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # 财务质量指标
    roe_3y_avg: Mapped[Optional[float]] = mapped_column(Float)
    roic_3y_avg: Mapped[Optional[float]] = mapped_column(Float)
    debt_ratio: Mapped[Optional[float]] = mapped_column(Float)
    current_ratio: Mapped[Optional[float]] = mapped_column(Float)
    quick_ratio: Mapped[Optional[float]] = mapped_column(Float)
    ocf_ni_ratio: Mapped[Optional[float]] = mapped_column(Float)

    # 竞争优势指标
    revenue: Mapped[Optional[float]] = mapped_column(Float)
    revenue_rank: Mapped[Optional[int]] = mapped_column(Integer)
    revenue_rank_3y_ago: Mapped[Optional[int]] = mapped_column(Integer)
    gross_margin: Mapped[Optional[float]] = mapped_column(Float)
    revenue_cagr_3y: Mapped[Optional[float]] = mapped_column(Float)

    # 治理指标
    pledge_ratio: Mapped[Optional[float]] = mapped_column(Float)
    related_transaction_ratio: Mapped[Optional[float]] = mapped_column(Float)
    goodwill_ratio: Mapped[Optional[float]] = mapped_column(Float)

    # 索引
    __table_args__ = (
        Index("idx_stock_calc_date", "stock_code", "calc_date"),
        UniqueConstraint("stock_code", "report_date", "calc_date"),
    )


class StockScore(Base):
    """股票评分表（复用IndustryScore结构）"""
    __tablename__ = "stock_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # 行业信息
    industry_code: Mapped[str] = mapped_column(String(20), nullable=False)
    industry_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # 时间信息
    report_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    score_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # 评分（50+50结构）
    financial_score: Mapped[Optional[float]] = mapped_column(Float, comment="财务质量(50分)")
    competitive_score: Mapped[Optional[float]] = mapped_column(Float, comment="竞争优势(50分)")
    total_score: Mapped[Optional[float]] = mapped_column(Float, comment="总分(100分)")

    # 排名
    rank: Mapped[Optional[int]] = mapped_column(Integer)

    # 评分详情
    score_details: Mapped[Optional[str]] = mapped_column(JSON)

    # 筛选状态
    passed_basic: Mapped[bool] = mapped_column(Boolean, default=False)
    passed_exclusion: Mapped[bool] = mapped_column(Boolean, default=False)
    passed_scoring: Mapped[bool] = mapped_column(Boolean, default=False)
    exclusion_reasons: Mapped[Optional[str]] = mapped_column(JSON)

    # 索引
    __table_args__ = (
        Index("idx_stock_score_date", "stock_code", "score_date"),
        Index("idx_total_score", "total_score"),
        UniqueConstraint("stock_code", "report_date", "score_date"),
    )
```

### 3.3 统一计算引擎

```python
# 扩展 calculator.py

class IndicatorCalculator:
    """统一指标计算器（支持行业和股票）"""

    # ========== 行业指标（已实现） ==========
    def calculate_cr5(self, market_shares: List[float]) -> Optional[float]:
        """CR5集中度"""
        pass

    # ========== 股票指标（新增） ==========

    def calculate_roe(self, net_profit: float, equity: float) -> Optional[float]:
        """计算ROE"""
        if equity == 0:
            return None
        return net_profit / equity

    def calculate_roe_3y_avg(self, roe_values: List[float]) -> Optional[float]:
        """计算3年平均ROE"""
        if not roe_values or len(roe_values) < 3:
            return None
        return sum(roe_values[-3:]) / 3

    def calculate_roic(
        self,
        net_profit: float,
        interest_expense: float,
        tax_rate: float,
        equity: float,
        interest_bearing_debt: float
    ) -> Optional[float]:
        """计算ROIC"""
        nopat = net_profit + interest_expense * (1 - tax_rate)
        invested_capital = equity + interest_bearing_debt

        if invested_capital == 0:
            return None
        return nopat / invested_capital

    def calculate_revenue_rank(
        self,
        stock_code: str,
        industry_revenues: Dict[str, float]
    ) -> Optional[int]:
        """计算营收排名"""
        sorted_stocks = sorted(
            industry_revenues.items(),
            key=lambda x: x[1],
            reverse=True
        )

        for rank, (code, _) in enumerate(sorted_stocks, 1):
            if code == stock_code:
                return rank
        return None

    def calculate_cagr(
        self,
        start_value: float,
        end_value: float,
        years: int
    ) -> Optional[float]:
        """计算复合年均增长率"""
        if start_value <= 0 or years <= 0:
            return None
        return (end_value / start_value) ** (1 / years) - 1
```

### 3.4 统一评分框架

```python
# 重构 scorer.py

class BaseScorer(ABC):
    """通用评分器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def score(self, entity: Any, date: str) -> ScoreResult:
        """评分接口"""
        pass

    def _calculate_dimension_score(
        self,
        value: float,
        rules: List[Dict]
    ) -> float:
        """根据规则计算维度得分（通用逻辑）"""
        for rule in rules:
            if self._match_rule(value, rule):
                return rule['score']
        return 0


class IndustryScorer(BaseScorer):
    """行业评分器（已实现，继承BaseScorer）"""

    def score(self, industry_code: str, date: str) -> IndustryScore:
        """行业评分"""
        # 7维度评分逻辑
        pass


class StockScorer(BaseScorer):
    """股票评分器（新增，继承BaseScorer）"""

    def score(self, stock_code: str, date: str) -> StockScore:
        """股票评分"""
        # 财务质量(50分) + 竞争优势(50分)
        financial_score = self._score_financial_quality(stock_code, date)
        competitive_score = self._score_competitive_advantage(stock_code, date)

        return StockScore(
            stock_code=stock_code,
            financial_score=financial_score,
            competitive_score=competitive_score,
            total_score=financial_score + competitive_score
        )

    def _score_financial_quality(self, stock_code: str, date: str) -> float:
        """财务质量评分(50分)"""
        roe_score = self._score_roe_stability(stock_code, date)  # 15分
        roic_score = self._score_roic_level(stock_code, date)    # 15分
        cf_score = self._score_cashflow_quality(stock_code, date) # 12分
        lev_score = self._score_leverage(stock_code, date)       # 8分

        return roe_score + roic_score + cf_score + lev_score

    def _score_competitive_advantage(self, stock_code: str, date: str) -> float:
        """竞争优势评分(50分)"""
        leader_score = self._score_leader_position(stock_code, date)  # 15分
        trend_score = self._score_leader_trend(stock_code, date)      # 10分
        margin_score = self._score_profit_margin(stock_code, date)    # 15分
        growth_score = self._score_growth(stock_code, date)           # 10分

        return leader_score + trend_score + margin_score + growth_score
```

### 3.5 统一筛选框架

```python
# 新增 filter.py

class BaseFilter(ABC):
    """通用筛选器基类"""

    def __init__(self, config: Dict[str, Any], repository: Any):
        self.config = config
        self.repository = repository

    @abstractmethod
    def filter(self, candidates: List[Any], date: str) -> FilterResult:
        """筛选接口"""
        pass

    def _apply_rules(
        self,
        candidates: List[Any],
        rules: List[Callable]
    ) -> List[Any]:
        """应用筛选规则（通用逻辑）"""
        result = candidates
        for rule in rules:
            result = [c for c in result if rule(c)]
        return result


class IndustryFilter(BaseFilter):
    """行业筛选器（已实现，重构为继承BaseFilter）"""

    def filter(self, industries: List[str], date: str) -> IndustryFilterResult:
        """行业筛选：红线+评分"""
        # 应用红线规则
        passed_redline = self._apply_redline_rules(industries, date)

        # 评分
        scored = self._score_industries(passed_redline, date)

        # 筛选入池
        pool = [i for i in scored if i.total_score >= self.config['min_score']]

        return IndustryFilterResult(pool=pool)


class StockFilter(BaseFilter):
    """股票筛选器（新增）"""

    def filter(self, industries: List[str], date: str) -> StockFilterResult:
        """股票筛选：三关卡"""
        # 获取行业成分股
        stocks = self._get_industry_stocks(industries, date)

        # 第一关：基础资格筛选
        passed_basic = self._basic_qualification(stocks, date)

        # 第二关：排除项过滤
        passed_exclusion = self._exclusion_filter(passed_basic, date)

        # 第三关：质量评分
        scored = self._quality_scoring(passed_exclusion, date)

        # 筛选入池
        pool = [s for s in scored if s.total_score >= self.config['min_score']]

        # 行业分散度控制
        final_pool = self._apply_diversification(pool)

        return StockFilterResult(pool=final_pool)
```

### 3.6 统一配置结构

```yaml
# config/unified_config.yaml

# ========== 通用配置 ==========
common:
  data_source: "ifind"
  database_path: "data/database/stocks.db"
  log_level: "INFO"

# ========== 行业筛选配置 ==========
industry_filter:
  min_score: 60
  redline_rules:
    # 红线规则
  scoring_weights:
    # 7维度权重（复用现有scoring_weights.yaml）

# ========== 股票筛选配置 ==========
stock_filter:
  # 基础资格
  basic_qualification:
    roe_3y_avg_min: 0.12
    roic_3y_avg_min: 0.10
    # ...

  # 排除项
  exclusion:
    st_stocks: true
    # ...

  # 评分权重
  scoring_weights:
    financial_quality:
      roe_stability: {weight: 15, thresholds: [...]}
      roic_level: {weight: 15, thresholds: [...]}
      # ...
    competitive_advantage:
      leader_position: {weight: 15, rules: [...]}
      # ...

  # 行业分散度
  diversification:
    max_industry_ratio: 0.35

# ========== 回测配置 ==========
backtest:
  # 通用回测参数（支持行业和股票）
  initial_capital: 1000000
  rebalance_freq: "Q"
  transaction_cost: 0.001
```

---

## 4. 实施计划

### 4.1 Phase 1: 数据模型扩展（Week 1）

- [ ] 在models.py中添加Stock相关表
- [ ] 创建数据库迁移脚本
- [ ] 更新Repository添加股票数据访问

### 4.2 Phase 2: 计算引擎扩展（Week 2）

- [ ] 在IndicatorCalculator中添加股票指标计算
- [ ] 单元测试

### 4.3 Phase 3: 评分框架重构（Week 3）

- [ ] 抽象BaseScorer
- [ ] 重构IndustryScorer继承BaseScorer
- [ ] 实现StockScorer
- [ ] 单元测试

### 4.4 Phase 4: 筛选框架重构（Week 4）

- [ ] 抽象BaseFilter
- [ ] 重构IndustryFilter继承BaseFilter
- [ ] 实现StockFilter
- [ ] 集成测试

### 4.5 Phase 5: CLI和配置（Week 5）

- [ ] 扩展CLI添加stock命令组
- [ ] 统一配置文件结构
- [ ] 端到端测试

---

## 5. 优化收益

### 5.1 代码复用率

- **数据层**：80%复用（共享IFindClient、Database、Repository基类）
- **计算层**：60%复用（扩展Calculator，共享计算逻辑）
- **评分层**：70%复用（共享BaseScorer框架）
- **筛选层**：50%复用（共享BaseFilter框架）
- **CLI层**：90%复用（扩展现有命令结构）

### 5.2 配置化程度

- 所有阈值和权重可配置
- 支持策略参数调优
- 便于A/B测试

### 5.3 可维护性

- 清晰的模块边界
- 统一的接口设计
- 完善的测试覆盖

---

**相关文档**：
- [概述](./01_overview.md)
- [数据库设计](./02_database_design.md)
- [质量筛选模块](./03_quality_screening.md)
