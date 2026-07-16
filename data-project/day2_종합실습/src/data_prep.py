"""데이터 준비: Stack Overflow Developer Survey 2024 다운로드, Pandas/Polars 로딩 비교,
결측치·중복 처리, 기본 EDA.

컬럼 선정 방침: 114개 전체 컬럼 중 타깃(RemoteWork)과 관련 있고 값이 깨끗한 컬럼만 골랐다.
자유서술형·조건부 스킵 컬럼은 결측이 극단적으로 많아 제외했지만, 다중선택 컬럼인
LanguageHaveWorkedWith는 상위 10개 언어를 이진 플래그(lang_*)로 풀어내 피처로 포함시켜
분석 대상을 넓혔다.

결측치 처리 방침: 타깃(RemoteWork)이 없는 행은 분석 자체가 불가능하므로 여기서 제거한다.
언어 플래그는 응답이 없으면 "모름"이 아니라 "해당 언어를 쓰지 않음(0)"으로 채운다. 그 외
컬럼(ConvertedCompYearly·WorkExp·JobSat·YearsCode·Industry·ICorPM 등)의 결측은 일부러
남겨둔다 — 결측 비율이 커서(최대 55%대) 여기서 한 번에 지우면 표본이 절반 이하로 줄어들고,
통계 분석은 컬럼 단위로 각자 필요한 곳에서 dropna를, ML은 SimpleImputer로 대체값을 채우는
게 더 타당하기 때문이다. eda_summary의 missing_ratio로 결측 현황은 투명하게 남긴다.
"""
import time
import urllib.request
from pathlib import Path

import pandas as pd
import polars as pl

SURVEY_URL = (
    "https://github.com/StackExchange/Survey/raw/refs/heads/main/"
    "packages/archive/2024/results.csv"
)
RAW_DATA_PATH = Path("data/raw/results.csv")

USE_COLUMNS = [
    "RemoteWork", "Age", "Employment", "EdLevel", "DevType", "OrgSize", "Country",
    "MainBranch", "Industry", "ICorPM", "AISent",
    "ConvertedCompYearly", "WorkExp", "JobSat", "YearsCode",
]

LANGUAGE_COLUMN = "LanguageHaveWorkedWith"
# 응답 빈도 상위 10개 언어(explode 후 value_counts 기준)를 이진 피처로 풀어낸다.
LANG_COLUMN_MAP = {
    "JavaScript": "lang_javascript",
    "HTML/CSS": "lang_html_css",
    "Python": "lang_python",
    "SQL": "lang_sql",
    "TypeScript": "lang_typescript",
    "Bash/Shell (all shells)": "lang_bash_shell",
    "Java": "lang_java",
    "C#": "lang_csharp",
    "C++": "lang_cpp",
    "C": "lang_c",
}
YEARS_CODE_TEXT_MAP = {"Less than 1 year": "0", "More than 50 years": "51"}


def download_if_missing(url: str, dest: Path) -> Path:
    """dest 파일이 없으면 url에서 다운로드해 캐시하고, 최종 경로를 반환한다."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        urllib.request.urlretrieve(url, dest)
    return dest


def _clean_years_code(series: pd.Series) -> pd.Series:
    """'Less than 1 year'/'More than 50 years' 같은 텍스트를 숫자로 바꾸고 나머지는 그대로 변환한다."""
    return pd.to_numeric(series.replace(YEARS_CODE_TEXT_MAP), errors="coerce")


def _add_language_flags(df: pd.DataFrame, raw_language_column: pd.Series) -> pd.DataFrame:
    """세미콜론으로 구분된 다중선택 언어 컬럼에서 상위 10개 언어를 이진 컬럼(lang_*)으로 추가한다."""
    tokens = raw_language_column.fillna("").str.split(";")
    for lang, col_name in LANG_COLUMN_MAP.items():
        df[col_name] = tokens.apply(lambda langs, lang=lang: int(lang in langs))
    return df


def run() -> dict:
    """데이터 준비 파이프라인을 실행한다.

    Returns:
        dict: {
            "df": pandas.DataFrame,            # USE_COLUMNS + lang_* 플래그, 정제 완료
            "eda_summary": dict,               # raw_shape, selected_shape, missing_ratio,
                                                # target_missing_removed, duplicates_removed
            "pandas_polars_compare": dict,     # pandas_shape, polars_shape, *_load_seconds
        }
    """
    try:
        path = download_if_missing(SURVEY_URL, RAW_DATA_PATH)
    except OSError as e:
        raise RuntimeError(f"설문 데이터 다운로드 실패: {e}") from e

    start = time.perf_counter()
    df_pandas_full = pd.read_csv(path)
    pandas_seconds = time.perf_counter() - start

    start = time.perf_counter()
    df_polars_full = pl.read_csv(path, infer_schema_length=10000)
    polars_seconds = time.perf_counter() - start

    pandas_polars_compare = {
        "pandas_shape": df_pandas_full.shape,
        "polars_shape": df_polars_full.shape,
        "pandas_load_seconds": round(pandas_seconds, 4),
        "polars_load_seconds": round(polars_seconds, 4),
    }

    df = df_pandas_full[USE_COLUMNS + [LANGUAGE_COLUMN]].copy()
    df["YearsCode"] = _clean_years_code(df["YearsCode"])
    df = _add_language_flags(df, df[LANGUAGE_COLUMN])
    df = df.drop(columns=[LANGUAGE_COLUMN])
    raw_shape = df.shape

    before = len(df)
    df = df.dropna(subset=["RemoteWork"])
    after_dropna = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    after_dedup = len(df)

    eda_summary = {
        "raw_shape": raw_shape,
        "selected_shape": df.shape,
        "missing_ratio": (df.isna().sum() / len(df) * 100).round(2).to_dict(),
        "target_missing_removed": before - after_dropna,
        "duplicates_removed": after_dropna - after_dedup,
    }

    return {"df": df, "eda_summary": eda_summary, "pandas_polars_compare": pandas_polars_compare}
