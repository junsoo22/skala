"""인터랙티브 시각화(Plotly): 수치형 컬럼 상관관계 히트맵."""
from pathlib import Path

import pandas as pd
import plotly.express as px

NUMERIC_COLS = ["ConvertedCompYearly", "WorkExp", "JobSat"]


def run(df: pd.DataFrame, output_dir: Path) -> dict:
    """Plotly 인터랙티브 차트를 생성해 HTML로 저장한다.

    Args:
        df: data_prep.run()이 반환한 정제 데이터.
        output_dir: HTML을 저장할 디렉터리.

    Returns:
        dict: {"plotly_chart_path": str}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / "eda_plotly.html"

    corr = df[NUMERIC_COLS].corr()
    fig = px.imshow(corr, text_auto=".2f", title="수치형 컬럼 상관관계")
    fig.update_layout(xaxis_title="컬럼", yaxis_title="컬럼")
    fig.write_html(chart_path)

    return {"plotly_chart_path": str(chart_path)}
