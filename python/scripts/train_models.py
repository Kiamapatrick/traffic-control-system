#!/usr/bin/env python
"""Train ML models on SUMO simulation data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traffic_control import (
    generate_manhattan_example,
    run_ml_pipeline,
    TrafficFlowRegressor,
)


def main():
    print("=" * 60)
    print("ML Model Training Pipeline")
    print("=" * 60)

    # Generate network
    print("\nGenerating Manhattan grid network...")
    network = generate_manhattan_example()

    # Run pipeline
    print("\nRunning ML pipeline...")
    models = run_ml_pipeline(
        network,
        output_dir="models",
        model_types=["linear", "ridge", "random_forest", "xgboost"],
        duration=3600,
        lookback=4,
    )

    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print(f"\nTrained {len(models)} models:")
    for name, model in models.items():
        print(f"  {name}: MAE={model.metrics.get('mae', 'N/A'):.4f}")

    print("\nModels saved to: models/")
    print("Use with: traffic-control predict --model random_forest ...")


if __name__ == "__main__":
    main()