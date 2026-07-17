# CRISP-DM 기반 프로젝트 정의 — Stack Overflow Developer Survey 2024

## 1. 문제·데이터셋 배경 탐색

Stack Overflow Developer Survey 2024(응답자 65,437명)는 전 세계 개발자의 근무형태·기술스택·
연봉·만족도를 담은 설문이다. 2024년 기준 재택근무는 채용·조직설계·급여정책에서 기업이 실제로
의사결정해야 하는 이슈이고, 이 데이터엔 `RemoteWork`(재택/하이브리드/출근)라는 명확한 응답
변수가 있어 이 주제를 데이터로 다뤄볼 근거가 있다.

## 2. 문제 정의

**개발자의 인구통계·경력·기술스택·AI에 대한 태도 정보로 재택근무 여부를 설명·예측할 수 있는가?
그리고 재택근무 여부는 연봉과 유의미한 관계가 있는가?**

## 3. 목표 설정

1. `RemoteWork`(Remote/Hybrid/In-person)를 예측하는 이진분류 모델을 구축한다 (Remote vs 비Remote)
2. Remote vs In-person 그룹 간 연봉 차이가 통계적으로 유의미한지 검증한다
3. 어떤 요인(사용 언어, AI 태도, 경력 등)이 예측력에 실제로 기여하는지 확인한다

## 4. 성공기준 (KPI)

| KPI | 목표 | 현재 달성 |
|---|---|---|
| 분류 모델 F1-score | 베이스라인보다 유의미하게 개선 | **0.612** (기본 컬럼만 썼을 때 0.578 대비 개선) |
| t-test 유의성 | p < 0.05 | **p = 3.3×10⁻⁹** (달성) |
| 파이프라인 재현성 | 자동 실행으로 리포트·모델 생성 | `python main.py` 한 번으로 report.md+차트 2종+모델 파일 자동 생성 (달성) |
| 데이터 규모 | 통계적으로 유의미한 표본 확보 | 52,622명 (달성) |

## 5. 프로토타입

`day2_종합실습/` 전체가 이 프로토타입이다.

```bash
cd day2_종합실습
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

실행하면 다음이 자동 생성된다:
- `reports/report.md` — 데이터 개요·통계분석·시각화·ML 결과 종합 리포트
- `reports/eda_seaborn.png` — 연봉 분포 + 근무형태별 실무경력 박스플롯
- `reports/eda_plotly.html` — 수치형 컬럼 상관관계 인터랙티브 히트맵
- `models/remote_work_model.pkl` — 학습된 분류 모델(LogisticRegression)

## 6. 데이터 준비 요약 (CRISP-DM: 데이터 이해 → 데이터 준비)

- 원본 114개 컬럼 중 응답률·관련성 기준으로 25개 컬럼 선정 (사용 컬럼 평균 응답률 73.8% vs
  전체 평균 61.2%)
- 타깃(`RemoteWork`) 결측 10,631건 제거, 중복 2,184건 제거 → 52,622행
- 다중선택 컬럼(`LanguageHaveWorkedWith`)은 상위 10개 언어를 이진 피처(`lang_*`)로 분해
- Pandas 대비 Polars 로딩 속도 약 7.9배 빠름 (0.15초 vs 1.23초, 전체 114개 컬럼 기준)
