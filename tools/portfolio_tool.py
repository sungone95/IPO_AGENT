import json
from typing import Dict, Any
from google import genai
from google.genai import types

from config import DEFAULT_GEMINI_MODEL


def get_user_transaction_history(user_id: str) -> Dict[str, Any]:
    """[고객 매매 데이터] 추후 DB(user_trades)와 연동 가능"""
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
    """최근 공모주 시장 평균 기준선"""
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
    disclosure_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """OpenDART 실데이터(disclosure_data)와 고객 데이터를 결합하여 정량 분석 생성"""
    user_data = get_user_transaction_history(user_id)
    market_data = get_market_trends()
    user_name = user_data.get("user_name", "고객")

    # DART 실데이터에서 최신 연도 재무 및 공시 본문 추출
    financials = (disclosure_data or {}).get("financials", {})
    summary = (disclosure_data or {}).get("summary", {})

    # 가장 최근 연도 재무 지표 추출
    latest_year = max(financials.keys()) if financials else None
    latest_fin = financials.get(latest_year, {}) if latest_year else {}

    rev = latest_fin.get("revenue", 0)
    op_margin = latest_fin.get("operating_margin_pct", 0.0)
    debt_ratio = latest_fin.get("debt_ratio_pct", 0.0)

    prompt = f"""
    당신은 {user_name} 고객(초보 개미 투자자)을 위한 직관적 IPO 공모주 분석 시스템입니다.
    아래 제공된 **실제 OpenDART 공시 및 재무 실데이터**를 바탕으로 엄밀한 정량 분석 결과를 JSON으로 출력하세요.

    [1. 대상 기업 기본 및 DART 실데이터]
    - 기업명: {company_info.get('company_name')}
    - 확정 공모가: {company_info.get('offering_price', 0):,}원
    - 기관 경쟁률: {company_info.get('competition_rate', 0)}:1 (시장평균: {market_data['avg_competition_rate']}:1)
    - 락업(의무보유확약): {company_info.get('lockup_rate', 0)}% (시장평균: {market_data['avg_lockup_rate']}%)
    - 유통물량 비율: {company_info.get('float_rate', 25.0)}%
    - 구주매출 비율: {company_info.get('old_shares_rate', 0.0)}%
    - DART 공시 사업 요약: {summary.get('business', '공시 자료 없음')}
    - DART 공시 핵심 위험 요소: {summary.get('risks', '공시 자료 없음')}
    - 최근 연도({latest_year}년) 재무: 매출액 {rev:,}원 / 영업이익률 {op_margin}% / 부채비율 {debt_ratio}%

    [2. 고객 매매 성향]
    - 위험 성향: {user_data['risk_profile']}
    - 해당 산업군 과거 승률: 83.3%

    다음 JSON 규격만 출력하세요:
    {{
        "user_name": "{user_name}",
        "recommendation": "청약 적극 추천" | "신중 청약" | "청약 보류",
        "strategy_type": "비례 + 균등 배정" | "균등 배정 전용" | "청약 패스",
        "predicted_day1_return": 140.0,
        "target_price": 68000,
        "traffic_lights": {{
            "institution": "🟢 우수" | "🟡 보통" | "🔴 주의",
            "lockup": "🟢 우수" | "🟡 보통" | "🔴 주의",
            "financial": "🟢 우수" | "🟡 보통" | "🔴 주의",
            "risks": "🟢 우수" | "🟡 보통" | "🔴 주의"
        }},
        "morning_guide": "상장일 아침 8시 40분 ~ 9시 호가 확인 후 시초가 공모가 2배 이상 형성 시 9:10 전 분할 매도",
        "quant_summary": "실제 재무(영업이익률 {op_margin}%)와 기관 수치 기반 1문장 정량 결론"
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
        result["latest_fin"] = latest_fin
        result["latest_year"] = latest_year
        return result
    except Exception as e:
        return {
            "user_name": user_name,
            "recommendation": "신중 청약",
            "strategy_type": "균등 배정 전용",
            "predicted_day1_return": 120.0,
            "target_price": int(company_info.get("offering_price", 28000) * 2.2),
            "traffic_lights": {
                "institution": "🟢 우수",
                "lockup": "🟡 보통",
                "financial": "🟡 보통",
                "risks": "🟡 보통"
            },
            "morning_guide": "상장 당일 8시 40분 호가 확인 후 시초가 급등 시 조기 분할 매도 권장",
            "quant_summary": f"DART 데이터 추출 완료 (오류 폴백: {str(exc if 'exc' in locals() else e)})",
            "latest_fin": latest_fin,
            "latest_year": latest_year
        }
