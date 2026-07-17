# Day 2 종합실습 — Stack Overflow Developer Survey 2024 End-to-End 분석

SKALA 데이터분석 및 AIOps 과정 Day 2 종합실습. Stack Overflow Developer Survey 2024
데이터로 Pandas/Polars 데이터 준비 → 통계분석 → 시각화 → sklearn ML Pipeline → Jinja2
리포트 자동 생성까지 수행한다.

## 개발 환경 설정

```bash
cd day2_종합실습
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 실행 방법

```bash
python main.py
```

최초 실행 시 `data/raw/results.csv`(약 152MB)를 자동 다운로드한다. 완료되면
`reports/report.md`, `reports/eda_seaborn.png`, `reports/eda_plotly.html`,
`models/remote_work_model.pkl`이 생성된다. 실행 로그는 콘솔과 `logs/pipeline.log`에
동시에 기록된다(`print()` 대신 `logging` 모듈 사용).

## 테스트

```bash
pytest tests/ -v
```

네트워크 다운로드 없이(합성 데이터 fixture 사용) 각 모듈의 `run()`을 독립적으로 검증한다.
`data_prep`은 다운로드 캐시 로직·컬럼 변환 함수만 순수 단위 테스트로 확인한다.

## 분석 내용

- **데이터**: Stack Overflow Developer Survey 2024 (114개 컬럼 중 25개 사용)
  - 기본 컬럼(10개): `RemoteWork`(타깃), `Age`, `Employment`, `EdLevel`, `DevType`, `OrgSize`,
    `Country`, `ConvertedCompYearly`, `WorkExp`, `JobSat`
  - 확장 컬럼(5개): `MainBranch`, `Industry`, `ICorPM`, `AISent`, `YearsCode`
  - 언어 플래그(10개): `LanguageHaveWorkedWith`(다중선택, 세미콜론 구분)에서 응답 빈도
    상위 10개 언어(JavaScript/HTML-CSS/Python/SQL/TypeScript/Bash·Shell/Java/C#/C++/C)를
    `lang_*` 이진 컬럼으로 풀어냄
  - 나머지 89개 컬럼은 자유서술형·조건부 스킵으로 결측이 극단적으로 많거나 분석 목적과
    무관해 제외
- **결측치 처리**: 타깃(`RemoteWork`)이 없는 행은 제거. 언어 플래그는 무응답을 "해당 언어
  미사용(0)"으로 채움. 그 외 컬럼의 결측(3~55%대)은 일괄 삭제하지 않고 통계 단계는
  `dropna`, ML 단계는 `SimpleImputer`로 각자 필요한 곳에서 처리 —
  `eda_summary.missing_ratio`로 결측 현황은 투명하게 보고한다.
- **통계**: 기술통계, 상관계수, Remote vs In-person 연봉 평균 t-test
- **시각화**: Seaborn(연봉 분포 + 실무경력 박스플롯), Plotly(상관관계 히트맵)
- **ML**: `RemoteWork == "Remote"` 이진분류, LogisticRegression(F1≈0.61) vs
  RandomForestClassifier(F1≈0.56) 비교 — 언어 플래그·AI 태도 등 확장 피처 덕분에 기본
  10컬럼만 썼을 때(F1≈0.58)보다 향상됨

## 프로젝트 구조

```
day2_종합실습/
├── data/raw/                   # 원본 데이터 (자동 다운로드, git 제외)
├── src/
│   ├── data_prep.py            # 데이터 준비
│   ├── stats_analysis.py       # 통계분석
│   ├── visualize_seaborn.py    # 정적 시각화
│   ├── visualize_plotly.py     # 인터랙티브 시각화
│   ├── ml_pipeline.py          # ML Pipeline
│   ├── report.py               # 리포트 자동화
│   └── logging_config.py       # 공용 logging 설정
├── tests/                      # pytest 테스트 (모듈별 1파일 + conftest.py 공용 fixture)
├── templates/report_template.md.j2
├── reports/                    # report.md, 차트 출력 (git 제외)
├── models/                     # 저장된 모델 (git 제외)
├── logs/                       # pipeline.log (git 제외)
├── main.py                     # 파이프라인 진입점
└── requirements.txt
```

## 아직 남은 것 (코드로 대신할 수 없는 부분)

- 팀 발표 5분
- 제출용 "실행결과 정리" PDF (실행 화면 캡처 + 본인 의견) — `캠퍼스명_반_이름_실습명.zip`
  파일명으로 제출

## 참고

- 설계 문서: `docs/superpowers/specs/2026-07-16-day2-종합실습-design.md`
- 구현 계획: `docs/superpowers/plans/2026-07-16-day2-종합실습-implementation.md`
- 데이터 출처: https://github.com/StackExchange/Survey (2024년 설문 결과)
