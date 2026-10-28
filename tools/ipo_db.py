"""Supabase 기반 IPO 종목 공시/재무 데이터 영구 캐시 모듈."""
from typing import Dict, Any, Optional, List
from datetime import datetime
import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY") or st.secrets.get("SUPABASE_KEY", "")
    return create_client(url, key)


def get_cached_ipo_data(corp_name: str) -> Optional[Dict[str, Any]]:
    """Supabase IPO_INFO_MASTER에서 이미 수집된 종목 데이터 조회 (캐시 히트)"""
    try:
        supabase = get_supabase_client()
        clean_name = corp_name.strip()
        response = supabase.table("IPO_INFO_MASTER") \
            .select("*") \
            .eq("stbd_name", clean_name) \
            .limit(1) \
            .execute()

        if response.data:
            row = response.data[0]
            cached_payload = row.get("raw_info", {})
            cached_payload["corp_code"] = row.get("stbd_code")
            cached_payload["company_name"] = row.get("stbd_name")
            cached_payload["sector"] = row.get("stbd_sector")
            cached_payload["sector_code"] = row.get("sector_code")
            cached_payload["_from_cache"] = True
            return cached_payload
    except Exception as e:
        st.warning(f"DB 캐시 조회 중 오류: {e}")

    return None


def save_ipo_data_to_cache(
    corp_code: str,
    corp_name: str,
    ipo_sector: str,
    raw_payload: Dict[str, Any],
    sector_code: str = "SEC_MEDIA"
) -> bool:
    """정제된 공모/재무/시장 실데이터를 DB에 영구 보존"""
    try:
        supabase = get_supabase_client()
        record = {
            "stbd_code": corp_code.strip() if corp_code else "",
            "stbd_name": corp_name.strip(),
            "stbd_sector": ipo_sector.strip() if ipo_sector else "기타",
            "sector_code": sector_code,
            "raw_info": raw_payload,
            "update_time": datetime.now().astimezone().isoformat()
        }
        supabase.table("IPO_INFO_MASTER").upsert(record, on_conflict="stbd_name").execute()
        return True
    except Exception as e:
        st.error(f"종목 데이터 DB 저장 실패: {e}")
        return False


def get_active_ipo_master_list() -> List[Dict[str, Any]]:
    """
    증권사 내부 DB(IPO_INFO_MASTER)에서 활성 공모주 목록을 실시간 조회.
    sector_code 필드를 포함하여 반환합니다.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("IPO_INFO_MASTER") \
            .select("stbd_name, stbd_code, stbd_sector, sector_code, update_time, raw_info") \
            .order("update_time", desc=True) \
            .execute()

        items = []
        for row in (response.data or []):
            name = row.get("stbd_name")
            if not name:
                continue

            raw_info = row.get("raw_info") or {}
            ipo_terms = raw_info.get("ipo_terms") or raw_info.get("ipo_metrics") or {}

            items.append({
                "company_name": name,
                "sector": row.get("stbd_sector") or raw_info.get("sector") or "업종 미분류",
                "sector_code": row.get("sector_code") or "SEC_MEDIA",  # 🌟 표준 산업코드
                "offering_price": ipo_terms.get("offering_price"),
                "competition_rate": ipo_terms.get("competition_rate"),
                "lockup_rate": ipo_terms.get("lockup_rate"),
                "subscription_date": ipo_terms.get("subscription_date"),
                "listing_date": ipo_terms.get("listing_date"),
                "underwriter": ipo_terms.get("underwriter"),
                "raw_info": raw_info
            })
        return items
    except Exception as e:
        st.error(f"공모주 마스터 DB 목록 로드 실패: {e}")
        return []