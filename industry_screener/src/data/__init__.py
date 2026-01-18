"""
数据访问层
"""

from .database import DatabaseManager, get_db_manager, get_session
from .ifind_api import IFindAPIClient, IFindAPIError, get_ifind_indicator_name
from .models import (
    BacktestResult,
    Base,
    CalculatedIndicator,
    IndustryScore,
    QualitativeScore,
    RawData,
)
from .repository import (
    BacktestResultRepository,
    BaseRepository,
    CalculatedIndicatorRepository,
    IndustryScoreRepository,
    QualitativeScoreRepository,
    RawDataRepository,
)

__all__ = [
    # database
    "DatabaseManager",
    "get_db_manager",
    "get_session",
    # ifind_api
    "IFindAPIClient",
    "IFindAPIError",
    "get_ifind_indicator_name",
    # models
    "Base",
    "RawData",
    "CalculatedIndicator",
    "IndustryScore",
    "QualitativeScore",
    "BacktestResult",
    # repository
    "BaseRepository",
    "RawDataRepository",
    "CalculatedIndicatorRepository",
    "IndustryScoreRepository",
    "QualitativeScoreRepository",
    "BacktestResultRepository",
]
