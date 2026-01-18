"""
可重用UI组件
"""

import plotly.graph_objects as go
import streamlit as st


def score_gauge(score: float, title: str, max_score: float = 100):
    """
    评分仪表盘组件

    Args:
        score: 分数
        title: 标题
        max_score: 最大分数
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        delta={'reference': max_score * 0.7},  # 70分为参考线
        gauge={
            'axis': {'range': [None, max_score]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_score * 0.6], 'color': "lightgray"},
                {'range': [max_score * 0.6, max_score * 0.8], 'color': "gray"},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_score * 0.9,
            },
        },
    ))

    fig.update_layout(height=250)
    st.plotly_chart(fig, use_container_width=True)


def industry_card(industry_name: str, score: float, rank: int, change: str = ""):
    """
    行业卡片组件

    Args:
        industry_name: 行业名称
        score: 评分
        rank: 排名
        change: 变化描述
    """
    with st.container():
        st.markdown(f"""
        <div style="
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid #ddd;
            background-color: #f9f9f9;
        ">
            <h4 style="margin: 0;">{industry_name}</h4>
            <p style="font-size: 2rem; margin: 0.5rem 0; color: #0066cc;">{score:.1f}</p>
            <p style="margin: 0; color: #666;">排名 #{rank} {change}</p>
        </div>
        """, unsafe_allow_html=True)


def metric_progress(label: str, value: float, max_value: float, unit: str = ""):
    """
    指标进度条组件

    Args:
        label: 标签
        value: 当前值
        max_value: 最大值
        unit: 单位
    """
    progress = value / max_value if max_value > 0 else 0
    progress = min(max(progress, 0), 1)  # 限制在0-1之间

    st.markdown(f"**{label}**")
    st.progress(progress)
    st.caption(f"{value}{unit} / {max_value}{unit}")


def data_quality_indicator(completeness: float, timeliness: int):
    """
    数据质量指示器

    Args:
        completeness: 完整性(0-1)
        timeliness: 时效性(天数)
    """
    col1, col2 = st.columns(2)

    with col1:
        if completeness >= 0.9:
            st.success(f"✅ 数据完整性: {completeness*100:.0f}%")
        elif completeness >= 0.7:
            st.warning(f"⚠️ 数据完整性: {completeness*100:.0f}%")
        else:
            st.error(f"❌ 数据完整性: {completeness*100:.0f}%")

    with col2:
        if timeliness <= 7:
            st.success(f"✅ 数据时效: {timeliness}天前")
        elif timeliness <= 30:
            st.warning(f"⚠️ 数据时效: {timeliness}天前")
        else:
            st.error(f"❌ 数据时效: {timeliness}天前")
