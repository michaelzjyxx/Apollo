# 测试计划 - 详细需求文档

## 文档信息

**文档类型**：测试计划文档
**版本**：v1.0
**创建日期**：2026-01-19
**状态**：待评审

---

## 1. 测试概述

### 1.1 测试目标

1. **功能正确性**：验证所有功能按需求正常工作
2. **数据准确性**：确保计算结果准确可靠
3. **性能达标**：满足性能指标要求
4. **稳定可靠**：系统稳定运行，错误处理完善

### 1.2 测试范围

**包含**：
- 单元测试：所有核心模块
- 集成测试：模块间交互
- 端到端测试：完整业务流程
- 性能测试：关键操作性能
- 数据验证测试：计算准确性

**不包含**：
- 压力测试（单用户系统）
- 安全测试（本地系统）
- 兼容性测试（固定环境）

### 1.3 测试策略

```
测试金字塔：
    /\
   /E2E\        端到端测试 (10%)
  /------\
 /集成测试\     集成测试 (30%)
/----------\
/  单元测试  \   单元测试 (60%)
```

---

## 2. 单元测试

### 2.1 测试覆盖率目标

| 模块 | 目标覆盖率 | 优先级 |
|------|-----------|--------|
| 质量筛选 | > 85% | 高 |
| 质量评分 | > 85% | 高 |
| 数据获取 | > 80% | 高 |
| 数据验证 | > 85% | 高 |
| 回测引擎 | > 80% | 中 |
| CLI工具 | > 70% | 中 |
| 配置管理 | > 75% | 低 |

### 2.2 质量筛选模块测试

#### 2.2.1 ROE/ROIC计算测试

```python
class TestROECalculation:
    """ROE计算测试"""

    def test_roe_calculation_normal(self):
        """测试正常情况下的ROE计算"""
        net_profit = 100_000_000
        equity = 500_000_000
        expected_roe = 0.20

        roe = calculate_roe(net_profit, equity)

        assert roe == pytest.approx(expected_roe, rel=1e-6)

    def test_roe_calculation_zero_equity(self):
        """测试股东权益为0的情况"""
        net_profit = 100_000_000
        equity = 0

        with pytest.raises(ValueError, match="Equity cannot be zero"):
            calculate_roe(net_profit, equity)

    def test_roe_calculation_negative_profit(self):
        """测试净利润为负的情况"""
        net_profit = -50_000_000
        equity = 500_000_000
        expected_roe = -0.10

        roe = calculate_roe(net_profit, equity)

        assert roe == pytest.approx(expected_roe, rel=1e-6)

    def test_roe_3y_average(self):
        """测试3年平均ROE计算"""
        roe_values = [0.15, 0.18, 0.22]
        expected_avg = 0.1833

        avg_roe = calculate_roe_3y_avg(roe_values)

        assert avg_roe == pytest.approx(expected_avg, rel=1e-4)
```

#### 2.2.2 行业集中度测试

```python
class TestIndustryConcentration:
    """行业集中度测试"""

    def test_cr3_calculation_high_concentration(self):
        """测试高集中度行业"""
        revenues = [1000, 800, 600, 200, 100]  # 前3名占比70%
        expected_cr3 = 0.889  # (1000+800+600)/2700

        cr3 = calculate_cr3(revenues)

        assert cr3 == pytest.approx(expected_cr3, rel=1e-3)

    def test_leader_standard_high_concentration(self):
        """测试高集中度行业的龙头标准"""
        cr3 = 0.60
        expected_top_n = 3

        top_n = get_leader_standard(cr3)

        assert top_n == expected_top_n

    def test_leader_standard_medium_concentration(self):
        """测试中集中度行业的龙头标准"""
        cr3 = 0.40
        expected_top_n = 2

        top_n = get_leader_standard(cr3)

        assert top_n == expected_top_n
```

#### 2.2.3 排除项测试

```python
class TestExclusionFilters:
    """排除项测试"""

    def test_st_stock_exclusion(self):
        """测试ST股票排除"""
        stock = Stock(code="600000.SH", name="*ST浦发")

        result = is_st_stock(stock)

        assert result is True

    def test_revenue_rank_decline(self):
        """测试营收排名下降"""
        ranks = [5, 4, 2]  # 连续2年上升

        result = is_revenue_rank_declining(ranks, consecutive_years=2)

        assert result is False

    def test_valuation_trap_non_cyclical(self):
        """测试非周期股估值陷阱"""
        roe_values = [0.20, 0.15, 0.10]  # ROE持续下降
        pe = 8
        industry = "医药生物"

        result = is_valuation_trap(roe_values, pe, industry)

        assert result is True

    def test_valuation_trap_cyclical(self):
        """测试周期股估值陷阱"""
        roe_values = [0.15, 0.08, 0.12]  # ROE波动但最低≥8%
        pe = 8
        industry = "化工"

        result = is_valuation_trap(roe_values, pe, industry)

        assert result is False
```

### 2.3 质量评分模块测试

```python
class TestQualityScoring:
    """质量评分测试"""

    def test_roe_stability_score(self):
        """测试ROE稳定性得分"""
        roe_3y_avg = 0.25
        expected_score = 15

        score = calculate_roe_stability_score(roe_3y_avg)

        assert score == expected_score

    def test_leader_position_score_absolute_leader(self):
        """测试绝对龙头得分"""
        rank = 1
        revenue = 1000
        second_revenue = 500  # 营收是第2名的2倍
        expected_score = 15

        score = calculate_leader_position_score(rank, revenue, second_revenue)

        assert score == expected_score

    def test_total_score_calculation(self):
        """测试总分计算"""
        financial_score = 45.5
        competitive_score = 38.2
        expected_total = 83.7

        total = calculate_total_score(financial_score, competitive_score)

        assert total == pytest.approx(expected_total, rel=1e-6)
```

### 2.4 数据获取模块测试

```python
class TestDataFetcher:
    """数据获取测试"""

    @pytest.fixture
    def mock_ifind_client(self, mocker):
        """Mock iFinD客户端"""
        return mocker.Mock(spec=IFindClient)

    def test_fetch_stock_list(self, mock_ifind_client):
        """测试获取股票列表"""
        mock_data = pd.DataFrame({
            'stock_code': ['600000.SH', '000001.SZ'],
            'stock_name': ['浦发银行', '平安银行']
        })
        mock_ifind_client.get_stock_list.return_value = mock_data

        fetcher = DataFetcher(mock_ifind_client)
        result = fetcher.fetch_stock_list()

        assert len(result) == 2
        assert result['stock_code'].tolist() == ['600000.SH', '000001.SZ']

    def test_batch_fetch(self, mock_ifind_client):
        """测试批量获取"""
        stock_codes = [f"60000{i}.SH" for i in range(250)]
        batch_size = 100

        fetcher = DataFetcher(mock_ifind_client, batch_size=batch_size)
        fetcher.fetch_in_batches(stock_codes, mock_ifind_client.get_financial_data)

        # 应该调用3次（250/100 = 3批）
        assert mock_ifind_client.get_financial_data.call_count == 3

    def test_retry_on_failure(self, mock_ifind_client):
        """测试失败重试"""
        mock_ifind_client.get_stock_list.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            pd.DataFrame({'stock_code': ['600000.SH']})
        ]

        fetcher = DataFetcher(mock_ifind_client)
        result = fetcher.fetch_with_retry(mock_ifind_client.get_stock_list)

        # 应该重试2次后成功
        assert mock_ifind_client.get_stock_list.call_count == 3
        assert len(result) == 1
```

### 2.5 数据验证模块测试

```python
class TestDataValidator:
    """数据验证测试"""

    def test_completeness_check_pass(self):
        """测试完整性检查通过"""
        data = pd.DataFrame({
            'stock_code': ['600000.SH'],
            'stock_name': ['浦发银行'],
            'revenue': [100_000_000]
        })
        required_fields = ['stock_code', 'stock_name', 'revenue']

        validator = DataValidator()
        result = validator.validate_completeness(data, required_fields)

        assert result.is_valid is True

    def test_completeness_check_fail_missing_column(self):
        """测试完整性检查失败（缺少列）"""
        data = pd.DataFrame({
            'stock_code': ['600000.SH'],
            'stock_name': ['浦发银行']
        })
        required_fields = ['stock_code', 'stock_name', 'revenue']

        validator = DataValidator()
        result = validator.validate_completeness(data, required_fields)

        assert result.is_valid is False
        assert 'Missing column: revenue' in result.issues

    def test_value_range_check(self):
        """测试值范围检查"""
        data = pd.DataFrame({
            'roe': [0.15, 1.50, -0.05]  # 第2个值超出范围
        })

        validator = DataValidator()
        result = validator.validate_value_range(data, 'roe', -1.0, 1.0)

        assert result.loc[1, 'roe_valid'] is False
```

### 2.6 回测引擎模块测试

```python
class TestBacktester:
    """回测引擎测试"""

    def test_equal_weight_portfolio(self):
        """测试等权组合构建"""
        stocks = ['600000.SH', '000001.SZ', '600036.SH']
        capital = 1_000_000

        portfolio = build_equal_weight_portfolio(stocks, capital)

        assert len(portfolio.stocks) == 3
        for stock in stocks:
            assert portfolio.weights[stock] == pytest.approx(1/3, rel=1e-6)

    def test_period_return_calculation(self):
        """测试区间收益计算"""
        portfolio = Portfolio(
            stocks=['600000.SH', '000001.SZ'],
            weights={'600000.SH': 0.5, '000001.SZ': 0.5}
        )
        start_prices = {'600000.SH': 10.0, '000001.SZ': 20.0}
        end_prices = {'600000.SH': 11.0, '000001.SZ': 22.0}

        # 600000: +10%, 000001: +10%, 组合: +10%
        expected_return = 0.10

        period_return = calculate_period_return(
            portfolio, start_prices, end_prices
        )

        assert period_return == pytest.approx(expected_return, rel=1e-6)

    def test_max_drawdown_calculation(self):
        """测试最大回撤计算"""
        nav_curve = [1.0, 1.2, 1.1, 1.3, 0.9, 1.0]
        expected_max_drawdown = 0.3077  # (1.3 - 0.9) / 1.3

        max_drawdown = calculate_max_drawdown(nav_curve)

        assert max_drawdown == pytest.approx(expected_max_drawdown, rel=1e-4)
```

---

## 3. 集成测试

### 3.1 数据获取与存储集成测试

```python
class TestDataFetchAndStore:
    """数据获取与存储集成测试"""

    def test_fetch_and_save_stock_list(self, db_session):
        """测试获取并保存股票列表"""
        fetcher = DataFetcher(ifind_client)
        repository = StockRepository(db_session)

        # 获取数据
        data = fetcher.fetch_stock_list()

        # 保存数据
        repository.save_stock_list(data)

        # 验证数据已保存
        saved_data = repository.get_stock_list()
        assert len(saved_data) == len(data)

    def test_incremental_update(self, db_session):
        """测试增量更新"""
        updater = DataUpdater(fetcher, repository)

        # 首次更新
        result1 = updater.update_data_type('financial')
        count1 = result1.record_count

        # 增量更新
        result2 = updater.update_data_type('financial')
        count2 = result2.record_count

        # 增量更新应该少于首次更新
        assert count2 < count1
```

### 3.2 筛选与评分集成测试

```python
class TestFilterAndScore:
    """筛选与评分集成测试"""

    def test_complete_screening_process(self, db_session):
        """测试完整筛选流程"""
        quality_filter = QualityFilter(config, db_session)

        # 执行筛选
        result = quality_filter.filter(
            industries=['食品饮料', '医药生物'],
            date='2024-01-01'
        )

        # 验证结果
        assert result.final_pool_size > 0
        assert result.final_pool_size <= result.after_scoring

        # 验证所有股票都有评分
        for stock in result.pool:
            assert stock.total_score >= 60
            assert 0 <= stock.financial_score <= 50
            assert 0 <= stock.competitive_score <= 50
```

### 3.3 回测完整流程集成测试

```python
class TestBacktestIntegration:
    """回测完整流程集成测试"""

    def test_complete_backtest(self, db_session):
        """测试完整回测流程"""
        backtester = Backtester(quality_filter, config)

        # 运行回测
        result = backtester.run(
            start_date='2019-01-01',
            end_date='2024-12-31'
        )

        # 验证结果
        assert result.performance.total_return is not None
        assert result.performance.annualized_return is not None
        assert result.performance.max_drawdown is not None
        assert result.comparison is not None
        assert result.report is not None
```

---

## 4. 端到端测试

### 4.1 CLI命令测试

```python
class TestCLICommands:
    """CLI命令测试"""

    def test_data_update_command(self, cli_runner):
        """测试数据更新命令"""
        result = cli_runner.invoke(cli, ['data', 'update', '--type', 'stock'])

        assert result.exit_code == 0
        assert '更新完成' in result.output

    def test_screen_run_command(self, cli_runner):
        """测试筛选命令"""
        result = cli_runner.invoke(cli, ['screen', 'run'])

        assert result.exit_code == 0
        assert '优质公司池' in result.output

    def test_pool_list_command(self, cli_runner):
        """测试公司池列表命令"""
        result = cli_runner.invoke(cli, ['pool', 'list'])

        assert result.exit_code == 0
        assert '股票代码' in result.output

    def test_backtest_run_command(self, cli_runner):
        """测试回测命令"""
        result = cli_runner.invoke(cli, ['backtest', 'run'])

        assert result.exit_code == 0
        assert '回测结果' in result.output
```

### 4.2 完整业务流程测试

```python
class TestEndToEndWorkflow:
    """端到端业务流程测试"""

    def test_complete_workflow(self, cli_runner, db_session):
        """测试完整业务流程"""
        # 1. 更新数据
        result = cli_runner.invoke(cli, ['data', 'update', '--type', 'all'])
        assert result.exit_code == 0

        # 2. 执行筛选
        result = cli_runner.invoke(cli, ['screen', 'run'])
        assert result.exit_code == 0

        # 3. 查看公司池
        result = cli_runner.invoke(cli, ['pool', 'list'])
        assert result.exit_code == 0

        # 4. 运行回测
        result = cli_runner.invoke(cli, ['backtest', 'run'])
        assert result.exit_code == 0

        # 5. 查看报告
        result = cli_runner.invoke(cli, ['backtest', 'report'])
        assert result.exit_code == 0
```

---

## 5. 性能测试

### 5.1 性能指标

| 操作 | 数据量 | 目标时间 | 测试方法 |
|------|--------|---------|---------|
| 质量筛选 | 5000只股票 | < 5分钟 | 计时测试 |
| 单股评分 | 1只股票 | < 1秒 | 计时测试 |
| 公司池查询 | 100只股票 | < 1秒 | 计时测试 |
| 回测 | 5年数据 | < 10分钟 | 计时测试 |
| 数据更新 | 全量数据 | < 30分钟 | 计时测试 |

### 5.2 性能测试用例

```python
class TestPerformance:
    """性能测试"""

    def test_quality_screening_performance(self, benchmark):
        """测试质量筛选性能"""
        quality_filter = QualityFilter(config, db_session)

        result = benchmark(
            quality_filter.filter,
            industries=all_industries,
            date='2024-01-01'
        )

        # 应该在5分钟内完成
        assert benchmark.stats['mean'] < 300

    def test_single_stock_scoring_performance(self, benchmark):
        """测试单股评分性能"""
        scorer = QualityScorer(config)

        result = benchmark(
            scorer.score,
            stock_code='600519.SH',
            date='2024-01-01'
        )

        # 应该在1秒内完成
        assert benchmark.stats['mean'] < 1.0

    def test_backtest_performance(self, benchmark):
        """测试回测性能"""
        backtester = Backtester(quality_filter, config)

        result = benchmark(
            backtester.run,
            start_date='2019-01-01',
            end_date='2024-12-31'
        )

        # 应该在10分钟内完成
        assert benchmark.stats['mean'] < 600
```

---

## 6. 数据验证测试

### 6.1 计算准确性验证

```python
class TestCalculationAccuracy:
    """计算准确性验证"""

    def test_roe_calculation_accuracy(self):
        """测试ROE计算准确性"""
        # 使用已知数据验证
        test_cases = [
            {
                'net_profit': 100_000_000,
                'equity': 500_000_000,
                'expected_roe': 0.20
            },
            {
                'net_profit': 50_000_000,
                'equity': 250_000_000,
                'expected_roe': 0.20
            }
        ]

        for case in test_cases:
            roe = calculate_roe(case['net_profit'], case['equity'])
            assert roe == pytest.approx(case['expected_roe'], rel=1e-6)

    def test_backtest_return_accuracy(self):
        """测试回测收益计算准确性"""
        # 使用简单场景手工验证
        portfolio = Portfolio(
            stocks=['600000.SH'],
            weights={'600000.SH': 1.0}
        )
        start_price = 10.0
        end_price = 11.0
        expected_return = 0.10

        period_return = calculate_period_return(
            portfolio,
            {'600000.SH': start_price},
            {'600000.SH': end_price}
        )

        assert period_return == pytest.approx(expected_return, rel=1e-6)
```

### 6.2 历史数据对比验证

```python
class TestHistoricalDataValidation:
    """历史数据对比验证"""

    def test_compare_with_known_results(self):
        """与已知结果对比"""
        # 使用2023年的筛选结果作为基准
        known_result = load_known_result('2023-12-31')

        # 重新运行筛选
        quality_filter = QualityFilter(config, db_session)
        new_result = quality_filter.filter(date='2023-12-31')

        # 对比结果
        assert len(new_result.pool) == len(known_result.pool)

        # 对比前10只股票
        for i in range(10):
            assert new_result.pool[i].stock_code == known_result.pool[i].stock_code
            assert new_result.pool[i].total_score == pytest.approx(
                known_result.pool[i].total_score, rel=1e-2
            )
```

---

## 7. 测试环境

### 7.1 测试数据准备

```python
@pytest.fixture(scope="session")
def test_database():
    """测试数据库"""
    # 创建测试数据库
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # 加载测试数据
    load_test_data(engine)

    yield engine

    # 清理
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(test_database):
    """数据库会话"""
    Session = sessionmaker(bind=test_database)
    session = Session()

    yield session

    session.rollback()
    session.close()
```

### 7.2 Mock数据

```python
@pytest.fixture
def mock_stock_data():
    """Mock股票数据"""
    return pd.DataFrame({
        'stock_code': ['600519.SH', '000858.SZ'],
        'stock_name': ['贵州茅台', '五粮液'],
        'industry': ['白酒', '白酒'],
        'roe': [0.32, 0.28],
        'roic': [0.28, 0.24]
    })

@pytest.fixture
def mock_ifind_client(mocker):
    """Mock iFinD客户端"""
    client = mocker.Mock(spec=IFindClient)
    client.get_stock_list.return_value = mock_stock_data()
    return client
```

---

## 8. 测试执行

### 8.1 测试命令

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/unit/test_quality_filter.py

# 运行特定测试类
pytest tests/unit/test_quality_filter.py::TestROECalculation

# 运行特定测试用例
pytest tests/unit/test_quality_filter.py::TestROECalculation::test_roe_calculation_normal

# 查看覆盖率
pytest --cov=industry_screener --cov-report=html

# 运行性能测试
pytest tests/performance/ --benchmark-only
```

### 8.2 持续集成

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        pytest --cov=industry_screener --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## 9. 测试报告

### 9.1 测试报告内容

1. **测试概要**
   - 测试用例总数
   - 通过/失败数量
   - 测试覆盖率

2. **失败用例详情**
   - 失败原因
   - 堆栈信息
   - 重现步骤

3. **性能测试结果**
   - 各操作耗时
   - 性能对比
   - 瓶颈分析

4. **覆盖率报告**
   - 模块覆盖率
   - 未覆盖代码
   - 改进建议

---

## 10. 测试计划时间表

### 10.1 测试阶段

| 阶段 | 时间 | 内容 |
|------|------|------|
| Phase 1 | Week 1-2 | 单元测试开发 |
| Phase 2 | Week 3 | 集成测试开发 |
| Phase 3 | Week 4 | 端到端测试开发 |
| Phase 4 | Week 5 | 性能测试和优化 |
| Phase 5 | Week 6 | 数据验证和回归测试 |

### 10.2 测试里程碑

- [ ] 单元测试覆盖率达到80%
- [ ] 所有集成测试通过
- [ ] 端到端测试通过
- [ ] 性能指标达标
- [ ] 数据准确性验证通过

---

**相关文档**：
- [概述](./01_overview.md)
- [质量筛选模块](./03_quality_screening.md)
- [数据获取模块](./04_data_acquisition.md)
- [回测验证模块](./05_backtesting.md)
