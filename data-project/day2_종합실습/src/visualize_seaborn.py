"""정적 시각화(Seaborn): 연봉 분포(RemoteWork별 hue) + 근무형태별 실무경력 박스플롯."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # GUI 없는 환경에서도 안전하게 파일로 저장하기 위한 비대화형 백엔드

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

plt.rcParams["font.family"] = "AppleGothic"  # 한글 라벨 깨짐 방지
plt.rcParams["axes.unicode_minus"] = False


def run(df: pd.DataFrame, output_dir: Path) -> dict:
    """Seaborn 정적 차트를 생성해 PNG로 저장한다.

    Args:
        df: data_prep.run()이 반환한 정제 데이터.
        output_dir: PNG를 저장할 디렉터리.

    Returns:
        dict: {"seaborn_chart_path": str}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / "eda_seaborn.png"

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    try:
        plot_df = df[df["ConvertedCompYearly"].notna() & (df["ConvertedCompYearly"] < 500_000)]
        sns.histplot(data=plot_df, x="ConvertedCompYearly", hue="RemoteWork", kde=True, ax=axes[0])
        axes[0].set_title("연봉 분포 (근무형태별)")
        axes[0].set_xlabel("연봉 (ConvertedCompYearly, USD)")
        axes[0].set_ylabel("응답자 수")

        sns.boxplot(data=df, x="RemoteWork", y="WorkExp", ax=axes[1])
        axes[1].set_title("근무형태별 실무경력 분포")
        axes[1].set_xlabel("근무형태 (RemoteWork)")
        axes[1].set_ylabel("실무경력 (WorkExp, 년)")
        axes[1].tick_params(axis="x", rotation=15)

        plt.tight_layout()
        plt.savefig(chart_path, dpi=120, bbox_inches="tight")
    finally:
        plt.close(fig)

    return {"seaborn_chart_path": str(chart_path)}
