# 작성일 : 2026-07-16
# 작성자 : 김준수
# 설명 : 1) [실습 3] Pandas EDA · Polars Lazy · DuckDB SQL 비교 실습
#       2) 대상 데이터: sales_100k.csv (매출 원천 데이터)
#       3) 흐름: sales_100k.csv 로딩 → Pandas 기초 EDA(shape/info/describe/isnull)
#          → IQR 이상치 제거 → region·category별 named aggregation 집계
#          → Polars Lazy API(scan_csv→filter→group_by→agg→sort→collect)로 동일 집계
#          → DuckDB SQL로 동일 집계 + 세 도구 결과 일치 검증 + timeit 성능 비교
#
# 변경일 : 2026-07-16 최초 작성: 기본 EDA, 타입 변환, 컬럼 선택, IQR 이상치 제거
#        2026-07-16 named aggregation groupby, Polars Lazy 동일 집계 추가
#        2026-07-16 DuckDB SQL 집계, 3개 도구 결과 일치 검증, timeit 성능 비교 추가
# --------------------------------------------------------------------------------------------

import timeit

import duckdb
import pandas as pd
import polars as pl

SALES_PATH = 'sales_100k.csv'


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


def section(title):
    # 콘솔 출력에 구분선을 그려 섹션 경계를 표시한다.
    print("\n" + "=" * 60)
    print(f"[{title}]")
    print("=" * 60)


df = load_sales_data(SALES_PATH)


section("1. 기본 EDA")
print(">> 행수, 열수:", df.shape)

print("\n>> 타입, 결측, 메모리 (info):")
df.info()

print("\n>> 수치 기술 통계 (describe):")
print(df.describe())

print("\n>> 범주형 포함 기술 통계 (describe include='all'):")
print(df.describe(include='all'))

print("\n>> 컬럼별 결측치 개수 (isnull):")
print(df.isnull().sum())

# region(1%)·category(0.8%) 결측치 처리 방안 검토 결과 (이번 실습에서는 미적용):
#   - dropna: 가장 간단하지만 이미 발생한 매출(amount)까지 집계에서 통째로 빠짐
#   - mode로 채우기: region/category는 매출이 아닌 그룹핑 키라서, 최빈값을 채우면
#     실제로는 알 수 없는 주문에 특정 지역/카테고리를 억지로 부여해 집계가 왜곡됨
#   - '미분류'로 채우기(권장): 매출은 보존하면서 결측을 숨기지 않고, pandas의
#     groupby(dropna 기본값) vs polars/duckdb(null도 그룹 유지) 간 결과 행수 차이도 해소됨
# → 실습 범위상 실제 처리는 하지 않고, groupby 시 pandas만 해당 행을 자동 제외함에 유의


section("2. IQR 이상치 탐지 및 제거")
Q1 = df['amount'].quantile(0.25)
Q3 = df['amount'].quantile(0.75)
IQR = Q3 - Q1
lo, hi = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
print(f">> 정상 범위: {lo:.1f} ~ {hi:.1f}")

df_clean = df[df['amount'].between(lo, hi)].copy()
print(f'>> 결측치/이상치 {(~df["amount"].between(lo, hi)).sum()}건 제거 (정상 범위 밖 또는 amount 결측)')
print(f'>> 제거 전: {len(df)}행 -> 제거 후: {len(df_clean)}행')


section("3. 타입 변환")
try:
    df_clean['order_date'] = pd.to_datetime(df_clean['order_date'])
    df_clean['region'] = df_clean['region'].astype('category')
    print(">> 변환 후 dtypes:")
    print(df_clean.dtypes)
except (ValueError, TypeError) as e:
    print(f">> 타입 변환 실패: {e}")


section("4. 컬럼 선택")
print(">> df_clean['amount'] (Series):")
print(df_clean['amount'])

print("\n>> df_clean[['region', 'amount']] (DataFrame):")
print(df_clean[['region', 'amount']])

print("\n>> df_clean.loc[df_clean['amount'] > 3000000] (조건 필터):")
print(df_clean.loc[df_clean['amount'] > 3_000_000])


section("5. Pandas groupby named aggregation (region x category)")
pandas_agg = (
    df_clean.groupby(['region', 'category'])
    .agg(total_amount=('amount', 'sum'), avg=('amount', 'mean'), cnt=('amount', 'count'))
    .reset_index()
    .sort_values(by='total_amount', ascending=False)
)
print(pandas_agg)


section("6. Polars Lazy API로 동일 집계")
polars_agg = (
    pl.scan_csv(SALES_PATH, schema_overrides={'amount': pl.Float64})
    .filter(pl.col('amount').is_between(lo, hi))
    .group_by(['region', 'category'])
    .agg([
        pl.col('amount').sum().alias('total_amount'),
        pl.col('amount').mean().alias('avg'),
        pl.len().alias('cnt'),
    ])
    .sort('total_amount', descending=True)
    .collect()  # 여기서 실제 실행
)
print(polars_agg)


section("7. DuckDB SQL + 세 도구 성능 비교")


def run_pandas_pipeline():
    # timeit 측정용: 로딩 -> IQR 필터 -> named aggregation 전체 파이프라인
    raw = pd.read_csv(SALES_PATH)
    clean = raw[raw['amount'].between(lo, hi)]
    return (
        clean.groupby(['region', 'category'])
        .agg(total_amount=('amount', 'sum'), avg=('amount', 'mean'), cnt=('amount', 'count'))
        .sort_values('total_amount', ascending=False)
    )


def run_polars_pipeline():
    # timeit 측정용: 6번과 동일한 Polars Lazy 파이프라인
    return (
        pl.scan_csv(SALES_PATH, schema_overrides={'amount': pl.Float64})
        .filter(pl.col('amount').is_between(lo, hi))
        .group_by(['region', 'category'])
        .agg([
            pl.col('amount').sum().alias('total_amount'),
            pl.col('amount').mean().alias('avg'),
            pl.len().alias('cnt'),
        ])
        .sort('total_amount', descending=True)
        .collect()
    )


def run_duckdb_pipeline():
    # timeit 측정용: DuckDB SQL로 파일을 직접 읽어 동일 집계
    return duckdb.sql(f"""
        SELECT region, category,
               SUM(amount) AS total_amount,
               AVG(amount) AS avg,
               COUNT(*) AS cnt
        FROM '{SALES_PATH}'
        WHERE amount BETWEEN {lo} AND {hi}
        GROUP BY region, category
        ORDER BY total_amount DESC
    """).df()


duckdb_agg = run_duckdb_pipeline()
print(">> DuckDB SQL 집계 결과 (상위 5행):")
print(duckdb_agg.head())

print("\n>> 세 도구 결과 일치 검증 (1위 total_amount 비교):")
try:
    top_pandas = pandas_agg.iloc[0]['total_amount']
    top_polars = polars_agg[0, 'total_amount']
    top_duckdb = duckdb_agg.iloc[0]['total_amount']
    assert abs(top_pandas - top_polars) < 1 and abs(top_pandas - top_duckdb) < 1
    print(f"   일치 (pandas={top_pandas:.1f}, polars={top_polars:.1f}, duckdb={top_duckdb:.1f})")
except AssertionError:
    print(f"   불일치! pandas={top_pandas:.1f}, polars={top_polars:.1f}, duckdb={top_duckdb:.1f}")

print("\n>> timeit 성능 비교 (동일 반복 횟수):")
NUMBER = 5
pandas_time = timeit.timeit(run_pandas_pipeline, number=NUMBER)
polars_time = timeit.timeit(run_polars_pipeline, number=NUMBER)
duckdb_time = timeit.timeit(run_duckdb_pipeline, number=NUMBER)

print(f"   Pandas : 총 {pandas_time:.3f}초 / 회당 {pandas_time / NUMBER:.3f}초")
print(f"   Polars : 총 {polars_time:.3f}초 / 회당 {polars_time / NUMBER:.3f}초")
print(f"   DuckDB : 총 {duckdb_time:.3f}초 / 회당 {duckdb_time / NUMBER:.3f}초")
print(
    f"   -> Polars가 Pandas 대비 약 {pandas_time / polars_time:.1f}배, "
    f"DuckDB가 약 {pandas_time / duckdb_time:.1f}배 빠름"
)
