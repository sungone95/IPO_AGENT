import json
from typing import Dict, Any
from google import genai
from google.genai import types

def get_user_transaction_history(user_id: str) -> Dict[str, Any]:
    """[Mock] 고객 매매 기록 및 성향 자동 추출 (추후 DB 쿼리로 교체)"""
    return {
        "user_id": user_id,
        "risk_profile": "공격투자형",
        "total_capital": 50000000,
        "sector_holding_stats": [
            {"sector": "바이오/제약", "trade_count": 12, "avg_holding_days": 1.5, "win_rate": 83.3},
            {"sector": "2차전지/소재", "trade_count": 5, "avg_holding_days": 14.0, "win_rate": 40.0},
            {"sector": "IT/SaaS", "trade_count": 8, "avg_holding_days": 3.0, "win_rate": 62.5}
        ]
    }

def get_market_trends() -> Dict[str, Any]:
    """[Mock] 최근 시장 분위기 및 산업 동향 추출 (추후 Crawling/DB 연동)"""
    return {
        "ipo_market_sentiment": "매우 과열 (최근 5개 공모주 평균 상장일 수익률 +140%)",
        "sector_trends": {
            "바이오/제약": "최근 FDA 승인 이슈로 테마 강세, 상장 당일 수급 집중 현상",
            "IT/SaaS": "단기 실적 유무에 따라 상장일 변동성이 커지는 흐름"
        }
    }

def analyze_user_portfolio_strategy_with_ai(client: genai.Client, user_id: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
    """Gemini AI가 유저 매매내역 + 시장동향 + 종목정보를 종합 추론하여 JSON 생성"""
    user_data = get_user_transaction_history(user_id)
    market_data = get_market_trends()
    
    prompt = f"""
    당신은 데이터 기반 공모주 투자 컨설턴트입니다.
    고객의 과거 매매 내역, 최근 시장/산업 동향, 청약 종목 정보를 종합 분석하여 맞춤형 진단을 작성하세요.

    [1. 고객 매매 패턴 데이터]
    - 위험 성향: {user_data['risk_profile']}
    - 청약 가용 자금: {user_data['total_capital']:,}원
    - 산업군별 거래 통계: {json.dumps(user_data['sector_holding_stats'], ensure_ascii=False)}

    [2. 최근 시장 및 산업 동향]
    - 공모주 시장 분위기: {market_data['ipo_market_sentiment']}
    - 관련 산업군 동향: {json.dumps(market_data['sector_trends'], ensure_ascii=False)}

    [3. 청약 대상 공모주 정보]
    - 기업명: {company_info.get('company_name')}
    - 속한 산업군: {company_info.get('sector', '일반')}
    - 확정 공모가: {company_info.get('offering_price', 0):,}원
    - 기관 수요예측 경쟁률: {company_info.get('competition_rate', 0)}:1
    - 주관사: {company_info.get('underwriter')}

    다음 규격에 맞는 JSON 형식만 출력하세요:
    {{
        "recommendation": "청약 적극 추천" | "신중 청약" | "청약 보류",
        "score": 85,
        "strategy_type": "비례 + 균등 배정" | "균등 배정 전용" | "청약 패스",
        "strategy_desc": "가용자금 및 배정 전략 관련 1~2문장",
        "sell_guide": "산업군 평균 보유일수와 시장 수급을 고려한 매도 가이드 1~2문장",
        "reasons": [
            "산업군 매매 패턴 연관 분석 근거",
            "시장/산업 동향 연관 분석 근거",
            "수요예측/자금 규모 연관 분석 근거"
        ]
    }}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {
            "recommendation": "분석 오류",
            "score": 0,
            "strategy_type": "보류",
            "strategy_desc": "AI 분석 중 오류가 발생했습니다.",
            "sell_guide": "기본 가이드를 참고하세요.",
            "reasons": [f"오류 상세: {str(e)}"]
        }
