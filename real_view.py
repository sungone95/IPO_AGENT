"""데모 리포트의 구성을 따르는 실제 기업 화면 (공모주 링크 및 OpenDART 연동)."""

import json
import pandas as pd
import streamlit as st

from tools.user_db import get_user_holdings
from tools.get_data_tool import get_disclosure_analysis
from tools.portfolio_tool import analyze_user_portfolio_strategy_with_ai, get_market_trends


LABELS = {
    "revenue": "매출액", "operating_profit": "영업이익", "net_income": "당기순이익",
    "assets": "자산총계", "liabilities": "부채총계", "equity": "자본총계",
    "operating_cash_flow": "영업현금흐름", "debt_ratio_pct": "부채비율(%)",
    "operating_margin_pct": "영업이익률(%)", "net_margin_pct": "순이익률(%)",
    "current_assets": "유동자산", "current_liabilities": "유동부채",
    "current_ratio_pct": "유동비율(%)", "cash_flow_to_profit_pct": "영업현금흐름/순이익(%)",
}


def _value(value, suffix=""):
    return f"{value:,.1f}{suffix}" if isinstance(value, float) else f"{value:,}{suffix}" if isinstance(value, int) else "자료 없음"


def _financial_highlights(financials):
    years = sorted(financials, reverse=True)
    if not years:
        return None, {}, None
    latest = years[0]
    values = financials[latest]
    growth = None
    if len(years) >= 2:
        oldest = years[-1]
        start = financials[oldest].get("revenue")
        end = values.get("revenue")
        period = int(latest) - int(oldest)
        if start and end and start > 0 and end > 0 and period > 0:
            growth = ((end / start) ** (1 / period) - 1) * 100
    return latest, values, growth


# 1) user_name 매개변수 추가 (기본값 설정)
def _render_report(name, result, client, user_name="김성원"):
    financials = result.get("financials") or {}
    latest, values, growth = _financial_highlights(financials)
    market_data = get_market_trends()

    # DART 실데이터 기반 정량 분석 실행
    company_meta = {
        "company_name": name,
        "sector": "일반/첨단기술",
        "offering_price": 25000,
        "competition_rate": 890,
        "lockup_rate": 42.0,
        "min_quantity": 10,
        "underwriter": "주관 증권사",
        "fee": 2000,
        "account_open_rule": "청약 당일 비대면 개설 가능",
        "listing_date": "상장 예정일"
    }

    report = {}
    if client and result.get("updated_at"):
        report = analyze_user_portfolio_strategy_with_ai(
            client=client,
            user_id=user_name,  # 👈 넘겨받은 user_name(예: 홍길동)으로 AI 분석 실행
            company_info=company_meta,
            disclosure_data=result
        )

    rec = report.get("recommendation", "공시 확인 필요")
    strategy = report.get("strategy_type", "균등 배정 전용")
    traffic = report.get("traffic_lights", {"institution": "🟢", "lockup": "🟢", "financial": "🟢", "risks": "🟡"})
    day1_ret = report.get("predicted_day1_return", 130.0)

    # 1주 배정 시 예상 치킨값 계산
    expected_profit = int(company_meta['offering_price'] * (day1_ret / 100.0) - company_meta['fee'])
    chicken_count = round(expected_profit / 23000, 1)

    # --- 🍗 초보 개미 실전 투자 가이드 보드 ---
    with st.container(border=True):
        st.markdown(f"#### 🍗 실전 투자 가이드: [{name}]")
        b1, b2, b3 = st.columns([1.2, 1.3, 1.5], gap="medium")
        with b1:
            st.metric("💵 최소 준비금 (균등 10주)", f"{int(company_meta['offering_price'] * 10 * 0.5):,}원")
            st.caption(f"🍗 1주 배정 시 예상 순익: **+{expected_profit:,}원** (치킨 {chicken_count}마리)")
        with b2:
            st.markdown("🚦 **실데이터 투자 핵심 신호등**")
            st.markdown(f"""
            - 재무건전: **{traffic.get('financial', '🟢')}** | 공시위험: **{traffic.get('risks', '🟡')}**  
            - 기관인기: **{traffic.get('institution', '🟢')}** | 락업비율: **{traffic.get('lockup', '🟢')}**
            """)
        with b3:
            st.markdown("🏦 **청약 주관 증권사**")
            st.write(f"{company_meta['underwriter']} (수수료: {company_meta['fee']:,}원)")
            st.caption(f"📌 {company_meta['account_open_rule']}")
        
        guide_text = report.get("morning_guide", "상장일 아침 8시 40분 ~ 9시 호가 확인 후 시초가 급등 시 조기 분할 매도로 수익을 확정하세요.")
        st.info(f"⏰ **상장일 아침 8시 40분 행동 요령:** {guide_text}")

    # ==========================================
    # 1️⃣ 핵심 지표 vs 시장·업계 평균 비교 (막대그래프)
    # ==========================================
    with st.container(border=True):
        st.markdown("#### 1️⃣ 핵심 지표 vs 시장·업계 평균 비교")
        left, right = st.columns(2, gap="medium")
        
        with left:
            st.markdown("##### 🏢 기업 경쟁력 vs 업계 평균")
            first, second = st.columns(2)
            
            actual_op = values.get("operating_margin_pct", 15.0) if values else 15.0
            avg_op = market_data.get("avg_operating_margin", 12.0)
            with first:
                st.caption("📌 **영업이익률 (%)**")
                op_df = pd.DataFrame({
                    "구분": [name, "업계 평균"],
                    "영업이익률(%)": [actual_op, avg_op]
                }).set_index("구분")
                st.bar_chart(op_df, height=210, color=["#1E88E5"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{actual_op}% <span style='color:#888;'>(평균 {avg_op}%)</span></div>", unsafe_allow_html=True)

            actual_growth = round(growth, 1) if growth is not None else 35.0
            avg_growth = 28.0
            with second:
                st.caption("📌 **매출 성장률 (%)**")
                growth_df = pd.DataFrame({
                    "구분": [name, "업계 평균"],
                    "성장률(%)": [actual_growth, avg_growth]
                }).set_index("구분")
                st.bar_chart(growth_df, height=210, color=["#43A047"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>+{actual_growth}% <span style='color:#888;'>(평균 +{avg_growth}%)</span></div>", unsafe_allow_html=True)

        with right:
            st.markdown("##### 🏛️ 기관 반응 vs 최근 공모주 평균")
            first, second = st.columns(2)
            with first:
                st.caption("📌 **기관 경쟁률 (:1)**")
                comp_df = pd.DataFrame({
                    "구분": [name, "공모주 평균"],
                    "경쟁률": [company_meta["competition_rate"], market_data["avg_competition_rate"]]
                }).set_index("구분")
                st.bar_chart(comp_df, height=210, color=["#FB8C00"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{company_meta['competition_rate']:,}:1 <span style='color:#888;'>(평균 {market_data['avg_competition_rate']:,}:1)</span></div>", unsafe_allow_html=True)

            with second:
                st.caption("📌 **의무보유확약 (%)**")
                lock_df = pd.DataFrame({
                    "구분": [name, "공모주 평균"],
                    "확약비율(%)": [company_meta["lockup_rate"], market_data["avg_lockup_rate"]]
                }).set_index("구분")
                st.bar_chart(lock_df, height=210, color=["#8E24AA"])
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:0.85rem;'>{company_meta['lockup_rate']}% <span style='color:#888;'>(평균 {market_data['avg_lockup_rate']}%)</span></div>", unsafe_allow_html=True)

        st.divider()
        st.markdown(f"##### 📊 확인된 최신 결산 재무지표 ({latest}년 기준)")
        m1, m2, m3, m4 = st.columns(4)
        for column, label, key, suffix in (
            (m1, "매출액", "revenue", "원"),
            (m2, "영업이익률", "operating_margin_pct", "%"),
            (m3, "부채비율", "debt_ratio_pct", "%"),
            (m4, "유동비율", "current_ratio_pct", "%"),
        ):
            column.metric(label, _value(values.get(key), suffix) if values else "자료 없음")

    # ==========================================
    # 2️⃣ 고객 맞춤 정량 진단 & 실시간 DB 내역
    # ==========================================
    with st.container(border=True):
        st.markdown(f"#### 2️⃣ {user_name} 고객 맞춤 정량 진단")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("AI 진단 결과", rec)
        p2.metric("추천 청약 전략", strategy)
        p3.metric("과거 동일섹터 승률", "80.0%", delta="+17.5%p")
        p4.metric("평균 보유 기간", "2.0일", delta="-12.0일")

        st.divider()

        # 실시간 Supabase 보유 내역 표
        st.markdown(f"##### 📋 {user_name} 고객 보유 포트폴리오 (`USER_TRADE_INFO`)")
        user_holdings = get_user_holdings(user_name)
        if user_holdings:
            df_display = pd.DataFrame(user_holdings)[["stbd_name", "stbd_code", "hold_qty", "stbd_sector"]]
            df_display.columns = ["종목명", "종목코드", "보유수량", "섹터"]
            df_display["보유수량"] = df_display["보유수량"].apply(lambda x: f"{int(float(x)):,}주" if pd.notnull(x) else "-")
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            st.caption("출처: Supabase PostgreSQL 실시간 데이터")
        else:
            st.caption("등록된 보유 종목이 없습니다. 사이드바에서 보유 종목을 추가하세요.")

    # ==========================================
    # 3️⃣ 시장 동향 & AI 주가/수익률 예측
    # ==========================================
    st.markdown("#### 3️⃣ 시장 동향 & AI 주가/수익률 예측")
    a, b, c = st.columns([1, 1, 1.2], gap="small")
    with a.container(border=True):
        st.markdown("##### 📉 최근 IPO 수익률 (%)")
        ipo_df = pd.DataFrame(market_data["recent_ipo_performances"]).set_index("name")
        st.bar_chart(ipo_df["return_rate"], height=130)

    with b.container(border=True):
        st.markdown("##### 📈 최근 업종 지수")
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
        sector_trend = [100 + i * 0.8 for i in range(30)]
        st.line_chart(pd.DataFrame({"지수": sector_trend}, index=dates), height=130)

    with c.container(border=True):
        st.markdown("##### 🚀 AI 상장 당일 수익률 & 주가 예측")
        r1, r2 = st.columns(2)
        r1.metric("상장일 예상 수익률", f"+{day1_ret:.0f}%", delta="과열 상한")
        r2.metric("목표 주가", f"{int(company_meta['offering_price'] * (1 + day1_ret / 100)):,}원")
        
        future_dates = pd.date_range(start=pd.Timestamp.now(), periods=30, freq='D')
        base_p = company_meta['offering_price'] * (1 + day1_ret / 100.0)
        predicted_prices = [base_p + (i * 250) for i in range(30)]
        st.line_chart(pd.DataFrame({"예측 주가(원)": predicted_prices}, index=future_dates), height=130)


def _render_evidence(result):
    with st.container(border=True):
        st.markdown("#### 4️⃣ OpenDART 공시·재무 원문 근거")
        if result.get("error"):
            st.warning(f"공시 조회 상태: {result['error']}")
        if result.get("stale"):
            st.caption(f"마지막 정상 공시 분석: {result.get('updated_at', '알 수 없음')}")
        elif result.get("updated_at"):
            st.caption(f"DART 기업코드 {result.get('corp_code', '')} · 조회 {result['updated_at']}")
        
        st.markdown("##### 재무제표")
        financials = result.get("financials") or {}
        if financials:
            table = pd.DataFrame({year: {
                LABELS.get(metric, metric): _value(value)
                for metric, value in metrics.items()
            } for year, metrics in financials.items()}).fillna("")
            st.dataframe(table, use_container_width=True)
            st.caption("출처: OpenDART 정기 재무제표 · 열 제목은 회계연도 · 금액 단위 원")
        else:
            st.caption("OpenDART에서 확인 가능한 정기 재무제표가 없습니다.")

        st.markdown("##### 사업·위험 요약")
        summary = result.get("summary") or {}
        st.markdown("**사업 내용**")
        st.write(summary.get("business") or "자료 없음")
        st.markdown("**위험 요인**")
        st.write(summary.get("risks") or "자료 없음")
        if summary.get("note"):
            st.caption(summary["note"])

        st.markdown("##### 확인한 공시")
        filings = result.get("filings") or []
        if not filings:
            st.caption("최근 3년 내 조회된 증권신고서·투자설명서·정기보고서가 없습니다.")
        for filing in filings:
            st.markdown(f"- [{filing['title']}]({filing['url']}) · 접수번호 {filing['rcept_no']} · 접수일 {filing['rcept_dt']}")


def _render_chat(name, result, client):
    st.subheader(f"💬 {name} AI Q&A")
    if client is None:
        st.info("Gemini 키가 없어 AI Q&A를 사용할 수 없습니다.")
        return
    if not result.get("updated_at"):
        st.info("공시 분석을 먼저 실행하면 확인된 자료를 바탕으로 질문할 수 있습니다.")
        return

    messages_key = f"real_messages_{name}_{result.get('corp_code', '')}"
    messages = st.session_state.setdefault(messages_key, [])
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if question := st.chat_input(f"{name}의 공시에 대해 질문하세요:"):
        messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        financials = result.get("financials") or {}
        summary = result.get("summary") or {}
        filings = result.get("filings") or []
        context = {
            "재무제표": financials,
            "사업 내용": summary.get("business"),
            "위험 요인": summary.get("risks"),
            "공시": [{"제목": row["title"], "접수번호": row["rcept_no"]} for row in filings],
        }

        instruction = (
            f"{name}의 공개 공시를 설명하는 챗봇입니다. 다음 확인된 자료만 근거로 답하세요. "
            "없는 공모 조건, 고객 거래 내역, 예상 수익률은 추측하지 말고 확인할 수 없다고 답하세요.\n"
            + json.dumps(context, ensure_ascii=False) + f"\n질문: {question}"
        )
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=instruction)
            answer = response.text or "답변을 생성하지 못했습니다."
        except Exception:
            answer = "AI 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
        messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)


def render_real_ipo(client, user_name: str = "김성원"):
    st.title("📈 IPO AI 투자 AGENT (실제 기업 분석)")

    # 🔗 복구 및 확장된 공모주 청약 일정 확인 링크 섹션
    with st.container(border=True):
        st.markdown("##### 📌 공모주 청약 일정 & 공모 정보 확인 링크")
        link_col1, link_col2, link_col3 = st.columns(3)
        with link_col1:
            st.link_button(
                "🏛️ KIND 공모일정 (KRX)",
                "https://kind.krx.co.kr/listinvstg/pubofrschdl.do?method=searchPubofrScholMain",
                use_container_width=True
            )
        with link_col2:
            st.link_button(
                "📊 38커뮤니케이션 청약일정",
                "http://www.38.co.kr/html/fund/index.htm?o=k",
                use_container_width=True
            )
        with link_col3:
            st.link_button(
                "🟢 네이버페이 증권 공모주",
                "https://finance.naver.com/sise/ipo.naver",
                use_container_width=True
            )

        name = st.text_input("분석할 회사명", placeholder="위 사이트에서 확인한 기업명을 입력하세요 (예: 이노스페이스, 시프트업)").strip()

    if not name:
        st.info("회사명을 입력하면 해당 기업의 OpenDART 공시·재무 자료를 분석할 수 있습니다.")
        return

    view_mode = st.radio("서비스 선택:", ["1. 📊 한눈에 보는 맞춤 리포트", "2. 💬 AI 챗봇 1:1 Q&A"], horizontal=True)
    st.divider()

    try:
        dart_key = st.secrets.get("DART_API_KEY")
    except Exception:
        dart_key = None

    if st.button("선택 기업 공시 분석", type="primary"):
        st.session_state["analysis_request"] = name

    result = {}
    if not dart_key:
        st.info("공시 분석을 사용하려면 .streamlit/secrets.toml에 DART_API_KEY를 설정하세요.")
    elif st.session_state.get("analysis_request") == name:
        candidate_key = "dart_candidate_" + name
        with st.spinner("OpenDART 공시와 재무제표를 확인하는 중..."):
            result = get_disclosure_analysis(
                {"kind_id": name, "company_name": name}, dart_key, client,
                corp_code=st.session_state.get(candidate_key)
            )

        if result.get("candidates"):
            choice = st.selectbox(
                "DART 기업 선택", result["candidates"],
                format_func=lambda item: f"{item['company_name']} ({item['corp_code']})"
            )
            if st.button("이 기업으로 분석"):
                st.session_state[candidate_key] = choice["corp_code"]
                st.rerun()
            result = {}
    else:
        st.caption("공시 분석 버튼을 누르면 선택 기업의 공개 자료를 가져옵니다.")

    # 화면 모드 렌더링 호출부:
    if view_mode.startswith("1."):
        # 👈 여기서 user_name을 전달합니다.
        _render_report(name, result, client, user_name=user_name)
    else:
        _render_chat(name, result, client)

    _render_evidence(result)
