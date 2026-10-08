import streamlit as st
from google.genai import types

from config import get_gemini_client
from tools.db_tool import sync_external_ipo_data, get_ipo_info_from_db, get_company_dict
from tools.portfolio_tool import analyze_user_portfolio_strategy_with_ai
from tools.report_tool import render_ipo_summary_card

# 1. Page Config 및 Client 준비
st.set_page_config(page_title="공모주 청약 Agent", page_icon="📈", layout="wide")
client = get_gemini_client()

# DB 초기 데이터 세팅
sync_external_ipo_data()

# 2. Sidebar
with st.sidebar:
    st.header("📌 주요 안내")
    st.info("💡 AI가 내부 DB와 고객의 투자 패턴을 종합 분석합니다.")
    
    st.subheader("⚡ 빠른 질문")
    if st.button("에이아이테크 분석해줘"):
        st.session_state.prompt_input = "에이아이테크 공모주 분석 및 맞춤 전략 알려줘"
    if st.button("바이오케어 분석해줘"):
        st.session_state.prompt_input = "바이오케어 공모주 분석해줘"

# 3. Main Header
st.title("📈 공모주 청약 안내 & 맞춤 분석 Agent")
st.caption("AI 기반 공모주 분석기 | 매매내역 기반 개인화 추천 리포트 제공")

# 4. Message State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 공모주 청약 분석 Agent입니다. 궁금하신 종목을 물어보세요!"}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 5. User Input
user_query = st.chat_input("예: 에이아이테크 청약 전략 분석해줘")
if "prompt_input" in st.session_state and st.session_state.prompt_input:
    user_query = st.session_state.prompt_input
    del st.session_state.prompt_input

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        # DB 맥락 로드
        db_context = get_ipo_info_from_db()

        system_instruction = f"""
        너는 대한민국 공모주 청약 전문 분석 에이전트야.
        
        [내부 DB 공모주 정보]
        {db_context}
        
        위 DB 정보를 참고하여 친절하고 전문적으로 답변해줘.
        """

        try:
            response = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=user_query,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3
                )
            )

            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)

        except Exception as e:
            full_response = f"❌ 답변 생성 중 오류가 발생했습니다: {str(e)}"
            response_placeholder.markdown(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

        # 6. 특정 종목 언급 시 AI 종합 분석 카드 생성 (B, C 툴 연동)
        target_company = None
        if "에이아이테크" in user_query:
            target_company = "에이아이테크"
        elif "바이오케어" in user_query:
            target_company = "바이오케어"

        if target_company:
            # 1) A의 DB에서 종목 정보 획득
            company_info = get_company_dict(target_company)
            if company_info:
                # 2) B의 AI 분석 실행 (user_id="user123")
                analysis_result = analyze_user_portfolio_strategy_with_ai(client, "user123", company_info)
                
                # 3) C의 UI 리포트 출력
                render_ipo_summary_card(company_info, analysis_result)
