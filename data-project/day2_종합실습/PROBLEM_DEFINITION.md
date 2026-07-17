# CRISP-DM 기반 프로젝트 정의 — Stack Overflow Developer Survey 2024

## 1. 문제·데이터셋 배경 탐색

Stack Overflow Developer Survey 2024(응답자 65,437명)는 전 세계 개발자의 근무형태·기술스택·
연봉·만족도를 담은 설문이다. 2024년 기준 재택근무는 채용·조직설계·급여정책에서 기업이 실제로
의사결정해야 하는 이슈이고, 이 데이터엔 `RemoteWork`(재택/하이브리드/출근)라는 명확한 응답
변수가 있어 이 주제를 데이터로 다뤄볼 근거가 있다.

## 2. 문제 정의

**개발자의 인구통계·경력·기술스택·AI에 대한 태도 정보로 재택근무 여부를 설명·예측할 수 있는가?
그리고 재택근무 여부는 연봉과 유의미한 관계가 있는가?**

### 2.1 핵심 변수 정의: `RemoteWork`

설문 문항("지금 근무 형태가 어떻게 되나요?")에 대한 응답으로, 세 가지 범주를 갖는다.

| 범주 | 의미 | 정제 데이터 기준 인원 |
|---|---|---|
| Hybrid (some remote, some in-person) | 하이브리드 — 재택과 사무실 출근을 섞어서 함(예: 주 2~3일 출근) | 22,081명 (42.0%) |
| Remote | 완전 재택근무 — 사무실에 안 나가고 원격지에서 근무 | 20,205명 (38.4%) |
| In-person | 완전 출근 — 매일 사무실에서 근무 | 10,336명 (19.6%) |

분석에서는 이 세 범주를 목적에 따라 다르게 활용한다:
- **ML 분류(3번 목표)**: Remote(1) vs 나머지(Hybrid+In-person, 0)로 이진화 — "완전 재택근무자인가"를 예측
- **t-test(2번 목표)**: Remote vs In-person 두 극단만 비교 — Hybrid는 중간 성격이라 제외하면 차이가 더 명확하게 드러남

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

### 6.1 사용 컬럼 상세 (원본 114개 중 25개)

**타깃 (1개)**

| 컬럼 | 의미 |
|---|---|
| `RemoteWork` | 근무 형태 (Remote/Hybrid/In-person) — 위 2.1 참고 |

**기본 범주형 (6개) — 인구통계·직무 기본 정보**

| 컬럼 | 의미 |
|---|---|
| `Age` | 연령대 (예: "25-34 years old") |
| `Employment` | 고용 형태 (정규직/프리랜서/학생 등, 다중선택 가능) |
| `EdLevel` | 최종 학력 |
| `DevType` | 개발자 직군 (풀스택/백엔드/프론트엔드/데스크톱 등) |
| `OrgSize` | 소속 조직 규모 (직원 수 구간) |
| `Country` | 거주 국가 |

**확장 범주형 (4개) — 이번에 추가로 넓힌 컬럼**

| 컬럼 | 의미 |
|---|---|
| `MainBranch` | 개발자 여부 유형 (전문 개발자/학습자/취미로 코딩/과거 개발자 등) |
| `Industry` | 소속 산업군 (소프트웨어/금융/헬스케어 등) |
| `ICorPM` | 개인 기여자(Individual Contributor) vs 매니저(People Manager) |
| `AISent` | AI 도구에 대한 태도 (매우 긍정적 ~ 매우 부정적) |

**수치형 (4개) — 통계·시각화·ML 전 단계에서 다목적으로 사용**

| 컬럼 | 의미 |
|---|---|
| `ConvertedCompYearly` | 연봉 (USD 환산) |
| `WorkExp` | 실무 경력 (년) |
| `JobSat` | 직무 만족도 (1~10점) |
| `YearsCode` | 총 코딩 경력 (취미 포함, 년) |

**언어 플래그 (10개) — `LanguageHaveWorkedWith`(다중선택)에서 파생, ML 피처 전용**

응답 빈도 상위 10개 언어를 "해당 언어를 써봤는가(1/0)"로 각각 이진 컬럼화했다.

`lang_javascript`, `lang_html_css`, `lang_python`, `lang_sql`, `lang_typescript`,
`lang_bash_shell`, `lang_java`, `lang_csharp`, `lang_cpp`, `lang_c`

## 7. 모델링 (알고리즘 분석)

**피처·타깃 구성**
- 타깃: `RemoteWork == "Remote"` → 1, 그 외(Hybrid/In-person) → 0 (이진분류)
- 피처 24개: 수치형 4개(`ConvertedCompYearly`/`WorkExp`/`JobSat`/`YearsCode`) + 언어 플래그
  10개(`lang_*`) + 범주형 10개(`Age`~`AISent`)

**전처리**: `ColumnTransformer`로 유형별로 다르게 처리한다.
- 수치형: `SimpleImputer(strategy="median")` → `StandardScaler`
- 범주형: `SimpleImputer(strategy="constant", fill_value="missing")` → `OneHotEncoder(handle_unknown="ignore")`

**알고리즘 후보 2개를 의도적으로 대비되는 계열로 골랐다**

| 모델 | 계열 | 선택 이유 |
|---|---|---|
| `LogisticRegression` | 선형 | 해석 용이, 학습 빠름, 베이스라인으로 적합 |
| `RandomForestClassifier` | 비선형(트리 앙상블) | 피처 간 상호작용·비선형 패턴을 잡아낼 수 있는지 확인 |

두 계열을 비교하면 "이 문제가 몇 개 요인의 단순 결합으로 설명되는지, 아니면 복잡한 상호작용이
필요한지"를 확인할 수 있다.

**학습 설정**: `train_test_split(test_size=0.2, random_state=42, stratify=y)` — 클래스 비율
(약 38:62)을 train/test에 동일하게 유지하고, `random_state` 고정으로 재현성을 확보한다.

**선택 기준**: `accuracy`가 아니라 **F1-score**로 최종 모델을 고른다. 클래스가 완전히
균형잡히지 않아서(38:62) accuracy만으로는 다수 클래스를 그냥 예측해도 점수가 높게 나올 수
있기 때문이다.

**결과**: `LogisticRegression`(F1 0.612)이 `RandomForest`(F1 0.556)보다 우세해 최종
선택됐다 → 이 데이터에서는 재택근무 여부가 복잡한 비선형 상호작용보다 몇 개 요인(연봉·경력·
언어스택·AI 태도 등)의 비교적 단순한 결합으로 상당 부분 설명된다는 뜻이다. 모델은
`joblib.dump()`로 저장하고, 재로딩 후 동일한 F1이 나오는지까지 검증한다.

## 8. 평가 (성능지표, 목표 검토)

3번 목표 각각을 실제 결과로 다시 검토한다.

| 목표 | 결과 | 판정 |
|---|---|---|
| 1) 재택근무 여부 이진분류 모델 구축 | LogisticRegression F1 0.612, Accuracy 72.9% | ✅ 달성 |
| 2) Remote vs In-person 연봉 차이 통계적 검증 | t=5.93, p=3.3×10⁻⁹ (p<0.05) | ✅ 달성 |
| 3) 예측력에 기여하는 요인 파악 | 기본 10컬럼(F1 0.578) → 확장 25컬럼(F1 0.612)으로 **피처를 추가하니 실제로 성능이 오른다는 것까지는 확인**했지만, 어떤 피처가 얼마나 기여했는지(계수·중요도 분석)는 아직 안 함 | ⚠️ 부분 달성 |

**종합 평가**: 4개 KPI(F1 개선/t-test 유의성/파이프라인 재현성/데이터 규모) 중 3개는 완전히
달성했고, "어떤 요인이 왜 중요한지"는 다음 단계 과제로 남아있다. 개선하려면
`LogisticRegression.coef_`를 `OneHotEncoder`가 만든 피처 이름과 매칭해서 계수 크기순으로
보거나, `permutation_importance`로 피처 중요도를 뽑아보면 된다.

## 9. 배포

이번 과제 범위는 실제 서비스 배포가 아니라 "팀에게 결과를 공유하고 검증받는 것"이므로,
그 관점에서의 배포 방식은 다음과 같다.

- **코드·문서**: GitHub 저장소에 전체 커밋·push 완료 — 누구나 clone 후
  `pip install -r requirements.txt && python main.py`로 동일한 결과를 재현할 수 있다
- **모델**: `models/remote_work_model.pkl`을 `joblib.load()`로 불러오면 바로 예측에 재사용 가능
  (Pipeline 객체 안에 전처리까지 포함돼 있어 원본 컬럼만 있으면 추가 전처리 코드 없이 동작)
- **리포트**: `reports/report.md` + 차트 2종을 그대로 팀 공유·발표 자료로 활용

실제 프로덕션 배포까지 간다면 고려할 점(현재 범위 밖, 참고용):
- 모델을 FastAPI 등으로 감싸 예측 API화
- 신규 설문 데이터가 나올 때마다 파이프라인 재실행하는 스케줄링(예: PDF 12장의 `schedule`)
- 이미 붙여둔 `logging`(콘솔+`logs/pipeline.log`)을 운영 모니터링으로 확장
