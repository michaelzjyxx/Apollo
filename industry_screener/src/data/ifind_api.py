"""
iFinD API 客户端
封装同花顺 iFinD 数据接口

注意: 此模块需要安装 iFinD SDK (iFinDPy)
实际的 API 调用需要根据 iFinD 官方文档进行适配
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from loguru import logger

from ..utils import IndicatorType, get_config_value


class IFindAPIError(Exception):
    """iFinD API 异常"""

    pass


class IFindAPIClient:
    """iFinD API 客户端"""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 iFinD API 客户端

        Args:
            username: iFinD 用户名
            password: iFinD 密码
            config: 配置字典
        """
        if config is None:
            config = self._load_config_from_file()

        self.config = config
        self.username = username or config.get("username")
        self.password = password or config.get("password")

        # API 配置
        self.max_retries = config.get("max_retries", 3)
        self.retry_interval = config.get("retry_interval", 5)
        self.rate_limit = config.get("rate_limit", 1)  # 每秒最多请求次数
        self.timeout = config.get("timeout", 30)

        # 连接状态
        self._is_connected = False
        self._last_request_time = 0

        # iFinD 客户端实例 (需要安装 iFinDPy)
        self._client = None

    @staticmethod
    def _load_config_from_file() -> Dict[str, Any]:
        """从配置文件加载 API 配置"""
        return {
            "username": get_config_value("ifind_api.username", default=""),
            "password": get_config_value("ifind_api.password", default=""),
            "max_retries": get_config_value("ifind_api.max_retries", default=3),
            "retry_interval": get_config_value("ifind_api.retry_interval", default=5),
            "rate_limit": get_config_value("ifind_api.rate_limit", default=1),
            "timeout": get_config_value("ifind_api.timeout", default=30),
        }

    def connect(self) -> bool:
        """
        连接到 iFinD API

        Returns:
            连接是否成功
        """
        try:
            # TODO: 实际实现需要导入 iFinDPy 并调用登录接口
            # from iFinDPy import THS_iFinDLogin
            # result = THS_iFinDLogin(self.username, self.password)
            # if result != 0:
            #     raise IFindAPIError(f"iFinD 登录失败,错误代码: {result}")

            logger.info("iFinD API 连接成功")
            self._is_connected = True
            return True

        except Exception as e:
            logger.error(f"iFinD API 连接失败: {e}")
            self._is_connected = False
            return False

    def disconnect(self):
        """断开 iFinD API 连接"""
        try:
            # TODO: 实际实现需要调用登出接口
            # from iFinDPy import THS_iFinDLogout
            # THS_iFinDLogout()

            logger.info("iFinD API 连接已断开")
            self._is_connected = False

        except Exception as e:
            logger.error(f"iFinD API 断开连接失败: {e}")

    def _check_connection(self):
        """检查连接状态"""
        if not self._is_connected:
            raise IFindAPIError("iFinD API 未连接,请先调用 connect()")

    def _rate_limit_check(self):
        """速率限制检查"""
        if self.rate_limit > 0:
            current_time = time.time()
            time_since_last_request = current_time - self._last_request_time
            min_interval = 1.0 / self.rate_limit

            if time_since_last_request < min_interval:
                sleep_time = min_interval - time_since_last_request
                logger.debug(f"速率限制: 等待 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)

            self._last_request_time = time.time()

    def _retry_request(self, func, *args, **kwargs):
        """
        重试机制

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                self._rate_limit_check()
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"API 请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_interval)

        raise IFindAPIError(
            f"API 请求失败,已重试 {self.max_retries} 次: {last_exception}"
        )

    def get_industry_data(
        self,
        industry_code: str,
        indicator: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """
        获取行业数据

        Args:
            industry_code: 行业代码
            indicator: 指标名称
            start_date: 起始日期
            end_date: 结束日期
            frequency: 数据频率 (daily/weekly/monthly/quarterly/yearly)

        Returns:
            包含数据的 DataFrame,列: [date, value]
        """
        self._check_connection()

        def _fetch():
            # TODO: 实际实现需要调用 iFinD API
            # 示例:
            # from iFinDPy import THS_DS
            # result = THS_DS(
            #     industry_code,
            #     indicator,
            #     start_date.strftime('%Y-%m-%d'),
            #     end_date.strftime('%Y-%m-%d'),
            #     frequency
            # )
            # return result.data

            # 暂时返回空 DataFrame 作为占位符
            logger.warning(
                f"iFinD API 实际实现待完成 - "
                f"industry_code={industry_code}, "
                f"indicator={indicator}"
            )
            return pd.DataFrame(columns=["date", "value"])

        return self._retry_request(_fetch)

    def get_industry_constituent_stocks(
        self,
        industry_code: str,
        date: Optional[datetime] = None,
    ) -> List[str]:
        """
        获取行业成分股

        Args:
            industry_code: 行业代码
            date: 日期,为 None 则使用最新

        Returns:
            股票代码列表
        """
        self._check_connection()

        def _fetch():
            # TODO: 实际实现
            logger.warning(f"iFinD API 实际实现待完成 - industry_code={industry_code}")
            return []

        return self._retry_request(_fetch)

    def get_stock_data(
        self,
        stock_codes: Union[str, List[str]],
        indicator: str,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """
        获取个股数据

        Args:
            stock_codes: 股票代码或代码列表
            indicator: 指标名称
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            包含数据的 DataFrame
        """
        self._check_connection()

        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]

        def _fetch():
            # TODO: 实际实现
            logger.warning(
                f"iFinD API 实际实现待完成 - "
                f"stock_codes={stock_codes}, "
                f"indicator={indicator}"
            )
            return pd.DataFrame()

        return self._retry_request(_fetch)

    def get_macro_data(
        self,
        indicator: str,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """
        获取宏观经济数据

        Args:
            indicator: 指标名称 (pmi/cpi/ppi/m2等)
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            包含数据的 DataFrame
        """
        self._check_connection()

        def _fetch():
            # TODO: 实际实现
            logger.warning(f"iFinD API 实际实现待完成 - indicator={indicator}")
            return pd.DataFrame(columns=["date", "value"])

        return self._retry_request(_fetch)

    def batch_fetch_industry_indicators(
        self,
        industry_codes: List[str],
        indicators: List[str],
        start_date: datetime,
        end_date: datetime,
        frequency: str = "quarterly",
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        批量获取多个行业的多个指标

        Args:
            industry_codes: 行业代码列表
            indicators: 指标列表
            start_date: 起始日期
            end_date: 结束日期
            frequency: 数据频率

        Returns:
            嵌套字典: {industry_code: {indicator: DataFrame}}
        """
        self._check_connection()

        results = {}

        for industry_code in industry_codes:
            results[industry_code] = {}

            for indicator in indicators:
                try:
                    df = self.get_industry_data(
                        industry_code=industry_code,
                        indicator=indicator,
                        start_date=start_date,
                        end_date=end_date,
                        frequency=frequency,
                    )
                    results[industry_code][indicator] = df
                    logger.debug(
                        f"获取数据成功: {industry_code} - {indicator}, "
                        f"{len(df)} 条记录"
                    )

                except Exception as e:
                    logger.error(
                        f"获取数据失败: {industry_code} - {indicator}, 错误: {e}"
                    )
                    results[industry_code][indicator] = pd.DataFrame()

        return results

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


# 指标名称映射 (系统内部名称 -> iFinD API 字段名)
# 需要根据实际的 iFinD API 文档进行配置
INDICATOR_MAPPING = {
    # 竞争格局指标
    IndicatorType.CR5: "industry_cr5",  # 待确认
    IndicatorType.LEADER_SHARE: "industry_leader_share",  # 待确认
    IndicatorType.PRICE_VOLATILITY: "price_std",  # 待确认
    IndicatorType.CAPACITY_UTILIZATION: "capacity_utilization",  # 待确认
    # 盈利能力指标
    IndicatorType.ROE: "roe_avg",  # 待确认
    IndicatorType.GROSS_MARGIN: "gross_profit_margin",  # 待确认
    # 成长性指标
    IndicatorType.REVENUE_GROWTH: "revenue_yoy",  # 待确认
    IndicatorType.PROFIT_GROWTH: "profit_yoy",  # 待确认
    # 现金流指标
    IndicatorType.OCF_NI_RATIO: "ocf_to_ni",  # 待确认
    IndicatorType.CAPEX_INTENSITY: "capex_to_depreciation",  # 待确认
    # 估值指标
    IndicatorType.PE_TTM: "pe_ttm",
    IndicatorType.PB: "pb",
    # 景气度指标
    IndicatorType.PMI: "pmi",
    IndicatorType.NEW_ORDER: "pmi_new_order",
    IndicatorType.M2: "m2_yoy",
    IndicatorType.SOCIAL_FINANCING: "social_financing_yoy",
    IndicatorType.PPI: "ppi_yoy",
    IndicatorType.CPI: "cpi_yoy",
    # 周期位置指标
    IndicatorType.INVENTORY_YOY: "inventory_yoy",
    IndicatorType.INVENTORY_TURNOVER: "inventory_turnover_days",
    # 资金流向
    IndicatorType.NORTHBOUND_FLOW: "northbound_flow",
    IndicatorType.MAIN_FUND_FLOW: "main_fund_flow",
}


def get_ifind_indicator_name(indicator_type: IndicatorType) -> str:
    """
    获取 iFinD API 的指标名称

    Args:
        indicator_type: 系统内部指标类型

    Returns:
        iFinD API 字段名
    """
    if indicator_type in INDICATOR_MAPPING:
        return INDICATOR_MAPPING[indicator_type]
    else:
        logger.warning(f"指标 {indicator_type} 未在映射表中,使用原始名称")
        return indicator_type.value
