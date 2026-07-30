import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. 설정 및 기본 데이터
# ==========================================
st.set_page_config(page_title="미국 주식 포트폴리오 백테스터 & 리밸런서", layout="wide")

# 주요 ETF에 대한 백필 기본 대체 지수 매핑
DEFAULT_BENCHMARKS = {
    "QQQM": "QQQ",
    "SPLG": "SPY",
    "VOO": "SPY",
    "IVV": "SPY",
    "SCHD": "^GSPC",
    "SCHG": "QQQ",
    "JEPI": "^GSPC"
}

# ==========================================
# 2. 핵심 함수: 데이터 수집 및 백필(Backfill)
# ==========================================
@st.cache_data(ttl=3600)
def fetch_and_backfill_data(tickers, start_date, end_date):
    """
    요청한 티커 목록 데이터를 수집하고, 데이터가 부족한 티커는 대체 지수로 역산(Backfill)합니다.
    """
    all_tickers_to_fetch = set(tickers)
    # 필요한 대체 지수 티커 추가
    for t in tickers:
        bm = DEFAULT_BENCHMARKS.get(t, "^GSPC")
        all_tickers_to_fetch.add(bm)
        
    df_raw = yf.download(list(all_tickers_to_fetch), start=start_date, end=end_date)['Close']
    
    # 단일 종목일 경우 DataFrame 처리
    if isinstance(df_raw, pd.Series):
        df_raw = df_raw.to_frame()
        
    filled_df = pd.DataFrame(index=df_raw.index)
    
    for t in tickers:
        if t not in df_raw.columns or df_raw[t].dropna().empty:
            continue
            
        target_s = df_raw[t].dropna()
        bm_ticker = DEFAULT_BENCHMARKS.get(t, "^GSPC")
        
        if bm_ticker in df_raw.columns:
            bm_s = df_raw[bm_ticker].dropna()
        else:
            bm_s = df_raw['^GSPC'].dropna() if '^GSPC' in df_raw.columns else target_s
            
        # 데이터 병합 기준
        combined = pd.DataFrame({'target': target_s, 'bm': bm_s}).dropna(subset=['bm'])
        first_valid = combined['target'].first_valid_index()
        
        if first_valid is None or first_valid == combined.index[0]:
            filled_df[t] = combined['target'].ffill().bfill()
        else:
            # 역순 백필 계산
            bm_pct = combined['bm'].pct_change()
            base_price = combined.loc[first_valid, 'target']
            sub_bm_pct = bm_pct.loc[:first_valid]
            
            restored = [base_price]
            for r in sub_bm_pct.iloc[::-1][:-1]:
                prev_p = restored[-1] / (1 + r) if pd.notna(r) and r != -1 else restored[-1]
                restored.append(prev_p)
            restored.reverse()
            
            full_s = combined['target'].copy()
            full_s.loc[:first_valid] = restored
            filled_df[t] = full_s
            
    return filled_df.ffill().bfill()

# ==========================================
# 3. 백테스트 시뮬레이션 엔진
# ==========================================
def run_backtest(price_df, weights, init_balance, monthly_contrib, rebalance_freq):
    """
    포트폴리오 백테스트 수행 (초기 투자금 + 월 적립금 + 리밸런싱)
    """
    tickers = list(weights.keys())
    weights_arr = np.array([weights[t] for t in tickers])
    
    # 일간 수익률
    returns_df = price_df[tickers].pct_change().fillna(0)
    
    portfolio_history = []
    dates = price_df.index
    
    current_cash = init_balance
    current_shares = np.zeros(len(tickers))
    
    # 첫날 목표 비중으로 매수
    first_prices = price_df[tickers].iloc[0].values
    current_shares = (init_balance * weights_arr) / first_prices
    
    last_rebalance_month = -1
    last_rebalance_quarter = -1
    last_rebalance_year = -1
    
    for i, date in enumerate(dates):
        current_prices = price_df[tickers].iloc[i].values
        
        # 월 적립금 납입 (매월 첫 거래일)
        if i > 0 and date.month != dates[i-1].month:
            current_shares += (monthly_contrib * weights_arr) / current_prices
            
        # 리밸런싱 조건 확인
        need_rebalance = False
        if rebalance_freq == "매월" and (i > 0 and date.month != dates[i-1].month):
            need_rebalance = True
        elif rebalance_freq == "매분기" and (i > 0 and date.quarter != dates[i-1].quarter):
            need_rebalance = True
        elif rebalance_freq == "매년" and (i > 0 and date.year != dates[i-1].year):
            need_rebalance = True
            
        # 리밸런싱 실행
        if need_rebalance:
            total_val = np.sum(current_shares * current_prices)
            current_shares = (total_val * weights_arr) / current_prices
            
        # 일일 평가액 저장
        total_eval = np.sum(current_shares * current_prices)
        portfolio_history.append(total_eval)
        
    result_df = pd.DataFrame({'Total': portfolio_history}, index=dates)
    
    # 성과 지표 계산
    total_return = (result_df['Total'].iloc[-1] / (init_balance + monthly_contrib * len(pd.date_range(dates[0], dates[-1], freq='MS')))) - 1
    days = (dates[-1] - dates[0]).days
    cagr = ((result_df['Total'].iloc[-1] / result_df['Total'].iloc[0]) ** (365.25 / days)) - 1
    
    cummax = result_df['Total'].cummax()
    drawdown = (result_df['Total'] - cummax) / cummax
    mdd = drawdown.min()
    
    return result_df, cagr, mdd, drawdown

# ==========================================
# 4. Streamlit UI 구성
# ==========================================
st.title("📈 미국 주식 포트폴리오 통합 대시보드")
st.markdown("신규 상장 ETF **자동 백필 백테스트** 및 **추가 투자금 리밸런서**")

tab1, tab2 = st.tabs(["📊 백테스트 (Backfill 적용)", "⚖️ 신규 투자금 리밸런싱 계산기"])

# ------------------------------------------
# TAB 1: 백테스트
# ------------------------------------------
with tab1:
    st.sidebar.header("⚙️ 백테스트 설정")
    
    # 종목 및 비중 설정
    ticker_input = st.sidebar.text_input("포트폴리오 티커 (쉼표 구분)", "QQQM, SPLG, SCHD")
    tickers = [t.strip().upper() for t in ticker_input.split(",")]
    
    st.sidebar.subheader("목표 비중 설정 (%)")
    weights = {}
    default_w = round(100 / len(tickers), 1)
    tot_w = 0
    for t in tickers:
        w = st.sidebar.number_input(f"{t} 비중 (%)", min_value=0.0, max_value=100.0, value=default_w, step=5.0)
        weights[t] = w / 100.0
        tot_w += w
        
    if abs(tot_w - 100.0) > 0.1:
        st.sidebar.warning(f"비중 합계가 100%가 되도록 맞춰주세요. (현재: {tot_w:.1f}%)")
        
    start_date = st.sidebar.date_input("시작일", datetime(2015, 1, 1))
    end_date = st.sidebar.date_input("종료일", datetime.today())
    
    init_balance = st.sidebar.number_input("초기 투자금 ($)", value=10000, step=1000)
    monthly_contrib = st.sidebar.number_input("월 적립금 ($)", value=500, step=100)
    rebalance_freq = st.sidebar.selectbox("리밸런싱 주기", ["매월", "매분기", "매년", "안함"])
    
    if st.sidebar.button("🚀 백테스트 실행"):
        if abs(tot_w - 100.0) <= 0.1:
            with st.spinner("데이터 수집 및 대체 지수 백필 처리 중..."):
                price_df = fetch_and_backfill_data(tickers, start_date, end_date)
                res_df, cagr, mdd, dd_series = run_backtest(price_df, weights, init_balance, monthly_contrib, rebalance_freq)
                
            col1, col2, col3 = st.columns(3)
            col1.metric("최종 자산 평가액", f"${res_df['Total'].iloc[-1]:,.2f}")
            col2.metric("CAGR (연평균 수익률)", f"{cagr*100:.2f}%")
            col3.metric("MDD (최대 낙폭)", f"{mdd*100:.2f}%")
            
            # 차트
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=res_df.index, y=res_df['Total'], mode='lines', name='포트폴리오 자산'))
            fig.update_layout(title="포트폴리오 자산 성장 추이", xaxis_title="날짜", yaxis_title="평가액 ($)")
            st.plotly_chart(fig, use_container_width=True)
            
            # 낙폭 차트
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(x=dd_series.index, y=dd_series * 100, mode='lines', fill='tozeroy', name='Drawdown'))
            fig_dd.update_layout(title="MDD (Drawdown) 추이", xaxis_title="날짜", yaxis_title="낙폭 (%)")
            st.plotly_chart(fig_dd, use_container_width=True)

# ------------------------------------------
# TAB 2: 리밸런싱 계산기
# ------------------------------------------
with tab2:
    st.header("💡 추가 입금액 반영 최적 매수 수량 계산기")
    st.write("주기적 리밸런싱 시 신규 투입금을 활용해 매도 없이(또는 최소화하여) 목표 비중을 맞춥니다.")
    
    add_cash = st.number_input("금회 추가 투입금 ($)", value=1000, step=100)
    
    st.subheader("현재 보유 현황 및 목표 비중 입력")
    
    input_data = []
    for t in tickers:
        col1, col2, col3 = st.columns(3)
        with col1:
            qty = st.number_input(f"{t} 현재 보유 수량", min_value=0, value=10, key=f"qty_{t}")
        with col2:
            # 최근 가격 자동 조회
            ticker_obj = yf.Ticker(t)
            hist = ticker_obj.history(period="5d")
            latest_price = float(hist['Close'].iloc[-1]) if not hist.empty else 100.0
            price = st.number_input(f"{t} 현재가 ($)", value=round(latest_price, 2), key=f"price_{t}")
        with col3:
            target_pct = weights.get(t, 0.33) * 100
            st.write(f"**{t} 목표 비중:** {target_pct:.1f}%")
            
        input_data.append({
            'Ticker': t,
            'Qty': qty,
            'Price': price,
            'TargetWeight': weights.get(t, 0.33)
        })
        
    if st.button("🧮 필요 매수 수량 계산"):
        curr_total = sum(d['Qty'] * d['Price'] for d in input_data)
        next_total = curr_total + add_cash
        
        results = []
        for d in input_data:
            curr_val = d['Qty'] * d['Price']
            target_val = next_total * d['TargetWeight']
            diff_val = target_val - curr_val
            
            # 매수 필요 수량 (소수점 버림)
            buy_qty = int(diff_val // d['Price']) if diff_val > 0 else 0
            needed_cost = buy_qty * d['Price']
            
            results.append({
                '티커': d['Ticker'],
                '현재 보유수량': d['Qty'],
                '현재 평가액 ($)': f"${curr_val:,.2f}",
                '목표 평가액 ($)': f"${target_val:,.2f}",
                '추천 추가 매수 수량': f"{buy_qty} 주",
                '필요 소요 금액 ($)': f"${needed_cost:,.2f}"
            })
            
        st.subheader("📋 리밸런싱 매수 주문 가이드")
        st.table(pd.DataFrame(results))