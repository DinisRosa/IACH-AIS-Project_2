# Auditoria final e plano de ação — IACH AIS

**Data:** 20/11/2026
**Estado revisto:** 20/11/2026, após os commits de baselines e integração do pipeline.
**Âmbito:** auditoria consolidada do estado atual, incluindo a análise
metodológica de segmentação e *data leakage*, seguida do plano de ação.

Este é o documento único para compreender o estado atual e orientar todo o
trabalho seguinte do projeto.

## 1. Conclusão executiva

O projeto tem um **pipeline técnico de preparação de dados essencialmente
concluído, reproduzível e verificado**. A limpeza, divisão, normalização,
janelamento e infraestrutura de carregamento das janelas funcionam.

No entanto, a auditoria metodológica acrescenta uma ressalva importante:

> O código atual não mostra fuga estrutural de informação, mas o repositório
> não contém registos suficientes para provar completamente que todas as
> decisões históricas de parametrização foram tomadas sem observar, direta
> ou indiretamente, o conjunto de teste.

Assim, os parâmetros atuais — 30 minutos, 50% de sobreposição,
`gap_max_s=600` e `min_pontos=30` — devem ser tratados como **configuração de
referência provisória**, não ainda como configuração final congelada.

### 1.1. Feito e bom

- Ambiente Python e dependências instalados e reproduzíveis.
- Pipeline CSV → Parquet → divisão → normalização → janelas executável.
- Divisão por trajetória completa antes da criação de janelas.
- IDs mutuamente exclusivos entre treino, validação e teste.
- Normalização ajustada exclusivamente no treino.
- Parâmetros de normalização guardados em JSON.
- Janelas temporais persistidas para os três conjuntos.
- Integridade das janelas verificada.
- `Dataset`, `DataLoader`, bucketing, máscara, loss mascarada e packing para
  GRU implementados e testados.

### 1.2. Feito, mas deve ser modificado ou formalizado

- A qualidade dos dados tem outliers e uma discrepância temporal ainda sem
  decisão documentada.
- A política para os pontos que ficam sem janela ainda não está definida.
- A origem e o processo de seleção dos parâmetros de janelamento não estão
  suficientemente registados.
- Não está demonstrado historicamente que o teste foi usado apenas para
  avaliação final.
- A relação entre IDs com prefixos comuns e navios não foi investigada.
- `requirements.txt` é uma lista curada, não um `pip freeze` completo.
- Existem pequenas inconsistências na documentação, na contagem de gaps e
  na ordenação assumida por alguns scripts.

### 1.3. Ainda não feito

- Seleção dos baselines ponto a ponto na validação e avaliação no teste.
- Baselines por janela, incluindo HMM e aproximação ao método de Wu et al.
- Treino e avaliação do classificador sequencial.
- Agregação de previsões de janelas sobrepostas.
- Pós-processamento temporal e reconstrução de segmentos.
- Ablações de duração, sobreposição, features e modo de janelamento.
- Métricas por ponto e por segmento.
- Avaliação final independente no teste.
- Deteção incremental/streaming.
- Explicabilidade, calibração, visualização e dashboard HCAI.
- Resultados, discussão e resposta às perguntas de investigação.

## 2. Evidência de execução do estado atual

Foi lido o README, o plano de passos, o plano de ação, todos os módulos de
`src/`, `requirements.txt`, `AGENTS.md`, `.gitignore`, a proposta LaTeX, a
bibliografia e o histórico Git.

O pipeline foi executado a partir da raiz:

```bash
time ./IACH_AIS_venv/bin/python src/main.py
```

Resultado:

- exit code 0;
- aproximadamente 11 segundos;
- artefactos derivados regenerados;
- teste do `Dataset`/`DataLoader` terminou com `Tudo OK`.

Também foram executados:

```bash
./IACH_AIS_venv/bin/python src/verificar_divisao.py
./IACH_AIS_venv/bin/python src/analisar_gaps.py
```

### 2.1. Ambiente

| Componente | Versão/estado |
|---|---|
| Python | 3.14.4 |
| PyTorch | 2.15.0+cpu |
| scikit-learn | 1.9.1 |
| pandas | 3.1.1 |
| numpy | 2.5.5 |
| pyarrow | 26.0.1 |
| matplotlib | 3.11.2 |
| seaborn | 0.13.2 |
| tqdm | 4.70.1 |
| CUDA | Indisponível; execução CPU |

## 3. Pipeline de dados

### 3.1. Conversão e estrutura

O CSV original contém 1 026 279 pontos e 123 trajetórias. A limpeza:

- lê as colunas necessárias;
- ordena por `(id, t)`;
- converte `fishing` para `label=1` e as restantes classes para `label=0`;
- grava o Parquet limpo;
- usa tipos compactos.

As colunas finais normalizadas são:

```text
id, t_rel, label, x, y, signed_turn, time_gap, euc_speed, distanceToShore
```

### 3.2. Divisão

`dividir_parquet` divide por ID completo, antes do janelamento, com semente
42. A verificação atual devolveu:

| Conjunto | Trajetórias | Pontos | Proporção de pesca |
|---|---:|---:|---:|
| Treino | 86 | 706 522 | 75,6% |
| Validação | 19 | 173 532 | 77,1% |
| Teste | 18 | 146 225 | 73,5% |
| Total | 123 | 1 026 279 | 775 521 pontos |

Foram confirmados:

- nenhum ID em mais de um conjunto;
- todos os IDs originais preservados;
- nenhuma trajetória dividida entre conjuntos;
- total de pontos preservado;
- total de pontos de pesca preservado.

Isto elimina o risco estrutural de distribuir janelas da mesma trajetória
por conjuntos diferentes.

### 3.3. Normalização

`preparar_dados.py`:

1. divide o Parquet por trajetória;
2. calcula `t_rel` a partir do `time_gap` bruto;
3. ajusta mediana e IQR exclusivamente no treino;
4. guarda os parâmetros em `normalizacao.json`;
5. aplica os mesmos parâmetros ao treino, validação e teste.

Não foi encontrado `fit` global nem cálculo das estatísticas de normalização
usando validação ou teste.

### 3.4. Janelamento

`criar_janelas.py` suporta:

- modo temporal;
- modo por número de pontos;
- sobreposição configurável;
- corte em gaps;
- padding;
- máscara;
- rótulos por ponto;
- persistência em `.npz`.

`gerar_janelas.py` aplica a configuração atual:

```text
duracao_s = 1800
sobreposicao_pct = 50
gap_max_s = 600
min_pontos = 30
```

Resultados verificados em `data/janelas_resumo.json`:

| Conjunto | Janelas | T | Pontos sem janela | Cobertura | Padding |
|---|---:|---:|---:|---:|---:|
| Treino | 7 685 | 590 | 2 617 | 99,630% | 69,2% |
| Validação | 1 949 | 531 | 79 | 99,954% | 66,6% |
| Teste | 1 619 | 481 | 625 | 99,573% | 63,0% |

As listas `problemas` do resumo estão vazias. Foram confirmados IDs,
posições, `t_rel`, gaps, máscara e padding.

### 3.5. Batching

`dataset_janelas.py` implementa:

- `DatasetJanelas`;
- `collate_janelas`;
- `BucketBatchSampler`;
- `criar_dataloader`;
- `perda_mascarada`.

O teste existente confirmou:

- formas corretas;
- padding apenas no fim;
- `y=-1` apenas no padding;
- loss sem contribuição do padding;
- gradiente nulo no padding;
- bucketing com 3,9% de padding contra 62,5% sem bucketing;
- `pack_padded_sequence` com BiGRU;
- tratamento em memória de `time_gap[0]` em 34 janelas pós-gap.

A parte de convoluções/pooling mascarados para CNN ainda não existe, mas não
bloqueia o início da implementação GRU.

## 4. Qualidade dos dados e problemas conhecidos

### 4.1. Gaps

Na função `analisar_gaps`, que exclui o primeiro ponto de cada trajetória:

- 174 gaps superiores a 10 minutos;
- 22 gaps superiores a 1 hora;
- maior gap de 13,103 horas em `219012671-1`;
- deslocamento de 1,555 km nesse gap;
- velocidade implícita de 0,119 km/h;
- rótulo de pesca antes e depois;
- nenhum dos 174 gaps tem velocidade implícita superior a 30 km/h.

O bloco `__main__` imprime 177 gaps >10 minutos porque conta também os
primeiros pontos das trajetórias. A diferença deve ser uniformizada.

### 4.2. Outliers

Persistem sem decisão:

- 63 pontos com `euc_speed > 30` nós;
- 5 pontos com mais de 50 nós;
- 1 ponto com 90,702 nós;
- 636 intervalos curtos com velocidade implícita superior a 30 km/h;
- `time_gap` normalizado máximo aproximado de 7 860;
- `euc_speed` normalizado máximo aproximado de 19,2.

Não se deve remover, corrigir ou clipar estes valores automaticamente.
Primeiro deve ser tomada uma decisão explícita e comparada, se necessário,
uma variante original com uma variante tratada.

### 4.3. Inconsistência temporal

No ID `219429000-2` existe um ponto em que o timestamp avança 30 segundos,
mas `time_gap` indica 10 segundos. O `t_rel` é calculado a partir de
`time_gap`, portanto há um desvio de 20 segundos face ao timestamp original.

O dado original não deve ser alterado silenciosamente. A discrepância deve
ser investigada e documentada antes do treino.

### 4.4. IDs com prefixos comuns

Foram identificados 29 prefixos partilhados envolvendo 68 IDs. Ainda não
está confirmado se representam o mesmo navio ou apenas uma convenção de
identificação.

Se representarem o mesmo navio, uma divisão por ID pode deixar características
do mesmo navio em conjuntos diferentes. Deve ser feita uma análise de
sensibilidade com grupos por navio, sem substituir automaticamente a divisão
principal.

## 5. Auditoria metodológica de leakage

### 5.1. O que está confirmado

| Questão | Conclusão | Evidência |
|---|---|---|
| Divisão antes do janelamento | Confirmado | `preparar_dados.py` chama `dividir_parquet` antes de `gerar_janelas` |
| IDs exclusivos | Confirmado | `verificar_divisao.py` e execução atual |
| Normalização só no treino | Confirmado | `ajustar_normalizacao(treino)` |
| Mesma implementação nos conjuntos | Confirmado | `gerar_janelas.py` usa `CONJUNTOS` e os mesmos parâmetros |
| Rótulos usados para alvos | Confirmado | `criar_janelas.py` copia `label` para `y` |
| Seleção de janelas por rótulo | Não observada | não há filtro por proporção de classes |
| Leakage estrutural no código atual | Não identificado | inspeção e execução do pipeline |

### 5.2. O que não é leakage por si só

Não constitui automaticamente leakage:

- aplicar a mesma configuração de janelas aos três conjuntos;
- verificar a cobertura nos três conjuntos;
- verificar integridade de IDs, posições, gaps e padding;
- fazer auditoria física de gaps e velocidades;
- usar os rótulos para construir os alvos `y`.

O risco de leakage surgiria se resultados, rótulos ou métricas do teste fossem
usados para escolher parâmetros, features, arquitetura, limiares ou
pós-processamento.

### 5.3. O que não é verificável no histórico

O repositório não regista integralmente:

- todas as experiências de segmentação realizadas;
- todos os parâmetros experimentados;
- a origem temporal da escolha dos parâmetros atuais;
- se a cobertura do teste serviu apenas para integridade;
- se houve alteração de parâmetros depois de observar resultados do teste;
- se rótulos ou métricas de teste influenciaram alguma decisão;
- se os resultados da auditoria de gaps no dataset completo influenciaram
  `gap_max_s=600`.

Portanto, a conclusão correta é:

> **Não há evidência de leakage estrutural no código atual, mas a ausência de
> leakage histórico na seleção de parâmetros não pode ser provada
> completamente com os registos existentes.**

### 5.4. Estado metodológico dos parâmetros

Os parâmetros atuais são uma **configuração de referência provisória**.
Devem ser formalmente selecionados usando:

1. exploração estrutural no treino;
2. comparação de candidatos na validação;
3. congelamento da configuração;
4. uma única avaliação final independente no teste.

O teste não deve ser usado para escolher:

- duração;
- sobreposição;
- `min_pontos`;
- `gap_max_s`;
- features;
- arquitetura;
- hiperparâmetros;
- limiar de decisão;
- agregação;
- pós-processamento;
- variante final apresentada como melhor.

## 6. Inventário de experiências e estado do plano

### Confirmado como executado

- modo por pontos com 256 pontos e 50% de sobreposição;
- modo temporal com 30 minutos e 50% de sobreposição;
- sensibilidade de `min_pontos` no treino;
- geração final nos três conjuntos;
- teste do Dataset/DataLoader e BiGRU empacotada.
- baselines ponto a ponto (Dummy, regressão logística, random forest e
  HistGradientBoosting), ajustados e medidos apenas no treino (EXP-009).

Os resultados estruturais de treino registados incluem:

- 5 473 janelas no modo pontos sem corte de gaps;
- 5 436 janelas no modo pontos com `gap_max_s=600`;
- 7 916 janelas temporais com `min_pontos=2`;
- 7 745 com `min_pontos=20`;
- 7 685 com `min_pontos=30`;
- 7 388 com `min_pontos=50`.

### Previsto, mas não executado ou não registado como experiência completa

- sobreposições 0%, 25%, 50% e 75%;
- durações 15, 30 e 60 minutos;
- modos por pontos 128, 256 e 512;
- comparação com e sem `x`/`y`;
- seleção por desempenho na validação;
- seleção de baselines na validação e avaliação no teste;
- treino de modelo;
- agregação e pós-processamento;
- avaliação por ponto e segmento.

### Estado por fase

| Fase | Estado |
|---|---|
| Auditoria do repositório | Este documento concluído |
| Pipeline de dados | Essencialmente concluído; ressalvas metodológicas e de qualidade |
| Baselines ponto a ponto | Implementados e executados no treino; validação e teste por fazer |
| Baselines por janela | Por fazer |
| Avaliação ponto a ponto | Métricas in-sample calculadas; avaliação externa por fazer |
| Classificação sequencial/BiGRU | Infraestrutura pronta; modelo e treino por fazer |
| Agregação/pós-processamento | Por fazer |
| Ablações | Por fazer |
| Streaming | Por fazer |
| Explicabilidade/HCAI | Por fazer |
| Escrita final | Em curso, sem resultados experimentais |

## 7. LaTeX, bibliografia e reprodutibilidade

- A proposta PT usa `123` e `human-on-the-loop`.
- O PDF histórico mantém `128`/`human-in-the-loop` e deve ser tratado como
  artefacto histórico.
- A frase que descreve uma janela como sendo classificada diretamente deve ser
  clarificada, pois a implementação produz rótulos por ponto.
- Existem 16 PDFs na bibliografia, mas faltam PDFs locais para algumas
  entradas do `.bib`.
- `requirements.txt` contém 31 dependências pinadas.
- O ambiente tem 115 pacotes instalados; recomenda-se criar um
  `requirements.lock` se for necessária reprodutibilidade transitiva.

## 8. Recomendações prioritárias

1. **Formalizar a política metodológica:** declarar os parâmetros atuais como
   referência provisória e reservar o teste para avaliação final.
2. **Criar um registo de experiências:** configuração, conjunto usado,
   métrica, seed, data, resultado e decisão.
3. **Fechar a qualidade dos dados:** decidir o tratamento dos outliers e
   investigar o desalinhamento `t`/`time_gap`.
4. **Definir a política para pontos sem janela:** não os excluir
   silenciosamente; reportar cobertura e a regra nas métricas.
5. **Explorar e selecionar janelas apenas com treino/validação**, seguindo
   uma grelha previamente definida.
6. **Investigar IDs com prefixos comuns** e executar uma divisão agrupada
   como análise de sensibilidade, se representarem o mesmo navio.
7. Uniformizar a contagem de gaps no script.
8. Atualizar os estados em `passos_futuros.md`.
9. Selecionar e avaliar na validação os baselines ponto a ponto já implementados, antes da BiGRU.
10. Só depois de congelar decisões executar a avaliação final no teste.

## 9. Plano de ação recomendado

### Etapa A — Fechar a auditoria metodológica

- confirmar a proveniência dos parâmetros atuais;
- marcar 30 min/50%/600 s/30 pontos como referência provisória;
- criar o protocolo treino → validação → teste;
- registar explicitamente que as coberturas do teste são apenas controlo de
  integridade até ao congelamento.

### Etapa B — Fechar dados e cobertura

- decidir a política de outliers;
- investigar o desalinhamento temporal;
- decidir a política para pontos sem janela;
- investigar prefixos comuns;
- guardar relatórios reproduzíveis.

### Etapa C — Explorar segmentação sem usar o teste para seleção

- executar a grelha de sobreposição, duração, modo por pontos e features;
- medir apenas propriedades estruturais no treino;
- reduzir candidatos;
- comparar desempenho apenas na validação.

### Etapa D — Baselines

- DummyClassifier;
- LogisticRegression;
- RandomForest;
- Gradient Boosting disponível;
- métricas comuns, previsões por ponto e resultados reproduzíveis.

### Etapa E — Modelo sequencial

- implementar BiGRU offline;
- treinar só com treino;
- selecionar hiperparâmetros na validação;
- guardar checkpoint, configuração, normalização e histórico.

### Etapa F — Agregação e avaliação

- reconstruir previsões por ponto;
- tratar explicitamente pontos sem cobertura;
- implementar segmentos e pós-processamento;
- executar ablações;
- congelar decisões e avaliar no teste.

### Etapa G — Streaming e HCAI

- desenvolver simulador causal;
- medir latência e estabilidade;
- adicionar confiança calibrada, explicações, mapas e interface de apoio à
  decisão humana.

## 10. Limitações

- Não é possível provar apenas pelo repositório que o dataset foi novamente
  descarregado ou que todas as execuções históricas ocorreram exatamente como
  descrito.
- Não é possível provar completamente a ausência de leakage histórico sem
  logs completos de decisões e experiências.
- A qualidade estatística das escolhas atuais ainda não foi comparada por
  desempenho de modelos.
- Não existe uma suite de testes automática completa.
- A relação entre IDs com prefixos comuns e navios permanece por confirmar.
- O notebook foi executado e validado anteriormente, mas não nesta auditoria
  consolidada; o pipeline principal e os testes do Dataset foram executados
  nesta data.

## Anexo A — Comandos de verificação

```bash
./IACH_AIS_venv/bin/python -V
./IACH_AIS_venv/bin/python src/main.py
./IACH_AIS_venv/bin/python src/verificar_divisao.py
./IACH_AIS_venv/bin/python src/analisar_gaps.py
cat data/janelas_resumo.json
```

## Anexo B — Critério final adotado

| Tema | Estado adotado |
|---|---|
| Pipeline técnico | Essencialmente concluído |
| Leakage estrutural no código | Não identificado |
| Leakage histórico | Não totalmente verificável |
| Parâmetros de janelamento | Referência provisória |
| Teste | Reservado para avaliação final após congelamento |
| Auditorias anteriores | Consolidadas neste documento e removidas |


---

# Plano de ação consolidado

# IACH-AIS --- Plano de ação e especificação de implementação

**Objetivo deste documento:** orientar um agente de desenvolvimento a
analisar o estado atual do repositório e implementar, por etapas, um
sistema de deteção de atividade de pesca em trajetórias AIS, preservando
o trabalho já existente.

**Repositório:** https://github.com/DinisRosa/IACH-AIS-Project_2\
**Documentos de referência:** `proposta_pt.tex` e
`projetoIACH_2026-11-20_large-v3-turbo.txt`\
**Data:** 20 de novembro de 2026

------------------------------------------------------------------------

## 0. Instruções prioritárias para o agente

Este documento é um plano de trabalho, não uma autorização para
reescrever o projeto inteiro.

Antes de alterar código:

1.  Inspecionar o repositório, a branch ativa, o estado do Git e a
    estrutura de diretórios.
2.  Ler o README, documentação, código, testes, configurações e
    artefactos existentes.
3.  Identificar o que está efetivamente implementado e o que está apenas
    documentado.
4.  Executar os testes e o pipeline existente, quando possível,
    registando o estado inicial.
5.  Comparar a implementação com este plano e produzir uma análise de
    diferenças (*gap analysis*).
6.  Propor alterações pequenas e incrementais. Não remover nem
    substituir componentes funcionais sem justificação.
7.  Não inventar nomes de colunas, formatos de ficheiros, caminhos ou
    resultados. Confirmar tudo no código e nos dados.
8.  Não alterar os dados originais. Os dados processados e os resultados
    devem ser regeneráveis.
9.  Não fazer *commit*, *push*, deploy ou alterações destrutivas sem
    autorização explícita.
10. No fim de cada etapa, apresentar ficheiros alterados, decisões
    tomadas, testes executados, resultados e limitações.

**Regra essencial:** o agente deve tratar os números e estados
apresentados neste plano como informação de contexto a confirmar no
repositório atual, não como prova de que os ficheiros continuam iguais.

------------------------------------------------------------------------

## 1. Visão e objetivo do projeto

O projeto procura desenvolver um sistema de segmentação semântica de
trajetórias AIS para distinguir períodos de **pesca** e **navegação**,
com foco na estabilidade temporal, explicabilidade e apoio à decisão
humana.

A proposta académica centra-se em:

-   Janelas sobrepostas para classificação de trajetórias.
-   Pós-processamento temporal das previsões.
-   Avaliação por ponto e por segmento.
-   Comparação com *baselines*, incluindo HMM e o método de Wu et
    al. (2022), conforme a viabilidade de implementação.
-   Explicabilidade e confiança calibrada.
-   Apoio à decisão de inspetores (*human-on-the-loop*), mantendo a
    decisão final do lado humano.

Existe também uma extensão funcional pretendida: **detetar atividade de
pesca a partir de uma trajetória que está a ser recebida
progressivamente, sem exigir que a rota completa esteja disponível**.
Esta extensão deve ser tratada como uma experiência incremental/online,
distinguindo-a claramente da avaliação offline com trajetórias
completas.

### 1.1. Objetivos técnicos

1.  Consolidar o pipeline de dados.
2.  Criar um primeiro classificador ponto a ponto.
3.  Avaliar o classificador em trajetórias completas.
4.  Implementar e avaliar um modelo sequencial baseado em janelas,
    começando pela BiGRU caso a infraestrutura existente o suporte.
5.  Agregar previsões de janelas sobrepostas e reconstruir previsões por
    ponto.
6.  Avaliar métodos de pós-processamento temporal.
7.  Estudar duração, tamanho e sobreposição das janelas.
8.  Simular receção incremental de pontos AIS e avaliar janelas
    parciais.
9.  Acrescentar explicabilidade, calibração de confiança e visualização
    para apoio à decisão.

### 1.2. Princípio de desenvolvimento

A sequência deve ser orientada por evidência experimental:

**primeiro estabelecer um baseline simples e reproduzível; depois
introduzir modelos sequenciais; só depois otimizar janelas e
pós-processamento; finalmente avaliar o cenário incremental.**

Não começar por procurar a melhor sobreposição ou por executar uma
pesquisa extensa de hiperparâmetros antes de existir um modelo de
referência.

------------------------------------------------------------------------

## 2. Contexto conhecido e pontos a confirmar

Os documentos de contexto descrevem um dataset público de trajetórias
AIS anotadas, com os seguintes valores aproximados:

-   123 trajetórias anotadas.
-   Cerca de 1,03 milhões de pontos AIS.
-   Dataset original com 13 atributos por ponto e rótulos em cinco
    classes.
-   Agregação das classes num problema binário:
    -   Pesca: `02-` e `04-fishing`.
    -   Navegação: `01-`, `03-` e `05-sailing`.

A proposta indica que a divisão deve ser feita por ID completo de
trajetória, mantendo todos os pontos de cada trajetória no mesmo
conjunto. A proposta também refere explicitamente que IDs com o mesmo
prefixo **não** são agrupados. Esta decisão deve ser mantida como
configuração de referência para reproduzir a proposta, mas o risco de
trajetórias do mesmo navio ficarem em conjuntos diferentes deve ser
discutido como limitação e, se os identificadores permitirem, avaliado
numa experiência de robustez separada.

O contexto de trabalho anterior descreveu uma preparação já realizada
com:

-   CSV convertido para Parquet.
-   Seleção de nove colunas: `id`, `t_rel`, `label`, `x`, `y`,
    `signed_turn`, `time_gap`, `euc_speed` e `distanceToShore`.
-   Divisão referida como 86 trajetórias de treino, 19 de validação e 18
    de teste.
-   Normalização por mediana e IQR, ajustada apenas no treino.
-   Janelas temporais de 30 minutos, com 50% de sobreposição.
-   Separação em blocos quando existem gaps superiores a 10 minutos.
-   Dataset/DataLoader com suporte a sequências de comprimento variável
    e máscaras.

**Todos estes detalhes têm de ser verificados no código e nos artefactos
atuais antes de serem reutilizados.** Se os valores reais forem
diferentes, documentar a diferença e usar o estado real do repositório.

### 2.1. Verificações obrigatórias dos dados

-   Confirmar nomes, tipos, unidades e significado de todas as colunas.
-   Confirmar a regra de conversão das cinco classes originais para o
    rótulo binário.
-   Verificar valores em falta, duplicados, outliers e ordenação
    temporal.
-   Confirmar como são calculadas as features derivadas.
-   Verificar se há informação futura usada inadvertidamente no cálculo
    de features.
-   Verificar como são identificadas trajetórias e navios.
-   Confirmar a distribuição das classes por trajetória e por conjunto.
-   Confirmar que a normalização é ajustada apenas no treino.
-   Confirmar que nenhum ponto da mesma unidade de divisão aparece em
    mais do que um conjunto.

------------------------------------------------------------------------

## 3. Fase 0 --- Auditoria do repositório e reprodução do estado atual

### Objetivo

Saber exatamente o que existe antes de modificar o projeto.

### Tarefas

1.  Inspecionar a árvore de ficheiros e identificar os pontos de
    entrada.
2.  Ler a documentação e os planos já existentes.
3.  Identificar scripts de ingestão, limpeza, transformação, divisão,
    normalização e janelamento.
4.  Identificar os formatos e localizações dos dados e artefactos.
5.  Identificar modelos, código de treino, avaliação e testes já
    existentes.
6.  Executar testes automatizados.
7.  Executar o pipeline atual, se os dados e dependências estiverem
    disponíveis.
8.  Registar comandos, versões de bibliotecas, duração, erros e
    resultados.
9.  Comparar o estado real com as secções deste documento.

### Entregável

Criar ou atualizar `docs/markdown/auditoria_estado_atual.md`, contendo:

-   Estrutura atual do projeto.
-   Componentes existentes e respetivo estado.
-   Comandos para reproduzir o pipeline.
-   Testes executados e resultados.
-   Problemas encontrados.
-   Diferenças face a este plano.
-   Proposta de sequência de alterações.

**Critério de conclusão:** o pipeline atual está compreendido e existe
um ponto de partida reproduzível, ou estão documentados os bloqueios que
impedem a reprodução.

------------------------------------------------------------------------

## 4. Fase 1 --- Consolidar o pipeline de dados

### Objetivo

Garantir que os dados processados podem ser regenerados e que a
preparação não introduz fuga de informação.

### Tarefas

1.  Confirmar a conversão do CSV original para Parquet.
2.  Confirmar a seleção das colunas necessárias e justificar cada
    exclusão.
3.  Confirmar que as features derivadas são calculadas de forma
    consistente.
4.  Confirmar a divisão treino/validação/teste por trajetória completa.
5.  Confirmar a normalização com estatísticas calculadas exclusivamente
    no treino.
6.  Guardar os parâmetros de normalização para reutilização em
    validação, teste e inferência.
7.  Confirmar o tratamento de gaps temporais e de trajetórias com pontos
    insuficientes.
8.  Garantir que os dados originais nunca são sobrescritos.
9.  Garantir que todos os artefactos podem ser regenerados através de
    comandos documentados.

### Atenção especial: fuga de informação

A divisão deve ocorrer antes da criação de janelas. Nunca se deve criar
janelas de uma trajetória e só depois distribuí-las aleatoriamente por
treino, validação e teste.

A proposta define a divisão por ID completo de trajetória. Manter essa
estratégia na experiência principal. Investigar separadamente se IDs com
prefixos semelhantes ou identificadores associados ao mesmo navio podem
causar dependência entre conjuntos.

### Entregáveis

-   Pipeline de preparação reproduzível.
-   Parquet processado.
-   Ficheiros/manifestos dos splits.
-   Parâmetros de normalização guardados.
-   Relatório de qualidade e distribuição dos dados.
-   Testes de integridade e ausência de sobreposição entre conjuntos.

### Critério de conclusão

É possível regenerar os dados processados e os splits a partir dos dados
originais, com as mesmas regras e sem fuga de informação entre
conjuntos.

------------------------------------------------------------------------

## 5. Fase 2 --- Baselines de classificação ponto a ponto

### Objetivo

Criar uma referência quantitativa antes de introduzir segmentação por
janelas.

Cada ponto AIS é classificado individualmente com base apenas nas
features disponíveis nesse ponto. Este baseline permite medir quanto se
consegue aprender sem contexto temporal explícito de uma sequência.

### Modelos iniciais

Implementar, preferencialmente nesta ordem:

1.  `DummyClassifier` --- referência trivial, incluindo estratégia da
    classe maioritária.
2.  `LogisticRegression` --- baseline linear.
3.  `RandomForestClassifier` --- modelo não linear e interpretável por
    importância de features.
4.  Um modelo de Gradient Boosting disponível no ambiente do projeto,
    por exemplo HistGradientBoosting ou outra implementação já
    instalada.

Não acrescentar dependências pesadas sem necessidade. Verificar as
bibliotecas já instaladas antes de escolher a implementação.

### Regras de treino

-   Treinar exclusivamente com o conjunto de treino.
-   Usar validação para selecionar configurações.
-   Não usar o conjunto de teste para escolher modelos ou
    hiperparâmetros.
-   Preservar o desequilíbrio natural das classes na experiência
    principal, conforme descrito na proposta.
-   Registar qualquer experiência adicional com pesos de classe ou
    reamostragem como variante separada.
-   Garantir que as features utilizadas estão disponíveis no instante da
    previsão.
-   Guardar modelo, configuração, métricas e previsões.

### Métricas

Reportar, no mínimo:

-   Accuracy.
-   Precision.
-   Recall/Sensitivity.
-   F1-score.
-   Confusion matrix.
-   ROC-AUC, quando aplicável.
-   PR-AUC, especialmente devido ao desequilíbrio de classes.

A classe positiva deve ser definida explicitamente como **pesca**.
Documentar a convenção dos rótulos e a ordem das classes nas matrizes de
confusão.

Não interpretar Accuracy isoladamente: a distribuição descrita na
documentação é desequilibrada e uma previsão constante da classe
maioritária pode obter uma accuracy aparentemente elevada.

### Entregáveis

-   Módulo de definição/treino dos baselines.
-   Módulo de métricas.
-   Configurações reproduzíveis.
-   Modelos serializados.
-   Previsões por ponto para validação e teste.
-   Tabela comparativa e matrizes de confusão.

### Critério de conclusão

Existe pelo menos um baseline treinado e avaliado de forma reproduzível,
com previsões associadas aos pontos originais das trajetórias.

------------------------------------------------------------------------

## 6. Fase 3 --- Avaliação ponto a ponto em trajetórias completas

### Objetivo

Perceber como se comporta o baseline ao longo de uma trajetória completa
e estabelecer a referência para a segmentação.

### Tarefas

1.  Aplicar o modelo às trajetórias de validação e teste, sem alterar a
    ordem temporal.
2.  Associar cada previsão ao ID da trajetória e ao ponto
    correspondente.
3.  Guardar a probabilidade prevista, além da classe final, quando o
    modelo a disponibilizar.
4.  Produzir mapas ou gráficos temporais que comparem rótulos reais e
    previstos.
5.  Identificar falsos positivos, falsos negativos e transições mal
    classificadas.
6.  Medir a fragmentação das sequências previstas.
7.  Guardar os resultados num formato que permita compará-los com os
    modelos baseados em janelas.

### Métricas adicionais de sequência

-   Número de segmentos previstos por trajetória.
-   Duração dos segmentos.
-   Número de transições previstas.
-   Erro temporal das fronteiras, quando as fronteiras de referência
    estiverem disponíveis.
-   IoU por segmento, com uma definição explícita de correspondência
    entre segmentos.

### Entregável

Relatório de baseline ponto a ponto, com métricas agregadas e análise de
casos.

### Critério de conclusão

É possível visualizar e comparar, ponto a ponto, a verdade de referência
e as previsões do modelo para trajetórias completas.

------------------------------------------------------------------------

## 7. Fase 4 --- Classificação sequencial com janelas

### Objetivo

Introduzir contexto temporal e comparar o desempenho com o baseline
ponto a ponto.

### Configuração experimental inicial

Usar inicialmente a configuração já descrita no contexto do projeto,
caso seja confirmada no código:

-   Duração: 30 minutos.
-   Sobreposição: 50%.
-   Passo entre janelas: 15 minutos.
-   Separação de blocos em gaps superiores a 10 minutos.

Se a implementação atual usar janelas por número de pontos em vez de
duração temporal, não misturar os dois conceitos. Documentar a unidade e
manter a configuração existente como experiência de referência.

### Modelo inicial

Começar pela BiGRU se o `Dataset`/`DataLoader`, as máscaras e os testes
existentes confirmarem que a infraestrutura está preparada para
sequências variáveis.

A BiGRU é adequada para avaliação offline com contexto passado e futuro
dentro da janela. **Não a apresentar como modelo causal de streaming**,
porque a direção bidirecional utiliza contexto que não estaria
disponível no instante atual.

### Tarefas

1.  Rever o `Dataset` e o `DataLoader` existentes.
2.  Confirmar padding e máscaras.
3.  Confirmar que os pontos de padding não contribuem para a loss nem
    para as métricas.
4.  Implementar ou completar o modelo BiGRU.
5.  Implementar o ciclo de treino e validação.
6.  Guardar checkpoints e histórico de treino.
7.  Prever por ponto dentro de cada janela.
8.  Guardar probabilidades e previsões por janela.
9.  Avaliar o modelo nas mesmas trajetórias e pontos usados para o
    baseline.

### Agregação de janelas sobrepostas

Um ponto pode surgir em várias janelas. É necessário reconstruir uma
única previsão por ponto.

Implementar e comparar, pelo menos:

-   Média simples das probabilidades.
-   Média ponderada pela posição do ponto na janela, se fizer sentido e
    estiver bem justificada.

A votação por classes pode ser incluída como variante, mas a agregação
de probabilidades preserva mais informação.

Garantir que cada previsão agregada está associada ao ponto original
correto. Tratar explicitamente pontos sem cobertura e janelas demasiado
curtas.

### Entregáveis

-   Modelo sequencial treinável.
-   Treino e validação reproduzíveis.
-   Agregador de previsões sobrepostas.
-   Previsões reconstruídas por trajetória.
-   Comparação com os baselines ponto a ponto.

### Critério de conclusão

A BiGRU ou outro modelo sequencial escolhido produz previsões por ponto
e pode ser comparado de forma justa com o baseline.

------------------------------------------------------------------------

## 8. Fase 5 --- Pós-processamento temporal

### Objetivo

Avaliar se a regularização temporal reduz ruído e fragmentação sem
apagar transições verdadeiras entre pesca e navegação.

### Variantes a comparar

1.  Sem pós-processamento.
2.  Votação por vizinhança temporal.
3.  Hidden Markov Model (HMM), se a implementação e os pressupostos
    forem adequados.
4.  Outros métodos simples de suavização, apenas se houver justificação
    experimental.

O HMM pode também ser tratado como baseline independente, conforme a
proposta académica.

### Cuidados

-   Ajustar parâmetros apenas com treino/validação.
-   Não suavizar através de gaps temporais que representam interrupções
    reais na sequência.
-   Não eliminar segmentos curtos sem estudar se correspondem a
    atividade real.
-   Medir os efeitos positivos e negativos sobre as fronteiras.
-   Não assumir que menos segmentos significa melhor resultado.

### Métricas

Além das métricas por ponto:

-   Número de segmentos por trajetória.
-   Duração média e distribuição das durações.
-   Fragmentação.
-   Erro de fronteira.
-   IoU por segmento.
-   Alteração das previsões causada pelo pós-processamento.

### Critério de conclusão

Existe uma comparação controlada entre previsões originais e previsões
pós-processadas, com evidência sobre ganhos e perdas.

------------------------------------------------------------------------

## 9. Fase 6 --- Estudo de duração e sobreposição das janelas

### Objetivo

Responder às perguntas de investigação da proposta e escolher
configurações com base em validação.

### Matriz inicial sugerida

  Parâmetro           Valores a estudar
  ------------------- ---------------------------------
  Duração temporal    15, 30 e 60 minutos
  Sobreposição        0%, 25%, 50% e 75%
  Pós-processamento   Nenhum, votação e HMM
  Agregação           Média simples e média ponderada

Os valores devem ser ajustados à frequência e à distribuição real dos
dados. Uma janela de duração fixa pode conter números muito diferentes
de pontos.

### Experiência alternativa por número de pontos

Se for relevante para a aplicação, estudar janelas com comprimento fixo
em pontos, por exemplo 50, 100 ou 200 pontos. Não misturar diretamente
resultados de janelas temporais e janelas por número de pontos sem
documentar as diferenças.

### Ablação principal da proposta

  Experiência   Sobreposição   Pós-processamento
  ------------- -------------- -------------------
  A             Não            Não
  B             Sim            Não
  C             Não            Sim
  D             Sim            Sim

Esta ablação permite responder:

-   **RQ1:** em que medida as janelas sobrepostas reduzem a
    instabilidade das fronteiras face a janelas não sobrepostas?
-   **RQ2:** em que medida o pós-processamento reduz a fragmentação e
    melhora a concordância com os segmentos anotados?
-   **RQ3:** qual é a interação entre sobreposição e pós-processamento?

### Regras experimentais

-   Selecionar configurações usando validação.
-   Usar o mesmo conjunto de teste apenas para avaliação final.
-   Registar sementes, versões, parâmetros e resultados.
-   Comparar exatamente os mesmos pontos e trajetórias.
-   Reportar média e dispersão quando existirem várias sementes ou
    repetições.
-   Considerar custo computacional e latência, além das métricas de
    qualidade.

### Critério de conclusão

Existe uma análise experimental que permite justificar a configuração
escolhida e responder às RQ1--RQ3, mesmo que alguma componente não
produza melhorias.

------------------------------------------------------------------------

## 10. Fase 7 --- Deteção incremental com trajetórias incompletas

### Objetivo

Simular uma aplicação operacional em que uma agência recebe pontos AIS
progressivamente e pretende identificar atividade de pesca sem conhecer
a rota completa.

Esta é uma extensão importante do objetivo inicial e deve ser avaliada
separadamente da classificação offline.

### 10.1. Simulador de transmissão

Criar um simulador que:

1.  Receba uma trajetória de validação ou teste.
2.  Ordene os pontos cronologicamente.
3.  Revele os pontos progressivamente, respeitando os timestamps.
4.  Nunca disponibilize ao modelo pontos futuros.
5.  Atualize o estado do sistema à medida que chegam novos pontos.
6.  Guarde as previsões produzidas em cada instante.

A trajetória completa pode ser usada pelo simulador como fonte dos
eventos futuros, mas o modelo e o detetor só podem aceder aos pontos já
recebidos.

### 10.2. Estratégias a comparar

**A. Janela completa**

O modelo só prevê quando a janela atingir a duração ou o número de
pontos definido.

-   Vantagem: distribuição de entrada semelhante à usada no treino.
-   Desvantagem: maior atraso até à primeira previsão.

**B. Janela parcial**

O modelo recebe os pontos disponíveis, mesmo quando a janela ainda não
está completa.

-   Vantagem: possibilidade de previsão mais cedo.
-   Risco: sequências parciais podem diferir da distribuição de treino.

**C. Janela progressiva**

O modelo produz uma primeira previsão quando atinge um mínimo de pontos
e atualiza-a à medida que chegam novos pontos.

-   Vantagem: compromisso entre contexto e rapidez.
-   Requisito: treinar ou validar explicitamente com prefixos/sequências
    parciais.

Não assumir que um modelo treinado apenas com janelas completas funciona
corretamente com janelas parciais. Avaliar essa hipótese
experimentalmente.

### 10.3. Janelas finais e janelas em streaming

Na avaliação offline, pode ser útil deslocar a última janela para cobrir
o fim da trajetória.

Num cenário online, não se pode deslocar retroativamente uma janela para
usar pontos futuros. O sistema deve manter um buffer e avançar de acordo
com o passo definido.

Distinguir claramente:

-   Geração offline de janelas para cobrir toda a trajetória.
-   Buffer online de pontos já recebidos.
-   Janela parcial ainda em formação.
-   Janela final quando a transmissão termina, se esse evento for
    conhecido.

### 10.4. Features causais

Verificar que todas as features utilizadas no modo online podem ser
calculadas com os dados já recebidos.

Features como velocidade, variação de rumo ou aceleração devem ser
calculadas sem usar pontos futuros. Se alguma feature atual depender de
uma observação posterior, criar uma variante causal ou excluí-la do
experimento online.

### 10.5. Métricas operacionais

-   Tempo até à primeira deteção correta.
-   Número de pontos recebidos até à deteção.
-   Atraso em minutos.
-   Precision, Recall e F1 ao longo da transmissão.
-   Falsos positivos durante navegação.
-   Estabilidade das previsões à medida que chegam novos pontos.
-   Desempenho em janelas parciais de diferentes comprimentos.
-   Percentagem de tempo/pontos sem previsão.

### Entregáveis

-   Simulador de streaming.
-   Buffer/janela incremental.
-   Detetor que só utiliza informação disponível.
-   Registo temporal das previsões.
-   Relatório de latência e desempenho incremental.

### Critério de conclusão

Demonstrar, em trajetórias não usadas no treino, se e com que atraso o
sistema consegue detetar atividade de pesca sem ter acesso à rota
completa.

------------------------------------------------------------------------

## 11. Fase 8 --- Explicabilidade, calibração e apoio à decisão humana

### Objetivo

Alinhar a implementação com a dimensão HCAI da proposta.

### Trabalho a desenvolver

1.  Avaliar importância das features nos modelos tabulares, por exemplo
    com SHAP ou métodos adequados ao modelo.
2.  Investigar explicações para o modelo sequencial, sem assumir que
    métodos de modelos tabulares se aplicam diretamente.
3.  Calibrar probabilidades, por exemplo com isotonic regression ou
    temperature scaling, usando dados de validação.
4.  Avaliar a calibração com métricas apropriadas, como Brier score e
    Expected Calibration Error, se implementadas corretamente.
5.  Produzir confiança por ponto e por segmento.
6.  Visualizar trajetórias e segmentos num mapa.
7.  Identificar casos incertos para revisão humana.
8.  Documentar limitações, enviesamentos e riscos de interpretação.

### Princípio ético

A classificação automática não deve, por si só, fundamentar sanções. O
sistema deve apoiar o inspetor, apresentar evidência e incerteza e
manter a decisão final do lado humano.

### Critério de conclusão

Existe uma prova de conceito que apresenta previsões, confiança e
justificações de forma auditável, sem substituir a decisão humana.

------------------------------------------------------------------------

## 12. Organização de código sugerida

A estrutura seguinte é uma proposta de destino, não uma exigência para
reorganizar tudo de imediato. O agente deve preservar a estrutura
existente sempre que seja adequada e migrar módulos apenas quando
necessário.

``` text
IACH-AIS-Project_2/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── splits/
│   └── windows/
├── models/
│   ├── baselines/
│   ├── bigru/
│   └── checkpoints/
├── results/
│   ├── metrics/
│   ├── predictions/
│   ├── figures/
│   └── experiments/
├── src/
│   ├── dados/
│   │   ├── limpar_csv.py
│   │   ├── preparar_dados.py
│   │   ├── dividir_dataset.py
│   │   └── analisar_gaps.py
│   ├── segmentacao/
│   │   ├── criar_janelas.py
│   │   ├── gerar_janelas.py
│   │   └── dataset_janelas.py
│   ├── modelos/
│   │   ├── baselines.py
│   │   ├── bigru.py
│   │   └── treinar.py
│   ├── avaliacao/
│   │   ├── metricas.py
│   │   ├── visualizar.py
│   │   └── comparar_experiencias.py
│   ├── pos_processamento/
│   │   ├── agregar_previsoes.py
│   │   └── suavizar.py
│   └── streaming/
│       ├── simulador_streaming.py
│       └── detetor_incremental.py
├── docs/
│   ├── markdown/
│   ├── latex/
│   └── bibliografia/
└── requirements.txt
```

### Organização de experiências

Usar nomes inequívocos e guardar configurações:

``` text
results/
└── experiments/
    ├── exp_001_pointwise_rf/
    ├── exp_002_pointwise_gb/
    ├── exp_003_bigru_30m_50/
    ├── exp_004_bigru_30m_50_post/
    └── exp_005_streaming/
```

Cada experiência deve guardar, quando aplicável:

-   Configuração completa.
-   Semente aleatória.
-   Versão/identificador do código.
-   Modelo e checkpoint.
-   Métricas de treino e validação.
-   Previsões e probabilidades.
-   Métricas de teste, apenas na avaliação final.
-   Gráficos e logs.
-   Data e notas sobre a experiência.

Evitar guardar cópias desnecessárias de datasets grandes. Preferir
referências aos artefactos de dados e manifestos.

------------------------------------------------------------------------

## 13. Métricas e protocolo comum de avaliação

Para permitir comparações justas, centralizar as funções de avaliação e
documentar as definições.

### Métricas por ponto

-   Accuracy.
-   Precision.
-   Recall/Sensitivity.
-   F1-score.
-   ROC-AUC.
-   PR-AUC.
-   Matriz de confusão.

### Métricas por segmento

-   IoU por segmento.
-   Critério de correspondência entre segmento previsto e real.
-   Erro de fronteira inicial e final.
-   Número de segmentos por trajetória.
-   Duração média e distribuição de durações.
-   Fragmentação.

### Métricas online

-   Atraso de deteção.
-   Pontos até à deteção.
-   Desempenho por comprimento de prefixo.
-   Estabilidade entre atualizações.
-   Cobertura de previsões.

### Regras de comparação

-   Mesmas trajetórias e pontos para todos os modelos comparados.
-   Mesma definição da classe positiva.
-   Mesma política para valores sem previsão.
-   Mesma regra de construção dos segmentos.
-   Parâmetros escolhidos na validação, não no teste.
-   Reportar resultados por trajetória sempre que útil, além das
    métricas agregadas por ponto, para que trajetórias longas não
    dominem toda a avaliação.

------------------------------------------------------------------------

## 14. Cronograma lógico e prioridades

A ordem de execução recomendada é:

    Ordem Fase                                 Prioridade
  ------- ------------------------------------ ------------
        0 Auditoria do repositório             Imediata
        1 Consolidar pipeline de dados         Alta
        2 Baselines ponto a ponto              Alta
        3 Avaliação de trajetórias completas   Alta
        4 Modelo sequencial / BiGRU            Alta
        5 Agregação e pós-processamento        Alta
        6 Estudo de janelas e ablação          Média
        7 Deteção incremental / streaming      Média-alta
        8 Explicabilidade e interface          Média

A implementação deve avançar por etapas pequenas. Não começar várias
fases em paralelo.

------------------------------------------------------------------------

## 15. Primeira tarefa concreta para o agente

**Começar apenas pela Fase 0 e preparar a Fase 2, sem modificar ainda a
lógica central do pipeline.**

### Instruções de execução

1.  Auditar o repositório e confirmar os ficheiros existentes.
2.  Confirmar como os dados processados são carregados e como os splits
    são representados.
3.  Identificar a coluna de rótulo, as features e os identificadores dos
    pontos/trajectórias.
4.  Verificar como se obtêm as previsões por ponto e como se preserva a
    correspondência com os dados originais.
5.  Verificar dependências disponíveis para os modelos tabulares.
6.  Identificar o local mais adequado para implementar os baselines,
    respeitando a arquitetura existente.
7.  Propor um plano de alterações de ficheiros e testes.
8.  Só depois de apresentar essa análise, implementar os baselines ponto
    a ponto, caso não existam já.
9.  Não alterar o conjunto de teste para seleção de modelos.
10. Executar testes e produzir um relatório com os resultados.

### Critérios de aceitação da primeira implementação

-   O pipeline de dados existente continua a funcionar.
-   Os modelos são treinados apenas com treino.
-   A seleção de configurações usa validação.
-   A classe positiva é explicitamente pesca.
-   As métricas incluem F1, Precision, Recall e matriz de confusão.
-   As previsões ficam associadas aos pontos e trajetórias originais.
-   Os resultados são reproduzíveis através de configuração e semente
    registadas.
-   Não há alterações destrutivas aos dados originais.
-   Existe documentação de execução.

### Relatório que o agente deve devolver

1.  Estado inicial do repositório.
2.  Ficheiros analisados.
3.  Componentes que já existiam e foram reutilizados.
4.  Ficheiros criados ou modificados.
5.  Decisões técnicas e respetiva justificação.
6.  Comandos executados.
7.  Testes e resultados.
8.  Métricas obtidas, com indicação explícita do conjunto em que foram
    calculadas.
9.  Problemas encontrados e próximos passos.

------------------------------------------------------------------------

## 16. Decisões que não devem ser tomadas prematuramente

-   Não escolher a melhor sobreposição antes de comparar modelos.
-   Não substituir automaticamente janelas temporais por janelas de
    número fixo de pontos.
-   Não reduzir cada janela a uma média de features como abordagem
    principal: isso pode apagar transições entre pesca e navegação que
    ocorram dentro da janela.
-   Não assumir que a última janela parcial é equivalente a uma janela
    completa.
-   Não usar BiGRU como modelo causal de streaming.
-   Não usar o conjunto de teste para afinar hiperparâmetros.
-   Não afirmar que a segmentação melhora o modelo sem uma comparação
    experimental controlada.
-   Não interpretar uma redução da fragmentação como melhoria
    automática.
-   Não remover features sem medir o impacto e verificar se são
    necessárias para a inferência online.

------------------------------------------------------------------------

## 17. Resultado final pretendido

No final, o projeto deverá ter:

1.  Pipeline de dados reproduzível.
2.  Baselines ponto a ponto.
3.  Modelo sequencial treinado e avaliado.
4.  Reconstrução de previsões por trajetória a partir de janelas.
5.  Agregação de janelas sobrepostas.
6.  Pós-processamento temporal avaliado por ablação.
7.  Estudo de duração e sobreposição das janelas.
8.  Simulador de receção incremental de pontos AIS.
9.  Avaliação de deteção com trajetórias incompletas e latência.
10. Explicabilidade e confiança calibrada.
11. Visualização para apoio à decisão humana.
12. Relatório experimental que responda às perguntas de investigação da
    proposta.

**Orientação final:** preservar o que já funciona, medir antes de
otimizar e separar rigorosamente os resultados offline dos resultados de
deteção incremental. O objetivo é produzir um sistema tecnicamente
reproduzível e uma avaliação académica defensável, não apenas obter uma
accuracy elevada.
