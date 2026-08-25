from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
import numpy as np
import pandas as pd
from datetime import datetime

if TYPE_CHECKING:
    from traffic_control.models import Network
    from traffic_control.ml.regression import TrafficFlowRegressor


def run_ml_pipeline(
    network: "Network",
    output_dir: str = "models",
    model_types: list[str] | None = None,
    duration: int = 3600,
    lookback: int = 4,
) -> dict[str, "TrafficFlowRegressor"]:
    from traffic_control.ml.dataset import SUMODataGenerator, create_features, prepare_training_data
    from traffic_control.ml.regression import train_models, compare_models

    generator = SUMODataGenerator()

    print("Generating SUMO simulation data...")
    df = generator.generate_dataset(network, name="training", duration=duration)

    print("Creating features...")
    df = create_features(df, network)

    print("Preparing training data...")
    X, y, feature_names = prepare_training_data(df, target="flow", lookback=lookback)

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"Training on {len(X_train)} samples, testing on {len(X_test)} samples")

    print("Training models...")
    models = train_models(X_train, y_train, feature_names, model_types)

    print("Evaluating models...")
    comparison = compare_models(models, X_test, y_test)
    print(comparison.to_string(index=False))

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    saved_models = {}
    for name, model in models.items():
        model.metrics = model.evaluate(X_test, y_test)
        model.version = datetime.now().isoformat()
        model.save(Path(output_dir) / f"{name}.joblib")
        saved_models[name] = model

    best_model = comparison.iloc[0]["model"]
    print(f"\nBest model: {best_model} (MAE: {comparison.iloc[0]['mae']:.4f})")

    return saved_models


def predict_flows(
    network: "Network",
    model_id: str,
    features: dict[str, float],
    model_dir: str = "models",
) -> dict[str, float]:
    from traffic_control.ml.regression import TrafficFlowRegressor

    model_path = Path(model_dir) / f"{model_id}.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Model {model_id} not found at {model_path}")

    model = TrafficFlowRegressor.load(model_path)

    X = np.array([[features.get(f, 0) for f in model.features]])
    predictions = model.predict(X)

    return {f"pred_{i}": float(p) for i, p in enumerate(predictions[0])}


def evaluate_model_on_network(
    network: "Network",
    model_id: str,
    duration: int = 3600,
    lookback: int = 4,
    model_dir: str = "models",
) -> dict:
    from traffic_control.ml.dataset import SUMODataGenerator, create_features, prepare_training_data
    from traffic_control.ml.regression import TrafficFlowRegressor

    generator = SUMODataGenerator()

    df = generator.generate_dataset(network, name="eval", duration=duration)
    df = create_features(df, network)
    X, y, feature_names = prepare_training_data(df, target="flow", lookback=lookback)

    model_path = Path(model_dir) / f"{model_id}.joblib"
    model = TrafficFlowRegressor.load(model_path)

    metrics = model.evaluate(X, y)
    return metrics