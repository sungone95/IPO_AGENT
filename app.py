import streamlit as st
import pandas as pd
import numpy as np
from config import get_gemini_client, DEFAULT_GEMINI_MODEL
from tools.portfolio_tool import analyze_user_portfolio_strategy_with_ai, get_market_trends

# 1. 페이지 기본 설정 및 Client 초기화
st.set_page_config(
    page_title="IPO AI 투자 컨설턴트",
    page_icon="📈",
    layout="wide"
)

client = get_gemini_client()

# 컴팩트 여백 및 스타일링
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    div[data-testid="stMetric"] {padding: 1px 4px;}
    div[data-testid="stMetricValue"] {font-size: 1.15rem !important;}
    div[data-testid="stMetricLabel"] {font-size: 0.8rem !important;}
    h4 {margin-top: 0.1rem !important; margin-bottom: 0.3rem !important; font-size: 1.05rem !important;}
    h5 {margin-top: 0.1rem !important; margin-bottom: 0.2rem !important; font-size: 0.95rem !important;}
    .stAlert {padding: 0.4rem 0.6rem !important;}
    </style>
""", unsafe_allow_html=True)

# 2. 정량 Mock 데이터
UPCOMING_IPOS = {
    "바이오큐어": {
        "company_name": "바이오큐어",
        "sector": "바이오/제약",
        "market_share": 42.0,
        "market_share_avg": 15.0,     # 업계 평균 점유율
        "revenue_growth": 128.0,
        "revenue_growth_avg": 35.0,   # 업계 평균 성장률
        "offering_price": 28000,
        "competition_rate": 1420,
        "lockup_rate": 65.4,
        "underwriter": "한국투자증권",
        "start_date": "2026-10-10",
        "d_day": "D-1"
    },
    "클라우드원": {
        "company_name": "클라우드원",
        "sector": "IT/SaaS",
        "market_share": 35.0,
        "market_share_avg": 12.0,
        "revenue_growth": 85.0,
        "revenue_growth_avg": 28.0,
        "offering_price": 15000,
        "competition_rate": 890,
        "lockup_rate": 42.1,
        "underwriter": "NH투자증권",
        "start_date": "2026-10-12",
        "d_day": "D-3"
    },
    "에코에너지": {
        "company_name": "에코에너지",
        "sector": "2차전지/소재",
        "market_share": 18.5,
        "market_share_avg": 20.0,
        "revenue_growth": 45.0,
        "revenue_growth_avg": 40.0,
        "offering_price": 42000,
        "competition_rate": 350,
        "lockup_rate": 12.8,
        "underwriter": "미래에셋증권",
        "start_date": "2026-10-15",
        "d_day": "D-6"
    }
}

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 🎯 1단계: 상단 종목 선택 카드 ---
st.title("📈 IPO AI 정량 투자 컨설턴트")

with st.container(border=True):
    selected_company_name = st.radio(
        "🔥 **[필수 선택] 분석 종목 클릭:**",
        options=list(UPCOMING_IPOS.keys()),
        format_func=lambda k: f"📌 {UPCOMING_IPOS[k]['company_name']} ({UPCOMING_IPOS[k]['sector']}) | 공모가 {UPCOMING_IPOS[k]['offering_price']:,}원 [{UPCOMING_IPOS[k]['d_day']}]",
        horizontal=True,
        index=0
    )

company_info = UPCOMING_IPOS[selected_company_name]
market_data = get_market_trends()

if "last_selected_company" not in st.session_state or st.session_state["last_selected_company"] != selected_company_name:
    st.session_state["last_selected_company"] = selected_company_name
    st.session_state["report_data"] = None
    st.session_state.messages = []

view_mode = st.radio(
    "서비스 선택:",
    options=["1. 📊 3초 비교 막대그래프 리포트", "2. 💬 AI 챗봇 1:1 Q&A"],
    horizontal=True,
    index=0
)

st.divider()

# ==========================================
# SECTION 1: 3초 비교 막대그래프 리포트
# ==========================================
if view_mode == "1. 📊 3초 비교 막대그래프 리포트":
    user_name = "김투린"

    if "report_data" not in st.session_state or st.session_state["report_data"] is None:
        with st.spinner("평균 비교 데이터 산출 중..."):
            st.session_state["report_data"] = analyze_user_portfolio_strategy_with_ai(
                client=client,
                user_id="user123",
                company_info=company_info
            )

    report = st.session_state["report_data"]
    rec = report.get("recommendation", "N/A")
    strategy = report.get("strategy_type", "-")

    # ==========================================
    # 1️⃣ 핵심 지표 vs 시장·업계 평균 비교 (개별 차트 분리)
    # ==========================================
    with st.container(border=True):
        st.markdown("#### 1️⃣ 핵심 지표 vs 시장·업계 평균 비교 (3초 스캔)")
        
        c_left, c_right = st.columns(2, gap="medium")
        
        # 👈 [LEFT]: 기업 지표 (시장점유율 / 매출성장률) 비교
        with c_left:
            st.markdown("##### 🏢 기업 경쟁력 vs 업계 평균")
            
            sub1, sub2 = st.columns(2)
            with sub1:
                st.caption("📌 **시장 점유율 (%)**")
                share_df = pd.DataFrame({
                    "구분": [company_info["company_name"], "업계 평균"],
                    "점유율(%)": [company_info["market_share"], company_info["market_share_avg"]]
                }).set_index("구분")
                st.bar_chart(share_df, height=210, color=["#1E88E5"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{company_info['market_share']}% <span style='color:#888;'>(평균 {company_info['market_share_avg']}%)</span></div>", unsafe_allow_html=True)

            with sub2:
                st.caption("📌 **3년 매출 성장률 (%)**")
                growth_df = pd.DataFrame({
                    "구분": [company_info["company_name"], "업계 평균"],
                    "성장률(%)": [company_info["revenue_growth"], company_info["revenue_growth_avg"]]
                }).set_index("구분")
                st.bar_chart(growth_df, height=210, color=["#43A047"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>+{company_info['revenue_growth']}% <span style='color:#888;'>(평균 +{company_info['revenue_growth_avg']}%)</span></div>", unsafe_allow_html=True)

        # 👉 [RIGHT]: 기관 반응 (경쟁률 / 의무보유확약) 비교
        with c_right:
            st.markdown("##### 🏛️ 기관 반응 vs 최근 공모주 평균")
            
            sub3, sub4 = st.columns(2)
            with sub3:
                st.caption("📌 **기관 경쟁률 (:1)**")
                comp_df = pd.DataFrame({
                    "구분": [company_info["company_name"], "공모주 평균"],
                    "경쟁률": [company_info["competition_rate"], market_data["avg_competition_rate"]]
                }).set_index("구분")
                st.bar_chart(comp_df, height=210, color=["#FB8C00"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{company_info['competition_rate']:,}:1 <span style='color:#888;'>(평균 {market_data['avg_competition_rate']:,}:1)</span></div>", unsafe_allow_html=True)

            with sub4:
                st.caption("📌 **의무보유확약 (%)**")
                lock_df = pd.DataFrame({
                    "구분": [company_info["company_name"], "공모주 평균"],
                    "확약비율(%)": [company_info["lockup_rate"], market_data["avg_lockup_rate"]]
                }).set_index("구분")
                st.bar_chart(lock_df, height=210, color=["#8E24AA"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{company_info['lockup_rate']}% <span style='color:#888;'>(평균 {market_data['avg_lockup_rate']}%)</span></div>", unsafe_allow_html=True)

    # ==========================================
    # 2️⃣ 고객 맞춤 진단 (수치 메트릭 카드)
    # ==========================================
    with st.container(border=True):
        st.markdown(f"#### 2️⃣ {user_name} 고객 맞춤 정량 진단")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("AI 진단 결과", rec)
        p2.metric("추천 청약 전략", strategy)
        p3.metric("과거 동일섹터 승률", "83.3%", delta="+20.8%p")
        p4.metric("평균 보유 기간", "1.5일", delta="-12.5일")

    # ==========================================
    # 3️⃣ & 4️⃣ 시장 동향 & AI 주가/수익률 예측
    # ==========================================
    st.markdown("#### 3️⃣ 시장 동향 & AI 주가/수익률 예측")
    
    col_a, col_b, col_c = st.columns([1, 1, 1.2], gap="small")

    with col_a:
        with st.container(border=True):
            st.markdown("##### 📉 최근 IPO 수익률 (%)")
            ipo_df = pd.DataFrame(market_data["recent_ipo_performances"]).set_index("name")
            st.bar_chart(ipo_df["return_rate"], height=130)

    with col_b:
        with st.container(border=True):
            st.markdown(f"##### 📈 최근 {company_info['sector']} 지수")
            dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
            sector_trend = np.linspace(100, 125, 30) + np.random.normal(0, 2, 30)
            st.line_chart(pd.DataFrame({"지수": sector_trend}, index=dates), height=130)

    with col_c:
        with st.container(border=True):
            st.markdown("##### 🚀 AI 상장 당일 수익률 & 주가 예측")
            day1_ret = report.get("predicted_day1_return", 150.0)
            target_p = report.get("target_price", company_info['offering_price'] * 2.5)
            
            r1, r2 = st.columns(2)
            r1.metric("상장일 예상 수익률", f"+{day1_ret:.0f}%", delta="과열 상한")
            r2.metric("목표 주가", f"{int(target_p):,}원")

            future_dates = pd.date_range(start=pd.Timestamp.now(), periods=30, freq='D')
            base_p = company_info['offering_price'] * (1 + day1_ret / 100.0)
            predicted_prices = base_p + np.cumsum(np.random.normal(50, 300, 30))
            
            st.line_chart(pd.DataFrame({"예측 주가(원)": predicted_prices}, index=future_dates), height=130)

# ==========================================
# SECTION 2: 챗봇 형태 질의응답
# ==========================================
else:
    user_name = "김투린"
    st.subheader(f"💬 {company_info['company_name']} AI Q&A ({user_name} 고객님 전용)")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input(f"{company_info['company_name']}에 대해 질문하세요:"):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        system_instruction = f"""
        당신은 {user_name} 고객님만을 위한 공모주 정량 분석 AI 챗봇입니다.
        종목: {company_info['company_name']}
        공모가: {company_info['offering_price']:,}원
        기관경쟁률: {company_info['competition_rate']}:1
        의무보유확약: {company_info['lockup_rate']}%
        시장점유율: {company_info['market_share']}%
        
        수치 데이터를 근거로 명확히 답변하세요.
        """

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                response = client.models.generate_content_stream(
                    model=DEFAULT_GEMINI_MODEL,
                    contents=f"{system_instruction}\n\n질문: {user_query}",
                    config={"temperature": 0.2}
                )

                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        response_placeholder.markdown(full_response + "▌")

                response_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
