import streamlit as st
from config import get_gemini_client, DEFAULT_GEMINI_MODEL
from tools.portfolio_tool import analyze_user_portfolio_strategy_with_ai

# 1. 페이지 기본 설정 및 Client 초기화
st.set_page_config(
    page_title="IPO AI 투자 컨설턴트",
    page_icon="📈",
    layout="wide"
)

client = get_gemini_client()

# 2. Mock 데이터: 청약 임박 공모주 종목 리스트
UPCOMING_IPOS = {
    "바이오큐어": {
        "company_name": "바이오큐어",
        "sector": "바이오/제약",
        "offering_price": 28000,
        "competition_rate": 1420,
        "underwriter": "한국투자증권",
        "d_day": "D-1 (청약 마감 임박)"
    },
    "클라우드원": {
        "company_name": "클라우드원",
        "sector": "IT/SaaS",
        "offering_price": 15000,
        "competition_rate": 890,
        "underwriter": "NH투자증권",
        "d_day": "D-2"
    },
    "에코에너지": {
        "company_name": "에코에너지",
        "sector": "2차전지/소재",
        "offering_price": 42000,
        "competition_rate": 350,
        "underwriter": "미래에셋증권",
        "d_day": "D-3"
    }
}

# 3. 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 🎯 1단계: 첫 화면 종목 선택 (Selectbox & Cards) ---
st.title("📈 IPO AI 투자 컨설턴트")
st.markdown("현재 청약 진행 및 임박한 공모주 목록입니다. **분석할 종목을 선택해 주세요.**")

# 상단 종목 선택 셀렉트박스
selected_company_name = st.selectbox(
    "🔥 청약 임박 공모주 선택:",
    options=list(UPCOMING_IPOS.keys()),
    index=0
)

# 선택된 종목 객체 세팅
company_info = UPCOMING_IPOS[selected_company_name]

# 종목 변경 시 기존 AI 분석 결과 / 대화 내용 초기화 체크
if "last_selected_company" not in st.session_state or st.session_state["last_selected_company"] != selected_company_name:
    st.session_state["last_selected_company"] = selected_company_name
    st.session_state["report_data"] = None
    st.session_state.messages = []  # 이전 종목 대화 내용 초기화

# 선택된 종목 요약 뱃지 표시
st.info(
    f"📌 **선택 종목:** {company_info['company_name']} | "
    f"**산업:** {company_info['sector']} | "
    f"**공모가:** {company_info['offering_price']:,}원 | "
    f"**기관경쟁률:** {company_info['competition_rate']}:1 | "
    f"**일정:** {company_info['d_day']}"
)

st.divider()

# --- 🎯 2단계: 분석 방식 선택 (리포트 vs 챗봇) ---
view_mode = st.radio(
    "원하시는 서비스를 선택하세요:",
    options=["1. 📊 한눈에 보는 AI 요약 리포트", "2. 💬 AI 챗봇 1:1 질의응답"],
    horizontal=True,
    index=0
)

st.divider()

# ==========================================
# SECTON 1: 최종 시각화 요약 장표
# ==========================================
if view_mode == "1. 📊 한눈에 보는 AI 요약 리포트":
    st.subheader(f"📊 {company_info['company_name']} AI 종합 투자 진단 리포트")
    
    # 리포트 생성 버튼 / 자동 로딩
    if st.button("🔄 리포트 새로고침 / AI 분석 실행", type="primary"):
        st.session_state["report_data"] = None

    if "report_data" not in st.session_state or st.session_state["report_data"] is None:
        with st.spinner(f"{company_info['company_name']} 데이터를 바탕으로 AI가 진단 중입니다..."):
            st.session_state["report_data"] = analyze_user_portfolio_strategy_with_ai(
                client=client,
                user_id="user123",
                company_info=company_info
            )

    report = st.session_state["report_data"]

    # [상단 대시보드 메트릭 카드]
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rec = report.get("recommendation", "N/A")
        if "적극" in rec:
            st.success(f"### 🎯 AI 추천: {rec}")
        elif "신중" in rec:
            st.warning(f"### ⚠️ AI 추천: {rec}")
        else:
            st.error(f"### ⛔ AI 추천: {rec}")

    with col2:
        st.metric(
            label="AI 종합 평가 점수",
            value=f"{report.get('score', 0)}점 / 100점"
        )

    with col3:
        st.info(f"💡 **추천 청약 전략**\n\n{report.get('strategy_type', '-')}")

    st.markdown("---")

    # [본문 상세 섹션]
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("#### 💡 AI 핵심 추천 근거")
        for reason in report.get("reasons", []):
            st.markdown(f"- {reason}")

        st.markdown("---")
        st.markdown("#### 🎯 전략 및 매도 가이드")
        st.
