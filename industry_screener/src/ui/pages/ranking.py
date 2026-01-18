"""
行业排名页面
"""

import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from ...data import get_db_manager
from ...core import DataService


def show():
    """显示行业排名页面"""
    st.title("📈 行业评分排名")

    db = get_db_manager()
    with db.get_session() as session:
        service = DataService(session)

        # 筛选条件
        col1, col2, col3 = st.columns(3)

        with col1:
            score_date = st.date_input(
                "评分日期",
                value=datetime.now(),
            )

        with col2:
            min_score = st.slider(
                "最低分数",
                min_value=0,
                max_value=100,
                value=60,
                step=5,
            )

        with col3:
            top_n = st.selectbox(
                "显示数量",
                options=[10, 20, 31],
                index=0,
            )

        st.markdown("---")

        # 获取数据
        try:
            top_industries = service.get_top_industries(
                score_date=datetime.combine(score_date, datetime.min.time()),
                n=top_n,
                min_score=min_score if min_score > 0 else None,
            )

            if not top_industries:
                st.warning("未找到符合条件的行业")
                return

            # 转换数据
            data = []
            for score in top_industries:
                # 处理 JSON 字段
                redline_list = []
                if score.redline_triggered:
                    try:
                        redline_list = json.loads(score.redline_triggered) if isinstance(score.redline_triggered, str) else score.redline_triggered
                    except:
                        redline_list = []

                data.append({
                    "排名": score.rank,
                    "行业": score.industry_name,
                    "总分": score.total_score,
                    "定性": score.qualitative_score,
                    "政策": score.policy_score,
                    "商业模式": score.business_model_score,
                    "壁垒": score.barrier_score,
                    "护城河": score.moat_score,
                    "竞争格局": score.competition_score,
                    "盈利能力": score.profitability_score,
                    "成长性": score.growth_score,
                    "现金流": score.cashflow_score,
                    "估值": score.valuation_score,
                    "景气度": score.sentiment_score,
                    "周期位置": score.cycle_score,
                    "红线": "✓" if redline_list and len(redline_list) > 0 else "",
                    "红线扣分": score.redline_penalty,
                })

            df = pd.DataFrame(data)

            # 显示统计信息
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("入选行业数", len(df))

            with col2:
                st.metric("平均分", f"{df['总分'].mean():.1f}")

            with col3:
                st.metric("最高分", f"{df['总分'].max():.1f}")

            with col4:
                triggered_count = df['红线'].str.contains('✓').sum()
                st.metric("红线触发", f"{triggered_count}个")

            st.markdown("---")

            # 评分对比图
            st.markdown("### 📊 评分对比")

            fig = px.bar(
                df,
                x="行业",
                y=["定性", "竞争格局", "盈利能力", "成长性", "现金流", "估值", "景气度", "周期位置"],
                title="各维度评分对比",
                barmode="stack",
            )

            fig.update_layout(
                xaxis_title="",
                yaxis_title="得分",
                height=400,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
            )
            fig.update_xaxes(tickangle=-45)

            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            # 详细表格
            st.markdown("### 📋 详细排名表")

            # 格式化表格
            styled_df = df.style.format({
                '总分': '{:.1f}',
                '定性': '{:.1f}',
                '政策': '{:.0f}',
                '商业模式': '{:.0f}',
                '壁垒': '{:.0f}',
                '护城河': '{:.0f}',
                '竞争格局': '{:.1f}',
                '盈利能力': '{:.1f}',
                '成长性': '{:.1f}',
                '现金流': '{:.1f}',
                '估值': '{:.1f}',
                '景气度': '{:.1f}',
                '周期位置': '{:.1f}',
                '红线扣分': '{:.1f}',
            })

            st.dataframe(styled_df, use_container_width=True, height=600)

            # 选择行业查看详情
            st.markdown("---")
            selected_industry = st.selectbox(
                "选择行业查看详情",
                options=df["行业"].tolist(),
            )

            if selected_industry:
                selected_data = df[df["行业"] == selected_industry].iloc[0]

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"### {selected_industry} - 评分详情")

                    st.metric("总分", f"{selected_data['总分']:.1f}", delta=f"排名 #{selected_data['排名']}")

                    st.markdown("**定性评分 (20分)**")
                    st.progress(selected_data['定性'] / 20)
                    st.caption(f"政策: {selected_data['政策']:.0f}, 商业模式: {selected_data['商业模式']:.0f}, "
                              f"壁垒: {selected_data['壁垒']:.0f}, 护城河: {selected_data['护城河']:.0f}")

                with col2:
                    st.markdown("### 定量评分")

                    metrics = {
                        "竞争格局": (selected_data['竞争格局'], 15),
                        "盈利能力": (selected_data['盈利能力'], 15),
                        "成长性": (selected_data['成长性'], 10),
                        "现金流": (selected_data['现金流'], 10),
                        "估值": (selected_data['估值'], 10),
                        "景气度": (selected_data['景气度'], 5),
                        "周期位置": (selected_data['周期位置'], 5),
                    }

                    for name, (score, total) in metrics.items():
                        st.markdown(f"**{name}** ({total}分)")
                        st.progress(score / total if total > 0 else 0)
                        st.caption(f"{score:.1f} / {total}")

        except Exception as e:
            st.error(f"加载数据失败: {e}")
            st.exception(e)
