import time

import pandas as pd  # Pandas 불러오기


def section(title):
    print("\n" + "=" * 60)
    print(f"[{title}]")
    print("=" * 60)


# 딕셔너리로 표를 만든다(키=열 이름, 값=열 데이터)
section("1. 딕셔너리로 만든 간단한 DataFrame")
df = pd.DataFrame({'이름': ['A', 'B', 'C'], '점수': [90, 70, 85]})
print(df)

print("\n>> 점수 평균:", df['점수'].mean())  # '점수' 열의 평균 → 결과: 81.666...

print("\n>> 점수 80 이상인 행:")
high = df[df['점수'] >= 80]
print(high)

print("\n>> DataFrame 크기 (행수, 열수):", df.shape)


section("2. sales.csv 불러오기")
df = pd.read_csv('sales.csv')
print(df.head())


section("3. 기초 확인")
print(">> 행수, 열수:", df.shape)

print("\n>> 타입, 결측, 메모리 (info):")
df.info()

print("\n>> 수치 기술 통계 (describe):")
print(df.describe())

print("\n>> 범주형 포함 기술 통계 (describe include='all'):")
print(df.describe(include='all'))


section("4. 타입 변환")
print(">> 변환 전 dtypes:")
print(df.dtypes)

df['date'] = pd.to_datetime(df['date'])
df['region'] = df['region'].astype('category')

print("\n>> 변환 후 dtypes:")
print(df.dtypes)


section("5. 컬럼 선택")
print(">> df['amount'] (Series):")
print(df['amount'])

print("\n>> df[['region', 'amount']] (DataFrame):")
print(df[['region', 'amount']])

print("\n>> df.loc[df['amount'] > 1000] (조건 필터):")
print(df.loc[df['amount'] > 1000])


section("6. 결측치 확인")
print(">> 컬럼별 결측치 개수:")
print(df.isna().sum())

print("\n>> 컬럼별 결측치 비율(%):")
print(df.isna().sum() / len(df) * 100)


section("7. 결측치 처리")
df['amount'] = df['amount'].fillna(df['amount'].median())
df['category'] = df['category'].fillna(df['category'].mode()[0])
df = df.dropna(subset=['date', 'amount'])

print(">> 처리 후 결측치 개수:")
print(df.isna().sum())


section("8. IQR 이상치 탐지 및 제거")
Q1 = df['amount'].quantile(0.25)
Q3 = df['amount'].quantile(0.75)
IQR = Q3 - Q1
lo, hi = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
print(f">> 정상 범위: {lo:.1f} ~ {hi:.1f}")

df_clean = df[df['amount'].between(lo, hi)]
print(f'>> 이상치 {(~df["amount"].between(lo, hi)).sum()}건 제거')
print(f'>> 제거 전: {len(df)}행 -> 제거 후: {len(df_clean)}행')


section("9. 벡터화 vs apply - 문자열 변환")
category_map = {'전자': 'electronics', '의류': 'clothing', '식품': 'food'}
df['category_en'] = df['category'].map(category_map)

# 느린 방법: apply (행마다 파이썬 함수 호출)
df['category_upper_apply'] = df['category_en'].apply(lambda x: x.upper())
# 빠른 방법: 벡터화 (C로 구현된 문자열 연산을 열 전체에 한 번에 적용)
df['category_upper_vec'] = df['category_en'].str.upper()

print(">> apply(lambda x: x.upper()) 결과:")
print(df[['category_en', 'category_upper_apply']].head())

print("\n>> str.upper() (벡터화) 결과:")
print(df[['category_en', 'category_upper_vec']].head())

print("\n>> 두 결과가 동일한가?", (df['category_upper_apply'] == df['category_upper_vec']).all())


section("10. 날짜 처리 - dt 접근자")
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['weekday'] = df['date'].dt.day_name()

print(df[['date', 'year', 'month', 'weekday']].head())


section("11. 속도 비교: apply vs 벡터화 (대량 데이터 기준)")
big = pd.Series(['electronics', 'clothing', 'food'] * 200_000)  # 60만 행

start = time.perf_counter()
big.apply(lambda x: x.upper())
apply_time = time.perf_counter() - start

start = time.perf_counter()
big.str.upper()
vec_time = time.perf_counter() - start

print(f">> apply 소요 시간      : {apply_time:.4f}초")
print(f">> str.upper() 소요 시간: {vec_time:.4f}초")
print(f">> 벡터화가 약 {apply_time / vec_time:.1f}배 빠름")


section("12. Polars - Eager vs Lazy")
import polars as pl

# Eager (즉시 실행): 호출 시점에 바로 연산 수행
df_pl = pl.read_csv('sales.csv')
eager_result = df_pl.filter(pl.col('amount') > 0)
print(">> Eager 결과 (amount > 0):")
print(eager_result.head())

# Lazy (실행 계획만 구성, collect() 시점에 최적화 후 한 번에 실행)
lazy_result = (
    pl.scan_csv('sales.csv', schema_overrides={'amount': pl.Float64})
    .filter(pl.col('region') == '서울')
    .filter(pl.col('amount') > 0)
    .group_by('category')
    .agg([
        pl.col('amount').sum().alias('total'),
        pl.len().alias('cnt'),
    ])
    .sort('total', descending=True)
    .collect()  # 여기서 실제 실행
)
print("\n>> Lazy 결과 (서울 지역, amount>0 -> category별 집계):")
print(lazy_result)


section("13. Pandas -> Polars 문법 비교")
print(">> Pandas: df[df['amount']>0][['region','amount']]")
print(df[df['amount'] > 0][['region', 'amount']].head())

print("\n>> Polars: df.filter(pl.col('amount')>0).select(['region','amount'])")
print(df_pl.filter(pl.col('amount') > 0).select(['region', 'amount']).head())

print("\n>> 컬럼 추가 - with_columns (pandas의 assign에 대응):")
print(df_pl.with_columns((pl.col('amount') * 1.1).alias('adjusted')).head())

print("\n>> 문자열/날짜 처리 (region 대문자화, date 문자열 -> Date 타입):")
print(
    df_pl.with_columns(
        pl.col('region').str.to_uppercase(),
        pl.col('date').str.to_date('%Y-%m-%d', strict=False),
    ).head()
)


section("14. Polars <-> Pandas 상호 변환")
df_pd_converted = df_pl.to_pandas()
df_pl_converted = pl.from_pandas(df_pd_converted)
print(">> polars.to_pandas() 결과 타입:", type(df_pd_converted))
print(">> pandas -> pl.from_pandas() 결과 타입:", type(df_pl_converted))


section("15. DuckDB - 파일에 직접 SQL")
import duckdb

result = duckdb.sql("""
    SELECT region,
           SUM(amount) AS total,
           AVG(amount) AS avg,
           COUNT(*) AS cnt
    FROM 'sales.csv'
    WHERE amount > 0
    GROUP BY region
    ORDER BY total DESC
""").df()
print(result)


section("16. DuckDB - 여러 파일 JOIN")
df_pl.write_parquet('sales.parquet')  # sales.csv -> sales.parquet 변환 (JOIN 예시용)

join_result = duckdb.sql("""
    SELECT s.region, s.amount, s.category, c.tier
    FROM 'sales.parquet' s
    JOIN 'customers.csv' c ON s.region = c.region
    ORDER BY s.amount DESC
""").df()
print(join_result.head(10))