"""
红线监控页面
"""

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from ...data import get_db_manager
from ...core import DataService


def show():
    """显示红线监控页面"""
    st.title("⚠️ 红线监控")

    st.markdown("""
    ### 红线规则

    触发以下任一条件,扣10分:

    1. **毛利率连续下滑**: 连续4季度下滑 > 5pct
    2. **收入连续下滑**: 连续2季度下滑 > 20%
    3. **估值极端高位**: PE或PB历史95%分位以上维持1月
    4. **资金持续流出**: 北向+主力资金连续8周流出 > 100亿
    """)

    st.markdown("---")

    # 获取触发红线的行业
    db = get_db_manager()
    with db.get_session() as session:
        service = DataService(session)

        score_date = st.date_input(
            "查询日期",
            value=datetime.now(),
        )

        try:
            all_industries = service.get_top_industries(
                score_date=datetime.combine(score_date, datetime.min.time()),
                n=31,
            )

            # 筛选触发红线的行业
            triggered = []
            safe = []

            for score in all_industries:
                redline_list = []
                if score.redline_triggered:
                    try:
                        redline_list = json.loads(score.redline_triggered) if isinstance(score.redline_triggered, str) else score.redline_triggered
                    except:
                        redline_list = []

                if redline_list and len(redline_list) > 0:
                    triggered.append(score)
                else:
                    safe.append(score)

            # 统计卡片
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "触发红线",
                    f"{len(triggered)}个行业",
                    delta=f"-{len(triggered) * 10}分",
                    delta_color="inverse",
                )

            with col2:
                st.metric(
                    "安全行业",
                    f"{len(safe)}个",
                    delta="正常",
                    delta_color="normal",
                )

            with col3:
                trigger_rate = len(triggered) / len(all_industries) * 100 if all_industries else 0
                st.metric(
                    "触发率",
                    f"{trigger_rate:.1f}%",
                )

            st.markdown("---")

            if triggered:
                st.markdown("### 🚨 已触发红线的行业")

                data = []
                for score in triggered:
                    redlines = []
                    if score.redline_triggered:
                        try:
                            redlines = json.loads(score.redline_triggered) if isinstance(score.redline_triggered, str) else score.redline_triggered
                        except:
                            redlines = []

                    data.append({
                        "行业": score.industry_name,
                        "总分": score.total_score,
                        "扣分": score.redline_penalty,
                        "触发红线": ", ".join(redlines) if redlines else "",
                        "排名": score.rank,
                    })

                df = pd.DataFrame(data)

                st.dataframe(
                    df.style.format({
                        '总分': '{:.1f}',
                        '扣分': '{:.1f}',
                    }),
                    use_container_width=True,
                )
            else:
                st.success("✅ 当前没有行业触发红线")

            st.markdown("---")

            # 安全行业
            if safe:
                st.markdown("### ✅ 安全行业(未触发红线)")

                with st.expander(f"查看 {len(safe)} 个安全行业"):
                    safe_data = [{
                        "排名": score.rank,
                        "行业": score.industry_name,
                        "总分": score.total_score,
                    } for score in safe]

                    safe_df = pd.DataFrame(safe_data)
                    st.dataframe(
                        safe_df.style.format({'总分': '{:.1f}'}),
                        use_container_width=True,
                    )

        except Exception as e:
            st.error(f"加载数据失败: {e}")
