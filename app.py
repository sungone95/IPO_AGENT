import streamlit as st
from google import genai
from google.genai import types

# 1. 페이지 설정
st.set_page_config(page_title="공모주 청약 Agent", page_icon="📈", layout="wide")

# 2. Gemini API 클라이언트 초기화
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception:
    st.error("⚠️ GEMINI_API_KEY가 설정되지 않았습니다. Streamlit Settings > Secrets를 확인해 주세요.")
    st.stop()

# 3. 사이드바 (주요 안내 및 빠른 질문 버튼)
with st.sidebar:
    st.header("📌 주요 안내")
    st.info("💡 공모주 청약 정보, 일정, 주관사, 균등/비례 청약 전략을 질문해 보세요.")
    
    st.subheader("⚡ 빠른 질문하기")
    if st.button("이번 달 공모주 일정 알려줘"):
        st.session_state.prompt_input = "이번 달 주요 공모주 청약 일정과 주관사 정리해줘"
    if st.button("균등/비례 배정 전략 팁"):
        st.session_state.prompt_input = "공모주 청약할 때 균등배정이랑 비례배정 차이와 전략을 알려줘"
    if st.button("공모주 청약 시 준비물"):
        st.session_state.prompt_input = "공모주 청약하기 전에 미리 준비해야 할 준비물이 뭐야?"

# 4. 메인 타이틀
st.title("📈 공모주 청약 안내 & 분석 Agent")
st.caption("AI 기반 공모주 분석기 | 기업 개요, 공모가, 주관사, 청약 전략까지 안내합니다.")

# 5. 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 공모주 청약 분석 Agent입니다. 궁금하신 종목이나 청약 질문을 자유롭게 해주세요!"}
    ]

# 6. 이전 대화 화면 출력
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 사이드바 버튼 클릭 처리
user_query = st.chat_input("예: 이번 주 공모주 청약 일정 알려줘")
if "prompt_input" in st.session_state and st.session_state.prompt_input:
    user_query = st.session_state.prompt_input
    del st.session_state.prompt_input

# 7. 질문 입력 시 Gemini API 호출 및 스트리밍 답변
if user_query:
    # 사용자 메시지 표시
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    # Agent 답변 처리
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        # 공모주 전문 분석가 페르소나 설정
        system_instruction = """
        너는 대한민국 공모주 청약 전문 분석 에이전트야.
        사용자가 공모주 종목이나 청약에 대해 물어보면 친절하고 전문적으로 답변해줘.
        
        답변할 때는 아래 구성을 권장해:
        1. 핵심 요약 (청약일, 공모가, 주관사 등)
        2. 기업 개요 및 관전 포인트
        3. 청약 전략 및 주의사항 (비등/균등 배정 팁)
        
        모르는 정보가 있거나 실시간 조회가 필요할 땐 정중하게 안내해줘.
        """

        try:
            # 1차 시도: 가장 안정적인 gemini-1.5-flash 모델 사용
            response = client.models.generate_content_stream(
                model="gemini-1.5-flash",
                contents=user_query,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
            )

            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)

        except Exception as e:
            # 503 과부하 또는 기타 오류 발생 시 2차 시도 (gemini-1.5-pro 백업)
            try:
                response = client.models.generate_content_stream(
                    model="gemini-1.5-pro",
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
            except Exception as inner_e:
                full_response = f"❌ 구글 API 서버 일시적 과부하입니다. 잠시 후 다시 시도해 주세요.\n(상세 오류: {str(inner_e)})"
                response_placeholder.markdown(full_response)

        # 답변 저장
        st.session_state.messages.append({"role": "assistant", "content": full_response})
