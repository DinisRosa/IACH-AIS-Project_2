"""Executa o pipeline de dados de ponta a ponta.

Uso:
    python src/main.py
    python -m src.main

Gera, em data/: ais_123.parquet, treino_norm.parquet, teste_norm.parquet,
validacao_norm.parquet, normalizacao.json, janelas_treino.npz,
janelas_validacao.npz, janelas_teste.npz e janelas_resumo.json. No fim, corre
o teste de Dataset/DataLoader, a investigação de qualidade e os baselines
ponto a ponto definidos nos módulos correspondentes.

Para uma versão explicada passo a passo, ver src/pipeline.ipynb.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from .baselines_ponto import executar_baselines
    from .gerar_janelas import gerar_janelas
    from .investigar_qualidade import investigar_qualidade
    from .limpar_csv import limpar_csv_para_parcelar
    from .preparar_dados import preparar_dados
    from .testar_dataset_janelas import main as testar_dataset_janelas
except ImportError:
    from baselines_ponto import executar_baselines
    from gerar_janelas import gerar_janelas
    from investigar_qualidade import investigar_qualidade
    from limpar_csv import limpar_csv_para_parcelar
    from preparar_dados import preparar_dados
    from testar_dataset_janelas import main as testar_dataset_janelas


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
    testar_dataset_janelas()
    investigar_qualidade()
    executar_baselines()


if __name__ == "__main__":
    main()
