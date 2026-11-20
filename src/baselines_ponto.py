"""Baselines de classificação ponto a ponto usando exclusivamente o treino."""

import json
import pickle
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
)


FEATURES = [
    "x",
    "y",
    "signed_turn",
    "time_gap",
    "euc_speed",
    "distanceToShore",
]
SEED = 42


def carregar_treino(caminho="data/treino_norm.parquet"):
    """Carrega o conjunto de treino e devolve X e y."""
    df = pd.read_parquet(caminho, columns=FEATURES + ["label"])
    X = df[FEATURES].to_numpy(dtype=np.float32)
    y = df["label"].to_numpy(dtype=np.int8)
    return X, y


def criar_modelos():
    return {
        "dummy_majoritario": DummyClassifier(strategy="most_frequent"),
        "regressao_logistica": LogisticRegression(
            solver="lbfgs",
            max_iter=500,
            random_state=SEED,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=16,
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=SEED,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            learning_rate=0.1,
            max_iter=100,
            max_leaf_nodes=31,
            l2_regularization=0.1,
            random_state=SEED,
        ),
    }


def probabilidades_positivas(modelo, X):
    if not hasattr(modelo, "predict_proba"):
        return None
    return modelo.predict_proba(X)[:, 1]


def avaliar_ponto(modelo, X, y):
    y_pred = modelo.predict(X).astype(np.int8)
    resultado = {
        "accuracy": float(accuracy_score(y, y_pred)),
        "precision_pesca": float(precision_score(y, y_pred, pos_label=1, zero_division=0)),
        "recall_pesca": float(recall_score(y, y_pred, pos_label=1, zero_division=0)),
        "f1_pesca": float(f1_score(y, y_pred, pos_label=1, zero_division=0)),
        "matriz_confusao": confusion_matrix(
            y, y_pred, labels=[0, 1]
        ).tolist(),
    }

    y_score = probabilidades_positivas(modelo, X)
    if y_score is not None:
        resultado["roc_auc"] = float(roc_auc_score(y, y_score))
        resultado["pr_auc"] = float(average_precision_score(y, y_score))
    else:
        resultado["roc_auc"] = None
        resultado["pr_auc"] = None
    return resultado


def executar_baselines(
    treino_path="data/treino_norm.parquet",
    modelos_dir="data/modelos/baselines",
    resultado_path="data/baselines_treino.json",
):
    X, y = carregar_treino(treino_path)
    modelos_dir = Path(modelos_dir)
    resultado_path = Path(resultado_path)
    modelos_dir.mkdir(parents=True, exist_ok=True)
    resultado_path.parent.mkdir(parents=True, exist_ok=True)

    resultados = {
        "conjunto": "treino",
        "tipo_avaliacao": "metricas_no_treino_de_ajuste",
        "validacao_utilizada": False,
        "teste_utilizado": False,
        "n_pontos": len(y),
        "features": FEATURES,
        "classe_positiva": 1,
        "seed": SEED,
        "modelos": {},
    }

    for nome, modelo in criar_modelos().items():
        inicio = perf_counter()
        modelo.fit(X, y)
        duracao_s = perf_counter() - inicio
        metricas = avaliar_ponto(modelo, X, y)
        metricas["tempo_treino_s"] = duracao_s

        with (modelos_dir / f"{nome}.pkl").open("wb") as ficheiro:
            pickle.dump(modelo, ficheiro, protocol=pickle.HIGHEST_PROTOCOL)
        resultados["modelos"][nome] = metricas
        print(
            f"{nome}: accuracy={metricas['accuracy']:.4f}, "
            f"f1_pesca={metricas['f1_pesca']:.4f}, "
            f"tempo={duracao_s:.2f}s"
        )

    resultado_path.write_text(
        json.dumps(resultados, indent=2, ensure_ascii=False),
    )
    print(f"Resultado guardado em {resultado_path}")
    print(f"Modelos guardados em {modelos_dir}")
    return resultados


if __name__ == "__main__":
    executar_baselines()
