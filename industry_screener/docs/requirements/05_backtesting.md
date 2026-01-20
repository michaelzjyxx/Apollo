# 回测验证模块 - 详细需求文档

## 文档信息

**文档类型**：模块需求文档
**版本**：v1.0
**创建日期**：2026-01-19
**状态**：待评审

---

## 1. 模块概述

### 1.1 目标

回测验证模块用于验证质量筛选策略的有效性，通过历史数据回放，评估优质公司池的投资表现。

### 1.2 核心功能

1. **历史回放**：按时间序列回放筛选过程
2. **收益计算**：计算持仓组合的收益表现
3. **绩效分析**：计算各类绩效指标
4. **对比分析**：与基准指数对比
5. **报告生成**：生成回测报告

### 1.3 回测范围

**时间范围**：2019-2024（5年历史数据）
**再平衡频率**：季度（每季度末调仓）
**持仓策略**：等权持仓
**基准指数**：沪深300、申万行业指数

---

## 2. 功能需求

### 2.1 历史回放

#### 2.1.1 时间序列回放

**需求描述**：
按季度遍历历史数据，在每个时间点执行质量筛选

**回放逻辑**：

```python
def backtest_historical(
    start_date: str,
    end_date: str,
    rebalance_freq: str = "Q"  # Q=季度, M=月度
) -> BacktestResult:
    """历史回测"""

    # 生成再平衡日期序列
    rebalance_dates = generate_rebalance_dates(
        start_date, end_date, rebalance_freq
    )

    portfolio_history = []

    for date in rebalance_dates:
        # 1. 在该时间点执行筛选
        pool = quality_filter.filter(date=date)

        # 2. 构建等权组合
        portfolio = build_equal_weight_portfolio(pool)

        # 3. 计算到下一个再平衡日的收益
        returns = calculate_period_returns(
            portfolio,
            start=date,
            end=next_rebalance_date
        )

        portfolio_history.append({
            'date': date,
            'portfolio': portfolio,
            'returns': returns
        })

    return BacktestResult(portfolio_history)
```

#### 2.1.2 数据时点正确性

**需求描述**：
确保使用的数据在该时间点是可获得的，避免未来函数

**关键原则**：

1. **财务数据**：使用报告期 + 公告延迟
   - 年报：报告期后4个月可用
   - 季报：报告期后1个月可用

2. **行情数据**：使用当日收盘价

3. **行业分类**：使用当时的行业分类

**实现示例**：

```python
def get_available_financial_data(stock_code: str, as_of_date: str):
    """获取截至某日期可用的财务数据"""

    # 查询最新的已公告财报
    latest_report = db.query(FinancialData).filter(
        FinancialData.stock_code == stock_code,
        FinancialData.announce_date <= as_of_date
    ).order_by(
        FinancialData.report_date.desc()
    ).first()

    return latest_report
```

---

### 2.2 收益计算

#### 2.2.1 持仓组合构建

**需求描述**：
根据筛选结果构建等权持仓组合

**构建规则**：

- 等权分配：每只股票权重 = 1 / 股票数量
- 初始资金：100万元（可配置）
- 交易成本：买卖各0.1%（可配置）

**实现示例**：

```python
@dataclass
class Portfolio:
    """投资组合"""
    date: str
    stocks: List[str]
    weights: Dict[str, float]
    positions: Dict[str, int]  # 持仓股数
    cash: float
    total_value: float

def build_equal_weight_portfolio(
    stocks: List[str],
    total_capital: float = 1_000_000,
    transaction_cost: float = 0.001
) -> Portfolio:
    """构建等权组合"""

    n_stocks = len(stocks)
    weight_per_stock = 1.0 / n_stocks

    # 获取当前股价
    prices = get_stock_prices(stocks, date)

    # 计算每只股票的持仓
    positions = {}
    total_cost = 0

    for stock in stocks:
        # 分配资金
        allocated = total_capital * weight_per_stock

        # 计算可买股数（100股为1手）
        shares = int(allocated / prices[stock] / 100) * 100

        # 实际成本
        cost = shares * prices[stock] * (1 + transaction_cost)

        positions[stock] = shares
        total_cost += cost

    cash = total_capital - total_cost

    return Portfolio(
        date=date,
        stocks=stocks,
        weights={s: weight_per_stock for s in stocks},
        positions=positions,
        cash=cash,
        total_value=total_capital
    )
```

#### 2.2.2 区间收益计算

**需求描述**：
计算持仓组合在两个再平衡日之间的收益

**计算公式**：

```python
# 组合收益 = Σ(股票i权重 × 股票i收益)
portfolio_return = sum(
    weight_i * (price_end_i / price_start_i - 1)
    for i in stocks
)

# 考虑交易成本
net_return = portfolio_return - transaction_cost
```

**实现示例**：

```python
def calculate_period_returns(
    portfolio: Portfolio,
    start_date: str,
    end_date: str
) -> PeriodReturn:
    """计算区间收益"""

    # 获取期初期末价格
    start_prices = get_stock_prices(portfolio.stocks, start_date)
    end_prices = get_stock_prices(portfolio.stocks, end_date)

    # 计算每只股票的收益
    stock_returns = {}
    for stock in portfolio.stocks:
        stock_returns[stock] = (
            end_prices[stock] / start_prices[stock] - 1
        )

    # 计算组合收益
    portfolio_return = sum(
        portfolio.weights[stock] * stock_returns[stock]
        for stock in portfolio.stocks
    )

    # 计算组合价值
    end_value = sum(
        portfolio.positions[stock] * end_prices[stock]
        for stock in portfolio.stocks
    ) + portfolio.cash

    return PeriodReturn(
        start_date=start_date,
        end_date=end_date,
        portfolio_return=portfolio_return,
        start_value=portfolio.total_value,
        end_value=end_value,
        stock_returns=stock_returns
    )
```

#### 2.2.3 再平衡处理

**需求描述**：
在再平衡日调整持仓，卖出不在新池中的股票，买入新股票

**再平衡逻辑**：

```python
def rebalance_portfolio(
    old_portfolio: Portfolio,
    new_stocks: List[str],
    date: str
) -> Portfolio:
    """再平衡组合"""

    # 1. 卖出不在新池中的股票
    stocks_to_sell = set(old_portfolio.stocks) - set(new_stocks)
    for stock in stocks_to_sell:
        shares = old_portfolio.positions[stock]
        price = get_stock_price(stock, date)
        proceeds = shares * price * (1 - transaction_cost)
        old_portfolio.cash += proceeds
        del old_portfolio.positions[stock]

    # 2. 计算当前总价值
    current_value = old_portfolio.cash + sum(
        old_portfolio.positions[stock] * get_stock_price(stock, date)
        for stock in old_portfolio.positions
    )

    # 3. 构建新的等权组合
    new_portfolio = build_equal_weight_portfolio(
        new_stocks,
        total_capital=current_value,
        transaction_cost=transaction_cost
    )

    return new_portfolio
```

---

### 2.3 绩效分析

#### 2.3.1 收益指标

**需求描述**：
计算各类收益指标

**指标列表**：

| 指标 | 计算公式 | 说明 |
|------|---------|------|
| 累计收益率 | (期末价值 / 期初价值) - 1 | 总收益 |
| 年化收益率 | (1 + 累计收益率)^(1/年数) - 1 | 年化表现 |
| 区间收益率 | 每个再平衡期的收益率 | 分段表现 |

**实现示例**：

```python
def calculate_return_metrics(
    portfolio_history: List[PeriodReturn]
) -> ReturnMetrics:
    """计算收益指标"""

    # 累计收益率
    total_return = (
        portfolio_history[-1].end_value /
        portfolio_history[0].start_value - 1
    )

    # 年化收益率
    years = (
        (portfolio_history[-1].end_date -
         portfolio_history[0].start_date).days / 365
    )
    annualized_return = (1 + total_return) ** (1 / years) - 1

    # 区间收益率
    period_returns = [p.portfolio_return for p in portfolio_history]

    return ReturnMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        period_returns=period_returns
    )
```

#### 2.3.2 风险指标

**需求描述**：
计算各类风险指标

**指标列表**：

| 指标 | 计算公式 | 说明 |
|------|---------|------|
| 最大回撤 | max(峰值 - 当前值) / 峰值 | 最大跌幅 |
| 波动率 | std(收益率) × √252 | 年化波动 |
| 下行波动率 | std(负收益率) × √252 | 下行风险 |

**实现示例**：

```python
def calculate_risk_metrics(
    portfolio_history: List[PeriodReturn]
) -> RiskMetrics:
    """计算风险指标"""

    # 计算净值曲线
    nav_curve = calculate_nav_curve(portfolio_history)

    # 最大回撤
    max_drawdown = 0
    peak = nav_curve[0]

    for nav in nav_curve:
        if nav > peak:
            peak = nav
        drawdown = (peak - nav) / peak
        max_drawdown = max(max_drawdown, drawdown)

    # 波动率
    returns = [p.portfolio_return for p in portfolio_history]
    volatility = np.std(returns) * np.sqrt(252 / len(returns))

    # 下行波动率
    negative_returns = [r for r in returns if r < 0]
    downside_volatility = (
        np.std(negative_returns) * np.sqrt(252 / len(returns))
        if negative_returns else 0
    )

    return RiskMetrics(
        max_drawdown=max_drawdown,
        volatility=volatility,
        downside_volatility=downside_volatility
    )
```

#### 2.3.3 风险调整收益指标

**需求描述**：
计算风险调整后的收益指标

**指标列表**：

| 指标 | 计算公式 | 说明 |
|------|---------|------|
| 夏普比率 | (年化收益 - 无风险利率) / 波动率 | 单位风险收益 |
| 索提诺比率 | (年化收益 - 无风险利率) / 下行波动率 | 下行风险收益 |
| 卡玛比率 | 年化收益 / 最大回撤 | 回撤调整收益 |

**实现示例**：

```python
def calculate_risk_adjusted_metrics(
    return_metrics: ReturnMetrics,
    risk_metrics: RiskMetrics,
    risk_free_rate: float = 0.03
) -> RiskAdjustedMetrics:
    """计算风险调整收益指标"""

    # 夏普比率
    sharpe_ratio = (
        (return_metrics.annualized_return - risk_free_rate) /
        risk_metrics.volatility
    )

    # 索提诺比率
    sortino_ratio = (
        (return_metrics.annualized_return - risk_free_rate) /
        risk_metrics.downside_volatility
        if risk_metrics.downside_volatility > 0 else 0
    )

    # 卡玛比率
    calmar_ratio = (
        return_metrics.annualized_return /
        risk_metrics.max_drawdown
        if risk_metrics.max_drawdown > 0 else 0
    )

    return RiskAdjustedMetrics(
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio
    )
```

#### 2.3.4 胜率统计

**需求描述**：
统计持仓股票的胜率

**统计指标**：

| 指标 | 计算方法 | 说明 |
|------|---------|------|
| 期间胜率 | 正收益期数 / 总期数 | 盈利频率 |
| 个股胜率 | 正收益股票数 / 总股票数 | 选股准确率 |
| 平均盈亏比 | 平均盈利 / 平均亏损 | 盈亏对比 |

**实现示例**：

```python
def calculate_win_rate_metrics(
    portfolio_history: List[PeriodReturn]
) -> WinRateMetrics:
    """计算胜率指标"""

    # 期间胜率
    period_returns = [p.portfolio_return for p in portfolio_history]
    win_periods = sum(1 for r in period_returns if r > 0)
    period_win_rate = win_periods / len(period_returns)

    # 个股胜率
    all_stock_returns = []
    for period in portfolio_history:
        all_stock_returns.extend(period.stock_returns.values())

    win_stocks = sum(1 for r in all_stock_returns if r > 0)
    stock_win_rate = win_stocks / len(all_stock_returns)

    # 平均盈亏比
    profits = [r for r in all_stock_returns if r > 0]
    losses = [abs(r) for r in all_stock_returns if r < 0]

    avg_profit = np.mean(profits) if profits else 0
    avg_loss = np.mean(losses) if losses else 0
    profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0

    return WinRateMetrics(
        period_win_rate=period_win_rate,
        stock_win_rate=stock_win_rate,
        profit_loss_ratio=profit_loss_ratio
    )
```

---

### 2.4 对比分析

#### 2.4.1 基准对比

**需求描述**：
与沪深300指数对比

**对比指标**：

- 累计收益对比
- 年化收益对比
- 最大回撤对比
- 夏普比率对比
- 超额收益（Alpha）

**实现示例**：

```python
def compare_with_benchmark(
    strategy_metrics: PerformanceMetrics,
    benchmark_code: str = "000300.SH"  # 沪深300
) -> BenchmarkComparison:
    """与基准对比"""

    # 获取基准数据
    benchmark_returns = get_index_returns(
        benchmark_code,
        start_date,
        end_date
    )

    # 计算基准指标
    benchmark_metrics = calculate_performance_metrics(
        benchmark_returns
    )

    # 计算超额收益
    excess_return = (
        strategy_metrics.annualized_return -
        benchmark_metrics.annualized_return
    )

    # 计算信息比率
    tracking_error = np.std(
        strategy_returns - benchmark_returns
    ) * np.sqrt(252)

    information_ratio = excess_return / tracking_error

    return BenchmarkComparison(
        strategy=strategy_metrics,
        benchmark=benchmark_metrics,
        excess_return=excess_return,
        information_ratio=information_ratio
    )
```

#### 2.4.2 行业对比

**需求描述**：
与申万行业指数对比

**对比维度**：

- 各行业的收益贡献
- 行业配置效果
- 行业内选股效果

---

### 2.5 报告生成

#### 2.5.1 回测报告结构

**需求描述**：
生成完整的回测报告

**报告内容**：

1. **回测概要**
   - 回测时间范围
   - 再平衡频率
   - 初始资金
   - 交易成本

2. **收益表现**
   - 累计收益率
   - 年化收益率
   - 净值曲线图

3. **风险分析**
   - 最大回撤
   - 波动率
   - 回撤曲线图

4. **风险调整收益**
   - 夏普比率
   - 索提诺比率
   - 卡玛比率

5. **胜率统计**
   - 期间胜率
   - 个股胜率
   - 盈亏比

6. **基准对比**
   - vs 沪深300
   - 超额收益
   - 信息比率

7. **持仓分析**
   - 平均持仓数量
   - 换手率
   - 行业分布

8. **年度表现**
   - 各年度收益
   - 各年度最大回撤

**报告格式**：

- Markdown格式
- 包含图表（使用matplotlib）
- 可导出为PDF

---

## 3. 技术规格

### 3.1 核心类设计

#### 3.1.1 Backtester 类

```python
class Backtester:
    """回测引擎"""

    def __init__(
        self,
        quality_filter: QualityFilter,
        config: BacktestConfig
    ):
        self.quality_filter = quality_filter
        self.config = config

    def run(
        self,
        start_date: str,
        end_date: str
    ) -> BacktestResult:
        """运行回测"""

        # 1. 生成再平衡日期
        rebalance_dates = self._generate_rebalance_dates(
            start_date, end_date
        )

        # 2. 历史回放
        portfolio_history = self._historical_replay(
            rebalance_dates
        )

        # 3. 计算绩效指标
        performance = self._calculate_performance(
            portfolio_history
        )

        # 4. 基准对比
        comparison = self._compare_with_benchmark(
            performance
        )

        # 5. 生成报告
        report = self._generate_report(
            performance, comparison
        )

        return BacktestResult(
            portfolio_history=portfolio_history,
            performance=performance,
            comparison=comparison,
            report=report
        )
```

#### 3.1.2 PerformanceAnalyzer 类

```python
class PerformanceAnalyzer:
    """绩效分析器"""

    def analyze(
        self,
        portfolio_history: List[PeriodReturn]
    ) -> PerformanceMetrics:
        """分析绩效"""

        return_metrics = self._calculate_return_metrics(
            portfolio_history
        )

        risk_metrics = self._calculate_risk_metrics(
            portfolio_history
        )

        risk_adjusted = self._calculate_risk_adjusted_metrics(
            return_metrics, risk_metrics
        )

        win_rate = self._calculate_win_rate_metrics(
            portfolio_history
        )

        return PerformanceMetrics(
            returns=return_metrics,
            risks=risk_metrics,
            risk_adjusted=risk_adjusted,
            win_rate=win_rate
        )
```

### 3.2 数据模型

#### 3.2.1 BacktestResult 模型

```python
@dataclass
class BacktestResult:
    """回测结果"""
    # 基本信息
    start_date: str
    end_date: str
    rebalance_freq: str
    initial_capital: float

    # 持仓历史
    portfolio_history: List[PeriodReturn]

    # 绩效指标
    performance: PerformanceMetrics

    # 基准对比
    comparison: BenchmarkComparison

    # 报告
    report: str
```

#### 3.2.2 PerformanceMetrics 模型

```python
@dataclass
class PerformanceMetrics:
    """绩效指标"""
    # 收益指标
    total_return: float
    annualized_return: float
    period_returns: List[float]

    # 风险指标
    max_drawdown: float
    volatility: float
    downside_volatility: float

    # 风险调整收益
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # 胜率统计
    period_win_rate: float
    stock_win_rate: float
    profit_loss_ratio: float
```

### 3.3 配置文件

#### 3.3.1 backtest_params.yaml

```yaml
# 回测参数
backtest:
  # 时间范围
  default_start_date: "2019-01-01"
  default_end_date: "2024-12-31"

  # 再平衡频率
  rebalance_freq: "Q"  # Q=季度, M=月度, Y=年度

  # 资金设置
  initial_capital: 1000000  # 100万

  # 交易成本
  transaction_cost:
    buy: 0.001  # 0.1%
    sell: 0.001  # 0.1%

  # 持仓策略
  position:
    weighting: "equal"  # equal=等权, market_cap=市值加权
    min_stocks: 10  # 最少持仓数
    max_stocks: 100  # 最多持仓数

  # 基准设置
  benchmark:
    default: "000300.SH"  # 沪深300
    alternatives:
      - "000905.SH"  # 中证500
      - "000852.SH"  # 中证1000

  # 风险参数
  risk:
    risk_free_rate: 0.03  # 无风险利率3%

  # 报告设置
  report:
    format: "markdown"  # markdown | html | pdf
    include_charts: true
    chart_style: "seaborn"
```

---

## 4. 接口设计

### 4.1 回测接口

```python
# 运行回测
def run_backtest(
    start_date: str,
    end_date: str,
    config: Optional[BacktestConfig] = None
) -> BacktestResult:
    """运行回测"""

# 快速回测（使用默认参数）
def quick_backtest() -> BacktestResult:
    """快速回测（最近5年）"""

# 参数敏感性分析
def sensitivity_analysis(
    param_name: str,
    param_values: List[Any]
) -> Dict[Any, BacktestResult]:
    """参数敏感性分析"""
```

### 4.2 绩效分析接口

```python
# 计算绩效指标
def calculate_performance(
    portfolio_history: List[PeriodReturn]
) -> PerformanceMetrics:
    """计算绩效指标"""

# 基准对比
def compare_with_benchmark(
    strategy_returns: List[float],
    benchmark_code: str
) -> BenchmarkComparison:
    """与基准对比"""
```

### 4.3 报告生成接口

```python
# 生成回测报告
def generate_backtest_report(
    result: BacktestResult,
    output_path: str,
    format: str = "markdown"
) -> None:
    """生成回测报告"""

# 生成图表
def generate_charts(
    result: BacktestResult,
    output_dir: str
) -> List[str]:
    """生成图表"""
```

---

## 5. 实现计划

### 5.1 Phase 1: 基础框架（Week 1）

- [ ] 创建核心类结构
- [ ] 实现配置加载
- [ ] 单元测试

### 5.2 Phase 2: 历史回放（Week 2）

- [ ] 实现时间序列回放
- [ ] 实现数据时点正确性
- [ ] 集成测试

### 5.3 Phase 3: 收益计算（Week 3）

- [ ] 实现持仓组合构建
- [ ] 实现区间收益计算
- [ ] 实现再平衡逻辑
- [ ] 单元测试

### 5.4 Phase 4: 绩效分析（Week 4）

- [ ] 实现各类绩效指标
- [ ] 实现基准对比
- [ ] 单元测试

### 5.5 Phase 5: 报告生成（Week 5）

- [ ] 实现报告生成
- [ ] 实现图表生成
- [ ] 端到端测试

---

## 6. 测试需求

### 6.1 单元测试

**测试覆盖率目标**：> 80%

**关键测试用例**：

1. **收益计算测试**
   - 等权组合构建
   - 区间收益计算
   - 再平衡逻辑

2. **绩效指标测试**
   - 各类指标计算
   - 边界情况
   - 异常数据

3. **时点正确性测试**
   - 财务数据可用性
   - 未来函数检测

### 6.2 集成测试

**测试场景**：

1. **完整回测流程**
   - 历史回放
   - 收益计算
   - 绩效分析
   - 报告生成

2. **不同参数组合**
   - 不同再平衡频率
   - 不同持仓策略
   - 不同时间范围

### 6.3 验证测试

**验证方法**：

1. **手工验证**
   - 抽样验证收益计算
   - 对比已知结果

2. **逻辑验证**
   - 净值曲线单调性
   - 收益率合理性

---

## 7. 风险与依赖

### 7.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 未来函数 | 高 | 严格的时点检查 |
| 数据缺失 | 中 | 缺失值处理 |
| 计算错误 | 高 | 充分测试验证 |

### 7.2 数据依赖

- 历史财务数据（5年）
- 历史行情数据（5年）
- 基准指数数据

---

**相关文档**：
- [概述](./01_overview.md)
- [质量筛选模块](./03_quality_screening.md)
- [数据获取模块](./04_data_acquisition.md)
