"""Day 2 종합실습 파이프라인 진입점."""
from pathlib import Path

from src import data_prep, stats_analysis, visualize_seaborn, visualize_plotly, ml_pipeline, report
from src.logging_config import setup_logging

REPORTS_DIR = Path("reports")
logger = setup_logging()


def section(title):
    # 로그에 구분선을 남겨 단계 경계를 표시한다.
    logger.info("=" * 60)
    logger.info("[%s]", title)
    logger.info("=" * 60)


def main():
    section("1. 데이터 준비 (Pandas/Polars 로딩 비교 + 정제)")
    prep = data_prep.run()
    logger.info("정제 후 shape: %s", prep["df"].shape)
    logger.info("Pandas vs Polars: %s", prep["pandas_polars_compare"])
    logger.info("EDA 요약: %s", prep["eda_summary"])

    section("2. 통계분석 (기술통계/상관계수/t-test)")
    stats = stats_analysis.run(prep["df"])
    logger.info("t-test: %s", stats["ttest"])

    section("3. 시각화 (Seaborn 정적 차트)")
    seaborn_result = visualize_seaborn.run(prep["df"], output_dir=REPORTS_DIR)
    logger.info("저장: %s", seaborn_result["seaborn_chart_path"])

    section("4. 시각화 (Plotly 인터랙티브 차트)")
    plotly_result = visualize_plotly.run(prep["df"], output_dir=REPORTS_DIR)
    logger.info("저장: %s", plotly_result["plotly_chart_path"])

    section("5. ML Pipeline (LogisticRegression vs RandomForest)")
    ml = ml_pipeline.run(prep["df"])
    logger.info("모델 비교: %s", ml["model_comparison"])
    logger.info("최종 선택: %s -> %s", ml["best_model_name"], ml["model_path"])

    section("6. 리포트 자동 생성")
    report_path = report.run({**prep, **stats, **seaborn_result, **plotly_result, **ml})
    logger.info("리포트 생성 완료: %s", report_path)


if __name__ == "__main__":
    main()
