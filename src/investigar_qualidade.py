"""Investiga anomalias conhecidas do conjunto AIS e a separação por prefixo."""

import json

import numpy as np
import pandas as pd


def investigar_qualidade(csv_path="data/123_fishing_trajs.csv",
                        parquet_path="data/ais_123.parquet",
                        treino_path="data/treino_norm.parquet",
                        validacao_path="data/validacao_norm.parquet",
                        teste_path="data/teste_norm.parquet"):
    df = pd.read_csv(
        csv_path,
        usecols=["id", "t", "label", "x", "y", "distance_gap",
                 "time_gap", "euc_speed"],
    )
    df["t"] = pd.to_datetime(df["t"], errors="raise")
    df = df.sort_values(["id", "t"], kind="stable").reset_index(drop=True)

    dt_real = df.groupby("id", observed=True)["t"].diff().dt.total_seconds()
    diff_t = (dt_real - df["time_gap"]).abs()
    desalinhamentos = df.loc[diff_t > 1].copy()
    desalinhamentos["diferenca_s"] = diff_t.loc[desalinhamentos.index]

    euc_extremos = df.loc[df["euc_speed"] > 30]
    velocidades_impl = df["distance_gap"] / df["time_gap"].replace(0, np.nan) * 3.6
    impl_extremos = df.loc[velocidades_impl > 30].copy()
    impl_extremos["velocidade_kmh"] = velocidades_impl.loc[impl_extremos.index]

    ids = pd.read_parquet(parquet_path, columns=["id"])["id"].astype(str).drop_duplicates()
    prefixos = ids.str.rsplit("-", n=1).str[0]
    grupos = pd.DataFrame({"id": ids, "prefixo": prefixos})
    grupos_partilhados = grupos[grupos.groupby("prefixo")["prefixo"].transform("size") > 1]

    conjuntos = {
        nome: set(pd.read_parquet(caminho, columns=["id"])["id"].astype(str))
        for nome, caminho in (
            ("treino", treino_path),
            ("validacao", validacao_path),
            ("teste", teste_path),
        )
    }
    prefixos_cruzados = []
    for prefixo, ids_grupo in grupos_partilhados.groupby("prefixo")["id"]:
        ids_grupo = set(ids_grupo)
        membros = tuple(
            nome for nome, ids_conjunto in conjuntos.items()
            if ids_grupo & ids_conjunto
        )
        if len(membros) > 1:
            prefixos_cruzados.append({
                "prefixo": prefixo,
                "n_ids": len(ids_grupo),
                "conjuntos": sorted(membros),
                "ids": sorted(ids_grupo),
            })

    return {
        "linhas": len(df),
        "trajetorias": df["id"].nunique(),
        "nulos": int(df.isna().sum().sum()),
        "timestamps_duplicados": int(df.duplicated(["id", "t"]).sum()),
        "desalinhamentos_t_time_gap": desalinhamentos[
            ["id", "t", "time_gap", "diferenca_s"]
        ].to_dict("records"),
        "euc_speed_gt30_n": len(euc_extremos),
        "euc_speed_gt50_n": int((df["euc_speed"] > 50).sum()),
        "euc_speed_max": float(df["euc_speed"].max()),
        "euc_speed_concentracao_por_id": (
            euc_extremos.groupby("id").size().sort_values(ascending=False).to_dict()
        ),
        "velocidade_implicita_gt30_n": len(impl_extremos),
        "velocidade_implicita_gt30_trajetorias": impl_extremos["id"].nunique(),
        "velocidade_implicita_max_kmh": float(velocidades_impl.max()),
        "prefixos_partilhados_n": grupos_partilhados["prefixo"].nunique(),
        "ids_com_prefixo_partilhado_n": grupos_partilhados["id"].nunique(),
        "prefixos_cruzados": prefixos_cruzados,
    }


if __name__ == "__main__":
    resultado = investigar_qualidade()
    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
