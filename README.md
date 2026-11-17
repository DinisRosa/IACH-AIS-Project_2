# Code — snapshot seguro

Cópia de segurança do código do pipeline de dados. Tudo o que está em `Code/`
foi executado e verificado (limpeza do CSV, divisão, normalização, janelamento,
análise de gaps e verificação da divisão) e é seguro de usar.

- `Code/` — módulos do pipeline e `main.py`.
- `Code/pipeline.ipynb` — o mesmo pipeline explicado passo a passo.
- `requirements.txt` — dependências do ambiente.
- `data/.gitkeep` — mantém a pasta `data/` (os dados não são versionados).

## Executar

A partir da raiz do repositório:

```bash
python Code/main.py
```

O CSV original tem de estar em `data/123_fishing_trajs.csv`; o pipeline gera
os Parquet e o `normalizacao.json` em `data/`. Para a versão explicada:

```bash
jupyter lab Code/pipeline.ipynb
```

A documentação completa e o plano de trabalho estão no branch `main`.
