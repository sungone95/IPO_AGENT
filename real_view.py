"""실제 증권사 DB(IPO_INFO_MASTER, 성과/업종 테이블) 기반 공모주 AI 분석 뷰 모듈."""
from __future__ import annotations

import streamlit as st
import pandas as pd
from tools.ipo_db import get_active_ipo_master_list, get_supabase_client
from tools.batch_issue_updater import run_batch_update_issues
from tools.user_db import get_user_profile_from_db
from tools.ipo_advisor import generate_ipo_recommendation_from_db


def _format_price(val) -> str:
    """공모가 안전 포맷팅 헬퍼 (문자열, 쉼표, None 방어)"""
    if not val:
        return "미확정"
    try:
        clean_num = str(val).replace(",", "").replace("원", "").strip()
        return f"{int(clean_num):,}원"
    except (ValueError, TypeError):
        return str(val)


def _render_market_trends_dashboard(target_sector_code: str):
    """
    표준 sector_code Key로 1:1 직접 조회하여 
    최근 상장 10개 종목 첫날 성과 및 동종 산업군 주가 추세를 렌더링합니다.
    """
    supabase = get_supabase_client()
    st.markdown("#### 📊 최근 공모주 시장 분위기 & 산업군 주가 추세")

    tab_recent, tab_sector = st.tabs(["🔥 최근 10개 공모주 첫날 수익률", "📈 동종 산업군 기간별 주가 흐름"])

    # --------------------------------------------------------------------------
    # 탭 1: 최근 상장 10개 종목 첫날 성과 (IPO_RECENT_PERFORMANCE)
    # --------------------------------------------------------------------------
    with tab_recent:
        try:
            res_ipo = supabase.table("IPO_RECENT_PERFORMANCE") \
                .select("stbd_name, day1_return_pct, day1_high_return_pct, listing_date, offering_price, close_price") \
                .order("listing_date", desc=True) \
                .limit(10) \
                .execute()

            if res_ipo.data:
                df_ipo = pd.DataFrame(res_ipo.data)
                avg_day1 = df_ipo["day1_return_pct"].mean()
                avg_high = df_ipo["day1_high_return_pct"].mean()

                m1, m2 = st.columns([1, 2])
                with m1:
                    st.metric("최근 10종목 평균 종가 수익률", f"+{avg_day1:.1f}%")
                    st.metric("상장일 장중 최고가 평균 수익률", f"+{avg_high:.1f}%")
                    st.caption("💡 공모가 대비 상장 첫날 장마감 기준 실측 평균 수익률입니다.")
                with m2:
                    chart_df = df_ipo.set_index("stbd_name")[["day1_return_pct", "day1_high_return_pct"]]
                    chart_df.columns = ["첫날 종가 수익률(%)", "첫날 장중 최고(%)"]
                    st.bar_chart(chart_df)

                with st.expander("📋 최근 10개 공모주 첫날 상세 성적표 보기"):
                    table_view = df_ipo[["stbd_name", "listing_date", "offering_price", "close_price", "day1_return_pct"]]
                    table_view.columns = ["종목명", "상장일", "공모가(원)", "첫날 종가(원)", "수익률(%)"]
                    st.dataframe(table_view, hide_index=True, use_container_width=True)
            else:
                st.caption("최근 상장 종목 성과 데이터가 없습니다.")
        except Exception as e:
            st.caption(f"최근 공모주 지표 로드 중 오류: {e}")

    # --------------------------------------------------------------------------
    # 탭 2: 표준 sector_code 기반 1:1 즉시 매칭 (SECTOR_TREND_PERFORMANCE)
    # --------------------------------------------------------------------------
    with tab_sector:
        try:
            # 🌟 복잡한 문자열 검색 없이 sector_code Key로 단일 행 1:1 즉각 조회
            query_code = target_sector_code if target_sector_code else "SEC_MEDIA"
            res_sector = supabase.table("SECTOR_TREND_PERFORMANCE") \
                .select("*") \
                .eq("sector_code", query_code) \
                .limit(1) \
                .execute()

            if res_sector.data:
                row = res_sector.data[0]
                sentiment_icon = "🟢" if row["market_sentiment"] == "강세" else ("🔴" if row["market_sentiment"] == "조정" else "🟡")

                st.info(f"{sentiment_icon} **[{row['sector_name']}]** 업종 평가: **{row['market_sentiment']}** (분류코드: `{row['sector_code']}` | 지수: `{row['benchmark_index']}`)")
                st.caption(f"💡 {row['trend_summary']}")

                # 4대 기간별 수익률 지표 카드
                p1, p2, p3, p4 = st.columns(4)
                p1.metric("최근 1주일", f"{float(row['return_1w_pct']):+}%")
                p2.metric("최근 1개월", f"{float(row['return_1m_pct']):+}%")
                p3.metric("최근 6개월", f"{float(row['return_6m_pct']):+}%")
                p4.metric("최근 1년", f"{float(row['return_1y_pct']):+}%")

                # 기간별 주가 수익률 추세 라인 차트
                trend_df = pd.DataFrame({
                    "기간": ["1주일", "1개월", "6개월", "1년"],
                    "누적 수익률(%)": [
                        float(row["return_1w_pct"]),
                        float(row["return_1m_pct"]),
                        float(row["return_6m_pct"]),
                        float(row["return_1y_pct"])
                    ]
                }).set_index("기간")
                st.line_chart(trend_df)
            else:
                st.caption(f"코드 `{query_code}`에 해당하는 산업군 주가 흐름 데이터가 없습니다.")
        except Exception as e:
            st.caption(f"산업군 주가 지표 로드 중 오류: {e}")


def _render_evidence(result: dict):
    """
    원천 JSON 덤프 대신 초보자도 직관적으로 검증할 수 있는 
    구조화된 팩트 체크 대시보드 뷰어 (영업이익률 미니 차트 포함)
    """
    with st.expander("🔍 분석 근거 원천 팩트 데이터 검증 (증권사 DB 기준)", expanded=False):
        st.caption("AI가 임의로 지어내지 않고 분석의 기초로 삼은 증권사 DB 공식 수치입니다.")

        ipo_terms = result.get("ipo_terms") or result.get("ipo_metrics") or {}
        fin_history = result.get("financial_history") or result.get("financials") or {}
        biz_analysis = result.get("business_analysis") or {}

        # 1. 공모 조건 명세표
        st.markdown("##### 📌 1. 확정 공모 조건 명세")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"- **기업명 / 업종:** {result.get('company_name', '-')} ({result.get('sector', '-')})")
            st.markdown(f"- **표준 산업분류코드:** `{result.get('sector_code', '-')}`")
            st.markdown(f"- **희망 공모가 밴드:** {ipo_terms.get('price_band') or '확인 필요'}")
        with c2:
            st.markdown(f"- **최종 확정 공모가:** {_format_price(ipo_terms.get('offering_price'))}")
            st.markdown(f"- **청약 일정:** {ipo_terms.get('subscription_date') or '미정'}")
            st.markdown(f"- **상장 예정일:** {ipo_terms.get('listing_date') or '미정'}")
        with c3:
            comp_txt = f"{float(ipo_terms.get('competition_rate')):,.1f} : 1" if ipo_terms.get('competition_rate') else "수요예측 전"
            lock_txt = f"{float(ipo_terms.get('lockup_rate'))}%" if ipo_terms.get('lockup_rate') else "확인 전"
            st.markdown(f"- **주관 증권사:** {ipo_terms.get('underwriter') or '공시 확인 필요'}")
            st.markdown(f"- **기관 경쟁률:** {comp_txt}")
            st.markdown(f"- **의무보유확약(락업):** {lock_txt}")

        st.divider()

        # 2. 최근 3개년 재무 실적 현황 및 영업이익률 미니 차트
        st.markdown("##### 📈 2. 최근 3개년 재무 실적 및 영업이익률 추이")
        if fin_history:
            fin_rows = []
            chart_dict = {}

            for year in sorted(fin_history.keys()):
                metrics = fin_history[year]
                rev_growth = metrics.get("revenue_growth_pct")
                op_margin = metrics.get("operating_margin_pct")
                debt_ratio = metrics.get("debt_ratio_pct")

                fin_rows.append({
                    "사업연도": f"{year}년",
                    "매출 성장률": f"{rev_growth:+.1f}%" if rev_growth is not None else "-",
                    "영업이익률": f"{op_margin:.1f}%" if op_margin is not None else "-",
                    "부채비율": f"{debt_ratio:.1f}%" if debt_ratio is not None else "-"
                })

                if op_margin is not None:
                    chart_dict[f"{year}년"] = float(op_margin)

            col_table, col_chart = st.columns([3, 2])
            with col_table:
                df_fin = pd.DataFrame(fin_rows)
                st.dataframe(df_fin, hide_index=True, use_container_width=True)

            with col_chart:
                if chart_dict:
                    df_op = pd.DataFrame(
                        list(chart_dict.values()), 
                        index=list(chart_dict.keys()), 
                        columns=["영업이익률(%)"]
                    )
                    st.bar_chart(df_op, use_container_width=True)
                    latest_margin = list(chart_dict.values())[-1]
                    status_text = "🟢 흑자 경영 유지 중" if latest_margin > 0 else "🔴 영업적자 (기술특례 등)"
                    st.caption(f"💡 최근 결산 기준 **{latest_margin:.1f}%** ({status_text})")
        else:
            st.info("등록된 3개년 재무 데이터가 없습니다.")

        st.divider()

        # 3. 사업 내용 및 위험 요인
        st.markdown("##### 🛡️ 3. 사업 내용 및 핵심 위험 팩트")
        col_biz, col_risk = st.columns(2)
        with col_biz:
            st.markdown("**💡 무슨 사업으로 돈을 버는가?**")
            st.write(biz_analysis.get("business_summary") or "등록된 사업 설명 없음")
            diff = biz_analysis.get("peer_differentiation")
            if diff and diff != "자료 없음":
                st.caption(f"**경쟁사 대비 차별점:** {diff}")

        with col_risk:
            st.markdown("**⚠️ 공시 서류 상 가장 큰 위험 요인은?**")
            st.write(biz_analysis.get("investment_risks") or "등록된 위험 공시 없음")
            sentiment = biz_analysis.get("market_sentiment")
            if sentiment and sentiment != "자료 없음":
                st.caption(f"**증권가 시장 분위기:** {sentiment}")


def _render_report(name: str, result: dict, client, user_name: str = "김성원"):
    """DART/DB 실데이터 + 초보자용 AI 진단 + 시장/산업 흐름 대시보드 렌더링"""
    ipo_terms = result.get("ipo_terms") or result.get("ipo_metrics") or {}
    biz_analysis = result.get("business_analysis") or {}
    sector = result.get("sector", "업종 미분류")
    sector_code = result.get("sector_code", "SEC_MEDIA")

    user_profile = get_user_profile_from_db(user_name=user_name)
    company_record = {
        "company_name": name,
        "sector": sector,
        "sector_code": sector_code,
        "raw_info": result
    }

    # 1. AI 1:1 맞춤 진단 결과 생성
    report = generate_ipo_recommendation_from_db(
        client=client,
        user_profile=user_profile,
        company_record=company_record
    )

    # [영역 1] 기업 핵심 공모 정보 카드
    with st.container(border=True):
        st.markdown(f"### 🏢 {name} 공모 정보 및 핵심 강점")
        underwriter_txt = ipo_terms.get("underwriter") or "공시 확인 필요"
        st.caption(f"업종: **{sector}** (표준코드: `{sector_code}`) | 청약 주관사: **{underwriter_txt}**")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("확정 공모가", _format_price(ipo_terms.get("offering_price")))
        c2.metric("기관 경쟁률", f"{float(ipo_terms.get('competition_rate')):,.1f}:1" if ipo_terms.get("competition_rate") else "확인 전")
        c3.metric(
            "기관 주식 미매도 약속",
            f"{float(ipo_terms.get('lockup_rate'))}%" if ipo_terms.get("lockup_rate") else "확인 전",
            help="상장일 기관들이 주식을 바로 팔지 않겠다고 약속한 비중입니다. 높을수록 첫날 급락을 방어해 줍니다."
        )
        c4.metric("상장 예정일", ipo_terms.get("listing_date") or "일정 확인 전")

        biz_desc = biz_analysis.get("business_summary")
        if biz_desc and biz_desc != "자료 없음":
            st.divider()
            st.markdown(f"**💡 무슨 일로 돈을 버는 회사인가요?**\n\n{biz_desc}")

        strengths = biz_analysis.get("strengths") or []
        if strengths:
            st.markdown("**🚀 이 회사의 핵심 강점 (차별화 포인트)**")
            for item in strengths:
                st.markdown(f"- {item}")

        latest_issues = biz_analysis.get("latest_news_issues", [])
        if latest_issues:
            st.divider()
            st.markdown("📰 **오늘 아침 수집된 최신 시장 반응 (3줄 요약)**")
            for issue in latest_issues:
                st.markdown(f"- {issue}")

    # [영역 2] 🌟 sector_code를 전달하여 1:1 정확한 산업군 차트 렌더링
    st.divider()
    with st.container(border=True):
        _render_market_trends_dashboard(target_sector_code=sector_code)

    # [영역 3] 초보자 1:1 맞춤 청약 가이드
    st.divider()
    with st.container(border=True):
        st.markdown(f"### 🎯 `{user_name}` 고객님 맞춤형 청약 진단")

        rec_color = "🟢" if "추천" in report.get("recommendation", "") else ("🔴" if "보류" in report.get("recommendation", "") else "🟡")
        r_col1, r_col2 = st.columns([1, 2])
        with r_col1:
            st.subheader(f"{rec_color} {report.get('recommendation', '신중 청약')}")
            st.caption(f"권장 청약 전략: **{report.get('strategy_type', '소액 균등')}**")
        with r_col2:
            t_lights = report.get("traffic_lights", {})
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("기관 관심도", t_lights.get("institution", "🟡"))
            t2.metric("첫날 급락방어", t_lights.get("lockup", "🟡"))
            t3.metric("회사 재무건전", t_lights.get("financial", "🟡"))
            t4.metric("최신 시장이슈", t_lights.get("issues", "🟡"))

        st.divider()
        st.markdown(f"**1. 내 기존 주식 바구니와의 궁합**\n\n{report.get('portfolio_match')}")
        st.markdown(f"**2. 회사 살림살이 안전성 (재무)**\n\n{report.get('financial_status')}")
        st.markdown(f"**3. 내 통장 잔고 맞춤 자금 전략**\n\n{report.get('capital_action')}")

        if report.get("morning_tip"):
            st.success(f"🔔 **상장일 아침 행동 가이드:** {report.get('morning_tip')}")


def _render_chat(name: str, result: dict, client):
    """선택 종목 1:1 AI 질의응답 챗봇"""
    st.markdown(f"#### 💬 `{name}` 공모주 무엇이든 물어보세요")
    st.caption("전문 용어 없이 초보자 눈높이로 쉽게 답변해 드립니다.")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_prompt := st.chat_input("예: 이 회사 상장 첫날 바로 파는 게 좋을까?"):
        st.session_state["chat_history"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            system_ctx = f"종목명: {name}, 업종: {result.get('sector')}, 표준코드: {result.get('sector_code')}, 공모정보: {result.get('ipo_terms')}, 재무/사업: {result.get('business_analysis')}"
            full_prompt = f"다음 공모주 데이터를 바탕으로 질문에 주식 초보자 눈높이로 친절하고 솔직하게 2~3문장으로 답하세요.\n\n[데이터]\n{system_ctx}\n\n[질문]\n{user_prompt}"
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            bot_reply = res.text.strip()
            st.markdown(bot_reply)
            st.session_state["chat_history"].append({"role": "assistant", "content": bot_reply})


def render_real_ipo(client, user_name: str = "김성원"):
    st.title("📈 IPO AI 투자 AGENT (실제 기업 분석)")

    # 사이드바: 관리자 패널
    with st.sidebar:
        st.markdown("### ⚙️ 데이터 관리자 패널")
        st.caption("공모주 일정/재무는 DB 데이터를 사용하며, 최신 시장 반응/이슈만 웹(Tavily)에서 수집합니다.")
        if st.button("🔄 최신 시장 이슈 즉시 업데이트", help="등록된 전 종목의 최신 언론/기관 반응을 Tavily로 갱신합니다."):
            with st.spinner("최신 시장 반응 및 뉴스 요약을 DB에 반영하는 중..."):
                run_batch_update_issues(client)
            st.success("✅ 최신 시장 이슈 업데이트 완료!")
            st.rerun()

    # 링크 섹션
    with st.container(border=True):
        st.markdown("##### 📌 공모주 청약 일정 & 공모 정보 확인 링크")
        link_col1, link_col2, link_col3 = st.columns(3)
        with link_col1:
            st.link_button("🏛️ KIND 공모일정 (KRX)", "https://kind.krx.co.kr/listinvstg/pubofrschdl.do?method=searchPubofrScholMain", use_container_width=True)
        with link_col2:
            st.link_button("📊 38커뮤니케이션 청약일정", "http://www.38.co.kr/html/fund/index.htm?o=k", use_container_width=True)
        with link_col3:
            st.link_button("🟢 네이버페이 증권 공모주", "https://finance.naver.com/sise/ipo.naver", use_container_width=True)

        ipo_list = get_active_ipo_master_list()
        if not ipo_list:
            st.warning("현재 DB에 등록된 활성 공모주 종목이 없습니다. 관리자 DB를 확인해 주세요.")
            return

        company_names = [item["company_name"] for item in ipo_list]
        name_to_meta = {item["company_name"]: item for item in ipo_list}

        name = st.selectbox(
            "분석할 공모주 선택",
            options=company_names,
            index=0 if company_names else None,
            help="종목명을 입력하면 DB에 등록된 종목이 필터링됩니다."
        )

        target_meta = name_to_meta.get(name, {})
        raw_info = target_meta.get("raw_info", {})
        terms = raw_info.get("ipo_terms", {})

        sector_str = target_meta.get("sector") or "미분류"
        sector_code_str = target_meta.get("sector_code") or "SEC_MEDIA"
        price_str = _format_price(terms.get("offering_price"))
        underwriter_str = terms.get("underwriter") or "공시 확인 필요"

        st.caption(f"업종: **{sector_str}** (`{sector_code_str}`) | 공모가: **{price_str}** | 주관사: **{underwriter_str}**")

    # 뷰 모드 선택
    view_mode = st.radio("서비스 선택:", ["1. 📊 한눈에 보는 맞춤 리포트", "2. 💬 AI 챗봇 1:1 Q&A"], horizontal=True)

    # 분석 버튼
    col_btn, _ = st.columns([1, 2])
    with col_btn:
        if st.button("🚀 선택 기업 분석 및 맞춤 진단", type="primary", use_container_width=True):
            st.session_state["analysis_request"] = name

    st.divider()

    # 화면 제어
    analyzed_target = st.session_state.get("analysis_request")
    if not analyzed_target or analyzed_target != name:
        with st.container(border=True):
            st.info(f"💡 상단에서 **[{name}]** 종목을 확인하신 후 **[🚀 선택 기업 분석 및 맞춤 진단]** 버튼을 클릭해 주세요.")
            st.markdown(f"""
            - **표준 산업분류 1:1 매칭**: 표준 코드(`{sector_code_str}`)를 통해 동종 산업군의 1주/1달/6개월/1년 수익률을 오차 없이 대조합니다.
            - **증권사 보유 실데이터 진단**: 공모가, 기관경쟁률, 락업비율, 3개년 재무제표 등 DB에 완비된 정보를 기반으로 분석합니다.
            - **1:1 고객 포트폴리오 대조**: `{user_name}` 고객님의 실제 보유 주식(`USER_TRADE_INFO`) 대비 분산/쏠림을 진단합니다.
            """)
        return

    # 데이터 바인딩
    result = {
        **raw_info,
        "company_name": name,
        "sector": sector_str,
        "sector_code": sector_code_str,
        "ipo_metrics": terms,
        "financials": raw_info.get("financial_history", {}),
        "business_analysis": raw_info.get("business_analysis", {}),
        "summary": {
            "business": raw_info.get("business_analysis", {}).get("business_summary", "공시 확인 필요"),
            "risks": raw_info.get("business_analysis", {}).get("investment_risks", "공시 확인 필요")
        },
        "strengths": raw_info.get("business_analysis", {}).get("strengths", []),
        "updated_at": raw_info.get("updated_at") or target_meta.get("update_time", ""),
        "_from_cache": True
    }

    st.caption(f"⚡ **증권사 마스터 DB 연동 완료** ({result.get('updated_at', '')} 기준 데이터)")

    # 렌더링
    if view_mode.startswith("1."):
        _render_report(name, result, client, user_name=user_name)
    else:
        _render_chat(name, result, client)

    _render_evidence(result)