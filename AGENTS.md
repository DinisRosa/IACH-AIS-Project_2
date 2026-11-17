# Instructions for project agents

## Start here

- This repository's root is the project root.
- Read [`README.md`](README.md) first: it is the project map (goal, data,
  pipeline, environment and how to run it).
- Python code and its setup instructions live under `src/`; the module entry
  point is `src/main.py`.
- The detailed plan and per-step status are in
  [`docs/markdown/passos_futuros.md`](docs/markdown/passos_futuros.md).

## Branch and artifact rules

- Before editing, inspect `git status --short --branch` and preserve existing
  changes.
- `main` is the integration branch. Older topic branches (`code`, `latex`,
  `limpeza`, `bibliografia`) are historical snapshots from before the
  `src/`/`docs/` reorganization; do not merge them back without checking for
  duplicated or obsolete files.
- Keep new phase outputs on a branch that matches the phase. Never force-push
  or rewrite shared branch history.
- Only commit when explicitly asked. Stage only the files relevant to the
  request.

## Commit messages

- Follow the existing history: a concise subject `tipo(scope): resumo no
  imperativo` (e.g. `feat(dados): ...`, `docs(plano): ...`), then a blank line.
- Write a detailed body instead of a one-liner: what changed, the key decisions,
  relevant results and how it was verified. Use short paragraphs or bullets for
  multi-file changes.
- Read `git log` for style before committing. Write in Portuguese.

## Data and generated artifacts

- `data/` holds local inputs and generated data and is ignored by Git
  (`*.csv`, `*.parquet`, `*.json`, `*.npz`). Do not commit downloaded datasets
  or pipeline outputs.
- Preserve the source CSV `data/123_fishing_trajs.csv`. Regenerate derived
  files (`ais_123.parquet`, `treino_norm.parquet`, `teste_norm.parquet`,
  `validacao_norm.parquet`, `normalizacao.json`, `janelas_*.npz`,
  `janelas_resumo.json`) with `python src/main.py` instead of committing them.
- Leave virtual environments (`IACH_AIS_venv/`), caches and LaTeX build
  intermediates out of commits.

## Project materials

- Keep research sources in `docs/bibliografia/`, proposal sources in
  `docs/latex/`, and notes/decisions in `docs/`.
- Make project-specific changes only when they support the user's current
  request; do not reorganize unrelated code or research material.
