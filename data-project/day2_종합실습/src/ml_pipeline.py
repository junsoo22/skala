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
# 원-핫 인코딩된 범주형 피처는 표본이 이 값 미만이면 계수가 커도 신뢰하지 않는다
# (희귀 범주는 과적합으로 계수가 튀기 쉬움 — 예: 응답자 16명뿐인 나라의 계수는 우연일 가능성이 높음)
MIN_CATEGORY_SAMPLES = 500
TOP_N_FEATURES = 10


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


def _feature_importance(pipeline: Pipeline, X_train: pd.DataFrame) -> dict:
    """최종 선택된 모델의 피처 중요도를 계산한다.

    - "안정적인 피처"(수치형+언어 플래그)는 전체 응답자에 다 존재하는 값이라 표본 걱정 없이
      그대로 사용한다.
    - 원-핫 인코딩된 범주형 피처는 MIN_CATEGORY_SAMPLES 이상인 것만 "신뢰할 수 있는 피처"로
      취급한다. 희귀 범주(예: 응답자 10여 명뿐인 나라)는 계수가 커도 과적합일 가능성이 높다.
    """
    clf = pipeline.named_steps["clf"]
    feature_names = pipeline.named_steps["prep"].get_feature_names_out()

    if hasattr(clf, "coef_"):
        scores = clf.coef_[0]
    elif hasattr(clf, "feature_importances_"):
        scores = clf.feature_importances_
    else:
        return {"stable_features": [], "reliable_categorical_features": []}

    importance = pd.DataFrame({"feature": feature_names, "score": scores})
    importance["abs_score"] = importance["score"].abs()

    always_present = {f"num__{c}" for c in NUM_COLS}
    stable = (
        importance[importance["feature"].isin(always_present)]
        .sort_values("abs_score", ascending=False)
        .head(TOP_N_FEATURES)
    )

    category_counts = {}
    for col in CAT_COLS:
        for value, count in X_train[col].value_counts().items():
            category_counts[f"cat__{col}_{value}"] = int(count)
    importance["n"] = importance["feature"].map(category_counts)
    reliable_cat = (
        importance[importance["feature"].str.startswith("cat__") & (importance["n"] >= MIN_CATEGORY_SAMPLES)]
        .sort_values("abs_score", ascending=False)
        .head(TOP_N_FEATURES)
    )

    return {
        "stable_features": stable[["feature", "score"]].round(4).to_dict("records"),
        "reliable_categorical_features": reliable_cat[["feature", "score", "n"]].round(4).to_dict("records"),
    }


def run(df: pd.DataFrame) -> dict:
    """전처리+모델 Pipeline을 구성해 학습·평가·저장한다.

    Args:
        df: data_prep.run()이 반환한 정제 데이터.

    Returns:
        dict: {
            "model_comparison": dict,  # {"LogisticRegression": {"accuracy":.., "f1":..}, "RandomForest": {...}}
            "best_model_name": str,
            "model_path": str,
            "feature_importance": dict,  # {"stable_features": [...], "reliable_categorical_features": [...]}
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

    feature_importance = _feature_importance(best_model, X_train)
    logger.info("피처 중요도(안정적) top: %s", feature_importance["stable_features"][:3])

    return {
        "model_comparison": model_comparison,
        "best_model_name": best_model_name,
        "model_path": str(MODEL_PATH),
        "feature_importance": feature_importance,
    }
