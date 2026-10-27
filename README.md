# sasana-kalpang-witness

A **demonstration, one run per cell, not a proof.** It asks which combination of witnesses survives which adversary when an AI agent's tool call is recorded by [Sasana](https://github.com/sahiee-dev/Sasana) (hash-chained, Ed25519-sealed by Archeion) and its real-world effect is observed through [KALPANG](https://github.com/gokuljayaprakash8/kalpang-effect-boundary-lab)'s effect-boundary path.

## Credits

Gokul Jayaprakash: KALPANG Effect Boundary Lab (authorization binding, the controlled GitHub executor and a separate REST read-back, https://github.com/gokuljayaprakash8/kalpang-effect-boundary-lab); the expected results and pass criteria for all cells; the A8+E cell; review of the results.

Sahir: Sasana (sealing and verification, https://github.com/sahiee-dev/Sasana); the initial 2×2 proposal; cells 2, 3, E and A8; the witness-independence column and the edit-history purge test; the harness, tamper generator, sealed-vs-fresh comparator and edit-history probe; all runs and the analysis; found the macOS test failure that led to the sandbox fix.

Run details: Sasana 2.0.2 (PyPI). KALPANG at de79f03 for the live runs; its test suite was re-run at 16a6fc2 (18/18), and the GitHub-path files are identical at both commits. One run per cell, a demonstration, not a proof. GitHub behaviour observed 2026-10-21.

The spec is in `results/spec_kalpang.md`.

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
* `results/kalpang_retarget.md`: how to retarget a copy of KALPANG (the live runs used `de79f03`; the same file is unchanged at `16a6fc2`) to your own fixture (a one-sentence instruction). KALPANG's source is not redistributed here.

## Reproducing

Needs Docker (the pinned GitHub MCP server image runs under `linux/amd64`), Node, Python 3.10+, a private fixture repo with one issue, and a fine-grained token scoped to that repo only (Issues read/write) in `GITHUB_PERSONAL_ACCESS_TOKEN`. The harness has no fallback to other credentials. Paths assume a scratch directory holding `venv/` (with `sasana[archeion]==2.0.2`), `vendor/kalpang`, and this repo's `work/` beside it. The edit-history purge step was done through the GitHub web UI and is not scripted.

Every live run adds comments to the fixture issue. Do not point this at a repository you do not control.
