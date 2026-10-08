import streamlit as st
from typing import Dict, Any

def render_ipo_summary_card(company_info: Dict[str, Any], analysis_result: Dict[str, Any]):
    """Streamlit 대화창 하단에 시각적 리포트 카드를 렌더링"""
    st.markdown("---")
    st.subheader(f"📊 {company_info.get('company_name', '종목')} 맞춤 분석 리포트")
    
    # 상단 Key Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="🎯 최종 추천", 
            value=analysis_result.get("recommendation", "N/A"), 
            delta=f"{analysis_result.get('score', 0)}점"
        )
    with col2:
        st.metric(
            label="💡 배정 방식", 
            value=analysis_result.get("strategy_type", "N/A")
        )
    with col3:
        st.metric(
            label="💰 확정 공모가", 
            value=f"{company_info.get('offering_price', 0):,}원"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 하단 2개 컬럼 상세
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.markdown("### 📌 종목 개요")
        st.markdown(f"- **산업군:** {company_info.get('sector', '미정')}")
        st.markdown(f"- **주관사:** {company_info.get('underwriter', '미정')}")
        st.markdown(f"- **청약 일정:** {company_info.get('subscription_date', '미정')}")
        st.markdown(f"- **수요예측 경쟁률:** {company_info.get('competition_rate', 0)} : 1")
        st.markdown(f"- **의무보유 확약:** {company_info.get('lockup_rate', '0%')}")

    with right_col:
        st.markdown("### 🔍 개인화 분석 근거")
        for reason in analysis_result.get("reasons", []):
            st.markdown(f"✅ {reason}")
        
        st.info(f"💡 **배정 전략:** {analysis_result.get('strategy_desc', '')}")
        st.warning(f"📈 **매도 가이드:** {analysis_result.get('sell_guide', '')}")

    st.markdown("---")
