import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. 페이지 기본 설정 및 미래에셋 연금계좌 TOP 100 ETF DB
# ---------------------------------------------------------
st.set_page_config(page_title="연금저축 백테스터 & 리밸런싱 계산기", layout="wide")
st.title("📊 연금저축 자산관리 통합 도구")

# 미래에셋 연금계좌(연금저축/IRP) 매수 가능 주요 ETF TOP 100+ DB
STOCK_DATABASE = {
    # --- [미국 대표지수 추종 (S&P500 / 나스닥 / 다우 / 라셀)] ---
    "TIGER 미국S&P500": "360750.KS",
    "KODEX 미국S&P500TR": "379800.KS",
    "ACE 미국S&P500": "368590.KS",
    "SOL 미국S&P500": "433330.KS",
    "RISE 미국S&P500": "368200.KS",
    "TIGER 미국나스닥100": "133690.KS",
    "KODEX 미국나스닥100TR": "379810.KS",
    "ACE 미국나스닥100": "367380.KS",
    "TIGER 미국다우존스30": "245340.KS",
    "KIWOOM 미국S&P500모멘텀": "487950.KS",
    "KODEX 미국러셀2000(H)": "284430.KS",

    # --- [미국 배당주 / SCHD / 고배당 / 커버드콜] ---
    "TIGER 미국배당다우존스 [SCHD]": "458730.KS",
    "ACE 미국배당다우존스 [SCHD]": "423160.KS",
    "SOL 미국배당다우존스 [SCHD]": "446720.KS",
    "ACE 미국배당퀄리티": "480410.KS",
    "TIGER 미국배당+3%프리미엄다우존스": "474220.KS",
    "TIGER 미국배당+7%프리미엄다우존스": "474230.KS",
    "KODEX 미국배당프리미엄Active": "438010.KS",
    "TIGER 미국S&P500타겟데일리커버드콜": "482730.KS",
    "KODEX 미국30년국채+12%프리미엄(합성H)": "482080.KS",

    # --- [빅테크 / AI / 소프트웨어 / 데이터센터] ---
    "TIGER 미국테크TOP10 INDXX": "381170.KS",
    "ACE 미국빅테크TOP7 Plus": "465580.KS",
    "KODEX 미국나스닥100동일가중": "485030.KS",
    "TIGER 미국AI빅테크10": "490090.KS",
    "KODEX 미국AI소프트웨어TOP4Plus": "487820.KS",
    "KODEX 미국AI전력핵심인프라": "486330.KS",
    "TIGER 미국AI전력SMR": "486340.KS",
    "RISE 미국AI테크액티브": "483210.KS",
    "SOL 미국AI전력인프라": "486350.KS",
    "KODEX 미국AI광통신네트워크": "0173Y0.KS",

    # --- [반도체 / 빅테크 테마] ---
    "TIGER 미국필라델피아반도체나스닥": "381180.KS",
    "ACE 미국반도체MV": "388420.KS",
    "TIGER 미국필라델피아AI반도체나스닥": "497570.KS",
    "KODEX 미국반도체MV": "391620.KS",
    "TIGER TSMC파운드리밸류체인": "453950.KS",
    "TIGER 반도체TOP10": "446770.KS",
    "KODEX AI반도체핵심공정": "471750.KS",

    # --- [국내 주식 / 대표지수 / 고배당 / 밸류업] ---
    "KODEX 200": "069500.KS",
    "TIGER 200": "102110.KS",
    "KODEX 코스닥150": "229200.KS",
    "PLUS 고배당주": "294200.KS",
    "TIGER 은행고배당플러스TOP10": "458170.KS",
    "KODEX 코리아밸류업": "489500.KS",
    "TIGER 코리아밸류업": "489510.KS",
    "ARIRANG 고배당주": "161510.KS",
    "KODEX 배당성장": "279530.KS",

    # --- [국내 테마 / 방산 / 조선 / 원자력 / 2차전지] ---
    "PLUS K방산": "463250.KS",
    "SOL 조선TOP3플러스": "466920.KS",
    "TIGER 코리아원자력": "426180.KS",
    "TIGER 2차전지테마": "305540.KS",
    "KODEX 2차전지산업": "305720.KS",
    "TIGER 바이오TOP10": "364970.KS",
    "TIGER 현대차그룹+": "091230.KS",

    # --- [글로벌 / 인도 / 일본 / 중국 / 비만치료제] ---
    "TIGER 인도니프티50": "453870.KS",
    "KODEX 인도Nifty50": "453880.KS",
    "ACE 일본TOPIX범설(H)": "196030.KS",
    "TIGER 일본반도체FACTSET": "465660.KS",
    "TIGER 차이나항셍테크": "371160.KS",
    "TIGER 차이나전기차SOLACTIVE": "371460.KS",
    "TIGER 글로벌비만치료제TOP2 Plus": "476690.KS",
    "KODEX 글로벌비만치료제TOP2 Plus": "476700.KS",

    # --- [채권 / 금 / 자산배분 / 파킹형] ---
    "ACE 미국30년국채액티브(H)": "453850.KS",
    "TIGER 미국30년스트립액티브(합성H)": "472150.KS",
    "KODEX 미국30년국채액티브(H)": "465520.KS",
    "SOL 미국30년국채커버드콜(합성)": "474130.KS",
    "TIGER 골드선물(H)": "139320.KS",
    "ACE 골드선물(H)": "411060.KS",
    "KODEX KIS국고채30년Enhanced": "385560.KS",
    "ACE 국고채10년": "365780.KS",
    "KODEX CD금리액티브(합성)": "459580.KS",
    "TIGER KOFR금리액티브(합성)": "423150.KS",
    "KODEX 미국달러SOFR금리액티브(합성)": "449450.KS",

    # --- [미국 직투 주식 & ETF (해외주식 일반계좌 백테스트용)] ---
    "[미국ETF] SPY - S&P500": "SPY",
    "[미국ETF] QQQ - 나스닥100": "QQQ",
    "[미국ETF] SCHD - 미국 배당성장": "SCHD",
    "[미국ETF] TLT - 미국 20년+ 장기채": "TLT",
    "[미국ETF] GLD - 금 현물": "GLD",
    "[미국주식] AAPL - 애플": "AAPL",
    "[미국주식] MSFT - 마이크로소프트": "MSFT",
    "[미국주식] NVDA - 엔비디아": "NVDA",
    "[미국주식] TSLA - 테슬라": "TSLA"
}

# 상장일이 짧아 데이터가 부족한 ETF에 적용할 대체 지수/ETF 매핑
BACKFILL_MAP = {
    # S&P 500 계열 -> SPY
    "360750.KS": "SPY", "379800.KS": "SPY", "368590.KS": "SPY", "433330.KS": "SPY", 
    "368200.KS": "SPY", "487950.KS": "SPY",
    # 나스닥 100 계열 -> QQQ
    "133690.KS": "QQQ", "379810.KS": "QQQ", "367380.KS": "QQQ", "485030.KS": "QQQ", 
    "381170.KS": "QQQ", "465580.KS": "QQQ", "490090.KS": "QQQ", "487820.KS": "QQQ",
    # 미국 배당주 / SCHD 계열 -> SCHD
    "458730.KS": "SCHD", "423160.KS": "SCHD", "446720.KS": "SCHD", "480410.KS": "SCHD", 
    "474220.KS": "SCHD", "474230.KS": "SCHD", "438010.KS": "SCHD", "482730.KS": "SPY",
    # 반도체 계열 -> SOXX 또는 NVDA
    "381180.KS": "SOXX", "388420.KS": "SOXX", "497570.KS": "SOXX", "391620.KS": "SOXX", 
    "453950.KS": "TSM", "446770.KS": "005930.KS", "471750.KS": "005930.KS",
    # 미국 장기채 계열 -> TLT
    "453850.KS": "TLT", "472150.KS": "TLT", "465520.KS": "TLT", "474130.KS": "TLT", 
    "482080.KS": "TLT",
    # 코스피 / 코리아 밸류업 -> KODEX 200 (069500.KS)
    "489500.KS": "069500.KS", "489510.KS": "069500.KS", "102110.KS": "069500.KS",
    # AI 전력 / 인프라 -> XLU (미국 유틸리티 ETF) 또는 QQQ
    "486330.KS": "XLU", "486340.KS": "XLU", "483210.KS": "QQQ", "486350.KS": "XLU"

    # AI 광통신/네트워크 -> QQQ 백필 매핑 추가
    "0173Y0.KS": "QQQ",

}

ticker_to_label = {v: k for k, v in STOCK_DATABASE.items()}

# 안전한 최신 주가 가져오기 함수 (캐싱 적용)
@st.cache_data(ttl=300)
def get_latest_price(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period="7d")
        if not hist.empty:
            return float(hist['Close'].dropna().iloc[-1])
        return 0.0
    except Exception:
        return 0.0

# ---------------------------------------------------------
# 자동 백필(Backfill) 지원 주가 데이터 수집 함수
# ---------------------------------------------------------
def fetch_and_backfill_data(tickers, start_date, end_date):
    """
    종목별 데이터를 수집하되, 백테스트 시작일 이후에 상장되어 
    데이터가 부족한 종목은 대체 티커(BACKFILL_MAP)의 수익률로 과거를 채웁니다.
    """
    all_needed_tickers = set(tickers)
    for t in tickers:
        if t in BACKFILL_MAP:
            all_needed_tickers.add(BACKFILL_MAP[t])

    # 1. 전체 필요한 티커 데이터 다운로드
    raw_data = yf.download(list(all_needed_tickers), start=start_date, end=end_date)['Close']
    
    if isinstance(raw_data, pd.Series):
        raw_data = raw_data.to_frame(name=list(all_needed_tickers)[0])

    raw_data = raw_data.ffill().bfill()
    
    backfilled_df = pd.DataFrame(index=raw_data.index)
    backfill_info = []

    for t in tickers:
        if t not in raw_data.columns:
            continue
        
        series = raw_data[t].dropna()
        if series.empty:
            continue
            
        first_valid_idx = series.index[0]
        
        # 백테스트 시작일보다 상장일이 늦고, 대체 티커가 등록되어 있는 경우
        if first_valid_idx > raw_data.index[0] and t in BACKFILL_MAP:
            bench_ticker = BACKFILL_MAP[t]
            if bench_ticker in raw_data.columns:
                bench_series = raw_data[bench_ticker]
                
                # 상장일 당일의 수익률 연결 기준점
                base_price = series.loc[first_valid_idx]
                
                # 대체 종목의 일별 수익률 계산
                bench_pct = bench_series.pct_change().fillna(0)
                
                # 상장 이전 기간에 대해 대체 종목 수익률을 역산하여 과거 주가 추정
                past_dates = raw_data.index[raw_data.index < first_valid_idx]
                estimated_prices = {}
                
                curr_p = base_price
                for d in reversed(past_dates):
                    # 역방향 계산: P_{t-1} = P_t / (1 + r_t)
                    r = bench_pct.loc[d]
                    curr_p = curr_p / (1 + r) if (1 + r) != 0 else curr_p
                    estimated_prices[d] = curr_p
                
                past_series = pd.Series(estimated_prices).sort_index()
                combined_series = pd.concat([past_series, series])
                backfilled_df[t] = combined_series
                
                label = ticker_to_label.get(t, t)
                bench_label = ticker_to_label.get(bench_ticker, bench_ticker)
                backfill_info.append(f"**{label}** ({first_valid_idx.strftime('%Y-%m-%d')} 상장) ➡️ **{bench_label}** 수익률로 과거 데이터 백필 적용")
            else:
                backfilled_df[t] = raw_data[t]
        else:
            backfilled_df[t] = raw_data[t]

    return backfilled_df.dropna(), backfill_info

# 탭 구성
tab1, tab2 = st.tabs(["🚀 포트폴리오 백테스터", "⚖️ 현재 비중 계산 & 매매 리밸런싱"])


# =========================================================
# TAB 1: 백테스트 시뮬레이션
# =========================================================
with tab1:
    st.header("백테스트 시뮬레이션")
    st.caption("미래에셋 연금계좌 주요 ETF 및 선택한 종목의 과거 수익률과 CAGR(연평균 수익률)을 분석합니다.")
    
    st.sidebar.header("⚙️ [백테스트] 설정")
    selected_display_names = st.sidebar.multiselect(
        "🔍 종목 선택 (한글/영어)",
        options=list(STOCK_DATABASE.keys()),
        default=[
            "KIWOOM 미국S&P500모멘텀",
            "TIGER 미국나스닥100",
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
            with st.spinner("주가 데이터 수집 및 대체 지수 백필 처리 중..."):
                end_date = datetime.today()
                start_date = end_date - timedelta(days=int(years * 365.25))

                # 백필 지원 수집 함수 활용
                data, backfill_info = fetch_and_backfill_data(all_tickers, start_date, end_date)

                if data.empty or len(data) < 10:
                    st.error("데이터가 부족합니다. 백테스트 기간이나 종목을 변경해 주세요.")
                else:
                    # 백필 정보가 있는 경우 안내 메시지 표시
                    if backfill_info:
                        with st.expander("💡 **신규 상장 ETF 자동 백필(Backfill) 적용 안내**", expanded=True):
                            st.write("선택한 ETF 중 백테스트 기간 내 상장된 신생 ETF는 상장 이전 기간 동안 연관 대표지수/대체 ETF 수익률을 활용해 자동 복원 처리되었습니다.")
                            for info in backfill_info:
                                st.markdown(f"- {info}")

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
                    
                    # 🔥 [연간 수익률 (CAGR) 산출]
                    if actual_years > 0 and total_invested > 0:
                        cagr = (((final_val / total_invested) ** (1.0 / actual_years)) - 1.0) * 100
                    else:
                        cagr = 0.0

                    peak = portfolio_series.cummax()
                    drawdown = (portfolio_series - peak) / peak
                    mdd = drawdown.min() * 100

                    st.info(f"📅 백테스트 실행 기간: **{dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}** (약 {actual_years:.1f}년)")

                    # 6개 요약 지표 출력
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    col1.metric("총 투입 원금", f"{total_invested:,.0f}원")
                    col2.metric("최종 평가 금액", f"{final_val:,.0f}원")
                    col3.metric("순수익금", f"{total_profit:+,.0f}원")
                    col4.metric("누적 수익률", f"{total_return:+.2f}%")
                    col5.metric("연평균 수익률 (CAGR)", f"{cagr:+.2f}%")
                    col6.metric("MDD (최대 낙폭)", f"{mdd:.2f}%", delta_color="inverse")

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
    st.caption("보유 수량을 입력하면 실시간 주가 기준 현재 비중을 자동 계산하고, 목표 비중 맞춤용 매수/매도 수량을 안내합니다.")

    reb_selected_names = st.multiselect(
        "🔍 현재 보유 중이거나 리밸런싱에 포함할 종목 선택",
        options=list(STOCK_DATABASE.keys()),
        default=[
            "TIGER 미국배당다우존스 [SCHD]",
            "PLUS 고배당주"
        ],
        key="reb_select"
    )

    reb_tickers = [STOCK_DATABASE[name] for name in reb_selected_names]

    if not reb_tickers:
        st.warning("종목을 선택해 주세요.")
    else:
        extra_cash = st.number_input("💵 이번 리밸런싱 시 추가로 입금할 금액 (원)", value=1000000, step=100000, key="reb_extra_cash")
        
        st.subheader("1️⃣ 보유 수량 및 목표 비중 입력")

        # 실시간 가격 수집
        prices = {ticker: get_latest_price(ticker) for ticker in reb_tickers}

        # 현재 평가금액 총합 계산
        temp_shares = {}
        total_current_val = 0.0
        for ticker in reb_tickers:
            s_val = st.session_state.get(f"shares_{ticker}", 10)
            temp_shares[ticker] = s_val
            total_current_val += s_val * prices[ticker]

        # 레이아웃 헤더 (5컬럼: 종목명 | 보유 수량 | 현재가 | 현재 비중 | 목표 비중)
        cols = st.columns([3, 2, 2, 2, 2])
        cols[0].markdown("**종목명**")
        cols[1].markdown("**현재 보유 수량 (주)**")
        cols[2].markdown("**현재가 (원)**")
        cols[3].markdown("**현재 비중 (%)**")
        cols[4].markdown("**목표 비중 (%)**")

        input_data = []
        default_target_w = round(100.0 / len(reb_tickers), 1)

        for idx, ticker in enumerate(reb_tickers):
            label = ticker_to_label.get(ticker, ticker)
            p = prices[ticker]
            
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
            c1.write(f"**{label}**")
            
            shares = c2.number_input(f"보유 수량 ({label})", min_value=0, value=10, step=1, label_visibility="collapsed", key=f"shares_{ticker}")
            
            cur_val = shares * p
            cur_weight_pct = (cur_val / total_current_val * 100.0) if total_current_val > 0 else 0.0
            
            c3.write(f"{int(p):,}원" if p > 0 else "조회불가")
            c4.markdown(f"**{cur_weight_pct:.2f}%**")
            
            target_w = c5.number_input(f"목표 비중 ({label})", min_value=0.0, max_value=100.0, value=default_target_w, step=1.0, label_visibility="collapsed", key=f"target_w_{ticker}")
            
            input_data.append({
                "ticker": ticker,
                "label": label,
                "shares": shares,
                "price": p,
                "current_val": cur_val,
                "target_weight": target_w / 100.0
            })

        sum_target_w = sum(item["target_weight"] for item in input_data)
        if abs(sum_target_w - 1.0) > 0.001:
            st.error(f"⚠️ 목표 비중의 합이 100%가 되어야 합니다. (현재 합계: {sum_target_w*100:.1f}%)")

        if st.button("🧮 리밸런싱 주문 가이드 계산하기", type="primary"):
            if abs(sum_target_w - 1.0) > 0.001:
                st.error("목표 비중의 합을 100%로 맞춘 후 계산 버튼을 눌러주세요.")
            else:
                total_future_val = total_current_val + extra_cash

                results = []
                for item in input_data:
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
                        "현재가": f"{int(p):,}원" if p > 0 else "조회 실패",
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