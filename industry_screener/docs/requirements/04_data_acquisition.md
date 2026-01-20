# 数据获取模块 - 详细需求文档

## 文档信息

**文档类型**：模块需求文档
**版本**：v1.0
**创建日期**：2026-01-19
**状态**：待评审

---

## 1. 模块概述

### 1.1 目标

数据获取模块负责从iFinD API获取股票筛选所需的各类数据，并存储到本地数据库中，确保数据的完整性、准确性和时效性。

### 1.2 核心功能

1. **数据获取**：从iFinD API批量获取数据
2. **数据验证**：检查数据完整性和有效性
3. **数据存储**：存储到SQLite数据库
4. **数据更新**：定期更新和增量更新
5. **错误处理**：重试机制和错误记录

### 1.3 数据范围

**股票基础数据**：
- 股票列表（代码、名称、上市日期）
- 行业分类（申万一级、二级、三级）
- 交易状态（ST标记、停牌状态）

**财务数据**：
- 利润表（营业收入、营业成本、净利润等）
- 资产负债表（总资产、总负债、股东权益等）
- 现金流量表（经营性现金流等）
- 财务指标（ROE、ROIC、毛利率等）

**行情数据**：
- 日行情（开盘价、收盘价、成交量等）
- 市值数据（总市值、流通市值）

**治理数据**：
- 股东信息（大股东持股、质押比例）
- 关联交易数据
- 监管处罚记录

**行业数据**：
- 行业成分股
- 行业指标（行业总营收、行业集中度等）

---

## 2. 功能需求

### 2.1 数据获取

#### 2.1.1 iFinD API 客户端

**需求描述**：
封装iFinD API调用，提供统一的数据获取接口

**核心功能**：
- API连接管理
- 请求限流控制
- 自动重试机制
- 错误处理和日志记录

**接口设计**：

```python
class IFindClient:
    """iFinD API客户端"""

    def __init__(self, config: IFindConfig):
        self.config = config
        self.rate_limiter = RateLimiter(
            max_requests=config.max_requests_per_minute
        )

    def get_stock_list(
        self,
        market: str = "A股"
    ) -> pd.DataFrame:
        """获取股票列表"""

    def get_financial_data(
        self,
        stock_codes: List[str],
        indicators: List[str],
        start_date: str,
        end_date: str,
        report_type: str = "年报"
    ) -> pd.DataFrame:
        """获取财务数据"""

    def get_market_data(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取行情数据"""

    def get_industry_classification(
        self,
        stock_codes: List[str],
        classification: str = "申万"
    ) -> pd.DataFrame:
        """获取行业分类"""

    def get_industry_constituents(
        self,
        industry_code: str,
        date: str
    ) -> List[str]:
        """获取行业成分股"""
```

#### 2.1.2 批量获取策略

**需求描述**：
为避免API限流，需要实现批量获取和限速策略

**实现策略**：

1. **分批获取**
   - 每批最多100只股票
   - 批次间间隔1秒

2. **限流控制**
   - 每分钟最多60次请求
   - 使用令牌桶算法

3. **并发控制**
   - 最多3个并发请求
   - 避免过载

**示例代码**：

```python
class BatchFetcher:
    """批量数据获取器"""

    def __init__(self, client: IFindClient, batch_size: int = 100):
        self.client = client
        self.batch_size = batch_size

    def fetch_in_batches(
        self,
        stock_codes: List[str],
        fetch_func: Callable,
        **kwargs
    ) -> pd.DataFrame:
        """分批获取数据"""
        results = []

        for i in range(0, len(stock_codes), self.batch_size):
            batch = stock_codes[i:i + self.batch_size]

            try:
                data = fetch_func(batch, **kwargs)
                results.append(data)

                # 批次间延迟
                if i + self.batch_size < len(stock_codes):
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Batch {i} failed: {e}")
                # 记录失败的批次，稍后重试

        return pd.concat(results, ignore_index=True)
```

#### 2.1.3 增量更新策略

**需求描述**：
支持增量更新，避免每次全量获取

**更新策略**：

| 数据类型 | 更新频率 | 增量策略 |
|---------|---------|---------|
| 股票列表 | 每日 | 获取新上市股票 |
| 财务数据 | 季度 | 仅更新最新季报 |
| 行情数据 | 每日 | 仅获取最新交易日 |
| 行业分类 | 每月 | 检测变更后更新 |
| 治理数据 | 每周 | 获取最新公告 |

**实现逻辑**：

```python
def incremental_update(data_type: str) -> None:
    """增量更新数据"""

    # 获取上次更新时间
    last_update = get_last_update_time(data_type)

    # 根据数据类型确定更新策略
    if data_type == "financial":
        # 财务数据：获取最新季报
        latest_report_date = get_latest_report_date()
        if latest_report_date > last_update:
            fetch_financial_data(since=last_update)

    elif data_type == "market":
        # 行情数据：获取最新交易日
        latest_trade_date = get_latest_trade_date()
        if latest_trade_date > last_update:
            fetch_market_data(since=last_update)

    # 更新时间戳
    update_last_update_time(data_type, datetime.now())
```

---

### 2.2 数据验证

#### 2.2.1 完整性检查

**需求描述**：
检查获取的数据是否完整

**检查项**：

1. **必填字段检查**
   - 股票代码不能为空
   - 关键财务指标不能全部为空

2. **数据量检查**
   - 股票列表数量应在合理范围（3000-5000只）
   - 每只股票应有完整的历史数据

3. **时间连续性检查**
   - 财务数据应按季度连续
   - 行情数据应按交易日连续

**实现示例**：

```python
class DataValidator:
    """数据验证器"""

    def validate_completeness(
        self,
        data: pd.DataFrame,
        required_columns: List[str]
    ) -> ValidationResult:
        """完整性检查"""

        issues = []

        # 检查必填字段
        for col in required_columns:
            if col not in data.columns:
                issues.append(f"Missing column: {col}")
            elif data[col].isna().all():
                issues.append(f"Column {col} is all null")

        # 检查数据量
        if len(data) == 0:
            issues.append("Empty dataset")

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues
        )
```

#### 2.2.2 有效性检查

**需求描述**：
检查数据值是否在合理范围内

**检查规则**：

| 字段 | 有效性规则 |
|------|-----------|
| ROE | -100% ~ 100% |
| 负债率 | 0% ~ 200% |
| 毛利率 | -50% ~ 100% |
| 营业收入 | > 0 |
| 股价 | > 0 |
| 市值 | > 0 |

**实现示例**：

```python
def validate_value_range(
    data: pd.DataFrame,
    column: str,
    min_value: float,
    max_value: float
) -> pd.DataFrame:
    """值范围检查"""

    invalid_mask = (data[column] < min_value) | (data[column] > max_value)
    invalid_count = invalid_mask.sum()

    if invalid_count > 0:
        logger.warning(
            f"{column}: {invalid_count} values out of range "
            f"[{min_value}, {max_value}]"
        )

        # 标记异常值
        data.loc[invalid_mask, f"{column}_valid"] = False

    return data
```

#### 2.2.3 一致性检查

**需求描述**：
检查数据之间的逻辑一致性

**检查规则**：

1. **财务数据一致性**
   - 总资产 = 总负债 + 股东权益
   - 毛利 = 营业收入 - 营业成本
   - ROE = 净利润 / 股东权益

2. **时间一致性**
   - 财报日期应早于公告日期
   - 数据日期应在合理范围内

3. **跨表一致性**
   - 股票代码在各表中应一致
   - 同一股票的行业分类应一致

---

### 2.3 数据存储

#### 2.3.1 存储策略

**需求描述**：
将验证后的数据存储到SQLite数据库

**存储原则**：

1. **原始数据保留**
   - 保存API返回的原始数据
   - 便于追溯和重新计算

2. **计算指标分离**
   - 计算指标单独存储
   - 避免重复计算

3. **历史版本管理**
   - 保留数据更新历史
   - 支持时间点查询

**表结构设计**：

参见 [数据库设计文档](./02_database_design.md)

#### 2.3.2 事务管理

**需求描述**：
确保数据写入的原子性

**实现策略**：

```python
def save_data_with_transaction(
    data: pd.DataFrame,
    table_name: str,
    db_session: Session
) -> None:
    """事务性数据保存"""

    try:
        # 开始事务
        db_session.begin()

        # 批量插入
        data.to_sql(
            table_name,
            con=db_session.connection(),
            if_exists='append',
            index=False
        )

        # 提交事务
        db_session.commit()

        logger.info(f"Saved {len(data)} records to {table_name}")

    except Exception as e:
        # 回滚事务
        db_session.rollback()
        logger.error(f"Failed to save data: {e}")
        raise
```

---

### 2.4 数据更新

#### 2.4.1 定时更新

**需求描述**：
支持定时自动更新数据

**更新计划**：

| 数据类型 | 更新时间 | 更新内容 |
|---------|---------|---------|
| 股票列表 | 每日 9:00 | 新上市股票 |
| 行情数据 | 每日 16:00 | 当日行情 |
| 财务数据 | 季报发布后 | 最新季报 |
| 行业分类 | 每月1日 | 行业调整 |

**实现方式**：

```python
# 使用APScheduler实现定时任务
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# 每日更新股票列表
scheduler.add_job(
    update_stock_list,
    trigger='cron',
    hour=9,
    minute=0
)

# 每日更新行情数据
scheduler.add_job(
    update_market_data,
    trigger='cron',
    hour=16,
    minute=0
)

scheduler.start()
```

#### 2.4.2 手动更新

**需求描述**：
支持通过CLI命令手动触发更新

**命令接口**：

```bash
# 更新所有数据
python -m industry_screener data update --all

# 更新特定类型数据
python -m industry_screener data update --type financial

# 更新特定日期范围
python -m industry_screener data update --start 2023-01-01 --end 2023-12-31

# 强制全量更新
python -m industry_screener data update --force
```

---

### 2.5 错误处理

#### 2.5.1 重试机制

**需求描述**：
API调用失败时自动重试

**重试策略**：

- 最多重试3次
- 指数退避：1秒、2秒、4秒
- 记录重试日志

**实现示例**：

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
def fetch_with_retry(fetch_func: Callable, *args, **kwargs):
    """带重试的数据获取"""
    try:
        return fetch_func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Fetch failed, will retry: {e}")
        raise
```

#### 2.5.2 错误记录

**需求描述**：
记录所有数据获取错误，便于排查

**记录内容**：

- 错误时间
- 错误类型
- 错误详情
- 请求参数
- 堆栈信息

**存储方式**：

```python
@dataclass
class DataFetchError:
    """数据获取错误记录"""
    timestamp: datetime
    data_type: str
    error_type: str
    error_message: str
    request_params: Dict[str, Any]
    stack_trace: str

# 存储到数据库
class ErrorLog(Base):
    __tablename__ = 'data_fetch_errors'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    data_type = Column(String(50), nullable=False)
    error_type = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=False)
    request_params = Column(JSON)
    stack_trace = Column(Text)
```

---

## 3. 技术规格

### 3.1 核心类设计

#### 3.1.1 DataFetcher 类

```python
class DataFetcher:
    """数据获取器"""

    def __init__(
        self,
        client: IFindClient,
        validator: DataValidator,
        repository: DataRepository
    ):
        self.client = client
        self.validator = validator
        self.repository = repository

    def fetch_and_save(
        self,
        data_type: str,
        **kwargs
    ) -> FetchResult:
        """获取并保存数据"""

        # 1. 获取数据
        data = self._fetch_data(data_type, **kwargs)

        # 2. 验证数据
        validation = self.validator.validate(data, data_type)
        if not validation.is_valid:
            logger.error(f"Validation failed: {validation.issues}")
            raise ValidationError(validation.issues)

        # 3. 保存数据
        self.repository.save(data, data_type)

        return FetchResult(
            data_type=data_type,
            record_count=len(data),
            validation=validation
        )
```

#### 3.1.2 DataUpdater 类

```python
class DataUpdater:
    """数据更新器"""

    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher

    def update_all(self, force: bool = False) -> UpdateResult:
        """更新所有数据"""
        results = []

        for data_type in DATA_TYPES:
            try:
                result = self.update_data_type(data_type, force)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to update {data_type}: {e}")

        return UpdateResult(results)

    def update_data_type(
        self,
        data_type: str,
        force: bool = False
    ) -> FetchResult:
        """更新特定类型数据"""

        # 检查是否需要更新
        if not force and not self._need_update(data_type):
            logger.info(f"{data_type} is up to date")
            return None

        # 执行更新
        return self.fetcher.fetch_and_save(data_type)
```

### 3.2 配置文件

#### 3.2.1 data_sources.yaml

```yaml
# iFinD API配置
ifind:
  # API连接
  host: "api.wind.com.cn"
  port: 443
  timeout: 30

  # 限流配置
  rate_limit:
    max_requests_per_minute: 60
    max_concurrent_requests: 3

  # 重试配置
  retry:
    max_attempts: 3
    backoff_multiplier: 1
    min_wait_seconds: 1
    max_wait_seconds: 10

  # 批量获取配置
  batch:
    stock_batch_size: 100
    batch_interval_seconds: 1

# 数据更新配置
update:
  # 增量更新
  incremental:
    enabled: true
    lookback_days: 7  # 回溯天数

  # 定时更新
  schedule:
    stock_list:
      enabled: true
      cron: "0 9 * * *"  # 每日9:00

    market_data:
      enabled: true
      cron: "0 16 * * *"  # 每日16:00

    financial_data:
      enabled: false  # 手动触发

  # 数据保留
  retention:
    raw_data_days: 365  # 原始数据保留1年
    error_log_days: 90  # 错误日志保留90天

# 数据验证配置
validation:
  # 值范围
  value_ranges:
    roe: [-1.0, 1.0]
    debt_ratio: [0.0, 2.0]
    gross_margin: [-0.5, 1.0]
    revenue: [0, null]
    stock_price: [0, null]

  # 完整性要求
  required_fields:
    stock_basic: [stock_code, stock_name, list_date]
    financial: [stock_code, report_date, revenue, net_profit]
    market: [stock_code, trade_date, close_price]

  # 异常值处理
  outlier_handling:
    method: "flag"  # flag | remove | cap
    threshold: 3  # 标准差倍数
```

---

## 4. 接口设计

### 4.1 数据获取接口

```python
# 获取股票列表
def fetch_stock_list(market: str = "A股") -> pd.DataFrame:
    """获取股票列表"""

# 获取财务数据
def fetch_financial_data(
    stock_codes: List[str],
    start_date: str,
    end_date: str,
    indicators: Optional[List[str]] = None
) -> pd.DataFrame:
    """获取财务数据"""

# 获取行情数据
def fetch_market_data(
    stock_codes: List[str],
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """获取行情数据"""

# 获取行业分类
def fetch_industry_classification(
    stock_codes: List[str],
    classification: str = "申万"
) -> pd.DataFrame:
    """获取行业分类"""
```

### 4.2 数据更新接口

```python
# 更新所有数据
def update_all_data(force: bool = False) -> UpdateResult:
    """更新所有数据"""

# 更新特定类型数据
def update_data_type(
    data_type: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force: bool = False
) -> FetchResult:
    """更新特定类型数据"""

# 检查数据时效性
def check_data_freshness() -> Dict[str, datetime]:
    """检查各类数据的最后更新时间"""
```

### 4.3 数据查询接口

```python
# 查询股票基础信息
def get_stock_info(stock_code: str) -> StockInfo:
    """查询股票基础信息"""

# 查询财务数据
def get_financial_data(
    stock_code: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """查询财务数据"""

# 查询行情数据
def get_market_data(
    stock_code: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """查询行情数据"""
```

---

## 5. 实现计划

### 5.1 Phase 1: API客户端（Week 1）

- [ ] 实现IFindClient基础类
- [ ] 实现限流和重试机制
- [ ] 单元测试

### 5.2 Phase 2: 数据获取（Week 2）

- [ ] 实现各类数据获取方法
- [ ] 实现批量获取策略
- [ ] 集成测试

### 5.3 Phase 3: 数据验证（Week 3）

- [ ] 实现数据验证器
- [ ] 实现各类验证规则
- [ ] 单元测试

### 5.4 Phase 4: 数据存储（Week 4）

- [ ] 实现数据存储逻辑
- [ ] 实现事务管理
- [ ] 集成测试

### 5.5 Phase 5: 数据更新（Week 5）

- [ ] 实现增量更新
- [ ] 实现定时任务
- [ ] 实现CLI命令
- [ ] 端到端测试

---

## 6. 测试需求

### 6.1 单元测试

**测试覆盖率目标**：> 80%

**关键测试用例**：

1. **API客户端测试**
   - Mock API响应
   - 测试限流机制
   - 测试重试逻辑

2. **数据验证测试**
   - 完整性检查
   - 有效性检查
   - 一致性检查

3. **批量获取测试**
   - 分批逻辑
   - 并发控制
   - 错误处理

### 6.2 集成测试

**测试场景**：

1. **完整数据获取流程**
   - 从API获取数据
   - 验证数据
   - 存储到数据库

2. **增量更新测试**
   - 检测需要更新的数据
   - 仅获取增量部分
   - 验证更新结果

3. **错误恢复测试**
   - API调用失败
   - 数据验证失败
   - 存储失败

### 6.3 性能测试

**性能指标**：

| 场景 | 数据量 | 目标时间 |
|------|--------|---------|
| 获取股票列表 | 5000只 | < 30秒 |
| 获取财务数据 | 100只×3年 | < 2分钟 |
| 获取行情数据 | 100只×1年 | < 1分钟 |
| 全量更新 | 全部数据 | < 30分钟 |

---

## 7. 风险与依赖

### 7.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| API限流 | 高 | 中 | 限速、缓存、分批 |
| API不稳定 | 高 | 中 | 重试、降级方案 |
| 数据质量问题 | 高 | 中 | 验证、人工复核 |
| 网络超时 | 中 | 低 | 超时设置、重试 |

### 7.2 外部依赖

- **iFinD API**：核心数据源
- **网络连接**：稳定的网络环境
- **API权限**：有效的API账号

---

**相关文档**：
- [概述](./01_overview.md)
- [数据库设计](./02_database_design.md)
- [质量筛选模块](./03_quality_screening.md)
