from pathlib import Path

import pandas as pd

COLUNAS_ORIGEM = ["id", "t", "label", "x", "y", "signed_turn",
                  "time_gap", "euc_speed", "distanceToShore"]
COLUNAS_FLOAT = ["x", "y", "signed_turn", "time_gap",
                 "euc_speed", "distanceToShore"]


def limpar_csv_para_parcelar(csv_path, output_path, manter_t=False):
    """Lê o CSV original, mantém só as colunas úteis e grava em Parquet.

    - Ordena por (id, t) antes de gravar, para garantir a ordem temporal.
    - Binariza o label: qualquer classe com 'fishing' -> 1, resto -> 0.
    - Se manter_t=True, mantém também a coluna 't' no ficheiro final.

    Devolve o caminho do ficheiro Parquet criado (str).
    """
    df = pd.read_csv(csv_path, usecols=COLUNAS_ORIGEM)

    # Ordem temporal dentro de cada trajetória
    df = df.sort_values(["id", "t"], kind="stable").reset_index(drop=True)

    # Label binário (pesca = 1, navegação = 0)
    if not pd.api.types.is_numeric_dtype(df["label"]):
        df["label"] = (
            df["label"].astype(str).str.contains("fishing", case=False, na=False)
        )
    df["label"] = df["label"].astype("int8")

    # Tipos compactos
    df["id"] = df["id"].astype("category")
    df[COLUNAS_FLOAT] = df[COLUNAS_FLOAT].astype("float32")

    colunas_finais = ["id", "label", "x", "y", "signed_turn",
                      "time_gap", "euc_speed", "distanceToShore"]
    if manter_t:
        colunas_finais.insert(1, "t")
    df = df[colunas_finais]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    return str(output_path)


if __name__ == "__main__":
    print(limpar_csv_para_parcelar("./data/123_fishing_trajs.csv", "./data/ais_123.parquet", manter_t=True))