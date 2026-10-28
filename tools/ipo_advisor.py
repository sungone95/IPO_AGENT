"""DB 실데이터(고객 계좌 + 종목 마스터 + 배치 최신 이슈) 100% 기반 초보자 맞춤 진단 모듈."""
from __future__ import annotations
import json
from google.genai import types

from config import DEFAULT_GEMINI_MODEL


def generate_ipo_recommendation_from_db(
    client,
    user_profile: dict,
    company_record: dict
) -> dict:
    """외부 API 호출 없이 DB에 완비된 데이터만으로 즉각 초보자 맞춤 진단 생성"""
    if client is None:
        return {"recommendation": "진단 불가", "one_line_verdict": "AI 엔진 미설정"}

    # 1. DB에서 꺼낸 고객 정보
    user_name = user_profile.get("user_name", "고객")
    user_holdings = user_profile.get("holdings", [])
    user_sectors = user_profile.get("holding_sectors", [])
    risk_profile = user_profile.get("risk_profile", "안정형")
    total_cash = float(user_profile.get("total_cash", 0.0))

    # 2. DB에서 꺼낸 종목 정보 (공모조건, 재무, 배치 수집된 최신 이슈)
    raw_info = company_record.get("raw_info", {})
    ipo_terms = raw_info.get("ipo_terms", {})
    biz = raw_info.get("business_analysis", {})
    financials = raw_info.get("financial_history", {})
    sector = company_record.get("sector") or raw_info.get("sector", "미분류")

    # 포트폴리오 섹터 중복 검증
    same_sector_stocks = [
        h.get("stbd_name") for h in user_holdings 
        if sector != "미분류" and sector in h.get("stbd_sector", "")
    ]
    has_same_sector = len(same_sector_stocks) > 0

    # 3. 프롬프트 생성 (외부 검색 없이 DB 팩트만 제공)
    prompt = f"""
당신은 주식 초보자에게 1:1 자산관리를 돕는 증권사 AI 전담 PB입니다.
아래 **[DB에 보관된 고객 실제 계좌 정보]**와 **[DB에 등록된 공모주 팩트 지표 및 배치 수집 최신 이슈]**만을 엄격히 대조하여 알기 쉽게 진단해 주세요. 없는 수치를 꾸며내지 마세요.

[1. 고객 계좌 데이터 (USER_TRADE_INFO)]
- 고객명: {user_name} (투자성향: {risk_profile}, 청약 가용현금: {total_cash:,.0f}원)
- 실제 보유 주식: {user_holdings if user_holdings else '보유 종목 없음'}
- 보유 중인 산업군: {user_sectors if user_sectors else '없음'}
- 대상 공모주({sector})와 동일 업종 보유 여부: {"⚠️ 이미 보유 중 -> " + str(same_sector_stocks) if has_same_sector else "✅ 미보유 (새로운 업종 분산 투자)"}

[2. 공모주 팩트 데이터 (IPO_INFO_MASTER)]
- 종목명: {company_record.get('company_name')}
- 업종: {sector}
- 확정 공모가: {f"{int(ipo_terms.get('offering_price', 0)):,}원" if ipo_terms.get('offering_price') else "미확정"}
- 기관 수요예측 경쟁률: {f"{ipo_terms.get('competition_rate')}:1" if ipo_terms.get('competition_rate') else "확인 전"}
- 기관 의무보유확약(락업): {f"{ipo_terms.get('lockup_rate')}%" if ipo_terms.get('lockup_rate') else "확인 전"}
- 최근 재무 실적: {financials}
- 이 회사의 핵심 강점: {biz.get('strengths', [])}
- 🌟 오늘 수집된 최신 시장 분위기: {biz.get('market_sentiment', '안정적인 참여 흐름')}
- 🌟 최근 언론/시장 주요 이슈: {biz.get('latest_news_issues', [])}

[비전문가 맞춤 작성 규칙]
1. 어려운 금융 전문 용어(PER, 락업, 오버행 등)는 일상어로 풀어쓰세요.
2. 고객의 가용현금({total_cash:,.0f}원)으로 무리하게 큰돈(비례)을 넣는 것이 나은지, 소액(균등)만 안전하게 챙기는 것이 나은지 확실히 짚어주세요.
3. 동일 업종 주식이 이미 있다면 계좌 쏠림 위험을 안내하세요.

반드시 아래 JSON 규격으로만 응답하세요:
{{
    "recommendation": "청약 적극 추천" | "신중 청약 (소액 균등)" | "청약 보류 (관망)",
    "strategy_type": "최소 증거금 균등 배정" | "가용자금 집중 비례 배정" | "청약 패스",
    "traffic_lights": {{
        "institution": "🟢 우수" | "🟡 보통" | "🔴 주의",
        "lockup": "🟢 우수" | "🟡 보통" | "🔴 주의",
        "financial": "🟢 건전" | "🟡 보통" | "🔴 주의",
        "issues": "🟢 긍정" | "🟡 중립" | "🔴 부정"
    }},
    "portfolio_match": "내 보유 주식들과 비교했을 때 분산 투자 관점에서 어떤지 2문장",
    "financial_status": "회사가 빚이 많지 않고 돈을 잘 버는지 초보자 눈높이 진단 2문장",
    "capital_action": "내 통장 잔고 기준 구체적 청약 자금 배분 팁 2문장",
    "morning_tip": "상장일 아침 초보자가 당황하지 않고 챙겨야 할 매도 타이밍 팁"
}}
"""
    try:
        res = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.1}
        )
        return json.loads(res.text.strip())
    except Exception as e:
        return {
            "recommendation": "신중 청약",
            "strategy_type": "최소 증거금 균등 배정",
            "traffic_lights": {"institution": "🟡", "lockup": "🟡", "financial": "🟡", "issues": "🟡"},
            "portfolio_match": "보유 포트폴리오와의 연계성을 점검 중입니다.",
            "financial_status": "재무제표 확인 후 투자를 결정하세요.",
            "capital_action": "가용 자금을 고려해 무리하지 않는 선에서 청약하세요.",
            "morning_tip": "상장일 아침 주관사 앱의 시초가 형성 상태를 확인하세요."
        }