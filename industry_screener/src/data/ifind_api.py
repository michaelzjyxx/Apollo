"""
iFinD API 客户端
封装同花顺 iFinD 数据接口

注意: 此模块需要安装 iFinD SDK (iFinDPy)
实际的 API 调用需要根据 iFinD 官方文档进行适配
"""

import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd
import requests
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
        self.api_mode = config.get("mode", "sdk")  # sdk 或 http
        self.refresh_token = config.get("refresh_token")
        self._access_token = config.get("access_token")  # 动态获取或配置

        # API 配置
        self.max_retries = config.get("max_retries", 3)
        self.retry_interval = config.get("retry_interval", 5)
        self.rate_limit = config.get("rate_limit", 1)  # 每秒最多请求次数
        self.timeout = config.get("timeout", 30)
        self.http_base_url = config.get("http_base_url", "https://quantapi.51ifind.com/api/v1")

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
            "mode": get_config_value("ifind_api.mode", default="sdk"),
            "refresh_token": get_config_value("ifind_api.refresh_token", default=""),
            "access_token": get_config_value("ifind_api.access_token", default=""),
            "max_retries": get_config_value("ifind_api.max_retries", default=3),
            "retry_interval": get_config_value("ifind_api.retry_interval", default=5),
            "rate_limit": get_config_value("ifind_api.rate_limit", default=1),
            "timeout": get_config_value("ifind_api.timeout", default=30),
            "http_base_url": get_config_value("ifind_api.http_base_url", default="https://quantapi.51ifind.com/api/v1"),
        }

    def connect(self) -> bool:
        """
        连接到 iFinD API

        Returns:
            连接是否成功
        """
        try:
            if self.api_mode == "sdk":
                # TODO: 实际实现需要导入 iFinDPy 并调用登录接口
                # from iFinDPy import THS_iFinDLogin
                # result = THS_iFinDLogin(self.username, self.password)
                # if result != 0:
                #     raise IFindAPIError(f"iFinD 登录失败,错误代码: {result}")
                pass
            elif self.api_mode == "http":
                # HTTP 模式: 如果没有 access_token，尝试通过 refresh_token 获取
                if not self._access_token:
                    if not self.refresh_token:
                        raise IFindAPIError("HTTP 模式需要配置 refresh_token")
                    self._access_token = self._get_new_access_token()
                    logger.info("已通过 refresh_token 获取新的 access_token")
                else:
                    logger.info("使用配置中现有的 access_token")
            
            logger.info(f"iFinD API 连接成功 (模式: {self.api_mode})")
            self._is_connected = True
            return True

        except Exception as e:
            logger.error(f"iFinD API 连接失败: {e}")
            self._is_connected = False
            return False

    def _get_new_access_token(self) -> str:
        """通过 refresh_token 获取新的 access_token"""
        url = f"{self.http_base_url}/get_access_token"
        headers = {"Content-Type": "application/json", "refresh_token": self.refresh_token}
        # 注意: refresh_token 可以放在 headers 或 body 中，文档示例放在 headers
        
        try:
            response = requests.post(url, headers=headers, json={"refresh_token": self.refresh_token}, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # 检查业务错误码
            if data.get("errorcode") != 0:
                 raise IFindAPIError(f"获取 access_token 失败: {data.get('errmsg')} (code: {data.get('errorcode')})")
            
            access_token = data.get("data", {}).get("access_token")
            if not access_token:
                raise IFindAPIError("响应中未包含 access_token")
                
            return access_token
        except Exception as e:
            raise IFindAPIError(f"请求 access_token 异常: {e}")

    def disconnect(self):
        """断开 iFinD API 连接"""
        try:
            if self.api_mode == "sdk":
                # TODO: 实际实现需要调用登出接口
                # from iFinDPy import THS_iFinDLogout
                # THS_iFinDLogout()
                pass
            
            logger.info("iFinD API 连接已断开")
            self._is_connected = False

        except Exception as e:
            logger.error(f"iFinD API 断开连接失败: {e}")

    def _http_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 HTTP 请求

        Args:
            endpoint: API 端点 (e.g., "basic_data_service")
            payload: 请求体

        Returns:
            JSON 响应数据
        """
        url = f"{self.http_base_url}/{endpoint}"
        
        # 内部重试逻辑
        for attempt in range(2):
            headers = {
                "Content-Type": "application/json",
                "access_token": self._access_token or "",
                "ifindlang": "cn"
            }
            
            try:
                response = requests.post(
                    url, 
                    json=payload, 
                    headers=headers, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                
                # 检查 Token 是否失效 (错误码根据文档: -1302, -1010, -1300 等)
                error_code = data.get("errorcode") if isinstance(data, dict) else 0
                
                # 某些接口直接返回数据结构，某些返回标准包装
                # 假设标准包装，检查 token 失效
                if error_code in [-1302, -1010, -1300] and attempt == 0:
                    logger.warning(f"Token 可能已失效 (code: {error_code}), 尝试刷新...")
                    self._access_token = self._get_new_access_token()
                    continue
                
                return data
                
            except requests.RequestException as e:
                # 网络层面错误，由外层 _retry_request 处理或直接抛出
                raise e
                
        return {}

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

    def _batch_request(
        self, 
        codes: List[str], 
        fetch_func: Callable[[List[str]], pd.DataFrame], 
        chunk_size: int = 100
    ) -> pd.DataFrame:
        """
        批量请求辅助方法
        
        Args:
            codes: 代码列表
            fetch_func: 执行单个批次获取的函数
            chunk_size: 每批次大小
            
        Returns:
            合并后的DataFrame
        """
        if not codes:
            return pd.DataFrame()
            
        results = []
        total_chunks = (len(codes) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(codes), chunk_size):
            chunk = codes[i:i + chunk_size]
            try:
                # logger.debug(f"正在获取第 {i//chunk_size + 1}/{total_chunks} 批次数据 ({len(chunk)} 条)...")
                df = fetch_func(chunk)
                if not df.empty:
                    results.append(df)
                
                # 避免触发频率限制
                self._rate_limit_check()
                
            except Exception as e:
                logger.error(f"批次请求失败 (chunk {i//chunk_size + 1}): {e}")
                
        if not results:
            return pd.DataFrame()
            
        return pd.concat(results, ignore_index=True)

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
            if self.api_mode == "sdk":
                # SDK 模式: 使用 THS_DS
                # from iFinDPy import THS_DS
                # result = THS_DS(
                #     industry_code,
                #     indicator,
                #     "",  # params
                #     "",  # global_params
                #     start_date.strftime('%Y-%m-%d'),
                #     end_date.strftime('%Y-%m-%d')
                # )
                # if result.errorcode != 0:
                #    raise IFindAPIError(f"THS_DS Error: {result.errmsg}")
                # return result.data
                pass
            
            elif self.api_mode == "http":
                # HTTP 模式: 使用 date_sequence
                # 映射频率参数
                freq_map = {
                    "daily": "D", "weekly": "W", "monthly": "M", 
                    "quarterly": "Q", "yearly": "Y"
                }
                interval = freq_map.get(frequency, "D")
                
                payload = {
                    "codes": industry_code,
                    "startdate": start_date.strftime('%Y-%m-%d'),
                    "enddate": end_date.strftime('%Y-%m-%d'),
                    "functionpara": {
                        "Interval": interval,
                        "Fill": "Blank"
                    },
                    "indipara": [
                        {
                            "indicator": indicator,
                            "indiparams": []
                        }
                    ]
                }
                
                data = self._http_request("date_sequence", payload)
                
                # 解析 HTTP 响应
                # 假设返回结构: {"tables": [{"table": {"date": [...], "value": [...]}}]}
                # 实际 iFinD 返回结构比较复杂，通常包含 thscode, time, indicator_name 等列
                if "tables" in data and data["tables"]:
                    table_data = data["tables"][0]
                    # 需要根据返回的 JSON 结构转换为 DataFrame
                    # 这里假设 table_data 是一个字典列表或包含行列数据的结构
                    # 通常 iFinD HTTP 返回的 table 字段是一个对象，包含 time 和指标列
                    if "table" in table_data:
                        df = pd.DataFrame(table_data["table"])
                        # 重命名列: time -> date, 指标名 -> value
                        if "time" in df.columns:
                            df.rename(columns={"time": "date"}, inplace=True)
                        if indicator in df.columns:
                            df.rename(columns={indicator: "value"}, inplace=True)
                        return df
                
                return pd.DataFrame(columns=["date", "value"])

            logger.warning(
                f"iFinD API 实际实现待完成 (SDK模式) - "
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
            if self.api_mode == "sdk":
                # SDK 模式: 使用 THS_DateQuery
                pass
                
            elif self.api_mode == "http":
                # HTTP 模式: 使用 basic_data_service 配合 ths_member_stock 指标
                # 注意: 这种用法可能需要特定的 HTTP 接口支持，或者使用 date_sequence
                # 通常行业成分股是截面数据，使用 basic_data_service 或 date_sequence 均可
                # 假设使用 basic_data_service 获取成分股
                
                query_date = date.strftime('%Y-%m-%d') if date else datetime.now().strftime('%Y-%m-%d')
                
                # 尝试使用 date_sequence，因为 basic_data_service 可能不支持返回列表类型的指标
                payload = {
                    "codes": industry_code,
                    "startdate": query_date,
                    "enddate": query_date,
                    "functionpara": {
                        "Interval": "D",
                        "Fill": "Blank"
                    },
                    "indipara": [
                        {
                            "indicator": "ths_member_stock",
                            "indiparams": []
                        }
                    ]
                }
                
                # 注意: ths_member_stock 可能返回的是逗号分隔的字符串或列表
                data = self._http_request("date_sequence", payload)
                
                if "tables" in data and data["tables"]:
                    table_data = data["tables"][0]
                    if "table" in table_data:
                        df = pd.DataFrame(table_data["table"])
                        if "ths_member_stock" in df.columns and not df.empty:
                            members_str = df.iloc[0]["ths_member_stock"]
                            if isinstance(members_str, str):
                                return members_str.split(";")
                            elif isinstance(members_str, list):
                                return members_str
                
                return []

            logger.warning(f"iFinD API 实际实现待完成 (SDK模式) - industry_code={industry_code}")
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

        # 使用批量请求方法
        def _fetch_chunk(chunk_codes: List[str]) -> pd.DataFrame:
            if self.api_mode == "sdk":
                # SDK 模式
                pass
                
            elif self.api_mode == "http":
                # HTTP 模式: 使用 date_sequence
                payload = {
                    "codes": ",".join(chunk_codes),
                    "startdate": start_date.strftime('%Y-%m-%d'),
                    "enddate": end_date.strftime('%Y-%m-%d'),
                    "functionpara": {
                        "Interval": "D",
                        "Fill": "Blank"
                    },
                    "indipara": [
                        {
                            "indicator": indicator,
                            "indiparams": []
                        }
                    ]
                }
                
                data = self._http_request("date_sequence", payload)
                
                if "tables" in data and data["tables"]:
                    all_dfs = []
                    for table in data["tables"]:
                        if "table" in table:
                            df = pd.DataFrame(table["table"])
                            # 确保包含 thscode 列 (iFinD 返回通常包含 thscode, time)
                            if "thscode" not in df.columns and "code" in table:
                                df["thscode"] = table["code"]
                            
                            # 重命名列
                            if "time" in df.columns:
                                df.rename(columns={"time": "date"}, inplace=True)
                            if indicator in df.columns:
                                df.rename(columns={indicator: "value"}, inplace=True)
                                
                            all_dfs.append(df)
                    
                    if all_dfs:
                        return pd.concat(all_dfs, ignore_index=True)

                return pd.DataFrame()

            logger.warning(
                f"iFinD API 实际实现待完成 (SDK模式) - "
                f"stock_codes={chunk_codes[:3]}..., "
                f"indicator={indicator}"
            )
            return pd.DataFrame()

        return self._batch_request(stock_codes, _fetch_chunk)

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

    # ========== 股票数据获取方法 ==========

    def get_stock_basic_info(
        self,
        stock_codes: Union[str, List[str]],
        date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        获取股票基础信息

        Args:
            stock_codes: 股票代码或代码列表
            date: 查询日期，为 None 则使用最新

        Returns:
            DataFrame, 列: [stock_code, stock_name, industry_code, industry_name,
                          list_date, is_st]
        """
        self._check_connection()

        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]

        def _fetch_chunk(chunk_codes: List[str]) -> pd.DataFrame:
            # TODO: 实际实现需要调用 iFinD API
            # 示例:
            # indicators = (
            #     "ths_stock_short_name_stock;"
            #     "ths_industry_shenwan_l2_stock;"
            #     "ths_industry_shenwan_l2_name_stock;"
            #     "ths_ipo_date_stock;"
            #     "ths_stock_status"
            # )
            # result = THS_BD(
            #     thscode=';'.join(chunk_codes),
            #     jsonIndicator=indicators,
            #     jsonparam='',
            #     begintime=date.strftime('%Y-%m-%d') if date else ''
            # )
            
            logger.warning(
                f"iFinD API 实际实现待完成 - stock_codes={chunk_codes[:3]}..."
            )
            # 返回空DataFrame但包含列名，确保下游不报错
            return pd.DataFrame(
                columns=[
                    "stock_code",
                    "stock_name",
                    "industry_code",
                    "industry_name",
                    "list_date",
                    "is_st",
                ]
            )

        return self._batch_request(stock_codes, _fetch_chunk)

    def get_stock_financial_data(
        self,
        stock_codes: Union[str, List[str]],
        start_date: datetime,
        end_date: datetime,
        report_type: str = "report",
    ) -> pd.DataFrame:
        """
        获取股票财务数据

        Args:
            stock_codes: 股票代码或代码列表
            start_date: 起始日期
            end_date: 结束日期
            report_type: 报告类型 ('report'=报告期, 'ttm'=TTM)

        Returns:
            DataFrame, 包含财务数据
            列: [stock_code, report_date, total_assets, total_liabilities,
                current_assets, current_liabilities, inventory, net_assets,
                goodwill, operating_revenue, operating_cost, net_profit,
                cash_flow_oper_act, roe, gross_margin]
        """
        self._check_connection()

        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]

        def _fetch_chunk(chunk_codes: List[str]) -> pd.DataFrame:
            # TODO: 实际实现需要调用 iFinD API
            # indicators = (
            #     "ths_total_assets_stock;"
            #     "ths_total_liabilities_stock;"
            #     "ths_current_assets_stock;"
            #     "ths_current_liabilities_stock;"
            #     "ths_inventory_stock;"
            #     "ths_net_assets_stock;"
            #     "ths_goodwill_stock;"
            #     "ths_operating_revenue_stock;"
            #     "ths_operating_cost_stock;"
            #     "ths_net_profit_stock;"
            #     "ths_cash_flow_oper_act_stock;"
            #     "ths_roe_stock;"
            #     "ths_gross_profit_margin_stock"
            # )
            # params = "100;100;100;100;100;100;100;100;100;100;100;100;100"  # 报告期参数
            # result = THS_DP(
            #     thscode=';'.join(chunk_codes),
            #     jsonIndicator=indicators,
            #     jsonparam=params,
            #     begintime=start_date.strftime('%Y-%m-%d'),
            #     endtime=end_date.strftime('%Y-%m-%d')
            # )

            logger.warning(
                f"iFinD API 实际实现待完成 - "
                f"stock_codes={chunk_codes[:3]}..., "
                f"date_range={start_date} to {end_date}"
            )
            return pd.DataFrame()

        return self._batch_request(stock_codes, _fetch_chunk)

    def get_stock_market_data(
        self,
        stock_codes: Union[str, List[str]],
        start_date: datetime,
        end_date: datetime,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """
        获取股票行情数据

        Args:
            stock_codes: 股票代码或代码列表
            start_date: 起始日期
            end_date: 结束日期
            frequency: 数据频率 ('daily', 'weekly', 'monthly')

        Returns:
            DataFrame, 列: [stock_code, trade_date, close_price,
                          market_value, pe_ttm, pb]
        """
        self._check_connection()

        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]

        def _fetch_chunk(chunk_codes: List[str]) -> pd.DataFrame:
            # TODO: 实际实现需要调用 iFinD API
            # indicators = (
            #     "ths_close_price_stock;"
            #     "ths_market_value_stock;"
            #     "ths_pe_ttm_stock;"
            #     "ths_pb_stock"
            # )
            # result = THS_DP(
            #     thscode=';'.join(chunk_codes),
            #     jsonIndicator=indicators,
            #     jsonparam='',
            #     begintime=start_date.strftime('%Y-%m-%d'),
            #     endtime=end_date.strftime('%Y-%m-%d')
            # )

            logger.warning(
                f"iFinD API 实际实现待完成 - "
                f"stock_codes={chunk_codes[:3]}..., "
                f"date_range={start_date} to {end_date}"
            )
            return pd.DataFrame()

        return self._batch_request(stock_codes, _fetch_chunk)

    def get_stock_shareholder_data(
        self,
        stock_codes: Union[str, List[str]],
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """
        获取股票股东数据

        Args:
            stock_codes: 股票代码或代码列表
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            DataFrame, 列: [stock_code, report_date, institutional_ownership,
                          pledge_ratio]
        """
        self._check_connection()

        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]

        def _fetch_chunk(chunk_codes: List[str]) -> pd.DataFrame:
            # TODO: 实际实现需要调用 iFinD API
            # indicators = (
            #     "ths_institutional_ownership_stock;"
            #     "ths_pledge_ratio_stock"
            # )
            # result = THS_DP(
            #     thscode=';'.join(chunk_codes),
            #     jsonIndicator=indicators,
            #     jsonparam='',
            #     begintime=start_date.strftime('%Y-%m-%d'),
            #     endtime=end_date.strftime('%Y-%m-%d')
            # )

            logger.warning(
                f"iFinD API 实际实现待完成 - stock_codes={chunk_codes[:3]}..."
            )
            return pd.DataFrame()

        return self._batch_request(stock_codes, _fetch_chunk)

    def get_industry_stocks(
        self,
        industry_code: str,
        date: Optional[datetime] = None,
    ) -> List[str]:
        """
        获取行业成分股列表

        Args:
            industry_code: 行业代码（申万二级）
            date: 查询日期，为 None 则使用最新

        Returns:
            股票代码列表
        """
        self._check_connection()

        def _fetch():
            # TODO: 实际实现需要调用 iFinD API
            # query_date = date.strftime('%Y-%m-%d') if date else datetime.now().strftime('%Y-%m-%d')
            # result = THS_DateQuery(
            #     thscode=industry_code,
            #     jsonIndicator="ths_member_stock",
            #     jsonparam="",
            #     begintime=query_date,
            #     endtime=query_date
            # )

            logger.warning(
                f"iFinD API 实际实现待完成 - industry_code={industry_code}"
            )
            return []

        return self._retry_request(_fetch)

    def batch_fetch_stock_data(
        self,
        stock_codes: List[str],
        start_date: datetime,
        end_date: datetime,
        data_types: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取股票数据

        Args:
            stock_codes: 股票代码列表
            start_date: 起始日期
            end_date: 结束日期
            data_types: 数据类型列表 ['basic', 'financial', 'market', 'shareholder']
                       默认获取所有类型

        Returns:
            字典: {data_type: DataFrame}
        """
        self._check_connection()

        if data_types is None:
            data_types = ["basic", "financial", "market", "shareholder"]

        results = {}

        logger.info(
            f"开始批量获取股票数据: {len(stock_codes)} 只股票, "
            f"数据类型: {data_types}"
        )

        # 基础信息
        if "basic" in data_types:
            try:
                results["basic"] = self.get_stock_basic_info(stock_codes)
                logger.info(f"基础信息获取完成: {len(results['basic'])} 条记录")
            except Exception as e:
                logger.error(f"基础信息获取失败: {e}")
                results["basic"] = pd.DataFrame()

        # 财务数据
        if "financial" in data_types:
            try:
                results["financial"] = self.get_stock_financial_data(
                    stock_codes, start_date, end_date
                )
                logger.info(f"财务数据获取完成: {len(results['financial'])} 条记录")
            except Exception as e:
                logger.error(f"财务数据获取失败: {e}")
                results["financial"] = pd.DataFrame()

        # 行情数据
        if "market" in data_types:
            try:
                results["market"] = self.get_stock_market_data(
                    stock_codes, start_date, end_date
                )
                logger.info(f"行情数据获取完成: {len(results['market'])} 条记录")
            except Exception as e:
                logger.error(f"行情数据获取失败: {e}")
                results["market"] = pd.DataFrame()

        # 股东数据
        if "shareholder" in data_types:
            try:
                results["shareholder"] = self.get_stock_shareholder_data(
                    stock_codes, start_date, end_date
                )
                logger.info(f"股东数据获取完成: {len(results['shareholder'])} 条记录")
            except Exception as e:
                logger.error(f"股东数据获取失败: {e}")
                results["shareholder"] = pd.DataFrame()

        logger.success(f"批量数据获取完成: {len(data_types)} 种数据类型")

        return results

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
