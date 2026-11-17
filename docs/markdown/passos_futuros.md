# Passos futuros — Segmentação semântica de trajetórias AIS

Legenda: `[x]` feito · `[~]` parcialmente feito / por confirmar · `[ ]` por fazer

## Estado atual (17/11/2026)

Ficheiros já criados:
- `limpar_csv.py` → `limpar_csv_para_parcelar` (CSV → Parquet limpo, label binário, ordenado por `(id, t)`)
- `dividir_dataset.py` → `dividir_parquet` (divisão por trajetória completa)
- `verificar_divisao.py` → `verificar_divisao` (confirma ids sem sobreposição, total de pontos e trajetórias completas)
- `preparar_dados.py` → `preparar_dados` (divisão + `t_rel` bruto + normalização mediana/IQR ajustada só ao treino + JSON de parâmetros)
- `analisar_gaps.py` → `analisar_gaps` / `resumo_gaps` / `candidatos_fusao` (estudo dos gaps temporais e deteção de possíveis trajetórias fundidas)

Dataset: **123 trajetórias** (confirmado ao voltar a descarregar o dataset do Kaggle; a proposta original indicava 128, valor entretanto corrigido) → divisão 70/15/15 = 86 / 18 / 19.
Colunas finais: `id, t_rel, label, x, y, signed_turn, time_gap, euc_speed, distanceToShore`.

Decisões tomadas:
- Normalização mediana/IQR em todas as colunas contínuas, incluindo `time_gap` (sem `log1p`)
- `t_rel` (segundos desde o início da trajetória) mantido em bruto, à parte, para janelas e deteção de gaps
- Janelas a testar das duas formas: primeiro por nº de pontos, depois por duração temporal fixa

---

## 0. Ambiente
- [x] Criar venv do projeto
- [x] Instalar só o necessário para dados (`pandas`, `pyarrow`)
- [x] Instalar bibliotecas de ML (PyTorch 2.15.0 **CPU**, scikit-learn 1.9.1, matplotlib, seaborn, tqdm); versões em `requirements.txt`

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

## 2. Normalização
- [x] Função de ajuste (só treino) e de aplicação
- [x] Parâmetros guardados em JSON
- [x] `t_rel` bruto à parte
- [x] Verificar distribuições normalizadas (`describe`)
- [ ] Testar o modelo com e sem `x`, `y` (posições absolutas) para ver se decora zonas geográficas
- [ ] Guardar o JSON junto com o modelo final (necessário para a inferência e o dashboard)

## 3. Janelamento com sobreposição  ← **próximo passo**
Valores propostos (por confirmar):
- Por pontos: 256, sobreposição 50% (testar depois 128 e 512)
- Por tempo: 30 min, sobreposição 50% (testar depois 15 e 60 min)
- Rótulo **por ponto**
- Sem padding: todas as trajetórias são bem mais longas que uma janela; só a última janela de cada trajetória é recuada para terminar no fim
- Janelas que atravessam um `time_gap` acima de ~10 min são partidas nesse ponto (limiar configurável)

Tarefas:
- [ ] Função `criar_janelas(parquet, ...)` com modo "pontos" e modo "tempo"
- [ ] Sobreposição configurável: 0%, 25%, 50%, 75%
- [ ] Não atravessar fronteiras entre `id`
- [ ] Guardar por janela o `id` e os índices dos pontos na trajetória original (necessário para o pós-processamento)
- [ ] Opcional: cache das janelas (`.npz`)

## 4. Baselines
- [ ] HMM simples sobre `euc_speed` e `signed_turn` (Peel e Good, 2011)
- [ ] Modelo clássico sobre *features* agregadas por janela (ex.: gradient boosting)
- [ ] Reimplementar ou aproximar Wu et al. (2022)

## 5. Classificador de janelas
- [ ] Escolher o modelo principal (candidatos: 1D-CNN, BiGRU, com atenção opcional)
- [ ] Definir função de custo, otimizador e hiperparâmetros (só treino e validação)
- [ ] Desequilíbrio de classes: a proposta mantém o natural, sem reamostragem nem pesos
- [ ] Treinar e guardar o melhor modelo

## 6. Pós-processamento temporal
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
- [ ] Métricas por ponto e por segmento: precisão, sensibilidade, F1, IoU
- [ ] Estabilidade: fragmentação e erro de fronteira
- [ ] Comparação com os baselines
- [ ] Considerar validação cruzada por trajetória ou várias divisões (o teste tem só ~19 trajetórias)
- [ ] Responder às RQ1, RQ2 e RQ3

## 8. Avaliação qualitativa e HCAI
- [ ] Mapas com segmentos preditos sobrepostos à verdade de referência
- [ ] Casos de sucesso e falha
- [ ] Explicabilidade com SHAP
- [ ] Confiança calibrada (Guo et al., 2017) e definição de como a confiança por segmento é obtida
- [ ] Dashboard de prova de conceito

## 9. Escrita e entrega
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
