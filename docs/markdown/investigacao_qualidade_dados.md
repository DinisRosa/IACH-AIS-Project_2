# Investigacao da qualidade dos dados

**Data:** 20/11/2026

Este documento consolida a investigacao das anomalias conhecidas no conjunto
AIS e define a forma minima de documentar a decisao antes do treino.

## Resultado confirmado

| Questao | Resultado | Consequencia |
|---|---|---|
| Nulos | Nenhum nulo nas 1 026 279 linhas verificadas | Sem imputacao imediata |
| Timestamps duplicados | Nenhum `(id, t)` duplicado | Sem duplicacao temporal visivel |
| Desalinhamento `t`/`time_gap` | 1 ponto em `219429000-2` em `2021-11-15 17:17:11`: `t` avanca 30 s, `time_gap=10 s` | `t_rel` acumulado fica desviado 20 s nesse troco |
| `euc_speed > 30` nós | 63 pontos, concentrados em 6 IDs | Revisao por variante |
| `euc_speed > 50` nós | 5 pontos | Valor maximo: 90,702 nós |
| Cobertura das janelas | Treino: 7 992; validação: 1 970; teste: 1 714 janelas; 0 pontos sem janela nos três conjuntos | <span style="color:purple">Cobertura 100%; nenhum ponto será excluído das métricas por falta de janela</span> |
| Velocidade implicita >30 km/h | 636 intervalos, em 42 IDs | O script de gaps nao deve usa-los como candidatos a fusao, pois filtra primeiro gaps >10 min |
| Gaps >10 min | 174 internos | Nenhum deles tem velocidade implicita >30 km/h |
| Prefixos compartilhados | 29 prefixos, 68 IDs | A divisao atual nao agrupa IDs com prefixo comum |
| Prefixos cruzados pela divisao | 16 prefixos ficam em mais de um conjunto | Efeito potencial de fuga por navio nao confirmado |

## Desalinhamento temporal

O timestamp real avanca 30 segundos, mas `time_gap` informa 10 segundos.
Como `t_rel` e calculado pela soma de `time_gap`, o erro nao deve ser corrigido
atraves de inferencias silenciosas.

**Decisao recomendada:** preservar os ficheiros brutos, manter o valor bruto
`time_gap` para auditabilidade e reportar o desvio. No treino, testar apenas
duas variantes aprovadas: manter o dado original e reconstruir `t_rel` a partir
de `t`; `t_rel` e o modo de janelamento so podem ser alterados por uma ablacão
documentada.

## Outliers de velocidade

Os 63 valores de `euc_speed >30` nós incluem 48 pontos em
`220099000-3`. O valor de 90,702 nós corresponde a uma distancia curta
(46,661 m) num intervalo de 1 segundo. Os intervalos implicitos confirmam
636 casos fisicamente anómalos com limiar superior a 30 km/h, mas o conjunto
exato nao pode ser considerado apenas erro sem comparar trajetorias.

**Decisao recomendada:** nao remover nem clipar automaticamente. Criar duas
variantes controladas:

1. original sem tratamento;
2. robusta com winsorização ou clipping definido apenas no treino.

A variante robusta precisa de limites congelados antes de usar a validação.
Se houver ganho no treino/validacao, a escolha deve ser comparada pelo mesmo
protocolo e nunca pelo teste.

## Gaps e fusao de trajetorias

Os gaps internos superiores a 10 minutos nao apresentam velocidade implicita
suspeita acima de 30 km/h. O maior gap continua em `219012671-1`:
aproximadamente 13,10 horas e 1,555 km, com cerca de 0,119 km/h. Isto suporta
a interpretacao de falha de transmissao, nao fusao por si só.

O bloco `__main__` de `analisar_gaps.py` foi corrigido para contar apenas
intervalos internos: a contagem deixa de misturar os primeiros pontos das
trajetorias. A funcao continua excluindo o primeiro ponto mesmo quando a
ordenacao usa `t`.

## Prefixos comuns

A divisao usa o ID completo e nao prova que IDs de um navio nao sejam
divididos. Foram encontrados 29 prefixos partilhados por 68 IDs; 16 prefixos
cruzam conjuntos no split atual.

Nao foi demonstrado que o prefixo identifica o navio. A decisao recomendada e:

1. fazer uma verificacao de latitudes/longitudes, duracoes e sequencia temporal
   por prefixo;
2. se houver evidencias consistentes de navio, repetir o split por grupo;
3. preservar o split atual como baseline e reportar a sensibilidade agrupada.

## Protocolo antes do treino

- congelar uma baseline original;
- reservar teste para avaliacao final;
- usar treino/validacao para escolher duracao, sobreposicao, features,
  normalizacao robusta e politica de padding;
- <span style="color:purple">a política de cobertura está definida: não excluir pontos por ausência de janela; reconstruir uma previsão por ponto original e contar cada ponto uma vez nas métricas. A agregação entre janelas sobrepostas continua por implementar e deve ser registada como decisão metodológica própria;</span>
- guardar seed, commit, conjunto, metrica e decisao no registo de experiencias;
- nao alterar a divisao principal sem uma analise comparativa separada.

## Reproducao

```bash
./IACH_AIS_venv/bin/python src/investigar_qualidade.py
./IACH_AIS_venv/bin/python src/analisar_gaps.py
```
