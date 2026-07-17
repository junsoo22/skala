"""ML Pipeline: RemoteWork == 'Remote' 여부 이진분류.

ColumnTransformer(수치형 imputer+scaler / 범주형 imputer+onehot) + Pipeline으로
LogisticRegression vs RandomForestClassifier를 비교하고, F1 기준으로 더 나은 모델을
joblib으로 저장한다.
"""
import logging
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

logger = logging.getLogger(__name__)

LANG_FLAG_COLS = [
    "lang_javascript", "lang_html_css", "lang_python", "lang_sql", "lang_typescript",
    "lang_bash_shell", "lang_java", "lang_csharp", "lang_cpp", "lang_c",
]
NUM_COLS = ["ConvertedCompYearly", "WorkExp", "JobSat", "YearsCode"] + LANG_FLAG_COLS
CAT_COLS = [
    "Age", "Employment", "EdLevel", "DevType", "OrgSize", "Country",
    "MainBranch", "Industry", "ICorPM", "AISent",
]
MODEL_PATH = Path("models/remote_work_model.pkl")


def _build_preprocessor() -> ColumnTransformer:
    num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    cat_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("num", num_pipeline, NUM_COLS),
        ("cat", cat_pipeline, CAT_COLS),
    ])


def run(df: pd.DataFrame) -> dict:
    """전처리+모델 Pipeline을 구성해 학습·평가·저장한다.

    Args:
        df: data_prep.run()이 반환한 정제 데이터.

    Returns:
        dict: {
            "model_comparison": dict,  # {"LogisticRegression": {"accuracy":.., "f1":..}, "RandomForest": {...}}
            "best_model_name": str,
            "model_path": str,
        }
    """
    y = (df["RemoteWork"] == "Remote").astype(int)
    X = df[NUM_COLS + CAT_COLS]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=1000),
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    }

    model_comparison = {}
    fitted_models = {}
    for name, clf in candidates.items():
        pipeline = Pipeline([("prep", _build_preprocessor()), ("clf", clf)])
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        model_comparison[name] = {
            "accuracy": round(accuracy_score(y_test, y_pred), 4),
            "f1": round(f1_score(y_test, y_pred), 4),
        }
        fitted_models[name] = pipeline
        logger.info("%s 학습 완료: %s", name, model_comparison[name])

    best_model_name = max(model_comparison, key=lambda name: model_comparison[name]["f1"])
    best_model = fitted_models[best_model_name]
    logger.info("최종 선택 모델: %s", best_model_name)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODEL_PATH)
    logger.info("모델 저장 완료: %s", MODEL_PATH)

    reloaded = joblib.load(MODEL_PATH)
    reloaded_f1 = round(f1_score(y_test, reloaded.predict(X_test)), 4)
    if reloaded_f1 != model_comparison[best_model_name]["f1"]:
        logger.error(
            "재로딩 모델 F1 불일치: 원본=%s, 재로딩=%s",
            model_comparison[best_model_name]["f1"], reloaded_f1,
        )
        raise RuntimeError("저장된 모델을 재로딩한 결과가 원본과 다릅니다.")
    logger.info("재로딩 검증 통과: F1=%s", reloaded_f1)

    return {
        "model_comparison": model_comparison,
        "best_model_name": best_model_name,
        "model_path": str(MODEL_PATH),
    }
