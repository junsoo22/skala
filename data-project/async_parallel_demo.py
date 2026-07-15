"""
6. 비동기와 병렬 처리 입문 — 실습 데모
=======================================

PDF p.57~62 내용을 직접 체감할 수 있도록 4개 데모로 구성했다.
각 데모는 독립적으로 실행되며, 실제 걸린 시간을 print로 비교해 개념을 눈으로 확인한다.

1) GIL 데모 — CPU bound에는 threading이 안 통하고, I/O bound에는 통한다
2) asyncio 데모 — I/O bound 작업을 동시에 실행하면 대기 시간이 겹쳐져서 빨라진다
3) multiprocessing 데모 — CPU bound 작업을 여러 프로세스로 나누면 진짜 병렬로 빨라진다
4) 성능 측정 데모 — timeit / cProfile / sys.getsizeof
"""

import asyncio
import cProfile
import io
import os
import pstats
import sys
import threading
import time
import timeit
from concurrent.futures import ProcessPoolExecutor


def _print_header(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ------------------------------------------------------------------
# 1) GIL 데모 — threading이 CPU bound에는 안 통하고 I/O bound에는 통한다
# ------------------------------------------------------------------
def cpu_task(n=5_000_000):
    """순수 계산(CPU bound) 작업. GIL 때문에 threading으로 나눠도 안 빨라진다."""
    return sum(i * i for i in range(n))


def io_task(sec=0.5):
    """대기(I/O bound) 작업. 대기 중 GIL이 풀려서 threading 효과가 있다."""
    time.sleep(sec)


def demo_gil():
    _print_header("1) GIL 데모: CPU bound vs I/O bound에서 threading 효과 비교")

    # CPU bound: 순차 실행 vs 스레드 2개
    start = time.perf_counter()
    cpu_task()
    cpu_task()
    cpu_seq = time.perf_counter() - start

    start = time.perf_counter()
    t1 = threading.Thread(target=cpu_task)
    t2 = threading.Thread(target=cpu_task)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    cpu_threaded = time.perf_counter() - start

    print(f"[CPU bound] 순차 실행: {cpu_seq:.3f}초")
    print(f"[CPU bound] 스레드 2개: {cpu_threaded:.3f}초  <- GIL 때문에 거의 안 빨라짐 (오히려 오버헤드로 더 걸릴 수도 있음)")

    # I/O bound: 순차 실행 vs 스레드 2개
    start = time.perf_counter()
    io_task()
    io_task()
    io_seq = time.perf_counter() - start

    start = time.perf_counter()
    t1 = threading.Thread(target=io_task)
    t2 = threading.Thread(target=io_task)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    io_threaded = time.perf_counter() - start

    print(f"[I/O bound] 순차 실행: {io_seq:.3f}초")
    print(f"[I/O bound] 스레드 2개: {io_threaded:.3f}초  <- 대기 중 GIL이 풀려서 절반 가까이 줄어듦")


# ------------------------------------------------------------------
# 2) asyncio 데모 — I/O bound 작업을 동시에 실행
# ------------------------------------------------------------------
async def fake_api_call(call_id, delay=0.5):
    """실제 네트워크 없이 API 호출의 '대기 시간'만 재현한 가짜 호출."""
    await asyncio.sleep(delay)
    return {"id": call_id, "status": "ok"}


async def fetch_sequential(n):
    results = []
    for i in range(n):
        results.append(await fake_api_call(i))
    return results


async def fetch_concurrent(n):
    tasks = [fake_api_call(i) for i in range(n)]
    return await asyncio.gather(*tasks)


def demo_asyncio():
    _print_header("2) asyncio 데모: I/O bound 작업 10개를 순차 vs 동시 실행")

    start = time.perf_counter()
    asyncio.run(fetch_sequential(10))
    seq_time = time.perf_counter() - start
    print(f"순차 실행 (await를 하나씩): {seq_time:.2f}초  (10 x 0.5초가 그대로 더해짐)")

    start = time.perf_counter()
    asyncio.run(fetch_concurrent(10))
    concurrent_time = time.perf_counter() - start
    print(f"동시 실행 (asyncio.gather): {concurrent_time:.2f}초  (대기 시간이 겹쳐져서 거의 0.5초로 끝남)")

    try:
        import httpx  # noqa: F401
        print("\n[참고] httpx가 설치돼 있어 실제 API로도 테스트 가능합니다 (이 데모는 네트워크 없이도 동작하도록 asyncio.sleep으로 대체함).")
    except ImportError:
        print("\n[참고] httpx 미설치. 실제 API를 호출하려면 `pip install httpx` 후 client.get(url) 패턴을 사용하면 됨.")


# ------------------------------------------------------------------
# 3) multiprocessing 데모 — CPU bound 작업을 여러 프로세스로 병렬 처리
# ------------------------------------------------------------------
def heavy_calc(n):
    """CPU를 실제로 쓰는 계산. 프로세스별로 별도 GIL을 가지므로 진짜 병렬로 실행된다."""
    return sum(i * i for i in range(n))


def demo_multiprocessing():
    _print_header("3) multiprocessing 데모: CPU bound 작업을 순차 vs 여러 프로세스로 처리")

    n_cores = os.cpu_count()
    chunks = [3_000_000] * n_cores
    print(f"CPU 코어 수: {n_cores}, 작업 개수: {len(chunks)}개 (각 {chunks[0]:,}까지 제곱합)")

    start = time.perf_counter()
    [heavy_calc(n) for n in chunks]
    seq_time = time.perf_counter() - start
    print(f"순차 실행: {seq_time:.2f}초")

    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=n_cores) as exe:
        list(exe.map(heavy_calc, chunks))
    parallel_time = time.perf_counter() - start
    print(f"ProcessPoolExecutor({n_cores}개 프로세스): {parallel_time:.2f}초  "
          f"(이론상 최대 {n_cores}배까지 빨라질 수 있음, 실제로는 프로세스 생성/데이터 전달 비용 때문에 그보다 적게 향상)")
    print(f"속도 향상: {seq_time / parallel_time:.1f}배")


# ------------------------------------------------------------------
# 4) 성능 측정 데모 — timeit / cProfile / sys.getsizeof
# ------------------------------------------------------------------
def slow_function():
    """cProfile로 병목을 찾아볼 일부러 느린 함수."""
    total = 0
    for _ in range(200_000):
        total += 1
    time.sleep(0.3)  # 이 부분이 압도적으로 오래 걸리도록 설계
    return total


def demo_profiling():
    _print_header("4) 성능 측정 데모: timeit / cProfile / sys.getsizeof")

    # timeit: 짧은 코드 조각의 정밀한 반복 측정
    t = timeit.timeit(
        "''.join(my_list)",
        setup="my_list=['a']*1000",
        number=10000,
    )
    print(f"[timeit] ''.join(list) x 10000회 평균: {t:.4f}초")

    # cProfile: 함수 내부 어디가 느린지 분석
    print("\n[cProfile] slow_function() 프로파일링 결과 (누적시간 기준 상위 5개):")
    profiler = cProfile.Profile()
    profiler.enable()
    slow_function()
    profiler.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(5)
    print(stream.getvalue())

    # sys.getsizeof: 리스트 vs 제너레이터 메모리 비교
    lst = list(range(10_000))
    gen = (x for x in range(10_000))
    print(f"[sys.getsizeof] list(range(10000)): {sys.getsizeof(lst):,} bytes")
    print(f"[sys.getsizeof] generator(range(10000)): {sys.getsizeof(gen):,} bytes")


if __name__ == "__main__":
    demo_gil()
    demo_asyncio()
    demo_multiprocessing()
    demo_profiling()
