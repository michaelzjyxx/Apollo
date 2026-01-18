"""
Industry Screener - Streamlit Web 应用主入口
"""

import sys
from pathlib import Path

import streamlit as st

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils import setup_logger

# 页面配置
st.set_page_config(
    page_title="Industry Screener - A股行业筛选系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 设置日志
setup_logger()

# 侧边栏
with st.sidebar:
    st.title("📊 Industry Screener")
    st.markdown("---")

    # 导航
    page = st.radio(
        "导航",
        [
            "🏠 首页概览",
            "📈 行业排名",
            "🔍 行业详情",
            "📉 趋势分析",
            "⚠️ 红线监控",
            "💼 回测结果",
            "⚙️ 系统设置",
        ],
    )

    st.markdown("---")
    st.caption("© 2026 Industry Screener")

# 主页面路由
if page == "🏠 首页概览":
    from .pages import home

    home.show()
elif page == "📈 行业排名":
    from .pages import ranking

    ranking.show()
elif page == "🔍 行业详情":
    from .pages import detail

    detail.show()
elif page == "📉 趋势分析":
    from .pages import trend

    trend.show()
elif page == "⚠️ 红线监控":
    from .pages import redline

    redline.show()
elif page == "💼 回测结果":
    from .pages import backtest

    backtest.show()
elif page == "⚙️ 系统设置":
    from .pages import settings

    settings.show()
