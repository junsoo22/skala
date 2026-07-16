"""Day 2 종합실습 파이프라인 진입점."""
from pathlib import Path

from src import data_prep, stats_analysis, visualize_seaborn, visualize_plotly, ml_pipeline, report

REPORTS_DIR = Path("reports")


def section(title):
    # 콘솔 출력에 구분선을 그려 단계 경계를 표시한다.
    print("\n" + "=" * 60)
    print(f"[{title}]")
    print("=" * 60)


def main():
    section("1. 데이터 준비 (Pandas/Polars 로딩 비교 + 정제)")
    prep = data_prep.run()
    print(f">> 정제 후 shape: {prep['df'].shape}")
    print(f">> Pandas vs Polars: {prep['pandas_polars_compare']}")
    print(f">> EDA 요약: {prep['eda_summary']}")

    section("2. 통계분석 (기술통계/상관계수/t-test)")
    stats = stats_analysis.run(prep["df"])
    print(f">> t-test: {stats['ttest']}")

    section("3. 시각화 (Seaborn 정적 차트)")
    seaborn_result = visualize_seaborn.run(prep["df"], output_dir=REPORTS_DIR)
    print(f">> 저장: {seaborn_result['seaborn_chart_path']}")

    section("4. 시각화 (Plotly 인터랙티브 차트)")
    plotly_result = visualize_plotly.run(prep["df"], output_dir=REPORTS_DIR)
    print(f">> 저장: {plotly_result['plotly_chart_path']}")

    section("5. ML Pipeline (LogisticRegression vs RandomForest)")
    ml = ml_pipeline.run(prep["df"])
    print(f">> 모델 비교: {ml['model_comparison']}")
    print(f">> 최종 선택: {ml['best_model_name']} -> {ml['model_path']}")

    section("6. 리포트 자동 생성")
    report_path = report.run({**prep, **stats, **seaborn_result, **plotly_result, **ml})
    print(f">> 리포트 생성 완료: {report_path}")


if __name__ == "__main__":
    main()
