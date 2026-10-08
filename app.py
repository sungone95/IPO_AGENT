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

# 2. Mock 데이터: 객관적 수치 정보(metrics_info) 추가
UPCOMING_IPOS = {
    "바이오큐어": {
        "company_name": "바이오큐어",
        "sector": "바이오/제약",
        "business_summary": "암세포만 쏙 골라서 치료하는 신약을 개발하는 바이오 벤처 기업입니다.",
        "metrics_info": "국내 췌장암 항체치료제 분야 점유율 1위 (국내 시장 42% 점유), 최근 3년 매출 성장률 128%",
        "offering_price": 28000,
        "competition_rate": 1420,
        "underwriter": "한국투자증권",
        "start_date": "2026-10-10",
        "d_day": "D-1 (청약 마감 임박)"
    },
    "클라우드원": {
        "company_name": "클라우드원",
        "sector": "IT/SaaS",
        "business_summary": "기업들이 컴퓨터 데이터를 안전하게 보관하고 관리해주는 소프트웨어를 만듭니다.",
        "metrics_info": "국내 공공기관 B2B 클라우드 데이터 관리 분야 1위, 국내 시장 점유율 35%",
        "offering_price": 15000,
        "competition_rate": 890,
        "underwriter": "NH투자증권",
        "start_date": "2026-10-12",
        "d_day": "D-3"
    },
    "에코에너지": {
        "company_name": "에코에너지",
        "sector": "2차전지/소재",
        "business_summary": "전기차가 더 오랫동안 달릴 수 있도록 배터리 핵심 부품을 만드는 회사입니다.",
        "metrics_info": "세계 3위 규모의 전해액 첨가제 생산 기술 보유, 글로벌 완성차 납품 비중 25%",
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

# --- 🎯 1단계: 첫 화면 - 강조된 종목 선택 섹션 ---
st.title("📈 IPO AI 투자 컨설턴트")

with st.container(border=True):
    st.markdown("### 🔥 **[필수 선택] 분석할 공모주를 먼저 클릭하세요!**")
    
    selected_company_name = st.radio(
        "청약 임박 종목 목록:",
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

# 선택된 종목 요약 안내 바
st.success(
    f"✅ **선택된 기업:** **{company_info['company_name']}** | "
    f"**산업:** {company_info['sector']} | "
    f"**공모가:** {company_info['offering_price']:,}원 | "
    f"**기관경쟁률:** {company_info['competition_rate']}:1 | "
    f"**일정:** {company_info['start_date']} ({company_info['d_day']})"
)

st.markdown("---")

# --- 🎯 2단계: 서비스 선택 ---
view_mode = st.radio(
    "원하시는 서비스를 선택하세요:",
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
    st.subheader(f"📊 {user_name} 고객님만을 위한 [{company_info['company_name']}] 종합 투자 진단")

    if st.button("🔄 리포트 새로고침 / AI 재분석", type="primary"):
        st.session_state["report_data"] = None

    if "report_data" not in st.session_state or st.session_state["report_data"] is None:
        with st.spinner(f"{user_name} 고객님의 매매 내역과 {company_info['company_name']} 종목 데이터를 분석 중입니다..."):
            st.session_state["report_data"] = analyze_user_portfolio_strategy_with_ai(
                client=client,
                user_id="user123",
                company_info=company_info
            )

    report = st.session_state["report_data"]

    # [상단 컴팩트 메트릭 요약]
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            rec = report.get("recommendation", "N/A")
            st.caption(f"👤 {user_name} 고객님 맞춤 AI 추천")
            if "적극" in rec:
                st.markdown(f"<h4 style='margin:0; color:#2e7d32;'>🎯 {rec}</h4>", unsafe_allow_html=True)
            elif "신중" in rec:
                st.markdown(f"<h4 style='margin:0; color:#ed6c02;'>⚠️ {rec}</h4>", unsafe_allow_html=True)
            else:
                st.markdown(f"<h4 style='margin:0; color:#d32f2f;'>⛔ {rec}</h4>", unsafe_allow_html=True)

    with c2:
        with st.container(border=True):
            st.caption("💡 추천 청약 및 배정 전략")
            st.markdown(f"<h4 style='margin:0; color:#0288d1;'>{report.get('strategy_type', '-')}</h4>", unsafe_allow_html=True)

    st.markdown("###")

    # [1️⃣ 종목 분석 (객관적 수치 지표 + 간결 2줄 요약)]
    with st.container(border=True):
        st.markdown(f"#### 1️⃣ 종목 분석: **{company_info['company_name']}**은 어떤 회사인가요?")
        
        # 객관적 핵심 지표 뱃지
        st.caption(f"🏆 **핵심 시장 지표:** {company_info.get('metrics_info', '-')}")
        
        # AI 초등학생 수준 2줄 쉬운 설명
        st.info(f"💡 {report.get('company_simple_summary', company_info['business_summary'])}")

    st.markdown("###")

    # [2️⃣ 고객 맞춤 추천/비추천 사유]
    with st.container(border=True):
        st.markdown(f"#### 2️⃣ {user_name} 고객님 맞춤 진단: 왜 이 추천이 나왔을까요?")
        st.markdown(f"**📌 과거 매매 패턴 기반 분석:**")
        st.write(report.get("personal_reason", "고객 매매 내역을 종합 분석 중입니다."))
        st.markdown(f"**📈 AI 매도 가이드:** {report.get('sell_guide', '-')}")

    st.markdown("###")

    # [3️⃣ & 4️⃣ 시각화 영역]
    col_left, col_right = st.columns(2)

    with col_left:
        with st.container(border=True):
            st.markdown("#### 3️⃣ 최근 1달간 IPO 종목 상장일 수익률 (%)")
            market_data = get_market_trends()
            ipo_df = pd.DataFrame(market_data["recent_ipo_performances"]).set_index("name")
            st.bar_chart(ipo_df["return_rate"])
            st.caption(" 최근 1달 공모주 시장 상장 당일 평균 수익률은 **+140%** 수준으로 매우 과열 상태입니다.")

    with col_right:
        with st.container(border=True):
            st.markdown(f"#### 4️⃣ 최근 3달간 [{company_info['sector']}] 산업군 주가 추이")
            dates = pd.date_range(end=pd.Timestamp.now(), periods=90, freq='D')
            
            if company_info['sector'] == "바이오/제약":
                trend = np.linspace(100, 145, 90) + np.random.normal(0, 3, 90)
            elif company_info['sector'] == "IT/SaaS":
                trend = np.linspace(100, 115, 90) + np.random.normal(0, 4, 90)
            else:
                trend = np.linspace(100, 85, 90) + np.random.normal(0, 2, 90)

            trend_df = pd.DataFrame({"주가지수": trend}, index=dates)
            st.line_chart(trend_df)
            st.caption(f" 최근 3개월간 **{company_info['sector']}** 테마의 종합 주가 흐름입니다.")

# ==========================================
# SECTION 2: 챗봇 형태 질의응답
# ==========================================
else:
    user_name = "김투린"
    st.subheader(f"💬 {company_info['company_name']} AI Q&A ({user_name} 고객님 전용)")
    st.caption(f"선택하신 **{company_info['company_name']}** 공모주에 대해 궁금한 점을 자유롭게 질문해 주세요.")

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
