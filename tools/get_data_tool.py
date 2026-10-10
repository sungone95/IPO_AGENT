"""회사명으로 OpenDART 공시와 재무 데이터를 조회하는 데이터 접근 계층."""
from __future__ import annotations

import io
import json
import re
import sqlite3
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

DB_PATH = Path(__file__).resolve().parents[1] / "ipo_data.db"
DART = "https://opendart.fss.or.kr/api"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SUMMARY_VERSION = 3


def _stamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS disclosure_analysis (
            kind_id TEXT PRIMARY KEY, corp_code TEXT, payload TEXT NOT NULL, updated_at TEXT NOT NULL);
        """)


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
        # 기업코드 파일이 점검 중이면 최근 지분증권 공시 목록에서 기업을 찾는다.
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
    # LGCNS_AIAgent/FinancialMetricCalculator의 수익성·안정성·현금흐름
    # 분류를 상장 전 기업에 공개되는 DART 계정 항목으로 축약한 계산이다.
    names = {"매출액": "revenue", "영업이익": "operating_profit", "당기순이익": "net_income",
             "자산총계": "assets", "부채총계": "liabilities", "자본총계": "equity",
             "유동자산": "current_assets", "유동부채": "current_liabilities",
             "영업활동현금흐름": "operating_cash_flow",
             "영업활동으로인한현금흐름": "operating_cash_flow"}
    result = {}
    for year in range(date.today().year - 1, date.today().year - 4, -1):
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
            if values.get("equity") and "liabilities" in values:
                values["debt_ratio_pct"] = round(100 * values["liabilities"] / values["equity"], 1)
            if values.get("revenue"):
                if "operating_profit" in values:
                    values["operating_margin_pct"] = round(
                        100 * values["operating_profit"] / values["revenue"], 1)
                if "net_income" in values:
                    values["net_margin_pct"] = round(100 * values["net_income"] / values["revenue"], 1)
            if values.get("current_liabilities") and "current_assets" in values:
                values["current_ratio_pct"] = round(100 * values["current_assets"] / values["current_liabilities"], 1)
            if values.get("net_income") and "operating_cash_flow" in values:
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
    # 원문 파일 API가 점검 중일 때 공개 DART 뷰어의 목차별 본문을 사용한다.
    page = _http("GET", f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={number}").text
    sections = []
    for match in re.finditer(r"var node\d+ = \{\};(.*?)(?=var node\d+ = \{\};|//js tree)", page, re.S):
        block = match.group(1)
        def field(key):
            value = re.search(r"\['" + key + r"'\]\s*=\s*\"([^\"]*)\"", block)
            return value.group(1) if value else None
        title = field("text")
        if not title or not any(term in title for term in (
                "사업의 개요", "주요 제품 및 서비스", "사업위험", "회사위험")):
            continue
        params = {key: field(key) for key in ("rcpNo", "dcmNo", "eleId", "offset", "length", "dtd")}
        if not all(params.values()):
            continue
        viewer = _http("GET", "https://dart.fss.or.kr/report/viewer.do", params=params)
        text = re.sub(r"\s+", " ", BeautifulSoup(viewer.text, "html.parser").get_text(" ", strip=True))
        if text:
            sections.append((title, text[:4000]))
    sections.sort(key=lambda item: 0 if any(term in item[0] for term in ("사업의 개요", "주요 제품 및 서비스")) else 1)
    return "\n".join(f"[{title}] {text}" for title, text in sections)[:15000]


def _summary(filings, financials, key, client):
    if client is None:
        return {"business": "자료 없음", "risks": "자료 없음", "note": "Gemini 키가 설정되지 않았습니다."}
    excerpts = []
    source = None
    candidates = [item for item in filings if (
        "증권신고서" in item["title"] or "투자설명서" in item["title"] or "사업보고서" in item["title"])
        and not any(term in item["title"] for term in ("발행조건확정", "첨부정정", "정정제출요구"))]
    for item in candidates[:3]:
        try:
            text = _document_text(item["rcept_no"], key)
            if text:
                excerpts.append("[" + item["title"] + " " + item["rcept_no"] + "] " + text[:9000])
                source = item
        except (requests.RequestException, ValueError, zipfile.BadZipFile):
            continue
        if excerpts:
            break
    if not excerpts:
        return {"business": "자료 없음", "risks": "자료 없음",
                "note": "공시 목록은 확인했지만 사업·위험 본문을 가져오지 못했습니다."}
    prompt = ("제공된 공시 원문만 근거로 사업 내용과 위험 요인을 각각 3문장 이내로 요약하세요. "
              "근거 없으면 '자료 없음'으로 답하세요. 수익률은 추정하지 마세요. "
              "JSON 키는 business, risks입니다.\n" + "\n".join(excerpts)
              + "\n재무 데이터: " + json.dumps(financials, ensure_ascii=False))
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.1})
        data = json.loads(response.text)
        return {**{part: str(data.get(part) or "자료 없음") for part in ("business", "risks")},
                "note": f"요약 근거: {source['title']} · 접수번호 {source['rcept_no']}"}
    except Exception as exc:
        return {"business": "자료 없음", "risks": "자료 없음",
                "note": f"AI 요약 실패: {type(exc).__name__}"}


def get_disclosure_analysis(company, api_key, client=None, corp_code=None, force=False):
    init_db()
    with _db() as conn:
        cached = conn.execute("SELECT * FROM disclosure_analysis WHERE kind_id=?",
                              (company["kind_id"],)).fetchone()
    if cached and not force and datetime.now().astimezone() - datetime.fromisoformat(cached["updated_at"]) < timedelta(hours=24):
        payload = json.loads(cached["payload"])
        if payload.get("summary_version") == SUMMARY_VERSION:
            return {**payload, "stale": False}
    try:
        candidates = _candidates(company["company_name"], api_key)
        if corp_code:
            candidates = [item for item in candidates if item["corp_code"] == corp_code]
        if not candidates:
            raise ValueError("일치하는 DART 기업을 찾지 못했습니다.")
        if len(candidates) > 1:
            return {"candidates": candidates, "error": "동명이인 기업을 선택해 주세요."}
        selected = candidates[0]
        filings = _filings(selected["corp_code"], api_key)
        financials = _financials(selected["corp_code"], api_key)
        result = {
            "corp_code": selected["corp_code"], "company_name": selected["company_name"],
            "filings": filings[:12], "financials": financials,
            "summary": _summary(filings, financials, api_key, client),
            "summary_version": SUMMARY_VERSION,
            "updated_at": _stamp(), "stale": False, "error": None,
        }
        with _db() as conn:
            conn.execute("""INSERT INTO disclosure_analysis VALUES (?,?,?,?)
                ON CONFLICT(kind_id) DO UPDATE SET corp_code=excluded.corp_code,
                payload=excluded.payload, updated_at=excluded.updated_at""",
                (company["kind_id"], selected["corp_code"], json.dumps(result, ensure_ascii=False),
                 result["updated_at"]))
        return result
    except (requests.RequestException, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        if cached:
            return {**json.loads(cached["payload"]), "stale": True, "error": str(exc)}
        return {"filings": [], "financials": {}, "summary": {"business": "자료 없음", "risks": "자료 없음"},
                "error": str(exc), "stale": False}
