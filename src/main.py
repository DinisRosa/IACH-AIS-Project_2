from limpar_csv import limpar_csv_para_parcelar
from preparar_dados import preparar_dados


limpar_csv_para_parcelar("./data/123_fishing_trajs.csv", "./data/ais_123.parquet")
preparar_dados("./data/ais_123.parquet",
               "./data/treino_norm.parquet", "./data/teste_norm.parquet", "./data/validacao_norm.parquet",
               70, 15, 15)



import pandas as pd
t = pd.read_parquet("./data/treino_norm.parquet")
cols = ["x", "y", "signed_turn", "time_gap", "euc_speed", "distanceToShore"]
print(t[cols].describe(percentiles=[.01, .05, .95, .99]).T[["min", "1%", "5%", "95%", "99%", "max"]])

import pandas as pd
t = pd.read_parquet("data/treino_norm.parquet")
d = t.groupby("id", observed=True)["t_rel"].max() / 3600
print(d.describe())  # duração por trajetória, em horas

import pandas as pd
print(pd.read_parquet("./data/ais_123.parquet")["id"].nunique())

import pandas as pd
df = pd.read_csv("./data/123_fishing_trajs.csv", usecols=["id", "t"])
print(df["id"].nunique())
# ids com saltos de tempo muito grandes podem ser duas trajetórias fundidas

from criar_janelas import criar_janelas

r = criar_janelas("./data/treino_norm.parquet", n_pontos=256, sobreposicao_pct=50)

print(r["X"].shape)   # (nº de janelas, 256, 6)
print(r["info"])


import pandas as pd

# 1. Quantos gaps acima de 10 min existem no treino, e qual é o maior (em horas)?
t = pd.read_parquet("data/treino_norm.parquet", columns=["id", "t_rel"])
gap = t.groupby("id", observed=True)["t_rel"].diff()
print((gap > 600).sum(), gap.max() / 3600)

# 2. Quanto tempo real cobrem as janelas de 256 pontos (em minutos)?
dur = (r["meta"]["t_fim"] - r["meta"]["t_ini"]) / 60
print(dur.describe())


r_gap = criar_janelas("./data/treino_norm.parquet", 256, 50, gap_max_s=600)
print(r_gap["info"])

dur = (r["meta"]["t_fim"] - r["meta"]["t_ini"]) / 60
print("janelas com mais de 60 min:", (dur > 60).sum(), "de", len(dur))


r = criar_janelas("./data/treino_norm.parquet", n_pontos=256,
                  sobreposicao_pct=50, gap_max_s=600)

r_t = criar_janelas("./data/treino_norm.parquet", duracao_s=30*60,
                    sobreposicao_pct=50, gap_max_s=600)
print(r_t["X"].shape)
print(r_t["info"])

n = r_t["meta"]["n_pontos"]
print(n.describe(percentiles=[.01, .05, .5, .95, .99]))
print("janelas com menos de 30 pontos:", (n < 30).sum(), "de", len(n))