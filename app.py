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

# 여백 축소용 커스텀 CSS (컴팩트 배치)
st.markdown("""
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 1.5rem;}
    div[data-testid="stMetric"] {padding: 2px 8px;}
    div[data-testid="stMetricValue"] {font-size: 1.25rem !important;}
    h4 {margin-top: 0.2rem !important; margin-bottom: 0.4rem !important;}
    .stAlert {padding: 0.5rem 0.8rem !important;}
    </style>
""", unsafe_allow_html=True)

# 2. Mock 데이터
UPCOMING_IPOS = {
    "바이오큐어": {
        "company_name": "바이오큐어",
        "sector": "바이오/제약",
        "business_summary": "암세포만 쏙 골라서 치료하는 신약을 개발하는 바이오 벤처 기업입니다.",
        "metrics_info": "국내 췌장암 치료제 1위 (점유율 42%), 3년 매출성장률 128%",
        "offering_price": 28000,
        "competition_rate": 1420,  # 경쟁률 (max ~2000 기준)
        "lockup_rate": 65.4,       # 락업 비율 (%)
        "underwriter": "한국투자증권",
        "start_date": "2026-10-10",
        "d_day": "D-1"
    },
    "클라우드원": {
        "company_name": "클라우드원",
        "sector": "IT/SaaS",
        "business_summary": "기업들이 데이터를 안전하게 보관하고 관리해주는 소프트웨어를 만듭니다.",
        "metrics_info": "공공기관 B2B 데이터 관리 1위 (점유율 35%)",
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
        "business_summary": "전기차가 오래 달릴 수 있도록 배터리 핵심 부품을 만드는 회사입니다.",
        "metrics_info": "세계 3위 전해액 생산기술, 완성차 납품 25%",
        "offering_price": 42000,
        "competition_rate": 350,
        "lockup_rate": 12.8,
        "underwriter": "미래에셋증권",
        "start_date": "2026-10-15",
        "d_day": "D-6"
    }
}

# 3. 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 🎯 1단계: 첫 화면 - 상단 컴팩트 종목 선택 카드 ---
st.title("📈 IPO AI 투자 컨설턴트")

with st.container(border=True):
    selected_company_name = st.radio(
        "🔥 **[필수 선택] 분석할 공모주 클릭:**",
        options=list(UPCOMING_IPOS.keys()),
        format_func=lambda k: f"📌 {UPCOMING_IPOS[k]['company_name']} ({UPCOMING_IPOS[k]['sector']}) | {UPCOMING_IPOS[k]['start_date']} [{UPCOMING_IPOS[k]['d_day']}]",
        horizontal=True,
        index=0
    )

company_info = UPCOMING_IPOS[selected_company_name]

# 종목 변경 시 기존 AI 분석 결과 / 대화 내용 초기화
if "last_selected_company" not in st.session_state or st.session_state["last_selected_company"] != selected_company_name:
    st.session_state["last_selected_company"] = selected_company_name
    st.session_state["report_data"] = None
    st.session_state.messages = []

# 선택 종목 요약 띠 (한 줄 컴팩트)
st.success(
    f"✅ **{company_info['company_name']}** | {company_info['sector']} | 공모가 {company_info['offering_price']:,}원 | 기관경쟁률 {company_info['competition_rate']}:1 | 락업 {company_info['lockup_rate']}% | {company_info['start_date']} ({company_info['d_day']})"
)

# 서비스 모드 선택
view_mode = st.radio(
    "서비스 선택:",
    options=["1. 📊 고객 맞춤 AI 요약 리포트", "2. 💬 AI 챗봇 1:1 질의응답"],
    horizontal=True,
    index=0
)

st.divider()

# ==========================================
# SECTION 1: 개인화 시각화 요약 리포트
# ==========================================
if view_mode == "1. 📊 고객 맞춤 AI 요약 리포트":
    user_name = "김투린"
    st.markdown(f"### 📊 {user_name} 고객님 맞춤 [{company_info['company_name']}] 3초 진단 리포트")

    if "report_data" not in st.session_state or st.session_state["report_data"] is None:
        with st.spinner(f"{user_name} 고객님의 매매 패턴 분석 중..."):
            st.session_state["report_data"] = analyze_user_portfolio_strategy_with_ai(
                client=client,
                user_id="user123",
                company_info=company_info
            )

    report = st.session_state["report_data"]
    rec = report.get("recommendation", "N/A")
    strategy = report.get("strategy_type", "-")

    # ==========================================
    # 1️⃣ [회사설명(좌) + 기관수치 시각화(우) 1개 Row 통합]
    # ==========================================
    with st.container(border=True):
        st.markdown(f"#### 1️⃣ 기업 핵심 요약 & 기관 반응 분석")
        
        col_left, col_right = st.columns([1, 1], gap="medium")
        
        # 👈 [LEFT]: 회사 설명 및 핵심 시장 지표
        with col_left:
            st.markdown("##### 🏢 어떤 회사인가요?")
            st.info(f"💡 {report.get('company_simple_summary', company_info['business_summary'])}")
            st.caption(f"🏆 **대표 수치:** {company_info.get('metrics_info', '-')}")

        # 👉 [RIGHT]: 기관 수치 시각화 (게이지) & 쉬운 풀이
        with col_right:
            st.markdown("##### 🏛️ 기관 투자자 반응 (3초 시각화)")
            
            # 경쟁률 게이지 (2000:1 기준)
            comp_val = min(company_info['competition_rate'] / 2000.0, 1.0)
            st.caption(f"🔥 **기관 경쟁률:** **{company_info['competition_rate']:,} : 1**")
            st.progress(comp_val)
            
            # 의무보유확약 게이지 (100% 기준)
            lockup_val = min(company_info['lockup_rate'] / 100.0, 1.0)
            st.caption(f"🔒 **의무보유확약(락업):** **{company_info['lockup_rate']}%**")
            st.progress(lockup_val)
            
            # 👦 초등학생 눈높이 쉬운 수치 해설
            inst_exp = report.get("institutional_explanation", "전문가들이 많이 줄을 섰고 바로 안 팔고 꼭 쥐고 있겠다고 약속했습니다.")
            st.success(f"👦 **[3초 해석]** {inst_exp}")

    st.markdown("<div style='margin-bottom: -10px;'></div>", unsafe_allow_html=True)

    # ==========================================
    # 2️⃣ 고객 맞춤 추천/비추천 사유
    # ==========================================
    with st.container(border=True):
        st.markdown(f"#### 2️⃣ {user_name} 고객님 맞춤 진단")
        
        col_rec1, col_rec2 = st.columns(2)
        with col_rec1:
            if "적극" in rec:
                st.markdown(f"🎯 **AI 추천:** <span style='color:#2e7d32; font-weight:bold; font-size:1.1rem;'>{rec}</span>", unsafe_allow_html=True)
            elif "신중" in rec:
                st.markdown(f"⚠️ **AI 추천:** <span style='color:#ed6c02; font-weight:bold; font-size:1.1rem;'>{rec}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"⛔ **AI 추천:** <span style='color:#d32f2f; font-weight:bold; font-size:1.1rem;'>{rec}</span>", unsafe_allow_html=True)
        
        with col_rec2:
            st.markdown(f"💡 **청약 전략:** <span style='color:#0288d1; font-weight:bold; font-size:1.1rem;'>{strategy}</span>", unsafe_allow_html=True)

        st.markdown(f"**📌 과거 패턴 분석:** {report.get('personal_reason', '-')}")
        st.markdown(f"**📈 AI 매도 가이드:** {report.get('sell_guide', '-')}")

    st.markdown("<div style='margin-bottom: -10px;'></div>", unsafe_allow_html=True)

    # ==========================================
    # 3️⃣ & 4️⃣ 시각화 영역 (차트 2열 배치)
    # ==========================================
    col_chart_left, col_chart_right = st.columns(2, gap="medium")

    with col_chart_left:
        with st.container(border=True):
            st.markdown("#### 3️⃣ 최근 1달 IPO 상장일 수익률 (%)")
            market_data = get_market_trends()
            ipo_df = pd.DataFrame(market_data["recent_ipo_performances"]).set_index("name")
            st.bar_chart(ipo_df["return_rate"], height=160)
            st.caption(" 최근 1달 공모주 상장일 평균 수익률 **+140%** (과열)")

    with col_chart_right:
        with st.container(border=True):
            st.markdown(f"#### 4️⃣ 최근 3달 [{company_info['sector']}] 주가 추이")
            dates = pd.date_range(end=pd.Timestamp.now(), periods=90, freq='D')
            
            if company_info['sector'] == "바이오/제약":
                trend = np.linspace(100, 145, 90) + np.random.normal(0, 3, 90)
            elif company_info['sector'] == "IT/SaaS":
                trend = np.linspace(100, 115, 90) + np.random.normal(0, 4, 90)
            else:
                trend = np.linspace(100, 85, 90) + np.random.normal(0, 2, 90)

            trend_df = pd.DataFrame({"주가지수": trend}, index=dates)
            st.line_chart(trend_df, height=160)
            st.caption(f" 최근 3개월 **{company_info['sector']}** 테마 주가 추이")

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
        당신은 {user_name} 고객님만을 위한 공모주 투자 전문 AI 챗봇입니다.
        현재 문의 종목 정보:
        - 기업명: {company_info['company_name']}
        - 산업군: {company_info['sector']}
        - 핵심 경쟁력: {company_info.get('metrics_info', '-')}
        - 확정 공모가: {company_info['offering_price']:,}원
        - 기관 경쟁률: {company_info['competition_rate']}:1
        - 의무보유확약 비율: {company_info['lockup_rate']}%
        - 주관사: {company_info['underwriter']}
        
        {user_name} 고객님의 질문에 친절하고 전문적으로 답변해 주세요.
        """

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                response = client.models.generate_content_stream(
                    model=DEFAULT_GEMINI_MODEL,
                    contents=f"{system_instruction}\n\n사용자 질문: {user_query}",
                    config={"temperature": 0.3}
                )

                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        response_placeholder.markdown(full_response + "▌")

                response_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"답변 생성 중 오류가 발생했습니다: {str(e)}")
