# iFinD 数据指标全量确认清单

本文档列出了系统所需的所有数据字段。请核对状态为 **[待确认]** 的项目，并在 iFinD 终端中查找对应的真实代码填入。

## 一、宏观经济指标 (Macro Data)
**获取方式**: EDB 经济数据库 (通常代码以 `M` 开头)

| 指标名称 | 内部字段名 | 当前代码/占位符 | 状态 | 待确认真实代码 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PMI** | `PMI` | `"pmi"` | 🔴 **[待确认]** | `M_______` | 制造业采购经理指数 |
| **新订单指数** | `NEW_ORDER` | `"pmi_new_order"` | 🔴 **[待确认]** | `M_______` | 制造业PMI:新订单 |
| **M2同比** | `M2` | `"m2_yoy"` | 🔴 **[待确认]** | `M_______` | M2供应量同比增长率 |
| **社融同比** | `SOCIAL_FINANCING` | `"social_financing_yoy"` | 🔴 **[待确认]** | `M_______` | 社会融资规模存量同比 |
| **PPI同比** | `PPI` | `"ppi_yoy"` | 🔴 **[待确认]** | `M_______` | 工业生产者出厂价格指数(PPI)同比 |
| **CPI同比** | `CPI` | `"cpi_yoy"` | 🔴 **[待确认]** | `M_______` | 居民消费价格指数(CPI)同比 |

---

## 二、行业级指标 (Industry Data)
**获取方式**: 申万二级行业指数 (如 `801xxx.SI`) 对应的衍生指标

| 指标名称 | 内部字段名 | 当前代码/占位符 | 状态 | 待确认真实代码 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **行业PE-TTM** | `PE_TTM` | `"pe_ttm"` | 🔴 **[待确认]** | `ths________` | 申万行业指数整体市盈率(TTM) |
| **行业PB** | `PB` | `"pb"` | 🔴 **[待确认]** | `ths________` | 申万行业指数整体市净率 |
| **北向资金** | `NORTHBOUND_FLOW` | `"northbound_flow"` | 🔴 **[待确认]** | `ths________` | 陆股通行业资金净流入 |
| **主力资金** | `MAIN_FUND_FLOW` | `"main_fund_flow"` | 🔴 **[待确认]** | `ths________` | 行业主力资金净流入 |
| **行业收入增速** | `REVENUE_GROWTH` | `"revenue_yoy"` | 🟡 **[需确认]** | `ths________` | 若无直接指标，需聚合成分股计算 |
| **行业利润增速** | `PROFIT_GROWTH` | `"profit_yoy"` | 🟡 **[需确认]** | `ths________` | 若无直接指标，需聚合成分股计算 |

---

## 三、复杂计算指标 (Complex Derived Metrics)
**获取方式**: 需要确认是否有直接指标，否则需通过成分股聚合计算

| 指标名称 | 内部字段名 | 疑似方案 | 状态 | 确认结果 |
| :--- | :--- | :--- | :--- | :--- |
| **行业CR5** | `CR5` | 聚合计算 (营收前5占比) | 🟡 **[需确认]** | □ 确认需聚合 <br>□ 有直接指标: ______ |
| **龙头份额** | `LEADER_SHARE` | 聚合计算 (最大营收占比) | 🟡 **[需确认]** | □ 确认需聚合 <br>□ 有直接指标: ______ |
| **价格波动率** | `PRICE_VOLATILITY` | 计算 (行业指数收盘价标准差) | 🟡 **[需确认]** | □ 确认需计算 <br>□ 有直接指标: ______ |
| **产能利用率** | `CAPACITY_UTILIZATION` | 需寻找宏观/行业数据 | 🔴 **[待确认]** | □ 代码: ______ <br>□ 无法获取 |
| **行业平均ROE** | `ROE` | 聚合计算 (成分股中位数) | 🟡 **[需确认]** | □ 确认需聚合 <br>□ 有直接指标: ______ |
| **存货周转** | `INVENTORY_TURNOVER` | 聚合计算 (成分股中位数) | 🟡 **[需确认]** | □ 确认需聚合 <br>□ 有直接指标: ______ |

---

## 四、股票基础数据 (Stock Basic Data)
**获取方式**: 股票代码 (如 `600519.SH`) 对应的基础指标
**状态**: ✅ **[已确认]** (基于现有文档映射，请最终核对是否可用)

### 4.1 基础信息
| 指标名称 | 内部字段名 | iFinD字段名 | 说明 |
| :--- | :--- | :--- | :--- |
| **股票简称** | `stock_name` | `ths_stock_short_name_stock` | |
| **申万一级行业** | `industry_code_l1` | `ths_industry_shenwan_l1_stock` | |
| **申万二级行业** | `industry_code_l2` | `ths_industry_shenwan_l2_stock` | |
| **上市日期** | `list_date` | `ths_ipo_date_stock` | |
| **ST状态** | `is_st` | `ths_stock_status` | |

### 4.2 财务数据 (Financials)
| 指标名称 | 内部字段名 | iFinD字段名 | 说明 |
| :--- | :--- | :--- | :--- |
| **总资产** | `total_assets` | `ths_total_assets_stock` | |
| **总负债** | `total_liabilities` | `ths_total_liabilities_stock` | |
| **流动资产** | `current_assets` | `ths_current_assets_stock` | |
| **存货** | `inventory` | `ths_inventory_stock` | |
| **净资产** | `net_assets` | `ths_net_assets_stock` | |
| **商誉** | `goodwill` | `ths_goodwill_stock` | |
| **营业收入** | `operating_revenue` | `ths_operating_revenue_stock` | |
| **营业成本** | `operating_cost` | `ths_operating_cost_stock` | |
| **净利润** | `net_profit` | `ths_net_profit_stock` | |
| **净利润(TTM)** | `net_profit_ttm` | `ths_net_profit_ttm_stock` | |
| **经营现金流** | `cash_flow_oper_act` | `ths_cash_flow_oper_act_stock` | |
| **ROE** | `roe` | `ths_roe_stock` | |
| **ROIC** | `roic` | `ths_roic_stock` | 🔴 **[新增]** 核心质量指标 |
| **毛利率** | `gross_margin` | `ths_gross_profit_margin_stock` | |
| **净利增长率** | `net_profit_growth_rate` | `ths_net_profit_growth_rate_stock` | 同比增长 |
| **流动比率** | `current_ratio` | `ths_current_ratio_stock` | 🔴 **[新增]** 财务安全 |
| **速动比率** | `quick_ratio` | `ths_quick_ratio_stock` | 🔴 **[新增]** 财务安全 |
| **关联交易** | `related_transaction` | `ths_sq_related_trade_stock` | 🔴 **[新增]** 治理风险(需确认字段) |


### 4.3 行情与估值 (Market & Valuation)
| 指标名称 | 内部字段名 | iFinD字段名 | 说明 |
| :--- | :--- | :--- | :--- |
| **收盘价** | `close_price` | `ths_close_price_stock` | 前复权? |
| **总市值** | `market_value` | `ths_market_value_stock` | |
| **PE(TTM)** | `pe_ttm` | `ths_pe_ttm_stock` | |
| **PB** | `pb` | `ths_pb_stock` | |

### 4.4 股东数据 (Shareholders)
| 指标名称 | 内部字段名 | iFinD字段名 | 说明 |
| :--- | :--- | :--- | :--- |
| **机构持仓** | `institutional_ownership` | `ths_institutional_ownership_stock` | 需确认计算口径 |
| **质押比例** | `pledge_ratio` | `ths_pledge_ratio_stock` | 大股东质押比例 |

---

## 五、下一步行动
1.  **宏观/行业指标**: 请在 iFinD 终端搜索上述红色的 `[待确认]` 指标，将真实代码填入表格。
2.  **聚合逻辑**: 确认是否接受对 CR5、ROE 等使用“成分股聚合”的计算方式（即：如果没有直接的行业指标，我们就拉取所有成分股算平均）。
3.  **填好后**: 请将更新后的文档内容发回，我们将更新 `src/data/ifind_api.py` 中的映射表。
