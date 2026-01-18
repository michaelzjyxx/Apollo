"""
数据库连接管理
"""

from contextlib import contextmanager
from typing import Generator, Optional

from loguru import logger
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from ..utils import get_config_value
from .models import Base


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, config: Optional[dict] = None):
        """
        初始化数据库管理器

        Args:
            config: 数据库配置字典,为 None 则从配置文件读取
        """
        if config is None:
            config = self._load_config_from_file()

        self.config = config
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @staticmethod
    def _load_config_from_file() -> dict:
        """从配置文件加载数据库配置"""
        return {
            "host": get_config_value("database.host", default="localhost"),
            "port": get_config_value("database.port", default=3306),
            "username": get_config_value("database.username", default="root"),
            "password": get_config_value("database.password", default=""),
            "database": get_config_value(
                "database.database", default="industry_screener"
            ),
            "charset": get_config_value("database.charset", default="utf8mb4"),
            "pool_size": get_config_value("database.pool_size", default=10),
            "max_overflow": get_config_value("database.max_overflow", default=20),
            "echo": get_config_value("database.echo", default=False),
        }

    def _get_connection_string(self) -> str:
        """构建数据库连接字符串"""
        return (
            f"mysql+pymysql://{self.config['username']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}"
            f"/{self.config['database']}"
            f"?charset={self.config['charset']}"
        )

    @property
    def engine(self) -> Engine:
        """获取数据库引擎"""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self) -> Engine:
        """创建数据库引擎"""
        connection_string = self._get_connection_string()

        # 创建引擎
        engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=self.config.get("pool_size", 10),
            max_overflow=self.config.get("max_overflow", 20),
            pool_pre_ping=True,  # 连接前测试连接是否有效
            pool_recycle=3600,  # 1小时后回收连接
            echo=self.config.get("echo", False),  # 是否打印SQL
        )

        # 添加事件监听器
        self._setup_event_listeners(engine)

        logger.info(
            f"数据库引擎创建成功 - "
            f"host={self.config['host']}, "
            f"database={self.config['database']}"
        )

        return engine

    @staticmethod
    def _setup_event_listeners(engine: Engine):
        """设置事件监听器"""

        @event.listens_for(engine, "connect")
        def set_sql_mode(dbapi_conn, connection_record):
            """设置 SQL 模式"""
            cursor = dbapi_conn.cursor()
            cursor.execute("SET sql_mode='STRICT_TRANS_TABLES'")
            cursor.close()

        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """连接签出时的日志"""
            logger.debug("数据库连接已签出")

    @property
    def session_factory(self) -> sessionmaker:
        """获取 Session 工厂"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话(上下文管理器)

        Yields:
            Session 对象

        Examples:
            >>> db = DatabaseManager()
            >>> with db.get_session() as session:
            ...     result = session.query(RawData).first()
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库会话异常: {e}")
            raise
        finally:
            session.close()

    def create_tables(self, drop_existing: bool = False):
        """
        创建数据库表

        Args:
            drop_existing: 是否删除现有表
        """
        if drop_existing:
            logger.warning("删除现有数据库表...")
            Base.metadata.drop_all(self.engine)

        logger.info("创建数据库表...")
        Base.metadata.create_all(self.engine)
        logger.info("数据库表创建成功")

    def drop_tables(self):
        """删除所有数据库表"""
        logger.warning("删除所有数据库表...")
        Base.metadata.drop_all(self.engine)
        logger.info("数据库表删除成功")

    def test_connection(self) -> bool:
        """
        测试数据库连接

        Returns:
            连接是否成功
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self._engine is not None:
            self._engine.dispose()
            logger.info("数据库连接已关闭")


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    获取全局数据库管理器实例

    Returns:
        DatabaseManager 实例
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_session() -> Generator[Session, None, None]:
    """
    获取数据库会话(便捷函数)

    Yields:
        Session 对象
    """
    db = get_db_manager()
    with db.get_session() as session:
        yield session
