# Passos futuros — Segmentação semântica de trajetórias AIS

Legenda: `[x]` feito · `[~]` parcialmente feito / por confirmar · `[ ]` por fazer

## Estado atual (17/11/2026)

Ficheiros já criados:
- `limpar_csv.py` → `limpar_csv_para_parcelar` (CSV → Parquet limpo, label binário, ordenado por `(id, t)`)
- `dividir_dataset.py` → `dividir_parquet` (divisão por trajetória completa)
- `preparar_dados.py` → `preparar_dados` (divisão + `t_rel` bruto + normalização mediana/IQR ajustada só ao treino + JSON de parâmetros)
- `criar_janelas.py` → `criar_janelas` (janelas por nº de pontos **ou** por duração, com sobreposição, corte em gaps opcional, máscara de padding) e `carregar_janelas`
- <span style="color:red">`gerar_janelas.py` → `gerar_janelas` (gera os três `.npz` finais, verifica a integridade e escreve `janelas_resumo.json`; adicionado a 17/11/2026)</span>
- <span style="color:green">`dataset_janelas.py` → `DatasetJanelas`, `criar_dataloader`, `BucketBatchSampler` e `perda_mascarada` (lê os `.npz`, respeita a `mascara`/`y=-1`, trata o `time_gap[0]` pós-gap e faz bucketing; adicionado a 17/11/2026)</span>
- <span style="color:green">`testar_dataset_janelas.py` → teste de formas, máscara, `time_gap[0]`, loss mascarada e packing com BiGRU (adicionado a 17/11/2026)</span>
- `verificar_divisao.py` → `verificar_divisao` (confirma ids sem sobreposição, total de pontos e trajetórias completas)
- `analisar_gaps.py` → `analisar_gaps` / `resumo_gaps` / `candidatos_fusao` (estudo dos gaps temporais e deteção de possíveis trajetórias fundidas)

Dataset: **123 trajetórias** (confirmado ao voltar a descarregar o dataset do Kaggle; a proposta original indicava 128, valor entretanto corrigido) → divisão 70/15/15 = 86 / 18 / 19.
Colunas finais: `id, t_rel, label, x, y, signed_turn, time_gap, euc_speed, distanceToShore`.

Decisões tomadas:
- Normalização mediana/IQR em todas as colunas contínuas, incluindo `time_gap` (sem `log1p`)
- `t_rel` (segundos desde o início da trajetória) mantido em bruto, à parte, para janelas e deteção de gaps
- Janelas a testar das duas formas: primeiro por nº de pontos, depois por duração temporal fixa
- Modo principal: **tempo** (30 min, sobreposição 50%), por dar contexto temporal homogéneo; modo pontos fica como alternativa/ablação
- `gap_max_s = 600` (10 min), `min_pontos = 30` e `T` sem limite; padding tratado no classificador
- <span style="color:green">`time_gap[0]` é zerado em memória apenas nas janelas que começam depois de um gap > 600 s (evita o valor ≈7 860 e o sinal artificial de “começa após gap”); os `.npz` ficam intactos</span>

## Mapa das secções

| Secção | Estado | O que se faz |
| --- | --- | --- |
| 0. Ambiente | Concluída | venv e bibliotecas de dados/ML |
| 1. Dados e verificação | Concluída | limpeza, divisão, qualidade e gaps |
| 2. Normalização | Quase concluída | normalização ajustada ao treino |
| 3. Janelamento | <span style="color:green">**Quase concluída** (3.1–3.3 feitos e 3.5 feito para GRU; faltam 3.4 e 3.6)</span> | janelas sobrepostas, gaps, padding, batching |
| 4. Baselines | Por começar | HMM, modelo clássico e aproximação a Wu et al. |
| 5. Classificador | Por começar | treinar a rede de janelas |
| 6. Pós-processamento | Por começar | agregar/suavizar previsões e estabilizar segmentos |
| 7. Avaliação quantitativa | Por começar | métricas por ponto/segmento e comparações |
| 8. Avaliação qualitativa e HCAI | Por começar | mapas, explicabilidade, confiança, dashboard |
| 9. Escrita e entrega | Por começar | documentar decisões, resultados e entregar |

---

## 0. Ambiente
- [x] Criar venv do projeto
- [x] Instalar só o necessário para dados (`pandas`, `pyarrow`)
- [x] Instalar bibliotecas de ML (PyTorch 2.15.0 **CPU**, scikit-learn 1.9.1, matplotlib, seaborn, tqdm); versões em `requirements.txt`
- [x] JupyterLab/ipykernel e notebook `src/pipeline.ipynb` (pipeline explicado passo a passo)

## 1. Dados e verificação
- [x] Conversão CSV → Parquet (colunas mantidas, label binário, ordenação)
- [x] Verificação de qualidade (nulos, duplicados, valores impossíveis)
- [x] Divisão por trajetória completa (treino/teste/validação)
- [x] Contagem de trajetórias confirmada: 123 (dataset descarregado de novo do Kaggle, para excluir erro de cópia)
- [x] Duração das trajetórias vista via `t_rel` (mediana ≈ 15 h, mín. ≈ 6 h, máx. ≈ 85 h)
- [x] Confirmado (`verificar_divisao`): nenhum `id` em mais de um conjunto, trajetórias completas, 1 026 279 pontos no total (= original), 775 521 de pesca preservados
- [x] Proporção de pesca por conjunto: treino 75,6% · teste 73,5% · validação 77,1% (pesca é a classe maioritária; divisão razoavelmente equilibrada)
- [x] Diferença 123 vs 128 esclarecida: o dataset tem mesmo 123 trajetórias (proposta corrigida)
- [x] Investigar o `time_gap` máximo (~13 h): é uma falha de transmissão, não uma fusão — 1,55 km em 13,1 h (0,12 km/h), label de pesca antes e depois; 0 gaps com velocidade implícita > 30 km/h
- [x] `main.py` reduzido a orquestrador; a lógica fica nos módulos (sem imports nem blocos repetidos)

## 2. Normalização
- [x] Função de ajuste (só treino) e de aplicação
- [x] Parâmetros guardados em JSON
- [x] `t_rel` bruto à parte
- [x] Verificar distribuições normalizadas (`describe`)

## 3. Janelamento com sobreposição  ← <span style="color:green">**quase concluído** (3.1–3.3 feitos e 3.5 feito para GRU em 17/11/2026; faltam 3.4 e 3.6)</span>

Objetivo: transformar as trajetórias normalizadas em janelas com sobreposição (por pontos ou por tempo), com máscara para padding, prontas para o classificador.

### 3.1. Decisões tomadas
- [x] Rótulo **por ponto** (não por janela)
- [x] Modo principal: **tempo**, 30 min, sobreposição 50% (comparar depois com 15/60 min)
- [x] Modo alternativo: **pontos**, 256, sobreposição 50% (testar 128/512)
- [x] Sem padding no modo pontos: só a última janela de cada trajetória é recuada para terminar no fim
- [x] No modo tempo o nº de pontos varia por janela: padding no fim + `mascara` (`y = -1` no padding)
- [x] `gap_max_s = 600` (10 min): nenhuma janela atravessa gaps maiores
- [x] `min_pontos = 30`: descarta janelas sem contexto suficiente
- [x] `T` sem limite (590 no treino); o padding (~69% de `X`) é tratado no treino, não limitando `T`
- [x] Corte por `id`: nenhuma janela atravessa trajetórias

### 3.2. Resultados no treino (86 trajetórias)
- [x] Modo pontos (256, 50%, sem gap): 5 473 janelas, `T = 256`; 453 janelas cobrem mais de 60 min
- [x] Modo pontos com `gap_max_s=600`: 5 436 janelas e 3 376 pontos sem janela (≈ 0,5%)
- [x] Modo tempo (30 min, 50%, `gap_max_s=600`, `min_pontos=2`): 7 916 janelas, `T = 590`, pontos por janela 6 / 173 / 590, 1 347 pontos sem janela (≈ 0,2%), padding ≈ 70%
- [x] `min_pontos=30`: 7 685 janelas e 2 617 pontos sem janela (≈ 0,4%); remove as 231 janelas com <30 pontos
- [x] Confirmado que limitar `T` quase não reduz o padding (T=494 → ≈64%, T=361 → ≈50%) e perde janelas densas

Sensibilidade de `min_pontos` (treino, 30 min, 50%, `gap_max_s=600`, `T = 590`):

| `min_pontos` | janelas | pontos sem janela | padding |
| --- | --- | --- | --- |
| 2 | 7 916 | 1 347 (0,19%) | 70,0% |
| 20 | 7 745 | 2 134 (0,30%) | 69,4% |
| **30** | **7 685** | **2 617 (0,37%)** | **69,2%** |
| 50 | 7 388 | 7 073 (1,00%) | 68,2% |

### 3.3. Gerar e guardar as janelas finais (treino/validação/teste)
Objetivo: produzir os `.npz` finais com os mesmos parâmetros e confirmar a cobertura em cada conjunto.

<span style="color:red">**Concluído em 17/11/2026** — `src/gerar_janelas.py` gera os três `.npz`, verifica a integridade e grava `data/janelas_resumo.json`:</span>

| Conjunto | Janelas | `T` | Pontos sem janela | Cobertura | Padding | Integridade |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Treino | 7 685 | 590 | 2 617 | 99,630% | 69,2% | OK |
| Validação | 1 949 | 531 | 79 | 99,954% | 66,6% | OK |
| Teste | 1 619 | 481 | 625 | 99,573% | 63,0% | OK |

- [x] Confirmar os parâmetros finais: `duracao_s=30*60`, `sobreposicao_pct=50`, `gap_max_s=600`, `min_pontos=30`
- [x] Criar `src/gerar_janelas.py` que gera e guarda `data/janelas_treino.npz`, `data/janelas_validacao.npz` e `data/janelas_teste.npz`
- [x] Registar por conjunto: `n_janelas`, `T`, `pontos_descartados` e cobertura
- [x] Confirmar que `T` pode variar entre conjuntos e que o modelo lida com isso (packing/máscara)
- [x] Verificar a integridade: metas dentro do `id` certo e nenhuma janela a atravessar um gap > 600 s

### 3.4. Política para pontos sem janela
Objetivo: decidir o que fazer aos pontos que ficam fora de todas as janelas.

- [ ] Excluir esses pontos das métricas (ficam sem previsão)
- [ ] Reportar a cobertura por conjunto (≈ 99,6% no treino com `min_pontos=30`)
- [ ] Documentar a decisão no relatório

### 3.5. Carregamento e batching (para o classificador)  ← <span style="color:green">**feito para GRU em 17/11/2026**</span>
Objetivo: alimentar o modelo com as janelas, ignorando o padding de forma correta.

- [x] Implementar Dataset/DataLoader a partir do `.npz`, respeitando a `mascara`
- [x] Ignorar o padding na loss (`y = -1`)
- [~] GRU: `pack_padded_sequence`; CNN: convoluções/pooling mascarados
- [x] Agrupar janelas por tamanho (bucketing) para reduzir o padding por batch
- [x] Testar um batch pequeno e validar formas, máscara e loss

<span style="color:green">Implementado em `src/dataset_janelas.py` e testado por `src/testar_dataset_janelas.py`; `main.py` corre o teste no fim e o notebook tem a secção 5. No treino: 7 685 janelas, `T=590`, padding por batch 3,9% com bucketing vs 62,5% sem; `time_gap[0]=0` em 34 janelas pós-gap; loss mascarada e `pack_padded_sequence` com BiGRU OK. A parte CNN continua por fazer.</span>

### 3.6. Ablações e variantes a testar (mais tarde)
- [ ] Sobreposição: 0%, 25%, 50%, 75%
- [ ] Duração: 15, 30 e 60 min
- [ ] Modo pontos (128/256/512) vs modo tempo
- [ ] Sem `x` e `y` vs com todas as features (para ver se o modelo decora zonas geográficas)

## 4. Baselines
Objetivo: ter referências simples e interpretáveis para comparar com a rede.

- [ ] HMM simples sobre `euc_speed` e `signed_turn` (Peel e Good, 2011)
- [ ] Modelo clássico sobre *features* agregadas por janela (ex.: gradient boosting)
- [ ] Reimplementar ou aproximar Wu et al. (2022)

## 5. Classificador de janelas
Objetivo: treinar o modelo principal que classifica cada ponto de cada janela.

- [ ] Escolher o modelo principal (candidatos: 1D-CNN, BiGRU, com atenção opcional)
- [ ] Definir função de custo, otimizador e hiperparâmetros (só treino e validação)
- [ ] Desequilíbrio de classes: a proposta mantém o natural, sem reamostragem nem pesos
- [ ] Treinar e guardar o melhor modelo
- [ ] Guardar o `normalizacao.json` junto com o modelo final (necessário para a inferência e o dashboard)

## 6. Pós-processamento temporal
Objetivo: combinar as previsões das janelas sobrepostas e gerar segmentos contíguos e estáveis.

- [ ] Agregação das previsões de janelas sobrepostas (votação ponderada)
- [ ] Suavização (HMM ou votação por vizinhança)
- [ ] Segmentos contíguos e estáveis
- [ ] Estudo de ablação com quatro variantes:
  1. sem sobreposição nem pós-processamento
  2. só sobreposição
  3. só pós-processamento
  4. ambos (método proposto)
- [ ] Robustez face à sobreposição (0, 25, 50, 75%) e à regularização temporal

## 7. Avaliação quantitativa
Objetivo: medir o desempenho e comparar com os baselines.

- [ ] Métricas por ponto e por segmento: precisão, sensibilidade, F1, IoU
- [ ] Estabilidade: fragmentação e erro de fronteira
- [ ] Comparação com os baselines
- [ ] Considerar validação cruzada por trajetória ou várias divisões (o teste tem só ~19 trajetórias)
- [ ] Responder às RQ1, RQ2 e RQ3

## 8. Avaliação qualitativa e HCAI
Objetivo: mostrar os resultados e sustentar a decisão humana (human-on-the-loop).

- [ ] Mapas com segmentos preditos sobrepostos à verdade de referência
- [ ] Casos de sucesso e falha
- [ ] Explicabilidade com SHAP
- [ ] Confiança calibrada (Guo et al., 2017) e definição de como a confiança por segmento é obtida
- [ ] Dashboard de prova de conceito

## 9. Escrita e entrega
Objetivo: documentar o trabalho e preparar a entrega.

- [x] Corrigir "128" para "123" na proposta/relatório (proposta corrigida, alterações a vermelho)
- [ ] Documentar decisões de desenho (janela, rótulo, IDs com o mesmo prefixo, normalização, `t_rel`)
- [ ] Reportar a distribuição de classes por conjunto
- [x] `pip freeze > requirements.txt` (regenerar se as dependências mudarem)
- [ ] Redigir resultados e discussão

---

## Notas e riscos
- IDs com o mesmo prefixo são tratados como independentes; justificar ou testar o impacto de possível fuga de informação.
- Normalização, imputação e limiares só com estatísticas do treino.
- A pesca é a classe maioritária (~75% dos pontos): a *accuracy* engana; reportar métricas das duas classes e comparar com o baseline trivial "prever sempre pesca".
- Se o deep learning não superar o baseline simples, isso também é um resultado válido.
