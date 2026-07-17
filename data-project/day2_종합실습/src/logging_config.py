"""파이프라인 전체에서 공용으로 쓰는 logging 설정.

print() 대신 logging 모듈을 쓰면 심각도(INFO/WARNING/ERROR)를 구분할 수 있고, 콘솔 출력과
별개로 logs/pipeline.log 파일에 실행 기록이 남아 나중에 재현·디버깅할 때 참고할 수 있다.
"""
import logging
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "pipeline.log"


def setup_logging() -> logging.Logger:
    """콘솔 + logs/pipeline.log 파일에 동시에 기록하는 핸들러를 루트 로거에 등록한다."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger("day2_pipeline")
