import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. 페이지 기본 설정 및 한글 검색용 종목 DB
# ---------------------------------------------------------
st.set_page_config(page_title="글로벌 & 연금저축 포트폴리오 백테스터", layout="wide")
st.title("📊 포트폴리오 백테스터")
st.caption("한글 검색으로 연금저축/미국 ETF를 선택하고 과거 리밸런싱 수익률을 시뮬레이션하세요.")

# 한글 검색 데이터베이스 (표시명: [그룹] 한글명 (티커) -> 야후 파이낸스 티커)
STOCK_DATABASE = {
    # --- 한국 연금저축펀드 가능 대표 ETF ---
    "[연금/국내] TIGER 미국S&P500 (360750)": "360750.KS",
    "[연금/국내] TIGER 미국나스닥100 (133690)": "133690.KS",
    "[연금/국내] TIGER 미국배당다우존스 (458730)": "458730.KS",
    "[연금/국내] TIGER 미국30년스트립액티브 (472150)": "472150.KS",
    "[연금/국내] KODEX 미국S&P500TR (379800)": "379800.KS",
    "[연금/국내] ACE 미국30년국채액티브 (453850)": "453850.KS",
    "[연금/국내] KODEX 200 코스피 (069500)": "069500.KS",
    "[연금/국내] TIGER 골드선물 금 (139320)": "139320.KS",
    "[연금/국내] KODEX 미국달러선물 환율 (261240)": "261240.KS",
    "[국내주식] 삼성전자 (005930)": "005930.KS",
    "[국내주식] SK하이닉스 (000660)": "000660.KS",

    # --- 미국 주요 대표 ETF & 주식 ---
    "[미국ETF] SPY - S&P500 지수": "SPY",
    "[미국ETF] QQQ - 나스닥100 지수": "QQQ",
    "[미국ETF] SCHD - 미국 배당성장": "SCHD",
    "[미국ETF] TLT - 미국 20년+ 장기국채": "TLT",
    "[미국ETF] GLD - 금 현물": "GLD",
    "[미국ETF] VT - 전세계 주식": "VT",
    "[미국ETF] VNQ - 미국 리츠 부동산": "VNQ",
    "[미국ETF] JEPI - 고배당 커버드콜": "JEPI",
    "[미국주식] AAPL - 애플 (Apple)": "AAPL",
    "[미국주식] MSFT - 마이크로소프트 (Microsoft)": "MSFT",
    "[미국주식] NVDA - 엔비디아 (NVIDIA)": "NVDA",
    "[미국주식] TSLA - 테슬라 (Tesla)": "TSLA",
    "[미국주식] AMZN - 아마존 (Amazon)": "AMZN",
    "[미국주식] GOOGL - Alphabet / 구글": "GOOGL"
}

# ---------------------------------------------------------
# 2. 사이드바 - 사용자 입력창 (한글 연관 검색 연동)
# ---------------------------------------------------------
st.sidebar.header("⚙️ 포트폴리오 설정")

# (1) 한글 연관 검색 드롭다운 (st.multiselect)
selected_display_names = st.sidebar.multiselect(
    "🔍 종목 검색 (한글/영어 이름 입력)",
    options=list(STOCK_DATABASE.keys()),
    default=[
        "[연금/국내] TIGER 미국S&P500 (360750)",
        "[연금/국내] TIGER 미국배당다우존스 (458730)",
        "[미국ETF] TLT - 미국 20년+ 장기국채"
    ],
    help="검색창에 '나스닥', 'S&P', '배당', '애플' 등을 치면 관련 종목이 나타납니다."
)

# 선택한 종목들의 실제 티커 추출
selected_tickers = [STOCK_DATABASE[name] for name in selected_display_names]

# (2) 검색에 없는 개별 티커 직접 추가 입력
manual_input = st.sidebar.text_input(
    "➕ 목록에 없는 티커 직접 추가 (예: SOXX, 005380.KS)",
    help="쉼표(,)로 구분해서 입력하세요. 한국 주식/ETF는 끝에 .KS를 붙입니다."
)
manual_tickers = [t.strip().upper() for t in manual_input.split(",") if t.strip()]

# 최종 종목 리스트 (중복 제거)
all_tickers = list(dict.fromkeys(selected_tickers + manual_tickers))

if not all_tickers:
    st.sidebar.warning("최소 1개 이상의 종목을 선택해 주세요.")

# (3) 종목별 비중 입력
weights = []
st.sidebar.subheader("⚖️ 종목별 비중 (%)")
default_weight = round(100 / len(all_tickers), 1) if all_tickers else 0.0

# 화면 표시용 레이블 생성 역매핑
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

# 비중 합계 검증
total_weight = sum(weights)
if abs(total_weight - 1.0) > 0.001:
    st.sidebar.error(f"⚠️ 비중의 합이 100%가 되어야 합니다. (현재: {total_weight*100:.1f}%)")

# (4) 백테스트 기간 및 조건
years = st.sidebar.slider("백테스트 기간 (년)", min_value=1, max_value=20, value=5)
rebalance_freq = st.sidebar.selectbox(
    "리밸런싱 주기", 
    ["월간 (Monthly)", "분기 (Quarterly)", "연간 (Annually)", "리밸런싱 안함 (No Rebalance)"]
)
initial_capital = st.sidebar.number_input("초기 투자금 (원/달러)", value=10000000, step=1000000)

# ---------------------------------------------------------
# 3. 백테스트 연산 및 시각화
# ---------------------------------------------------------
if st.sidebar.button("🚀 백테스트 실행", type="primary"):
    if not all_tickers:
        st.error("종목을 선택해 주세요.")
    elif abs(total_weight - 1.0) > 0.001:
        st.error("종목 비중의 합을 100%로 맞춘 후 다시 실행해 주세요.")
    else:
        with st.spinner("주가 데이터를 분석하고 있습니다..."):
            end_date = datetime.today()
            start_date = end_date - timedelta(days=int(years * 365.25))

            raw_data = yf.download(all_tickers, start=start_date, end=end_date)['Close']
            
            if isinstance(raw_data, pd.Series):
                raw_data = raw_data.to_frame(name=all_tickers[0])

            # 한국/미국 휴장일 상이함 보정 (휴장일은 직전가 채움)
            data = raw_data.ffill().bfill().dropna()

            if data.empty or len(data) < 10:
                st.error("데이터가 부족합니다. 선택한 종목의 상장 기간이나 티커를 확인해 주세요.")
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

                # 결과 계산
                final_val = portfolio_series.iloc[-1]
                total_return = ((final_val / initial_capital) - 1) * 100
                actual_years = (dates[-1] - dates[0]).days / 365.25
                cagr = (((final_val / initial_capital) ** (1 / max(actual_years, 0.1))) - 1) * 100

                peak = portfolio_series.cummax()
                drawdown = (portfolio_series - peak) / peak
                mdd = drawdown.min() * 100

                # 출력 UI
                st.info(f"📅 실제 분석 데이터 기간: **{dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}** (약 {actual_years:.1f}년)")

                st.markdown("### 📌 성과 요약")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("최종 평가 금액", f"{final_val:,.0f}")
                col2.metric("누적 수익률", f"{total_return:+.2f}%")
                col3.metric("CAGR (연평균 수익률)", f"{cagr:.2f}%")
                col4.metric("MDD (최대 낙폭)", f"{mdd:.2f}%", delta_color="inverse")

                # 차트
                st.markdown("### 📈 자산 성장 추이")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=portfolio_series.index, 
                    y=portfolio_series.values, 
                    mode='lines', 
                    name='Portfolio',
                    line=dict(color='#1f77b4', width=2)
                ))
                fig.update_layout(xaxis_title="날짜", yaxis_title="자산 가치", hovermode="x unified", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

                # 하락폭 차트
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