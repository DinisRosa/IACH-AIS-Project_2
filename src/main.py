"""Executa o pipeline de dados de ponta a ponta.

Uso:
    python src/main.py

Gera, em data/: ais_123.parquet, treino_norm.parquet, teste_norm.parquet,
validacao_norm.parquet, normalizacao.json, janelas_treino.npz,
janelas_validacao.npz, janelas_teste.npz e janelas_resumo.json.

Para uma versão explicada passo a passo, ver src/pipeline.ipynb.
"""

from gerar_janelas import gerar_janelas
from limpar_csv import limpar_csv_para_parcelar
from preparar_dados import preparar_dados


def main():
    limpar_csv_para_parcelar(
        "data/123_fishing_trajs.csv",
        "data/ais_123.parquet",
    )
    preparar_dados(
        "data/ais_123.parquet",
        "data/treino_norm.parquet",
        "data/teste_norm.parquet",
        "data/validacao_norm.parquet",
        70, 15, 15,
    )
    gerar_janelas()


if __name__ == "__main__":
    main()
