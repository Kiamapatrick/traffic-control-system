from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

if TYPE_CHECKING:
    from traffic_control.models import Network


class TrafficFlowRegressor:
    def __init__(self, model_type: str = "random_forest", **kwargs):
        self.model_type = model_type
        self.kwargs = kwargs
        self.model = None
        self.scaler = StandardScaler()
        self.features = None
        self.target = "flow"
        self.metrics = {}
        self.version = "1.0"

    def _create_model(self):
        if self.model_type == "linear":
            return LinearRegression()
        elif self.model_type == "ridge":
            return Ridge(alpha=self.kwargs.get("alpha", 1.0))
        elif self.model_type == "random_forest":
            return RandomForestRegressor(
                n_estimators=self.kwargs.get("n_estimators", 100),
                max_depth=self.kwargs.get("max_depth", 10),
                random_state=self.kwargs.get("random_state", 42),
                n_jobs=-1,
            )
        elif self.model_type == "xgboost":
            try:
                import xgboost as xgb
                return xgb.XGBRegressor(
                    n_estimators=self.kwargs.get("n_estimators", 100),
                    max_depth=self.kwargs.get("max_depth", 6),
                    learning_rate=self.kwargs.get("learning_rate", 0.1),
                    random_state=self.kwargs.get("random_state", 42),
                    n_jobs=-1,
                )
            except ImportError:
                raise ValueError("XGBoost not installed. Install with: pip install xgboost")
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: list[str] | None = None):
        self.features = feature_names or [f"f_{i}" for i in range(X.shape[1])]
        self.model = self._create_model()

        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict:
        preds = self.predict(X)
        self.metrics = {
            "mae": float(mean_absolute_error(y, preds)),
            "rmse": float(np.sqrt(mean_squared_error(y, preds))),
            "mape": float(mean_absolute_percentage_error(y, preds)),
        }
        return self.metrics

    def cross_validate(self, X: np.ndarray, y: np.ndarray, n_splits: int = 5) -> dict:
        tscv = TimeSeriesSplit(n_splits=n_splits)
        X_scaled = self.scaler.fit_transform(X)

        mae_scores = cross_val_score(
            self._create_model(), X_scaled, y, cv=tscv, scoring="neg_mean_absolute_error", n_jobs=-1
        )
        rmse_scores = cross_val_score(
            self._create_model(), X_scaled, y, cv=tscv, scoring="neg_root_mean_squared_error", n_jobs=-1
        )

        return {
            "cv_mae_mean": float(-mae_scores.mean()),
            "cv_mae_std": float(mae_scores.std()),
            "cv_rmse_mean": float(-rmse_scores.mean()),
            "cv_rmse_std": float(rmse_scores.std()),
        }

    def get_feature_importance(self) -> dict[str, float] | None:
        if self.model is None or not hasattr(self.model, "feature_importances_"):
            return None

        importances = self.model.feature_importances_
        if len(importances) != len(self.features):
            return None

        return dict(zip(self.features, importances))

    def save(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "model": self.model,
            "scaler": self.scaler,
            "features": self.features,
            "target": self.target,
            "model_type": self.model_type,
            "metrics": self.metrics,
            "version": self.version,
            "kwargs": self.kwargs,
        }
        joblib.dump(data, path)

    @classmethod
    def load(cls, path: str | Path) -> "TrafficFlowRegressor":
        data = joblib.load(path)
        regressor = cls(model_type=data["model_type"], **data.get("kwargs", {}))
        regressor.model = data["model"]
        regressor.scaler = data["scaler"]
        regressor.features = data["features"]
        regressor.target = data.get("target", "flow")
        regressor.metrics = data.get("metrics", {})
        regressor.version = data.get("version", "1.0")
        return regressor


def train_models(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    model_types: list[str] | None = None,
) -> dict[str, TrafficFlowRegressor]:
    if model_types is None:
        model_types = ["linear", "ridge", "random_forest"]

    models = {}
    for mt in model_types:
        try:
            reg = TrafficFlowRegressor(model_type=mt)
            reg.fit(X, y, feature_names)
            models[mt] = reg
        except Exception as e:
            print(f"Failed to train {mt}: {e}")

    return models


def compare_models(
    models: dict[str, TrafficFlowRegressor],
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> pd.DataFrame:
    rows = []
    for name, model in models.items():
        metrics = model.evaluate(X_test, y_test)
        rows.append({
            "model": name,
            "mae": metrics["mae"],
            "rmse": metrics["rmse"],
            "mape": metrics["mape"],
        })
    return pd.DataFrame(rows).sort_values("mae")