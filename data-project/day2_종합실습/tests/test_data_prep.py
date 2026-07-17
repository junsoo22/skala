"""data_prep 순수 로직(네트워크 없이 테스트 가능한 부분) 검증."""
from pathlib import Path

import pandas as pd

from src import data_prep


def test_clean_years_code_handles_text_values():
    series = pd.Series(["Less than 1 year", "More than 50 years", "10", None])
    result = data_prep._clean_years_code(series)
    assert result.iloc[0] == 0.0
    assert result.iloc[1] == 51.0
    assert result.iloc[2] == 10.0
    assert pd.isna(result.iloc[3])


def test_add_language_flags_marks_exact_matches_only():
    df = pd.DataFrame({"dummy": [1, 2, 3]})
    raw = pd.Series(["Python;JavaScript", "C++", None])
    result = data_prep._add_language_flags(df.copy(), raw)

    assert result["lang_python"].tolist() == [1, 0, 0]
    assert result["lang_javascript"].tolist() == [1, 0, 0]
    assert result["lang_cpp"].tolist() == [0, 1, 0]
    # "C"는 "C++"의 부분 문자열이 아니라 별개 토큰이므로 매칭되면 안 됨
    assert result["lang_c"].tolist() == [0, 0, 0]


def test_download_if_missing_skips_download_when_cached(tmp_path, monkeypatch):
    dest = tmp_path / "cached.csv"
    dest.write_text("already here")
    calls = []
    monkeypatch.setattr(
        data_prep.urllib.request, "urlretrieve",
        lambda url, filename: calls.append((url, filename)),
    )

    result = data_prep.download_if_missing("http://example.com/x.csv", dest)

    assert result == dest
    assert calls == []


def test_download_if_missing_downloads_when_absent(tmp_path, monkeypatch):
    dest = tmp_path / "new.csv"
    calls = []

    def fake_urlretrieve(url, filename):
        calls.append(url)
        Path(filename).write_text("downloaded")

    monkeypatch.setattr(data_prep.urllib.request, "urlretrieve", fake_urlretrieve)

    result = data_prep.download_if_missing("http://example.com/x.csv", dest)

    assert len(calls) == 1
    assert result.exists()
