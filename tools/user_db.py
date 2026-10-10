"""Supabase USER_TRADE_INFO 테이블 기반 고객 보유 포트폴리오 연동 모듈."""
import streamlit as st
from supabase import create_client, Client
from typing import Dict, Any, List
from collections import defaultdict


@st.cache_resource
def get_supabase_client() -> Client:
    """Streamlit Secrets에서 Supabase 연결 클라이언트 생성"""
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    return create_client(url, key)


def get_all_users() -> List[str]:
    """DB에 등록된 모든 고객명 고유 목록 조회"""
    try:
        supabase = get_supabase_client()
        response = supabase.table("USER_TRADE_INFO").select("user_name").execute()
        users = sorted(list({row["user_name"] for row in (response.data or []) if row.get("user_name")}))
        return users or ["김성원"]
    except Exception as e:
        st.warning(f"고객 목록 조회 실패: {e}")
        return ["김성원"]


def get_user_holdings(user_name: str) -> List[Dict[str, Any]]:
    """DB에서 특정 고객의 개별 보유 주식 목록 조회"""
    try:
        supabase = get_supabase_client()
        response = supabase.table("USER_TRADE_INFO").select("*").eq("user_name", user_name).execute()
        return response.data or []
    except Exception as e:
        st.warning(f"고객 보유 주식 DB 조회 실패: {e}")
        return []


def get_user_profile_from_db(user_name: str) -> Dict[str, Any]:
    """
    USER_TRADE_INFO 테이블의 보유 내역을 조회하여 
    portfolio_tool 및 Gemini가 분석에 사용하는 포맷으로 가공
    """
    holdings = get_user_holdings(user_name)

    if holdings:
        sector_agg = defaultdict(lambda: {"count": 0, "total_qty": 0})
        for item in holdings:
            sector = item.get("stbd_sector", "기타")
            qty = float(item.get("hold_qty") or 0)
            sector_agg[sector]["count"] += 1
            sector_agg[sector]["total_qty"] += qty

        sector_holding_stats = [
            {
                "sector": sector,
                "trade_count": data["count"],
                "total_hold_qty": data["total_qty"],
                "avg_holding_days": 2.0,
                "win_rate": 80.0,
                "avg_return_rate": 18.5
            }
            for sector, data in sector_agg.items()
        ]

        return {
            "user_name": user_name,
            "risk_profile": "성장추구형",
            "holdings": holdings,
            "sector_holding_stats": sector_holding_stats
        }

    # 해당 고객의 보유 종목이 아직 없을 때
    return {
        "user_name": user_name,
        "risk_profile": "성장추구형",
        "holdings": [],
        "sector_holding_stats": []
    }


def insert_user_holding(
    user_name: str,
    stbd_code: str,
    stbd_name: str,
    hold_qty: float,
    stbd_sector: str
) -> bool:
    """USER_TRADE_INFO 테이블에 보유 주식 등록/수정"""
    try:
        supabase = get_supabase_client()
        payload = {
            "user_name": user_name.strip(),
            "stbd_code": stbd_code.strip(),
            "stbd_name": stbd_name.strip(),
            "hold_qty": float(hold_qty),
            "stbd_sector": stbd_sector.strip()
        }
        supabase.table("USER_TRADE_INFO").upsert(payload).execute()
        return True
    except Exception as e:
        st.error(f"주식 등록 실패: {e}")
        return False