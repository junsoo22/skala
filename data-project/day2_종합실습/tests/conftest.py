"""pytest 공용 설정: src를 임포트 가능하게 경로를 잡고, 테스트용 합성 데이터를 제공한다."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# tests/ 밖(day2_종합실습/)에 있는 src 패키지를 pytest 실행 위치와 무관하게 임포트할 수 있게 한다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """실제 파이프라인 데이터(data_prep.run() 결과)와 같은 컬럼 구조를 가진 합성 데이터.

    네트워크 다운로드 없이 stats_analysis/visualize_*/ml_pipeline을 테스트하기 위한 것으로,
    100행이면 train_test_split(stratify=y)이 실패하지 않을 만큼 클래스별 표본이 확보된다.
    """
    rng = np.random.default_rng(42)
    n = 100
    return pd.DataFrame({
        "RemoteWork": rng.choice(
            ["Remote", "Hybrid (some remote, some in-person)", "In-person"], n
        ),
        "Age": rng.choice(["18-24 years old", "25-34 years old", "35-44 years old"], n),
        "Employment": rng.choice(["Employed, full-time", "Independent contractor"], n),
        "EdLevel": rng.choice(["Bachelor's degree", "Master's degree"], n),
        "DevType": rng.choice(["Developer, full-stack", "Developer, back-end"], n),
        "OrgSize": rng.choice(["10 to 19 employees", "20 to 99 employees"], n),
        "Country": rng.choice(["United States", "Germany", "South Korea"], n),
        "MainBranch": "I am a developer by profession",
        "Industry": rng.choice(["Software Development", "Fintech", None], n),
        "ICorPM": rng.choice(["Individual contributor", "People manager"], n),
        "AISent": rng.choice(["Favorable", "Unfavorable", "Indifferent"], n),
        "ConvertedCompYearly": rng.uniform(30_000, 200_000, n),
        "WorkExp": rng.uniform(0, 30, n),
        "JobSat": rng.integers(1, 11, n),
        "YearsCode": rng.uniform(0, 40, n),
        "lang_javascript": rng.integers(0, 2, n),
        "lang_html_css": rng.integers(0, 2, n),
        "lang_python": rng.integers(0, 2, n),
        "lang_sql": rng.integers(0, 2, n),
        "lang_typescript": rng.integers(0, 2, n),
        "lang_bash_shell": rng.integers(0, 2, n),
        "lang_java": rng.integers(0, 2, n),
        "lang_csharp": rng.integers(0, 2, n),
        "lang_cpp": rng.integers(0, 2, n),
        "lang_c": rng.integers(0, 2, n),
    })
