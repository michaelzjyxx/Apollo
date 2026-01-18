"""
日志配置模块
使用 Loguru 提供统一的日志管理
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from .config_loader import get_config_value


def setup_logger(
    log_dir: Optional[Path] = None,
    log_level: Optional[str] = None,
    rotation: Optional[str] = None,
    retention: Optional[str] = None,
    compression: Optional[str] = None,
) -> None:
    """
    配置日志系统

    Args:
        log_dir: 日志目录,默认从配置文件读取
        log_level: 日志级别,默认从配置文件读取
        rotation: 日志轮转规则,默认从配置文件读取
        retention: 日志保留时间,默认从配置文件读取
        compression: 日志压缩格式,默认从配置文件读取
    """
    # 移除默认的 handler
    logger.remove()

    # 从配置文件读取默认值
    if log_level is None:
        log_level = get_config_value("logging.level", default="INFO")

    if log_dir is None:
        log_dir_str = get_config_value("logging.log_dir", default="data/logs")
        project_root = Path(__file__).parent.parent.parent
        log_dir = project_root / log_dir_str

    if rotation is None:
        rotation = get_config_value("logging.rotation", default="100 MB")

    if retention is None:
        retention = get_config_value("logging.retention", default="30 days")

    if compression is None:
        compression = get_config_value("logging.compression", default="zip")

    # 获取日志格式
    log_format = get_config_value(
        "logging.format",
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # 创建日志目录
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 添加控制台输出 handler
    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 添加文件输出 handler - 所有日志
    logger.add(
        log_dir / "app.log",
        format=log_format,
        level=log_level,
        rotation=rotation,
        retention=retention,
        compression=compression,
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    # 添加文件输出 handler - 错误日志
    logger.add(
        log_dir / "error.log",
        format=log_format,
        level="ERROR",
        rotation=rotation,
        retention=retention,
        compression=compression,
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    logger.info(f"日志系统初始化完成 - 日志目录: {log_dir}, 日志级别: {log_level}")


def get_logger(name: str):
    """
    获取指定名称的 logger

    Args:
        name: logger 名称

    Returns:
        logger 实例
    """
    return logger.bind(name=name)
