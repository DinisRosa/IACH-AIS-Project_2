import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from dividir_dataset import dividir_parquet

COLUNAS_FEATURES = ["x", "y", "signed_turn", "time_gap",
                    "euc_speed", "distanceToShore"]


def adicionar_t_rel(df):
    """Acrescenta t_rel: segundos desde o primeiro ponto de cada trajetória.

    Calculado a partir do time_gap BRUTO (antes de normalizar), por isso
    tem de ser chamado antes de aplicar_normalizacao. Assume que o df está
    ordenado por (id, t) e que time_gap[i] = t[i] - t[i-1]; o primeiro ponto
    de cada trajetória fica com t_rel = 0. Não é normalizado.
    """
    df = df.copy()
    g = df.groupby("id", observed=True)["time_gap"]
    t_rel = g.cumsum() - g.transform("first")
    df.insert(df.columns.get_loc("id") + 1, "t_rel", t_rel.astype("float64"))
    return df


def ajustar_normalizacao(df_treino, colunas=COLUNAS_FEATURES):
    """Calcula mediana e IQR de cada coluna, usando SÓ o treino.

    Se o IQR for 0 (coluna quase constante), recorre ao desvio-padrão
    e, em último caso, a 1.0, para nunca dividir por zero.
    """
    params = {}
    for c in colunas:
        v = df_treino[c].astype("float64")
        mediana = float(v.median())
        q1, q3 = v.quantile([0.25, 0.75])
        escala = float(q3 - q1)
        if escala <= 0:
            escala = float(v.std())
        if not np.isfinite(escala) or escala <= 0:
            escala = 1.0
        params[c] = {"mediana": mediana, "escala": escala}
    return params


def aplicar_normalizacao(df, params):
    """Aplica (valor - mediana) / escala, com os parâmetros do treino."""
    df = df.copy()
    for c, p in params.items():
        df[c] = ((df[c].astype("float64") - p["mediana"]) / p["escala"]).astype("float32")
    return df


def preparar_dados(parquet_path, treino_path, teste_path, validacao_path,
                   percent_treino, percent_teste, percent_validacao,
                   params_path="data/normalizacao.json", seed=42):
    """Divide por trajetória e normaliza (mediana/IQR ajustados só ao treino).

    1. Divide o Parquet em treino/teste/validação por id completo.
    2. Acrescenta t_rel (segundos desde o início da trajetória, em bruto,
       calculado a partir do time_gap antes de normalizar).
    3. Ajusta a normalização ao treino e guarda os parâmetros em JSON.
    4. Aplica a mesma transformação aos três conjuntos e grava os Parquet.

    O t_rel NÃO é normalizado: serve para o janelamento (por pontos ou por
    tempo) e para detetar gaps. O time_gap normalizado é a feature da rede.

    Devolve (treino_path, teste_path, validacao_path, params_path).
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        bruto = dividir_parquet(
            parquet_path,
            tmp / "treino.parquet", tmp / "teste.parquet", tmp / "validacao.parquet",
            percent_treino, percent_teste, percent_validacao, seed=seed,
        )
        treino, teste, validacao = (
            adicionar_t_rel(pd.read_parquet(p)) for p in bruto
        )

    params = ajustar_normalizacao(treino)

    params_path = Path(params_path)
    params_path.parent.mkdir(parents=True, exist_ok=True)
    params_path.write_text(json.dumps(params, indent=2, ensure_ascii=False))

    caminhos = []
    for df, destino in ((treino, treino_path),
                        (teste, teste_path),
                        (validacao, validacao_path)):
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        aplicar_normalizacao(df, params).to_parquet(destino, index=False)
        caminhos.append(str(destino))

    return (*caminhos, str(params_path))


if __name__ == "__main__":
    print(preparar_dados(
        "data/ais_128.parquet",
        "data/treino_norm.parquet", "data/teste_norm.parquet",
        "data/validacao_norm.parquet",
        70, 15, 15,
    ))
