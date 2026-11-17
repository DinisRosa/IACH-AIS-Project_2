"""Análise dos gaps temporais entre pontos consecutivos das trajetórias AIS.

Serve para dois fins:
- escolher o limiar de gap a partir do qual uma janela deve ser interrompida;
- detetar trajetórias que possam ser duas viagens fundidas no mesmo `id`
  (salto de posição incompatível com o tempo decorrido).
"""

import numpy as np
import pandas as pd

LIMIAR_GAP_SEGUNDOS = 600.0  # 10 minutos
VELOCIDADE_MAX_KMH = 30.0  # acima disto, o salto é suspeito para um navio de pesca


def analisar_gaps(parquet_path, limiar_segundos=LIMIAR_GAP_SEGUNDOS):
    """Tabela com todos os gaps acima de `limiar_segundos`.

    Ordena por id, calcula a posição e o tempo relativo de cada ponto e a
    distância/velocidade entre pontos consecutivos. O primeiro ponto de cada
    trajetória é ignorado, porque o seu `time_gap` não é um intervalo interno.

    Cada linha representa o ponto que vem DEPOIS do gap, com o gap em horas,
    a distância percorrida no intervalo e a velocidade implícita.
    """
    df = pd.read_parquet(parquet_path)
    df = df.sort_values(["id"], kind="stable").reset_index(drop=True)
    grupo = df.groupby("id", observed=True)

    df["idx"] = grupo.cumcount()
    df["t_rel"] = grupo["time_gap"].cumsum() - grupo["time_gap"].transform("first")
    df["dist_m"] = np.hypot(grupo["x"].diff(), grupo["y"].diff())
    df["vel_kmh"] = df["dist_m"] / df["time_gap"].replace(0, np.nan) * 3.6
    df["label_antes"] = grupo["label"].shift(1)

    gaps = df[(df["time_gap"] > limiar_segundos) & (df["idx"] > 0)].copy()
    gaps["gap_h"] = gaps["time_gap"] / 3600
    gaps["t_rel_h"] = gaps["t_rel"] / 3600
    gaps["dist_km"] = gaps["dist_m"] / 1000
    gaps["muda_label"] = gaps["label"] != gaps["label_antes"]

    colunas = ["id", "idx", "t_rel_h", "gap_h", "dist_km", "vel_kmh",
               "label_antes", "label", "muda_label"]
    return (gaps[colunas]
            .sort_values("gap_h", ascending=False)
            .reset_index(drop=True))


def resumo_gaps(gaps):
    """Resume os gaps por trajetória: quantos, o maior e o tempo total."""
    if gaps.empty:
        return pd.DataFrame(columns=["n_gaps", "gap_max_h", "gap_total_h",
                                     "dist_max_km"])
    return (gaps.groupby("id", observed=True)
            .agg(n_gaps=("gap_h", "size"),
                 gap_max_h=("gap_h", "max"),
                 gap_total_h=("gap_h", "sum"),
                 dist_max_km=("dist_km", "max"))
            .sort_values("gap_max_h", ascending=False))


def candidatos_fusao(gaps, velocidade_max_kmh=VELOCIDADE_MAX_KMH):
    """Gaps em que a posição salta demasiado para o tempo decorrido.

    Uma velocidade implícita acima de `velocidade_max_kmh` sugere que o mesmo
    `id` junta duas trajetórias distintas. É só um indício: gaps longos com
    deslocamento pequeno (navio parado a pescar) não são sinal de fusão.
    """
    return gaps[gaps["vel_kmh"] > velocidade_max_kmh].reset_index(drop=True)


if __name__ == "__main__":
    caminho = "./data/ais_123.parquet"
    time_gap = pd.read_parquet(caminho, columns=["time_gap"])["time_gap"]

    print("Número de gaps acima de:")
    for limite in (60, 600, 3600, 6 * 3600):
        print(f"  {limite / 60:>6.0f} min: {int((time_gap > limite).sum()):>5d}")

    gaps = analisar_gaps(caminho)
    print(f"\nMaiores gaps (>{LIMIAR_GAP_SEGUNDOS / 60:.0f} min):")
    print(gaps.head(10).to_string(index=False))

    print("\nTrajetórias com o maior gap:")
    print(resumo_gaps(gaps).head(10).to_string())

    suspeitos = candidatos_fusao(gaps)
    print(f"\nGaps com velocidade implícita > {VELOCIDADE_MAX_KMH:.0f} km/h "
          f"(candidatos a fusão): {len(suspeitos)}")
    if not suspeitos.empty:
        print(suspeitos.to_string(index=False))
