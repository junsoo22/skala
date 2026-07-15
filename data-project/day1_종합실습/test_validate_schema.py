"""
Day 1 종합 실습 — ⑤ 테스트 (pytest)
=======================================

validate_schema.py의 Pydantic v2 스키마(WeatherRecord, CountryInfo, IpInfo)와
필드 추출/검증 파이프라인이 정상값은 통과시키고 비정상값은 거부하는지 확인한다.
"""

import pytest
from pydantic import ValidationError

from validate_schema import (
    CountryInfo,
    IpInfo,
    WeatherRecord,
    extract_weather_rows,
    validate_many,
    validate_one,
)


# ------------------------------------------------------------------
# WeatherRecord
# ------------------------------------------------------------------
def test_weather_record_valid():
    r = WeatherRecord(time="2024-01-01T00:00", temperature_2m=25.1, precipitation_probability=40)
    assert r.temperature_2m == 25.1
    assert r.precipitation_probability == 40


def test_weather_record_rejects_out_of_range_probability():
    with pytest.raises(ValidationError):
        WeatherRecord(time="2024-01-01T00:00", temperature_2m=25.1, precipitation_probability=150)


def test_weather_record_rejects_non_numeric_temperature():
    with pytest.raises(ValidationError):
        WeatherRecord(time="2024-01-01T00:00", temperature_2m="abc", precipitation_probability=40)


def test_weather_record_rejects_empty_time():
    with pytest.raises(ValidationError):
        WeatherRecord(time="", temperature_2m=25.1, precipitation_probability=40)


# ------------------------------------------------------------------
# CountryInfo
# ------------------------------------------------------------------
def test_country_info_valid():
    c = CountryInfo(name="Korea", capital="Seoul", region="Asia", population=51_000_000, area=100_210)
    assert c.capital == "Seoul"


def test_country_info_rejects_non_positive_population():
    with pytest.raises(ValidationError):
        CountryInfo(name="Korea", capital="Seoul", region="Asia", population=0, area=100_210)


def test_country_info_rejects_empty_name():
    with pytest.raises(ValidationError):
        CountryInfo(name="", capital="Seoul", region="Asia", population=1000, area=100)


# ------------------------------------------------------------------
# IpInfo
# ------------------------------------------------------------------
def test_ip_info_valid():
    ip = IpInfo(query="8.8.8.8", country="United States", city="Ashburn", lat=39.03, lon=-77.5, status="success")
    assert ip.status == "success"


def test_ip_info_rejects_invalid_status_literal():
    with pytest.raises(ValidationError):
        IpInfo(query="8.8.8.8", country="US", city="Ashburn", lat=39.03, lon=-77.5, status="unknown")


def test_ip_info_rejects_latitude_out_of_range():
    with pytest.raises(ValidationError):
        IpInfo(query="8.8.8.8", country="US", city="Ashburn", lat=200, lon=-77.5, status="success")


# ------------------------------------------------------------------
# 필드 추출 + 검증 파이프라인
# ------------------------------------------------------------------
def test_extract_weather_rows_zips_arrays_correctly():
    fake_response = {
        "hourly": {
            "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
            "temperature_2m": [10.0, 11.0],
            "precipitation_probability": [0, 20],
        }
    }
    rows = extract_weather_rows(fake_response)
    assert rows == [
        {"time": "2024-01-01T00:00", "temperature_2m": 10.0, "precipitation_probability": 0},
        {"time": "2024-01-01T01:00", "temperature_2m": 11.0, "precipitation_probability": 20},
    ]


def test_validate_many_splits_valid_and_errors():
    rows = [
        {"time": "t1", "temperature_2m": 20.0, "precipitation_probability": 10},  # 정상
        {"time": "t2", "temperature_2m": 20.0, "precipitation_probability": 999},  # 범위 초과
    ]
    valid, errors = validate_many(WeatherRecord, rows)
    assert len(valid) == 1
    assert len(errors) == 1
    assert errors[0]["row"] == 1


def test_validate_one_returns_none_and_error_message_on_failure():
    model, error = validate_one(
        CountryInfo, {"name": "", "capital": "Seoul", "region": "Asia", "population": 1, "area": 1}
    )
    assert model is None
    assert error is not None
    assert "name" in error
