# 配置管理 - 详细需求文档

## 文档信息

**文档类型**：模块需求文档
**版本**：v1.0
**创建日期**：2026-01-19
**状态**：待评审

---

## 1. 模块概述

### 1.1 目标

提供灵活的配置管理机制，允许用户通过配置文件或命令行参数调整系统行为，无需修改代码。

### 1.2 设计原则

1. **配置驱动**：核心参数可配置
2. **分层管理**：默认配置 + 用户配置
3. **类型安全**：配置验证和类型检查
4. **易于使用**：YAML格式，清晰的注释
5. **向后兼容**：配置升级机制

---

## 2. 配置文件结构

### 2.1 配置文件列表

```
config/
├── quality_filter_rules.yaml       # 质量筛选规则
├── quality_scoring_weights.yaml    # 质量评分权重
├── data_sources.yaml               # 数据源配置
├── backtest_params.yaml            # 回测参数
├── shenwan_industries.yaml         # 申万行业分类
└── user_config.yaml                # 用户自定义配置（可选）
```

### 2.2 配置优先级

```
命令行参数 > 用户配置 > 默认配置
```

---

## 3. 配置文件详细设计

### 3.1 quality_filter_rules.yaml

**功能**：定义质量筛选的各项规则和阈值

```yaml
# 质量筛选规则配置
version: "1.0"

# 基础资格筛选
basic_qualification:
  # 盈利能力
  profitability:
    roe_3y_avg_min: 0.12          # ROE 3年平均最低值
    roic_3y_avg_min: 0.10         # ROIC 3年平均最低值
    allow_single_year_fluctuation: true  # 允许单年波动

  # 财务安全
  financial_safety:
    debt_ratio_max: 0.70          # 最大负债率
    operating_cashflow_min: 0     # 经营性现金流最小值
    current_ratio_min: 1.0        # 最小流动比率
    quick_ratio_min: 0.8          # 最小速动比率

  # 龙头地位
  leader_position:
    revenue_vs_leader_min: 0.30   # 营收占行业第1名最小比例

# 行业集中度标准
industry_concentration:
  high:
    cr3_threshold: 0.50           # CR3 >= 50%
    top_n: 3                      # 前3名
  medium:
    cr3_threshold: 0.30           # 30% <= CR3 < 50%
    top_n: 2                      # 前2名
  low:
    top_n: 1                      # 仅第1名

# 排除项规则
exclusion:
  # ST股票
  st_stocks:
    enabled: true

  # 营收排名下降
  revenue_rank_decline:
    enabled: true
    consecutive_years: 2          # 连续下降年数

  # 估值陷阱
  valuation_trap:
    enabled: true
    roe_slope_threshold: -0.02    # ROE斜率阈值
    cyclical_roe_min: 0.08        # 周期股ROE最小值

  # 治理风险
  governance_risk:
    enabled: true
    pledge_ratio_max: 0.50        # 最大质押比例
    related_transaction_ratio_max: 0.30  # 最大关联交易比例
    check_fraud_history: true     # 检查造假历史
    fraud_lookback_years: 5       # 造假历史回溯年数

  # 商誉地雷
  goodwill_risk:
    enabled: true
    goodwill_ratio_max: 0.30      # 商誉/净资产最大比例

  # 业绩下滑
  profit_decline:
    enabled: true
    decline_threshold: -0.20      # 下滑阈值
    consecutive_years: 2          # 连续下滑年数

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

# 行业分散度控制
diversification:
  enabled: true
  max_industry_ratio: 0.35        # 单一行业最大占比
  min_pool_size_for_diversification: 30  # 启用分散度控制的最小池规模
  small_industry_threshold: 2     # 小行业阈值（不受限制）

# 数据质量要求
data_quality:
  min_data_years: 3               # 最少数据年数
  allow_missing_quarters: 1       # 允许缺失季度数
  outlier_handling: "flag"        # 异常值处理: flag | remove | cap
```

### 3.2 quality_scoring_weights.yaml

**功能**：定义质量评分的权重和阈值

```yaml
# 质量评分权重配置
version: "1.0"

# 总分设置
total_score:
  max: 100
  pass_threshold: 60              # 入池最低分

# 财务质量评分（50分）
financial_quality:
  max_score: 50

  # ROE稳定性（15分）
  roe_stability:
    weight: 15
    thresholds:
      - value: 0.20
        score: 15
        label: "优秀"
      - value: 0.15
        score: 10
        label: "良好"
      - value: 0.12
        score: 6
        label: "及格"

  # ROIC水平（15分）
  roic_level:
    weight: 15
    thresholds:
      - value: 0.15
        score: 15
        label: "优秀"
      - value: 0.12
        score: 10
        label: "良好"
      - value: 0.10
        score: 6
        label: "及格"

  # 现金流质量（12分）
  cashflow_quality:
    weight: 12
    thresholds:
      - value: 1.2
        score: 12
        label: "优秀"
      - value: 0.8
        score: 8
        label: "良好"
      - value: 0.5
        score: 4
        label: "及格"

  # 负债率（8分）
  leverage:
    weight: 8
    thresholds:
      - value: 0.30
        score: 8
        label: "优秀"
      - value: 0.50
        score: 5
        label: "良好"
      - value: 0.70
        score: 2
        label: "及格"
    reverse: true                 # 值越小得分越高

# 竞争优势评分（50分）
competitive_advantage:
  max_score: 50

  # 龙头地位（15分）
  leader_position:
    weight: 15
    rules:
      absolute_leader:            # 绝对龙头
        rank: 1
        revenue_ratio: 1.50       # 营收≥第2名150%
        score: 15
      leading_leader:             # 领先龙头
        rank: 1
        revenue_ratio: 1.00       # 营收≥第2名100%
        score: 12
      leader:                     # 龙头
        rank: 1
        score: 10
      strong_second:              # 强势第二
        rank: 2
        revenue_ratio: 0.50       # 营收≥第1名50%
        score: 8
      top_tier:                   # 前列
        rank: [2, 3]
        score: 5

  # 龙头地位趋势（10分）
  leader_trend:
    weight: 10
    lookback_years: 3
    thresholds:
      - change: 2                 # 上升2名以上
        score: 10
        label: "快速崛起"
      - change: 1                 # 上升1名
        score: 8
        label: "稳步上升"
      - change: 0                 # 不变
        score: 6
        label: "稳定"
      - change: -1                # 下降1名
        score: 3
        label: "轻微下滑"
      - change: -2                # 下降2名以上
        score: 0
        label: "竞争力减弱"

  # 盈利能力优势（15分）
  profit_margin:
    weight: 15
    metric: "gross_margin"        # gross_margin | roe
    thresholds:
      - relative_advantage: 0.30  # 超出30%
        score: 15
        label: "显著优势"
      - relative_advantage: 0.20  # 超出20-30%
        score: 12
        label: "明显优势"
      - relative_advantage: 0.10  # 超出10-20%
        score: 9
        label: "一定优势"
      - relative_advantage: 0.00  # 超出0-10%
        score: 5
        label: "略有优势"

  # 成长性（10分）
  growth:
    weight: 10
    metric: "revenue_cagr"        # 营收CAGR
    lookback_years: 3
    thresholds:
      - value: 0.20               # ≥20%
        score: 10
        label: "高成长"
      - value: 0.15               # 15-20%
        score: 8
        label: "较高成长"
      - value: 0.10               # 10-15%
        score: 6
        label: "中等成长"
      - value: 0.05               # 5-10%
        score: 3
        label: "低成长"
      - value: 0.00               # <5%
        score: 1
        label: "停滞"

# 评分调整
adjustments:
  # 行业调整
  industry_adjustment:
    enabled: false
    adjustments: {}

  # 市值调整
  market_cap_adjustment:
    enabled: false
    small_cap_penalty: 0          # 小市值惩罚
    large_cap_bonus: 0            # 大市值奖励
```

### 3.3 data_sources.yaml

**功能**：配置数据源和数据获取参数

```yaml
# 数据源配置
version: "1.0"

# iFinD API配置
ifind:
  # 连接配置
  connection:
    host: "api.wind.com.cn"
    port: 443
    timeout: 30
    use_ssl: true

  # 认证配置（从环境变量读取）
  auth:
    username_env: "IFIND_USERNAME"
    password_env: "IFIND_PASSWORD"

  # 限流配置
  rate_limit:
    max_requests_per_minute: 60
    max_concurrent_requests: 3
    burst_size: 10

  # 重试配置
  retry:
    max_attempts: 3
    backoff_multiplier: 1
    min_wait_seconds: 1
    max_wait_seconds: 10
    retry_on_errors:
      - "timeout"
      - "connection_error"
      - "rate_limit"

  # 批量获取配置
  batch:
    stock_batch_size: 100
    batch_interval_seconds: 1
    max_batch_retries: 2

  # 缓存配置
  cache:
    enabled: true
    ttl_seconds: 3600             # 缓存有效期1小时
    max_size_mb: 500              # 最大缓存500MB

# 数据更新配置
update:
  # 增量更新
  incremental:
    enabled: true
    lookback_days: 7              # 回溯天数

  # 定时更新
  schedule:
    enabled: false                # 默认关闭，手动触发
    stock_list:
      cron: "0 9 * * *"           # 每日9:00
    market_data:
      cron: "0 16 * * *"          # 每日16:00
    financial_data:
      cron: "0 0 1 * *"           # 每月1日

  # 数据保留
  retention:
    raw_data_days: 365            # 原始数据保留1年
    calculated_data_days: 1825    # 计算数据保留5年
    error_log_days: 90            # 错误日志保留90天

# 数据验证配置
validation:
  # 完整性检查
  completeness:
    required_fields:
      stock_basic:
        - stock_code
        - stock_name
        - list_date
      financial:
        - stock_code
        - report_date
        - revenue
        - net_profit
      market:
        - stock_code
        - trade_date
        - close_price

  # 值范围检查
  value_ranges:
    roe: [-1.0, 1.0]
    roic: [-1.0, 1.0]
    debt_ratio: [0.0, 2.0]
    gross_margin: [-0.5, 1.0]
    revenue: [0, null]
    stock_price: [0, null]
    market_cap: [0, null]

  # 异常值处理
  outlier_handling:
    method: "flag"                # flag | remove | cap
    threshold: 3                  # 标准差倍数
    apply_to:
      - roe
      - roic
      - gross_margin

# 数据库配置
database:
  # SQLite配置
  sqlite:
    path: "data/database/stocks.db"
    echo: false                   # SQL日志
    pool_size: 5
    max_overflow: 10

  # 备份配置
  backup:
    enabled: true
    frequency: "daily"            # daily | weekly | monthly
    keep_backups: 7               # 保留备份数
    backup_path: "data/database/backups/"
```

### 3.4 backtest_params.yaml

**功能**：配置回测参数

```yaml
# 回测参数配置
version: "1.0"

# 基本参数
basic:
  # 时间范围
  default_start_date: "2019-01-01"
  default_end_date: "2024-12-31"

  # 再平衡频率
  rebalance_freq: "Q"             # Q=季度, M=月度, Y=年度

  # 资金设置
  initial_capital: 1000000        # 100万

# 交易成本
transaction_cost:
  # 买入成本
  buy:
    commission: 0.0003            # 佣金0.03%
    stamp_duty: 0.0000            # 印花税0%
    transfer_fee: 0.00002         # 过户费0.002%
    total: 0.00032                # 总计0.032%

  # 卖出成本
  sell:
    commission: 0.0003            # 佣金0.03%
    stamp_duty: 0.0010            # 印花税0.1%
    transfer_fee: 0.00002         # 过户费0.002%
    total: 0.00132                # 总计0.132%

  # 滑点
  slippage: 0.0010                # 0.1%

# 持仓策略
position:
  # 权重方式
  weighting: "equal"              # equal=等权, market_cap=市值加权

  # 持仓限制
  min_stocks: 10                  # 最少持仓数
  max_stocks: 100                 # 最多持仓数
  min_weight: 0.01                # 单股最小权重1%
  max_weight: 0.10                # 单股最大权重10%

  # 行业限制
  max_industry_weight: 0.35       # 单一行业最大权重35%

  # 再平衡阈值
  rebalance_threshold: 0.05       # 权重偏离5%时再平衡

# 基准设置
benchmark:
  # 默认基准
  default: "000300.SH"            # 沪深300

  # 备选基准
  alternatives:
    - code: "000905.SH"
      name: "中证500"
    - code: "000852.SH"
      name: "中证1000"
    - code: "000001.SH"
      name: "上证指数"

# 风险参数
risk:
  # 无风险利率
  risk_free_rate: 0.03            # 3%

  # 风险限制
  max_drawdown_limit: 0.50        # 最大回撤限制50%
  max_volatility_limit: 0.40      # 最大波动率限制40%

  # 止损设置
  stop_loss:
    enabled: false
    threshold: -0.20              # 单股止损-20%

# 报告设置
report:
  # 输出格式
  format: "markdown"              # markdown | html | pdf

  # 报告内容
  include_sections:
    - summary
    - returns
    - risks
    - risk_adjusted
    - win_rate
    - benchmark_comparison
    - holdings_analysis
    - annual_performance

  # 图表设置
  charts:
    enabled: true
    style: "seaborn"              # seaborn | ggplot | default
    dpi: 300
    formats:
      - png
      - svg

  # 输出路径
  output_path: "data/reports/"
```

---

## 4. 配置加载与验证

### 4.1 配置加载器

```python
class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.configs = {}

    def load_all(self) -> Dict[str, Any]:
        """加载所有配置"""
        config_files = [
            "quality_filter_rules.yaml",
            "quality_scoring_weights.yaml",
            "data_sources.yaml",
            "backtest_params.yaml"
        ]

        for file in config_files:
            name = file.replace(".yaml", "")
            self.configs[name] = self.load_config(file)

        # 加载用户配置（如果存在）
        user_config_path = self.config_dir / "user_config.yaml"
        if user_config_path.exists():
            user_config = self.load_config("user_config.yaml")
            self.merge_user_config(user_config)

        return self.configs

    def load_config(self, filename: str) -> Dict[str, Any]:
        """加载单个配置文件"""
        path = self.config_dir / filename

        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 验证配置
        self.validate_config(config, filename)

        return config

    def merge_user_config(self, user_config: Dict[str, Any]) -> None:
        """合并用户配置"""
        for key, value in user_config.items():
            if key in self.configs:
                self.configs[key] = self._deep_merge(
                    self.configs[key], value
                )
```

### 4.2 配置验证器

```python
class ConfigValidator:
    """配置验证器"""

    def validate(self, config: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
        """验证配置"""
        issues = []

        # 检查必填字段
        for field in schema.get("required", []):
            if field not in config:
                issues.append(f"Missing required field: {field}")

        # 检查字段类型
        for field, field_schema in schema.get("properties", {}).items():
            if field in config:
                value = config[field]
                expected_type = field_schema.get("type")

                if not self._check_type(value, expected_type):
                    issues.append(
                        f"Field {field}: expected {expected_type}, "
                        f"got {type(value).__name__}"
                    )

        # 检查值范围
        for field, field_schema in schema.get("properties", {}).items():
            if field in config:
                value = config[field]

                if "minimum" in field_schema and value < field_schema["minimum"]:
                    issues.append(
                        f"Field {field}: value {value} below minimum "
                        f"{field_schema['minimum']}"
                    )

                if "maximum" in field_schema and value > field_schema["maximum"]:
                    issues.append(
                        f"Field {field}: value {value} above maximum "
                        f"{field_schema['maximum']}"
                    )

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues
        )
```

---

## 5. 配置使用示例

### 5.1 在代码中使用配置

```python
# 加载配置
config_loader = ConfigLoader()
configs = config_loader.load_all()

# 使用配置
filter_config = configs["quality_filter_rules"]
roe_min = filter_config["basic_qualification"]["profitability"]["roe_3y_avg_min"]

# 创建筛选器
quality_filter = QualityFilter(filter_config)
```

### 5.2 通过CLI修改配置

```bash
# 查看配置
industry-screener config show quality_filter_rules

# 修改配置
industry-screener config set quality_filter_rules.basic_qualification.profitability.roe_3y_avg_min 0.15

# 重置配置
industry-screener config reset quality_filter_rules
```

---

## 6. 配置升级

### 6.1 版本管理

每个配置文件包含版本号：

```yaml
version: "1.0"
```

### 6.2 升级机制

```python
class ConfigUpgrader:
    """配置升级器"""

    def upgrade(self, config: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """升级配置"""
        if from_version == "1.0" and to_version == "1.1":
            config = self._upgrade_1_0_to_1_1(config)

        return config

    def _upgrade_1_0_to_1_1(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """从1.0升级到1.1"""
        # 添加新字段
        # 重命名字段
        # 删除废弃字段
        return config
```

---

## 7. 实现计划

### 7.1 Phase 1: 基础框架（Week 1）

- [ ] 创建配置文件模板
- [ ] 实现配置加载器
- [ ] 实现配置验证器

### 7.2 Phase 2: CLI集成（Week 2）

- [ ] 实现config命令组
- [ ] 实现配置查看
- [ ] 实现配置修改

### 7.3 Phase 3: 高级功能（Week 3）

- [ ] 实现用户配置
- [ ] 实现配置升级
- [ ] 文档完善

---

**相关文档**：
- [概述](./01_overview.md)
- [CLI工具](./06_cli_tools.md)
