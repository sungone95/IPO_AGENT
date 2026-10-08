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
        "avg_competition_rate": 950,   # 최근 1달 공모주 평균 기관경쟁률
        "avg_lockup_rate": 35.0,        # 최근 1달 공모주 평균 의무보유확약(%)
        "avg_day1_return": 140.0,       # 최근 1달 상장 당일 평균 수익률(%)
        "recent_ipo_performances": [
            {"name": "A바이오", "return_rate": 180},
            {"name": "B테크", "return_rate": 95},
            {"name": "C에너지", "return_rate": 140},
            {"name": "D소프트", "return_rate": 60},
            {"name": "E제약", "return_rate": 210}
        ]
    }


def analyze_user_portfolio_strategy_with_ai(client: genai.Client, user_id: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
    """Gemini AI가 정량 수치 기반 리포트 반환"""
    user_data = get_user_transaction_history(user_id)
    market_data = get_market_trends()
    user_name = user_data.get("user_name", "고객")
    
    prompt = f"""
    당신은 {user_name} 고객만을 위한 정량 수치 중심 공모주 분석 시스템입니다.
    주관적이거나 감정적인 표현(예: '높은 기술력을 바탕으로 성장 중', '전망이 밝음')을 절대 사용하지 말고,
    오직 정량적 숫자와 데이터 지표만 추출/예측하세요.

    [1. 대상 공모주 데이터]
    - 기업명: {company_info.get('company_name')}
    - 확정 공모가: {company_info.get('offering_price', 0)}원
    - 기관 경쟁률: {company_info.get('competition_rate', 0)}:1
    - 의무보유확약: {company_info.get('lockup_rate', 0)}%
    - 최근 시장 평균 기관경쟁률: {market_data['avg_competition_rate']}:1
    - 최근 시장 평균 락업: {market_data['avg_lockup_rate']}%

    [2. 고객 매매 패턴 수치]
    - 해당 산업군 과거 승률: 83.3%
    - 과거 평균 보유일수: 1.5일

    다음 JSON 규격만 출력하세요 (주관적 문장 제외, 오직 수치 및 수치 기반 정량 요약만):
    {{
        "user_name": "{user_name}",
        "recommendation": "청약 적극 추천" | "신중 청약" | "청약 보류",
        "strategy_type": "비례 + 균등 배정" | "균등 배정 전용" | "청약 패스",
        "predicted_day1_return": 165.0,  // 상장 당일 예상 수익률 (%) 숫자만
        "target_price": 74200,            // 목표 주가 (원) 숫자만
        "stop_loss_price": 30800,         // 손절가 (원) 숫자만
        "quant_summary": "과거 해당 산업 승률 83.3% / 평균 보유일수 1.5일 / 기관 경쟁률 시장 평균 대비 +470:1 우수"
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
            "recommendation": "분석 완료",
            "strategy_type": "비례 + 균등",
            "predicted_day1_return": 150.0,
            "target_price": 70000,
            "stop_loss_price": 30000,
            "quant_summary": f"수치 산출 오류: {str(e)}"
        }
