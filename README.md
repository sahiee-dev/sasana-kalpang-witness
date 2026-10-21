# sasana-kalpang-witness

A **demonstration, one run per cell, not a proof.** It asks which combination of witnesses survives which adversary when an AI agent's tool call is recorded by [Sasana](https://github.com/sahiee-dev/Sasana) (hash-chained, Ed25519-sealed by Archeion) and its real-world effect is observed through [KALPANG](https://github.com/gokuljayaprakash8/kalpang-effect-boundary-lab)'s effect-boundary path.

Credits: experiment design by **Gokul Jayaprakash** (KALPANG); Sasana and this harness by **Sahir Shaik Ahamed**. The spec is in `results/spec_kalpang.md`.

* Sasana **2.0.2 from PyPI**, not the repo checkout, so this tests what users get.
* Two real executions on a private fixture repo: X_in (in-bounds) and X_div (body substituted at the MCP transport boundary), each sealed by a separate Archeion process.
* Cells: 1, 2, 3, E, A8, A8+E (see the spec). No timestamp claims; one run per cell.

## Read first

* `results/table.md`: per-cell results (status, evidence class, exit code, fresh read, comparator, edit history, match/deviation).
* `results/witness_matrix.md`: witnesses × adversaries, with a "who runs this witness" column. In these runs one person played all roles.
* `results/run_log.md`: deviations, process notes and findings.

## Layout

* `work/*.mjs`, `work/witness.py`, `work/start_archeion.sh`, `work/gen_results.py`: the harness. `bodies.mjs` holds the comment bodies; only their SHA-256 hashes reach any record.
* `work/artifacts/`: sealed originals, tampered copies, verifier JSON, sanitized REST reads, edit-history probes, comparator output.
* `results/kalpang_retarget.md`: how to retarget a copy of KALPANG at commit `de79f03` to your own fixture (a one-sentence instruction). KALPANG's source is not redistributed here.

## Reproducing

Needs Docker (the pinned GitHub MCP server image runs under `linux/amd64`), Node, Python 3.10+, a private fixture repo with one issue, and a fine-grained token scoped to that repo only (Issues read/write) in `GITHUB_PERSONAL_ACCESS_TOKEN`. The harness has no fallback to other credentials. Paths assume a scratch directory holding `venv/` (with `sasana[archeion]==2.0.2`), `vendor/kalpang`, and this repo's `work/` beside it. The edit-history purge step was done through the GitHub web UI and is not scripted.

Every live run adds comments to the fixture issue. Do not point this at a repository you do not control.
