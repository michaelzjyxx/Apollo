# 质量筛选模块 - 详细需求文档

## 文档信息

**文档类型**：模块需求文档
**版本**：v1.0
**创建日期**：2026-01-19
**状态**：待评审

---

## 1. 模块概述

### 1.1 目标

质量筛选模块是股票筛选系统的核心模块，负责从优质行业中筛选出基本面优秀的公司，构建优质公司池。

**核心定位**：筛选出具有稳定盈利能力、竞争优势明显、财务安全的优质公司，为后续的择时策略提供监控范围。

### 1.2 输入输出

**输入**：
- 优质行业列表（申万二级行业代码）
- 筛选参数配置（可选，使用默认值）
- 筛选基准日期（默认为最新财报日期）

**输出**：
- 优质公司池（50-100只股票）
- 每只股票的质量评分明细
- 筛选过程日志和统计信息

### 1.3 核心功能

1. **基础资格筛选**：Pass/Fail 准入门槛
2. **排除项过滤**：一票否决机制
3. **质量评分**：100分制综合评分
4. **行业分散度控制**：避免单一行业过度集中

---

## 2. 功能需求

### 2.1 基础资格筛选（第一关）

#### 2.1.1 长期盈利能力稳定

**需求描述**：
- 计算公司近3年平均ROE和ROIC
- ROE近3年平均 ≥ 12%
- ROIC近3年平均 ≥ 10%

**计算公式**：

```python
# ROE计算
ROE = 净利润 / 股东权益
ROE_3y_avg = (ROE_year1 + ROE_year2 + ROE_year3) / 3

# ROIC计算
NOPAT = 净利润 + 利息费用 × (1 - 税率)
投入资本 = 股东权益 + 有息负债
ROIC = NOPAT / 投入资本
ROIC_3y_avg = (ROIC_year1 + ROIC_year2 + ROIC_year3) / 3
```

**数据来源**：
- 财务报表（近3年年报）
- 字段：净利润、股东权益、利息费用、所得税率、有息负债

**验证规则**：
- 不满足条件直接淘汰
- 允许单年波动，但不能持续下滑

#### 2.1.2 行业龙头地位

**需求描述**：
根据行业集中度（CR3）动态调整龙头标准

**步骤1：计算行业集中度CR3**
```python
CR3 = 行业前3名营收之和 / 行业总营收
```

**步骤2：根据CR3确定龙头标准**

| 行业集中度 | CR3范围 | 龙头标准 | 示例行业 |
|-----------|---------|---------|---------|
| 高集中度 | CR3 ≥ 50% | 营收排名前3名 | 白酒、乳制品、调味品 |
| 中集中度 | 30% ≤ CR3 < 50% | 营收排名前2名 | 家电、化工、医药 |
| 低集中度 | CR3 < 30% | 仅营收排名第1名 | 机械设备、纺织服装 |

**步骤3：相对规模要求**
- 营收 ≥ 行业第1名的30%
- 目的：避免"伪龙头"

**数据来源**：
- 申万二级行业成分股财报
- 字段：营业收入

#### 2.1.3 财务安全

**需求描述**：
确保公司财务健康，避免周期底部时资金链断裂

**指标要求**：

| 指标 | 阈值 | 计算公式 |
|------|------|---------|
| 负债率 | < 70% | 总负债 / 总资产 |
| 经营性现金流 | > 0 | 近4个季度累计 |
| 流动比率 | > 1 | 流动资产 / 流动负债 |
| 速动比率 | > 0.8 | 速动资产 / 流动负债 |

**数据来源**：
- 资产负债表
- 现金流量表

#### 2.1.4 竞争优势基础

**需求描述**：
满足以下任一条件即可

**条件1**：满足龙头地位要求（见2.1.2）

**条件2**：毛利率 ≥ 行业中位数

**数据来源**：
- 利润表：营业收入、营业成本
- 计算：毛利率 = (营业收入 - 营业成本) / 营业收入

---

### 2.2 排除项过滤（第二关）

#### 2.2.1 ST、*ST股票

**需求描述**：
- 识别方法：股票代码或名称包含ST标记
- 原因：有退市风险

**实现方式**：
```python
if 'ST' in stock_name or '*ST' in stock_name:
    exclude = True
```

#### 2.2.2 营收排名持续下降

**需求描述**：
- 计算方法：公司在所属二级行业的营收排名连续2年下降
- 原因：竞争力正在减弱，护城河正在消失

**实现逻辑**：
```python
rank_current = get_revenue_rank(stock, current_year)
rank_1y_ago = get_revenue_rank(stock, current_year - 1)
rank_2y_ago = get_revenue_rank(stock, current_year - 2)

if rank_current > rank_1y_ago > rank_2y_ago:
    exclude = True  # 排名数字越大表示排名越靠后
```

#### 2.2.3 估值陷阱（区分周期股和非周期股）

**非周期股**：
- 识别方法：PE很低但ROE持续下降（近3年ROE斜率 < -2%）
- 原因：低估值是合理的，不是错杀
- 适用行业：消费、医药、TMT、公用事业

**周期股**：
- 不适用此规则（允许ROE周期性波动）
- 但要求：近3年ROE最低值 ≥ 8%
- 适用行业：化工、有色金属、钢铁、煤炭、农林牧渔、机械设备、汽车、建筑材料、房地产

**实现逻辑**：
```python
# 计算ROE斜率
roe_slope = calculate_slope([roe_y1, roe_y2, roe_y3])

if is_non_cyclical_industry(stock):
    if pe < 10 and roe_slope < -0.02:
        exclude = True
else:  # 周期股
    if min([roe_y1, roe_y2, roe_y3]) < 0.08:
        exclude = True
```

#### 2.2.4 治理风险

**需求描述**：
识别以下任一情况直接剔除

**指标要求**：

| 风险类型 | 阈值 | 数据来源 |
|---------|------|---------|
| 大股东质押比例 | > 50% | 股东信息 |
| 关联交易占比 | > 30% | 关联交易金额/营业收入 |
| 财务造假历史 | 近5年内 | 证监会处罚记录 |

#### 2.2.5 商誉地雷

**需求描述**：
- 计算方法：商誉/净资产 > 30%
- 原因：有减值风险

**数据来源**：
- 资产负债表：商誉、股东权益

#### 2.2.6 连续业绩下滑

**需求描述**：
- 识别方法：连续2年净利润同比增长率 < -20%
- 原因：基本面恶化

**实现逻辑**：
```python
growth_y1 = (profit_y1 - profit_y2) / profit_y2
growth_y2 = (profit_y2 - profit_y3) / profit_y3

if growth_y1 < -0.20 and growth_y2 < -0.20:
    exclude = True
```

---

### 2.3 质量评分（第三关）

#### 2.3.1 评分总览

**总分**：100分
**入池标准**：≥ 60分
**评分结构**：
- 财务质量得分：50分
- 竞争优势得分：50分

#### 2.3.2 财务质量得分（50分）

**1. ROE稳定性（15分）**

| ROE近3年平均 | 得分 |
|-------------|------|
| > 20% | 15分 |
| 15-20% | 10分 |
| 12-15% | 6分 |

**2. ROIC水平（15分）**

| ROIC近3年平均 | 得分 |
|--------------|------|
| > 15% | 15分 |
| 12-15% | 10分 |
| 10-12% | 6分 |

**3. 现金流质量（12分）**

| 经营性现金流/净利润(TTM) | 得分 |
|------------------------|------|
| > 1.2 | 12分 |
| 0.8-1.2 | 8分 |
| 0.5-0.8 | 4分 |

**4. 负债率（8分）**

| 总负债/总资产 | 得分 |
|-------------|------|
| < 30% | 8分 |
| 30-50% | 5分 |
| 50-70% | 2分 |

#### 2.3.3 竞争优势得分（50分）

**1. 龙头地位（15分）**

| 龙头地位 | 得分 | 条件 |
|---------|------|------|
| 绝对龙头 | 15分 | 行业第1名 且 营收≥第2名的150% |
| 领先龙头 | 12分 | 行业第1名 且 营收≥第2名的100% |
| 龙头 | 10分 | 行业第1名 |
| 强势第二 | 8分 | 行业第2名 且 营收≥第1名的50% |
| 前列 | 5分 | 行业第2名 或 第3名 |

**2. 龙头地位趋势（10分）**

| 排名变化 | 得分 | 说明 |
|---------|------|------|
| 上升2名以上 | 10分 | 快速崛起 |
| 上升1名 | 8分 | 稳步上升 |
| 不变 | 6分 | 稳定 |
| 下降1名 | 3分 | 轻微下滑 |
| 下降2名以上 | 0分 | 竞争力减弱 |

**3. 盈利能力优势（15分）**

计算公式：
```python
相对优势 = (公司毛利率 - 行业中位数) / 行业中位数 × 100%
```

| 相对优势 | 得分 | 说明 |
|---------|------|------|
| > 30% | 15分 | 显著优势 |
| 20-30% | 12分 | 明显优势 |
| 10-20% | 9分 | 一定优势 |
| 0-10% | 5分 | 略有优势 |
| < 0% | 0分 | 无优势 |

**备注**：如果毛利率数据不可靠（如贸易型企业），可用ROE相对优势替代

**4. 成长性（10分）**

计算公式：
```python
CAGR = (今年营收 / 3年前营收) ^ (1/3) - 1
```

| 营收3年CAGR | 得分 | 说明 |
|------------|------|------|
| ≥ 20% | 10分 | 高成长 |
| 15-20% | 8分 | 较高成长 |
| 10-15% | 6分 | 中等成长 |
| 5-10% | 3分 | 低成长 |
| < 5% | 1分 | 停滞 |

---

### 2.4 行业分散度控制

#### 2.4.1 约束规则

**需求描述**：
- 单一申万一级行业最多占优质公司池的35%
- 如果某行业超过35%，按质量得分从高到低截取

**例外情况**：
- 如果优质公司池总数 < 30只，不执行此约束
- 如果某行业只有1-2只公司入池，不受此约束

**实现逻辑**：
```python
def apply_industry_diversification(pool, max_ratio=0.35):
    if len(pool) < 30:
        return pool

    industry_counts = pool.groupby('l1_industry').size()
    max_count = int(len(pool) * max_ratio)

    result = []
    for industry, stocks in pool.groupby('l1_industry'):
        if len(stocks) <= 2:
            result.extend(stocks)
        else:
            # 按得分排序，取前max_count只
            top_stocks = stocks.nlargest(max_count, 'total_score')
            result.extend(top_stocks)

    return result
```

---

## 3. 技术规格

### 3.1 核心类设计

#### 3.1.1 QualityFilter 类

```python
class QualityFilter:
    """质量筛选器"""

    def __init__(self, config: FilterConfig):
        self.config = config
        self.repo = StockRepository()

    def filter(self, industries: List[str], date: str) -> List[Stock]:
        """执行质量筛选"""
        # 步骤1：获取行业成分股
        stocks = self._get_industry_stocks(industries)

        # 步骤2：计算行业集中度
        cr3_map = self._calculate_cr3(stocks)

        # 步骤3：基础资格筛选
        qualified = self._basic_qualification(stocks, cr3_map)

        # 步骤4：排除项过滤
        filtered = self._exclusion_filter(qualified)

        # 步骤5：质量评分
        scored = self._quality_scoring(filtered)

        # 步骤6：筛选入池
        pool = self._select_by_score(scored, threshold=60)

        # 步骤7：行业分散度控制
        final_pool = self._apply_diversification(pool)

        return final_pool
```

#### 3.1.2 QualityScorer 类

```python
class QualityScorer:
    """质量评分器"""

    def score(self, stock: Stock) -> QualityScore:
        """计算质量得分"""
        financial_score = self._financial_quality_score(stock)
        competitive_score = self._competitive_advantage_score(stock)

        return QualityScore(
            total=financial_score + competitive_score,
            financial=financial_score,
            competitive=competitive_score,
            details=self._get_score_details(stock)
        )

    def _financial_quality_score(self, stock: Stock) -> float:
        """财务质量得分（50分）"""
        roe_score = self._roe_stability_score(stock)
        roic_score = self._roic_level_score(stock)
        cashflow_score = self._cashflow_quality_score(stock)
        leverage_score = self._leverage_score(stock)

        return roe_score + roic_score + cashflow_score + leverage_score

    def _competitive_advantage_score(self, stock: Stock) -> float:
        """竞争优势得分（50分）"""
        leader_score = self._leader_position_score(stock)
        trend_score = self._leader_trend_score(stock)
        margin_score = self._profit_margin_score(stock)
        growth_score = self._growth_score(stock)

        return leader_score + trend_score + margin_score + growth_score
```

### 3.2 数据模型

#### 3.2.1 QualityScore 模型

```python
@dataclass
class QualityScore:
    """质量评分"""
    stock_code: str
    stock_name: str
    total_score: float  # 总分 0-100
    financial_score: float  # 财务质量 0-50
    competitive_score: float  # 竞争优势 0-50

    # 财务质量明细
    roe_stability: float  # 0-15
    roic_level: float  # 0-15
    cashflow_quality: float  # 0-12
    leverage: float  # 0-8

    # 竞争优势明细
    leader_position: float  # 0-15
    leader_trend: float  # 0-10
    profit_margin: float  # 0-15
    growth: float  # 0-10

    # 关键指标
    roe_3y_avg: float
    roic_3y_avg: float
    debt_ratio: float
    revenue_rank: int
    revenue_rank_3y_ago: int

    # 入池理由
    reason: str
```

#### 3.2.2 FilterResult 模型

```python
@dataclass
class FilterResult:
    """筛选结果"""
    date: str
    total_candidates: int  # 候选股票数
    after_basic: int  # 基础资格筛选后
    after_exclusion: int  # 排除项过滤后
    after_scoring: int  # 评分后
    final_pool_size: int  # 最终入池数量

    pool: List[QualityScore]  # 优质公司池
    excluded: Dict[str, List[str]]  # 被排除的股票及原因
    statistics: Dict[str, Any]  # 统计信息
```

### 3.3 配置文件

#### 3.3.1 quality_filter_rules.yaml

```yaml
# 基础资格筛选
basic_qualification:
  roe_3y_avg_min: 0.12
  roic_3y_avg_min: 0.10
  debt_ratio_max: 0.70
  operating_cashflow_min: 0
  current_ratio_min: 1.0
  quick_ratio_min: 0.8
  revenue_vs_leader_min: 0.30

# 行业集中度标准
industry_concentration:
  high_cr3_threshold: 0.50  # CR3 >= 50%
  high_cr3_top_n: 3
  medium_cr3_threshold: 0.30  # 30% <= CR3 < 50%
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

# 周期行业定义
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
  max_industry_ratio: 0.35
  min_pool_size_for_diversification: 30
  small_industry_threshold: 2
```

#### 3.3.2 quality_scoring_weights.yaml

```yaml
# 财务质量评分（50分）
financial_quality:
  roe_stability:
    weight: 15
    thresholds:
      - [0.20, 15]  # >20%: 15分
      - [0.15, 10]  # 15-20%: 10分
      - [0.12, 6]   # 12-15%: 6分

  roic_level:
    weight: 15
    thresholds:
      - [0.15, 15]
      - [0.12, 10]
      - [0.10, 6]

  cashflow_quality:
    weight: 12
    thresholds:
      - [1.2, 12]
      - [0.8, 8]
      - [0.5, 4]

  leverage:
    weight: 8
    thresholds:
      - [0.30, 8]
      - [0.50, 5]
      - [0.70, 2]

# 竞争优势评分（50分）
competitive_advantage:
  leader_position:
    weight: 15
    rules:
      absolute_leader: [1.50, 15]  # 第1名且营收≥第2名150%
      leading_leader: [1.00, 12]   # 第1名且营收≥第2名100%
      leader: [0, 10]              # 第1名
      strong_second: [0.50, 8]     # 第2名且营收≥第1名50%
      top_tier: [0, 5]             # 第2或第3名

  leader_trend:
    weight: 10
    thresholds:
      - [2, 10]   # 上升2名以上
      - [1, 8]    # 上升1名
      - [0, 6]    # 不变
      - [-1, 3]   # 下降1名
      - [-2, 0]   # 下降2名以上

  profit_margin:
    weight: 15
    thresholds:
      - [0.30, 15]  # 超出30%
      - [0.20, 12]  # 超出20-30%
      - [0.10, 9]   # 超出10-20%
      - [0.00, 5]   # 超出0-10%

  growth:
    weight: 10
    thresholds:
      - [0.20, 10]  # ≥20%
      - [0.15, 8]   # 15-20%
      - [0.10, 6]   # 10-15%
      - [0.05, 3]   # 5-10%
      - [0.00, 1]   # <5%

# 入池标准
pool_selection:
  min_total_score: 60
```

---

## 4. 接口设计

### 4.1 主要接口

#### 4.1.1 筛选接口

```python
def filter_quality_stocks(
    industries: List[str],
    date: Optional[str] = None,
    config: Optional[FilterConfig] = None
) -> FilterResult:
    """
    执行质量筛选

    Args:
        industries: 优质行业列表（申万二级行业代码）
        date: 筛选基准日期，默认为最新财报日期
        config: 筛选配置，默认使用配置文件

    Returns:
        FilterResult: 筛选结果
    """
```

#### 4.1.2 评分接口

```python
def score_stock(
    stock_code: str,
    date: Optional[str] = None
) -> QualityScore:
    """
    计算单只股票的质量得分

    Args:
        stock_code: 股票代码
        date: 评分基准日期

    Returns:
        QualityScore: 质量评分
    """
```

#### 4.1.3 查询接口

```python
def get_quality_pool(
    date: Optional[str] = None,
    min_score: Optional[float] = None
) -> List[QualityScore]:
    """
    获取优质公司池

    Args:
        date: 查询日期
        min_score: 最低得分过滤

    Returns:
        List[QualityScore]: 优质公司列表
    """
```

---

## 5. 实现计划

### 5.1 Phase 1: 基础框架（Week 1-2）

- [ ] 创建核心类结构
- [ ] 实现配置加载
- [ ] 实现数据访问层接口
- [ ] 单元测试

### 5.2 Phase 2: 筛选逻辑（Week 3-4）

- [ ] 实现基础资格筛选
- [ ] 实现排除项过滤
- [ ] 实现质量评分
- [ ] 实现行业分散度控制
- [ ] 集成测试

### 5.3 Phase 3: 优化与验证（Week 5-6）

- [ ] 性能优化
- [ ] 边界情况处理
- [ ] 回测验证
- [ ] 文档完善

---

## 6. 测试需求

### 6.1 单元测试

**测试覆盖率目标**：> 80%

**关键测试用例**：

1. **ROE/ROIC计算测试**
   - 正常情况
   - 边界值
   - 异常数据

2. **行业集中度计算测试**
   - 高/中/低集中度
   - 边界情况

3. **评分逻辑测试**
   - 各项得分计算
   - 总分汇总
   - 边界值处理

4. **排除项测试**
   - 各类排除规则
   - 周期股vs非周期股
   - 组合情况

### 6.2 集成测试

**测试场景**：

1. **完整筛选流程**
   - 输入优质行业列表
   - 验证输出公司池
   - 检查评分合理性

2. **历史数据回放**
   - 使用历史数据
   - 验证筛选结果
   - 对比人工筛选

3. **边界情况**
   - 空行业列表
   - 无符合条件股票
   - 单一行业过多股票

### 6.3 性能测试

**性能指标**：

| 场景 | 数据量 | 目标时间 |
|------|--------|---------|
| 单行业筛选 | 50只股票 | < 10秒 |
| 全市场筛选 | 5000只股票 | < 5分钟 |
| 单股票评分 | 1只股票 | < 1秒 |

---

## 7. 风险与依赖

### 7.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| ROIC计算复杂 | 中 | 简化公式，提供备选方案 |
| 数据缺失 | 高 | 数据验证，缺失值处理 |
| 性能瓶颈 | 中 | 缓存，并行计算 |

### 7.2 数据依赖

- 财务数据：年报、季报
- 行情数据：股价、市值
- 行业数据：申万分类、成分股
- 治理数据：股东质押、关联交易、处罚记录

---

**相关文档**：
- [概述](./01_overview.md)
- [数据库设计](./02_database_design.md)
- [数据获取模块](./04_data_acquisition.md)
