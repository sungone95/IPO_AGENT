"""Supabase 실데이터 기반 고객 프로필 및 보유 자산 연동 모듈."""
import streamlit as st
from supabase import create_client, Client
from typing import Dict, Any, List


@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    return create_client(url, key)


def get_all_users() -> List[str]:
    """DB에 등록된 모든 고객명 고유 목록 조회"""
    try:
        supabase = get_supabase_client()
        res = supabase.table("USER_TRADE_INFO").select("user_name").execute()
        users = sorted(list({row["user_name"] for row in (res.data or []) if row.get("user_name")}))
        return users or ["김성원"]
    except Exception as e:
        st.warning(f"고객 목록 조회 실패: {e}")
        return ["김성원"]


def get_user_holdings(user_name: str) -> List[Dict[str, Any]]:
    """DB에서 특정 고객의 실제 보유 종목 목록 조회"""
    try:
        supabase = get_supabase_client()
        res = supabase.table("USER_TRADE_INFO").select("*").eq("user_name", user_name.strip()).execute()
        return res.data or []
    except Exception as e:
        st.warning(f"보유 주식 조회 실패: {e}")
        return []


def get_user_profile_from_db(user_name: str) -> Dict[str, Any]:
    """고객의 투자성향과 실제 보유 종목 데이터를 결합하여 반환"""
    supabase = get_supabase_client()
    clean_name = user_name.strip()
    
    # 1. 고객 투자성향 조회 (없으면 기본값 세팅)
    risk_profile = "성장추구형"
    total_cash = 30000000
    try:
        prof_res = supabase.table("USER_PROFILE").select("*").eq("user_name", clean_name).execute()
        if prof_res.data:
            risk_profile = prof_res.data[0].get("risk_profile", "성장추구형")
            total_cash = float(prof_res.data[0].get("total_cash", 30000000))
    except Exception:
        pass  # USER_PROFILE 테이블이 아직 없을 경우 대비 안전 fallback

    # 2. 실제 보유 주식 조회
    holdings = get_user_holdings(clean_name)
    holding_sectors = list({h.get("stbd_sector") for h in holdings if h.get("stbd_sector")})

    return {
        "user_name": clean_name,
        "risk_profile": risk_profile,
        "total_cash": total_cash,
        "holdings": holdings,
        "holding_sectors": holding_sectors,
        "total_holdings_count": len(holdings)
    }


def insert_user_holding(user_name: str, stbd_code: str, stbd_name: str, hold_qty: float, stbd_sector: str) -> bool:
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