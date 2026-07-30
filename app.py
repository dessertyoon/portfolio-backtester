import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. 페이지 기본 설정 및 사용자 보유 종목 DB
# ---------------------------------------------------------
st.set_page_config(page_title="내 포트폴리오 백테스터", layout="wide")
st.title("📊 내 보유 종목 백테스터 (적립식 투자 & 리밸런싱)")
st.caption("현재 계좌에 담고 계신 종목들을 바탕으로 과거 성과와 추가 납입 시뮬레이션을 수행합니다.")

# 사용자 보유 종목 데이터베이스 (이미지 기준)
STOCK_DATABASE = {
    "KIWOOM 미국S&P500모멘텀": "487950.KS",          # 야후 파이낸스 티커 확인 필요시 직접 수정 가능
    "KODEX 미국나스닥100": "441680.KS",
    "KODEX 미국AI광통신네트워크": "486330.KS",       # 야후 파이낸스 티커 확인 필요시 직접 수정 가능
    "ACE 미국S&P500": "368590.KS",
    "TIGER 미국테크TOP10 INDXX": "381170.KS",
    "ACE 미국배당퀄리티": "480410.KS",              # 야후 파이낸스 티커 확인 필요시 직접 수정 가능
    "PLUS 고배당주": "294200.KS",
    "TIGER 은행고배당플러스TOP10": "458170.KS",
    "TIGER 반도체TOP10": "446770.KS"
}

# ---------------------------------------------------------
# 2. 사이드바 - 사용자 입력창
# ---------------------------------------------------------
st.sidebar.header("⚙️ 포트폴리오 설정")

# (1) 보유 종목 선택
selected_display_names = st.sidebar.multiselect(
    "🔍 백테스트할 보유 종목 선택",
    options=list(STOCK_DATABASE.keys()),
    default=list(STOCK_DATABASE.keys())[:5] # 기본적으로 상위 5개 선택
)

selected_tickers = [STOCK_DATABASE[name] for name in selected_display_names]

manual_input = st.sidebar.text_input("➕ 기타 티커 직접 추가 (필요시)", value="")
manual_tickers = [t.strip().upper() for t in manual_input.split(",") if t.strip()]

all_tickers = list(dict.fromkeys(selected_tickers + manual_tickers))

if not all_tickers:
    st.sidebar.warning("최소 1개 이상의 종목을 선택해 주세요.")

# (2) 종목별 비중 입력
weights = []
st.sidebar.subheader("⚖️ 종목별 비중 (%)")
default_weight = round(100 / len(all_tickers), 1) if all_tickers else 0.0

ticker_to_label = {v: k for k, v in STOCK_DATABASE.items()}

for ticker in all_tickers:
    label = ticker_to_label.get(ticker, ticker)
    w = st.sidebar.number_input(
        f"{label} 비중 (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=default_weight, 
        step=5.0,
        key=f"weight_{ticker}"
    )
    weights.append(w / 100.0)

total_weight = sum(weights)
if abs(total_weight - 1.0) > 0.001:
    st.sidebar.error(f"⚠️ 비중의 합이 100%가 되어야 합니다. (현재: {total_weight*100:.1f}%)")

# (3) 투자 금액 및 리밸런싱/추가 납입 조건
st.sidebar.subheader("💵 투자 및 리밸런싱 옵션")
initial_capital = st.sidebar.number_input("초기 투자금 (원/$)", value=8000000, step=1000000)

rebalance_freq = st.sidebar.selectbox(
    "리밸런싱 주기", 
    ["월간 (Monthly)", "분기 (Quarterly)", "연간 (Annually)", "리밸런싱 안함 (No Rebalance)"]
)

add_cash = st.sidebar.number_input(
    "리밸런싱 회차당 추가 납입금 (원/$)", 
    value=1000000, 
    step=100000,
    help="선택한 리밸런싱 주기마다 포트폴리오에 새로 투입되는 추가 투자금입니다."
)

years = st.sidebar.slider("백테스트 기간 (년)", min_value=1, max_value=10, value=3)

# ---------------------------------------------------------
# 3. 백테스트 연산
# ---------------------------------------------------------
if st.sidebar.button("🚀 백테스트 실행", type="primary"):
    if not all_tickers:
        st.error("종목을 선택해 주세요.")
    elif abs(total_weight - 1.0) > 0.001:
        st.error("종목 비중의 합을 100%로 맞춘 후 다시 실행해 주세요.")
    else:
        with st.spinner("과거 주가 데이터를 분석 중입니다..."):
            end_date = datetime.today()
            start_date = end_date - timedelta(days=int(years * 365.25))

            raw_data = yf.download(all_tickers, start=start_date, end=end_date)['Close']
            
            if isinstance(raw_data, pd.Series):
                raw_data = raw_data.to_frame(name=all_tickers[0])

            data = raw_data.ffill().bfill().dropna()

            if data.empty or len(data) < 10:
                st.error("데이터가 부족하거나 일부 신규 상장 종목의 과거 데이터가 없을 수 있습니다. 기간을 짧게 설정하거나 데이터를 확인해 주세요.")
            else:
                daily_returns = data.pct_change().fillna(0)
                dates = data.index

                freq_map = {
                    "월간 (Monthly)": "ME",
                    "분기 (Quarterly)": "QE",
                    "연간 (Annually)": "YE",
                    "리밸런싱 안함 (No Rebalance)": None
                }
                code_freq = freq_map[rebalance_freq]

                portfolio_series = pd.Series(index=dates, dtype=float)
                total_invested_series = pd.Series(index=dates, dtype=float)

                rebalance_dates = set(data.resample(code_freq).first().index) if code_freq else set()

                asset_values = initial_capital * np.array(weights)
                current_invested = initial_capital

                for i in range(len(dates)):
                    date = dates[i]
                    
                    if i > 0:
                        ret = daily_returns.iloc[i].values
                        asset_values = asset_values * (1 + ret)

                    if date in rebalance_dates and i > 0:
                        current_invested += add_cash
                        total_val_with_cash = np.sum(asset_values) + add_cash
                        asset_values = total_val_with_cash * np.array(weights)

                    portfolio_series.iloc[i] = np.sum(asset_values)
                    total_invested_series.iloc[i] = current_invested

                # ---------------------------------------------------------
                # 4. 성과 지표 계산
                # ---------------------------------------------------------
                final_val = portfolio_series.iloc[-1]
                total_invested = total_invested_series.iloc[-1]
                total_profit = final_val - total_invested
                total_return = (total_profit / total_invested) * 100

                actual_years = (dates[-1] - dates[0]).days / 365.25
                cagr = (((final_val / total_invested) ** (1 / max(actual_years, 0.1))) - 1) * 100

                peak = portfolio_series.cummax()
                drawdown = (portfolio_series - peak) / peak
                mdd = drawdown.min() * 100

                # ---------------------------------------------------------
                # 5. UI 출력
                # ---------------------------------------------------------
                st.info(f"📅 실제 백테스트 기간: **{dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}** (약 {actual_years:.1f}년)")

                st.markdown("### 📌 성과 요약")
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("총 투입 원금", f"{total_invested:,.0f}")
                col2.metric("최종 평가 금액", f"{final_val:,.0f}")
                col3.metric("순수익금", f"{total_profit:+,.0f}")
                col4.metric("원금 대비 수익률", f"{total_return:+.2f}%")
                col5.metric("MDD (최대 낙폭)", f"{mdd:.2f}%", delta_color="inverse")

                st.markdown("### 📈 자산 성장 및 원금 추이")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=portfolio_series.index, 
                    y=portfolio_series.values, 
                    mode='lines', 
                    name='포트폴리오 평가금',
                    line=dict(color='#1f77b4', width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=total_invested_series.index, 
                    y=total_invested_series.values, 
                    mode='lines', 
                    name='누적 투입 원금',
                    line=dict(color='#7f7f7f', width=2, dash='dash')
                ))
                fig.update_layout(
                    xaxis_title="날짜", 
                    yaxis_title="금액", 
                    hovermode="x unified", 
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 📉 하락폭 (Drawdown)")
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(
                    x=drawdown.index, 
                    y=drawdown.values * 100, 
                    mode='lines', 
                    name='Drawdown',
                    fill='tozeroy',
                    line=dict(color='#d62728', width=1)
                ))
                fig_dd.update_layout(xaxis_title="날짜", yaxis_title="낙폭 (%)", hovermode="x unified", template="plotly_white")
                st.plotly_chart(fig_dd, use_container_width=True)