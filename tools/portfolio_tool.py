import json
from typing import Dict, Any
from google import genai
from google.genai import types

from config import DEFAULT_GEMINI_MODEL


def get_user_transaction_history(user_id: str) -> Dict[str, Any]:
    """[Mock] 고객 매매 기록 및 성향 수치 데이터"""
    return {
        "user_id": user_id,
        "user_name": "김투린",
        "risk_profile": "공격투자형",
        "total_capital": 50000000,
        "sector_holding_stats": [
            {"sector": "바이오/제약", "trade_count": 12, "avg_holding_days": 1.5, "win_rate": 83.3, "avg_return_rate": 24.5},
            {"sector": "2차전지/소재", "trade_count": 5, "avg_holding_days": 14.0, "win_rate": 40.0, "avg_return_rate": -5.2},
            {"sector": "IT/SaaS", "trade_count": 8, "avg_holding_days": 3.0, "win_rate": 62.5, "avg_return_rate": 11.8}
        ]
    }


def get_market_trends() -> Dict[str, Any]:
    """[Mock] 최근 시장 평균 수치 및 산업 동향"""
    return {
        "avg_competition_rate": 950,
        "avg_lockup_rate": 35.0,
        "avg_day1_return": 140.0,
        "recent_ipo_performances": [
            {"name": "A바이오", "return_rate": 180},
            {"name": "B테크", "return_rate": 95},
            {"name": "C에너지", "return_rate": 140},
            {"name": "D소프트", "return_rate": 60},
            {"name": "E제약", "return_rate": 210}
        ]
    }


def analyze_user_portfolio_strategy_with_ai(client: genai.Client, user_id: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
    """Gemini AI가 일반 초보 개미 투자자 눈높이의 정량 수치 및 3초 행동 전략을 반환"""
    user_data = get_user_transaction_history(user_id)
    market_data = get_market_trends()
    user_name = user_data.get("user_name", "고객")
    
    prompt = f"""
    당신은 {user_name} 고객(초보 개미 투자자)을 위한 3초 직관 IPO 투자 안내 시스템입니다.
    전문 용어나 모호한 수식어는 배제하고, 오직 직관적인 수치와 행동 지침만 산출하세요.

    [대상 공모주 정보]
    - 종목명: {company_info.get('company_name')}
    - 확정 공모가: {company_info.get('offering_price', 0):,}원
    - 기관 경쟁률: {company_info.get('competition_rate', 0)}:1 (시장평균: {market_data['avg_competition_rate']}:1)
    - 락업(의무보유확약): {company_info.get('lockup_rate', 0)}% (시장평균: {market_data['avg_lockup_rate']}%)
    - 유통가능물량 비율: {company_info.get('float_rate', 25.0)}%
    - 구주매출 비율: {company_info.get('old_shares_rate', 0.0)}%

    다음 JSON 규격만 출력하세요:
    {{
        "user_name": "{user_name}",
        "recommendation": "청약 적극 추천" | "신중 청약" | "청약 보류",
        "strategy_type": "비례 + 균등 배정" | "균등 배정 전용" | "청약 패스",
        "predicted_day1_return": 160.0,
        "target_price": 72800,
        "traffic_lights": {{
            "institution": "🟢 우수" | "🟡 보통" | "🔴 주의",
            "lockup": "🟢 우수" | "🟡 보통" | "🔴 주의",
            "float_shares": "🟢 우수" | "🟡 보통" | "🔴 주의",
            "old_shares": "🟢 우수" | "🟡 보통" | "🔴 주의"
        }},
        "morning_guide": "상장일 아침 8시 40분 ~ 9시 호가 확인 후 시초가 공모가 2배 이상 형성 시 9:10 전 분할 매도"
    }}
    """

    try:
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
        return result
    except Exception as e:
        return {
            "user_name": user_name,
            "recommendation": "청약 적극 추천",
            "strategy_type": "비례 + 균등",
            "predicted_day1_return": 150.0,
            "target_price": company_info.get('offering_price', 28000) * 2.5,
            "traffic_lights": {
                "institution": "🟢 우수",
                "lockup": "🟢 우수",
                "float_shares": "🟡 보통",
                "old_shares": "🟢 우수"
            },
            "morning_guide": "상장일 아침 8시 40분 호가 확인 후 9시 장 개장 직후 분할 매도하여 이익을 확정하세요."
        }
