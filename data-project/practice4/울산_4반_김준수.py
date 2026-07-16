# [실습 4] 시각화 4종 · 통계 검정 · sklearn Pipeline 실습 (실습 3 연계)
#
# 작성일 : 2026-07-16
# 작성자 : 김준수
# 설명 : 1) 대상 데이터: sales_100k.csv (실습 3과 동일 원천 데이터)
#       2) 1번 항목: 히스토그램+KDE / 박스플롯 / 월별 라인 / 상관 히트맵을
#          2x2 서브플롯(fig, axes) 하나에 구성해 PNG로 저장
#       3) 2번 항목: 서울 vs 부산 평균 매출 차이 t-test, region x category 독립성 카이제곱 검정
#       4) 3번 항목: ColumnTransformer + Pipeline(Ridge)로 amount 예측 모델 구성,
#          학습/평가 후 joblib으로 저장 및 재로딩 검증
#       5) 4번 항목: region_category_agg(지역·카테고리별 총매출)로 Plotly Express
#          인터랙티브 막대 차트를 만들고 HTML로 저장
#
# 변경일 : 2026-07-16 최초 작성 - sales_100k.csv 로딩/정제(실습 3과 동일 IQR) + EDA 시각화 4종 구현
#        2026-07-16 t-test(서울 vs 부산), 카이제곱(region x category) 통계 검정 추가
#        2026-07-16 실습3의 region x category named aggregation 코드를 재사용해 카이제곱
#                    분할표를 구성하도록 변경 (연계 Point 반영, pd.crosstab 재계산 제거)
#        2026-07-16 sklearn Pipeline(ColumnTransformer+Ridge) 학습/평가/저장/재로딩 추가
#        2026-07-16 Plotly Express 막대 차트(지역·카테고리별 총매출) HTML 저장 추가
#        2026-07-16 체크포인트 점검: Pipeline에 predict() 명시 호출 추가 (fit-predict-score 순서 명확화)
#        2026-07-16 Ridge(L2) vs Lasso(L1) 비교 후 테스트 R2가 더 높은 모델을 저장하도록 확장
#
# --------------------------------------------------------------------------------------------

import matplotlib

matplotlib.use('Agg')  # GUI 없는 환경에서도 안전하게 파일로 저장하기 위한 비대화형 백엔드

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns
from scipy import stats
from scipy.stats import chi2_contingency
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.base import clone
from sklearn.linear_model import Lasso, Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

plt.rcParams['font.family'] = 'AppleGothic'  # 한글 라벨 깨짐 방지
plt.rcParams['axes.unicode_minus'] = False   # 마이너스 기호 깨짐 방지

SALES_PATH = 'sales_100k.csv'
FIG_PATH = 'practice4_eda_4charts.png'
MODEL_PATH = 'sales_amount_pipeline.pkl'
CHART_HTML_PATH = 'region_category_bar.html'


class DataLoadError(Exception):
    # 파일 없음/빈 파일 등 데이터 로딩 실패를 하나의 예외로 통일해 상위로 알린다.
    pass


def load_sales_data(path):
    # sales_100k.csv를 안전하게 읽는다. 파일이 없거나 비어 있으면 DataLoadError를 발생시킨다.
    try:
        data = pd.read_csv(path)
    except FileNotFoundError as e:
        raise DataLoadError(f"'{path}' 파일을 찾을 수 없습니다.") from e
    if data.empty:
        raise DataLoadError(f"'{path}' 파일에 데이터가 없습니다.")
    return data


def clean_by_iqr(data, column):
    # 실습 3과 동일한 IQR 방식으로 이상치/결측을 제거한 사본을 반환한다.
    Q1, Q3 = data[column].quantile(0.25), data[column].quantile(0.75)
    IQR = Q3 - Q1
    lo, hi = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
    return data[data[column].between(lo, hi)].copy()


def section(title):
    # 콘솔 출력에 구분선을 그려 섹션 경계를 표시한다.
    print("\n" + "=" * 60)
    print(f"[{title}]")
    print("=" * 60)


df = load_sales_data(SALES_PATH)
df_clean = clean_by_iqr(df, 'amount')
df_clean['order_date'] = pd.to_datetime(df_clean['order_date'])
print(f">> 실습 3과 동일 IQR 정제: {len(df)}행 -> {len(df_clean)}행")


section("1. EDA 시각화 4종 (2x2 서브플롯)")

fig = None
try:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (1) 히스토그램 + KDE - amount 분포
    sns.histplot(data=df_clean, x='amount', kde=True, ax=axes[0, 0], color='steelblue')
    axes[0, 0].set_title('매출(amount) 분포 - 히스토그램 + KDE')

    # (2) 박스플롯 - region별 amount 분포
    sns.boxplot(data=df_clean, x='region', y='amount', ax=axes[0, 1])
    axes[0, 1].set_title('지역별 매출 분포 - 박스플롯')
    axes[0, 1].tick_params(axis='x', rotation=45)

    # (3) 월별 라인 차트 - 월별 총매출 추이
    monthly = df_clean.set_index('order_date')['amount'].resample('MS').sum()
    axes[1, 0].plot(monthly.index, monthly.values, marker='o', color='teal')
    axes[1, 0].set_title('월별 총매출 추이 - 라인 차트')
    axes[1, 0].tick_params(axis='x', rotation=45)

    # (4) 상관 히트맵 - 수치형 컬럼 간 상관관계
    numeric_cols = ['quantity', 'unit_price', 'customer_age', 'amount']
    corr = df_clean[numeric_cols].corr()
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f', ax=axes[1, 1])
    axes[1, 1].set_title('수치형 컬럼 상관관계 - 히트맵')

    plt.tight_layout()
    plt.savefig(FIG_PATH, dpi=150, bbox_inches='tight')
    print(f">> 4종 차트를 하나의 Figure로 저장했습니다: {FIG_PATH}")
except Exception as e:
    print(f">> 시각화 생성 실패: {e}")
finally:
    if fig is not None:
        plt.close(fig)


section("2. 통계 검정 - t-test + 카이제곱")

# 실습 3에서 사용한 region x category named aggregation 코드를 그대로 가져와 재사용한다.
# (연계 Point: region·category groupby 결과 -> 카이제곱 분할표 기반 변수로 활용)
region_category_agg = (
    df_clean.groupby(['region', 'category'])
    .agg(total_amount=('amount', 'sum'), avg=('amount', 'mean'), cnt=('amount', 'count'))
    .reset_index()
    .sort_values(by='total_amount', ascending=False)
)
print(">> 실습 3 재사용: region x category named aggregation 결과")
print(region_category_agg)

# (1) t-test: 서울 vs 부산 평균 매출 차이
# H0: 서울과 부산의 평균 매출에 차이가 없다 / H1: 차이가 있다
try:
    group_seoul = df_clean.loc[df_clean['region'] == '서울', 'amount']
    group_busan = df_clean.loc[df_clean['region'] == '부산', 'amount']
    t_stat, t_p = stats.ttest_ind(group_seoul, group_busan)
    print(f">> t-test (서울 n={len(group_seoul)} vs 부산 n={len(group_busan)}): t={t_stat:.3f}, p={t_p:.4f}")
    if t_p < 0.05:
        print("   -> p < 0.05: 서울과 부산의 평균 매출 차이는 통계적으로 유의미함")
    else:
        print("   -> p >= 0.05: 서울과 부산의 평균 매출 차이는 통계적으로 유의미하지 않음 (우연일 수 있음)")
except ValueError as e:
    print(f">> t-test 실패: {e}")

# (2) 카이제곱: region x category 독립성 검정
# H0: region과 category는 서로 독립이다 / H1: 서로 연관이 있다 (독립이 아니다)
# 분할표는 위 region_category_agg의 cnt를 피벗해서 만든다 (원본 재집계 X, 결과 재사용).
try:
    contingency = region_category_agg.pivot(index='region', columns='category', values='cnt').fillna(0)
    chi2, chi_p, dof, _ = chi2_contingency(contingency)
    print(f"\n>> 카이제곱 검정 (region x category, dof={dof}): chi2={chi2:.3f}, p={chi_p:.4f}")
    if chi_p < 0.05:
        print("   -> p < 0.05: region과 category는 서로 독립이 아님 (연관 있음)")
    else:
        print("   -> p >= 0.05: region과 category는 서로 독립 (연관 없음)")
except ValueError as e:
    print(f">> 카이제곱 검정 실패: {e}")


section("3. sklearn Pipeline 구성 + 저장")

NUM_COLS = ['quantity', 'unit_price', 'customer_age']
CAT_COLS = ['region', 'category', 'payment_method', 'customer_gender']
TARGET_COL = 'amount'

try:
    X = df_clean[NUM_COLS + CAT_COLS]
    y = df_clean[TARGET_COL]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 수치형: 결측 중앙값 대체 -> 표준화
    num_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
    ])
    # 범주형: 결측을 'missing' 범주로 대체 -> 원-핫 인코딩
    cat_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore')),
    ])
    preproc = ColumnTransformer([
        ('num', num_pipeline, NUM_COLS),
        ('cat', cat_pipeline, CAT_COLS),
    ])

    # 체크포인트는 "전처리 + 모델 1개 이상"만 요구하지만, 정규화 방식(L2 vs L1)에 따라
    # 이 데이터에서 실제로 성능 차이가 나는지 궁금해서 Ridge와 Lasso를 같은 전처리로
    # 나란히 학습시켜 비교하고, 테스트 R2가 더 높은 쪽을 최종 모델로 저장하기로 했다.
    # (preproc는 candidates 루프마다 clone()으로 새로 복제해서 서로 다른 Pipeline이
    #  같은 ColumnTransformer 인스턴스를 공유해 재학습(fit)으로 덮어쓰는 것을 방지한다.)
    candidates = {
        'Ridge (L2)': Ridge(alpha=1.0),
        'Lasso (L1)': Lasso(alpha=1.0),
    }

    print(f">> 학습 데이터: train {len(X_train)}행 / test {len(X_test)}행")

    results = {}
    for name, regressor in candidates.items():
        candidate_model = Pipeline([
            ('prep', clone(preproc)),
            ('reg', regressor),
        ])
        candidate_model.fit(X_train, y_train)
        y_pred = candidate_model.predict(X_test)
        r2 = r2_score(y_test, y_pred)
        results[name] = (candidate_model, r2)
        print(f">> {name} 테스트 R2: {r2:.4f}")

    best_name, (model, r2) = max(results.items(), key=lambda item: item[1][1])
    print(f">> 최종 선택: {best_name} (R2={r2:.4f}이 더 높아 저장 대상으로 선택)")

    y_pred = model.predict(X_test)
    print(">> 예측 예시 (실제 vs 예측, 5건):")
    for actual, predicted in zip(y_test.head(5), y_pred[:5]):
        print(f"   실제 {actual:,.0f} / 예측 {predicted:,.0f}")

    joblib.dump(model, MODEL_PATH)
    print(f">> 모델 저장: {MODEL_PATH}")

    loaded_model = joblib.load(MODEL_PATH)
    reloaded_r2 = loaded_model.score(X_test, y_test)
    match = "일치" if abs(r2 - reloaded_r2) < 1e-9 else "불일치"
    print(f">> 재로딩한 모델 R2: {reloaded_r2:.4f} (원본과 {match})")
except Exception as e:
    print(f">> Pipeline 학습/저장 실패: {e}")


section("4. Plotly 인터랙티브 차트 저장")

# 지역·카테고리별 총매출: 위 2번에서 재사용한 region_category_agg를 그대로 이용
try:
    fig_bar = px.bar(
        region_category_agg,
        x='region',
        y='total_amount',
        color='category',
        barmode='group',
        title='지역·카테고리별 총매출',
        labels={'region': '지역', 'total_amount': '총매출', 'category': '카테고리'},
    )
    fig_bar.write_html(CHART_HTML_PATH)
    print(f">> Plotly 인터랙티브 막대 차트 저장: {CHART_HTML_PATH}")
except Exception as e:
    print(f">> Plotly 차트 생성 실패: {e}")
