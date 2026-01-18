#!/usr/bin/env python3
"""
数据库初始化脚本

功能:
1. 创建数据库表
2. 导入定性评分预设库
3. 测试数据库连接
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from loguru import logger

from src.data import DatabaseManager, QualitativeScore, get_db_manager
from src.utils import get_config, setup_logger


def init_database(drop_existing: bool = False):
    """
    初始化数据库

    Args:
        drop_existing: 是否删除现有表
    """
    # 设置日志
    setup_logger()

    logger.info("=" * 60)
    logger.info("数据库初始化脚本")
    logger.info("=" * 60)

    # 获取数据库管理器
    db = get_db_manager()

    # 测试连接
    logger.info("测试数据库连接...")
    if not db.test_connection():
        logger.error("数据库连接失败,请检查配置")
        return False

    # 创建表
    logger.info("创建数据库表...")
    db.create_tables(drop_existing=drop_existing)

    # 导入定性评分预设库
    logger.info("导入定性评分预设库...")
    if not import_qualitative_scores():
        logger.warning("定性评分预设库导入失败")

    logger.info("=" * 60)
    logger.info("数据库初始化完成")
    logger.info("=" * 60)

    return True


def import_qualitative_scores() -> bool:
    """
    从 YAML 文件导入定性评分预设库

    Returns:
        是否成功
    """
    try:
        # 读取 YAML 文件
        config_path = project_root / "config" / "industry_qualitative.yaml"
        if not config_path.exists():
            logger.error(f"定性评分配置文件不存在: {config_path}")
            return False

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 获取数据库会话
        db = get_db_manager()
        with db.get_session() as session:
            # 清空现有数据(如果需要)
            # session.query(QualitativeScore).delete()

            # 导入数据
            industries = data.get("industries", [])
            count = 0

            for industry in industries:
                # 检查是否已存在
                existing = (
                    session.query(QualitativeScore)
                    .filter(
                        QualitativeScore.industry_code == industry["code"]
                    )
                    .first()
                )

                if existing:
                    # 更新现有记录
                    existing.industry_name = industry["name"]
                    existing.policy_score = industry["policy_score"]
                    existing.policy_reason = industry.get("policy_reason")
                    existing.business_model_score = industry["business_model_score"]
                    existing.business_model_reason = industry.get(
                        "business_model_reason"
                    )
                    existing.barrier_score = industry["barrier_score"]
                    existing.barrier_reason = industry.get("barrier_reason")
                    existing.moat_score = industry["moat_score"]
                    existing.moat_reason = industry.get("moat_reason")
                    existing.last_review = industry.get("last_review")
                    existing.is_active = True
                    logger.debug(f"更新定性评分: {industry['name']}")
                else:
                    # 创建新记录
                    score = QualitativeScore(
                        industry_code=industry["code"],
                        industry_name=industry["name"],
                        policy_score=industry["policy_score"],
                        policy_reason=industry.get("policy_reason"),
                        business_model_score=industry["business_model_score"],
                        business_model_reason=industry.get("business_model_reason"),
                        barrier_score=industry["barrier_score"],
                        barrier_reason=industry.get("barrier_reason"),
                        moat_score=industry["moat_score"],
                        moat_reason=industry.get("moat_reason"),
                        last_review=industry.get("last_review"),
                        is_active=True,
                    )
                    session.add(score)
                    logger.debug(f"导入定性评分: {industry['name']}")

                count += 1

            session.commit()
            logger.info(f"成功导入 {count} 个行业的定性评分")

        return True

    except Exception as e:
        logger.error(f"导入定性评分失败: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库初始化脚本")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="删除现有表并重新创建",
    )
    args = parser.parse_args()

    success = init_database(drop_existing=args.drop)
    sys.exit(0 if success else 1)
