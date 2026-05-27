"""Simple iris classifier MLOps pipeline for Kubeflow Pipelines.

Three components:
  1. load_data — fetches the iris dataset, splits into train/test, writes CSVs.
  2. train     — trains a RandomForestClassifier, exports the model with joblib.
  3. predict   — loads the model, runs prediction on test set, prints accuracy.

Compile to YAML with:
    pip install -r mlops/pipelines/requirements.txt
    python mlops/pipelines/iris_pipeline.py
"""

from kfp import dsl, compiler


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["scikit-learn==1.5.2", "pandas==2.2.3"],
)
def load_data(
    train_dataset: dsl.Output[dsl.Dataset],
    test_dataset: dsl.Output[dsl.Dataset],
):
    import pandas as pd
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split

    iris = load_iris(as_frame=True)
    df = iris.frame
    df.rename(columns={"target": "label"}, inplace=True)

    train_df, test_df = train_test_split(df, test_size=0.25, random_state=42, stratify=df["label"])
    train_df.to_csv(train_dataset.path, index=False)
    test_df.to_csv(test_dataset.path, index=False)
    print(f"[load_data] iris loaded: total={len(df)} train={len(train_df)} test={len(test_df)}")


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["scikit-learn==1.5.2", "pandas==2.2.3", "joblib==1.4.2"],
)
def train(
    train_dataset: dsl.Input[dsl.Dataset],
    model: dsl.Output[dsl.Model],
    n_estimators: int = 100,
):
    import pandas as pd
    import joblib
    from sklearn.ensemble import RandomForestClassifier

    df = pd.read_csv(train_dataset.path)
    X = df.drop(columns=["label"])
    y = df["label"]

    clf = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
    clf.fit(X, y)
    joblib.dump(clf, model.path)
    print(f"[train] trained RandomForest({n_estimators=}) on {len(df)} samples")
    print(f"[train] training accuracy: {clf.score(X, y):.4f}")


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["scikit-learn==1.5.2", "pandas==2.2.3", "joblib==1.4.2"],
)
def predict(
    test_dataset: dsl.Input[dsl.Dataset],
    model: dsl.Input[dsl.Model],
    metrics: dsl.Output[dsl.Metrics],
) -> float:
    import pandas as pd
    import joblib
    from sklearn.metrics import accuracy_score, classification_report

    df = pd.read_csv(test_dataset.path)
    X = df.drop(columns=["label"])
    y = df["label"]

    clf = joblib.load(model.path)
    preds = clf.predict(X)
    acc = float(accuracy_score(y, preds))
    print(f"[predict] test accuracy: {acc:.4f}")
    print("[predict] classification report:")
    print(classification_report(y, preds, digits=4))

    metrics.log_metric("accuracy", acc)
    metrics.log_metric("test_size", float(len(df)))
    return acc


@dsl.pipeline(
    name="iris-classifier",
    description="Trivial MLOps pipeline: load iris -> train RandomForest -> predict on test split.",
)
def iris_pipeline(n_estimators: int = 100):
    data = load_data()
    trained = train(train_dataset=data.outputs["train_dataset"], n_estimators=n_estimators)
    predict(
        test_dataset=data.outputs["test_dataset"],
        model=trained.outputs["model"],
    )


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__) or ".", "iris_pipeline.yaml")
    compiler.Compiler().compile(iris_pipeline, out)
    print(f"Compiled pipeline written to {out}")
