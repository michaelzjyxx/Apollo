"""
系统常量定义
"""

from enum import Enum
from typing import Dict, List


# ========== 行业分类 ==========

# 申万一级行业代码和名称映射
SHENWAN_L1_INDUSTRIES: Dict[str, str] = {
    '801010.SI': '农林牧渔',
    '801020.SI': '采掘',
    '801030.SI': '化工',
    '801040.SI': '钢铁',
    '801050.SI': '有色金属',
    '801080.SI': '电子',
    '801110.SI': '家用电器',
    '801120.SI': '食品饮料',
    '801130.SI': '纺织服装',
    '801140.SI': '轻工制造',
    '801150.SI': '医药生物',
    '801160.SI': '公用事业',
    '801170.SI': '交通运输',
    '801180.SI': '房地产',
    '801200.SI': '商业贸易',
    '801210.SI': '休闲服务',
    '801230.SI': '综合',
    '801710.SI': '建筑材料',
    '801720.SI': '建筑装饰',
    '801730.SI': '电气设备',
    '801740.SI': '国防军工',
    '801750.SI': '计算机',
    '801760.SI': '传媒',
    '801770.SI': '通信',
    '801780.SI': '银行',
    '801790.SI': '非银金融',
    '801880.SI': '汽车',
    '801890.SI': '机械设备',
    '801950.SI': '煤炭',
    '801960.SI': '石油石化',
    '801970.SI': '环保',
}

# 周期性行业
CYCLICAL_INDUSTRIES: List[str] = [
    '采掘', '化工', '钢铁', '有色金属', '煤炭', '石油石化', '建筑材料'
]

# 消费行业
CONSUMER_INDUSTRIES: List[str] = [
    '食品饮料', '纺织服装', '轻工制造', '医药生物', '商业贸易', '休闲服务', '家用电器'
]


# ========== 数据指标 ==========

class IndicatorType(str, Enum):
    """指标类型枚举"""

    # 竞争格局指标
    CR5 = "cr5"  # 行业CR5集中度
    LEADER_SHARE = "leader_share"  # 龙头市占率
    LEADER_SHARE_CHANGE = "leader_share_change"  # 龙头市占率变化
    PRICE_VOLATILITY = "price_volatility"  # 价格波动率
    CAPACITY_UTILIZATION = "capacity_utilization"  # 产能利用率

    # 盈利能力指标
    ROE = "roe"  # 加权ROE
    ROE_LEVEL = "roe_level"  # ROE水平
    ROE_TREND = "roe_trend"  # ROE趋势
    GROSS_MARGIN = "gross_margin"  # 毛利率
    GROSS_MARGIN_LEVEL = "gross_margin_level"  # 毛利率水平
    GROSS_MARGIN_TREND = "gross_margin_trend"  # 毛利率趋势

    # 成长性指标
    REVENUE_GROWTH = "revenue_growth"  # 营收增速
    PROFIT_GROWTH = "profit_growth"  # 利润增速
    PROFIT_ELASTICITY = "profit_elasticity"  # 利润弹性

    # 现金流指标
    OCF_NI_RATIO = "ocf_ni_ratio"  # 经营现金流/净利润
    CAPEX_INTENSITY = "capex_intensity"  # 资本开支强度

    # 估值指标
    PE_TTM = "pe_ttm"  # 滚动市盈率
    PB = "pb"  # 市净率
    PE_PERCENTILE = "pe_percentile"  # PE历史分位
    PB_PERCENTILE = "pb_percentile"  # PB历史分位
    PEG = "peg"  # PEG指标

    # 景气度指标
    PMI = "pmi"  # PMI指数
    NEW_ORDER = "new_order"  # 新订单指数
    M2 = "m2"  # M2增速
    SOCIAL_FINANCING = "social_financing"  # 社融增速
    PPI = "ppi"  # PPI同比
    CPI = "cpi"  # CPI同比

    # 周期位置指标
    INVENTORY_YOY = "inventory_yoy"  # 库存同比
    INVENTORY_TURNOVER = "inventory_turnover"  # 存货周转天数

    # 资金流向指标
    NORTHBOUND_FLOW = "northbound_flow"  # 北向资金流向
    MAIN_FUND_FLOW = "main_fund_flow"  # 主力资金流向


class DataFrequency(str, Enum):
    """数据频率枚举"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


# ========== 评分系统 ==========

class ScoreDimension(str, Enum):
    """评分维度枚举"""

    COMPETITION = "competition"  # 竞争格局 (15分)
    PROFITABILITY = "profitability"  # 盈利能力 (15分)
    GROWTH = "growth"  # 成长性 (10分)
    CASHFLOW = "cashflow"  # 现金流 (10分)
    VALUATION = "valuation"  # 估值 (10分)
    SENTIMENT = "sentiment"  # 景气度 (5分)
    CYCLE = "cycle"  # 周期位置 (5分)
    QUALITATIVE = "qualitative"  # 定性评分 (20分)


class QualitativeFactor(str, Enum):
    """定性因素枚举"""

    POLICY = "policy"  # 政策环境 (5分)
    BUSINESS_MODEL = "business_model"  # 商业模式 (5分)
    BARRIER = "barrier"  # 进入壁垒 (5分)
    MOAT = "moat"  # 护城河 (5分)


class RedlineFactor(str, Enum):
    """红线因素枚举"""

    GROSS_MARGIN_DECLINE = "gross_margin_decline"  # 毛利率连续下滑
    REVENUE_DECLINE = "revenue_decline"  # 收入连续下滑
    VALUATION_EXTREME = "valuation_extreme"  # 估值极端高位
    FUND_OUTFLOW = "fund_outflow"  # 资金持续流出


# ========== 库存周期 ==========

class InventoryCyclePosition(str, Enum):
    """库存周期位置枚举"""

    PASSIVE_RESTOCKING = "passive_restocking"  # 被动补库存(景气上行)
    ACTIVE_RESTOCKING = "active_restocking"  # 主动补库存(景气高位)
    PASSIVE_DESTOCKING = "passive_destocking"  # 被动去库存(景气下行)
    ACTIVE_DESTOCKING = "active_destocking"  # 主动去库存(景气底部)
    TRANSITION = "transition"  # 过渡期


# ========== 趋势判断 ==========

class Trend(str, Enum):
    """趋势枚举"""

    RISING = "rising"  # 上升
    STABLE = "stable"  # 平稳
    FALLING = "falling"  # 下降
    IMPROVING = "improving"  # 改善
    DECLINING = "declining"  # 恶化


# ========== 回测配置 ==========

class RebalanceFrequency(str, Enum):
    """再平衡频率枚举"""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class WeightMethod(str, Enum):
    """权重方法枚举"""

    EQUAL = "equal"  # 等权
    MARKET_CAP = "market_cap"  # 市值加权
    SCORE = "score"  # 评分加权


# ========== 数据验证 ==========

# 数据有效范围
VALUE_RANGES: Dict[str, tuple] = {
    "roe": (-100, 100),
    "gross_margin": (0, 100),
    "revenue_growth": (-100, 1000),
    "profit_growth": (-100, 1000),
    "pe_ttm": (0, 1000),
    "pb": (0, 100),
    "pmi": (0, 100),
    "cpi": (-10, 20),
    "ppi": (-20, 30),
}

# 数据时效性要求(天数)
TIMELINESS_REQUIREMENTS: Dict[DataFrequency, int] = {
    DataFrequency.QUARTERLY: 120,
    DataFrequency.MONTHLY: 60,
    DataFrequency.WEEKLY: 14,
    DataFrequency.DAILY: 7,
}

# 数据完整性阈值
COMPLETENESS_THRESHOLD = 0.9  # 缺失值不超过10%


# ========== iFinD API配置 ==========

# API指标映射 (iFinD字段名 -> 系统内部指标名)
IFIND_INDICATOR_MAPPING: Dict[str, str] = {
    # 这里需要根据实际的iFinD API字段名进行映射
    # 示例:
    # "wsd_roe_avg": IndicatorType.ROE,
    # "wsd_grossmargin": IndicatorType.GROSS_MARGIN,
    # ...
}


# ========== 默认值 ==========

DEFAULT_LOOKBACK_YEARS = 5  # 默认回溯年数
DEFAULT_BENCHMARK = "000300.SH"  # 默认基准指数(沪深300)
DEFAULT_TOP_N = 10  # 默认选择TOP N个行业
DEFAULT_MIN_SCORE = 70  # 默认最低评分要求
DEFAULT_N_STOCKS = 3  # 默认每个行业选择的个股数量
