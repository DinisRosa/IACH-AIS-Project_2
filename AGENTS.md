# Instructions for project agents

## Start here

- This repository's root is the project root.
- Use [`README.md`](README.md) for the project map and branch roles.
- Python code and its setup instructions are under `CODE/`; read
  [`CODE/README.md`](CODE/README.md) before changing the pipeline.

## Branch and artifact rules

- Before editing, inspect `git status --short --branch` and preserve existing
  changes.
- `features_engineering` is the completed feature-engineering record. Its
  generated figures and dataset archive belong on that branch.
- `model_training` is the next working phase. Do not restore obsolete
  feature-engineering outputs into its working tree.
- Keep future phase outputs on the matching phase branch. Never force-push or
  rewrite shared branch history.
- `CODE/database/`, `CODE/1_training/`, `CODE/2_testing/`, and
  `CODE/3_validation/` contain local inputs or generated data and are ignored
  by Git. Preserve the source CSV inputs; regenerate or restore derived JSON
  data only when needed.

## Project materials

- Keep research sources in `bibliografia/`, proposal sources in `latex/`, and
  project decisions in `docs/`.
- Leave downloaded datasets, virtual environments, caches, and LaTeX build
  intermediates out of commits.
- Make project-specific changes only when they support the user's current
  request; do not reorganize unrelated code or research material.
