"""
日期时间工具函数
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import pandas as pd


def get_quarter_dates(year: int, quarter: int) -> Tuple[datetime, datetime]:
    """
    获取指定季度的起止日期

    Args:
        year: 年份
        quarter: 季度 (1-4)

    Returns:
        (起始日期, 结束日期)
    """
    if quarter not in [1, 2, 3, 4]:
        raise ValueError(f"季度必须在 1-4 之间,实际值: {quarter}")

    quarter_starts = {
        1: (1, 1),
        2: (4, 1),
        3: (7, 1),
        4: (10, 1),
    }

    quarter_ends = {
        1: (3, 31),
        2: (6, 30),
        3: (9, 30),
        4: (12, 31),
    }

    start_month, start_day = quarter_starts[quarter]
    end_month, end_day = quarter_ends[quarter]

    start_date = datetime(year, start_month, start_day)
    end_date = datetime(year, end_month, end_day)

    return start_date, end_date


def get_current_quarter() -> Tuple[int, int]:
    """
    获取当前季度

    Returns:
        (年份, 季度)
    """
    now = datetime.now()
    quarter = (now.month - 1) // 3 + 1
    return now.year, quarter


def get_previous_quarter(year: int, quarter: int, n: int = 1) -> Tuple[int, int]:
    """
    获取前N个季度

    Args:
        year: 当前年份
        quarter: 当前季度
        n: 向前推移的季度数

    Returns:
        (年份, 季度)
    """
    total_quarters = (year - 1) * 4 + quarter
    total_quarters -= n

    new_year = (total_quarters - 1) // 4 + 1
    new_quarter = (total_quarters - 1) % 4 + 1

    return new_year, new_quarter


def get_quarter_list(
    start_year: int,
    start_quarter: int,
    end_year: Optional[int] = None,
    end_quarter: Optional[int] = None,
) -> List[Tuple[int, int]]:
    """
    获取季度列表

    Args:
        start_year: 起始年份
        start_quarter: 起始季度
        end_year: 结束年份,为 None 则使用当前年份
        end_quarter: 结束季度,为 None 则使用当前季度

    Returns:
        [(年份, 季度), ...]
    """
    if end_year is None or end_quarter is None:
        end_year, end_quarter = get_current_quarter()

    quarters = []
    current_year = start_year
    current_quarter = start_quarter

    while (current_year, current_quarter) <= (end_year, end_quarter):
        quarters.append((current_year, current_quarter))

        # 下一个季度
        current_quarter += 1
        if current_quarter > 4:
            current_quarter = 1
            current_year += 1

    return quarters


def get_year_list(
    start_year: int,
    end_year: Optional[int] = None,
) -> List[int]:
    """
    获取年份列表

    Args:
        start_year: 起始年份
        end_year: 结束年份,为 None 则使用当前年份

    Returns:
        [年份, ...]
    """
    if end_year is None:
        end_year = datetime.now().year

    return list(range(start_year, end_year + 1))


def get_trading_days(
    start_date: datetime,
    end_date: datetime,
    calendar: Optional[pd.DatetimeIndex] = None,
) -> List[datetime]:
    """
    获取交易日列表

    Args:
        start_date: 起始日期
        end_date: 结束日期
        calendar: 交易日历,为 None 则使用所有工作日

    Returns:
        交易日列表
    """
    if calendar is not None:
        # 使用提供的交易日历
        mask = (calendar >= start_date) & (calendar <= end_date)
        return calendar[mask].to_list()
    else:
        # 使用工作日(周一到周五)
        dates = pd.date_range(start_date, end_date, freq='B')
        return dates.to_list()


def get_recent_report_date(reference_date: Optional[datetime] = None) -> datetime:
    """
    获取最近的财报披露日期

    根据当前日期判断最近应该披露的是哪个季度的财报

    Args:
        reference_date: 参考日期,为 None 则使用当前日期

    Returns:
        最近的财报日期(季度末日期)
    """
    if reference_date is None:
        reference_date = datetime.now()

    year = reference_date.year
    month = reference_date.month

    # 财报披露规则:
    # Q1 (3月31日): 4月30日前披露
    # Q2 (6月30日): 8月31日前披露
    # Q3 (9月30日): 10月31日前披露
    # Q4 (12月31日): 次年4月30日前披露

    if month >= 5:  # 5月以后,Q1已披露
        if month >= 9:  # 9月以后,Q2已披露
            if month >= 11:  # 11月以后,Q3已披露
                # 最近是Q3
                return datetime(year, 9, 30)
            else:
                # 最近是Q2
                return datetime(year, 6, 30)
        else:
            # 最近是Q1
            return datetime(year, 3, 31)
    else:
        # 最近是去年Q4
        return datetime(year - 1, 12, 31)


def format_quarter(year: int, quarter: int) -> str:
    """
    格式化季度字符串

    Args:
        year: 年份
        quarter: 季度

    Returns:
        格式化字符串,如 '2024Q1'
    """
    return f"{year}Q{quarter}"


def parse_quarter(quarter_str: str) -> Tuple[int, int]:
    """
    解析季度字符串

    Args:
        quarter_str: 季度字符串,如 '2024Q1'

    Returns:
        (年份, 季度)
    """
    parts = quarter_str.split('Q')
    if len(parts) != 2:
        raise ValueError(f"无效的季度字符串: {quarter_str}")

    year = int(parts[0])
    quarter = int(parts[1])

    if quarter not in [1, 2, 3, 4]:
        raise ValueError(f"无效的季度值: {quarter}")

    return year, quarter


def is_trading_day(
    date: datetime,
    calendar: Optional[pd.DatetimeIndex] = None,
) -> bool:
    """
    判断是否为交易日

    Args:
        date: 日期
        calendar: 交易日历,为 None 则使用工作日规则

    Returns:
        是否为交易日
    """
    if calendar is not None:
        return date in calendar
    else:
        # 简单判断:非周六日即为交易日(实际应考虑节假日)
        return date.weekday() < 5


def get_next_trading_day(
    date: datetime,
    calendar: Optional[pd.DatetimeIndex] = None,
) -> datetime:
    """
    获取下一个交易日

    Args:
        date: 当前日期
        calendar: 交易日历

    Returns:
        下一个交易日
    """
    next_date = date + timedelta(days=1)

    while not is_trading_day(next_date, calendar):
        next_date += timedelta(days=1)

    return next_date


def get_previous_trading_day(
    date: datetime,
    calendar: Optional[pd.DatetimeIndex] = None,
) -> datetime:
    """
    获取上一个交易日

    Args:
        date: 当前日期
        calendar: 交易日历

    Returns:
        上一个交易日
    """
    prev_date = date - timedelta(days=1)

    while not is_trading_day(prev_date, calendar):
        prev_date -= timedelta(days=1)

    return prev_date
