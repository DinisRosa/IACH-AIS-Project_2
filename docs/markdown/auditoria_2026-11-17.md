# Auditoria ao estado do projeto — 17/11/2026

Âmbito: verificar, no repositório, se o que está marcado como feito em
`docs/markdown/passos_futuros.md` está realmente feito, se o que está marcado
como pendente ainda não foi feito e se o que está marcado como parcial ou por
confirmar está efetivamente nesse estado.

Foram lidos o `README.md`, o plano `docs/markdown/passos_futuros.md`, todos os
módulos de `src/`, o notebook `src/pipeline.ipynb`, `requirements.txt`, a
proposta LaTeX, a bibliografia e os artefactos em `data/`. Sempre que possível,
as afirmações foram confirmadas executando o código e medindo os dados.

> **Nota:** não foram alterados ficheiros de código, dados ou configuração;
> foi apenas criado este documento. O notebook foi executado para
> `/tmp/opencode/pipeline_audit.ipynb`, os dados derivados em `data/` foram
> regenerados (estão ignorados pelo Git) e a LaTeX foi compilada em modo de
> teste, com restauro do PDF e limpeza dos artefactos. Antes da criação deste
> documento, o repositório estava com `git status` limpo.

---

## 1. Resumo executivo

- A generalidade dos itens `[x]` está feita e os números de 3.2 do plano
  (`passos_futuros.md:81-95`) batem ao decimal.
- Foram encontrados **três rótulos desatualizados**:
  1. a secção 2 está como “Quase concluída” (`passos_futuros.md:31`), mas os
     quatro itens estão `[x]` e a normalização está verificada;
  2. a secção 9 está como “Por começar” (`passos_futuros.md:38`), mas já tem
     dois `[x]` e documentação parcial;
  3. o README afirma que “a preparação e a verificação dos dados estão
     concluídas” (`README.md:19-21`), mas a verificação de qualidade tem
     ressalvas (ver §3.3).
- Dois itens `[x]` são apenas parciais:
  1. “Verificação de qualidade (nulos, duplicados, valores impossíveis)”
     (`passos_futuros.md:50`) — não há script reproduzível e existem outliers
     de velocidade e um desalinhamento temporal não documentados;
  2. “`pip freeze > requirements.txt`” (`passos_futuros.md:181`) — o ficheiro
     tem 31 pacotes, mas o ambiente tem 115; é uma lista curada, não um
     `pip freeze` literal.
- A afirmação “0 gaps com velocidade implícita >30 km/h”
  (`passos_futuros.md:57`) é verdadeira apenas para os gaps >10 min. Há 636
  intervalos curtos com velocidade implícita >30 km/h e 63 pontos com
  `euc_speed` >30 nós.
- Tudo o que está `[ ]` nas secções 3.3 a 9 está de facto por fazer, com
  pequenas exceções de documentação/cobertura já parcialmente produzida
  (ver §8).
- O notebook executa de ponta a ponta; a LaTeX compila; os 31 pacotes
  pinados estão instalados nas versões pedidas.

---

## 2. Ambiente e execução

Verificado com `./IACH_AIS_venv/bin/python`:

| Item | Resultado |
| --- | --- |
| Python | 3.14.4 |
| PyTorch | 2.15.0+cpu; CUDA indisponível |
| scikit-learn | 1.9.1 |
| pandas | 3.1.1 |
| numpy | 2.5.5 |
| pyarrow | 26.0.1 |
| matplotlib | 3.11.2 |
| seaborn | 0.13.2 |
| tqdm | 4.70.1 |
| JupyterLab | 4.6.6 |
| ipykernel | 7.4.0 |

O notebook `src/pipeline.ipynb` foi executado com:

```bash
./IACH_AIS_venv/bin/jupyter nbconvert --to notebook --execute src/pipeline.ipynb \
  --output /tmp/opencode/pipeline_audit.ipynb \
  --ExecutePreprocessor.timeout=600 --ExecutePreprocessor.kernel_name=python3
```

Resultado: exit code 0. As células de verificação da divisão, distribuições,
gaps e janelamento produziram os valores esperados (ver abaixo).

Conclusão: secção 0 do plano confirmada.

---

## 3. Dados e qualidade

### 3.1. Estrutura e conversão

CSV de origem `data/123_fishing_trajs.csv`:

- 1 026 279 linhas, 13 colunas;
- 123 IDs de trajetória;
- 0 nulos em todas as colunas;
- 0 duplicados exatos;
- 0 duplicados `(id, t)`.

Colunas: `id, t, longitude, latitude, x, y, signed_turn, bearing, time_gap,
distance_gap, euc_speed, distanceToShore, label`.

Rótulos originais (5 classes):

| Rótulo | Pontos |
| --- | ---: |
| `02-fishing` | 764 388 |
| `04-fishing` | 11 133 |
| `03-sailing` | 129 645 |
| `01-sailing` | 120 589 |
| `05-sailing` | 524 |

Binário: 775 521 pesca (`1`) e 250 758 navegação (`0`).

A conversão para `data/ais_123.parquet` foi verificada:

- 1 026 279 linhas, 8 colunas;
- 123 IDs;
- a sequência de IDs e de rótulos coincide exatamente com o CSV ordenado por
  `(id, t)`;
- a binarização `fishing → 1` está correta.

Gamas principais:

| Coluna | Mínimo | Máximo |
| --- | ---: | ---: |
| `longitude` | 6,647597 | 12,340183 |
| `latitude` | 54,618528 | 58,042425 |
| `x` | 353 381 | 707 436 |
| `y` | 6 053 730 | 6 434 080 |
| `signed_turn` | -180 | 180 |
| `bearing` | 0 | 359,954 |
| `time_gap` | 1 s | 47 172 s (13,10 h) |
| `distance_gap` | 0,059 m | 19 257,43 m |
| `euc_speed` | 0,000544 | 90,702 |
| `distanceToShore` | 0 m | 90 455,23 m |

`time_gap` não tem zeros nem valores negativos.

### 3.2. Unidades de `euc_speed`

Os primeiros registos mostram que `euc_speed` está em **nós**:

- `distance_gap = 2,979797 m`, `time_gap = 4 s`;
- velocidade = 0,7449 m/s = 2,6818 km/h = 1,4481 nós;
- `euc_speed = 1,448065` no mesmo registo.

Outros valores observados:

- `time_gap == 1 s`: 10 676 pontos;
- `signed_turn == 0`: 1 518 pontos;
- `distanceToShore == 0`: 1 918 pontos;
- `time_gap` do primeiro ponto de cada ID: mínimo 2 s, mediana 9 s, máximo
  901 s; não afeta `t_rel`, porque o cálculo subtrai o primeiro valor.

### 3.3. Anomalias e outliers

Apesar de os testes básicos passarem, existem anomalias que não estão
documentadas no plano:

1. **Velocidades extremas em `euc_speed`**
   - 63 pontos com `euc_speed > 30` nós;
   - 5 pontos com `> 50` nós;
   - 1 ponto com `90,702` nós (≈168 km/h);
   - os 63 pontos concentram-se em 6 IDs: `220099000-3` (48),
     `220356000-3` (7), `220356000-2` (4), `220137000-2` (2),
     `219028021-2` (1) e `219709000-2` (1).

2. **Velocidade implícita em intervalos curtos**
   - 636 intervalos consecutivos com `distance_gap / time_gap > 30 km/h`;
   - máximo de 167,98 km/h;
   - estes casos **não** são analisados por `candidatos_fusao`, porque
     `analisar_gaps` só constrói a tabela para `time_gap > 600 s`
     (`src/analisar_gaps.py:36`) e `candidatos_fusao` filtra depois essa
     tabela (`src/analisar_gaps.py:62-69`).

3. **Desalinhamento entre `t` e `time_gap`**
   - um único ponto com diferença >1 s;
   - ID `219429000-2`, instante `2021-11-15 17:17:11`;
   - `t` avança 30 s, mas `time_gap = 10 s` (diferença de 20 s);
   - `t_rel` é calculado a partir de `time_gap`, pelo que este troço fica
     desviado 20 s em relação aos timestamps originais.

4. **Impacto na normalização**
   - `time_gap` bruto máximo 47 172 s, mediana 10 s e IQR 6 s;
   - valor normalizado máximo ≈ 7 860 (z-score);
   - `euc_speed` normalizado máximo ≈ 19,2;
   - não há clipping, winsorização nem remoção de outliers.

Conclusão: a verificação de qualidade básica (nulos, duplicados, gamas
negativas) passa, mas a parte de “valores impossíveis” **não está demonstrada
nem documentada**. O `[x]` de `passos_futuros.md:50` deve passar a `[~]`, ou
então deve ser acrescentada uma decisão explícita sobre estes outliers.

### 3.4. Durações

Calculadas a partir de `t_rel` por trajetória:

| Conjunto | Mínimo | Mediana | Máximo |
| --- | ---: | ---: | ---: |
| Treino | 5,986 h | 15,398 h | 85,098 h |
| Teste | 10,396 h | 16,271 h | 65,968 h |
| Validação | 7,700 h | 17,104 h | 70,013 h |
| Global | 5,986 h | 15,763 h | 85,098 h |

Os valores do plano (“mediana ≈15 h, mín. ≈6 h, máx. ≈85 h”) estão corretos.

### 3.5. IDs com prefixo comum

- 29 prefixos aparecem em mais de um ID;
- 68 IDs estão envolvidos;
- exemplos: `219025740` (5 IDs), `219025739` (4), `211477000` (3),
  `219004128` (3), `220006000` (3), `220349000` (3), entre outros.

A divisão é feita por ID completo, pelo que IDs com o mesmo prefixo podem
calhar em conjuntos diferentes. O risco está identificado no plano e na LaTeX,
mas não foi testado nem quantificado.

---

## 4. Divisão treino/teste/validação

`verificar_divisao` devolve `ok=True`:

- nenhum ID em mais de um conjunto;
- todos os IDs do original estão nos conjuntos e não há IDs a mais;
- total de pontos igual ao original;
- todas as trajetórias completas;
- pontos de pesca preservados.

| Conjunto | IDs | Pontos | Pesca |
| --- | ---: | ---: | ---: |
| Treino | 86 | 706 522 | 534 202 (75,61%) |
| Teste | 18 | 146 225 | 107 485 (73,51%) |
| Validação | 19 | 173 532 | 133 834 (77,12%) |
| Total | 123 | 1 026 279 | 775 521 |

A semente 42 está no código (`src/dividir_dataset.py:9`), a proporção é
70/15/15 e a validação fica com o resto. Confirmado.

---

## 5. Normalização

O JSON `data/normalizacao.json` foi comparado com as estatísticas dos dados
brutos de treino:

| Feature | Mediana JSON | Mediana bruta | Escala JSON | IQR bruto |
| --- | ---: | ---: | ---: | ---: |
| `x` | 544 820,6875 | 544 820,6875 | 200 743,3125 | 200 743,3125 |
| `y` | 6 337 198,75 | 6 337 198,75 | 163 109,5 | 163 109,5 |
| `signed_turn` | 1,4060702e-05 | 1,4060702e-05 | 5,3265676 | 5,3265676 |
| `time_gap` | 10 | 10 | 6 | 6 |
| `euc_speed` | 2,7223349 | 2,7223349 | 2,3813630 | 2,3813630 |
| `distanceToShore` | 20 505,171875 | 20 505,171875 | 31 691,7585 | 31 691,7585 |

- A mediana e o IQR do JSON coincidem exatamente com o treino bruto.
- O treino normalizado tem mediana 0 e IQR 1 em todas as features.
- Aplicar o JSON aos dados brutos de teste e validação reproduz exatamente os
  Parquet normalizados (diferença máxima 0,0).
- `t_rel` não é normalizado: começa em 0 em todas as trajetórias e vai até
  306 353 s no treino.
- Não há `log1p`; é mediana/IQR puro, como documentado.

Conclusão: secção 2 confirmada. O rótulo “Quase concluída” da tabela de
secções (`passos_futuros.md:31`) está desatualizado; deve ser “Concluída”.

---

## 6. Gaps

- 174 gaps >10 min (600 s) no total;
- 22 gaps >1 h;
- 121 gaps >10 min no treino;
- maior gap: 13,103 h no ID `219012671-1`, com 1,555 km percorridos e
  0,119 km/h; rótulo de pesca antes e depois;
- entre os gaps >10 min, 0 têm velocidade implícita >30 km/h.

A conclusão específica do maior gap está correta. A afirmação “0 gaps com
velocidade implícita >30 km/h” deve ser lida como “0 dos 174 gaps >10 min”;
não cobre os 636 intervalos curtos referidos em §3.3.

---

## 7. Janelamento

### 7.1. Decisões e implementação

Verificado em `src/criar_janelas.py`:

- rótulo por ponto;
- modo principal por tempo (`duracao_s=1800`, 50% de sobreposição);
- modo alternativo por pontos (`n_pontos=256`, 50%);
- modo pontos sem padding, com a última janela recuada até ao fim;
- modo tempo com padding no fim, `mascara=False` e `y=-1`;
- `gap_max_s=600`;
- `min_pontos=30`;
- `T` não limitado, igual ao maior número de pontos de uma janela;
- corte por ID;
- suporte a `output_path` e `carregar_janelas`.

Todas estas decisões estão implementadas. A integridade foi verificada:

- todas as janelas de tempo têm `n_pontos >= 30`;
- `mascara.sum() == n_pontos` em todas as janelas;
- todo o padding tem `y=-1` e `X=0`;
- `X`, `y` e `meta` coincidem com os dados de origem nas posições indicadas;
- nenhuma janela atravessa um gap >600 s (0 casos no treino);
- `t_ini`/`t_fim` são coerentes com `t_rel`;
- `fim <= len(id)`;
- `savez`/`carregar_janelas` faz round-trip perfeito.

### 7.2. Resultados no treino

Todos os valores do plano foram reproduzidos:

| Configuração | Janelas | T | Pontos sem janela | % do treino | Padding |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pontos 256, 50%, sem gap | 5 473 | 256 | 0 | 0,000% | 0,00% |
| Pontos 256, 50%, gap 600 | 5 436 | 256 | 3 376 | 0,478% | 0,00% |
| Tempo 1800, 50%, gap 600, min 2 | 7 916 | 590 | 1 347 | 0,191% | 70,01% |
| Tempo 1800, 50%, gap 600, min 20 | 7 745 | 590 | 2 134 | 0,302% | 69,39% |
| Tempo 1800, 50%, gap 600, min 30 | 7 685 | 590 | 2 617 | 0,370% | 69,19% |
| Tempo 1800, 50%, gap 600, min 50 | 7 388 | 590 | 7 073 | 1,001% | 68,23% |

Outros valores confirmados:

- modo pontos sem gap: 453 janelas cobrem mais de 60 min;
- modo tempo `min_pontos=2`: pontos por janela 6 / 173 / 590;
- `min_pontos=30`: remove 231 janelas face a `min_pontos=2`;
- limitar T: T=494 → 63,28% de padding, T=361 → 50,82% (o plano diz ≈64% e
  ≈50%); perdem-se 79 janelas acima de 494 pontos e 395 acima de 361.

### 7.3. Validação e teste (calculado nesta auditoria)

Ainda não está registado no plano/repositório, mas foi calculado com os mesmos
parâmetros:

| Conjunto | Janelas | T | Pontos sem janela | Cobertura | Padding |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validação | 1 949 | 531 | 79 | 99,954% | 66,63% |
| Teste | 1 619 | 481 | 625 | 99,573% | 63,01% |

Isto confirma que `T` varia entre conjuntos (590 no treino, 531 na validação,
481 no teste) e que o modelo terá de lidar com isso. Ainda não existe
`src/gerar_janelas.py` nem os `.npz` finais.

---

## 8. Estado dos itens do plano

### 8.1. Tabela de secções

| Secção | Rótulo atual | Veredito |
| --- | --- | --- |
| 0. Ambiente | Concluída | Confirmado |
| 1. Dados e verificação | Concluída | Confirmado, com ressalva na qualidade (§3.3) |
| 2. Normalização | Quase concluída | **Desatualizado**: está concluída |
| 3. Janelamento | Em curso | Confirmado: 3.1/3.2 feitos, 3.3–3.6 não |
| 4. Baselines | Por começar | Confirmado |
| 5. Classificador | Por começar | Confirmado |
| 6. Pós-processamento | Por começar | Confirmado |
| 7. Avaliação quantitativa | Por começar | Confirmado |
| 8. Avaliação qualitativa/HCAI | Por começar | Confirmado |
| 9. Escrita e entrega | Por começar | **Desatualizado**: já está em curso |

### 8.2. Itens `[x]` confirmados

- Secção 0: venv, bibliotecas, JupyterLab/ipykernel e notebook.
- Secção 1: conversão, contagem de 123, duração, verificação da divisão,
  proporções de pesca, esclarecimento 123 vs 128, investigação do maior gap,
  `main.py` como orquestrador.
- Secção 2: ajuste/aplicação da normalização, JSON, `t_rel` bruto e
  `describe`.
- Secção 3.1: todas as decisões de janelamento.
- Secção 3.2: todos os resultados e a tabela de sensibilidade.
- Secção 9: correção de 128→123 (fonte e PDF PT) e, com ressalva, requirements.

### 8.3. Itens `[x]` parciais ou por confirmar

- `passos_futuros.md:50` — “Verificação de qualidade (nulos, duplicados,
  valores impossíveis)”: básicos OK, outliers e desalinhamento temporal não
  documentados; não há script reproduzível.
- `passos_futuros.md:57` — “0 gaps com velocidade implícita >30 km/h”:
  verdadeiro só para gaps >10 min; ver §3.3.
- `passos_futuros.md:181` — “`pip freeze > requirements.txt`”: lista curada de
  31 pacotes, não o freeze completo (115 pacotes instalados).
- `passos_futuros.md:64` — “Verificar distribuições normalizadas
  (`describe`)”: a célula existe e executa, mas o notebook commitado não
  guarda outputs; a verificação é reproduzível, não está registada no Git.

### 8.4. Itens `[ ]` já parcialmente feitos

- `passos_futuros.md:100` — confirmar parâmetros finais: os parâmetros já estão
  decididos e documentados; falta formalizá-los no gerador.
- `passos_futuros.md:104` — verificar integridade: a propriedade é válida no
  treino (ver §7.1), mas não há script/registo.
- `passos_futuros.md:110` — reportar cobertura por conjunto: o treino já está
  reportado; validação/teste foram calculados nesta auditoria (§7.3), mas não
  estão no repositório.
- `passos_futuros.md:179` — documentar decisões de desenho: o conteúdo existe,
  mas disperso entre README, plano e LaTeX.
- `passos_futuros.md:180` — reportar distribuição de classes por conjunto: já
  está no plano e no output de `verificar_divisao`, mas não num relatório
  final.

### 8.5. Itens `[ ]` confirmados como não feitos

- **3.3**: `src/gerar_janelas.py` não existe; `data/janelas_treino.npz`,
  `janelas_validacao.npz` e `janelas_teste.npz` não existem; não há registo
  por conjunto nem verificação formal de T.
- **3.4**: política para pontos sem janela não está decidida/documentada num
  relatório.
- **3.5**: não há `Dataset`/`DataLoader`, loss com `y=-1`,
  `pack_padded_sequence`, convoluções/pooling mascarados, bucketing nem teste
  de batch.
- **3.6**: não há ablações de sobreposição (0/25/50/75%), duração
  (15/30/60 min), pontos (128/256/512) vs tempo, nem sem `x`/`y`.
- **4**: não há HMM, modelo clássico nem aproximação a Wu et al.
- **5**: não há escolha de modelo, função de custo, otimizador,
  hiperparâmetros, treino, modelo guardado nem `normalizacao.json` associado
  ao modelo.
- **6**: não há agregação de previsões, suavização, segmentos contíguos,
  ablação das quatro variantes nem robustez à sobreposição.
- **7**: não há métricas por ponto/segmento, estabilidade, comparação com
  baselines, validação cruzada nem resposta às RQ1–RQ3.
- **8**: não há mapas, casos de sucesso/falha, SHAP, calibração nem dashboard.
- **9**: não há resultados e discussão redigidos.

---

## 9. LaTeX e bibliografia

- `docs/latex/proposta_pt.tex` contém `123` e `human-on-the-loop` a vermelho
  (linhas 64, 84, 125 e 132).
- A fonte não contém `128` nem `human-in-the-loop`.
- O PDF `docs/latex/proposta_pt.pdf` contém `123` e `human-on-the-loop`.
- O PDF antigo `docs/latex/proposta_IAHC_DINIS_ROSA.pdf` mantém
  `128`/`human-in-the-loop`; é um artefacto histórico intencional, explicado no
  README da branch `latex`, mas não no README da `main`.
- A compilação da versão PT (na `main`) termina sem erros; apenas avisos
  benignos de `caption`, `lineno` e uma referência a reexecutar.
- O `.bib` tem 21 entradas e todas as 16 chaves citadas no `.tex` existem.
- A pasta `docs/bibliografia/` tem 16 PDFs; não tem PDFs para
  `shneiderman2020`, `guo2017`, `lundberg2017` e `agnew2009`, apesar de essas
  entradas existirem no `.bib` e de o README anunciar HCAI/calibração.
- A LaTeX diz “cada janela é classificada como pesca ou navegação”
  (`proposta_pt.tex:99`), mas a implementação é **rótulo por ponto** dentro da
  janela. Convém clarificar a redação.

---

## 10. Requirements e reprodutibilidade

- `requirements.txt` tem 31 pacotes pinados.
- Os 31 estão instalados nas versões pedidas.
- `pip freeze` tem 115 pacotes.
- O ficheiro não é um `pip freeze` literal: é uma lista curada (inclui
  `--extra-index-url` e não inclui muitas dependências transitivas do
  JupyterLab).
- Consequência: `pip install -r requirements.txt` instala as versões de topo,
  mas pode resolver versões diferentes para as dependências transitivas.
  Recomenda-se separar `requirements.txt` (topo) de um `requirements.lock`
  (freeze completo).

---

## 11. Inconsistências menores e riscos de código

- `src/analisar_gaps.py:27` ordena apenas por `id`; assume que o Parquet já
  está ordenado por `t` dentro de cada ID. Hoje está, mas é frágil.
- `src/limpar_csv.py:50` usa `manter_t=True` quando executado isoladamente,
  enquanto `src/main.py:17-20` e o notebook usam o default `False`. Correr o
  módulo isoladamente acrescenta a coluna `t`, que não aparece na lista de
  “colunas finais” do README.
- `src/dividir_dataset.py:61-64` escreve `treino.parquet`, `teste.parquet` e
  `validacao.parquet` quando executado isoladamente; são ficheiros
  intermédios que não estão na tabela de ficheiros gerados do README.
- `AGENTS.md:17-20` ainda descreve `code` e `latex` como snapshots históricos;
  depois das últimas alterações já são snapshots atuais.
- O notebook commitado não tem outputs; a verificação é reproduzível, mas não
  fica registada no Git.
- Não existe suite de testes no repositório; a validação é feita por scripts e
  pelo notebook.
- O risco de fuga de informação entre IDs com o mesmo prefixo continua aberto;
  está identificado, mas não testado.

---

## 12. Recomendações

1. Atualizar `passos_futuros.md`:
   - secção 2: “Quase concluída” → “Concluída”;
   - secção 9: “Por começar” → “Em curso”;
   - qualidade (`:50`) e `pip freeze` (`:181`) → `[~]`;
   - documentação, distribuição, cobertura, parâmetros e integridade →
     `[~]`/`[x]` conforme o critério adotado.
2. Acrescentar uma nota/decisão sobre outliers:
   - 63 pontos com `euc_speed >30` nós, 1 com 90,7 nós;
   - 636 intervalos curtos com velocidade implícita >30 km/h;
   - `time_gap` normalizado máximo ≈7 860 e `euc_speed` ≈19,2;
   - decidir entre manter, clipar/winsorizar ou remover, antes do treino.
3. Corrigir/registar o desalinhamento do `219429000-2` (`t` vs `time_gap`,
   diferença de 20 s).
4. Clarificar a frase “0 gaps com velocidade implícita >30 km/h” para
   “0 dos 174 gaps >10 min”, e reportar separadamente os intervalos curtos.
5. Criar `src/gerar_janelas.py`, persistir os três `.npz` e registar
   `n_janelas`, `T`, `pontos_descartados`, cobertura e padding por conjunto
   (treino: 7 685/590; validação: 1 949/531/99,954%; teste:
   1 619/481/99,573%).
6. Separar `requirements.txt` curado de um `requirements.lock` gerado por
   `pip freeze`.
7. Atualizar `AGENTS.md` e a redação da LaTeX sobre rótulo por ponto vs janela.
8. Considerar agrupar ou testar o impacto dos IDs com o mesmo prefixo.
9. Adicionar uma verificação de qualidade reproduzível (script) que cubra
   nulos, duplicados, `time_gap`, gamas e outliers de velocidade, e guardar o
   resultado no repositório.

## 13. Limitações da auditoria

- Não é possível provar, apenas a partir do repositório, que o dataset foi
  novamente descarregado do Kaggle nem que execuções históricas ocorreram
  exatamente como descrito; foi verificado o estado atual e a reprodutibilidade
  do pipeline.
- O notebook commitado não guarda outputs; esta auditoria executou-o agora.
- Não existe suite de testes automáticos; as verificações foram feitas com
  scripts ad hoc e inspeção dos artefactos.
- A qualidade matemática/estatística das escolhas (IQR, 30 min, 50%,
  `min_pontos=30`) não foi avaliada; apenas a implementação e os números
  reportados.

---

## Anexo A — Comandos de verificação usados

```bash
# ambiente
./IACH_AIS_venv/bin/python -V
./IACH_AIS_venv/bin/pip freeze
./IACH_AIS_venv/bin/python -m compileall -q src

# notebook
./IACH_AIS_venv/bin/jupyter nbconvert --to notebook --execute src/pipeline.ipynb \
  --output /tmp/opencode/pipeline_audit.ipynb \
  --ExecutePreprocessor.timeout=600 --ExecutePreprocessor.kernel_name=python3

# divisão, normalização e gaps
./IACH_AIS_venv/bin/python src/verificar_divisao.py
./IACH_AIS_venv/bin/python src/analisar_gaps.py

# janelamento e integridade
./IACH_AIS_venv/bin/python src/criar_janelas.py

# LaTeX (na main, a partir de docs/latex)
pdflatex proposta_pt
bibtex proposta_pt
pdflatex proposta_pt
pdflatex proposta_pt
```

## Anexo B — Números-chave

| Métrica | Valor |
| --- | ---: |
| Trajetórias | 123 |
| Pontos totais | 1 026 279 |
| Pontos de pesca | 775 521 |
| Treino / teste / validação (IDs) | 86 / 18 / 19 |
| Pontos treino / teste / validação | 706 522 / 146 225 / 173 532 |
| Pesca treino / teste / validação | 75,61% / 73,51% / 77,12% |
| Gaps >10 min | 174 |
| Gaps >10 min no treino | 121 |
| Maior gap | 13,103 h (`219012671-1`) |
| Janelas tempo `min_pontos=30` | 7 685 |
| T treino / validação / teste | 590 / 531 / 481 |
| Pontos sem janela (treino) | 2 617 (0,370%) |
| Padding treino | 69,19% |
| Cobertura treino | 99,63% |
| Cobertura validação / teste | 99,954% / 99,573% |
| Pacotes pinados / instalados | 31 / 115 |
