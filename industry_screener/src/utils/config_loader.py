"""
配置加载器
支持从 YAML 文件加载配置,并支持环境变量替换
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from loguru import logger


class ConfigLoader:
    """配置加载器类"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置加载器

        Args:
            config_dir: 配置文件目录,默认为项目根目录下的 config/
        """
        if config_dir is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = Path(config_dir)
        self._configs: Dict[str, Any] = {}

    def load_config(self, config_name: str) -> Dict[str, Any]:
        """
        加载指定的配置文件

        Args:
            config_name: 配置文件名(不含扩展名)

        Returns:
            配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
        """
        # 如果已经加载过,直接返回缓存
        if config_name in self._configs:
            return self._configs[config_name]

        # 尝试加载配置文件
        config_path = self.config_dir / f"{config_name}.yaml"
        if not config_path.exists():
            # 尝试加载 .example 文件
            example_path = self.config_dir / f"{config_name}.yaml.example"
            if example_path.exists():
                logger.warning(
                    f"配置文件 {config_path} 不存在,使用示例配置 {example_path}"
                )
                config_path = example_path
            else:
                raise FileNotFoundError(
                    f"配置文件不存在: {config_path} 或 {example_path}"
                )

        # 加载 YAML 文件
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # 递归替换环境变量
        config_data = self._replace_env_vars(config_data)

        # 缓存配置
        self._configs[config_name] = config_data
        logger.info(f"成功加载配置文件: {config_path}")

        return config_data

    def _replace_env_vars(self, data: Any) -> Any:
        """
        递归替换配置中的环境变量

        支持格式:
        - ${VAR_NAME} - 必须存在的环境变量
        - ${VAR_NAME:default_value} - 带默认值的环境变量

        Args:
            data: 配置数据(可能是字典、列表、字符串等)

        Returns:
            替换后的配置数据
        """
        if isinstance(data, dict):
            return {key: self._replace_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]
        elif isinstance(data, str):
            return self._substitute_env_var(data)
        else:
            return data

    def _substitute_env_var(self, value: str) -> Any:
        """
        替换单个字符串中的环境变量

        Args:
            value: 包含环境变量的字符串

        Returns:
            替换后的值(可能是字符串、整数、布尔值等)
        """
        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2)

            # 获取环境变量
            env_value = os.environ.get(var_name)

            if env_value is not None:
                result = env_value
            elif default_value is not None:
                result = default_value
            else:
                raise ValueError(
                    f"环境变量 {var_name} 未设置且无默认值"
                )

            return result

        # 执行替换
        result = re.sub(pattern, replacer, value)

        # 尝试转换为合适的类型
        return self._convert_type(result)

    @staticmethod
    def _convert_type(value: str) -> Any:
        """
        将字符串转换为合适的类型

        Args:
            value: 字符串值

        Returns:
            转换后的值
        """
        # 布尔值
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        if value.lower() in ('false', 'no', 'off', '0'):
            return False

        # 空值
        if value.lower() in ('null', 'none', ''):
            return None

        # 尝试转换为整数
        try:
            return int(value)
        except ValueError:
            pass

        # 尝试转换为浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # 保持字符串
        return value

    def get(self, config_name: str, key_path: str, default: Any = None) -> Any:
        """
        获取配置项的值,支持嵌套键

        Args:
            config_name: 配置文件名
            key_path: 键路径,使用点号分隔,如 'database.host'
            default: 默认值

        Returns:
            配置值

        Examples:
            >>> loader = ConfigLoader()
            >>> loader.get('config', 'database.host')
            'localhost'
        """
        config = self.load_config(config_name)

        # 分割键路径
        keys = key_path.split('.')

        # 递归获取值
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def reload(self, config_name: Optional[str] = None):
        """
        重新加载配置文件

        Args:
            config_name: 配置文件名,为 None 则重新加载所有配置
        """
        if config_name is None:
            self._configs.clear()
            logger.info("清空所有配置缓存")
        elif config_name in self._configs:
            del self._configs[config_name]
            logger.info(f"清空配置缓存: {config_name}")


# 全局配置加载器实例
_config_loader = ConfigLoader()


def get_config(config_name: str = "config") -> Dict[str, Any]:
    """
    获取配置文件

    Args:
        config_name: 配置文件名,默认为 'config'

    Returns:
        配置字典
    """
    return _config_loader.load_config(config_name)


def get_config_value(key_path: str, config_name: str = "config", default: Any = None) -> Any:
    """
    获取配置项的值

    Args:
        key_path: 键路径,使用点号分隔
        config_name: 配置文件名,默认为 'config'
        default: 默认值

    Returns:
        配置值
    """
    return _config_loader.get(config_name, key_path, default)
