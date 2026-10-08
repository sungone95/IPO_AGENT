import streamlit as st
from config import get_gemini_client, DEFAULT_GEMINI_MODEL
from tools.get_data_tool import get_company_dict
from tools.portfolio_tool import analyze_user_portfolio_strategy_with_ai

# 1. 페이지 기본 설정 및 Client 초기화
st.set_page_config(
    page_title="IPO AI 투자 컨설턴트",
    page_icon="📈",
    layout="wide"
)

client = get_gemini_client()

# 2. 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. 데이터 로드 (예시 종목 지정)
company_info = get_company_dict()  # 기본 조회 기업 데이터

# --- 상단 타이틀 및 모드 선택 (Segmented Control / Radio) ---
st.title("📈 IPO AI 투자 컨설턴트")
st.caption(f"대상 종목: **{company_info.get('company_name', '종목명')}** | 현재 적용 모델: `{DEFAULT_GEMINI_MODEL}`")

# 2가지 모드 선택 화면 (버튼 스타일 radio)
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
    st.subheader("📊 AI 종합 투자 진단 리포트")
    
    # 리포트 생성 버튼 / 자동 로딩
    if st.button("🔄 리포트 새로고침 / AI 분석 실행", type="primary"):
        st.session_state["report_data"] = None

    if "report_data" not in st.session_state or st.session_state["report_data"] is None:
        with st.spinner("AI가 유저 데이터와 시장 동향을 분석 중입니다..."):
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
        st.write(f"**배정 전략:** {report.get('strategy_desc', '-')}")
        st.write(f"**매도 시점 가이드:** {report.get('sell_guide', '-')}")

    with c_right:
        st.markdown("#### 📋 기업 기본 & 공모 정보")
        st.write(f"- **기업명:** {company_info.get('company_name', '-')}")
        st.write(f"- **산업군:** {company_info.get('sector', '일반')}")
        st.write(f"- **확정 공모가:** {company_info.get('offering_price', 0):,}원")
        st.write(f"- **기관 경쟁률:** {company_info.get('competition_rate', 0)} : 1")
        st.write(f"- **주관사:** {company_info.get('underwriter', '-')}")

        st.markdown("---")
        st.markdown("#### 🌐 최근 공모주 및 산업군 동향")
        st.info("최근 공모주 시장은 **바이오/제약 테마 수급 폭주** 및 상장 당일 변동성 확대 양상을 보이고 있습니다.")

# ==========================================
# SECTION 2: 챗봇 형태 질의응답 (기존 화면)
# ==========================================
else:
    st.subheader(f"💬 {company_info.get('company_name', '종목')} AI Q&A 대화창")
    st.caption("공모주 청약, 기업 재무, 사업 모델 등 궁금한 점을 자유롭게 질문해보세요.")

    # 기존 대화 내역 출력
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 질문 입력
    if user_query := st.chat_input("질문을 입력하세요 (예: 이 기업의 주요 매출원은 뭐야?):"):
        # 유저 메시지 저장 및 표시
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # AI 프롬프트 구성 (기업 정보 문맥 포함)
        system_instruction = f"""
        당신은 공모주 투자 전문 AI 챗봇입니다.
        현재 상담 대상 종목 정보:
        - 기업명: {company_info.get('company_name')}
        - 산업군: {company_info.get('sector')}
        - 확정 공모가: {company_info.get('offering_price')}원
        
        사용자의 질문에 친절하고 정확하게 답변해주세요.
        """

        # Gemini 스트리밍 응답 출력
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                response = client.models.generate_content_stream(
                    model=DEFAULT_GEMINI_MODEL,
                    contents=user_query,
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
