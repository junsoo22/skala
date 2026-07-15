"""
Day 1 종합 실습 — ④ 저장 및 성능 비교
=======================================

validate_schema.py(③ 스키마 검증)를 통과한 데이터를 CSV와 Parquet 두 형식으로 저장하고,
PDF p.61이 제시한 성능 측정 도구로 쓰기/읽기 성능을 분석한다.

- timeit: 쓰기/읽기 각각을 여러 번 반복해 평균 시간을 정밀 측정 (1회 측정의 노이즈 제거)
- cProfile: 쓰기/읽기 파이프라인 전체를 프로파일링해 실제로 어느 함수가 시간을 많이 쓰는지 분석
- sys.getsizeof: 같은 데이터를 리스트(of dict)로 들고 있을 때와 DataFrame으로 들고 있을 때의
  메모리 크기를 비교
"""

import asyncio
import cProfile
import io
import pstats
import sys
import timeit
from pathlib import Path

import pandas as pd

from validate_schema import (
    CountryInfo,
    IpInfo,
    extract_weather_rows,
    fetch_all,
    validate_many,
    validate_one,
    WeatherRecord,
)

BASE_DIR = Path(__file__).parent
REPEAT = 20  # timeit 반복 횟수


def warmup_parquet_engine():
    """
    pyarrow 엔진은 프로세스에서 처음 Parquet을 읽거나 쓸 때 내부 초기화 비용이 크게 든다
    (실측: 콜드 스타트 8.9ms vs 웜 상태 0.2ms, 약 40배 차이). timeit으로 반복 측정해도 첫 1회가
    평균을 크게 끌어올리므로, 측정 전에 더미 데이터로 한 번 미리 태워둔다.
    """
    dummy = pd.DataFrame({"x": [1, 2, 3]})
    dummy_path = BASE_DIR / "_warmup.parquet"
    dummy.to_parquet(dummy_path, index=False)
    pd.read_parquet(dummy_path)
    dummy_path.unlink()


# ------------------------------------------------------------------
# timeit — 쓰기/읽기 평균 시간 정밀 측정
# ------------------------------------------------------------------
def measure_write(df, csv_path, parquet_path):
    csv_write = timeit.timeit(lambda: df.to_csv(csv_path, index=False), number=REPEAT) / REPEAT
    parquet_write = timeit.timeit(lambda: df.to_parquet(parquet_path, index=False), number=REPEAT) / REPEAT
    return csv_write, parquet_write


def measure_read(csv_path, parquet_path):
    csv_read = timeit.timeit(lambda: pd.read_csv(csv_path), number=REPEAT) / REPEAT
    parquet_read = timeit.timeit(lambda: pd.read_parquet(parquet_path), number=REPEAT) / REPEAT
    return csv_read, parquet_read


def report(label, df, csv_path, parquet_path):
    # 파일이 존재해야 읽기 측정이 가능하므로 먼저 한 번 저장해둔다.
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)

    csv_write, parquet_write = measure_write(df, csv_path, parquet_path)
    csv_read, parquet_read = measure_read(csv_path, parquet_path)

    csv_size = csv_path.stat().st_size
    parquet_size = parquet_path.stat().st_size

    print(f"\n=== {label} ({len(df)}행, timeit {REPEAT}회 평균) ===")
    print(f"  쓰기: CSV {csv_write*1000:.3f}ms  vs  Parquet {parquet_write*1000:.3f}ms")
    print(f"  읽기: CSV {csv_read*1000:.3f}ms  vs  Parquet {parquet_read*1000:.3f}ms")
    print(f"  파일 크기: CSV {csv_size:,}B  vs  Parquet {parquet_size:,}B")


# ------------------------------------------------------------------
# cProfile — 쓰기/읽기 파이프라인에서 실제로 무엇이 시간을 쓰는지 분석
# ------------------------------------------------------------------
def profile_pipeline(df, csv_path, parquet_path):
    def run_once():
        df.to_csv(csv_path, index=False)
        df.to_parquet(parquet_path, index=False)
        pd.read_csv(csv_path)
        pd.read_parquet(parquet_path)

    profiler = cProfile.Profile()
    profiler.enable()
    run_once()
    profiler.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(8)
    print(stream.getvalue())


# ------------------------------------------------------------------
# sys.getsizeof — 같은 데이터를 리스트 vs DataFrame으로 들고 있을 때 메모리 비교
# ------------------------------------------------------------------
def compare_memory(weather_rows, weather_df):
    list_size = sys.getsizeof(weather_rows)
    df_size = sys.getsizeof(weather_df)
    print(f"\n[sys.getsizeof] weather_rows (list of dict, {len(weather_rows)}건): {list_size:,} bytes")
    print(f"[sys.getsizeof] weather_df (pandas DataFrame): {df_size:,} bytes")
    print("  (list는 dict 객체들의 포인터만 세고 dict 내부 값은 shallow하게 안 잡히는 반면, "
          "DataFrame은 실제 컬럼 데이터를 연속 메모리 블록에 들고 있어 계측값의 성격이 다르다.)")


def main():
    warmup_parquet_engine()
    results = asyncio.run(fetch_all())

    weather_rows = extract_weather_rows(results["open_meteo"])
    weather_valid, _ = validate_many(WeatherRecord, weather_rows)
    weather_df = pd.DataFrame([r.model_dump() for r in weather_valid])

    country_valid, _ = validate_one(CountryInfo, results["country_info"])
    country_df = pd.DataFrame([country_valid.model_dump()])

    ip_valid, _ = validate_one(IpInfo, results["ip_api"])
    ip_df = pd.DataFrame([ip_valid.model_dump()])

    report("weather (open_meteo)", weather_df,
           BASE_DIR / "weather.csv", BASE_DIR / "weather.parquet")
    report("country_info", country_df,
           BASE_DIR / "country_info.csv", BASE_DIR / "country_info.parquet")
    report("ip_info", ip_df,
           BASE_DIR / "ip_info.csv", BASE_DIR / "ip_info.parquet")

    print("\n=== cProfile: weather 저장/읽기 1회 사이클 프로파일링 (누적시간 상위 8개) ===")
    profile_pipeline(weather_df, BASE_DIR / "weather.csv", BASE_DIR / "weather.parquet")

    compare_memory(weather_rows, weather_df)

    print("참고: 행 수가 적으면(수십~수백 건) 파일 오픈/파싱 오버헤드가 지배적이라 "
          "CSV와 Parquet 차이가 크지 않거나 역전될 수 있다. Parquet의 이점(컬럼형 압축, "
          "빠른 읽기)은 수만~수백만 행 규모에서 뚜렷해진다.")


if __name__ == "__main__":
    main()
