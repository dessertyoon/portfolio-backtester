import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. 페이지 기본 설정 및 사전 정의 데이터 (ETF 프리셋)
# ---------------------------------------------------------
st.set_page_config(page_title="글로벌 & 연금저축 포트폴리오 백테스터", layout="wide")
st.title("📊 포트폴리오 백테스터 (미국 ETF & 연금저축 ETF)")
st.caption("미국 직투 ETF 및 한국 연금저축펀드 가능 ETF를 조합하여 과거 리밸런싱 성과를 시뮬레이션합니다.")

# 연금저축 및 대표 ETF 프리셋 (이름 -> 야후파이낸스 티커)
ETF_PRESETS = {
    # --- 한국 연금저축펀드 매수 가능 주요 ETF ---
    "TIGER 미국S&P500 (연금저축)": "360750.KS",
    "TIGER 미국나스닥100 (연금저축)": "133690.KS",
    "TIGER 미국배당다우존스 (연금저축)": "458730.KS",
    "TIGER 미국30년스트립액티브 (연금저축/채권)": "472150.KS",
    "KODEX 미국S&P500TR (연금저축)": "379800.KS",
    "ACE 미국30년국채액티브 (연금저축/채권)": "453850.KS",
    "KODEX 200 (국내주식)": "069500.KS",
    "TIGER 골드선물(H) (원자재)": "139320.KS",
    
    # --- 미국 주요 직투 ETF ---
    "SPY (미국 S&P500)": "SPY",
    "QQQ (미국 나스닥100)": "QQQ",
    "SCHD (미국 배당성장)": "SCHD",
    "TLT (미국 20년+ 국채)": "TLT",
    "GLD (금 ETF)": "GLD",
    "VT (전세계 주식)": "VT",
    "VNQ (미국 리츠)": "VNQ",
    "AAPL (애플)": "AAPL",
    "MSFT (마이크로소프트)": "MSFT",
}

# ---------------------------------------------------------
# 2. 사이드바 - 사용자 입력창
# ---------------------------------------------------------
st.sidebar.header("⚙️ 포트폴리오 설정")

# (1) ETF 프리셋 빠른 선택
selected_presets = st.sidebar.multiselect(
    "💡 추천/연금저축 ETF 목록에서 선택",
    options=list(ETF_PRESETS.keys()),
    default=[
        "TIGER 미국S&P500 (연금저축)", 
        "TIGER 미국배당다우존스 (연금저축)", 
        "ACE 미국30년국채액티브 (연금저축/채권)"
    ]
)

# 프리셋 선택에 따른 티커 추출
preset_tickers = [ETF_PRESETS[name] for name in selected_presets]

# (2) 직접 개별 티커 추가 입력 (쉼표 구분)
manual_input = st.sidebar.text_input(
    "➕ 기타 티커 직접 입력 (예: NVDA, 005930.KS)", 
    help="한국 주식/ETF는 숫 뒤에 .KS를 붙여주세요 (예: 삼성전자 005930.KS)"
)
manual_tickers = [t.strip().upper() for t in manual_input.split(",") if t.strip()]

# 최종 통합 티커 리스트
all_tickers = list(dict.fromkeys(preset_tickers + manual_tickers))

if not all_tickers:
    st.sidebar.warning("최소 1개 이상의 종목을 선택하거나 입력해 주세요.")

# (3) 종목별 비중 입력
weights = []
st.sidebar.subheader("⚖️ 종목별 비중 (%)")
default_weight = round(100 / len(all_tickers), 1) if all_tickers else 0.0

# 프리셋 역매핑 (화면 표시용 이름)
ticker_to_name = {v: k for k, v in ETF_PRESETS.items()}

for ticker in all_tickers:
    display_name = ticker_to_name.get(ticker, ticker)
    w = st.sidebar.number_input(
        f"{display_name} 비중 (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=default_weight, 
        step=5.0,
        key=f"weight_{ticker}"
    )
    weights.append(w / 100.0)

# 비중 합계 검증
total_weight = sum(weights)
if abs(total_weight - 1.0) > 0.001:
    st.sidebar.error(f"⚠️ 비중의 합이 100%가 되어야 합니다. (현재: {total_weight*100:.1f}%)")

# (4) 백테스트 기간 및 조건
years = st.sidebar.slider("백테스트 기간 (년)", min_value=1, max_value=20, value=5)
st.sidebar.caption("※ 국내 연금저축 ETF는 상장 기간이 짧아 백테스트 기간 설정 시 데이터가 존재하는 기간부터 계산됩니다.")

rebalance_freq = st.sidebar.selectbox(
    "리밸런싱 주기", 
    ["월간 (Monthly)", "분기 (Quarterly)", "연간 (Annually)", "리밸런싱 안함 (No Rebalance)"]
)
initial_capital = st.sidebar.number_input("초기 투자금 (원/달러)", value=10000000, step=1000000)

# ---------------------------------------------------------
# 3. 백테스트 실행 및 계산 로직
# ---------------------------------------------------------
if st.sidebar.button("🚀 백테스트 실행", type="primary"):
    if not all_tickers:
        st.error("종목을 선택해 주세요.")
    elif abs(total_weight - 1.0) > 0.001:
        st.error("종목 비중의 합을 100%로 맞춘 후 다시 실행해 주세요.")
    else:
        with st.spinner("야후 파이낸스에서 데이터를 수집 중입니다..."):
            end_date = datetime.today()
            start_date = end_date - timedelta(days=int(years * 365.25))

            # 야후 파이낸스 주가 데이터 수집
            raw_data = yf.download(all_tickers, start=start_date, end=end_date)['Close']
            
            if isinstance(raw_data, pd.Series):
                raw_data = raw_data.to_frame(name=all_tickers[0])

            # 데이터 결측치 처리 (한국 ETF와 미국 ETF 휴장일 차이 보정)
            data = raw_data.ffill().bfill().dropna()

            if data.empty or len(data) < 10:
                st.error("불러온 주가 데이터가 부족합니다. 상장된 지 얼마 안 된 종목이 포함되어 있거나 기간이 너무 길 수 있습니다.")
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

                if code_freq is None:
                    normalized_data = data / data.iloc[0]
                    weighted_data = normalized_data * weights
                    portfolio_series = weighted_data.sum(axis=1) * initial_capital
                else:
                    rebalance_dates = set(data.resample(code_freq).first().index)
                    asset_values = initial_capital * np.array(weights)

                    for i in range(len(dates)):
                        date = dates[i]
                        if i > 0:
                            ret = daily_returns.iloc[i].values
                            asset_values = asset_values * (1 + ret)

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
                cagr = (((final_val / initial_capital) ** (1 / max(actual_years, 0.1))) - 1) * 100

                peak = portfolio_series.cummax()
                drawdown = (portfolio_series - peak) / peak
                mdd = drawdown.min() * 100

                # ---------------------------------------------------------
                # 5. UI 출력
                # ---------------------------------------------------------
                st.info(f"📅 실제 백테스트 분석 기간: **{dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}** (약 {actual_years:.1f}년)")

                st.markdown("### 📌 백테스트 성과 요약")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("최종 자산 가치", f"{final_val:,.0f}")
                col2.metric("누적 수익률", f"{total_return:+.2f}%")
                col3.metric("CAGR (연평균 수익률)", f"{cagr:.2f}%")
                col4.metric("MDD (최대 낙폭)", f"{mdd:.2f}%", delta_color="inverse")

                # 자산 성장 차트
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
                    yaxis_title="자산 가치",
                    hovermode="x unified",
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)

                # 낙폭 차트
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