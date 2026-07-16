"""통계분석: 기술통계, 상관계수, t-test(RemoteWork에 따른 연봉 평균 차이)."""
import pandas as pd
from scipy import stats

NUMERIC_COLS = ["ConvertedCompYearly", "WorkExp", "JobSat", "YearsCode"]


def run(df: pd.DataFrame) -> dict:
    """통계분석을 수행한다.

    Args:
        df: data_prep.run()이 반환한 정제 데이터.

    Returns:
        dict: {
            "describe": pandas.DataFrame,  # NUMERIC_COLS의 df.describe() 결과
            "corr": pandas.DataFrame,      # NUMERIC_COLS 상관계수 행렬
            "ttest": dict,                 # {"t": float, "p": float, "interpretation": str}
        }
    """
    describe = df[NUMERIC_COLS].describe()
    corr = df[NUMERIC_COLS].corr()

    remote = df.loc[df["RemoteWork"] == "Remote", "ConvertedCompYearly"].dropna()
    inperson = df.loc[df["RemoteWork"] == "In-person", "ConvertedCompYearly"].dropna()

    try:
        t_stat, p_value = stats.ttest_ind(remote, inperson, equal_var=False)
        if p_value < 0.05:
            interpretation = (
                f"p < 0.05: Remote(n={len(remote)})와 In-person(n={len(inperson)}) 그룹의 "
                "연봉 평균 차이는 통계적으로 유의미함"
            )
        else:
            interpretation = (
                f"p >= 0.05: Remote(n={len(remote)})와 In-person(n={len(inperson)}) 그룹의 "
                "연봉 평균 차이는 통계적으로 유의미하지 않음 (우연일 수 있음)"
            )
        ttest = {"t": round(float(t_stat), 4), "p": float(p_value), "interpretation": interpretation}
    except ValueError as e:
        ttest = {"t": None, "p": None, "interpretation": f"t-test 실패: {e}"}

    return {"describe": describe, "corr": corr, "ttest": ttest}
