import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. 페이지 기본 설정 및 제목
# ---------------------------------------------------------
st.set_page_config(page_title="미국 주식 포트폴리오 백테스터", layout="wide")
st.title("📊 미국 주식 포트폴리오 백테스터")
st.caption("과거 20년 데이터를 바탕으로 포트폴리오 비중 및 리밸런싱 수익률을 시뮬레이션합니다.")

# ---------------------------------------------------------
# 2. 사이드바 - 사용자 입력창 구성
# ---------------------------------------------------------
st.sidebar.header("⚙️ 포트폴리오 설정")

# (1) 티커 입력
tickers_input = st.sidebar.text_input("종목 티커 (쉼표로 구분)", "AAPL, MSFT, TLT, GLD")
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# (2) 종목별 비중 입력
weights = []
st.sidebar.subheader("⚖️ 종목별 비중 (%)")
default_weight = round(100 / len(tickers), 1) if tickers else 0.0

for ticker in tickers:
    w = st.sidebar.number_input(
        f"{ticker} 비중 (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=default_weight, 
        step=5.0
    )
    weights.append(w / 100.0)

# 비중 합계 검증 및 경고
total_weight = sum(weights)
if abs(total_weight - 1.0) > 0.001:
    st.sidebar.error(f"⚠️ 비중의 합이 100%가 되어야 합니다. (현재: {total_weight*100:.1f}%)")

# (3) 백테스트 옵션
years = st.sidebar.slider("백테스트 기간 (년)", min_value=1, max_value=20, value=20)
rebalance_freq = st.sidebar.selectbox(
    "리밸런싱 주기", 
    ["월간 (Monthly)", "분기 (Quarterly)", "연간 (Annually)", "리밸런싱 안함 (No Rebalance)"]
)
initial_capital = st.sidebar.number_input("초기 투자금 ($)", value=10000, step=1000)

# ---------------------------------------------------------
# 3. 백테스트 실행 버튼 및 핵심 연산 로직
# ---------------------------------------------------------
if st.sidebar.button("🚀 백테스트 실행", type="primary"):
    if abs(total_weight - 1.0) > 0.001:
        st.error("종목 비중의 합을 100%로 맞춘 후 다시 실행해 주세요.")
    else:
        with st.spinner("야후 파이낸스에서 데이터를 불러와 백테스트를 수행 중입니다..."):
            # 날짜 범위 설정
            end_date = datetime.today()
            start_date = end_date - timedelta(days=int(years * 365.25))

            # 야후 파이낸스 주가 데이터 다운로드 (종가 기준)
            raw_data = yf.download(tickers, start=start_date, end=end_date)['Close']
            
            # 단일 종목 입력 시 Series -> DataFrame 변환 처리
            if isinstance(raw_data, pd.Series):
                raw_data = raw_data.to_frame(name=tickers[0])

            # 결측치 제거
            data = raw_data.dropna()

            if data.empty:
                st.error("주가 데이터를 불러오지 못했습니다. 입력한 티커명이나 상장 기간을 확인해 주세요.")
            else:
                # 일별 변동률(수익률) 계산
                daily_returns = data.pct_change().fillna(0)
                dates = data.index

                # 리밸런싱 주기 매핑
                freq_map = {
                    "월간 (Monthly)": "ME",
                    "분기 (Quarterly)": "QE",
                    "연간 (Annually)": "YE",
                    "리밸런싱 안함 (No Rebalance)": None
                }
                code_freq = freq_map[rebalance_freq]

                # 시뮬레이션 계산
                portfolio_series = pd.Series(index=dates, dtype=float)

                if code_freq is None:
                    # [A] Buy & Hold (리밸런싱 안 함)
                    normalized_data = data / data.iloc[0]
                    weighted_data = normalized_data * weights
                    portfolio_series = weighted_data.sum(axis=1) * initial_capital
                else:
                    # [B] 주기적 리밸런싱 실행
                    rebalance_dates = set(data.resample(code_freq).first().index)
                    asset_values = initial_capital * np.array(weights)

                    for i in range(len(dates)):
                        date = dates[i]
                        
                        # 일별 주가 변동 반영
                        if i > 0:
                            ret = daily_returns.iloc[i].values
                            asset_values = asset_values * (1 + ret)

                        # 리밸런싱 날짜인 경우 지정된 비중으로 재배분
                        if date in rebalance_dates and i > 0:
                            total_val = np.sum(asset_values)
                            asset_values = total_val * np.array(weights)

                        portfolio_series.iloc[i] = np.sum(asset_values)

                # ---------------------------------------------------------
                # 4. 결과 지표 계산
                # ---------------------------------------------------------
                final_val = portfolio_series.iloc[-1]
                total_return = ((final_val / initial_capital) - 1) * 100
                actual_years = (dates[-1] - dates[0]).days / 365.25
                cagr = (((final_val / initial_capital) ** (1 / actual_years)) - 1) * 100

                # MDD (최대 낙폭) 계산
                peak = portfolio_series.cummax()
                drawdown = (portfolio_series - peak) / peak
                mdd = drawdown.min() * 100

                # ---------------------------------------------------------
                # 5. UI 시각화 및 결과 출력
                # ---------------------------------------------------------
                # 요약 지표 카드로 표시
                st.markdown("### 📌 백테스트 성과 요약")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("최종 자산 가치", f"${final_val:,.0f}")
                col2.metric("누적 수익률", f"{total_return:+.2f}%")
                col3.metric("CAGR (연평균 수익률)", f"{cagr:.2f}%")
                col4.metric("MDD (최대 낙폭)", f"{mdd:.2f}%", delta_color="inverse")

                # plotly 상호작용 차트
                st.markdown("### 📈 자산 성장 추이")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=portfolio_series.index, 
                    y=portfolio_series.values, 
                    mode='lines', 
                    name='Portfolio',
                    line=dict(color='#1f77b4', width=2)
                ))
                fig.update_layout(
                    xaxis_title="날짜",
                    yaxis_title="자산 가치 ($)",
                    hovermode="x unified",
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)

                # 낙폭 차트 (Drawdown)
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
                fig_dd.update_layout(
                    xaxis_title="날짜",
                    yaxis_title="낙폭 (%)",
                    hovermode="x unified",
                    template="plotly_white"
                )
                st.plotly_chart(fig_dd, use_container_width=True)