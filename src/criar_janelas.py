from pathlib import Path

import numpy as np
import pandas as pd

COLUNAS_FEATURES = ["x", "y", "signed_turn", "time_gap",
                    "euc_speed", "distanceToShore"]


def _inicios_janelas(comprimento, n_pontos, passo):
    """Modo 'pontos': posições iniciais das janelas num segmento.

    Cobre o segmento todo: se a última janela regular não chegar ao fim,
    acrescenta-se uma janela final encostada ao fim (sem padding).
    """
    if comprimento < n_pontos:
        return np.array([], dtype=np.int64)
    inicios = np.arange(0, comprimento - n_pontos + 1, passo, dtype=np.int64)
    if inicios[-1] + n_pontos < comprimento:
        inicios = np.append(inicios, comprimento - n_pontos)
    return inicios


def _janelas_tempo(t, duracao_s, passo_s, min_pontos):
    """Modo 'tempo': (inicio, fim) de cada janela de duracao_s segundos.

    t são os t_rel (ordenados) de um segmento. Cada janela é o intervalo
    fechado [t0, t0 + duracao_s]; fim é exclusivo (posição). A última janela
    é encostada ao fim do segmento. Janelas com menos de min_pontos pontos
    são descartadas.
    """
    vazio = np.array([], dtype=np.int64)
    duracao_total = t[-1] - t[0]
    if duracao_total < duracao_s:
        if len(t) >= min_pontos:
            return np.array([0], dtype=np.int64), np.array([len(t)], dtype=np.int64)
        return vazio, vazio
    t0s = t[0] + np.arange(0, duracao_total - duracao_s + 1e-6, passo_s)
    if t0s[-1] + duracao_s < t[-1] - 1e-9:
        t0s = np.append(t0s, t[-1] - duracao_s)
    ini = np.searchsorted(t, t0s, side="left")
    fim = np.searchsorted(t, t0s + duracao_s, side="right")
    ok = (fim - ini) >= min_pontos
    return ini[ok].astype(np.int64), fim[ok].astype(np.int64)


def criar_janelas(parquet_path, n_pontos=None, sobreposicao_pct=50,
                  colunas=COLUNAS_FEATURES, gap_max_s=None, output_path=None,
                  duracao_s=None, min_pontos=2):
    """Divide cada trajetória em janelas com sobreposição.

    Dois modos (dá exatamente um dos dois):
      - n_pontos=256   -> janelas de 256 pontos (modo 'pontos')
      - duracao_s=1800 -> janelas de 30 minutos (modo 'tempo')

    Parâmetros
    ----------
    parquet_path : Parquet já normalizado (ex.: data/treino_norm.parquet),
        com as colunas id, t_rel, label e as features.
    sobreposicao_pct : sobreposição entre janelas consecutivas, de 0 a 99.
    colunas : features que entram em X (para a ablação sem x e y, retira-as
        desta lista).
    gap_max_s : se dado (segundos, ex.: 600), corta as trajetórias onde o
        tempo entre pontos consecutivos excede este valor, para nenhuma
        janela atravessar um gap grande. Por defeito, desligado.
    output_path : se dado, guarda o resultado num .npz.
    min_pontos : (modo 'tempo') nº mínimo de pontos para manter uma janela.

    Devolve um dicionário:
        X         (N, T, n_features) float32. No modo 'pontos', T = n_pontos.
                  No modo 'tempo' o nº de pontos varia, por isso T é o maior
                  nº de pontos de uma janela e as restantes ficam com padding
                  (zeros) no fim.
        y         (N, T) int8 — label de cada ponto. Padding = -1.
        mascara   (N, T) bool — True nos pontos reais, False no padding.
        meta      DataFrame, uma linha por janela: id, inicio, fim (posição
                  do 1.º ponto e de 1 depois do último na trajetória),
                  n_pontos, t_ini, t_fim (t_rel em segundos).
        colunas   lista das features, pela ordem de X.
        info      resumo (passo, nº de janelas, pontos sem janela, ...).
    """
    if (n_pontos is None) == (duracao_s is None):
        raise ValueError("Dá exatamente um de: n_pontos ou duracao_s.")
    if not 0 <= sobreposicao_pct < 100:
        raise ValueError("sobreposicao_pct tem de estar entre 0 e 99.")

    if n_pontos is not None:
        if int(n_pontos) != n_pontos or n_pontos < 2:
            raise ValueError("n_pontos tem de ser um inteiro >= 2.")
        modo = "pontos"
        n_pontos = int(n_pontos)
        passo = max(1, round(n_pontos * (1 - sobreposicao_pct / 100)))
    else:
        if duracao_s <= 0:
            raise ValueError("duracao_s tem de ser positivo.")
        modo = "tempo"
        passo = duracao_s * (1 - sobreposicao_pct / 100)  # em segundos

    df = pd.read_parquet(parquet_path)
    df["id"] = df["id"].astype(str)
    df = df.sort_values(["id", "t_rel"], kind="stable").reset_index(drop=True)

    trajetorias = []  # (id, feats, lab, t_rel, inicios, fins)
    pontos_sem_janela = 0
    sem_janelas = []

    for traj_id, g in df.groupby("id", sort=True):
        feats = g[list(colunas)].to_numpy(dtype=np.float32)
        lab = g["label"].to_numpy(dtype=np.int8)
        t_rel = g["t_rel"].to_numpy(dtype=np.float64)
        L = len(g)

        if gap_max_s is None:
            limites = [0, L]
        else:
            cortes = np.where(np.diff(t_rel) > gap_max_s)[0] + 1
            limites = [0, *cortes.tolist(), L]

        inis, fins = [], []
        for a, b in zip(limites[:-1], limites[1:]):
            if modo == "pontos":
                ini = _inicios_janelas(b - a, n_pontos, passo) + a
                fim = ini + n_pontos
            else:
                ini, fim = _janelas_tempo(t_rel[a:b], duracao_s, passo, min_pontos)
                ini, fim = ini + a, fim + a
                if len(ini) == 0:
                    ini = np.array([a], dtype=np.int64)
                    fim = np.array([b], dtype=np.int64)
            inis.append(ini)
            fins.append(fim)
        ini = np.concatenate(inis)
        fim = np.concatenate(fins)

        # pontos que ficaram fora de todas as janelas
        cob = np.zeros(L + 1, dtype=np.int64)
        np.add.at(cob, ini, 1)
        np.add.at(cob, fim, -1)
        pontos_sem_janela += int((np.cumsum(cob[:L]) <= 0).sum())

        if len(ini) == 0:
            sem_janelas.append(traj_id)
            continue
        trajetorias.append((traj_id, feats, lab, t_rel, ini, fim))

    if not trajetorias:
        raise ValueError("Nenhuma janela criada: o tamanho pedido é maior "
                         "do que todas as trajetórias (ou segmentos).")

    N = sum(len(t[4]) for t in trajetorias)
    T = max(int((t[5] - t[4]).max()) for t in trajetorias)
    F = len(colunas)
    X = np.zeros((N, T, F), dtype=np.float32)
    y = np.full((N, T), -1, dtype=np.int8)
    mascara = np.zeros((N, T), dtype=bool)
    meta_lista = []

    w = 0
    for traj_id, feats, lab, t_rel, ini, fim in trajetorias:
        for a, b in zip(ini, fim):
            n = b - a
            X[w, :n] = feats[a:b]
            y[w, :n] = lab[a:b]
            mascara[w, :n] = True
            w += 1
        meta_lista.append(pd.DataFrame({
            "id": traj_id, "inicio": ini, "fim": fim, "n_pontos": fim - ini,
            "t_ini": t_rel[ini], "t_fim": t_rel[fim - 1],
        }))
    meta = pd.concat(meta_lista, ignore_index=True)

    resultado = {
        "X": X, "y": y, "mascara": mascara, "meta": meta,
        "colunas": list(colunas),
        "info": {
            "modo": modo,
            "n_pontos": n_pontos,
            "duracao_s": duracao_s,
            "sobreposicao_pct": sobreposicao_pct,
            "passo": passo,
            "gap_max_s": gap_max_s,
            "n_trajetorias": int(df["id"].nunique()),
            "n_janelas": N,
            "T": T,
            "pontos_por_janela_min_mediana_max": (
                int(meta["n_pontos"].min()),
                float(meta["n_pontos"].median()),
                int(meta["n_pontos"].max()),
            ),
            "pontos_descartados": pontos_sem_janela,
            "trajetorias_sem_janelas": sem_janelas,
        },
    }

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            output_path, X=X, y=y, mascara=mascara,
            ids=meta["id"].to_numpy(dtype=str), inicio=meta["inicio"].to_numpy(),
            fim=meta["fim"].to_numpy(), t_ini=meta["t_ini"].to_numpy(),
            t_fim=meta["t_fim"].to_numpy(), colunas=np.array(colunas),
        )
    return resultado


def carregar_janelas(npz_path):
    """Lê um .npz guardado por criar_janelas e devolve o mesmo dicionário
    (sem 'info')."""
    d = np.load(npz_path, allow_pickle=False)
    mascara = d["mascara"] if "mascara" in d.files else np.ones(d["y"].shape, bool)
    meta = pd.DataFrame({
        "id": d["ids"], "inicio": d["inicio"], "fim": d["fim"],
        "n_pontos": d["fim"] - d["inicio"],
        "t_ini": d["t_ini"], "t_fim": d["t_fim"],
    })
    return {"X": d["X"], "y": d["y"], "mascara": mascara, "meta": meta,
            "colunas": d["colunas"].tolist()}


if __name__ == "__main__":
    r = criar_janelas("data/treino_norm.parquet", n_pontos=256,
                      sobreposicao_pct=50, gap_max_s=600)
    print(r["X"].shape, r["y"].shape)
    print(r["info"])
    r = criar_janelas("data/treino_norm.parquet", duracao_s=30 * 60,
                      sobreposicao_pct=50, gap_max_s=600)
    print(r["X"].shape, r["y"].shape)
    print(r["info"])
