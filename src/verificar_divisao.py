import pandas as pd


def verificar_divisao(original_path, treino_path, teste_path, validacao_path,
                      mostrar=True):
    """Confirma que a divisão treino/teste/validação está correta.

    O 'original' é o Parquet ANTES da divisão (ex.: data/ais_123.parquet).
    Verifica:
      1. nenhum id aparece em mais do que um conjunto;
      2. todos os ids do original estão nalgum conjunto (e nenhum a mais);
      3. o total de pontos dos três conjuntos é igual ao do original;
      4. cada trajetória mantém todos os seus pontos (completa, não partida);
      5. o total de pontos de pesca (label=1) é igual ao do original.

    Também reporta nº de trajetórias, nº de pontos e proporção de pesca
    por conjunto. Devolve um dicionário com os resultados e 'ok' (bool).
    """
    def ler(path):
        df = pd.read_parquet(path, columns=["id", "label"])
        df["id"] = df["id"].astype(str)
        return df

    original = ler(original_path)
    conjuntos = {
        "treino": ler(treino_path),
        "teste": ler(teste_path),
        "validacao": ler(validacao_path),
    }

    ids = {nome: set(df["id"]) for nome, df in conjuntos.items()}
    ids_original = set(original["id"])

    # 1. Sem sobreposição de ids entre conjuntos
    pares = [("treino", "teste"), ("treino", "validacao"), ("teste", "validacao")]
    sobrepostos = {f"{a}/{b}": sorted(ids[a] & ids[b]) for a, b in pares}
    sem_sobreposicao = all(len(v) == 0 for v in sobrepostos.values())

    # 2. Mesmos ids que o original
    uniao = set().union(*ids.values())
    ids_em_falta = sorted(ids_original - uniao)
    ids_a_mais = sorted(uniao - ids_original)

    # 3. Total de pontos
    total_pontos = sum(len(df) for df in conjuntos.values())
    pontos_ok = total_pontos == len(original)

    # 4. Cada trajetória completa
    n_original = original.groupby("id").size()
    n_novo = pd.concat(conjuntos.values()).groupby("id").size()
    diferentes = n_original.index.union(n_novo.index)
    diff = (n_original.reindex(diferentes, fill_value=0)
            != n_novo.reindex(diferentes, fill_value=0))
    trajetorias_incompletas = sorted(diff[diff].index)

    # 5. Pontos de pesca preservados
    pesca_original = int(original["label"].sum())
    pesca_novo = int(sum(df["label"].sum() for df in conjuntos.values()))

    resultado = {
        "sem_sobreposicao_ids": sem_sobreposicao,
        "ids_sobrepostos": sobrepostos,
        "ids_em_falta": ids_em_falta,
        "ids_a_mais": ids_a_mais,
        "total_pontos_original": len(original),
        "total_pontos_conjuntos": total_pontos,
        "pontos_ok": pontos_ok,
        "trajetorias_incompletas": trajetorias_incompletas,
        "pesca_ok": pesca_original == pesca_novo,
        "por_conjunto": {
            nome: {
                "trajetorias": len(ids[nome]),
                "pontos": len(df),
                "proporcao_pesca": float(df["label"].mean()) if len(df) else 0.0,
            }
            for nome, df in conjuntos.items()
        },
    }
    resultado["ok"] = (
        sem_sobreposicao and not ids_em_falta and not ids_a_mais
        and pontos_ok and not trajetorias_incompletas
        and resultado["pesca_ok"]
    )

    if mostrar:
        def marca(ok):
            return "OK   " if ok else "ERRO "
        print(f"{marca(sem_sobreposicao)} nenhum id aparece em mais de um conjunto")
        print(f"{marca(not ids_em_falta and not ids_a_mais)} ids do original = ids dos conjuntos "
              f"({len(ids_original)} trajetórias)")
        print(f"{marca(pontos_ok)} total de pontos: {total_pontos} "
              f"(original: {len(original)})")
        print(f"{marca(not trajetorias_incompletas)} todas as trajetórias completas")
        print(f"{marca(resultado['pesca_ok'])} pontos de pesca preservados "
              f"({pesca_novo} / {pesca_original})")
        print()
        for nome, r in resultado["por_conjunto"].items():
            print(f"{nome:10s} {r['trajetorias']:4d} trajetórias | "
                  f"{r['pontos']:8d} pontos | pesca: {r['proporcao_pesca']:.1%}")
        print("\nRESULTADO:", "tudo OK" if resultado["ok"] else "há problemas")

    return resultado


if __name__ == "__main__":
    verificar_divisao(
        "data/ais_123.parquet",
        "data/treino_norm.parquet",
        "data/teste_norm.parquet",
        "data/validacao_norm.parquet",
    )
