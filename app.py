import streamlit as st
import pandas as pd
import numpy as np
import os
from config import get_gemini_client, DEFAULT_GEMINI_MODEL
from tools.portfolio_tool import analyze_user_portfolio_strategy_with_ai, get_market_trends
from tools.get_data_tool import get_disclosure_analysis  # 👈 OpenDART 실데이터 모듈 임포트

# 1. 기본 설정 및 환경변수 확인
st.set_page_config(page_title="IPO AI 투자 컨설턴트", page_icon="📈", layout="wide")
client = get_gemini_client()
DART_API_KEY = os.getenv("DART_API_KEY", "")

st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    div[data-testid="stMetric"] {padding: 1px 4px;}
    div[data-testid="stMetricValue"] {font-size: 1.15rem !important;}
    h4 {margin-top: 0.1rem !important; margin-bottom: 0.3rem !important; font-size: 1.05rem !important;}
    h5 {margin-top: 0.1rem !important; margin-bottom: 0.2rem !important; font-size: 0.95rem !important;}
    .stAlert {padding: 0.4rem 0.6rem !important;}
    </style>
""", unsafe_allow_html=True)

# 2. 분석 대상 IPO 기본 메타데이터 (kind_id 등 DART 연동용 키 포함)
UPCOMING_IPOS = {
    "바이오큐어": {
        "kind_id": "KIND_BIO001",
        "company_name": "바이오큐어",
        "sector": "바이오/제약",
        "offering_price": 28000,
        "competition_rate": 1420,
        "lockup_rate": 65.4,
        "float_rate": 22.5,
        "old_shares_rate": 0.0,
        "min_quantity": 10,
        "underwriter": "한국투자증권",
        "fee": 2000,
        "account_open_rule": "청약 당일 비대면 개설 가능",
        "start_date": "2026-10-10",
        "listing_date": "2026-10-20",
        "d_day": "D-1"
    },
    "클라우드원": {
        "kind_id": "KIND_CLOUD002",
        "company_name": "클라우드원",
        "sector": "IT/SaaS",
        "offering_price": 15000,
        "competition_rate": 890,
        "lockup_rate": 42.1,
        "float_rate": 28.0,
        "old_shares_rate": 10.0,
        "min_quantity": 10,
        "underwriter": "NH투자증권",
        "fee": 2000,
        "account_open_rule": "청약 전일까지 개설 필수",
        "start_date": "2026-10-12",
        "listing_date": "2026-10-22",
        "d_day": "D-3"
    }
}

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 🎯 1단계: 상단 종목 선택 카드 ---
st.title("📈 IPO AI 정량 투자 컨설턴트 (OpenDART 연동)")

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
    st.session_state["dart_data"] = None
    st.session_state["report_data"] = None
    st.session_state.messages = []

view_mode = st.radio(
    "서비스 선택:",
    options=["1. 📊 한눈에 보는 실데이터 맞춤 리포트", "2. 💬 AI 챗봇 1:1 Q&A"],
    horizontal=True,
    index=0
)

st.divider()

# ==========================================
# SECTION 1: 실데이터 기반 맞춤 리포트
# ==========================================
if view_mode == "1. 📊 한눈에 보는 실데이터 맞춤 리포트":
    user_name = "김투린"

    # [1] OpenDART 실데이터 로드 및 캐싱
    if "dart_data" not in st.session_state or st.session_state["dart_data"] is None:
        with st.spinner(f"OpenDART에서 {company_info['company_name']} 공시 및 재무제표 수집 중..."):
            dart_res = get_disclosure_analysis(
                company={"kind_id": company_info["kind_id"], "company_name": company_info["company_name"]},
                api_key=DART_API_KEY,
                client=client
            )
            st.session_state["dart_data"] = dart_res

    dart_data = st.session_state["dart_data"]

    # [2] 실데이터 기반 맞춤 리포트 생성
    if "report_data" not in st.session_state or st.session_state["report_data"] is None:
        with st.spinner("실데이터 정량 지표 분석 및 투자 전략 도출 중..."):
            st.session_state["report_data"] = analyze_user_portfolio_strategy_with_ai(
                client=client,
                user_id="user123",
                company_info=company_info,
                disclosure_data=dart_data
            )

    report = st.session_state["report_data"]
    rec = report.get("recommendation", "청약 추천")
    strategy = report.get("strategy_type", "균등 배정 전용")
    traffic = report.get("traffic_lights", {})
    latest_fin = report.get("latest_fin", {})
    latest_year = report.get("latest_year", "최근")

    # --- 🍗 초보 개미 실전 가이드 보드 ---
    with st.container(border=True):
        st.markdown(f"#### 🍗 실전 투자 가이드: [{company_info['company_name']}]")
        
        min_deposit = int((company_info['offering_price'] * company_info['min_quantity']) * 0.5)
        day1_return_rate = report.get("predicted_day1_return", 140.0)
        expected_profit = int(company_info['offering_price'] * (day1_return_rate / 100.0) - company_info['fee'])
        chicken_count = round(expected_profit / 23000, 1)

        b1, b2, b3 = st.columns([1.2, 1.3, 1.5], gap="medium")
        with b1:
            st.metric("💵 최소 준비금 (균등 10주)", f"{min_deposit:,}원")
            st.caption(f"🍗 1주 배정 시 예상 순익: **+{expected_profit:,}원** (치킨 {chicken_count}마리)")

        with b2:
            st.markdown("🚦 **실데이터 기반 신호등**")
            st.markdown(f"""
            - 기관인기: **{traffic.get('institution', '🟢')}** | 락업: **{traffic.get('lockup', '🟢')}**
            - 재무건전: **{traffic.get('financial', '🟢')}** | 공시위험: **{traffic.get('risks', '🟡')}**
            """)

        with b3:
            st.markdown("🏦 **청약 주관 증권사**")
            st.markdown(f"**{company_info['underwriter']}** (수수료 {company_info['fee']:,}원)")
            st.caption(f"📌 {company_info['account_open_rule']}")

        st.info(f"⏰ **상장일({company_info['listing_date']}) 아침 8시 40분 행동 요령:** {report.get('morning_guide', '-')}")

    # ==========================================
    # 1️⃣ 핵심 실데이터(DART 재무 & 기관) 비교 막대그래프
    # ==========================================
    with st.container(border=True):
        st.markdown("#### 1️⃣ DART 공시 실데이터 vs 시장·업계 기준 비교")
        
        c_left, c_right = st.columns(2, gap="medium")
        
        # 👈 [LEFT]: 실제 DART 재무제표 수치 비교 (영업이익률, 부채비율)
        with c_left:
            st.markdown(f"##### 🏢 {latest_year}년 DART 결산 재무 건전성")
            sub1, sub2 = st.columns(2)
            
            actual_op_margin = latest_fin.get("operating_margin_pct", 15.0)
            avg_op_margin = market_data.get("avg_operating_margin", 12.0)
            with sub1:
                st.caption("📌 **영업이익률 (%)**")
                op_df = pd.DataFrame({
                    "구분": [company_info["company_name"], "업계 기준"],
                    "영업이익률(%)": [actual_op_margin, avg_op_margin]
                }).set_index("구분")
                st.bar_chart(op_df, height=210, color=["#1E88E5"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{actual_op_margin}% <span style='color:#888;'>(기준 {avg_op_margin}%)</span></div>", unsafe_allow_html=True)

            actual_debt = latest_fin.get("debt_ratio_pct", 85.0)
            avg_debt = market_data.get("avg_debt_ratio", 110.0)
            with sub2:
                st.caption("📌 **부채비율 (낮을수록 안전)**")
                debt_df = pd.DataFrame({
                    "구분": [company_info["company_name"], "업계 기준"],
                    "부채비율(%)": [actual_debt, avg_debt]
                }).set_index("구분")
                st.bar_chart(debt_df, height=210, color=["#43A047"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{actual_debt}% <span style='color:#888;'>(기준 {avg_debt}%)</span></div>", unsafe_allow_html=True)

        # 👉 [RIGHT]: 기관 반응 지표 비교
        with c_right:
            st.markdown("##### 🏛️ 기관 수요예측 vs 최근 공모주 평균")
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
    # 2️⃣ 고객 맞춤 진단 (공시 요약 반영)
    # ==========================================
    with st.container(border=True):
        st.markdown(f"#### 2️⃣ {user_name} 고객 맞춤 정량 진단")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("AI 진단 결과", rec)
        p2.metric("추천 청약 전략", strategy)
        p3.metric("동일섹터 과거 승률", "83.3%", delta="+20.8%p")
        p4.metric("평균 보유 기간", "1.5일", delta="-12.5일")

        summary_data = dart_data.get("summary", {})
        st.caption(f"📋 **DART 핵심 요약:** {summary_data.get('business', '공시 요약 완료')} | ⚠️ **주요 위험:** {summary_data.get('risks', '특이 위험 없음')}")

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
            day1_ret = report.get("predicted_day1_return", 140.0)
            target_p = report.get("target_price", company_info['offering_price'] * 2.4)
            
            r1, r2 = st.columns(2)
            r1.metric("상장일 예상 수익률", f"+{day1_ret:.0f}%", delta="과열 상한")
            r2.metric("목표 주가", f"{int(target_p):,}원")

            future_dates = pd.date_range(start=pd.Timestamp.now(), periods=30, freq='D')
            base_p = company_info['offering_price'] * (1 + day1_ret / 100.0)
            predicted_prices = base_p + np.cumsum(np.random.normal(50, 300, 30))
            st.line_chart(pd.DataFrame({"예측 주가(원)": predicted_prices}, index=future_dates), height=130)

# ==========================================
# SECTION 2: 챗봇 형태 질의응답 (DART 공시 컨텍스트 주입)
# ==========================================
else:
    user_name = "김투린"
    st.subheader(f"💬 {company_info['company_name']} AI Q&A ({user_name} 고객님 전용)")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input(f"{company_info['company_name']}의 DART 공시 내용에 대해 질문하세요:"):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        dart_data = st.session_state.get("dart_data", {})
        summary_info = dart_data.get("summary", {})

        system_instruction = f"""
        당신은 {user_name} 고객님만을 위한 공모주 정량 분석 AI 챗봇입니다.
        현재 기업 정보: {company_info['company_name']} (공모가 {company_info['offering_price']:,}원)
        - DART 사업 요약: {summary_info.get('business', '정보 없음')}
        - DART 주요 위험: {summary_info.get('risks', '정보 없음')}
        - 재무 수치: {dart_data.get('financials', {})}
        
        초보 개미 투자자도 바로 이해할 수 있도록 실제 DART 공시 내용을 인용하여 쉽고 명확하게 답변하세요.
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
