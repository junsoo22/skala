"""
Day 1 종합 실습 — ③ 스키마 검증
=======================================

김준수_day종합실습.py(② 비동기 수집)가 가져온 3개 API 응답에서 필요한 필드를 추출해
Pydantic v2 모델로 타입·범위를 검증한다.

- open_meteo: hourly.time / temperature_2m / precipitation_probability 배열을
  시간대별 레코드(WeatherRecord)로 변환해 각각 검증한다.
- country_info: 국가 정보 중 이름·수도·인구·면적·권역을 CountryInfo로 검증한다.
- ip_api: 조회한 IP의 국가·도시·위경도를 IpInfo로 검증한다.

성공한 레코드는 valid로, 실패한 레코드는 errors({field, error})로 분리한다.
"""

import asyncio
from typing import List, Literal

from pydantic import BaseModel, Field, ValidationError

from collect_async import fetch_all


# ------------------------------------------------------------------
# Pydantic v2 스키마
# ------------------------------------------------------------------
class WeatherRecord(BaseModel):
    """시간대별 기온·강수확률 1건. 기온은 상식적 범위, 강수확률은 0~100%로 제한한다."""

    time: str = Field(..., min_length=1)
    temperature_2m: float = Field(..., ge=-50, le=60, description="섭씨 -50~60도 범위")
    precipitation_probability: int = Field(..., ge=0, le=100, description="0~100%")


class CountryInfo(BaseModel):
    """국가 정보. 이름·수도·권역은 필수, 인구·면적은 양수여야 한다."""

    name: str = Field(..., min_length=1)
    capital: str = Field(..., min_length=1)
    region: str = Field(..., min_length=1)
    population: int = Field(..., gt=0)
    area: float = Field(..., gt=0)


class IpInfo(BaseModel):
    """IP 조회 결과. 위도/경도는 지구 좌표 범위, status는 성공/실패만 허용한다."""

    query: str = Field(..., min_length=1, description="조회한 IP")
    country: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    status: Literal["success", "fail"]


# ------------------------------------------------------------------
# 필드 추출 + 검증 파이프라인
# ------------------------------------------------------------------
def extract_weather_rows(open_meteo_data) -> List[dict]:
    """open_meteo 응답의 hourly 배열들을 시간대별 dict 리스트로 변환한다."""
    hourly = open_meteo_data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    precs = hourly.get("precipitation_probability", [])
    return [
        {"time": t, "temperature_2m": temp, "precipitation_probability": prec}
        for t, temp, prec in zip(times, temps, precs)
    ]


def validate_many(model_cls, rows):
    """rows(dict 리스트)를 model_cls로 하나씩 검증해 (valid, errors) 튜플로 분리한다."""
    valid, errors = [], []
    for i, row in enumerate(rows):
        try:
            valid.append(model_cls(**row))
        except ValidationError as e:
            errors.append({"row": i, "error": str(e)})
    return valid, errors


def validate_one(model_cls, data):
    """data(dict) 하나를 model_cls로 검증한다. 성공하면 모델 인스턴스, 실패하면 None과 에러 문자열."""
    try:
        return model_cls(**data), None
    except ValidationError as e:
        return None, str(e)


def main():
    results = asyncio.run(fetch_all())

    print("=== open_meteo: WeatherRecord 검증 ===")
    weather_rows = extract_weather_rows(results["open_meteo"])
    weather_valid, weather_errors = validate_many(WeatherRecord, weather_rows)
    print(f"전체 {len(weather_rows)}건 중 valid {len(weather_valid)}건, errors {len(weather_errors)}건")
    print(f"  예시(첫 3건): {[r.model_dump() for r in weather_valid[:3]]}")
    for e in weather_errors[:3]:
        print(f"  [errors] row {e['row']}: {e['error'].splitlines()[0]}")

    print("\n=== country_info: CountryInfo 검증 ===")
    country_valid, country_error = validate_one(CountryInfo, results["country_info"])
    if country_valid:
        print(f"  검증 성공: {country_valid.model_dump()}")
    else:
        print(f"  [errors] {country_error}")

    print("\n=== ip_api: IpInfo 검증 ===")
    ip_valid, ip_error = validate_one(IpInfo, results["ip_api"])
    if ip_valid:
        print(f"  검증 성공: {ip_valid.model_dump()}")
    else:
        print(f"  [errors] {ip_error}")

    # 타입 오류가 실제로 잡히는지 데모로 확인 (요구사항: "타입 오류 시 예외 처리 포함")
    print("\n=== 데모: 일부러 잘못된 데이터로 예외 처리 확인 ===")
    bad_weather = {"time": "2024-01-01T00:00", "temperature_2m": "abc", "precipitation_probability": 150}
    _, err = validate_one(WeatherRecord, bad_weather)
    assert err is not None, "타입/범위 오류가 있는 데이터는 반드시 실패해야 합니다."
    print("  temperature_2m='abc'(타입 오류) + precipitation_probability=150(범위 초과) -> 검증 실패 확인")
    print(f"  {err}")


if __name__ == "__main__":
    main()
