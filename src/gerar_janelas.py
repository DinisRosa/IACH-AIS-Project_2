"""Gera e guarda as janelas finais de treino, validação e teste.

Uso (a partir da raiz do repositório):
    python src/gerar_janelas.py

Pré-requisito: já terem sido gerados os Parquet normalizados
(`python src/main.py`).

Produz em data/:
    janelas_treino.npz, janelas_validacao.npz, janelas_teste.npz
    janelas_resumo.json   (n_janelas, T, cobertura, padding por conjunto)

Os parâmetros são os decididos na secção 3.1 do plano e são iguais nos
três conjuntos. T pode variar entre conjuntos (o modelo tem de usar a
máscara), por isso é registado no resumo.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from criar_janelas import criar_janelas, carregar_janelas

PARAMETROS = {
    "duracao_s": 30 * 60,
    "sobreposicao_pct": 50,
    "gap_max_s": 600,
    "min_pontos": 30,
}

CONJUNTOS = {
    "treino": ("data/treino_norm.parquet", "data/janelas_treino.npz"),
    "validacao": ("data/validacao_norm.parquet", "data/janelas_validacao.npz"),
    "teste": ("data/teste_norm.parquet", "data/janelas_teste.npz"),
}

RESUMO_PATH = "data/janelas_resumo.json"


def verificar_integridade(parquet_path, janelas, gap_max_s):
    """Verifica as janelas contra o Parquet de origem.

    Confirma que:
      1. todos os ids das janelas existem no Parquet;
      2. as posições (inicio, fim) estão dentro da trajetória;
      3. t_ini/t_fim coincidem com o t_rel nessas posições;
      4. nenhuma janela atravessa um gap > gap_max_s;
      5. mascara, n_pontos e y (padding = -1) são coerentes.

    Devolve uma lista de problemas (vazia se estiver tudo bem).
    """
    problemas = []

    df = pd.read_parquet(parquet_path, columns=["id", "t_rel"])
    df["id"] = df["id"].astype(str)
    df = df.sort_values(["id", "t_rel"], kind="stable")
    t_por_id = {k: g["t_rel"].to_numpy(dtype=np.float64)
                for k, g in df.groupby("id", sort=True)}

    meta = janelas["meta"]

    # 1. ids conhecidos
    desconhecidos = set(meta["id"]) - set(t_por_id)
    if desconhecidos:
        problemas.append(f"ids que não existem no Parquet: {sorted(desconhecidos)[:5]}")

    # 2-4. por trajetória
    for traj_id, m in meta.groupby("id", sort=True):
        if traj_id not in t_por_id:
            continue
        t = t_por_id[traj_id]
        ini = m["inicio"].to_numpy(dtype=np.int64)
        fim = m["fim"].to_numpy(dtype=np.int64)

        if (ini < 0).any() or (fim > len(t)).any() or (ini >= fim).any():
            problemas.append(f"{traj_id}: posições fora da trajetória")
            continue

        if not (np.allclose(m["t_ini"].to_numpy(), t[ini])
                and np.allclose(m["t_fim"].to_numpy(), t[fim - 1])):
            problemas.append(f"{traj_id}: t_ini/t_fim não coincidem com t_rel")

        # flags[i] = nº de gaps grandes até à posição i (inclusive)
        flags = np.concatenate([[0], np.diff(t) > gap_max_s]).cumsum()
        atravessa = (flags[fim - 1] - flags[ini]) > 0
        if atravessa.any():
            problemas.append(
                f"{traj_id}: {int(atravessa.sum())} janelas atravessam um gap > {gap_max_s} s"
            )

    # 5. máscara, n_pontos e padding
    mascara, y = janelas["mascara"], janelas["y"]
    if not np.array_equal(mascara.sum(axis=1), meta["n_pontos"].to_numpy()):
        problemas.append("mascara.sum != n_pontos")
    if (y[~mascara] != -1).any():
        problemas.append("padding sem y = -1")
    if (y[mascara] == -1).any():
        problemas.append("pontos reais com y = -1")
    if (janelas["X"][~mascara] != 0).any():
        problemas.append("padding com X != 0")

    return problemas


def gerar_janelas(conjuntos=CONJUNTOS, parametros=PARAMETROS,
                  resumo_path=RESUMO_PATH, verificar=True):
    """Gera os .npz de cada conjunto e grava o resumo em JSON.

    Por conjunto regista: n_trajetorias, n_janelas, T, pontos_total,
    pontos_descartados, cobertura, padding e (se verificar=True) a lista
    de problemas de integridade, que deve vir vazia.
    """
    resumo = {"parametros": dict(parametros), "conjuntos": {}}

    for nome, (parquet_path, npz_path) in conjuntos.items():
        r = criar_janelas(parquet_path, output_path=npz_path, **parametros)
        info = r["info"]

        pontos_total = int(pd.read_parquet(parquet_path, columns=["id"]).shape[0])
        descartados = int(info["pontos_descartados"])

        entrada = {
            "ficheiro": str(npz_path),
            "n_trajetorias": info["n_trajetorias"],
            "n_janelas": info["n_janelas"],
            "T": info["T"],
            "pontos_total": pontos_total,
            "pontos_descartados": descartados,
            "cobertura": 1 - descartados / pontos_total,
            "padding": float(1 - r["mascara"].mean()),
            "trajetorias_sem_janelas": info["trajetorias_sem_janelas"],
        }

        if verificar:
            # Relê do disco, para validar o que ficou realmente guardado
            guardado = carregar_janelas(npz_path)
            entrada["problemas"] = verificar_integridade(
                parquet_path, guardado, parametros["gap_max_s"]
            )

        resumo["conjuntos"][nome] = entrada

    resumo_path = Path(resumo_path)
    resumo_path.parent.mkdir(parents=True, exist_ok=True)
    resumo_path.write_text(json.dumps(resumo, indent=2, ensure_ascii=False))
    return resumo


def _imprimir(resumo):
    p = resumo["parametros"]
    print(f"Parâmetros: {p['duracao_s'] // 60} min, "
          f"sobreposição {p['sobreposicao_pct']}%, "
          f"gap_max_s={p['gap_max_s']}, min_pontos={p['min_pontos']}\n")
    print(f"{'conjunto':10s} {'janelas':>8s} {'T':>5s} {'sem janela':>11s} "
          f"{'cobertura':>10s} {'padding':>8s}  integridade")
    for nome, e in resumo["conjuntos"].items():
        problemas = e.get("problemas")
        estado = "n/a" if problemas is None else ("OK" if not problemas else "ERRO")
        print(f"{nome:10s} {e['n_janelas']:8d} {e['T']:5d} "
              f"{e['pontos_descartados']:11d} {e['cobertura']:10.3%} "
              f"{e['padding']:8.1%}  {estado}")
        for prob in e.get("problemas") or []:
            print(f"    - {prob}")


if __name__ == "__main__":
    _imprimir(gerar_janelas())
