"""
Practice 2 — 파일 I/O, 예외 처리, Pydantic 검증 파이프라인
=======================================================

Python_Practice2_Data.json(실제 거래 데이터, 100건)을 읽어 Pydantic v2 스키마로
검증하고, 결과를 CSV/JSON으로 저장 후 재로딩까지 확인한다.

1) 예외 처리 + 파일 읽기 — safe_load_json() / safe_load_csv()
   - 파일 없으면 None 반환 + logger.error, 성공 시 dict 리스트 반환 + logger.info
   - finally에서 "로딩 종료" 출력
2) Pydantic v2 스키마 정의 — SalesRecord
   - region · month: 비어있으면 안 됨 / amount: 0 초과 / category: 없어도 됨
3) 검증 파이프라인 (valid / errors 분리)
   - raw_data를 순회하며 SalesRecord로 변환, 성공 -> valid, 실패 -> errors({row, error})
4) 결과 파일 저장 + 재로딩 확인
   - valid는 CSV로, errors는 JSON으로 저장하고 다시 읽어 건수 검증

데이터/스키마 관련 참고사항
---------------------------
- PDF p.46 Checkpoint 원문은 필드명을 "date"로 표기하지만, 실제 Python_Practice2_Data.json은
  region/category/amount/month 4개 필드만 가지고 있어 date가 없다. 실제 데이터에 맞춰
  SalesRecord의 필수 문자열 필드를 date 대신 month로 정의했다.
- Python_Practice2_Data.json은 100건 전부 정상값이라(Python_Practice1_Data.json과 동일한
  성격의 데이터) validate_records를 돌려도 errors가 0건이다. 이는 실제 데이터를 있는 그대로
  검증한 결과이며, 이전 버전처럼 "valid 4건/errors 3건"이 나오도록 인위적으로 맞춘 픽스처를
  쓰지 않는다. main()의 assert는 전부 "valid+errors==전체 건수", "재로딩 건수==저장 건수"처럼
  데이터 구성과 무관하게 항상 성립해야 하는 불변식만 사용한다(매직넘버 없음).
- 다만 이 실제 데이터만으로는 ValidationError 예외 경로가 한 번도 실행되지 않으므로,
  그 경로가 실제로 동작하는지 증명하기 위해 demo_validation_error()에서 직접 정의한
  소규모 결함 데이터로 별도 검증한다.

변경 이력
---------
- 2026-07-15  최초 작성: sales_test.csv 픽스처 기반 1)~4) 문항 구현
- 2026-07-15  Python_Practice2_Data.json(실제 데이터)으로 전환, 하드코딩된 valid/errors
              개수 assert 제거, 스키마 필드를 date -> month로 수정
"""

import csv
import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / "Python_Practice2_Data.json"
VALID_CSV = BASE_DIR / "sales_valid.csv"
ERRORS_JSON = BASE_DIR / "sales_errors.json"

logger = logging.getLogger("practice2")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)


# ------------------------------------------------------------------
# 1) 예외 처리 + 파일 읽기
# ------------------------------------------------------------------
def safe_load_json(path):
    """
    JSON 파일(리스트 of dict)을 읽어 그대로 반환한다.
    파일이 없으면 None을 반환하고 logger.error로 원인을 남긴다.
    성공/실패와 무관하게 finally에서 로딩 종료를 기록한다.
    """
    try:
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
    except FileNotFoundError:
        logger.error(f"파일을 찾을 수 없습니다: {path}")
        return None
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"파일을 읽는 중 문제가 발생했습니다: {path} ({e})")
        return None
    else:
        logger.info(f"파일 로딩 성공: {path} ({len(rows)}건)")
        return rows
    finally:
        logger.info("로딩 종료")


def safe_load_csv(path):
    """
    CSV 파일을 읽어 dict 리스트로 반환한다. (재로딩 검증 및 결과 파일 확인용)
    파일이 없으면 None을 반환하고 logger.error로 원인을 남긴다.
    성공/실패와 무관하게 finally에서 로딩 종료를 기록한다.
    """
    try:
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        logger.error(f"파일을 찾을 수 없습니다: {path}")
        return None
    except OSError as e:
        logger.error(f"파일을 읽는 중 문제가 발생했습니다: {path} ({e})")
        return None
    else:
        logger.info(f"파일 로딩 성공: {path} ({len(rows)}건)")
        return rows
    finally:
        logger.info("로딩 종료")


# ------------------------------------------------------------------
# 2) Pydantic v2 스키마 정의
# ------------------------------------------------------------------
class SalesRecord(BaseModel):
    """거래 1건에 대한 검증 스키마. region·month는 필수(공백 불가), amount는 양수여야 한다."""

    region: str = Field(..., min_length=1, description="비어있으면 안 됨")
    month: str = Field(..., min_length=1, description="비어있으면 안 됨")
    amount: float = Field(..., gt=0, description="0보다 커야 함")
    category: Optional[str] = Field(default=None, description="없어도 됨")


# ------------------------------------------------------------------
# 3) 검증 파이프라인 (valid / errors 분리)
# ------------------------------------------------------------------
def validate_records(raw_data):
    """raw_data의 각 행을 SalesRecord로 검증해 (valid, errors) 튜플로 분리한다."""
    valid, errors = [], []
    for i, row in enumerate(raw_data):
        try:
            valid.append(SalesRecord(**row))
        except ValidationError as e:
            logger.warning(f"검증 실패 (row {i}): {e}")
            errors.append({"row": i, "error": str(e)})
    return valid, errors


# ------------------------------------------------------------------
# 4) 결과 파일 저장 + 재로딩 확인
# ------------------------------------------------------------------
def save_results(valid, errors, valid_csv_path, errors_json_path):
    """valid 레코드는 CSV로, errors는 JSON(한글 보존)으로 저장한다."""
    fieldnames = list(SalesRecord.model_fields.keys())
    try:
        with open(valid_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in valid:
                writer.writerow(record.model_dump())

        errors_json_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        logger.error(f"결과 저장 중 문제가 발생했습니다: {e}")
        raise


def demo_validation_error():
    """
    Python_Practice2_Data.json은 전부 정상값이라 ValidationError 경로가 실행될 일이 없다.
    이 함수는 직접 정의한 소규모 결함 데이터로 그 경로가 실제로 동작하는지 확인한다.
    """
    sample = [
        {"region": "서울", "month": "2024-01", "amount": 1000, "category": "전자"},  # 정상
        {"region": "부산", "month": "2024-02", "amount": 800, "category": "의류"},  # 정상
        {"region": "대구", "month": "2024-03", "amount": 1200, "category": None},  # 정상 (category 없어도 됨)
        {"region": "인천", "month": "2024-04", "amount": 500, "category": "식품"},  # 정상
        {"region": "", "month": "2024-01", "amount": 700, "category": "전자"},  # region 비어있음
        {"region": "광주", "month": "", "amount": 650, "category": "의류"},  # month 비어있음
        {"region": "대전", "month": "2024-02", "amount": -1, "category": "식품"},  # amount <= 0
    ]
    valid, errors = validate_records(sample)
    assert len(valid) == 4 and len(errors) == 3, "demo_validation_error 샘플 구성과 결과가 다릅니다."
    print(f"[데모] 정의한 결함 3건이 그대로 errors에 잡힘 (valid={len(valid)}, errors={len(errors)})")
    for e in errors:
        print(f"  [데모 errors] row {e['row']}: {e['error'].splitlines()[0]}")
    return valid, errors


def main():
    """전체 파이프라인을 실행하고, 데이터 구성과 무관하게 항상 성립해야 하는 불변식을 assert로 검증한다."""
    raw_data = safe_load_json(INPUT_JSON)
    assert raw_data is not None, "Python_Practice2_Data.json 로딩에 실패했습니다."
    print(f"원본 행 수: {len(raw_data)}")

    missing = safe_load_json(BASE_DIR / "존재하지_않는_파일.json")
    assert missing is None, "존재하지 않는 파일은 None을 반환해야 합니다."
    print("assert 통과: 존재하지 않는 파일 -> None 반환 확인")

    print("\n--- ValidationError 경로 동작 확인 (직접 정의한 소규모 데모) ---")
    demo_validation_error()

    print("\n--- 실제 데이터(Python_Practice2_Data.json) 검증 ---")
    valid, errors = validate_records(raw_data)
    print(f"valid: {len(valid)}건, errors: {len(errors)}건")
    for e in errors:
        print(f"  [errors] row {e['row']}: {e['error'].splitlines()[0]}")

    # 데이터 구성(개수)에 의존하지 않는 불변식만 검증한다.
    assert len(valid) + len(errors) == len(raw_data), "valid+errors 합이 원본 건수와 다릅니다."
    print("assert 통과: valid + errors == 원본 건수 확인")

    save_results(valid, errors, VALID_CSV, ERRORS_JSON)

    reloaded = safe_load_csv(VALID_CSV)
    assert reloaded is not None and len(reloaded) == len(valid), "재로딩 건수가 저장한 valid 건수와 다릅니다."
    print(f"assert 통과: 재로딩 후 len(reloaded)==len(valid)({len(valid)}) 확인 "
          f"(저장 파일: {VALID_CSV.name}, {ERRORS_JSON.name})")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        raise SystemExit(f"[검증 실패] {e}")
