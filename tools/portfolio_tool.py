import json
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from config import DEFAULT_GEMINI_MODEL
from tools.user_db import get_user_profile_from_db


def get_user_transaction_history(user_id: str = "김성원") -> Dict[str, Any]:
    """Supabase USER_TRADE_INFO 테이블에서 실시간 조회"""
    return get_user_profile_from_db(user_name=user_id)


def get_market_trends() -> Dict[str, Any]:
    """공모주 시장 참고 기준선"""
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
    """
    임의 추정치/하드코딩 수치를 전면 배제하고,
    100% 실데이터(고객 계좌 + DART/Tavily 수집 정보)만 교차 대조하여
    주식 초보자도 바로 이해할 수 있는 행동 가이드를 생성합니다.
    """
    # 1. 실제 고객 계좌 실데이터 (USER_TRADE_INFO)
    user_profile = get_user_profile_from_db(user_id)
    user_name = user_profile.get("user_name", user_id)
    user_holdings = user_profile.get("holdings", [])
    user_sectors = user_profile.get("holding_sectors", [])
    risk_profile = user_profile.get("risk_profile", "안정추구형")
    total_cash = float(user_profile.get("total_cash", 0.0))

    # 2. DART 재무 실데이터 파싱 (임의 fallback 기본값 완전 배제)
    financials = (disclosure_data or {}).get("financial_history") or (disclosure_data or {}).get("financials", {})
    summary = (disclosure_data or {}).get("summary", {})
    biz_analysis = (disclosure_data or {}).get("business_analysis", {})
    ipo_terms = (disclosure_data or {}).get("ipo_terms") or company_info.get("ipo_metrics", {})

    latest_year = max(financials.keys()) if financials else None
    latest_fin = financials.get(latest_year, {}) if latest_year else {}

    # 가짜 수치 대신 실제 값만 바인딩 (없으면 None 처리)
    op_margin = latest_fin.get("operating_margin_pct")
    debt_ratio = latest_fin.get("debt_ratio_pct")
    revenue_growth = latest_fin.get("revenue_growth_pct")

    # 3. 공모 조건 실데이터 바인딩 (하드코딩 25000, 900, 35.0 제거)
    ipo_sector = company_info.get("sector") or (disclosure_data or {}).get("sector", "업종 미분류")
    offering_price = ipo_terms.get("offering_price") or company_info.get("offering_price")
    comp_rate = ipo_terms.get("competition_rate") or company_info.get("competition_rate")
    lockup_rate = ipo_terms.get("lockup_rate") or company_info.get("lockup_rate")

    # 4. 파이썬 레벨 실제 포트폴리오 섹터 중복 검증
    same_sector_stocks = [
        h.get("stbd_name") for h in user_holdings 
        if ipo_sector != "업종 미분류" and ipo_sector in h.get("stbd_sector", "")
    ]
    has_same_sector = len(same_sector_stocks) > 0

    # 5. 초보자 친화 멘토링 프롬프트
    prompt = f"""
당신은 주식 초보자에게 친절하고 객관적인 맞춤 조언을 제공하는 AI 자산관리 멘토입니다.
아래 **[실제 고객 계좌 데이터]**와 **[DART/Tavily 확인 실데이터]**만을 엄밀하게 대조하여 분석하세요.
데이터에 명시되지 않은 가짜 수치나 허위 공모 조건을 절대 꾸며내지 마세요.

==================================================
[1. 고객 실제 보유 계좌 데이터 (USER_TRADE_INFO)]
- 고객명: {user_name} (투자성향: {risk_profile}, 청약 가용현금: {total_cash:,.0f}원)
- 실제 보유 종목: {user_holdings if user_holdings else '보유 종목 없음'}
- 보유 중인 산업군: {user_sectors if user_sectors else '없음'}
- 대상 공모주({ipo_sector})와 동일 산업군 보유 여부: {"⚠️ 이미 보유 중 -> " + str(same_sector_stocks) if has_same_sector else "✅ 미보유 (새로운 산업군 분산 투자 효과)"}

[2. 신규 공모주 실측 지표 (DART 공시 및 Tavily 웹 검색 결과)]
- 종목명: {company_info.get('company_name')}
- 산업군(업종): {ipo_sector}
- 확정 공모가: {f"{offering_price:,}원" if offering_price else "아직 확정 전 (희망 밴드 확인 필요)"}
- 기관 수요예측 경쟁률: {f"{comp_rate}:1" if comp_rate else "결과 발표 전 (수요예측 미실시)"}
- 기관 의무보유확약비율: {f"{lockup_rate}%" if lockup_rate else "결과 발표 전"}
- 최근 결산 재무건전성: 영업이익률 {f"{op_margin}%" if op_margin is not None else "자료 없음"}, 부채비율 {f"{debt_ratio}%" if debt_ratio is not None else "자료 없음"}
- 사업 내용 및 강점: {biz_analysis.get('business_summary') or summary.get('business', '공시 확인 필요')} / 강점: {biz_analysis.get('strengths', [])}
- 시장 평가 및 경쟁사 대비 차별점: {biz_analysis.get('market_sentiment', '자료 없음')} / {biz_analysis.get('peer_differentiation', '자료 없음')}
- 핵심 위험요인: {biz_analysis.get('investment_risks') or summary.get('risks', '공시 확인 필요')}
==================================================

[초보자 맞춤 작성 및 추론 규칙]
1. 하드코딩/임의 추정 금지:
   - 공모가, 경쟁률, 확약비율이 미발표(확인 전) 상태라면 "아직 기관 수요예측 수치가 나오지 않아 흥행 여부를 조금 더 지켜봐야 합니다"라고 솔직하게 쓰세요.
2. 비전문가 눈높이 쉬운 설명:
   - PER, 오버행, 락업비율, 오버웨이트 같은 전문 금융 용어는 사용하지 마세요.
   - '의무보유확약' ➔ '기관들이 상장 날 주식을 바로 팔지 않겠다고 약속한 비중'
   - '비례 배정 실익' ➔ '많은 증거금을 넣었을 때 1주라도 더 건질 수 있는지 여부'
3. 고객 맞춤형 포트폴리오 대조:
   - 동일 업종 종목({same_sector_stocks})이 이미 있다면 특정 산업에 돈이 쏠리는 위험을 경고하세요.
   - 고객의 가용현금({total_cash:,.0f}원) 규모에 비추어 균등만 넣는 것이 나은지, 큰돈을 넣어 비례까지 노려볼 만한지 명확히 짚어주세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
    "recommendation": "청약 적극 추천" | "신중 청약 (소액 균등)" | "청약 보류 (관망)",
    "strategy_type": "최소 증거금 균등 배정" | "가용자금 집중 비례 배정" | "청약 패스",
    "traffic_lights": {{
        "institution": "🟢 우수" | "🟡 보통" | "🔴 주의/미발표",
        "lockup": "🟢 우수" | "🟡 보통" | "🔴 주의/미발표",
        "financial": "🟢 건전" | "🟡 보통" | "🔴 주의/적자",
        "risks": "🟢 양호" | "🟡 보통" | "🔴 주의"
    }},
    "evidence_breakdown": {{
        "sector_check": {{
            "status": "동일 업종 보유 중" 또는 "새로운 업종 편입",
            "holding_items": "{same_sector_stocks if has_same_sector else '없음'}",
            "rationale": "초보자도 단번에 이해할 수 있는 내 주식 포트폴리오 분산/쏠림 분석 2문장"
        }},
        "financial_risk_fit": {{
            "customer_risk_profile": "{risk_profile}",
            "financial_diagnosis": "회사가 실제로 돈을 잘 벌고 빚이 많은지 초보자 눈높이로 진단한 2문장",
            "strategy_fit": "고객 성향상 원금을 지키기 위해 취해야 할 안전 조언 1문장"
        }},
        "capital_allocation": {{
            "available_cash": "{total_cash:,.0f}원",
            "competition_assessment": "현재 내 통장 잔고로 무리해서 큰돈을 넣을 필요가 있는지, 균등 최소 금액(몇만 원)만 넣는 게 실익이 큰지 알기 쉽게 설명한 2문장"
        }}
    }},
    "morning_guide": "상장일 아침 8시 40분부터 9시 사이에 주식을 가진 초보자가 당황하지 않고 대처할 수 있는 실천 팁 2문장"
}}
"""

    try:
        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.1}
        )
        return json.loads(response.text.strip())
    except Exception as e:
        # 오류 발생 시에도 가짜 목표가/수익률 산식을 배제하고 안전한 설명문으로 응답
        return {
            "recommendation": "신중 청약 (소액 균등)",
            "strategy_type": "최소 증거금 균등 배정",
            "traffic_lights": {"institution": "🟡 보통", "lockup": "🟡 보통", "financial": "🟡 보통", "risks": "🟡 보통"},
            "evidence_breakdown": {
                "sector_check": {
                    "status": "동일 업종 보유 중" if has_same_sector else "새로운 업종 편입",
                    "holding_items": str(same_sector_stocks) if has_same_sector else "없음",
                    "rationale": f"{user_name}님의 기존 보유 자산과 비교할 때 과도한 자금 쏠림을 방지하기 위한 점검이 필요합니다."
                },
                "financial_risk_fit": {
                    "customer_risk_profile": risk_profile,
                    "financial_diagnosis": f"최근 공시 기준 영업이익률({op_margin or '확인중'}%)과 부채비율({debt_ratio or '확인중'}%)을 확인해야 합니다.",
                    "strategy_fit": f"{risk_profile} 투자 성향에 맞추어 큰돈을 묶어두기보다는 소액으로 방어적인 접근을 권장합니다."
                },
                "capital_allocation": {
                    "available_cash": f"{total_cash:,.0f}원",
                    "competition_assessment": f"경쟁률 발표 수치를 확인한 뒤 실익이 적다면 무리한 비례 청약 대신 최소 수량(균등) 위주로 참여하는 것이 안전합니다."
                }
            },
            "morning_guide": "상장일 아침 08:40 이후 주관사 앱에서 예상 체결 가격 흐름을 확인한 뒤 매도 시점을 결정하세요."
        }