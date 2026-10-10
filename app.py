import streamlit as st
import pandas as pd
import numpy as np
from config import get_gemini_client, DEFAULT_GEMINI_MODEL
from tools.portfolio_tool import analyze_user_portfolio_strategy_with_ai, get_market_trends
from tools.user_db import get_all_users, get_user_holdings, insert_user_holding
from real_view import render_real_ipo

# 1. 페이지 기본 설정 및 Client 초기화
st.set_page_config(
    page_title="IPO AI 투자 AGENT",
    page_icon="📈",
    layout="wide"
)

client = None

st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    div[data-testid="stMetric"] {padding: 1px 4px;}
    div[data-testid="stMetricValue"] {font-size: 1.15rem !important;}
    div[data-testid="stMetricLabel"] {font-size: 0.8rem !important;}
    h4 {margin-top: 0.1rem !important; margin-bottom: 0.3rem !important; font-size: 1.05rem !important;}
    h5 {margin-top: 0.1rem !important; margin-bottom: 0.2rem !important; font-size: 0.95rem !important;}
    .stAlert {padding: 0.4rem 0.6rem !important;}
    .action-board {background-color: #f0f4f8; padding: 10px; border-radius: 8px; border-left: 5px solid #1E88E5;}
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 👤 [SIDEBAR] 고객 선택 & 매매내역 관리
# ==========================================
with st.sidebar:
    st.header("👤 고객 포트폴리오 관리")

    # 1. 고객 선택
    registered_users = get_all_users()
    user_options = registered_users + ["+ 신규 고객 직접 입력"]
    
    selected_option = st.selectbox("분석 대상 고객 선택:", user_options, index=0)
    
    if selected_option == "+ 신규 고객 직접 입력":
        current_user = st.text_input("새 고객명 입력:", value="홍길동").strip()
    else:
        current_user = selected_option

    st.success(f"현재 선택된 고객: **{current_user}**")
    st.divider()

    # 2. 현재 고객 보유 주식 현황
    user_holdings = get_user_holdings(current_user)
    with st.expander(f"📋 {current_user}님 보유 종목 ({len(user_holdings)}건)", expanded=False):
        if user_holdings:
            df_holdings = pd.DataFrame(user_holdings)[["stbd_name", "stbd_code", "hold_qty", "stbd_sector"]]
            df_holdings.columns = ["종목명", "코드", "보유수량", "업종"]
            st.dataframe(df_holdings, use_container_width=True, hide_index=True)
        else:
            st.caption("등록된 보유 종목이 없습니다. 아래에서 추가해 보세요.")

    # 3. 매매/보유 내역 입력 폼
    with st.expander("➕ 종목 매매/보유 내역 등록", expanded=False):
        with st.form("trade_info_form", clear_on_submit=True):
            st.caption(f"대상 고객: **{current_user}**")
            in_code = st.text_input("종목코드 (stbd_code)", value="A005930")
            in_name = st.text_input("종목명 (stbd_name)", value="삼성전자")
            in_qty = st.number_input("보유수량 (hold_qty)", min_value=1, value=100, step=10)
            in_sector = st.selectbox(
                "업종/섹터 (stbd_sector)",
                ["IT/반도체", "바이오/제약", "2차전지/소재", "IT/SaaS", "금융/지주", "자동차/운송", "일반/제조", "기타"]
            )

            submit_btn = st.form_submit_button("Supabase에 저장", use_container_width=True)
            if submit_btn:
                if in_code and in_name:
                    success = insert_user_holding(
                        user_name=current_user,
                        stbd_code=in_code,
                        stbd_name=in_name,
                        hold_qty=in_qty,
                        stbd_sector=in_sector
                    )
                    if success:
                        st.success(f"{in_name} 등록 완료!")
                        st.rerun()
                else:
                    st.error("종목코드와 종목명을 모두 입력해주세요.")


# ==========================================
# 📊 [MAIN] 데이터 모드 분기
# ==========================================
data_mode = st.radio("데이터 모드", ["실제 기업 분석", "데모 종목"], horizontal=True)

if data_mode == "실제 기업 분석":
    try:
        client = get_gemini_client() if st.secrets.get("GEMINI_API_KEY") else None
    except Exception:
        client = None
    render_real_ipo(client, user_name=current_user)
    st.stop()

client = get_gemini_client()
st.info(f"데모 모드: 현재 **{current_user}** 고객님의 포트폴리오가 추천 분석에 반영됩니다.")

# 2. 정량 Mock 데이터
UPCOMING_IPOS = {
    "바이오큐어": {
        "company_name": "바이오큐어",
        "sector": "바이오/제약",
        "market_share": 42.0,
        "market_share_avg": 15.0,
        "revenue_growth": 128.0,
        "revenue_growth_avg": 35.0,
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
        "company_name": "클라우드원",
        "sector": "IT/SaaS",
        "market_share": 35.0,
        "market_share_avg": 12.0,
        "revenue_growth": 85.0,
        "revenue_growth_avg": 28.0,
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
    },
    "에코에너지": {
        "company_name": "에코에너지",
        "sector": "2차전지/소재",
        "market_share": 18.5,
        "market_share_avg": 20.0,
        "revenue_growth": 45.0,
        "revenue_growth_avg": 40.0,
        "offering_price": 42000,
        "competition_rate": 350,
        "lockup_rate": 12.8,
        "float_rate": 38.5,
        "old_shares_rate": 25.0,
        "min_quantity": 10,
        "underwriter": "미래에셋증권",
        "fee": 2000,
        "account_open_rule": "청약 당일 비대면 개설 가능",
        "start_date": "2026-10-15",
        "listing_date": "2026-10-25",
        "d_day": "D-6"
    }
}

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 🎯 1단계: 상단 종목 선택 카드 ---
st.title("📈 IPO AI 투자 AGENT")

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
    st.session_state["report_data"] = None
    st.session_state.messages = []

view_mode = st.radio(
    "서비스 선택:",
    options=["1. 📊 한눈에 보는 맞춤 리포트", "2. 💬 AI 챗봇 1:1 Q&A"],
    horizontal=True,
    index=0
)

st.divider()

# ==========================================
# SECTION 1: 한눈에 보는 맞춤 리포트
# ==========================================
if view_mode == "1. 📊 한눈에 보는 맞춤 리포트":
    if "report_data" not in st.session_state or st.session_state["report_data"] is None:
        with st.spinner("맞춤 정량 데이터 및 수익 분석 중..."):
            st.session_state["report_data"] = analyze_user_portfolio_strategy_with_ai(
                client=client,
                user_id=current_user,
                company_info=company_info
            )

    report = st.session_state["report_data"]
    rec = report.get("recommendation", "청약 추천")
    strategy = report.get("strategy_type", "균등 배정 전용")
    traffic = report.get("traffic_lights", {"institution": "🟢", "lockup": "🟢", "financial": "🟢", "risks": "🟡"})

    # --- 실전 액션 보드 (치킨값 계산기 + 신호등 + 준비물) ---
    with st.container(border=True):
        st.markdown(f"#### 🍗 실전 투자 가이드: [{company_info['company_name']}]")

        min_deposit = int((company_info['offering_price'] * company_info['min_quantity']) * 0.5)
        day1_return_rate = report.get("predicted_day1_return", 150.0)
        expected_profit_per_share = int(company_info['offering_price'] * (day1_return_rate / 100.0) - company_info['fee'])
        chicken_count = round(expected_profit_per_share / 23000, 1)

        b1, b2, b3 = st.columns([1.2, 1.3, 1.5], gap="medium")

        with b1:
            st.metric(
                label="💵 최소 준비금 (균등 10주)",
                value=f"{min_deposit:,}원",
                help=f"공모가 {company_info['offering_price']:,}원 × 10주 × 증거금률 50%"
            )
            st.caption(f"🍗 1주 배정 시 예상 순익: **+{expected_profit_per_share:,}원** (치킨 {chicken_count}마리)")

        with b2:
            st.markdown("🚦 **투자 핵심 신호등**")
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
    # 1️⃣ 핵심 지표 vs 시장·업계 평균 비교
    # ==========================================
    with st.container(border=True):
        st.markdown("#### 1️⃣ 핵심 지표 vs 시장·업계 평균 비교")

        c_left, c_right = st.columns(2, gap="medium")

        with c_left:
            st.markdown("##### 🏢 기업 경쟁력 vs 업계 평균")
            sub1, sub2 = st.columns(2)
            with sub1:
                st.caption("📌 **시장 점유율 (%)**")
                share_df = pd.DataFrame({
                    "구분": [company_info["company_name"], "업계 평균"],
                    "점유율(%)": [company_info["market_share"], company_info["market_share_avg"]]
                }).set_index("구분")
                st.bar_chart(share_df, height=210, color=["#1E88E5"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{company_info['market_share']}% <span style='color:#888;'>(평균 {company_info['market_share_avg']}%)</span></div>", unsafe_allow_html=True)

            with sub2:
                st.caption("📌 **3년 매출 성장률 (%)**")
                growth_df = pd.DataFrame({
                    "구분": [company_info["company_name"], "업계 평균"],
                    "성장률(%)": [company_info["revenue_growth"], company_info["revenue_growth_avg"]]
                }).set_index("구분")
                st.bar_chart(growth_df, height=210, color=["#43A047"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>+{company_info['revenue_growth']}% <span style='color:#888;'>(평균 +{company_info['revenue_growth_avg']}%)</span></div>", unsafe_allow_html=True)

        with c_right:
            st.markdown("##### 🏛️ 기관 반응 vs 최근 공모주 평균")
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
    # 2️⃣ 고객 맞춤 진단 & Supabase 보유 DB 내역 표시
    # ==========================================
    with st.container(border=True):
        st.markdown(f"#### 2️⃣ {current_user} 고객 맞춤 정량 진단")
        
        # 1. 상단 진단 지표 카드
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("AI 진단 결과", rec)
        p2.metric("추천 청약 전략", strategy)
        p3.metric("과거 동일섹터 승률", "80.0%", delta="+17.5%p")
        p4.metric("평균 보유 기간", "2.0일", delta="-12.0일")

        st.divider()

        # 2. 🌟 선택된 고객의 실제 Supabase DB 보유 종목 내역 🌟
        st.markdown(f"##### 📋 {current_user} 고객 실시간 포트폴리오 (`USER_TRADE_INFO`)")
        
        # user_holdings는 사이드바에서 조회한 해당 고객의 실시간 DB 데이터
        if user_holdings:
            # 요약 메트릭
            total_qty = sum(float(item.get("hold_qty") or 0) for item in user_holdings)
            sectors = list({item.get("stbd_sector") for item in user_holdings if item.get("stbd_sector")})
            
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.caption(f"📌 **보유 종목 수:** {len(user_holdings)}개")
            m_col2.caption(f"📌 **총 보유 수량:** {int(total_qty):,}주")
            m_col3.caption(f"📌 **투자 섹터:** {', '.join(sectors)}")

            # DB 내역 테이블 렌더링
            df_display = pd.DataFrame(user_holdings)[["stbd_name", "stbd_code", "hold_qty", "stbd_sector"]]
            df_display.columns = ["종목명 (stbd_name)", "종목코드 (stbd_code)", "보유수량 (hold_qty)", "섹터 (stbd_sector)"]
            
            # 수량 정수 및 천단위 콤마 포맷 적용
            df_display["보유수량 (hold_qty)"] = df_display["보유수량 (hold_qty)"].apply(lambda x: f"{int(float(x)):,}주" if pd.notnull(x) else "-")

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
            st.caption("출처: Supabase PostgreSQL `USER_TRADE_INFO` 실시간 조회")
        else:
            st.info(f"💡 현재 **{current_user}** 고객님의 등록된 보유 주식 내역이 없습니다. 왼쪽 사이드바의 **'➕ 종목 매매/보유 내역 등록'**에서 종목을 추가해 보세요.")

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
            day1_ret = report.get("predicted_day1_return", 150.0)
            target_p = report.get("target_price", company_info['offering_price'] * 2.5)

            r1, r2 = st.columns(2)
            r1.metric("상장일 예상 수익률", f"+{day1_ret:.0f}%", delta="과열 상한")
            r2.metric("목표 주가", f"{int(target_p):,}원")

            future_dates = pd.date_range(start=pd.Timestamp.now(), periods=30, freq='D')
            base_p = company_info['offering_price'] * (1 + day1_ret / 100.0)
            predicted_prices = base_p + np.cumsum(np.random.normal(50, 300, 30))

            st.line_chart(pd.DataFrame({"예측 주가(원)": predicted_prices}, index=future_dates), height=130)

# ==========================================
# SECTION 2: 챗봇 형태 질의응답
# ==========================================
else:
    st.subheader(f"💬 {company_info['company_name']} AI Q&A ({current_user} 고객님 전용)")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input(f"{company_info['company_name']}에 대해 질문하세요:"):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        system_instruction = f"""
        당신은 {current_user} 고객님만을 위한 공모주 정량 분석 AI 챗봇입니다.
        종목: {company_info['company_name']}
        공모가: {company_info['offering_price']:,}원
        기관경쟁률: {company_info['competition_rate']}:1
        의무보유확약: {company_info['lockup_rate']}%
        시장점유율: {company_info['market_share']}%
        주관사: {company_info['underwriter']}

        초보 개미 투자자도 바로 이해할 수 있도록 명확한 수치로 간결하게 답변하세요.
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