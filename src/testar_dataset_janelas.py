"""Teste pequeno do Dataset/DataLoader das janelas (formas, máscara,
time_gap na posição 0 e loss).

Uso (a partir da raiz do repositório, depois de gerar_janelas.py):
    python src/testar_dataset_janelas.py

Usa os dados reais de treino. Termina com erro (AssertionError) se algo
falhar; no fim imprime um resumo.
"""

import json
from pathlib import Path

import numpy as np
import torch

from criar_janelas import carregar_janelas
from dataset_janelas import (DatasetJanelas, criar_dataloader,
                             perda_mascarada)

RAIZ = Path(__file__).resolve().parents[1]
NPZ = RAIZ / "data" / "janelas_treino.npz"
PARQUET = RAIZ / "data" / "treino_norm.parquet"
PARAMS = RAIZ / "data" / "normalizacao.json"
BATCH = 64


def main():
    ds = DatasetJanelas(NPZ, PARQUET)
    bruto = carregar_janelas(NPZ)  # cópia intacta, para comparar
    tg = ds.colunas.index("time_gap")
    T = ds.X.shape[1]
    print(f"{len(ds)} janelas, T={T}, features={ds.colunas}")

    # --- 1. Formas e corte ao máximo real do batch -------------------------
    dl = criar_dataloader(ds, batch_size=BATCH, shuffle=True, seed=0)
    vistos, cortados, pad_bucket, pontos_bucket = [], 0, 0, 0
    for b in dl:
        B, Tb, F = b["X"].shape
        assert F == len(ds.colunas)
        assert b["y"].shape == (B, Tb) and b["mascara"].shape == (B, Tb)
        assert b["lengths"].shape == (B,) and b["idx"].shape == (B,)
        assert Tb == int(b["lengths"].max()), "Tb tem de ser o máximo real"
        cortados += Tb < T
        pad_bucket += B * Tb
        pontos_bucket += int(b["lengths"].sum())
        vistos.extend(b["idx"].tolist())
    assert sorted(vistos) == list(range(len(ds))), "cada janela 1 vez/época"
    print(f"[ok] formas; {cortados}/{len(dl)} batches cortados abaixo de T")

    # Bucketing deve reduzir o padding face a batches sem ordenar
    ingenuo = 0
    L = ds.lengths.numpy()
    perm = np.random.default_rng(0).permutation(len(L))
    for i in range(0, len(L), BATCH):
        ingenuo += len(L[perm[i:i + BATCH]]) * L[perm[i:i + BATCH]].max()
    pad_ing = 1 - L.sum() / ingenuo
    pad_buc = 1 - pontos_bucket / pad_bucket
    assert pad_buc < pad_ing
    print(f"[ok] padding por batch: {pad_buc:.1%} com bucketing "
          f"vs {pad_ing:.1%} sem")

    # --- 2. Máscara ---------------------------------------------------------
    b = next(iter(dl))
    m, y, lens = b["mascara"], b["y"], b["lengths"]
    assert torch.equal(m.sum(1), lens)
    passos = torch.arange(m.shape[1])[None, :]
    assert torch.equal(m, passos < lens[:, None]), "padding só no fim"
    assert torch.equal(m, y != -1), "y == -1 exatamente no padding"
    assert (b["X"][~m] == 0).all()
    print("[ok] máscara coerente com lengths e y == -1")

    # --- 3. time_gap na posição 0 ------------------------------------------
    n_flag = int(ds.pos_gap.sum())
    assert n_flag > 0
    X_ds = ds.X.numpy()
    X_raw = bruto["X"]
    # alterada só a posição 0 do time_gap, e só nas janelas com flag
    assert (X_ds[ds.pos_gap, 0, tg] == 0).all()
    igual = X_ds.copy()
    igual[ds.pos_gap, 0, tg] = X_raw[ds.pos_gap, 0, tg]
    assert np.array_equal(igual, X_raw), "nada mais foi alterado em X"
    # as janelas com flag tinham mesmo um gap enorme antes de serem tratadas
    p = json.load(open(PARAMS))["time_gap"]
    limiar = (600 - p["mediana"]) / p["escala"]
    assert (X_raw[ds.pos_gap, 0, tg] > limiar).all()
    # no batch devolvido pelo DataLoader
    for b in criar_dataloader(ds, batch_size=BATCH, shuffle=False):
        sel = ds.pos_gap[b["idx"].numpy()]
        assert (b["X"][torch.from_numpy(sel), 0, tg] == 0).all()
    # o .npz em disco não foi tocado
    assert np.array_equal(carregar_janelas(NPZ)["X"], X_raw)
    max_pos0 = np.abs(X_ds[:, 0, tg]).max()
    print(f"[ok] time_gap[0]=0 em {n_flag} janelas pós-gap; "
          f"|time_gap[0]| máx. agora = {max_pos0:.1f} "
          f"(antes: {np.abs(X_raw[:, 0, tg]).max():.1f})")

    # --- 4. Loss ------------------------------------------------------------
    b = next(iter(dl))
    y, m = b["y"], b["mascara"]
    logits = torch.randn(y.shape, requires_grad=True)
    loss = perda_mascarada(logits, y)
    manual = torch.nn.functional.binary_cross_entropy_with_logits(
        logits[m], y[m].float())
    assert torch.allclose(loss, manual, atol=1e-6), "média só dos pontos reais"
    # perturbar os logits do padding não muda a loss
    outros = logits.detach().clone()
    outros[~m] = 1e3
    assert torch.allclose(perda_mascarada(outros, y), loss.detach(), atol=1e-6)
    # gradiente nulo no padding
    loss.backward()
    assert (logits.grad[~m] == 0).all() and (logits.grad[m] != 0).any()
    # logits perfeitos -> loss ~ 0
    perfeito = (y.clamp(min=0).float() * 2 - 1) * 20
    assert perda_mascarada(perfeito, y) < 1e-6
    print(f"[ok] loss mascarada = {loss.item():.4f} (== BCE só nos pontos reais)")

    # --- 5. Packing (forma como o GRU vai receber o batch) ------------------
    gru = torch.nn.GRU(len(ds.colunas), 8, batch_first=True,
                       bidirectional=True)
    emb = torch.nn.utils.rnn.pack_padded_sequence(
        b["X"], b["lengths"], batch_first=True, enforce_sorted=False)
    out, _ = gru(emb)
    out, _ = torch.nn.utils.rnn.pad_packed_sequence(
        out, batch_first=True, total_length=b["X"].shape[1])
    assert out.shape == (*b["X"].shape[:2], 16)
    print(f"[ok] pack_padded_sequence + BiGRU: saída {tuple(out.shape)}")

    print("\nTudo OK.")


if __name__ == "__main__":
    main()
