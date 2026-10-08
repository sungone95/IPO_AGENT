import os
import sys

# 1. 파이썬 모듈 검색 경로에 프로젝트 루트 디렉터리 추가 (ImportError 방지)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from google.genai import types

from config import get_gemini_client, DEFAULT_GEMINI_MODEL

# tools/__init__.py (Option A) 덕분에 한 번에 깔끔하게 import 가능
from tools import (
    sync_external_ipo_data,
    get_ipo_info_from_db,
    get_company_dict,
    analyze_user_portfolio_strategy_with_ai,
    render_ipo_summary_card
)

# 2. Page Config 및 Gemini Client 초기화
st.set_page_config(page_title="공모주 청약 Agent", page_icon="📈", layout="wide")
client = get_gemini_client()

# DB 초기화 및 테스트 데이터 세팅
sync_external_ipo_data()

# 3. 사이드바
with st.sidebar:
    st.header("📌 주요 안내")
    st.info("💡 AI가 내부 DB 데이터와 고객의 과거 투자 패턴을 종합 분석합니다.")
    
    st.subheader("⚡ 빠른 질문하기")
    if st.button("에이아이테크 분석해줘"):
        st.session_state.prompt_input = "에이아이테크 공모주 분석 및 맞춤 청약 전략 알려줘"
    if st.button("바이오케어 분석해줘"):
        st.session_state.prompt_input = "바이오케어 공모주 분석해줘"

# 4. 메인 타이틀
st.title("📈 공모주 청약 안내 & 맞춤 분석 Agent")
st.caption("AI 기반 공모주 분석기 | 매매내역 기반 개인화 추천 리포트 제공")

# 5. 대화 세션 및 기록 관리
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 공모주 청약 분석 Agent입니다. 궁금하신 종목이나 청약 관련 질문을 편하게 해주세요!"}
    ]

# 이전 대화 기록 화면 출력
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 6. 사용자 입력 처리 (채팅창 또는 사이드바 버튼)
user_query = st.chat_input("예: 에이아이테크 청약 전략 분석해줘")
if "prompt_input" in st.session_state and st.session_state.prompt_input:
    user_query = st.session_state.prompt_input
    del st.session_state.prompt_input

# 7. 질의응답 및 AI 분석 실행
if user_query:
    # 사용자 메시지 기록 및 표시
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    # Agent 답변 처리
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        # DB에 저장된 공모주 맥락 정보 로드 (개발자 A 모듈)
        db_context = get_ipo_info_from_db()

        system_instruction = f"""
        너는 대한민국 공모주 청약 전문 분석 에이전트야.
        
        [내부 DB 공모주 정보]
        {db_context}
        
        사용자의 질문에 위 DB 정보를 참고하여 친절하고 전문적으로 답변해줘.
        """

        try:
            # Gemini 모델 스트리밍 응답 호출
            response = client.models.generate_content_stream(
                model=DEFAULT_GEMINI_MODEL,
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

        # 답변 세션에 저장
        st.session_state.messages.append({"role": "assistant", "content": full_response})

        # 8. 종목 관련 질문 시 맞춤형 AI 리포트/장표 자동 생성 (개발자 B, C 모듈)
        target_company = None
        if "에이아이테크" in user_query:
            target_company = "에이아이테크"
        elif "바이오케어" in user_query:
            target_company = "바이오케어"

        if target_company:
            # 1) DB에서 해당 종목 정보 가져오기 (개발자 A)
            company_info = get_company_dict(target_company)
            
            if company_info:
                # 2) 고객 데이터 + 시장동향 + 종목정보 종합 AI 분석 (개발자 B)
                analysis_result = analyze_user_portfolio_strategy_with_ai(client, "user123", company_info)
                
                # 3) UI 맞춤 리포트 장표 출력 (개발자 C)
                render_ipo_summary_card(company_info, analysis_result)
