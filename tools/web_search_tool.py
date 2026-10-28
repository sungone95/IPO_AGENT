"""Tavily Search API 및 Gemini를 활용한 IPO 실시간 시장/산업 심층 분석 모듈."""
from __future__ import annotations
import json
import streamlit as st
from tavily import TavilyClient
from config import get_gemini_client, DEFAULT_GEMINI_MODEL


def search_ipo_web_data(company_name: str, sector: str, client) -> dict:
    """
    DART 유무와 상관없이 무조건 웹 조사를 실행하여
    공모 조건 교차확인, 산업군 내 입지/강점, 증권가 시장 평가를 수집
    """
    tavily_key = st.secrets.get("TAVILY_API_KEY")
    if not tavily_key or not client:
        return {}

    try:
        tavily = TavilyClient(api_key=tavily_key)

        # 🌟 2개 트랙으로 최신 웹 정보 수집
        query_ipo = f"{company_name} 공모주 기관 수요예측 경쟁률 의무보유확약 공모가 상장일"
        query_market = f"{company_name} {sector} 시장점유율 경쟁사 대비 강점 피어그룹 수혜 전망"

        res_ipo = tavily.search(query=query_ipo, search_depth="basic", max_results=3)
        res_market = tavily.search(query=query_market, search_depth="basic", max_results=3)

        raw_results = res_ipo.get("results", []) + res_market.get("results", [])
        
        seen_urls = set()
        contexts = []
        for r in raw_results:
            url = r.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                contexts.append(f"[{r.get('title')}]\n{r.get('content')}")

        if not contexts:
            return {}

        prompt = f"""
당신은 주식 초보자에게 친절하게 설명해 주는 공모주 전문 멘토입니다.
제공된 실시간 웹 뉴스 및 증권 기사를 바탕으로 '{company_name}'(업종: {sector})에 대해 분석하세요.

[웹 검색 수집 자료]
{"".join(contexts)}

[추출 규칙]
1. 수치 지표(공모가, 경쟁률, 확약비율)는 텍스트에서 명확히 확인되는 경우만 숫자로 추출하고, 없으면 null을 반환하세요.
2. 'industry_strengths': 해당 산업군 내에서 동종업계 경쟁사 대비 갖는 실질적 경쟁 우위, 기술 장벽, 시장 점유율 팩트 (3~4개)
3. 'market_sentiment': 기관 투자자 및 증권가에서 바라보는 해당 종목의 객관적 시장 평가 및 투자 심리 (2문장)
4. 'peer_differentiation': 경쟁사(피어그룹) 대비 핵심 차별점 (1~2문장)

반드시 아래 JSON 포맷으로만 응답하세요:
{{
    "offering_price": 숫자 정수 또는 null,
    "competition_rate": 숫자 또는 null,
    "lockup_rate": 숫자 또는 null,
    "listing_date": "문자열 또는 null",
    "underwriter": "문자열 또는 null",
    "industry_strengths": [
        "산업군 내 핵심 강점 1",
        "산업군 내 핵심 강점 2",
        "산업군 내 핵심 강점 3"
    ],
    "market_sentiment": "시장 및 기관 투자자들의 평가 요약",
    "peer_differentiation": "경쟁사 대비 핵심 차별점"
}}
"""
        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL ,
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.1}
        )
        return json.loads(response.text.strip())
    except Exception as e:
        st.caption(f"Tavily 웹 시장 분석 건너뜀: {e}")
        return {}