import json
from typing import Dict, Any
from google import genai
from google.genai import types

from config import DEFAULT_GEMINI_MODEL


def get_user_transaction_history(user_id: str) -> Dict[str, Any]:
    """[Mock] 고객 매매 기록 및 성향 자동 추출"""
    return {
        "user_id": user_id,
        "user_name": "김투린",
        "risk_profile": "공격투자형",
        "total_capital": 50000000,
        "sector_holding_stats": [
            {"sector": "바이오/제약", "trade_count": 12, "avg_holding_days": 1.5, "win_rate": 83.3},
            {"sector": "2차전지/소재", "trade_count": 5, "avg_holding_days": 14.0, "win_rate": 40.0},
            {"sector": "IT/SaaS", "trade_count": 8, "avg_holding_days": 3.0, "win_rate": 62.5}
        ]
    }


def get_market_trends() -> Dict[str, Any]:
    """[Mock] 최근 시장 분위기 및 산업 동향 추출"""
    return {
        "ipo_market_sentiment": "매우 과열 (최근 상장주 당일 평균 수익률 +140%)",
        "recent_ipo_performances": [
            {"name": "A바이오", "return_rate": 180},
            {"name": "B테크", "return_rate": 95},
            {"name": "C에너지", "return_rate": 140},
            {"name": "D소프트", "return_rate": 60},
            {"name": "E제약", "return_rate": 210}
        ],
        "sector_trends": {
            "바이오/제약": "최근 FDA 승인 이슈로 테마 강세, 상장 당일 수급 집중 현상",
            "IT/SaaS": "단기 실적 유무에 따라 상장일 변동성이 커지는 흐름",
            "2차전지/소재": "글로벌 수요 감소 여파로 조정 국면"
        }
    }


def analyze_user_portfolio_strategy_with_ai(client: genai.Client, user_id: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
    """Gemini AI가 고객 맞춤형 리포트를 작성"""
    user_data = get_user_transaction_history(user_id)
    market_data = get_market_trends()
    user_name = user_data.get("user_name", "고객")
    
    prompt = f"""
    당신은 {user_name} 고객만을 위한 맞춤형 공모주 투자 컨설턴트입니다.
    고객의 과거 매매 패턴, 최근 시장/산업 동향, 청약 종목 정보 및 기관 투자자 수치를 종합 분석하여 맞춤형 진단을 작성하세요.

    [1. 고객 정보]
    - 고객명: {user_name}
    - 위험 성향: {user_data['risk_profile']}
    - 청약 가용 자금: {user_data['total_capital']:,}원
    - 산업군별 과거 매매 성과: {json.dumps(user_data['sector_holding_stats'], ensure_ascii=False)}

    [2. 최근 시장 동향]
    - 관련 산업군 동향: {json.dumps(market_data['sector_trends'], ensure_ascii=False)}

    [3. 청약 대상 공모주 정보 및 수치 지표]
    - 기업명: {company_info.get('company_name')}
    - 속한 산업군: {company_info.get('sector', '일반')}
    - 주요 사업 요약: {company_info.get('business_summary', '정보 없음')}
    - 주요 객관적 수치 성과: {company_info.get('metrics_info', '정보 없음')}
    - 확정 공모가: {company_info.get('offering_price', 0):,}원
    - 기관 경쟁률: {company_info.get('competition_rate', 0)}:1
    - 기관 의무보유확약 비율: {company_info.get('lockup_rate', 0)}%

    다음 규격에 맞는 JSON 형식만 출력하세요:
    {{
        "user_name": "{user_name}",
        "recommendation": "청약 적극 추천" | "신중 청약" | "청약 보류",
        "company_simple_summary": "초등학생도 이해하기 쉬운 2줄 이내 요약. 반드시 객관적 수치 지표(점유율 등)를 포함하세요.",
        "institutional_explanation": "기관 경쟁률({company_info.get('competition_rate')}:1)과 의무보유확약 비율({company_info.get('lockup_rate')}%)이 의미하는 바를 초등학생도 알기 쉽게 설명하세요. (예: 전문가 몇 명이 줄을 섰고, 이 주식을 바로 안 팔고 얼마나 오래 갖고 있겠다고 약속했는지 비유하여 2~3문장 작성)",
        "personal_reason": "{user_name} 고객님의 과거 {company_info.get('sector')} 산업 매매 성공률(win_rate), 보유기간, 위험성향 데이터를 근거로 왜 추천/비추천하는지 2~3문장으로 명확히 설명",
        "strategy_type": "비례 + 균등 배정" | "균등 배정 전용" | "청약 패스",
        "sell_guide": "{user_name} 고객의 해당 산업군 평균 보유일수와 시장 수급을 반영한 매도 전략 1~2문장"
    }}
    """

    try:
        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        result = json.loads(response.text)
        result["user_name"] = user_name
        return result
    except Exception as e:
        return {
            "user_name": user_name,
            "recommendation": "분석 오류",
            "company_simple_summary": "기업 정보를 불러오는 중 오류가 발생했습니다.",
            "institutional_explanation": "기관 투자자 수치를 분석 중 오류가 발생했습니다.",
            "personal_reason": f"오류 원인: {str(e)}",
            "strategy_type": "보류",
            "sell_guide": "기본 가이드를 참고하세요."
        }
