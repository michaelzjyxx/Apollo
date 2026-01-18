"""
行业详情页面
"""

import streamlit as st

from ...data import get_db_manager
from ...utils import SHENWAN_L1_INDUSTRIES


def show():
    """显示行业详情页面"""
    st.title("🔍 行业详情")

    # 选择行业
    industry_name = st.selectbox(
        "选择行业",
        options=list(SHENWAN_L1_INDUSTRIES.values()),
    )

    if industry_name:
        st.markdown(f"### {industry_name} - 详细信息")

        # TODO: 从数据库获取行业详细数据
        st.info("行业详情页面开发中...")

        tabs = st.tabs(["📊 评分历史", "📈 指标趋势", "🏢 成分股", "📝 定性分析"])

        with tabs[0]:
            st.markdown("#### 评分历史")
            st.info("显示该行业的历史评分趋势...")

        with tabs[1]:
            st.markdown("#### 指标趋势")
            st.info("显示23个关键指标的历史趋势...")

        with tabs[2]:
            st.markdown("#### 成分股列表")
            st.info("显示该行业的成分股及其权重...")

        with tabs[3]:
            st.markdown("#### 定性分析")

            db = get_db_manager()
            with db.get_session() as session:
                from ...data import QualitativeScoreRepository

                repo = QualitativeScoreRepository(session)

                # 获取行业代码
                industry_code = [code for code, name in SHENWAN_L1_INDUSTRIES.items() if name == industry_name][0]

                qual = repo.get_by_industry_code(industry_code)

                if qual:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric("政策环境", f"{qual.policy_score}/5")
                        st.caption(qual.policy_reason)

                        st.metric("商业模式", f"{qual.business_model_score}/5")
                        st.caption(qual.business_model_reason)

                    with col2:
                        st.metric("进入壁垒", f"{qual.barrier_score}/5")
                        st.caption(qual.barrier_reason)

                        st.metric("护城河", f"{qual.moat_score}/5")
                        st.caption(qual.moat_reason)

                    st.info(f"最后审核: {qual.last_review.date()}")
                else:
                    st.warning("未找到定性评分数据")
