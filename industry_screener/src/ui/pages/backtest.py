"""
回测结果页面
"""

import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ...data import BacktestResultRepository, get_db_manager


def show():
    """显示回测结果页面"""
    st.title("💼 回测结果")

    db = get_db_manager()
    with db.get_session() as session:
        repo = BacktestResultRepository(session)

        # 获取所有回测
        results = repo.get_all(limit=50)

        if not results:
            st.info("暂无回测结果,请先运行回测")

            st.markdown("### 如何运行回测?")
            st.code("""
python main.py backtest run \\
    --strategy dynamic_adjustment \\
    --start-date 2020-01-01 \\
    --end-date 2024-12-31 \\
    --top-n 10 \\
    --min-score 70
            """, language="bash")
            return

        # 选择回测
        backtest_names = [r.backtest_name for r in results]
        selected_name = st.selectbox(
            "选择回测",
            options=backtest_names,
        )

        if not selected_name:
            return

        # 获取选中的回测
        selected = next((r for r in results if r.backtest_name == selected_name), None)

        if not selected:
            return

        st.markdown("---")

        # 基本信息
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**策略名称**")
            st.info(selected.strategy_name)

        with col2:
            st.markdown("**回测期间**")
            st.info(f"{selected.start_date.date()} ~ {selected.end_date.date()}")

        with col3:
            st.markdown("**基准指数**")
            st.info(selected.benchmark_code)

        st.markdown("---")

        # 绩效指标
        st.markdown("### 📊 绩效指标")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "总收益",
                f"{selected.total_return:.2f}%",
                delta=f"vs 基准 {selected.excess_return:.2f}%",
            )

        with col2:
            st.metric(
                "年化收益",
                f"{selected.annual_return:.2f}%",
            )

        with col3:
            st.metric(
                "夏普比率",
                f"{selected.sharpe_ratio:.2f}",
            )

        with col4:
            st.metric(
                "最大回撤",
                f"{selected.max_drawdown:.2f}%",
                delta_color="inverse",
            )

        col5, col6, col7, col8 = st.columns(4)

        with col5:
            st.metric("胜率", f"{selected.win_rate:.2f}%")

        with col6:
            st.metric("基准收益", f"{selected.benchmark_return:.2f}%")

        with col7:
            trades_list = []
            if selected.trades:
                try:
                    trades_list = json.loads(selected.trades) if isinstance(selected.trades, str) else selected.trades
                except:
                    trades_list = []
            st.metric("交易次数", f"{len(trades_list)}")

        with col8:
            # 计算换手率
            st.metric("参数", "动态调整")

        st.markdown("---")

        # 收益曲线
        daily_returns_data = []
        if selected.daily_returns:
            try:
                daily_returns_data = json.loads(selected.daily_returns) if isinstance(selected.daily_returns, str) else selected.daily_returns
            except:
                daily_returns_data = []

        if daily_returns_data:
            st.markdown("### 📈 收益曲线")

            df = pd.DataFrame(daily_returns_data)
            df['date'] = pd.to_datetime(df['date'])

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['cumulative_return'] * 100,
                mode='lines',
                name='策略收益',
                line=dict(color='blue', width=2),
            ))

            fig.update_layout(
                title='累计收益率',
                xaxis_title='日期',
                yaxis_title='累计收益率 (%)',
                hovermode='x unified',
                height=400,
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # 持仓记录
        holdings_data = []
        if selected.holdings:
            try:
                holdings_data = json.loads(selected.holdings) if isinstance(selected.holdings, str) else selected.holdings
            except:
                holdings_data = []

        if holdings_data:
            st.markdown("### 📋 持仓记录")

            holdings_df = pd.DataFrame([
                {
                    "调仓日期": h['date'],
                    "持仓行业数": len(h.get('industries', [])),
                    "行业列表": ", ".join([ind['industry_name'] for ind in h.get('industries', [])[:5]]) +
                                ("..." if len(h.get('industries', [])) > 5 else ""),
                }
                for h in holdings_data
            ])

            st.dataframe(holdings_df, use_container_width=True)

        # 交易记录
        trades_data = []
        if selected.trades:
            try:
                trades_data = json.loads(selected.trades) if isinstance(selected.trades, str) else selected.trades
            except:
                trades_data = []

        if trades_data:
            st.markdown("### 💱 交易记录")

            trades_df = pd.DataFrame(trades_data)

            col1, col2 = st.columns(2)

            with col1:
                buy_trades = trades_df[trades_df['action'] == 'buy']
                st.markdown(f"**买入记录** ({len(buy_trades)}笔)")
                if len(buy_trades) > 0:
                    st.dataframe(
                        buy_trades[['date', 'industry_name', 'score']].head(10),
                        use_container_width=True,
                    )

            with col2:
                sell_trades = trades_df[trades_df['action'] == 'sell']
                st.markdown(f"**卖出记录** ({len(sell_trades)}笔)")
                if len(sell_trades) > 0:
                    st.dataframe(
                        sell_trades[['date', 'industry_name', 'reason']].head(10),
                        use_container_width=True,
                    )
