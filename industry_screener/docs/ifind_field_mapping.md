# iFinD API 字段映射表

## 说明
本文档定义了质量筛选所需的所有数据字段及其在iFinD API中的对应字段名。

**注意**: 实际的iFinD字段名需要根据iFinD官方文档进行确认和调整。

---

## 一、基础信息字段

| 系统字段名 | iFinD字段名(待确认) | 数据类型 | 说明 |
|-----------|-------------------|---------|------|
| stock_code | - | string | 股票代码(如600519.SH) |
| stock_name | ths_stock_short_name_stock | string | 股票简称 |
| industry_code_l1 | ths_industry_shenwan_l1_stock | string | 申万一级行业代码 |
| industry_name_l1 | ths_industry_shenwan_l1_name_stock | string | 申万一级行业名称 |
| industry_code_l2 | ths_industry_shenwan_l2_stock | string | 申万二级行业代码 |
| industry_name_l2 | ths_industry_shenwan_l2_name_stock | string | 申万二级行业名称 |
| list_date | ths_ipo_date_stock | date | 上市日期 |
| is_st | ths_stock_status | string | ST状态(ST/\*ST/正常) |

---

## 二、财务报表字段

### 2.1 资产负债表

| 系统字段名 | iFinD字段名(待确认) | 数据类型 | 单位 | 说明 |
|-----------|-------------------|---------|------|------|
| total_assets | ths_total_assets_stock | float | 元 | 总资产 |
| total_liabilities | ths_total_liabilities_stock | float | 元 | 总负债 |
| current_assets | ths_current_assets_stock | float | 元 | 流动资产 |
| current_liabilities | ths_current_liabilities_stock | float | 元 | 流动负债 |
| inventory | ths_inventory_stock | float | 元 | 存货 |
| net_assets | ths_net_assets_stock | float | 元 | 净资产(股东权益) |
| goodwill | ths_goodwill_stock | float | 元 | 商誉 |

### 2.2 利润表

| 系统字段名 | iFinD字段名(待确认) | 数据类型 | 单位 | 说明 |
|-----------|-------------------|---------|------|------|
| operating_revenue | ths_operating_revenue_stock | float | 元 | 营业收入 |
| operating_cost | ths_operating_cost_stock | float | 元 | 营业成本 |
| net_profit | ths_net_profit_stock | float | 元 | 净利润 |
| net_profit_ttm | ths_net_profit_ttm_stock | float | 元 | 净利润(TTM) |

### 2.3 现金流量表

| 系统字段名 | iFinD字段名(待确认) | 数据类型 | 单位 | 说明 |
|-----------|-------------------|---------|------|------|
| cash_flow_oper_act | ths_cash_flow_oper_act_stock | float | 元 | 经营活动现金流 |

### 2.4 财务指标

| 系统字段名 | iFinD字段名(待确认) | 数据类型 | 单位 | 说明 |
|-----------|-------------------|---------|------|------|
| roe | ths_roe_stock | float | % | 净资产收益率(ROE) |
| gross_margin | ths_gross_profit_margin_stock | float | % | 毛利率 |
| net_profit_growth_rate | ths_net_profit_growth_rate_stock | float | % | 净利润增长率(同比) |

---

## 三、行情数据字段

| 系统字段名 | iFinD字段名(待确认) | 数据类型 | 单位 | 说明 |
|-----------|-------------------|---------|------|------|
| close_price | ths_close_price_stock | float | 元 | 收盘价 |
| market_value | ths_market_value_stock | float | 元 | 总市值 |
| pe_ttm | ths_pe_ttm_stock | float | 倍 | 市盈率(TTM) |
| pb | ths_pb_stock | float | 倍 | 市净率 |

---

## 四、股东数据字段

| 系统字段名 | iFinD字段名(待确认) | 数据类型 | 单位 | 说明 |
|-----------|-------------------|---------|------|------|
| institutional_ownership | ths_institutional_ownership_stock | float | % | 机构持仓比例 |
| pledge_ratio | ths_pledge_ratio_stock | float | % | 大股东质押比例 |

---

## 五、需要计算的字段

以下字段无法直接从iFinD获取,需要基于上述字段计算:

### 5.1 财务安全指标

```python
# 负债率
debt_ratio = total_liabilities / total_assets

# 流动比率
current_ratio = current_assets / current_liabilities

# 速动资产
quick_assets = current_assets - inventory

# 速动比率
quick_ratio = quick_assets / current_liabilities
```

### 5.2 财务质量指标

```python
# 经营性现金流/净利润
ocf_ni_ratio = cash_flow_oper_act / net_profit_ttm

# ROE 3年平均
roe_3y_avg = mean(roe_2021, roe_2022, roe_2023)

# ROE标准差(3年)
roe_3y_std = std(roe_2021, roe_2022, roe_2023)

# ROE最低值(3年)
roe_3y_min = min(roe_2021, roe_2022, roe_2023)

# ROE斜率(3年)
roe_3y_slope = linear_regression_slope([roe_2021, roe_2022, roe_2023])
```

### 5.3 竞争优势指标

```python
# 市占率
market_share = operating_revenue / industry_total_revenue

# 市占率变化(3年)
market_share_change = (market_share_2023 - market_share_2020) / market_share_2020

# 毛利率相对优势
gross_margin_advantage = gross_margin - industry_median_gross_margin
```

### 5.4 错杀潜力指标

```python
# 日收益率
daily_return = (close_price_today - close_price_yesterday) / close_price_yesterday

# 年化波动率
annual_volatility = std(daily_returns_3y) * sqrt(252)
```

### 5.5 排除项指标

```python
# 商誉占比
goodwill_ratio = goodwill / net_assets

# 净利润连续下滑判断
is_profit_declining = (
    net_profit_growth_rate_2022 < -20 and
    net_profit_growth_rate_2023 < -20
)
```

---

## 六、行业聚合字段

以下字段需要对行业内所有成分股进行聚合计算:

```python
# 行业总营收
industry_total_revenue = sum(operating_revenue for stock in industry_stocks)

# 行业中位数毛利率
industry_median_gross_margin = median(gross_margin for stock in industry_stocks)
```

**实现方式**:
1. 获取申万二级行业成分股列表
2. 获取所有成分股的营收/毛利率数据
3. 进行聚合计算

---

## 七、数据获取频率

| 数据类型 | 更新频率 | 获取时机 |
|---------|---------|---------|
| 财务报表数据 | 季度 | 财报发布后(4月/8月/10月/次年4月) |
| 行情数据 | 日 | 每日收盘后 |
| 股东数据 | 季度 | 季报发布后 |
| 基础信息 | 不定期 | 发生变更时 |

---

## 八、数据质量要求

### 8.1 必需字段(缺失则剔除)

- stock_code
- stock_name
- industry_code_l2
- roe (近3年)
- operating_revenue (近3年)
- total_assets
- total_liabilities
- net_profit

### 8.2 可选字段(缺失则使用默认值)

- institutional_ownership (默认: 0)
- pledge_ratio (默认: 0)
- goodwill (默认: 0)

### 8.3 数据验证规则

```python
# ROE范围: -100% ~ 100%
assert -100 <= roe <= 100

# 毛利率范围: 0% ~ 100%
assert 0 <= gross_margin <= 100

# 负债率范围: 0% ~ 200%
assert 0 <= debt_ratio <= 200

# 市占率范围: 0% ~ 100%
assert 0 <= market_share <= 100
```

---

## 九、iFinD API调用示例

```python
from iFinDPy import THS_DateQuery, THS_DP

# 1. 获取单个股票的财务数据
stock_code = "600519.SH"
indicators = "ths_roe_stock;ths_operating_revenue_stock;ths_total_assets_stock"
params = "100;100;100"  # 报告期参数

result = THS_DP(
    thscode=stock_code,
    jsonIndicator=indicators,
    jsonparam=params,
    begintime="2020-12-31",
    endtime="2023-12-31"
)

# 2. 获取行业成分股
industry_code = "801120.SI"  # 食品饮料
result = THS_DateQuery(
    thscode=industry_code,
    jsonIndicator="ths_member_stock",
    jsonparam="",
    begintime="2023-12-31",
    endtime="2023-12-31"
)

# 3. 获取日行情数据
result = THS_DP(
    thscode=stock_code,
    jsonIndicator="ths_close_price_stock",
    jsonparam="",
    begintime="2021-01-01",
    endtime="2023-12-31"
)
```

---

## 十、待确认事项

以下事项需要查阅iFinD官方文档确认:

1. ✅ 申万二级行业字段名
2. ✅ 机构持仓比例字段名和计算口径
3. ✅ 大股东质押比例字段名
4. ✅ 关联交易数据是否可获取
5. ✅ 行业成分股获取方式
6. ✅ 历史数据回溯年限
7. ✅ API调用频率限制
8. ✅ 数据更新时间点

---

## 十一、替代方案

如果某些字段在iFinD中无法获取,可以考虑以下替代方案:

| 字段 | iFinD | Wind | Choice | Tushare | 备注 |
|-----|-------|------|--------|---------|------|
| 机构持仓比例 | ✅ | ✅ | ✅ | ✅ | 多数据源都有 |
| 大股东质押 | ✅ | ✅ | ✅ | ✅ | 多数据源都有 |
| 关联交易 | ❓ | ❓ | ❓ | ❌ | 可能需要人工提取 |
| 财务造假历史 | ❌ | ❌ | ❌ | ❌ | 需要人工维护 |

---

## 更新日志

- 2024-01-XX: 初始版本,定义所有字段映射
- 待更新: 根据iFinD官方文档确认实际字段名
