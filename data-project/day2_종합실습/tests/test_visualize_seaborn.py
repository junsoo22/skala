"""visualize_seaborn.run() 검증."""
from pathlib import Path

from src import visualize_seaborn


def test_run_creates_png(sample_df, tmp_path):
    result = visualize_seaborn.run(sample_df, tmp_path)

    chart_path = Path(result["seaborn_chart_path"])
    assert chart_path.exists()
    assert chart_path.suffix == ".png"
    assert chart_path.stat().st_size > 0
