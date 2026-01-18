"""
系统设置页面
"""

import streamlit as st

from ...utils import get_config


def show():
    """显示系统设置页面"""
    st.title("⚙️ 系统设置")

    tabs = st.tabs(["📊 评分权重", "🗄️ 数据管理", "⏰ 调度配置", "ℹ️ 系统信息"])

    with tabs[0]:
        st.markdown("### 评分权重配置")
        st.info("评分权重配置请编辑 `config/scoring_weights.yaml` 文件")

        st.markdown("""
        **配置文件位置**: `config/scoring_weights.yaml`

        **主要配置项**:
        - 竞争格局 (15分)
        - 盈利能力 (15分)
        - 成长性 (10分)
        - 现金流 (10分)
        - 估值 (10分)
        - 景气度 (5分)
        - 周期位置 (5分)
        - 定性评分 (20分)
        - 红线扣分 (最多-10分)

        修改配置后无需重启系统,下次计算评分时自动生效。
        """)

    with tabs[1]:
        st.markdown("### 数据管理")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 数据库状态")

            # TODO: 从数据库获取统计信息
            st.metric("原始数据记录", "待实现")
            st.metric("计算指标记录", "待实现")
            st.metric("评分记录", "待实现")
            st.metric("回测记录", "待实现")

        with col2:
            st.markdown("#### 操作")

            if st.button("🔄 刷新统计"):
                st.info("刷新成功")

            if st.button("🗑️ 清理缓存"):
                st.warning("此操作不可恢复,请谨慎操作")

            if st.button("📥 导出配置"):
                st.info("导出配置到 data/exports/")

    with tabs[2]:
        st.markdown("### 调度器配置")

        config = get_config()
        scheduler_config = config.get('scheduler', {})

        st.markdown("#### 当前配置")

        st.json({
            "enabled": scheduler_config.get('enabled', False),
            "timezone": scheduler_config.get('timezone', 'Asia/Shanghai'),
            "quarterly_data": scheduler_config.get('quarterly_data', {}),
            "monthly_data": scheduler_config.get('monthly_data', {}),
            "weekly_data": scheduler_config.get('weekly_data', {}),
            "annual_data": scheduler_config.get('annual_data', {}),
        })

        st.info("修改调度配置请编辑 `config/config.yaml` 文件")

    with tabs[3]:
        st.markdown("### 系统信息")

        config = get_config()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 应用信息")
            st.text(f"应用名称: {config.get('app', {}).get('name', 'Industry Screener')}")
            st.text(f"版本: {config.get('app', {}).get('version', '1.0.0')}")
            st.text(f"环境: {config.get('app', {}).get('debug', False) and 'Development' or 'Production'}")

        with col2:
            st.markdown("#### 技术栈")
            st.text("Python: 3.10+")
            st.text("Database: MySQL 8.0+")
            st.text("ORM: SQLAlchemy 2.0+")
            st.text("UI: Streamlit")

        st.markdown("---")

        st.markdown("#### 支持与帮助")
        st.markdown("""
        - 📖 [部署文档](../docs/deployment_guide.md)
        - 📋 [技术设计文档](../docs/技术设计文档.md)
        - 🐛 [报告问题](https://github.com/your/repo/issues)
        """)
