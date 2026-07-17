"""stats_analysis.run() 검증."""
from src import stats_analysis


def test_run_returns_expected_keys(sample_df):
    result = stats_analysis.run(sample_df)
    assert set(result.keys()) == {"describe", "corr", "ttest"}


def test_describe_covers_numeric_cols(sample_df):
    result = stats_analysis.run(sample_df)
    assert list(result["describe"].columns) == stats_analysis.NUMERIC_COLS


def test_corr_is_square_matrix_over_numeric_cols(sample_df):
    result = stats_analysis.run(sample_df)
    corr = result["corr"]
    assert list(corr.columns) == stats_analysis.NUMERIC_COLS
    assert list(corr.index) == stats_analysis.NUMERIC_COLS


def test_ttest_p_value_in_valid_range(sample_df):
    result = stats_analysis.run(sample_df)
    p = result["ttest"]["p"]
    assert p is None or 0 <= p <= 1
    assert result["ttest"]["interpretation"]
