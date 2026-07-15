"""
Practice 1 — 자료구조 집계 · 컴프리헨션 · 제너레이터
=======================================================

Python_Practice1_Data.json(sales 거래 데이터, 100건)을 기반으로 아래 4개 과제를 수행한다.

1) 리스트/딕셔너리 컴프리헨션
   - amount >= 1000인 거래만 필터링
   - 지역별 총매출 dict를 컴프리헨션으로 계산 (top3 포함)
2) Counter + defaultdict
   - Counter로 지역별 거래 건수 집계
   - defaultdict로 카테고리별 amount 리스트 집계
3) 제너레이터 — 메모리 비교
   - amount > 1000인 행만 yield하는 제너레이터 작성
   - 동일 조건 리스트 버전과 sys.getsizeof 비교
4) 종합 — 월별 카테고리 매출 집계
   - (month, category) 조합별 총매출 dict 완성 (defaultdict + 컴프리헨션)

변경 이력
---------
- 2026-07-15  최초 작성: 1)~4) 문항 구현, assert 기반 자체 검증 추가
- 2026-07-15  코드 간결성 반영(정렬 결과 재사용), 오류/예외 처리 추가,
              함수 단위로 분리하고 docstring 추가
"""

import os
import sys
from collections import Counter, defaultdict

DATA_PATH = os.path.join(os.path.dirname(__file__), "Python_Practice1_Data.json")


def load_sales(path):
    """
    데이터 파일을 읽어 sales(거래 리스트)를 반환한다.
    파일은 실제로는 JSON이 아니라 `sales = [...]` 형태의 파이썬 코드이므로 exec로 실행한다.
    파일이 없거나 형식이 깨진 경우 원인을 알 수 있는 메시지와 함께 프로그램을 종료한다.
    """
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        raise SystemExit(f"[오류] 데이터 파일을 찾을 수 없습니다: {path}")
    except OSError as e:
        raise SystemExit(f"[오류] 데이터 파일을 읽는 중 문제가 발생했습니다: {e}")

    namespace = {}
    try:
        exec(source, namespace)
    except SyntaxError as e:
        raise SystemExit(f"[오류] 데이터 파일 형식이 올바르지 않습니다: {e}")

    if "sales" not in namespace:
        raise SystemExit("[오류] 데이터 파일에 'sales' 변수가 정의되어 있지 않습니다.")

    return namespace["sales"]


sales = load_sales(DATA_PATH)

# ------------------------------------------------------------------
# 1) 리스트/딕셔너리 컴프리헨션
# ------------------------------------------------------------------
# ① amount >= 1000인 거래만 필터링
high_value = [row for row in sales if row["amount"] >= 1000]

# ② 지역별 총매출 dict를 컴프리헨션으로 계산
regions = {row["region"] for row in high_value}
region_total = {
    r: sum(row["amount"] for row in high_value if row["region"] == r)
    for r in regions
}

# 금액 내림차순 정렬 결과를 한 번만 계산해 재사용한다.
# (top3 계산 / 출력 / assert 검증에서 매번 다시 정렬하는 반복을 제거 — 코드 간결성)
region_total_sorted = sorted(region_total.items(), key=lambda x: -x[1])
top3 = region_total_sorted[:3]

# ------------------------------------------------------------------
# 2) Counter + defaultdict
# ------------------------------------------------------------------
# ① Counter로 지역별 거래 건수 (sales 전체 기준)
region_counter = Counter(row["region"] for row in sales)

# ② defaultdict로 카테고리별 amount 리스트
category_amounts = defaultdict(list)
for row in sales:
    category_amounts[row["category"]].append(row["amount"])

# ------------------------------------------------------------------
# 3) 제너레이터 — 메모리 비교
# ------------------------------------------------------------------
def high_value_gen():
    """amount > 1000인 거래만 하나씩 생성(yield)하는 제너레이터.
    리스트와 달리 전체 결과를 미리 메모리에 만들지 않는다."""
    for row in sales:
        if row["amount"] > 1000:
            yield row


high_value_list = [row for row in sales if row["amount"] > 1000]
high_value_generator = high_value_gen()

# 제너레이터를 list로 변환(소비)하지 않은 원본 상태로 크기를 비교해야 의미가 있다.
list_size = sys.getsizeof(high_value_list)
gen_size = sys.getsizeof(high_value_generator)

# ------------------------------------------------------------------
# 4) 종합 — 월별 카테고리 매출 집계 (컴프리헨션 + defaultdict)
# ------------------------------------------------------------------
# ① defaultdict로 (month, category) 조합별 amount 리스트 그룹핑
month_category_amounts = defaultdict(list)
for row in sales:
    month_category_amounts[(row["month"], row["category"])].append(row["amount"])

# ② 컴프리헨션으로 그룹별 총매출 dict 완성
month_category_total = {
    key: sum(amounts) for key, amounts in month_category_amounts.items()
}

# 금액 내림차순 정렬 결과를 한 번만 계산해 재사용한다 (top3 계산 + 출력 겸용).
month_category_total_sorted = sorted(month_category_total.items(), key=lambda x: -x[1])
month_category_top3 = month_category_total_sorted[:3]


def main():
    """실습 1의 결과를 출력하고, 각 문항의 체크포인트를 assert로 자체 검증한다."""
    print(f"전체 거래 수: {len(sales)}")
    print(f"필터링된 거래 수 (amount >= 1000): {len(high_value)}")
    print("지역별 총매출:")
    for r, total in region_total_sorted:
        print(f"  {r}: {total:,}")

    print("\nTop3 지역 (금액 내림차순):")
    for rank, (r, total) in enumerate(top3, start=1):
        print(f"  {rank}위. {r}: {total:,}")

    try:
        assert region_total["서울"] == sum(
            row["amount"] for row in sales if row["region"] == "서울" and row["amount"] >= 1000
        ), "서울 지역 총매출이 원본 데이터 기준 합계와 다릅니다."
        assert top3 == region_total_sorted[:3], "top3 정렬 결과가 일관되지 않습니다."
        print("\nassert 통과: 서울 지역 총매출 및 top3 정렬 검증 완료")
    except KeyError:
        print("\n[오류] region_total에 '서울' 키가 존재하지 않습니다. 데이터 구성을 확인하세요.")

    print("\n지역별 거래 건수 (Counter.most_common()):")
    for r, cnt in region_counter.most_common():
        print(f"  {r}: {cnt}건")

    print("\n카테고리별 amount 리스트 (defaultdict):")
    for cat, amounts in category_amounts.items():
        print(f"  {cat}: {amounts}")

    assert sum(region_counter.values()) == len(sales), "지역별 거래 건수 합계가 전체 건수와 다릅니다."
    assert region_counter["서울"] == sum(1 for r in sales if r["region"] == "서울"), "서울 거래 건수가 일치하지 않습니다."
    assert sum(len(v) for v in category_amounts.values()) == len(sales), "카테고리별 리스트 길이 합계가 전체 건수와 다릅니다."
    print("\nassert 통과: 지역별 거래 건수 및 카테고리별 amount 리스트 검증 완료")

    print(f"\n리스트 버전 크기 (list): {list_size:,} bytes")
    print(f"제너레이터 버전 크기 (generator): {gen_size:,} bytes")
    print(f"차이: 리스트가 제너레이터보다 {list_size - gen_size:,} bytes 더 큼")

    assert gen_size < list_size, "제너레이터가 리스트보다 크거나 같습니다."
    print("\nassert 통과: generator sys.getsizeof < list 확인 완료")

    # 제너레이터는 한 번 소비하면 재사용 불가 — 검증용으로 새 제너레이터를 만들어 소비
    consumed = list(high_value_gen())
    assert consumed == high_value_list, "제너레이터가 산출한 값이 리스트 버전과 다릅니다."
    print("assert 통과: 제너레이터가 산출하는 값이 리스트 버전과 동일함 확인 완료")

    print("\n월별 카테고리 매출 집계:")
    for (month, category), total in sorted(month_category_total.items()):
        print(f"  {month} / {category}: {total:,}")

    print("\nTop3 월·카테고리 조합 (금액 내림차순):")
    for rank, ((month, category), total) in enumerate(month_category_top3, start=1):
        print(f"  {rank}위. {month} / {category}: {total:,}")

    try:
        assert month_category_total[("2024-01", "전자")] == sum(
            row["amount"] for row in sales if row["month"] == "2024-01" and row["category"] == "전자"
        ), "2024-01/전자 조합의 합계가 일치하지 않습니다."
        assert sum(month_category_total.values()) == sum(row["amount"] for row in sales), "전체 합계가 일치하지 않습니다."
        assert month_category_top3 == month_category_total_sorted[:3], "top3 정렬 결과가 일관되지 않습니다."
        assert month_category_top3[0][1] == max(month_category_total.values()), "1위 금액이 전체 최댓값과 다릅니다."
        print("\nassert 통과: 월별 카테고리 매출 집계 및 top3 정렬 검증 완료")
    except KeyError:
        print("\n[오류] month_category_total에 ('2024-01', '전자') 조합이 존재하지 않습니다.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        raise SystemExit(f"[검증 실패] {e}")
