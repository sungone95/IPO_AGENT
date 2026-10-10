# IPO AI 투자 AGENT

Streamlit 기반 공모주 공시 분석 앱입니다. 공모 일정은 KIND 링크에서 확인하고,
분석할 회사명을 직접 입력합니다. 재무·공시 데이터는 OpenDART에서 가져옵니다.
기존 가상 종목은 **데모 종목** 모드에서 확인할 수 있습니다.

## 실행

```bash
cd IPO_AGENT
python -m pip install -r requirements.txt
mkdir -p .streamlit
# .streamlit/secrets.toml에 아래 키를 설정
streamlit run app.py
```

```toml
DART_API_KEY = "OpenDART에서 발급받은 키"
GEMINI_API_KEY = "Google AI Studio에서 발급받은 키"
```

`DART_API_KEY`는 실제 기업 공시 분석에 필요합니다. `GEMINI_API_KEY`는
공시의 사업·위험 요약과 데모 모드의 AI 기능에 사용됩니다. 키는 Git에
올리지 마세요.

## 실제 데이터 흐름

1. 앱의 **KIND 공모일정 열기** 버튼으로 공모 일정을 확인한 뒤 회사명을 입력합니다.
2. **선택 기업 공시 분석**을 누르면 OpenDART 기업
   고유번호를 찾습니다. 이름이 여러 곳에 일치하면 사용자가 기업을 고릅니다.
3. 최근 공시에서 증권신고서·투자설명서와 정기보고서를 조회합니다.
   OpenDART 정기 재무제표가 있으면 매출액, 영업이익, 순이익, 자산·부채·자본,
   영업현금흐름 및 계산 가능한 비율을 표시합니다.
4. 공시 원문을 확보했고 Gemini 키가 있으면 사업·위험 요약을 생성합니다.
   각 공시의 접수번호, 접수일, 원문 링크도 함께 표시합니다.

기업 공시 분석은 24시간 동안 로컬 DB를 재사용합니다. 조회 실패 시 마지막
정상 데이터를 갱신 시각과 함께 표시합니다. SQLite 파일 `ipo_data.db`는
자동 생성되며 Git에서 제외됩니다.

앱은 KIND 일정을 직접 수집하지 않습니다. 상장 전 회사는 OpenDART 정기
재무제표가 없을 수 있으므로 이 경우 공시 목록과 확인 가능한 요약만 보여줍니다.

실제 기업 화면은 데모 리포트와 같은 블록 구성을 사용합니다. OpenDART에서
확인한 재무지표와 공시 요약만 채우고, 연결되지 않은 공모 조건·시장 평균·
고객 거래 성향·예상 주가와 수익률은 `자료 없음`으로 표시합니다. 재무·공시
상세 자료는 리포트 맨 아래에서 볼 수 있습니다. 실제 기업 AI Q&A는 조회된
공시·재무 자료만 문맥으로 사용합니다. 데모 종목의 기업·시장·고객 데이터와
차트는 모두 예시 값입니다.

## 데이터 출처

- [KIND 공모일정](https://kind.krx.co.kr/listinvstg/pubofrschdl.do?method=searchPubofrScholMain)
- [OpenDART 개발가이드](https://opendart.fss.or.kr/guide/main.do)
