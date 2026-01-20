# 需求文档优化清单

## 文档信息

**文档类型**：优化清单
**版本**：v1.0
**创建日期**：2026-01-19

---

## 1. 数据库设计优化 (02_database_design.md)

### ✅ 保留现有表结构
- `RawData`: 存储原始数据（行业和股票共用）
- `CalculatedIndicator`: 存储计算指标（行业）
- `IndustryScore`: 存储行业评分
- `QualitativeScore`: 定性评分预设
- `BacktestResult`: 回测结果

### ➕ 新增股票相关表

```python
# 1. 股票基础信息表
class Stock(Base):
    __tablename__ = "stocks"
    stock_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    stock_name: Mapped[str] = mapped_column(String(50))
    list_date: Mapped[datetime]
    delist_date: Mapped[Optional[datetime]]

    # 复用行业字段结构
    industry_code: Mapped[str] = mapped_column(String(20))
    industry_name: Mapped[str] = mapped_column(String(50))
    industry_level: Mapped[str] = mapped_column(String(10), default="L2")
    parent_industry_code: Mapped[Optional[str]]

    is_st: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

# 2. 股票财务数据表（复用RawData结构）
class StockFinancial(Base):
    __tablename__ = "stock_financials"
    # 与RawData相同的字段结构，只是entity从industry改为stock

# 3. 股票计算指标表
class StockCalculated(Base):
    __tablename__ = "stock_calculated"
    # 包含ROE、ROIC、营收排名等计算指标

# 4. 股票评分表（复用IndustryScore结构）
class StockScore(Base):
    __tablename__ = "stock_scores"
    # 财务质量(50分) + 竞争优势(50分) = 总分(100分)
    financial_score: Mapped[Optional[float]]
    competitive_score: Mapped[Optional[float]]
    total_score: Mapped[Optional[float]]

    # 筛选状态
    passed_basic: Mapped[bool]
    passed_exclusion: Mapped[bool]
    exclusion_reasons: Mapped[Optional[str]] = mapped_column(JSON)
```

### 🔧 关键修改点

1. **复用字段结构**：行业和股票使用相同的字段命名和类型
2. **统一索引策略**：entity_code + date的索引模式
3. **JSON存储详情**：评分详情、排除原因等使用JSON

---

## 2. 质量筛选模块优化 (03_quality_screening.md)

### 🔧 关键修改点

#### 2.1 复用现有Calculator

```python
# 不要重新实现，扩展现有的IndicatorCalculator
from src.core.calculator import IndicatorCalculator

class IndicatorCalculator:
    # ========== 已有的行业指标 ==========
    def calculate_cr5(self, market_shares): pass
    def calculate_roe(self, ...): pass  # 已有

    # ========== 新增股票指标 ==========
    def calculate_roe_3y_avg(self, roe_values: List[float]) -> float:
        """计算3年平均ROE"""
        return sum(roe_values[-3:]) / 3

    def calculate_roic(self, net_profit, interest, tax_rate, equity, debt):
        """计算ROIC"""
        nopat = net_profit + interest * (1 - tax_rate)
        invested_capital = equity + debt
        return nopat / invested_capital if invested_capital > 0 else None

    def calculate_revenue_rank(self, stock_code, industry_revenues):
        """计算营收排名"""
        sorted_stocks = sorted(industry_revenues.items(), key=lambda x: x[1], reverse=True)
        for rank, (code, _) in enumerate(sorted_stocks, 1):
            if code == stock_code:
                return rank
        return None

    def calculate_cr3(self, revenues: List[float]) -> float:
        """计算行业集中度CR3"""
        top_3 = sorted(revenues, reverse=True)[:3]
        return sum(top_3) / sum(revenues) if sum(revenues) > 0 else 0
```

#### 2.2 复用现有Scorer框架

```python
# 不要重新实现，扩展现有的Scorer
from src.core.scorer import Scorer

# 重构为基类
class BaseScorer(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def score(self, entity, date): pass

    def _calculate_dimension_score(self, value, rules):
        """通用评分逻辑"""
        for rule in rules:
            if self._match_rule(value, rule):
                return rule['score']
        return 0

# 行业评分器（已有，重构为继承BaseScorer）
class IndustryScorer(BaseScorer):
    def score(self, industry_code, date):
        # 7维度评分
        pass

# 股票评分器（新增）
class StockScorer(BaseScorer):
    def score(self, stock_code, date):
        # 2维度评分：财务质量(50) + 竞争优势(50)
        pass
```

#### 2.3 配置文件复用

```yaml
# config/stock_scoring_weights.yaml
# 复用现有scoring_weights.yaml的结构

financial_quality:  # 50分
  roe_stability:
    weight: 15
    rules:  # 复用现有规则结构
      - {min: 0.20, max: null, score: 15, desc: '优秀'}
      - {min: 0.15, max: 0.20, score: 10, desc: '良好'}
      - {min: 0.12, max: 0.15, score: 6, desc: '及格'}

  roic_level:
    weight: 15
    rules:
      - {min: 0.15, max: null, score: 15}
      - {min: 0.12, max: 0.15, score: 10}
      - {min: 0.10, max: 0.12, score: 6}

  cashflow_quality:
    weight: 12
    rules:
      - {min: 1.2, max: null, score: 12}
      - {min: 0.8, max: 1.2, score: 8}
      - {min: 0.5, max: 0.8, score: 4}

  leverage:
    weight: 8
    rules:
      - {min: null, max: 0.30, score: 8}
      - {min: 0.30, max: 0.50, score: 5}
      - {min: 0.50, max: 0.70, score: 2}
    reverse: true  # 值越小得分越高

competitive_advantage:  # 50分
  leader_position:
    weight: 15
    rules:
      - {condition: 'rank==1 and revenue>=second*1.5', score: 15, desc: '绝对龙头'}
      - {condition: 'rank==1 and revenue>=second*1.0', score: 12, desc: '领先龙头'}
      - {condition: 'rank==1', score: 10, desc: '龙头'}
      - {condition: 'rank==2 and revenue>=first*0.5', score: 8, desc: '强势第二'}
      - {condition: 'rank in [2,3]', score: 5, desc: '前列'}

  leader_trend:
    weight: 10
    lookback_years: 3
    rules:
      - {change: 2, score: 10, desc: '快速崛起'}
      - {change: 1, score: 8, desc: '稳步上升'}
      - {change: 0, score: 6, desc: '稳定'}
      - {change: -1, score: 3, desc: '轻微下滑'}
      - {change: -2, score: 0, desc: '竞争力减弱'}

  profit_margin:
    weight: 15
    metric: 'gross_margin'
    rules:
      - {relative_advantage: 0.30, score: 15, desc: '显著优势'}
      - {relative_advantage: 0.20, score: 12, desc: '明显优势'}
      - {relative_advantage: 0.10, score: 9, desc: '一定优势'}
      - {relative_advantage: 0.00, score: 5, desc: '略有优势'}

  growth:
    weight: 10
    metric: 'revenue_cagr'
    lookback_years: 3
    rules:
      - {min: 0.20, score: 10, desc: '高成长'}
      - {min: 0.15, score: 8, desc: '较高成长'}
      - {min: 0.10, score: 6, desc: '中等成长'}
      - {min: 0.05, score: 3, desc: '低成长'}
      - {min: 0.00, score: 1, desc: '停滞'}
```

---

## 3. 数据获取模块优化 (04_data_acquisition.md)

### 🔧 关键修改点

#### 3.1 复用IFindClient

```python
# 不要重新实现，扩展现有的IFindClient
from src.data.ifind_api import IFindClient

class IFindClient:
    # ========== 已有的行业数据获取 ==========
    def get_industry_data(self, ...): pass

    # ========== 新增股票数据获取 ==========
    def get_stock_list(self, market="A股") -> pd.DataFrame:
        """获取股票列表"""
        pass

    def get_stock_financials(
        self,
        stock_codes: List[str],
        indicators: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取股票财务数据"""
        pass

    def get_stock_market_data(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取股票行情数据"""
        pass
```

#### 3.2 复用Repository模式

```python
# 扩展现有的repository.py
from src.data.repository import BaseRepository

class BaseRepository(ABC):
    """通用仓库基类"""
    def __init__(self, session):
        self.session = session

    @abstractmethod
    def save(self, data): pass

    @abstractmethod
    def get(self, **kwargs): pass

# 行业仓库（已有）
class IndustryRepository(BaseRepository):
    pass

# 股票仓库（新增）
class StockRepository(BaseRepository):
    def save_stock_list(self, stocks: pd.DataFrame):
        """保存股票列表"""
        pass

    def save_stock_financials(self, financials: pd.DataFrame):
        """保存股票财务数据"""
        pass

    def get_stock_financials(self, stock_code, start_date, end_date):
        """查询股票财务数据"""
        pass
```

---

## 4. 回测模块优化 (05_backtesting.md)

### 🔧 关键修改点

#### 4.1 复用Backtester

```python
# 扩展现有的backtester.py
from src.core.backtester import Backtester

class Backtester:
    """统一回测引擎（支持行业和股票）"""

    def __init__(self, config):
        self.config = config
        self.entity_type = config.get('entity_type', 'industry')  # industry | stock

    def run(self, start_date, end_date):
        """运行回测"""
        if self.entity_type == 'industry':
            return self._backtest_industry(start_date, end_date)
        else:
            return self._backtest_stock(start_date, end_date)

    def _backtest_industry(self, start_date, end_date):
        """行业回测（已有）"""
        pass

    def _backtest_stock(self, start_date, end_date):
        """股票回测（新增）"""
        # 复用行业回测的框架
        # 1. 生成再平衡日期
        # 2. 历史回放
        # 3. 计算收益
        # 4. 绩效分析
        pass
```

---

## 5. CLI工具优化 (06_cli_tools.md)

### 🔧 关键修改点

#### 5.1 扩展现有CLI结构

```python
# 扩展 src/cli/main.py

@click.group()
def cli():
    """行业与股票筛选系统"""
    pass

# ========== 已有命令组 ==========
@cli.group()
def industry():
    """行业筛选命令"""
    pass

@cli.group()
def data():
    """数据管理命令"""
    pass

@cli.group()
def backtest():
    """回测命令"""
    pass

# ========== 新增命令组 ==========
@cli.group()
def stock():
    """股票筛选命令"""
    pass

@stock.command()
@click.option('--date', help='筛选日期')
@click.option('--industries', help='指定行业')
def screen(date, industries):
    """执行股票质量筛选"""
    pass

@stock.command()
@click.argument('stock_code')
def score(stock_code):
    """计算单只股票评分"""
    pass

@cli.group()
def pool():
    """优质公司池管理"""
    pass

@pool.command()
def list():
    """列出优质公司池"""
    pass
```

---

## 6. 配置管理优化 (07_configuration.md)

### 🔧 关键修改点

#### 6.1 统一配置结构

```yaml
# config/config.yaml（主配置文件）

# ========== 通用配置 ==========
common:
  data_source: "ifind"
  database_path: "data/database/stocks.db"
  log_level: "INFO"
  cache_enabled: true

# ========== 行业筛选配置 ==========
industry_filter:
  enabled: true
  config_file: "config/industry_scoring_weights.yaml"  # 复用现有文件
  min_score: 60

# ========== 股票筛选配置 ==========
stock_filter:
  enabled: true
  config_file: "config/stock_scoring_weights.yaml"  # 新增文件
  min_score: 60

  # 基础资格筛选
  basic_qualification:
    roe_3y_avg_min: 0.12
    roic_3y_avg_min: 0.10
    debt_ratio_max: 0.70
    current_ratio_min: 1.0
    quick_ratio_min: 0.8

  # 行业集中度标准
  industry_concentration:
    high_cr3_threshold: 0.50
    high_cr3_top_n: 3
    medium_cr3_threshold: 0.30
    medium_cr3_top_n: 2
    low_cr3_top_n: 1

  # 排除项
  exclusion:
    st_stocks: true
    revenue_rank_decline_years: 2
    roe_slope_threshold: -0.02
    cyclical_roe_min: 0.08
    pledge_ratio_max: 0.50
    related_transaction_ratio_max: 0.30
    goodwill_ratio_max: 0.30
    profit_decline_threshold: -0.20
    profit_decline_years: 2

  # 周期行业定义（复用现有）
  cyclical_industries:
    - 化工
    - 有色金属
    - 钢铁
    - 煤炭
    - 农林牧渔
    - 机械设备
    - 汽车
    - 建筑材料
    - 房地产

  # 行业分散度
  diversification:
    enabled: true
    max_industry_ratio: 0.35
    min_pool_size: 30

# ========== 回测配置 ==========
backtest:
  entity_type: "stock"  # industry | stock
  initial_capital: 1000000
  rebalance_freq: "Q"
  transaction_cost: 0.001
  benchmark: "000300.SH"
```

---

## 7. 实施优先级

### 高优先级（必须）
1. ✅ 数据模型扩展：添加Stock相关表
2. ✅ Calculator扩展：添加股票指标计算方法
3. ✅ 配置文件：创建stock_scoring_weights.yaml
4. ✅ Repository扩展：添加StockRepository

### 中优先级（重要）
5. ✅ Scorer重构：抽象BaseScorer，实现StockScorer
6. ✅ CLI扩展：添加stock和pool命令组
7. ✅ Backtester扩展：支持股票回测

### 低优先级（优化）
8. ⚠️ Filter抽象：抽象BaseFilter（可选，先实现功能）
9. ⚠️ 配置统一：合并配置文件（可选，先分开）

---

## 8. 代码复用检查清单

### ✅ 必须复用
- [ ] IFindClient：数据获取
- [ ] Database：数据库连接
- [ ] IndicatorCalculator：指标计算
- [ ] ConfigLoader：配置加载
- [ ] Logger：日志系统
- [ ] DateUtils：日期工具

### ✅ 扩展复用
- [ ] models.py：添加Stock表
- [ ] repository.py：添加StockRepository
- [ ] scorer.py：抽象BaseScorer
- [ ] backtester.py：支持股票回测
- [ ] CLI：扩展命令组

### ⚠️ 新增模块
- [ ] StockFilter：股票筛选器（新增）
- [ ] stock_scoring_weights.yaml：股票评分配置（新增）

---

## 9. 配置参数化检查

### ✅ 已参数化
- 所有评分权重和阈值
- 行业集中度标准
- 排除项规则
- 回测参数

### ✅ 需要参数化
- 数据更新频率
- 缓存策略
- 日志级别
- 性能参数

---

## 10. 文档修改总结

### 需要大幅修改的文档
- ❌ 无（架构设计合理，只需补充复用说明）

### 需要补充说明的文档
- ✅ 02_database_design.md：补充"复用现有表结构"说明
- ✅ 03_quality_screening.md：补充"复用Calculator和Scorer"说明
- ✅ 04_data_acquisition.md：补充"复用IFindClient"说明
- ✅ 05_backtesting.md：补充"复用Backtester"说明
- ✅ 06_cli_tools.md：补充"扩展现有CLI"说明
- ✅ 07_configuration.md：补充"统一配置结构"说明

### 建议
**不需要重写文档**，只需在每个文档开头添加"架构说明"章节，引用00_architecture_optimization.md，说明如何复用现有代码。

---

**相关文档**：
- [架构优化方案](./00_architecture_optimization.md)
- [概述](./01_overview.md)
