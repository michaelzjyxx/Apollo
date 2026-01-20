# 快速开始指南

本指南帮助你快速上手A股行业筛选系统的股票质量筛选功能。

---

## 系统架构

```
行业筛选 → 股票筛选 → 优质公司池
   ↓           ↓            ↓
行业评分    股票评分      投资组合
```

---

## 前置条件

### 1. 环境准备

```bash
# Python 3.10+
python --version

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库准备

```bash
# 运行数据库迁移脚本（创建股票相关表）
python scripts/migrate_stock_tables.py
```

### 3. 配置文件

确保配置文件存在：
- `config/app.yaml` - 应用基础配置
- `config/stock_scoring_weights.yaml` - 股票评分权重配置
- `config/shenwan_industries.yaml` - 申万行业配置

---

## 快速开始

### Step 1: 数据获取

#### 方式1：使用iFinD API（推荐）

如果你有iFinD API权限：

```python
from datetime import datetime
from src.data.ifind_api import IFindAPIClient
from src.data.database import get_session

# 连接API
with IFindAPIClient() as client:
    # 获取行业成分股
    industry_code = "801120.SI"  # 食品饮料
    stock_codes = client.get_industry_stocks(industry_code)

    # 获取股票数据
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2023, 12, 31)

    data = client.batch_fetch_stock_data(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        data_types=['basic', 'financial', 'market']
    )

    # 保存到数据库
    # TODO: 实现数据保存逻辑
```

#### 方式2：手动导入数据

如果没有API权限，可以手动准备CSV数据并导入。

### Step 2: 计算指标

使用计算引擎计算股票指标：

```python
from src.core.calculator import IndicatorCalculator
from src.data.repository import StockFinancialRepository, StockCalculatedRepository

calculator = IndicatorCalculator()

with get_session() as session:
    financial_repo = StockFinancialRepository(session)
    calc_repo = StockCalculatedRepository(session)

    # 获取财务数据
    stock_code = "600519.SH"
    financial_data = financial_repo.get_by_stock(stock_code)

    # 计算指标
    for data in financial_data:
        # 计算各项指标
        roe_3y_avg = calculator.calculate_roe_3y_avg(...)
        roic_3y_avg = calculator.calculate_roic_3y_avg(...)
        # ... 其他指标

        # 保存计算结果
        calc_data = StockCalculated(
            stock_code=stock_code,
            report_date=data.report_date,
            roe_3y_avg=roe_3y_avg,
            roic_3y_avg=roic_3y_avg,
            # ... 其他字段
        )
        calc_repo.save(calc_data)
```

### Step 3: 执行股票筛选

使用CLI工具执行筛选：

```bash
# 筛选指定行业的优质股票
python -m src.cli.main stock screen \
    --industries "801120.SI,801130.SI" \
    --date "2024-01-01" \
    --min-score 60 \
    --output "results/quality_stocks.csv"
```

或者使用Python API：

```python
from datetime import datetime
from src.core.stock_filter import StockFilter
from src.data.database import get_session

with get_session() as session:
    stock_filter = StockFilter(session)

    # 执行筛选
    result = stock_filter.filter(
        industries=["801120.SI", "801130.SI"],
        calc_date=datetime(2024, 1, 1),
        min_score=60
    )

    # 查看结果
    print(f"候选股票: {result['total_candidates']}")
    print(f"最终入池: {result['final_pool']}")

    # 保存结果
    stock_filter.save_results(result)
```

### Step 4: 查看优质公司池

```bash
# 列出优质公司池
python -m src.cli.main pool list --limit 20

# 查看单只股票详情
python -m src.cli.main pool show 600519.SH

# 导出公司池
python -m src.cli.main pool export \
    --output "results/pool.csv" \
    --format csv
```

---

## 筛选流程详解

### 三关卡筛选体系

#### 第一关：基础资格筛选

必须同时满足：
- **盈利能力**：ROE 3年平均 ≥ 10%，ROIC 3年平均 ≥ 8%
- **财务安全**：资产负债率 < 70%，流动比率 > 1.2，速动比率 > 0.8
- **龙头地位**：根据行业集中度确定
  - 高集中度（CR3≥60%）：前3名
  - 中集中度（40%≤CR3<60%）：前2名
  - 低集中度（CR3<40%）：仅第1名

#### 第二关：排除项过滤（一票否决）

以下情况将被排除：
- ST/\*ST股票
- 营收排名持续下降
- 估值陷阱（周期股PE<8且ROE斜率<0）
- 治理风险（质押比例>50%或关联交易>30%）
- 商誉地雷（商誉占净资产>30%）
- 连续业绩下滑（连续2年净利润下降>20%）

#### 第三关：质量评分

**财务质量（50分）**：
- ROE稳定性（15分）：3年平均ROE
- ROIC水平（15分）：3年平均ROIC
- 现金流质量（12分）：经营性现金流/净利润
- 负债率（8分）：资产负债率（值越小得分越高）

**竞争优势（50分）**：
- 龙头地位（15分）：营收排名及占比
- 龙头趋势（10分）：3年排名变化
- 盈利优势（15分）：毛利率相对行业
- 成长性（10分）：3年营收CAGR

**入池标准**：总分 ≥ 60分

#### 行业分散度控制

- 单一行业占比不超过35%
- 小行业（<3只股票）不受限制

---

## 评分权重配置

编辑 `config/stock_scoring_weights.yaml` 调整评分权重：

```yaml
financial_quality:
  total_weight: 50
  roe_stability:
    weight: 15
    rules:
      - min: 20, score: 15  # ROE>20%得满分
      - min: 15, score: 12
      - min: 10, score: 8
      - min: 5, score: 4
  # ... 其他配置
```

---

## CLI命令参考

### stock 命令组

```bash
# 执行股票筛选
python -m src.cli.main stock screen \
    --industries "行业代码1,行业代码2" \
    --date "YYYY-MM-DD" \
    --min-score 60 \
    --output "结果文件路径"

# 计算单只股票得分
python -m src.cli.main stock score 600519.SH \
    --date "YYYY-MM-DD" \
    --detail
```

### pool 命令组

```bash
# 列出优质公司池
python -m src.cli.main pool list \
    --date "YYYY-MM-DD" \
    --industry "行业名称" \
    --min-score 60 \
    --limit 50

# 查看股票详情
python -m src.cli.main pool show 600519.SH \
    --date "YYYY-MM-DD"

# 导出公司池
python -m src.cli.main pool export \
    --output "输出文件" \
    --format csv|excel|json \
    --date "YYYY-MM-DD"
```

---

## 数据表结构

### 核心表

1. **stock** - 股票基础信息
2. **stock_financial** - 股票财务数据
3. **stock_market** - 股票行情数据
4. **stock_calculated** - 股票计算指标
5. **stock_score** - 股票评分结果

### 数据流

```
原始数据 → stock_financial/stock_market
   ↓
计算指标 → stock_calculated
   ↓
质量评分 → stock_score
   ↓
筛选入池 → passed_scoring=True
```

---

## 常见问题

### Q1: 如何添加自定义评分指标？

1. 在 `src/core/calculator.py` 添加计算方法
2. 在 `src/data/models.py` 的 `StockCalculated` 添加字段
3. 在 `config/stock_scoring_weights.yaml` 配置评分规则
4. 在 `src/core/stock_scorer.py` 使用新指标

### Q2: 如何调整筛选标准？

编辑 `config/stock_scoring_weights.yaml`：
- `basic_qualification` - 基础资格标准
- `exclusion` - 排除项标准
- `pass_threshold` - 入池分数线（默认60分）

### Q3: 数据多久更新一次？

建议更新频率：
- 财务数据：季度更新（财报发布后）
- 行情数据：日度更新（收盘后）
- 股东数据：季度更新
- 指标计算：财务数据更新后

### Q4: 如何处理数据缺失？

系统会自动处理：
- 必需字段缺失：排除该股票
- 可选字段缺失：使用默认值（通常为0）
- 异常值：根据验证规则剔除

---

## 下一步

1. **对接数据源**：实现iFinD API调用或导入历史数据
2. **运行首次筛选**：测试完整流程
3. **回测验证**：验证筛选效果
4. **定期更新**：建立自动化更新机制

---

## 技术支持

- 项目文档：`docs/`
- 开发进度：`docs/development_progress.md`
- 字段映射：`docs/ifind_field_mapping.md`
- 需求文档：`docs/product_requirements_framework.md`

如有问题，请参考详细文档或提交Issue。
