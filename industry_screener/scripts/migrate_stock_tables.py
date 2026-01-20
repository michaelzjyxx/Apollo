#!/usr/bin/env python3
"""
数据库迁移脚本 - 创建股票相关表

运行方式:
    python scripts/migrate_stock_tables.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from industry_screener.src.data.database import engine
from industry_screener.src.data.models import (
    Base,
    Stock,
    StockCalculated,
    StockFinancial,
    StockMarket,
    StockScore,
)


def migrate_stock_tables():
    """创建股票相关表"""
    logger.info("开始创建股票相关表...")

    try:
        # 创建股票相关表
        tables_to_create = [
            Stock.__table__,
            StockFinancial.__table__,
            StockMarket.__table__,
            StockCalculated.__table__,
            StockScore.__table__,
        ]

        Base.metadata.create_all(engine, tables=tables_to_create)

        logger.success("股票相关表创建成功！")
        logger.info("已创建以下表:")
        for table in tables_to_create:
            logger.info(f"  - {table.name}")

        return True

    except Exception as e:
        logger.error(f"创建表失败: {e}")
        return False


def check_tables_exist():
    """检查表是否已存在"""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    stock_tables = [
        "stocks",
        "stock_financials",
        "stock_market",
        "stock_calculated",
        "stock_scores",
    ]

    logger.info("检查现有表...")
    for table in stock_tables:
        if table in existing_tables:
            logger.warning(f"  表 {table} 已存在")
        else:
            logger.info(f"  表 {table} 不存在，将创建")

    return [t for t in stock_tables if t not in existing_tables]


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("股票筛选系统 - 数据库迁移")
    logger.info("=" * 60)

    # 检查表是否存在
    tables_to_create = check_tables_exist()

    if not tables_to_create:
        logger.warning("所有股票相关表已存在，无需迁移")
        return

    # 确认迁移
    logger.info(f"\n将创建 {len(tables_to_create)} 个表")
    response = input("是否继续? (y/n): ")

    if response.lower() != "y":
        logger.info("迁移已取消")
        return

    # 执行迁移
    success = migrate_stock_tables()

    if success:
        logger.success("\n✅ 数据库迁移完成！")
        logger.info("\n下一步:")
        logger.info("  1. 运行数据获取脚本填充股票数据")
        logger.info("  2. 运行股票筛选命令测试功能")
    else:
        logger.error("\n❌ 数据库迁移失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
