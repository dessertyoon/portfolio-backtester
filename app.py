import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. 페이지 기본 설정 및 통합 종목 DB
# ---------------------------------------------------------
st.set_page_config(page_title="연금저축 백테스터 & 리밸런싱 계산기", layout="wide")
st.title("📊 연금저축 자산관리 통합 도구")

# 한글 검색 데이터베이스
STOCK_DATABASE = {
    # --- [실제 보유 종목] ---
    "KIWOOM 미국S&P500모멘텀": "487950.KS",
    "KODEX 미국나스닥100": "441680.KS",
    "KODEX 미국AI광통신네트워크": "486330.KS",
    "ACE 미국S&P500": "368590.KS",
    "TIGER 미국테크TOP10 INDXX": "381170.KS",
    "ACE 미국배당퀄리티": "480410.KS",
    "PLUS 고배당주": "294200.KS",
    "TIGER 은행고배당플러스TOP10": "458170.KS",
    "TIGER 반도체TOP10": "446770.KS",

    # --- [연금저축] 대표지수 추종 (S&P500 / 나스닥 / 다우) ---
    "[연금] TIGER 미국S&P500 (360750)": "360750.KS",
    "[연금] KODEX 미국S&P500TR (379800)": "379800.KS",
    "[연금] SOL 미국S&P500 (433330)": "433330.KS",
    "[연금] TIGER 미국나스닥100 (133690)": "133690.KS",
    "[연금] KODEX 미국나스닥100TR (379810)": "379810.KS",
    "[연금] TIGER 미국다우존스30 (245340)": "245340.KS",

    # --- [연금저축] 배당 / 성장 배당 (SCHD / 커버드콜) ---
    "[연금] TIGER 미국배당다우존스 [SCHD한국판] (458730)": "458730.KS",
    "[연금] ACE 미국배당다우존스 [SCHD한국판] (423160)": "423160.KS",
    "[연금] SOL 미국배당다우존스 [SCHD한국판] (446720)": "446720.KS",
    "[연금] KODEX 미국배당프리미엄Active (438010)": "438010.KS",
    "[연금] TIGER 미국배당+3%프리미엄다우존스 (474220)": "474220.KS",
    "[연금] TIGER 미국배당+7%프리미엄다우존스 (474230)": "474230.KS",

    # --- [연금저축] 빅테크 / 반도체 / 테마 ---
    "[연금] TIGER 미국필라델피아반도체나스닥 (381180)": "381180.KS",
    "[연금] ACE 미국반도체MV (388420)": "388420.KS",
    "[연금] ACE 미국빅테크TOP7 Plus (465580)": "465580.KS",

    # --- [연금저축] 미국 장기채권 / 국채 / 안전자산 ---
    "[연금] ACE 미국30년국채액티브(H) (453850)": "453850.KS",
    "[연금] TIGER 미국30년스트립액티브 (472150)": "472150.KS",
    "[연금] TIGER 골드선물(H) [금투자] (139320)": "139320.KS",
    "[연금] KODEX 200 [코스피200] (069500)": "069500.KS",

    # --- [미국 직투 ETF & 주식] ---
    "[미국ETF] SPY - S&P500 지수": "SPY",
    "[미국ETF] QQQ - 나스닥100 지수": "QQQ",
    "[미국ETF] SCHD - 미국 배당성장": "SCHD",
    "[미국ETF] TLT - 미국 20년+ 장기국채": "TLT",
    "[미국ETF] GLD - 금 현물": "GLD",
    "[미국주식] AAPL - 애플 (Apple)": "AAPL",
    "[미국주식] MSFT - 마이크로소프트 (Microsoft)": "MSFT",
    "[미국주식] NVDA - 엔비디아 (NVIDIA)": "NVDA",
    "[미국주식] TSLA - 테슬라 (Tesla)": "TSLA"
}

# 탭 생성
tab1, tab2 = st.tabs(["🚀 포트폴리오 백테스터", "⚖️ 현재 비중 계산 & 매매 리밸런싱"])

# =========================================================
# TAB 1: 백테스트 시뮬레이션
# =========================================================
with tab1:
    st.header("백테스트 시뮬레이션")
    st.caption("선택한 종목과 비중을 바탕으로 과거 성과를 시뮬레이션합니다.")
    
    st.sidebar.header("⚙️ [백테스트] 설정")
    selected_display_names = st.sidebar.multiselect(
        "🔍 종목 선택 (한글/영어)",
        options=list(STOCK_DATABASE.keys()),
        default=[
            "KIWOOM 미국S&P500모멘텀",
            "KODEX 미국나스닥100",
            "KODEX 미국AI광통신네트워크",
            "ACE 미국S&P500",
            "TIGER 미국테크TOP10 INDXX"
        ]
    )

    selected_tickers = [STOCK_DATABASE[name] for name in selected_display_names]
    manual_input = st.sidebar.text_input("➕ 직접 티커 추가 (예: SOXX, 005930.KS)", key="bt_manual")
    manual_tickers = [t.strip().upper() for t in manual_input.split(",") if t.strip()]
    all_tickers = list(dict.fromkeys(selected_tickers + manual_tickers))

    weights = []
    st.sidebar.subheader("⚖️ 백테스트 목표 비중 (%)")
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
            key=f"bt_weight_{ticker}"
        )
        weights.append(w / 100.0)

    total_weight = sum(weights)
    if abs(total_weight - 1.0) > 0.001 and all_tickers:
        st.sidebar.error(f"⚠️ 비중 합계가 100%여야 합니다. (현재: {total_weight*100:.1f}%)")

    initial_capital = st.sidebar.number_input("초기 투자금 (원)", value=10000000, step=1000000, key="bt_init")
    rebalance_freq = st.sidebar.selectbox("리밸런싱 주기", ["월간 (Monthly)", "분기 (Quarterly)", "연간 (Annually)", "리밸런싱 안함 (No Rebalance)"], key="bt_freq")
    add_cash = st.sidebar.number_input("회차당 추가 납입금 (원)", value=1000000, step=100000, key="bt_add")
    years = st.sidebar.slider("백테스트 기간 (년)", min_value=1, max_value=10, value=3, key="bt_years")

    if st.sidebar.button("🚀 백테스트 실행", type="primary", key="bt_btn"):
        if not all_tickers:
            st.error("종목을 선택해 주세요.")
        elif abs(total_weight - 1.0) > 0.001:
            st.error("종목 비중의 합을 100%로 맞춰주세요.")
        else:
            with st.spinner("주가 데이터를 분석 중입니다..."):
                end_date = datetime.today()
                start_date = end_date - timedelta(days=int(years * 365.25))

                raw_data = yf.download(all_tickers, start=start_date, end=end_date)['Close']
                if isinstance(raw_data, pd.Series):
                    raw_data = raw_data.to_frame(name=all_tickers[0])

                data = raw_data.ffill().bfill().dropna()

                if data.empty or len(data) < 10:
                    st.error("데이터가 부족합니다. 백테스트 기간이나 종목을 변경해 주세요.")
                else:
                    daily_returns = data.pct_change().fillna(0)
                    dates = data.index

                    freq_map = {"월간 (Monthly)": "ME", "분기 (Quarterly)": "QE", "연간 (Annually)": "YE", "리밸런싱 안함 (No Rebalance)": None}
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

                    final_val = portfolio_series.iloc[-1]
                    total_invested = total_invested_series.iloc[-1]
                    total_profit = final_val - total_invested
                    total_return = (total_profit / total_invested) * 100
                    actual_years = (dates[-1] - dates[0]).days / 365.25
                    peak = portfolio_series.cummax()
                    drawdown = (portfolio_series - peak) / peak
                    mdd = drawdown.min() * 100

                    st.info(f"📅 백테스트 기간: **{dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}** (약 {actual_years:.1f}년)")

                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("총 투입 원금", f"{total_invested:,.0f}원")
                    col2.metric("최종 평가 금액", f"{final_val:,.0f}원")
                    col3.metric("순수익금", f"{total_profit:+,.0f}원")
                    col4.metric("수익률", f"{total_return:+.2f}%")
                    col5.metric("MDD (최대 낙폭)", f"{mdd:.2f}%", delta_color="inverse")

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=portfolio_series.index, y=portfolio_series.values, mode='lines', name='포트폴리오 평가금', line=dict(color='#1f77b4', width=2)))
                    fig.add_trace(go.Scatter(x=total_invested_series.index, y=total_invested_series.values, mode='lines', name='누적 투입 원금', line=dict(color='#7f7f7f', width=2, dash='dash')))
                    fig.update_layout(xaxis_title="날짜", yaxis_title="금액 (원)", hovermode="x unified", template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# TAB 2: 현재 비중 계산 & 매매 리밸런싱
# =========================================================
with tab2:
    st.header("현재 비중 자동 계산 & 리밸런싱 주문 가이드")
    st.caption("현재 보유 주식 수를 입력하면 현재 비중을 계산하고, 목표 비중에 맞추기 위한 필요 매수/매도 수량을 알려줍니다.")

    reb_selected_names = st.multiselect(
        "🔍 현재 보유 중이거나 리밸런싱에 포함할 종목 선택",
        options=list(STOCK_DATABASE.keys()),
        default=[
            "KIWOOM 미국S&P500모멘텀",
            "KODEX 미국나스닥100",
            "KODEX 미국AI광통신네트워크",
            "ACE 미국S&P500",
            "TIGER 미국테크TOP10 INDXX",
            "ACE 미국배당퀄리티",
            "PLUS 고배당주"
        ],
        key="reb_select"
    )

    reb_tickers = [STOCK_DATABASE[name] for name in reb_selected_names]

    if not reb_tickers:
        st.warning("종목을 선택해 주세요.")
    else:
        # 추가 입금액 입력
        extra_cash = st.number_input("💵 이번 리밸런싱 시 추가로 입금할 금액 (원)", value=1000000, step=100000, key="reb_extra_cash")
        
        st.subheader("1️⃣ 보유 수량 및 목표 비중 입력")
        st.markdown("각 종목의 **현재 보유 주식 수(주)**와 **목표 비중(%)**을 입력해 주세요.")

        # 입력용 컬럼 설정
        input_data = []
        default_target_w = round(100.0 / len(reb_tickers), 1)

        cols = st.columns([3, 2, 2])
        cols[0].markdown("**종목명**")
        cols[1].markdown("**현재 보유 주식 수 (주)**")
        cols[2].markdown("**목표 비중 (%)**")

        for idx, ticker in enumerate(reb_tickers):
            label = ticker_to_label.get(ticker, ticker)
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.write(f"**{label}**")
            shares = c2.number_input(f"보유 수량 ({label})", min_value=0, value=10, step=1, label_visibility="collapsed", key=f"shares_{ticker}")
            target_w = c3.number_input(f"목표 비중 ({label})", min_value=0.0, max_value=100.0, value=default_target_w, step=1.0, label_visibility="collapsed", key=f"target_w_{ticker}")
            
            input_data.append({
                "ticker": ticker,
                "label": label,
                "shares": shares,
                "target_weight": target_w / 100.0
            })

        sum_target_w = sum(item["target_weight"] for item in input_data)
        if abs(sum_target_w - 1.0) > 0.001:
            st.error(f"⚠️ 목표 비중의 합이 100%가 되어야 합니다. (현재 합계: {sum_target_w*100:.1f}%)")

        if st.button("🧮 리밸런싱 계산하기", type="primary"):
            if abs(sum_target_w - 1.0) > 0.001:
                st.error("목표 비중의 합을 100%로 맞춘 후 계산 버튼을 눌러주세요.")
            else:
                with st.spinner("최신 주가 정보를 불러오는 중입니다..."):
                    # 야후 파이낸스 최신 가격 조회
                    price_data = yf.download(reb_tickers, period="5d")['Close']
                    
                    latest_prices = {}
                    for ticker in reb_tickers:
                        if isinstance(price_data, pd.DataFrame):
                            latest_prices[ticker] = float(price_data[ticker].dropna().iloc[-1])
                        else:
                            latest_prices[ticker] = float(price_data.dropna().iloc[-1])

                    # 리밸런싱 연산
                    total_current_val = 0.0
                    for item in input_data:
                        t = item["ticker"]
                        p = latest_prices[t]
                        item["price"] = p
                        item["current_val"] = item["shares"] * p
                        total_current_val += item["current_val"]

                    total_future_val = total_current_val + extra_cash

                    results = []
                    for item in input_data:
                        t = item["ticker"]
                        p = item["price"]
                        cur_val = item["current_val"]
                        cur_weight = (cur_val / total_current_val) if total_current_val > 0 else 0.0
                        
                        target_val = total_future_val * item["target_weight"]
                        diff_val = target_val - cur_val
                        diff_shares = int(round(diff_val / p)) if p > 0 else 0

                        if diff_shares > 0:
                            action = f"🟢 **매수 {diff_shares}주** (+{int(diff_val):,}원)"
                        elif diff_shares < 0:
                            action = f"🔴 **매도 {abs(diff_shares)}주** ({int(diff_val):,}원)"
                        else:
                            action = "⚪ **유지 (0주)**"

                        results.append({
                            "종목명": item["label"],
                            "현재가": f"{int(p):,}원",
                            "보유수량": f"{item['shares']}주",
                            "현재 평가금액": f"{int(cur_val):,}원",
                            "현재 비중": f"{cur_weight*100:.2f}%",
                            "목표 비중": f"{item['target_weight']*100:.1f}%",
                            "목표 평가금액": f"{int(target_val):,}원",
                            "추천 매매 수량": action
                        })

                    res_df = pd.DataFrame(results)

                    st.markdown("---")
                    st.subheader("2️⃣ 리밸런싱 결과 분석")
                    
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("현재 자산 총액", f"{int(total_current_val):,}원")
                    col_b.metric("추가 입금 예정액", f"{int(extra_cash):,}원")
                    col_c.metric("리밸런싱 후 목표 총 자산", f"{int(total_future_val):,}원")

                    st.markdown("### 📋 종목별 매매 주문 가이드")
                    st.write("아래 안내된 수량만큼 증권사 앱에서 매수/매도 주문을 실행하시면 목표 비중에 맞춰집니다.")
                    st.dataframe(res_df, use_container_width=True)