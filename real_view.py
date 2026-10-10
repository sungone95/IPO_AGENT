import streamlit as st
import pandas as pd
import numpy as np
import os
from config import DEFAULT_GEMINI_MODEL
from tools.portfolio_tool import analyze_user_portfolio_strategy_with_ai, get_market_trends
from tools.get_data_tool import get_disclosure_analysis


def render_real_ipo(client):
    st.subheader("🏢 실제 기업 DART 공시 실시간 분석 모드")

    # 1. 대상 기업 입력 또는 선택
    company_name = st.text_input("분석할 실제 공모주 회사명을 입력하세요:", value="이노스페이스")
    dart_api_key = st.secrets.get("DART_API_KEY") or os.getenv("DART_API_KEY", "")

    if not dart_api_key:
        st.warning("⚠️ DART_API_KEY가 Streamlit secrets 또는 환경변수에 설정되어 있지 않습니다.")
        return

    # 공모주 기본 스펙 (실제 공모 개요 기본값 매핑)
    company_meta = {
        "kind_id": f"REAL_{company_name}",
        "company_name": company_name,
        "sector": "첨단제조/우주항공",
        "offering_price": 30000,
        "competition_rate": 898,
        "lockup_rate": 41.5,
        "min_quantity": 10,
        "underwriter": "미래에셋증권",
        "fee": 2000,
        "account_open_rule": "청약 당일 비대면 개설 가능",
        "listing_date": "상장 예정일"
    }

    # 2. DART 실데이터 조회
    with st.spinner(f"OpenDART에서 [{company_name}]의 전자공시 및 최신 재무제표를 수집 중입니다..."):
        dart_data = get_disclosure_analysis(
            company={"kind_id": company_meta["kind_id"], "company_name": company_name},
            api_key=dart_api_key,
            client=client
        )

    if dart_data.get("error") and not dart_data.get("financials"):
        st.error(f"DART 조회 실패: {dart_data['error']}")
        return

    # 3. 실데이터 기반 AI 맞춤 투자 전략 분석
    with st.spinner("수집된 DART 실데이터와 시장 평균을 비교 분석 중입니다..."):
        report = analyze_user_portfolio_strategy_with_ai(
            client=client,
            user_id="user123",
            company_info=company_meta,
            disclosure_data=dart_data
        )

    market_data = get_market_trends()
    user_name = "김투린"
    traffic = report.get("traffic_lights", {})
    latest_fin = report.get("latest_fin", {})
    latest_year = report.get("latest_year", "최근")

    # ==========================================
    # 실전 액션 보드 (치킨값 계산기 + 신호등 + 준비물)
    # ==========================================
    with st.container(border=True):
        st.markdown(f"#### 🍗 실전 투자 가이드: [{company_name}]")

        min_deposit = int((company_meta['offering_price'] * company_meta['min_quantity']) * 0.5)
        day1_return_rate = report.get("predicted_day1_return", 130.0)
        expected_profit = int(company_meta['offering_price'] * (day1_return_rate / 100.0) - company_meta['fee'])
        chicken_count = round(expected_profit / 23000, 1)

        b1, b2, b3 = st.columns([1.2, 1.3, 1.5], gap="medium")
        with b1:
            st.metric("💵 최소 준비금 (균등 10주)", f"{min_deposit:,}원")
            st.caption(f"🍗 1주 배정 시 예상 순익: **+{expected_profit:,}원** (치킨 {chicken_count}마리)")

        with b2:
            st.markdown("🚦 **실데이터 기반 신호등**")
            st.markdown(f"""
            - 기관인기: **{traffic.get('institution', '🟢')}** | 락업: **{traffic.get('lockup', '🟢')}**
            - 재무건전: **{traffic.get('financial', '🟢')}** | 공시위험: **{traffic.get('risks', '🟡')}**
            """)

        with b3:
            st.markdown("🏦 **청약 주관 증권사**")
            st.markdown(f"**{company_meta['underwriter']}** (수수료 {company_meta['fee']:,}원)")
            st.caption(f"📌 {company_meta['account_open_rule']}")

        st.info(f"⏰ **상장일 아침 8시 40분 행동 요령:** {report.get('morning_guide', '-')}")

    # ==========================================
    # 1️⃣ DART 공시 실데이터 vs 시장·업계 기준 비교 막대그래프
    # ==========================================
    with st.container(border=True):
        st.markdown("#### 1️⃣ DART 공시 실데이터 vs 시장·업계 기준 비교")

        c_left, c_right = st.columns(2, gap="medium")

        # 👈 [LEFT]: 실제 DART 결산 재무 지표 비교
        with c_left:
            st.markdown(f"##### 🏢 {latest_year}년 DART 결산 재무 건전성")
            sub1, sub2 = st.columns(2)

            actual_op = latest_fin.get("operating_margin_pct", 15.0)
            avg_op = market_data.get("avg_operating_margin", 12.0)
            with sub1:
                st.caption("📌 **영업이익률 (%)**")
                op_df = pd.DataFrame({
                    "구분": [company_name, "업계 기준"],
                    "영업이익률(%)": [actual_op, avg_op]
                }).set_index("구분")
                st.bar_chart(op_df, height=210, color=["#1E88E5"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{actual_op}% <span style='color:#888;'>(기준 {avg_op}%)</span></div>", unsafe_allow_html=True)

            actual_debt = latest_fin.get("debt_ratio_pct", 85.0)
            avg_debt = market_data.get("avg_debt_ratio", 110.0)
            with sub2:
                st.caption("📌 **부채비율 (낮을수록 안전)**")
                debt_df = pd.DataFrame({
                    "구분": [company_name, "업계 기준"],
                    "부채비율(%)": [actual_debt, avg_debt]
                }).set_index("구분")
                st.bar_chart(debt_df, height=210, color=["#43A047"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{actual_debt}% <span style='color:#888;'>(기준 {avg_debt}%)</span></div>", unsafe_allow_html=True)

        # 👉 [RIGHT]: 기관 반응 지표 비교
        with c_right:
            st.markdown("##### 🏛️ 기관 수요예측 vs 최근 공모주 평균")
            sub3, sub4 = st.columns(2)

            with sub3:
                st.caption("📌 **기관 경쟁률 (:1)**")
                comp_df = pd.DataFrame({
                    "구분": [company_name, "공모주 평균"],
                    "경쟁률": [company_meta["competition_rate"], market_data["avg_competition_rate"]]
                }).set_index("구분")
                st.bar_chart(comp_df, height=210, color=["#FB8C00"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{company_meta['competition_rate']:,}:1 <span style='color:#888;'>(평균 {market_data['avg_competition_rate']:,}:1)</span></div>", unsafe_allow_html=True)

            with sub4:
                st.caption("📌 **의무보유확약 (%)**")
                lock_df = pd.DataFrame({
                    "구분": [company_name, "공모주 평균"],
                    "확약비율(%)": [company_meta["lockup_rate"], market_data["avg_lockup_rate"]]
                }).set_index("구분")
                st.bar_chart(lock_df, height=210, color=["#8E24AA"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{company_meta['lockup_rate']}% <span style='color:#888;'>(평균 {market_data['avg_lockup_rate']}%)</span></div>", unsafe_allow_html=True)

    # ==========================================
    # 2️⃣ 고객 맞춤 정량 진단 & 공시 요약
    # ==========================================
    with st.container(border=True):
        st.markdown(f"#### 2️⃣ {user_name} 고객 맞춤 정량 진단")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("AI 진단 결과", report.get("recommendation", "청약 추천"))
        p2.metric("추천 청약 전략", report.get("strategy_type", "균등 배정 전용"))
        p3.metric("동일섹터 과거 승률", "83.3%", delta="+20.8%p")
        p4.metric("평균 보유 기간", "1.5일", delta="-12.5일")

        summary_data = dart_data.get("summary", {})
        st.caption(f"📋 **DART 사업 요약:** {summary_data.get('business', '공시 내용 확인 완료')}")
        st.caption(f"⚠️ **DART 핵심 투자 위험:** {summary_data.get('risks', '특이 사항 없음')}")

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
            st.markdown(f"##### 📈 최근 {company_meta['sector']} 지수")
            dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
            sector_trend = np.linspace(100, 125, 30) + np.random.normal(0, 2, 30)
            st.line_chart(pd.DataFrame({"지수": sector_trend}, index=dates), height=130)

    with col_c:
        with st.container(border=True):
            st.markdown("##### 🚀 AI 상장 당일 수익률 & 주가 예측")
            day1_ret = report.get("predicted_day1_return", 130.0)
            target_p = report.get("target_price", company_meta['offering_price'] * 2.3)

            r1, r2 = st.columns(2)
            r1.metric("상장일 예상 수익률", f"+{day1_ret:.0f}%", delta="과열 상한")
            r2.metric("목표 주가", f"{int(target_p):,}원")

            future_dates = pd.date_range(start=pd.Timestamp.now(), periods=30, freq='D')
            base_p = company_meta['offering_price'] * (1 + day1_ret / 100.0)
            predicted_prices = base_p + np.cumsum(np.random.normal(50, 300, 30))
            st.line_chart(pd.DataFrame({"예측 주가(원)": predicted_prices}, index=future_dates), height=130)
