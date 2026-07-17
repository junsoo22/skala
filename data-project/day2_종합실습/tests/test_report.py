"""report.run() 검증 - 실제 templates/report_template.md.j2를 사용해 렌더링한다."""
from pathlib import Path

from src import report


def _dummy_context():
    return {
        "eda_summary": {
            "raw_shape": (65437, 25), "selected_shape": (52622, 25),
            "missing_ratio": {}, "target_missing_removed": 10631, "duplicates_removed": 2184,
        },
        "pandas_polars_compare": {
            "pandas_shape": (65437, 114), "polars_shape": (65437, 114),
            "pandas_load_seconds": 1.0, "polars_load_seconds": 0.14,
        },
        "describe": "dummy describe",
        "corr": "dummy corr",
        "ttest": {"t": 5.9, "p": 3.7e-09, "interpretation": "p < 0.05: 유의미함"},
        "seaborn_chart_path": "reports/eda_seaborn.png",
        "plotly_chart_path": "reports/eda_plotly.html",
        "model_comparison": {"LogisticRegression": {"accuracy": 0.71, "f1": 0.58}},
        "best_model_name": "LogisticRegression",
        "model_path": "models/remote_work_model.pkl",
        "feature_importance": {
            "stable_features": [{"feature": "num__YearsCode", "score": 0.12}],
            "reliable_categorical_features": [
                {"feature": "cat__Country_Ukraine", "score": 2.08, "n": 1853}
            ],
        },
    }


def test_run_creates_report_with_expected_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "OUTPUT_PATH", tmp_path / "report.md")

    path = report.run(_dummy_context())

    content = Path(path).read_text(encoding="utf-8")
    assert "## 1. 데이터 개요" in content
    assert "## 5. ML Pipeline 결과" in content
    assert "### 5.1 피처 중요도" in content
    assert "LogisticRegression" in content
    assert "num__YearsCode" in content
