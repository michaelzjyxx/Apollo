"""
核心基类定义 - 统一评分和筛选框架
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session


class BaseScorer(ABC):
    """通用评分器基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化评分器
        
        Args:
            config: 评分配置字典
        """
        self.config = config

    @abstractmethod
    def score(self, entity_id: str, date: Any) -> Any:
        """
        评分接口
        
        Args:
            entity_id: 实体ID（如行业代码或股票代码）
            date: 评分日期
            
        Returns:
            评分结果对象
        """
        pass

    def _apply_rules(
        self, 
        value: Optional[float], 
        rules: List[Dict[str, Any]],
        default_score: float = 0.0
    ) -> float:
        """
        应用数值规则进行评分
        
        Args:
            value: 待评分的数值
            rules: 规则列表，每个规则应包含 min, max, score
            default_score: 默认分数
            
        Returns:
            得分
        """
        if value is None:
            return default_score

        for rule in rules:
            min_val = rule.get("min")
            max_val = rule.get("max")

            # 检查是否在范围内
            # 如果 min_val 存在且 value < min_val，则不匹配
            if min_val is not None and value < min_val:
                continue
            # 如果 max_val 存在且 value >= max_val，则不匹配
            if max_val is not None and value >= max_val:
                continue

            return float(rule.get("score", 0.0))

        return default_score

    def _score_by_condition(
        self, 
        condition: str, 
        rules: List[Dict[str, Any]],
        default_score: float = 0.0
    ) -> float:
        """
        根据字符串条件进行评分
        
        Args:
            condition: 待匹配的条件字符串
            rules: 规则列表，每个规则应包含 condition, score
            default_score: 默认分数
            
        Returns:
            得分
        """
        if condition is None:
            return default_score

        for rule in rules:
            if rule.get("condition") == condition:
                return float(rule.get("score", 0.0))
                
        return default_score


class BaseFilter(ABC):
    """通用筛选器基类"""

    def __init__(self, session: Session, config: Dict[str, Any]):
        """
        初始化筛选器
        
        Args:
            session: 数据库会话
            config: 筛选配置字典
        """
        self.session = session
        self.config = config

    @abstractmethod
    def filter(self, candidates: List[Any], date: Any, **kwargs) -> Any:
        """
        筛选接口
        
        Args:
            candidates: 候选列表
            date: 筛选日期
            **kwargs: 其他参数
            
        Returns:
            筛选结果
        """
        pass
