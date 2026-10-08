""" 용빈사원님 외부데이터 가져오는 tool 
    ### 현재 임시 코드임 ###
"""


import sqlite3
import pandas as pd
from typing import Dict, Any

DB_PATH = "ipo_data.db"

def init_db():
    """DB 테이블 초기화"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ipo_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE,
            sector TEXT,
            offering_price INTEGER,
            competition_rate REAL,
            underwriter TEXT,
            subscription_date TEXT,
            lockup_rate TEXT
        )
    """)
    conn.commit()
    conn.close()

def sync_external_ipo_data():
    """외부 API 데이터를 호출하여 DB에 동기화 (용빈사원님 모듈 완성 전 임시 데이터)"""
    init_db()
    sample_data = [
        ("에이아이테크", "IT/SaaS", 25000, 1350.5, "한국투자증권", "2026-10-15 ~ 2026-10-16", "35.4%"),
        ("바이오케어", "바이오/제약", 18000, 890.2, "NH투자증권", "2026-10-20 ~ 2026-10-21", "12.1%")
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for item in sample_data:
        cursor.execute("""
            INSERT OR REPLACE INTO ipo_events 
            (company_name, sector, offering_price, competition_rate, underwriter, subscription_date, lockup_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, item)
    conn.commit()
    conn.close()

def get_ipo_info_from_db(company_name: str = None) -> str:
    """Gemini 프롬프트에 전달할 DB 조회 텍스트"""
    conn = sqlite3.connect(DB_PATH)
    if company_name:
        df = pd.read_sql_query("SELECT * FROM ipo_events WHERE company_name LIKE ?", conn, params=(f"%{company_name}%",))
    else:
        df = pd.read_sql_query("SELECT * FROM ipo_events", conn)
    conn.close()
    
    if df.empty:
        return "조회된 공모주 데이터가 없습니다."
    return df.to_string(index=False)

def get_company_dict(company_name: str) -> Dict[str, Any]:
    """특정 종목의 상세 정보를 Dict 형태로 반환 (B, C 모듈 연동용)"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM ipo_events WHERE company_name LIKE ?", conn, params=(f"%{company_name}%",))
    conn.close()
    
    if not df.empty:
        return df.iloc[0].to_dict()
    return {}
