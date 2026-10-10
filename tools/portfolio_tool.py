import json
from typing import Dict, Any, Optional
from google import genai
from google.genai import types

from config import DEFAULT_GEMINI_MODEL


# tools/portfolio_tool.py 상단 수정
from tools.user_db import get_user_profile_from_db

def get_user_transaction_history(user_id: str = "김성원") -> Dict[str, Any]:
    # Supabase USER_TRADE_INFO 테이블에서 실시간 조회
    return get_user_profile_from_db(user_name=user_id)


def get_market_trends() -> Dict[str, Any]:
    """공모주 시장 평균 기준선"""
    return {
        "avg_competition_rate": 950,
        "avg_lockup_rate": 35.0,
        "avg_day1_return": 140.0,
        "avg_operating_margin": 12.0,   # 업계 평균 영업이익률 기준선
        "avg_debt_ratio": 110.0,        # 업계 평균 부채비율 기준선
        "recent_ipo_performances": [
            {"name": "A바이오", "return_rate": 180},
            {"name": "B테크", "return_rate": 95},
            {"name": "C에너지", "return_rate": 140},
            {"name": "D소프트", "return_rate": 60},
            {"name": "E제약", "return_rate": 210}
        ]
    }


def analyze_user_portfolio_strategy_with_ai(
    client: genai.Client,
    user_id: str,
    company_info: Dict[str, Any],
    disclosure_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """실제 OpenDART 공시 데이터 또는 기본 메타데이터를 기반으로 실전형 추천 생성"""
    user_data = get_user_transaction_history(user_id)
    market_data = get_market_trends()
    user_name = user_data.get("user_name", "고객")

    # DART 실데이터 추출 (있는 경우)
    financials = (disclosure_data or {}).get("financials", {})
    summary = (disclosure_data or {}).get("summary", {})

    latest_year = max(financials.keys()) if financials else None
    latest_fin = financials.get(latest_year, {}) if latest_year else {}

    op_margin = latest_fin.get("operating_margin_pct", company_info.get("operating_margin", 15.0))
    debt_ratio = latest_fin.get("debt_ratio_pct", company_info.get("debt_ratio", 85.0))
    dart_biz = summary.get("business", company_info.get("business_summary", "공시 자료 없음"))
    dart_risks = summary.get("risks", "공시상 특별한 투자위험요소 기재 없음")

    offering_price = company_info.get("offering_price", 25000)
    comp_rate = company_info.get("competition_rate", 900)
    lockup_rate = company_info.get("lockup_rate", 30.0)

    prompt = f"""
    당신은 {user_name} 고객(초보 개미 투자자)을 위한 직관적 공모주 투자 가이드 시스템입니다.
    아래 제공된 **실제 기업 데이터 및 공시 정보**를 기반으로 수치 중심의 명확한 분석 결과를 JSON으로 출력하세요.

    [1. 대상 기업 정보]
    - 종목명: {company_info.get('company_name')}
    - 공모가: {offering_price:,}원
    - 기관 경쟁률: {comp_rate}:1 (시장평균: {market_data['avg_competition_rate']}:1)
    - 락업(의무보유확약): {lockup_rate}% (시장평균: {market_data['avg_lockup_rate']}%)
    - DART 공시 사업요약: {dart_biz}
    - DART 공시 위험요소: {dart_risks}
    - 결산 재무 지표: 영업이익률 {op_margin}%, 부채비율 {debt_ratio}%

    [2. 고객 성향]
    - 위험 성향: {user_data['risk_profile']}
    - 동일 산업군 과거 승률: 83.3%

    다음 JSON 규격만 출력하세요:
    {{
        "user_name": "{user_name}",
        "recommendation": "청약 적극 추천" | "신중 청약" | "청약 보류",
        "strategy_type": "비례 + 균등 배정" | "균등 배정 전용" | "청약 패스",
        "predicted_day1_return": 145.0,
        "target_price": {int(offering_price * 2.4)},
        "traffic_lights": {{
            "institution": "🟢 우수" | "🟡 보통" | "🔴 주의",
            "lockup": "🟢 우수" | "🟡 보통" | "🔴 주의",
            "financial": "🟢 우수" | "🟡 보통" | "🔴 주의",
            "risks": "🟢 우수" | "🟡 보통" | "🔴 주의"
        }},
        "morning_guide": "상장일 아침 8시 40분 ~ 9시 호가 확인 후 시초가 공모가 2배 이상 형성 시 9:10 전 분할 매도"
    }}
    """

    try:
        if client is None:
            raise ValueError("Gemini Client가 초기화되지 않았습니다.")

        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        result = json.loads(response.text)
        result["user_name"] = user_name
        result["latest_fin"] = latest_fin
        result["latest_year"] = latest_year
        return result
    except Exception:
        # 안전한 폴백(Fallback) 기본값
        return {
            "user_name": user_name,
            "recommendation": "청약 추천" if comp_rate > 800 else "신중 청약",
            "strategy_type": "균등 배정 전용",
            "predicted_day1_return": 130.0,
            "target_price": int(offering_price * 2.3),
            "traffic_lights": {
                "institution": "🟢 우수" if comp_rate > 900 else "🟡 보통",
                "lockup": "🟢 우수" if lockup_rate > 35 else "🟡 보통",
                "financial": "🟢 우수" if op_margin > 10 else "🟡 보통",
                "risks": "🟡 보통"
            },
            "morning_guide": "상장일 아침 8시 40분 호가 확인 후 시초가가 높게 형성되면 9시 장 개장 직후 분할 매도하세요.",
            "latest_fin": latest_fin,
            "latest_year": latest_year
        }
