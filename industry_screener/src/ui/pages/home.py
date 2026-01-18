"""
首页概览页面
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ...data import get_db_manager
from ...core import DataService


def show():
    """显示首页概览"""
    st.title("🏠 A股行业筛选系统 - 首页概览")

    # 获取数据
    db = get_db_manager()
    with db.get_session() as session:
        service = DataService(session)

        # 选择日期
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 行业评分概览")
        with col2:
            # TODO: 从数据库获取可用日期列表
            score_date = st.date_input(
                "评分日期",
                value=datetime.now(),
            )

        # 获取 Top 行业
        try:
            top_industries = service.get_top_industries(
                score_date=datetime.combine(score_date, datetime.min.time()),
                n=31,  # 获取所有行业
            )

            if not top_industries:
                st.warning("暂无评分数据,请先运行评分计算")
                return

            # 数据转换
            df = pd.DataFrame([{
                "行业": score.industry_name,
                "总分": score.total_score or 0,
                "排名": score.rank or 0,
                "定性": score.qualitative_score or 0,
                "竞争": score.competition_score or 0,
                "盈利": score.profitability_score or 0,
                "成长": score.growth_score or 0,
                "现金流": score.cashflow_score or 0,
                "估值": score.valuation_score or 0,
                "景气": score.sentiment_score or 0,
                "周期": score.cycle_score or 0,
                "红线扣分": score.redline_penalty or 0,
            } for score in top_industries])

            # Top 10 卡片
            st.markdown("### 🏆 TOP 10 行业")

            top_10 = df.head(10)

            cols = st.columns(5)
            for i, row in top_10.iterrows():
                col_idx = i % 5
                with cols[col_idx]:
                    medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"

                    st.metric(
                        label=f"{medal} {row['行业']}",
                        value=f"{row['总分']:.1f}分",
                        delta=f"排名 {row['排名']}",
                    )

            st.markdown("---")

            # 评分分布
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 📊 行业评分分布")

                # 柱状图
                fig = px.bar(
                    df,
                    x="行业",
                    y="总分",
                    color="总分",
                    color_continuous_scale="RdYlGn",
                    title="所有行业评分对比",
                )
                fig.update_layout(
                    xaxis_title="",
                    yaxis_title="总分",
                    showlegend=False,
                    height=400,
                )
                fig.update_xaxes(tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("### 🎯 评分维度分析(TOP 10)")

                # 雷达图 - 显示TOP 3的各维度评分
                top_3 = df.head(3)

                fig = go.Figure()

                categories = ["定性", "竞争", "盈利", "成长", "现金流", "估值", "景气", "周期"]

                for _, row in top_3.iterrows():
                    values = [
                        row["定性"],
                        row["竞争"],
                        row["盈利"],
                        row["成长"],
                        row["现金流"],
                        row["估值"],
                        row["景气"],
                        row["周期"],
                    ]
                    values.append(values[0])  # 闭合

                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=categories + [categories[0]],
                        name=row["行业"],
                        fill='toself',
                    ))

                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 20])),
                    showlegend=True,
                    height=400,
                )

                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            # 详细表格
            st.markdown("### 📋 详细评分表")

            # 添加颜色映射
            def color_score(val):
                if val >= 80:
                    return 'background-color: #d4edda'
                elif val >= 60:
                    return 'background-color: #fff3cd'
                else:
                    return 'background-color: #f8d7da'

            styled_df = df.style.map(
                color_score,
                subset=['总分']
            ).format({
                '总分': '{:.1f}',
                '定性': '{:.1f}',
                '竞争': '{:.1f}',
                '盈利': '{:.1f}',
                '成长': '{:.1f}',
                '现金流': '{:.1f}',
                '估值': '{:.1f}',
                '景气': '{:.1f}',
                '周期': '{:.1f}',
                '红线扣分': '{:.1f}',
            })

            st.dataframe(styled_df, use_container_width=True, height=400)

            # 导出功能
            st.download_button(
                label="📥 导出CSV",
                data=df.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"industry_scores_{score_date}.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"加载数据失败: {e}")
            st.exception(e)
