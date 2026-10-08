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

# 2. Mock 데이터: 청약 임박 공모주 종목 리스트 (청약시작일자 및 D-Day 추가)
UPCOMING_IPOS = {
    "바이오큐어": {
        "company_name": "바이오큐어",
        "sector": "바이오/제약",
        "offering_price": 28000,
        "competition_rate": 1420,
        "underwriter": "한국투자증권",
        "start_date": "2026-10-10",
        "d_day": "D-1 (청약 마감 임박)"
    },
    "클라우드원": {
        "company_name": "클라우드원",
        "sector": "IT/SaaS",
        "offering_price": 15000,
        "competition_rate": 890,
        "underwriter": "NH투자증권",
        "start_date": "2026-10-12",
        "d_day": "D-3"
    },
    "에코에너지": {
        "company_name": "에코에너지",
        "sector": "2차전지/소재",
        "offering_price": 42000,
        "competition_rate": 350,
        "underwriter": "미래에셋증권",
        "start_date": "2026-10-15",
        "d_day": "D-6"
    }
}

# 3. 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 🎯 1단계: 첫 화면 종목 선택 (청약시작일자 & D-Day 포함) ---
st.title("📈 IPO AI 투자 컨설턴트")
st.markdown("현재 청약 진행 및 임박한 공모주 목록입니다. **분석할 종목을 선택해 주세요.**")

# 콤보박스에 표시될 라벨 포맷 함수 (종목명 | D-Day | 청약시작일)
def format_ipo_option(company_key: str) -> str:
    info = UPCOMING_IPOS[company_key]
    return f"{info['company_name']} | [{info['d_day']}] 청약 시작일: {info['start_date']}"

selected_company_name = st.selectbox(
    "🔥 청약 임박 공모주 선택:",
    options=list(UPCOMING_IPOS.keys()),
    format_func=format_ipo_option,
    index=0
)

# 선택된 종목 객체 세팅
company_info = UPCOMING_IPOS[selected_company_name]

# 종목 변경 시 기존 AI 분석 결과 / 대화 내용 초기화 체크
if "last_selected_company" not in st.session_state or st.session_state["last_selected_company"] != selected_company_name:
    st.session_state["last_selected_company"] = selected_company_name
    st.session_state["report_data"] = None
    st.session_state.messages = []  # 이전 종목 대화 내용 초기화

# 선택된 종목 상단 요약 바
st.info(
    f"📌 **선택 종목:** {company_info['company_name']} | "
    f"**산업:** {company_info['sector']} | "
    f"**공모가:** {company_info['offering_price']:,}원 | "
    f"**기관경쟁률:** {company_info['competition_rate']}:1 | "
    f"**일정:** {company_info['start_date']} ({company_info['d_day']})"
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
# SECTION 1: 최종 시각화 요약 장표
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
    score = int(report.get("score", 0))

    # [1. 상단 핵심 요약 대시보드 (KPI Cards & 게이지)]
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            rec = report.get("recommendation", "N/A")
            st.caption("AI 투자 추천")
            if "적극" in rec:
                st.success(f"### 🎯 {rec}")
            elif "신중" in rec:
                st.warning(f"### ⚠️ {rec}")
            else:
                st.error(f"### ⛔ {rec}")

    with col2:
        with st.container(border=True):
            st.caption("AI 종합 평가 점수")
            st.metric(label="", value=f"{score} / 100점")
            # 점수 시각화 프로그레스 바
            st.progress(min(score, 100) / 100)

    with col3:
        with st.container(border=True):
            st.caption("추천 배정 전략")
            st.info(f"💡 **{report.get('strategy_type', '-')}**")

    st.markdown("###")

    # [2. 상세 분석 카드 영역]
    c_left, c_right = st.columns(2)

    with c_left:
        with st.container(border=True):
            st.markdown("#### 💡 AI 핵심 추천 근거")
            reasons = report.get("reasons", [])
            for idx, reason in enumerate(reasons, 1):
                st.markdown(f"**{idx}.** {reason}")

            st.divider()

            st.markdown("#### 🎯 전략 및 매도 가이드")
            st.markdown(f"**📌 배정 전략:** {report.get('strategy_desc', '-')}")
            st.markdown(f"**📈 매도 시점 가이드:** {report.get('sell_guide', '-')}")

    with c_right:
        with st.container(border=True):
            st.markdown("#### 📋 기업 기본 & 공모 주요 정보")
            
            # 메트릭 카드로 직관적 표시
            m1, m2 = st.columns(2)
            with m1:
                st.metric(label="확정 공모가", value=f"{company_info['offering_price']:,} 원")
            with m2:
                st.metric(label="기관 경쟁률", value=f"{company_info['competition_rate']} : 1")
                # 기관 경쟁률 게이지 (2000:1 기준)
                comp_ratio = min(company_info['competition_rate'] / 2000, 1.0)
                st.progress(comp_ratio)

            st.markdown("---")
            st.markdown(f"- **기업명:** `{company_info['company_name']}`")
            st.markdown(f"- **산업군:** `{company_info['sector']}`")
            st.markdown(f"- **주관사:** `{company_info['underwriter']}`")
            st.markdown(f"- **청약 시작일:** `{company_info['start_date']}` (`{company_info['d_day']}`)")

            st.divider()
            
            st.markdown("#### 🌐 최근 산업 & 시장 동향")
            st.caption(f"현재 **[{company_info['sector']}]** 테마 수급 현황 및 공모주 시장 분위기")
            st.warning("🔥 **시장 동향 summary:** 해당 섹터의 수급 집중 현상 및 최근 공모주 상장일 당일 변동성 확대를 고려하여 매도 가이드를 참고하세요.")

# ==========================================
# SECTION 2: 챗봇 형태 질의응답
# ==========================================
else:
    st.subheader(f"💬 {company_info['company_name']} AI Q&A 대화창")
    st.caption(f"선택하신 **{company_info['company_name']}** 공모주에 대해 궁금한 점을 자유롭게 질문해 주세요.")

    # 기존 대화 내역 출력
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 질문 입력
    if user_query := st.chat_input(f"{company_info['company_name']}에 대해 질문하세요 (예: 예상 수익률이나 청약할 만한 이유 알려줘):"):
        # 유저 메시지 저장 및 표시
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # AI 프롬프트 구성
        system_instruction = f"""
        당신은 공모주 투자 전문 AI 챗봇입니다.
        현재 고객이 문의한 청약 대상 기업 데이터:
        - 기업명: {company_info['company_name']}
        - 산업군: {company_info['sector']}
        - 확정 공모가: {company_info['offering_price']:,}원
        - 기관 경쟁률: {company_info['competition_rate']}:1
        - 주관사: {company_info['underwriter']}
        - 청약 시작일: {company_info['start_date']} ({company_info['d_day']})
        
        사용자의 질문에 친절하고 전문적으로 답변해 주세요.
        """

        # Gemini 스트리밍 응답 출력
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
