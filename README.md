# Segmentação semântica de trajetórias AIS para deteção de pesca

Projeto da unidade curricular **IA Centrada no Humano (MIACD, Universidade de
Coimbra)**. O objetivo é classificar automaticamente, ao longo de uma
trajetória AIS, os intervalos de **pesca** e de **navegação**, de forma robusta
e interpretável, como apoio à decisão de inspetores humanos
(*human-in-the-loop*).

A motivação é o combate à pesca ilegal, não declarada e não regulamentada
(IUU). O sistema proposto combina **janelas sobrepostas** e
**pós-processamento temporal** para estabilizar as fronteiras dos segmentos,
avaliando explicitamente o efeito de cada componente. O trabalho segue
princípios de HCAI: explicabilidade, confiança calibrada e decisão humana
final.

## Estado atual

A fase de **preparação de dados** está concluída. O próximo passo é o
**janelamento com sobreposição**; o plano completo, com o estado de cada
tarefa, está em [`docs/markdown/passos_futuros.md`](docs/markdown/passos_futuros.md).

| Fase | Estado |
| --- | --- |
| Limpeza do CSV e conversão para Parquet | Concluído |
| Divisão treino/teste/validação por trajetória | Concluído |
| Normalização e parâmetros guardados em JSON | Concluído |
| Janelamento com sobreposição | Próximo passo |
| Classificador de janelas | Por fazer |
| Pós-processamento temporal | Por fazer |
| Avaliação quantitativa e qualitativa | Por fazer |

## Estrutura do repositório

```text
.
├── src/                        Código do pipeline de dados
│   ├── limpar_csv.py           CSV → Parquet (colunas úteis, label binário)
│   ├── dividir_dataset.py      Divisão por trajetória completa
│   ├── preparar_dados.py       Divisão + t_rel + normalização ajustada ao treino
│   └── main.py                 Executa o pipeline de ponta a ponta
├── data/                       Entrada e saídas locais (ignoradas pelo Git)
├── docs/
│   ├── bibliografia/           Artigos e teses de referência
│   ├── latex/                  Proposta do projeto (fontes e PDF)
│   ├── markdown/               Notas e plano de trabalho
│   ├── FormattingGuidelines-IJCAI-ECAI-26/   Template oficial
│   └── enunciado_proposta_de_projeto.pdf
└── AGENTS.md                   Instruções para agentes/colaboradores
```

## Dados

Fonte: *Detailed Labelled Fishing Trajectories from AIS* (Kaggle), disponível
localmente em `data/128_fishing_trajs.csv` (~170 MB, não versionado).

- **123 trajetórias** e cerca de **1,03 milhões de pontos**. O `128` no nome
  do ficheiro vem da proposta original; o conjunto tem na realidade 123
  trajetórias, o que deve ser corrigido no relatório.
- Coordenadas `x`/`y` projetadas (metros), velocidade, variação de rumo,
  intervalo temporal e distância à costa por ponto.
- Rótulos originais em cinco classes, desequilibradas:

  | Rótulo original | Classe binária |
  | --- | --- |
  | `02-fishing`, `04-fishing` | `1` (pesca) |
  | `01-sailing`, `03-sailing`, `05-sailing` | `0` (navegação) |

O desequilíbrio natural é mantido (sem reamostragem nem pesos de classe).

### Ficheiros gerados em `data/`

| Ficheiro | Conteúdo |
| --- | --- |
| `ais_128.parquet` | CSV limpo com as colunas úteis e label binário |
| `treino_norm.parquet` | 86 trajetórias, normalizadas |
| `teste_norm.parquet` | 18 trajetórias, normalizadas |
| `validacao_norm.parquet` | 19 trajetórias, normalizadas |
| `normalizacao.json` | Parâmetros de normalização ajustados ao treino |

As trajetórias não devem ser usadas como dados de entrada sem regenerar estes
ficheiros: `data/` é ignorado pelo Git e todos os derivados são reprodutíveis
a partir do CSV.

## Pipeline de preparação

1. **Limpeza (`limpar_csv_para_parcelar`)** — lê apenas as colunas úteis,
   ordena por `(id, t)`, binariza o rótulo (`fishing` → 1, resto → 0),
   converte para tipos compactos e grava em Parquet.
2. **Divisão (`dividir_parquet`)** — divide por **trajetória completa**
   (`id`), garantindo que todos os pontos de uma trajetória ficam no mesmo
   conjunto. Proporção 70/15/15 com semente fixa (42).
3. **`t_rel` (`adicionar_t_rel`)** — segundos desde o primeiro ponto de cada
   trajetória, calculado a partir do `time_gap` bruto. Fica em bruto (não
   normalizado) para o janelamento e a deteção de gaps.
4. **Normalização (`ajustar_normalizacao` / `aplicar_normalizacao`)** — usa
   **mediana e IQR** por coluna, ajustados **só ao treino**, e aplica a mesma
   transformação aos três conjuntos. Os parâmetros ficam em JSON para
   reutilização na inferência.

Colunas finais dos conjuntos normalizados:
`id, t_rel, label, x, y, signed_turn, time_gap, euc_speed, distanceToShore`.

## Configuração do ambiente

Requer Python 3.12 ou superior (estas versões de numpy/pandas). O ambiente
local foi testado com Python 3.14.4, pandas 3.1.1, pyarrow 26.0.1 e numpy
2.5.5. O repositório não inclui `requirements.txt` nesta fase.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas pyarrow numpy
```

## Como executar

O CSV de origem tem de estar em `data/128_fishing_trajs.csv`. Executa a partir
da raiz do repositório, porque os caminhos são relativos a `data/`:

```bash
python src/main.py
```

Isto gera `data/ais_128.parquet`, `data/treino_norm.parquet`,
`data/teste_norm.parquet`, `data/validacao_norm.parquet` e
`data/normalizacao.json`.

Cada módulo também pode ser executado isoladamente:

```bash
python src/limpar_csv.py        # CSV → ais_128.parquet
python src/dividir_dataset.py   # ais_128.parquet → treino/teste/validação
python src/preparar_dados.py    # divisão + t_rel + normalização
```

## Decisões de desenho

- **Divisão por trajetória completa**, para evitar fuga de informação entre
  pontos da mesma trajetória.
- **Normalização com estatísticas do treino**, nunca do conjunto completo.
- **`t_rel` mantido em bruto**, separado das features normalizadas; o
  `time_gap` normalizado continua a ser a feature usada pelo modelo.
- **Sem reamostragem nem pesos de classe**, preservando o desequilíbrio real.
- **Semente fixa** na divisão, para resultados reprodutíveis.

## Documentação

- [`docs/markdown/passos_futuros.md`](docs/markdown/passos_futuros.md) — plano
  detalhado e estado de cada tarefa.
- [`docs/latex/proposta_pt.tex`](docs/latex/proposta_pt.tex) — proposta do
  projeto (problema, objetivos, abordagem e avaliação).
- `docs/bibliografia/` — artigos de referência (HMM para pesca, segmentação
  semântica de trajetórias, aprendizagem profunda com AIS, HCAI).
