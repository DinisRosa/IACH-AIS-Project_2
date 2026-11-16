from pathlib import Path

import numpy as np
import pandas as pd


def dividir_parquet(parquet_path, treino_path, teste_path, validacao_path,
                    percent_treino, percent_teste, percent_validacao,
                    seed=42):
    """Divide um Parquet em treino/teste/validação, por trajetória (id).

    Todos os pontos de cada trajetória ficam no mesmo subconjunto.
    As percentagens têm de ser inteiros que somam 100.

    Devolve (treino_path, teste_path, validacao_path) como strings.
    """
    if percent_treino + percent_teste + percent_validacao != 100:
        raise ValueError(
            "As percentagens têm de somar 100 "
            f"(recebido: {percent_treino}+{percent_teste}+{percent_validacao})."
        )
    if min(percent_treino, percent_teste, percent_validacao) < 0:
        raise ValueError("As percentagens não podem ser negativas.")

    df = pd.read_parquet(parquet_path)

    # Baralhar os ids de forma reprodutível
    ids = np.array(sorted(df["id"].astype(str).unique()))
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)

    n = len(ids)
    n_treino = round(n * percent_treino / 100)
    n_teste = round(n * percent_teste / 100)
    # A validação fica com o resto, para nunca perder nem duplicar ids
    ids_treino = ids[:n_treino]
    ids_teste = ids[n_treino:n_treino + n_teste]
    ids_validacao = ids[n_treino + n_teste:]

    id_str = df["id"].astype(str)
    partes = [
        (ids_treino, treino_path),
        (ids_teste, teste_path),
        (ids_validacao, validacao_path),
    ]

    caminhos = []
    for ids_parte, destino in partes:
        sub = df[id_str.isin(ids_parte)].reset_index(drop=True)
        if hasattr(sub["id"], "cat"):
            sub["id"] = sub["id"].cat.remove_unused_categories()
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        sub.to_parquet(destino, index=False)
        caminhos.append(str(destino))

    return tuple(caminhos)


if __name__ == "__main__":
    print(dividir_parquet(
        "./data/ais_128.parquet",
        "./data/treino.parquet", "./data/teste.parquet", "./data/validacao.parquet",
        70, 15, 15,
    ))