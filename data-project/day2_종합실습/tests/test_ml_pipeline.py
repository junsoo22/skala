"""ml_pipeline.run() 검증."""
from pathlib import Path

from src import ml_pipeline


def test_run_returns_expected_keys(sample_df, tmp_path, monkeypatch):
    monkeypatch.setattr(ml_pipeline, "MODEL_PATH", tmp_path / "model.pkl")

    result = ml_pipeline.run(sample_df)

    assert set(result.keys()) == {
        "model_comparison", "best_model_name", "model_path", "feature_importance",
    }
    assert set(result["model_comparison"].keys()) == {"LogisticRegression", "RandomForest"}
    assert result["best_model_name"] in result["model_comparison"]
    assert "stable_features" in result["feature_importance"]
    assert "reliable_categorical_features" in result["feature_importance"]


def test_model_metrics_are_valid_and_model_file_saved(sample_df, tmp_path, monkeypatch):
    monkeypatch.setattr(ml_pipeline, "MODEL_PATH", tmp_path / "model.pkl")

    result = ml_pipeline.run(sample_df)

    for metrics in result["model_comparison"].values():
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["f1"] <= 1

    model_path = Path(result["model_path"])
    assert model_path.exists()
    assert model_path.stat().st_size > 0


def test_stable_feature_importance_has_all_always_present_features(sample_df, tmp_path, monkeypatch):
    monkeypatch.setattr(ml_pipeline, "MODEL_PATH", tmp_path / "model.pkl")

    result = ml_pipeline.run(sample_df)

    stable = result["feature_importance"]["stable_features"]
    assert len(stable) > 0
    for entry in stable:
        assert entry["feature"].startswith("num__")
        assert isinstance(entry["score"], float)
