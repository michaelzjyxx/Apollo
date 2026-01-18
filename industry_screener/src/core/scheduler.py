"""
调度器 - 定时数据更新和评分计算

使用 APScheduler 实现:
- 季度财务数据更新
- 月度景气指标更新
- 周度估值/资金数据更新
- 年度竞争格局数据更新
"""

from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from ..data import IFindAPIClient, get_db_manager
from ..utils import get_config_value, get_current_quarter, get_recent_report_date
from .data_service import DataService


class DataScheduler:
    """数据更新调度器"""

    def __init__(self, api_client: Optional[IFindAPIClient] = None):
        """
        初始化调度器

        Args:
            api_client: iFinD API 客户端,为 None 则自动创建
        """
        self.scheduler = BackgroundScheduler(
            timezone=get_config_value("scheduler.timezone", default="Asia/Shanghai")
        )

        self.api_client = api_client or IFindAPIClient()
        self.enabled = get_config_value("scheduler.enabled", default=True)

        # 加载调度配置
        self.config = get_config_value("scheduler", default={})

        logger.info("调度器初始化成功")

    def setup_jobs(self):
        """设置所有定时任务"""

        if not self.enabled:
            logger.warning("调度器未启用")
            return

        # 1. 季度财务数据更新
        if self.config.get("quarterly_data", {}).get("enabled", True):
            quarterly_config = self.config["quarterly_data"]
            self.scheduler.add_job(
                func=self._update_quarterly_data,
                trigger=CronTrigger.from_crontab(quarterly_config["cron"]),
                id="quarterly_data_update",
                name="季度财务数据更新",
                replace_existing=True,
            )
            logger.info(
                f"添加定时任务: 季度财务数据更新 - {quarterly_config['cron']}"
            )

        # 2. 月度景气指标更新
        if self.config.get("monthly_data", {}).get("enabled", True):
            monthly_config = self.config["monthly_data"]
            self.scheduler.add_job(
                func=self._update_monthly_data,
                trigger=CronTrigger.from_crontab(monthly_config["cron"]),
                id="monthly_data_update",
                name="月度景气指标更新",
                replace_existing=True,
            )
            logger.info(
                f"添加定时任务: 月度景气指标更新 - {monthly_config['cron']}"
            )

        # 3. 周度估值/资金数据更新
        if self.config.get("weekly_data", {}).get("enabled", True):
            weekly_config = self.config["weekly_data"]
            self.scheduler.add_job(
                func=self._update_weekly_data,
                trigger=CronTrigger.from_crontab(weekly_config["cron"]),
                id="weekly_data_update",
                name="周度估值/资金数据更新",
                replace_existing=True,
            )
            logger.info(
                f"添加定时任务: 周度估值/资金数据更新 - {weekly_config['cron']}"
            )

        # 4. 年度竞争格局数据更新
        if self.config.get("annual_data", {}).get("enabled", True):
            annual_config = self.config["annual_data"]
            self.scheduler.add_job(
                func=self._update_annual_data,
                trigger=CronTrigger.from_crontab(annual_config["cron"]),
                id="annual_data_update",
                name="年度竞争格局数据更新",
                replace_existing=True,
            )
            logger.info(
                f"添加定时任务: 年度竞争格局数据更新 - {annual_config['cron']}"
            )

    def start(self):
        """启动调度器"""
        if not self.enabled:
            logger.warning("调度器未启用,跳过启动")
            return

        self.setup_jobs()
        self.scheduler.start()
        logger.info("调度器已启动")

        # 打印所有任务
        self.print_jobs()

    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("调度器已停止")

    def print_jobs(self):
        """打印所有定时任务"""
        jobs = self.scheduler.get_jobs()

        logger.info("=" * 60)
        logger.info(f"共有 {len(jobs)} 个定时任务:")

        for job in jobs:
            logger.info(f"  - {job.name} ({job.id})")
            logger.info(f"    下次运行: {job.next_run_time}")

        logger.info("=" * 60)

    # ========== 定时任务实现 ==========

    def _update_quarterly_data(self):
        """更新季度财务数据"""
        logger.info("开始更新季度财务数据...")

        try:
            # 获取最近应该披露的季报日期
            report_date = get_recent_report_date()

            # 获取配置
            quarterly_config = self.config["quarterly_data"]
            lookback_days = quarterly_config.get("lookback_days", 10)
            indicators = quarterly_config.get("indicators", [])

            # 计算查询时间范围
            start_date = report_date - timedelta(days=lookback_days)
            end_date = datetime.now()

            # 连接 API
            if not self.api_client.connect():
                logger.error("iFinD API 连接失败")
                return

            # 获取数据
            db = get_db_manager()
            with db.get_session() as session:
                service = DataService(session)

                count = service.fetch_and_store_raw_data(
                    api_client=self.api_client,
                    indicators=indicators,
                    start_date=start_date,
                    end_date=end_date,
                )

                logger.info(f"季度财务数据更新完成,共 {count} 条记录")

                # 计算指标
                self._calculate_and_score(service, report_date)

        except Exception as e:
            logger.error(f"季度财务数据更新失败: {e}")

        finally:
            self.api_client.disconnect()

    def _update_monthly_data(self):
        """更新月度景气指标"""
        logger.info("开始更新月度景气指标...")

        try:
            monthly_config = self.config["monthly_data"]
            indicators = monthly_config.get("indicators", [])

            # TODO: 实现月度数据更新逻辑

            logger.info("月度景气指标更新完成")

        except Exception as e:
            logger.error(f"月度景气指标更新失败: {e}")

    def _update_weekly_data(self):
        """更新周度估值/资金数据"""
        logger.info("开始更新周度估值/资金数据...")

        try:
            weekly_config = self.config["weekly_data"]
            indicators = weekly_config.get("indicators", [])

            # TODO: 实现周度数据更新逻辑

            logger.info("周度估值/资金数据更新完成")

        except Exception as e:
            logger.error(f"周度估值/资金数据更新失败: {e}")

    def _update_annual_data(self):
        """更新年度竞争格局数据"""
        logger.info("开始更新年度竞争格局数据...")

        try:
            annual_config = self.config["annual_data"]
            indicators = annual_config.get("indicators", [])

            # TODO: 实现年度数据更新逻辑

            logger.info("年度竞争格局数据更新完成")

        except Exception as e:
            logger.error(f"年度竞争格局数据更新失败: {e}")

    def _calculate_and_score(self, service: DataService, report_date: datetime):
        """
        计算指标并评分

        Args:
            service: 数据服务
            report_date: 报告期
        """
        logger.info(f"开始计算指标并评分: {report_date.date()}")

        try:
            # 1. 计算所有行业的指标
            # TODO: 批量计算

            # 2. 计算评分
            scores = service.calculate_scores(report_date=report_date)

            logger.info(f"指标计算和评分完成,共 {len(scores)} 个行业")

            # 3. 打印 Top 10
            top_10 = service.get_top_industries(
                score_date=datetime.now(), n=10
            )

            logger.info("Top 10 行业:")
            for i, score in enumerate(top_10, start=1):
                logger.info(
                    f"  {i}. {score.industry_name}: {score.total_score:.1f}分"
                )

        except Exception as e:
            logger.error(f"计算指标并评分失败: {e}")

    # ========== 手动触发 ==========

    def trigger_quarterly_update(self):
        """手动触发季度数据更新"""
        logger.info("手动触发季度数据更新")
        self._update_quarterly_data()

    def trigger_monthly_update(self):
        """手动触发月度数据更新"""
        logger.info("手动触发月度数据更新")
        self._update_monthly_data()

    def trigger_weekly_update(self):
        """手动触发周度数据更新"""
        logger.info("手动触发周度数据更新")
        self._update_weekly_data()

    def trigger_annual_update(self):
        """手动触发年度数据更新"""
        logger.info("手动触发年度数据更新")
        self._update_annual_data()
