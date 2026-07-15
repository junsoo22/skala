"""
Day 1 종합 실습 — ② 비동기 수집
=======================================

3개 API를 asyncio + httpx로 동시에 수집한다 (asyncio.gather() 활용).

API 구성 (PDF p.64 기준, RestCountries만 대체):
- Open-Meteo: 서울 3일 시간대별 기온·강수확률
- ip-api: IP(8.8.8.8) 기반 지역 정보
- RestCountries(v3.1)는 서비스가 v5로 개편되며 구버전 API가 폐지되어(2026-07-15 확인),
  같은 성격의 대체 API인 countries.dev(alpha/KR)로 교체했다.
"""

import asyncio
import time

import httpx

APIS = {
    "open_meteo": (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=37.5665&longitude=126.9780"
        "&hourly=temperature_2m,precipitation_probability"
        "&forecast_days=3&timezone=Asia/Seoul"
    ),
    "country_info": "https://countries.dev/alpha/KR",
    "ip_api": "http://ip-api.com/json/8.8.8.8",
}


async def fetch(client, name, url):
    """API 하나를 호출해 (이름, 결과) 튜플로 반환한다. 실패해도 다른 요청에 영향 없게 예외를 캡처한다."""
    try:
        r = await client.get(url, timeout=10)
        r.raise_for_status()
        return name, r.json()
    except Exception as e:
        return name, {"error": str(e)}


async def fetch_all():
    async with httpx.AsyncClient() as client:
        tasks = [fetch(client, name, url) for name, url in APIS.items()]
        results = await asyncio.gather(*tasks)
    return dict(results)


def main():
    start = time.perf_counter()
    results = asyncio.run(fetch_all())
    elapsed = time.perf_counter() - start

    print(f"3개 API 동시 수집 완료: {elapsed:.2f}초\n")
    for name, data in results.items():
        print(f"--- {name} ---")
        if "error" in data:
            print(f"  [실패] {data['error']}")
        else:
            print(f"  {str(data)[:200]}")
        print()


if __name__ == "__main__":
    main()
