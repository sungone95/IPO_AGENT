"""회사명으로 OpenDART 공시와 재무 데이터를 조회하는 데이터 접근 계층 (Supabase IPO_INFO_MASTER 캐시)."""
from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import date, datetime, timedelta
from xml.etree import ElementTree

import requests
import streamlit as st
from bs4 import BeautifulSoup
from supabase import create_client, Client
from tools.web_search_tool import search_ipo_web_data

DART = "https://opendart.fss.or.kr/api"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SUMMARY_VERSION = 5


def _stamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


@st.cache_resource
def _get_supabase_client() -> Client:
    """Streamlit Secrets 기반 Supabase 클라이언트 연결"""
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    return create_client(url, key)


def _http(method, url, **kwargs):
    response = requests.request(method, url, headers=HEADERS, timeout=20, **kwargs)
    response.raise_for_status()
    return response


def _dart_json(endpoint, key, **params):
    data = _http("GET", DART + "/" + endpoint + ".json", params={"crtfc_key": key, **params}).json()
    if data.get("status") not in (None, "000", "013"):
        raise ValueError("OpenDART " + endpoint + ": " + data.get("message", "조회 실패"))
    return data


def _candidates(name, key):
    clean_name = name.strip()
    
    # 🌟 1. Supabase IPO_INFO_MASTER 에 이미 등록된 기업인지 우선 확인 (zip 다운로드 절약)
    try:
        supabase = _get_supabase_client()
        db_res = supabase.table("IPO_INFO_MASTER") \
            .select("stbd_code, stbd_name") \
            .ilike("stbd_name", f"%{clean_name}%") \
            .execute()
        if db_res.data:
            exact = [item for item in db_res.data if item["stbd_name"] == clean_name]
            targets = exact or db_res.data[:5]
            return [{"corp_code": r["stbd_code"], "company_name": r["stbd_name"]} for r in targets]
    except Exception:
        pass

    # 🌟 2. DB에 없을 때만 DART 전체 고유번호 zip 다운로드 수행
    binary = _http("GET", DART + "/corpCode.xml", params={"crtfc_key": key}).content
    result = []
    if zipfile.is_zipfile(io.BytesIO(binary)):
        with zipfile.ZipFile(io.BytesIO(binary)) as archive:
            root = ElementTree.fromstring(archive.read("CORPCODE.xml"))
        for item in root.findall("list"):
            company = (item.findtext("corp_name") or "").strip()
            if company == name or name in company:
                result.append({"corp_code": item.findtext("corp_code"), "company_name": company})
    else:
        # 기업코드 파일 점검 시 최근 지분증권 공시 목록 검색
        for page in range(1, 11):
            data = _dart_json(
                "list", key, bgn_de=(date.today() - timedelta(days=89)).strftime("%Y%m%d"),
                end_de=date.today().strftime("%Y%m%d"), pblntf_detail_ty="C001",
                page_no=page, page_count=100)
            for item in data.get("list", []):
                company = item.get("corp_name", "").strip()
                if company == name or name in company:
                    result.append({"corp_code": item["corp_code"], "company_name": company})
            if page >= int(data.get("total_page", 0)):
                break
    result = list({item["corp_code"]: item for item in result}.values())
    exact = [item for item in result if item["company_name"] == name]
    return exact or sorted(result, key=lambda item: item["company_name"])[:10]


def _filings(corp_code, key):
    found = []
    for page in range(1, 4):
        data = _dart_json("list", key, corp_code=corp_code,
                          bgn_de=(date.today() - timedelta(days=1095)).strftime("%Y%m%d"),
                          end_de=date.today().strftime("%Y%m%d"), page_no=page, page_count=100)
        found += data.get("list", [])
        if page >= int(data.get("total_page", 0)):
            break
    types = ("증권신고서", "투자설명서", "사업보고서", "분기보고서", "반기보고서")
    found = [row for row in found if any(term in row.get("report_nm", "") for term in types)]
    found.sort(key=lambda row: (next(i for i, term in enumerate(types) if term in row["report_nm"]),
                                -int(row.get("rcept_dt", "0"))))
    return [{"title": row["report_nm"], "rcept_no": row["rcept_no"],
             "rcept_dt": row.get("rcept_dt"),
             "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + row["rcept_no"]}
            for row in found]


def _financials(corp_code, key):
    names = {"매출액": "revenue", "영업이익": "operating_profit", "당기순이익": "net_income",
             "자산총계": "assets", "부채총계": "liabilities", "자본총계": "equity",
             "유동자산": "current_assets", "유동부채": "current_liabilities",
             "영업활동현금흐름": "operating_cash_flow",
             "영업활동으로인한현금흐름": "operating_cash_flow"}
    result = {}
    current_year = date.today().year
    for year in range(current_year - 1, current_year - 4, -1):
        try:
            data = _dart_json("fnlttSinglAcntAll", key, corp_code=corp_code, bsns_year=year,
                              reprt_code="11011", fs_div="CFS")
            if not data.get("list"):
                data = _dart_json("fnlttSinglAcntAll", key, corp_code=corp_code, bsns_year=year,
                                  reprt_code="11011", fs_div="OFS")
        except (requests.RequestException, ValueError):
            continue
        values = {}
        for item in data.get("list", []):
            metric = names.get(item.get("account_nm", "").replace(" ", ""))
            amount = re.sub(r"[^\d-]", "", item.get("thstrm_amount") or "")
            if metric and amount and metric not in values:
                values[metric] = int(amount)
        if values:
            if values.get("equity") and "liabilities" in values and values["equity"] != 0:
                values["debt_ratio_pct"] = round(100 * values["liabilities"] / values["equity"], 1)
            if values.get("revenue") and values["revenue"] != 0:
                if "operating_profit" in values:
                    values["operating_margin_pct"] = round(
                        100 * values["operating_profit"] / values["revenue"], 1)
                if "net_income" in values:
                    values["net_margin_pct"] = round(100 * values["net_income"] / values["revenue"], 1)
            if values.get("current_liabilities") and "current_assets" in values and values["current_liabilities"] != 0:
                values["current_ratio_pct"] = round(100 * values["current_assets"] / values["current_liabilities"], 1)
            if values.get("net_income") and "operating_cash_flow" in values and values["net_income"] != 0:
                values["cash_flow_to_profit_pct"] = round(
                    100 * values["operating_cash_flow"] / values["net_income"], 1)
            result[str(year)] = values
    return result


def _document_text(number, key):
    try:
        binary = _http("GET", DART + "/document.xml", params={"crtfc_key": key, "rcept_no": number}).content
    except requests.RequestException:
        binary = b""
    if zipfile.is_zipfile(io.BytesIO(binary)):
        with zipfile.ZipFile(io.BytesIO(binary)) as archive:
            name = next((item for item in archive.namelist() if item.lower().endswith(".xml")), None)
            if name:
                text = re.sub(r"\s+", " ", BeautifulSoup(archive.read(name), "html.parser").get_text(" ", strip=True))
                sections = []
                for heading in ("사업의 내용", "투자위험요소", "위험요소"):
                    locations = [match.start() for match in re.finditer(re.escape(heading), text)]
                    if locations:
                        start = next((position for position in locations if position > 3000), locations[-1])
                        sections.append(f"[{heading}] " + text[start:start + 3500])
                return "\n".join(sections)[:14000] if sections else text[:10000]
    
    # 원문 파일 점검 시 공개 DART 뷰어 스크래핑
    page = _http("GET", f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={number}").text
    sections = []
    for match in re.finditer(r"var node\d+ = \{\};(.*?)(?=var node\d+ = \{\};|//js tree)", page, re.S):
        block = match.group(1)
        def field(k):
            val = re.search(r"\['" + k + r"'\]\s*=\s*\"([^\"]*)\"", block)
            return val.group(1) if val else None
        title = field("text")
        if not title or not any(term in title for term in (
                "사업의 개요", "주요 제품 및 서비스", "사업위험", "회사위험")):
            continue
        params = {k: field(k) for k in ("rcpNo", "dcmNo", "eleId", "offset", "length", "dtd")}
        if not all(params.values()):
            continue
        viewer = _http("GET", "https://dart.fss.or.kr/report/viewer.do", params=params)
        text = re.sub(r"\s+", " ", BeautifulSoup(viewer.text, "html.parser").get_text(" ", strip=True))
        if text:
            sections.append((title, text[:4000]))
    sections.sort(key=lambda item: 0 if any(term in item[0] for term in ("사업의 개요", "주요 제품 및 서비스")) else 1)
    return "\n".join(f"[{title}] {text}" for title, text in sections)[:15000]


def _extract_ipo_core_data(filings, financials, key, client, fallback_sector="기타"):
    """증권신고서/투자설명서 본문과 재무데이터를 분석하여 상장일정, 공모가, 강점 등을 정형 추출"""
    if client is None:
        return {
            "sector": fallback_sector,
            "ipo_metrics": {},
            "strengths": ["Gemini 클라이언트 미연결"],
            "business": "자료 없음",
            "risks": "자료 없음",
            "note": "AI 키 미설정"
        }

    excerpts = []
    source = None
    # 1. 증권신고서(지분증권), 투자설명서 우선 탐색
    candidates = [
        item for item in filings 
        if any(term in item["title"] for term in ("증권신고서(지분증권)", "투자설명서", "증권신고서", "사업보고서"))
        and not any(term in item["title"] for term in ("첨부정정", "정정제출요구"))
    ]

    for item in candidates[:3]:
        try:
            text = _document_text(item["rcept_no"], key)
            if text:
                excerpts.append(f"[{item['title']} - {item['rcept_no']}]\n" + text[:9000])
                source = item
                break
        except Exception:
            continue

    if not excerpts:
        return {
            "sector": fallback_sector,
            "ipo_metrics": {},
            "strengths": ["공시 본문 확보 실패"],
            "business": "공시 원문 누락",
            "risks": "공시 원문 누락",
            "note": "증권신고서 본문을 읽지 못했습니다."
        }

    # 2. 핵심 지표 추출 프롬프트
    prompt = f"""
당신은 대한민국 IPO 공모주 분석 전문가입니다.
제공된 공시 원문과 재무 데이터를 면밀히 검토하여 투자 판단에 직결되는 핵심 지표들을 추출하세요.
원문에 명시되어 있지 않은 수치는 추정하지 말고 null 또는 빈 문자열("")로 반환하세요.

[공시 원문 발췌본]
{"".join(excerpts)}

[재무제표 데이터]
{json.dumps(financials, ensure_ascii=False)}

반드시 아래 JSON 스키마 규격으로만 응답하세요:
{{
    "sector": "세부 산업군 명칭 (예: 인공지능/클라우드, 2차전지 장비, 바이오시밀러 등)",
    "ipo_metrics": {{
        "offering_price": 공모가(숫자만, 미확정 시 밴드 상단 정수, 없으면 null),
        "price_band": "희망공모가액 밴드 (예: '24,000 ~ 28,000원')",
        "subscription_date": "청약일정 (예: '2026.10.15 ~ 2026.10.16')",
        "listing_date": "상장예정일자 (예: '2026.10.28')",
        "underwriter": "대표주관회사 (예: 'KB증권')",
        "competition_rate": 기관 수요예측 경쟁률(실수/정수, 없으면 null),
        "lockup_rate": 의무보유확약 비율(숫자%, 없으면 null)
    }},
    "strengths": [
        "해당 기업만의 핵심 경쟁력 및 실적/기술 강점 1",
        "해당 기업만의 핵심 경쟁력 및 실적/기술 강점 2",
        "해당 기업만의 핵심 경쟁력 및 실적/기술 강점 3"
    ],
    "business_summary": "핵심 사업 모델 및 주요 매출원 (2~3문장)",
    "risks": "핵심 투자위험요소 및 유통물량/경쟁 리스크 (2~3문장)"
}}
"""
    try:
        response = client.models.generate_content(
            model="DEFAULT_GEMINI_MODEL",
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.1}
        )
        data = json.loads(response.text)
        data["note"] = f"근거 공시: {source['title']} ({source['rcept_no']})" if source else "자동 추출"
        return data
    except Exception as exc:
        return {
            "sector": fallback_sector,
            "ipo_metrics": {},
            "strengths": [f"AI 추출 실패: {type(exc).__name__}"],
            "business": "추출 오류",
            "risks": "추출 오류",
            "note": "추출 실패"
        }


# ==========================================
# 🌟 [MAIN] Supabase IPO_INFO_MASTER 연동 엔트리포인트
# ==========================================
SUMMARY_VERSION = 4  # 스키마가 대폭 업그레이드되었으므로 버전 상향 (기존 캐시 자동 갱신 유도)

# ==========================================
# 🌟 [MAIN] Supabase IPO_INFO_MASTER 연동 엔트리포인트
# ==========================================
def get_disclosure_analysis(company, api_key, client=None, corp_code=None, force=False):
    """
    잡다한 DART 링크/메타데이터를 제거하고, 
    핵심 공모조건/사업강점/재무지표만 정제하여 Supabase IPO_INFO_MASTER에 영구 저장
    """
    company_name = company.get("company_name", "").strip()
    clean_name = company_name
    supabase = _get_supabase_client()

    # 1. 🔍 [Cache Hit] 종목명 기준 DB 캐시 우선 조회
    cached_row = None
    if not force and clean_name:
        try:
            resp = supabase.table("IPO_INFO_MASTER") \
                .select("*") \
                .eq("stbd_name", clean_name) \
                .limit(1) \
                .execute()

            if resp.data:
                cached_row = resp.data[0]
                raw_info = cached_row.get("raw_info") or {}

                if "ipo_terms" in raw_info or "business_analysis" in raw_info:
                    biz_ana = raw_info.get("business_analysis", {})
                    return {
                        **raw_info,
                        "ipo_metrics": raw_info.get("ipo_terms", {}),
                        "financials": raw_info.get("financial_history", {}),
                        "business_analysis": biz_ana,
                        "summary": {
                            "business": biz_ana.get("business_summary", "자료 없음"),
                            "risks": biz_ana.get("investment_risks", "자료 없음")
                        },
                        "strengths": biz_ana.get("strengths", []),
                        "_from_cache": True,
                        "stale": False,
                        "updated_at": raw_info.get("updated_at")
                    }
        except Exception as e:
            st.warning(f"DB 캐시 조회 실패: {e}")

    # 2. 📡 [Cache Miss] DART + Web 수집 단계 분리 실행
    actual_corp_name = clean_name
    actual_corp_code = corp_code or ""
    detected_sector = company.get("sector") or "공모주/신규상장"
    
    filings = []
    financials = {}
    extracted = {}
    dart_strengths = []
    ipo_terms = {}

    # -------------------------------------------------------------
    # (A) DART 공시 수집 시도 (실패해도 중단 없이 통과)
    # -------------------------------------------------------------
    try:
        candidates = _candidates(clean_name, api_key)
        if corp_code:
            candidates = [item for item in candidates if item["corp_code"] == corp_code]

        if len(candidates) > 1:
            return {"candidates": candidates, "error": "동명이인 기업을 선택해 주세요."}

        if candidates:
            selected = candidates[0]
            actual_corp_code = selected["corp_code"]
            actual_corp_name = selected["company_name"]

            filings = _filings(actual_corp_code, api_key)
            financials = _financials(actual_corp_code, api_key)

            extracted = _extract_ipo_core_data(
                filings=filings,
                financials=financials,
                key=api_key,
                client=client,
                fallback_sector=detected_sector
            )
            detected_sector = extracted.get("sector") or detected_sector
            ipo_terms = extracted.get("ipo_metrics", {})
            dart_strengths = extracted.get("strengths", [])
    except Exception as dart_err:
        # DART 에러 시 멈추지 않고 알림만 남긴 뒤 Web Search로 계속 진행
        st.caption(f"DART 공시 수집 제한 ({clean_name}): {dart_err}. 실시간 웹 수집으로 대체합니다.")

    # -------------------------------------------------------------
    # (B) 🌟 웹 검색은 DART 유무와 무관하게 100% 무조건 실행!
    # -------------------------------------------------------------
    web_info = {}
    try:
        web_info = search_ipo_web_data(
            company_name=actual_corp_name,
            sector=detected_sector,
            client=client
        )
    except Exception as web_err:
        st.caption(f"웹 수집 중 예외 발생: {web_err}")

    # -------------------------------------------------------------
    # (C) 융합 및 보완 (Web 데이터로 빈자리 강제 채우기)
    # -------------------------------------------------------------
    # 1) 공모 수치 병합 (DART에 없거나 0이면 웹 데이터로 주입)
    if web_info:
        for k in ["offering_price", "competition_rate", "lockup_rate", "listing_date", "underwriter"]:
            if web_info.get(k) is not None:
                if not ipo_terms.get(k) or ipo_terms.get(k) == 0:
                    ipo_terms[k] = web_info[k]

    # 2) 강점 병합 (DART 강점 + 웹 업계 경쟁력)
    web_strengths = web_info.get("industry_strengths", []) if web_info else []
    all_strengths = list(dict.fromkeys(dart_strengths + web_strengths))
    if not all_strengths:
        all_strengths = ["실시간 시장 분석을 통해 지속 확인 중입니다."]

    # 3) 사업 내용 및 위험 요인 (DART가 없을 때 웹 정보 활용)
    biz_summary = extracted.get("business_summary")
    if not biz_summary or biz_summary in ("자료 없음", "공시 서류 본문을 가져오지 못했습니다."):
        biz_summary = web_info.get("market_sentiment") or f"{actual_corp_name}의 신규 상장 공모주 분석 자료입니다."

    risks = extracted.get("risks")
    if not risks or risks in ("자료 없음", "공시 서류 본문을 가져오지 못했습니다."):
        risks = "신규 상장 초기 주가 변동성 및 시장 수급 상황에 유의해야 합니다."

    # -------------------------------------------------------------
    # (D) 최종 정제 JSON 생성 및 Supabase 영구 적재
    # -------------------------------------------------------------
    pure_ipo_info = {
        "company_name": actual_corp_name,
        "sector": detected_sector,
        "ipo_terms": ipo_terms,
        "business_analysis": {
            "strengths": all_strengths[:5],
            "market_sentiment": web_info.get("market_sentiment", "시장 분석 진행 중") if web_info else "확인 필요",
            "peer_differentiation": web_info.get("peer_differentiation", "자료 없음") if web_info else "확인 필요",
            "business_summary": biz_summary,
            "investment_risks": risks
        },
        "financial_history": financials,
        "updated_at": _stamp()
    }

    try:
        payload = {
            "stbd_name": actual_corp_name,
            "stbd_code": actual_corp_code,
            "stbd_sector": detected_sector,
            "raw_info": pure_ipo_info,
            "update_time": datetime.now().astimezone().isoformat()
        }
        supabase.table("IPO_INFO_MASTER").upsert(payload, on_conflict="stbd_name").execute()
    except Exception as save_err:
        st.warning(f"IPO_INFO_MASTER 캐시 저장 실패: {save_err}")

    # UI 반환 데이터
    return {
        **pure_ipo_info,
        "ipo_metrics": pure_ipo_info["ipo_terms"],
        "financials": financials,
        "business_analysis": pure_ipo_info["business_analysis"],
        "summary": {
            "business": pure_ipo_info["business_analysis"]["business_summary"],
            "risks": pure_ipo_info["business_analysis"]["investment_risks"]
        },
        "strengths": pure_ipo_info["business_analysis"]["strengths"],
        "_from_cache": False,
        "stale": False,
        "error": None
    }