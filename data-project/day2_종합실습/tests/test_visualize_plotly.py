"""visualize_plotly.run() 검증."""
from pathlib import Path

from src import visualize_plotly


def test_run_creates_html_with_korean_labels(sample_df, tmp_path):
    result = visualize_plotly.run(sample_df, tmp_path)

    chart_path = Path(result["plotly_chart_path"])
    assert chart_path.exists()
    assert chart_path.suffix == ".html"

    content = chart_path.read_text(encoding="utf-8")
    for korean_label in visualize_plotly.KOREAN_LABELS.values():
        escaped = "".join(f"\\u{ord(ch):04x}" for ch in korean_label)
        assert escaped in content
