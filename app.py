import streamlit as st
import time

# 1. 웹 브라우저 탭 이름과 아이콘 설정
st.set_page_config(page_title="공모주 청약 Agent", page_icon="📈")

# 2. 메인 화면 제목
st.title("📈 공모주 청약 안내 & 분석 Agent")
st.caption("공모주 일정부터 기업 분석, 청약 전략까지 한눈에 확인하세요.")

# 3. 대화 기록 저장소 만들기 (새로고침해도 대화가 안 날아가게 함)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 공모주 청약 Agent입니다. 궁금하신 공모주 종목이나 일정을 물어보세요."}
    ]

# 4. 기존 대화 내용 화면에 표시하기
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 5. 사용자 질문 입력창
if user_input := st.chat_input("예: 이번 주 청약 가능한 공모주 알려줘"):
    # 유저가 입력한 글을 화면에 띄우고 저장
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # 6. 에이전트 답변 생성 (가짜 테스트 로직 -> 나중에 진짜 AI 연결할 곳)
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        # 실제 답변을 만드는 것처럼 보이게 애니메이션 효과
        with st.spinner("공모주 데이터를 분석 중입니다..."):
            time.sleep(1) # 1초 대기
            
            # 테스트용 예시 답변
            bot_reply = f"🤖 **[분석 결과]**\n\n'**{user_input}**'에 대한 공모주 정보입니다.\n- **추천 청약 여부**: 적극 참여\n- **주관사**: KB증권, NH투자증권\n- **공모가**: 15,000원\n\n*(현재 기본 틀 테스트 중이며, 6시간 내에 실제 AI 및 데이터가 연결될 예정입니다!)*"
            
            response_placeholder.markdown(bot_reply)
            
        # 답변을 저장소에 기록
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})