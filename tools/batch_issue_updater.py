"""매일 2회 배치로 실행되어 최신 시장 이슈/언론 반응만 DB에 갱신하는 모듈."""
from __future__ import annotations
import json
from datetime import datetime
import streamlit as st
from tavily import TavilyClient
from tools.ipo_db import get_supabase_client

from config import DEFAULT_GEMINI_MODEL


def run_batch_update_issues(gemini_client):
    """DB에 등록된 모든 공모주의 최신 이슈를 Tavily로 수집하여 DB에 저장"""
    supabase = get_supabase_client()
    tavily_key = st.secrets.get("TAVILY_API_KEY")
    if not tavily_key or not gemini_client:
        return

    tavily = TavilyClient(api_key=tavily_key)

    # 1. DB의 전체 공모주 조회
    resp = supabase.table("IPO_INFO_MASTER").select("stbd_name, raw_info").execute()
    records = resp.data or []

    for row in records:
        name = row["stbd_name"]
        raw_info = row.get("raw_info") or {}

        try:
            # 최근 24시간~최신 뉴스 위주 검색
            query = f"{name} 공모주 청약 최신 뉴스 시장 반응 흥행 이슈"
            res = tavily.search(query=query, search_depth="basic", max_results=3)
            
            snippets = [f"[{r.get('title')}] {r.get('content')}" for r in res.get("results", [])]
            if not snippets:
                continue

            # Gemini로 초보자 눈높이 3줄 요약
            prompt = f"""
당신은 주식 초보자에게 친절하게 금융 뉴스를 전하는 앵커입니다.
제공된 실시간 뉴스를 읽고 '{name}' 공모주에 대한 최신 시장 분위기와 핵심 이슈를 초등학생도 이해할 수 있는 쉬운 문장으로 딱 3줄 요약하세요.
절대 전문 용어(오버행, 의무확약 등)를 쓰지 말고 일상어로 풀어쓰세요.

[뉴스 내용]
{"".join(snippets)}

반드시 아래 JSON 포맷으로만 응답하세요:
{{
    "latest_news_issues": [
        "쉬운 최신 이슈 1문장",
        "쉬운 최신 이슈 1문장",
        "쉬운 최신 이슈 1문장"
    ],
    "sentiment_summary": "현재 시장 분위기 한 줄 평가 (예: 기관들의 관심이 매우 뜨거운 상황입니다)"
}}
"""
            gemini_res = gemini_client.models.generate_content(
                model=DEFAULT_GEMINI_MODEL,
                contents=prompt,
                config={"response_mime_type": "application/json", "temperature": 0.1}
            )
            parsed = json.loads(gemini_res.text.strip())

            # 2. raw_info의 business_analysis 내 최신 이슈만 교체
            biz = raw_info.setdefault("business_analysis", {})
            biz["latest_news_issues"] = parsed.get("latest_news_issues", [])
            biz["market_sentiment"] = parsed.get("sentiment_summary", biz.get("market_sentiment", ""))
            raw_info["issues_updated_at"] = datetime.now().astimezone().isoformat()

            # 3. Supabase 업데이트
            supabase.table("IPO_INFO_MASTER").update({
                "raw_info": raw_info,
                "update_time": datetime.now().astimezone().isoformat()
            }).eq("stbd_name", name).execute()

        except Exception as e:
            st.caption(f"{name} 최신 이슈 배치 갱신 실패: {e}")