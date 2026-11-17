"""Dataset, DataLoader e loss para as janelas guardadas em .npz (passo 3.5).

Decisões (ver docs/markdown/passos_futuros.md, secção 3):

- O padding é sempre no fim da janela. `mascara` (True nos pontos reais) e
  `y = -1` (padding) são a verdade; a loss ignora y == -1.
- T varia entre conjuntos (590/531/481). Aqui nada assume um T fixo: o
  `collate` corta cada batch ao maior comprimento real que ele contém e
  devolve `lengths`, para `pack_padded_sequence`.
- Bucketing por n_pontos: janelas de comprimento parecido ficam no mesmo
  batch, o que reduz o padding (~65% de X).

DECISÃO sobre o time_gap na posição 0
-------------------------------------
Numa janela que começa depois de um gap > gap_max_s (600 s), o `time_gap`
do primeiro ponto é o próprio gap (ex.: 13 h na falha de transmissão, valor
normalizado ≈ 7 860). Isso (a) domina a escala da feature e (b) dá ao modelo
um sinal artificial ("esta janela começa depois de um gap").
Por isso, SÓ nessas janelas, `time_gap[0]` passa a 0 (em unidades
normalizadas, 0 = mediana do treino). Isto é feito em memória, neste
Dataset: os .npz ficam intactos e fiéis aos dados.

A flag "começa depois de um gap" deriva do `t_rel` do Parquet normalizado:
t_rel[inicio] - t_rel[inicio - 1] > gap_max_s. Janelas com inicio == 0 (início
da trajetória) não são afetadas: não há gap antes delas.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset, Sampler

from criar_janelas import carregar_janelas

GAP_MAX_S = 600


def flags_pos_gap(parquet_path, ids, inicio, gap_max_s=GAP_MAX_S):
    """True nas janelas cujo 1.º ponto vem depois de um gap > gap_max_s.

    `ids` e `inicio` são os do meta das janelas. A ordenação (id, t_rel) é a
    mesma usada em `criar_janelas`, para `inicio` apontar para o mesmo ponto.
    """
    df = pd.read_parquet(parquet_path, columns=["id", "t_rel"])
    df["id"] = df["id"].astype(str)
    df = df.sort_values(["id", "t_rel"], kind="stable")
    t_por_id = {k: g["t_rel"].to_numpy(dtype=np.float64)
                for k, g in df.groupby("id", sort=True)}

    ids = np.asarray(ids).astype(str)
    inicio = np.asarray(inicio, dtype=np.int64)
    flags = np.zeros(len(ids), dtype=bool)
    for traj_id in np.unique(ids):
        k = np.where(ids == traj_id)[0]
        t = t_por_id[traj_id]
        ini = inicio[k]
        com_antes = ini > 0
        gap = np.zeros(len(k))
        gap[com_antes] = t[ini[com_antes]] - t[ini[com_antes] - 1]
        flags[k] = gap > gap_max_s
    return flags


class DatasetJanelas(Dataset):
    """Janelas de um .npz, com time_gap[0] tratado em memória.

    Cada item é a linha completa (T pontos); o `collate` corta ao máximo do
    batch. Devolve também `idx` (linha no .npz/meta), para ligar previsões
    às janelas no pós-processamento.
    """

    def __init__(self, npz_path, parquet_path, gap_max_s=GAP_MAX_S,
                 tratar_time_gap_pos0=True):
        d = carregar_janelas(npz_path)
        self.meta = d["meta"]
        self.colunas = d["colunas"]
        X = d["X"]  # já em memória: alterar aqui não toca no ficheiro .npz

        self.pos_gap = flags_pos_gap(
            parquet_path, self.meta["id"].to_numpy(),
            self.meta["inicio"].to_numpy(), gap_max_s,
        )
        if tratar_time_gap_pos0:
            X[self.pos_gap, 0, self.colunas.index("time_gap")] = 0.0

        self.X = torch.from_numpy(X)
        self.y = torch.from_numpy(d["y"].astype(np.int64))
        self.mascara = torch.from_numpy(d["mascara"])
        self.lengths = torch.from_numpy(
            self.meta["n_pontos"].to_numpy(dtype=np.int64, copy=True))

    def __len__(self):
        return len(self.lengths)

    def __getitem__(self, i):
        return {"X": self.X[i], "y": self.y[i], "mascara": self.mascara[i],
                "length": self.lengths[i], "idx": i}


def collate_janelas(itens):
    """Junta itens num batch, cortado ao maior comprimento real do batch.

    Devolve: X (B, Tb, F), y (B, Tb) com -1 no padding, mascara (B, Tb),
    lengths (B,) e idx (B,). O padding está sempre no fim, por isso
    `lengths` serve diretamente a pack_padded_sequence
    (usar enforce_sorted=False).
    """
    lengths = torch.stack([it["length"] for it in itens])
    tb = int(lengths.max())
    return {
        "X": torch.stack([it["X"][:tb] for it in itens]),
        "y": torch.stack([it["y"][:tb] for it in itens]),
        "mascara": torch.stack([it["mascara"][:tb] for it in itens]),
        "lengths": lengths,
        "idx": torch.tensor([it["idx"] for it in itens], dtype=torch.long),
    }


class BucketBatchSampler(Sampler):
    """Batches de janelas com comprimentos parecidos.

    shuffle=True (treino): baralha, divide em blocos de `batch_size *
    blocos_por_bucket`, ordena cada bloco por comprimento, parte em batches
    e baralha a ordem dos batches (varia a cada época).
    shuffle=False (avaliação): ordena tudo por comprimento, determinístico;
    o `idx` do batch devolve cada janela à sua posição no meta.
    """

    def __init__(self, lengths, batch_size, shuffle=True,
                 blocos_por_bucket=50, seed=0):
        self.lengths = np.asarray(lengths)
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.bloco = batch_size * blocos_por_bucket
        self.seed = seed
        self.epoca = 0

    def set_epoch(self, epoca):
        self.epoca = epoca

    def __len__(self):
        return -(-len(self.lengths) // self.batch_size)

    def __iter__(self):
        n = len(self.lengths)
        if not self.shuffle:
            ordem = np.argsort(self.lengths, kind="stable")
            batches = [ordem[i:i + self.batch_size]
                       for i in range(0, n, self.batch_size)]
        else:
            rng = np.random.default_rng(self.seed + self.epoca)
            perm = rng.permutation(n)
            batches = []
            for a in range(0, n, self.bloco):
                bloco = perm[a:a + self.bloco]
                bloco = bloco[np.argsort(self.lengths[bloco], kind="stable")]
                batches += [bloco[i:i + self.batch_size]
                            for i in range(0, len(bloco), self.batch_size)]
            rng.shuffle(batches)
        for b in batches:
            yield b.tolist()


def criar_dataloader(dataset, batch_size=64, shuffle=True, seed=0,
                     num_workers=0):
    """DataLoader com bucketing por n_pontos e collate cortado ao batch."""
    sampler = BucketBatchSampler(dataset.lengths.numpy(), batch_size,
                                 shuffle=shuffle, seed=seed)
    return DataLoader(dataset, batch_sampler=sampler,
                      collate_fn=collate_janelas, num_workers=num_workers)


def perda_mascarada(logits, y):
    """BCE com logits, ignorando y == -1 (padding).

    logits: (B, T) — um logit por ponto (pesca = 1). y: (B, T) com -1 no
    padding. Média sobre os pontos reais; o padding não contribui.
    """
    valido = (y != -1)
    alvo = y.clamp(min=0).to(logits.dtype)
    por_ponto = torch.nn.functional.binary_cross_entropy_with_logits(
        logits, alvo, reduction="none")
    return (por_ponto * valido).sum() / valido.sum().clamp(min=1)
