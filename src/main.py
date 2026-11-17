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