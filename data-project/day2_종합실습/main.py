"""Day 2 종합실습 파이프라인 진입점."""
from pathlib import Path

from src import data_prep, stats_analysis, visualize_seaborn, visualize_plotly, ml_pipeline, report

REPORTS_DIR = Path("reports")


def main():
    prep = data_prep.run()
    stats = stats_analysis.run(prep["df"])
    seaborn_result = visualize_seaborn.run(prep["df"], output_dir=REPORTS_DIR)
    plotly_result = visualize_plotly.run(prep["df"], output_dir=REPORTS_DIR)
    ml = ml_pipeline.run(prep["df"])
    report_path = report.run({**prep, **stats, **seaborn_result, **plotly_result, **ml})
    print(f"리포트 생성 완료: {report_path}")


if __name__ == "__main__":
    main()
