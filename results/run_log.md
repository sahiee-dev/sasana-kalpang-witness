# Run log and deviations (for review before anything is published)

Date of run: 2026-10-21. Sasana 2.0.2 from PyPI (`pip install sasana[archeion]==2.0.2`, Python 3.11 venv, every harness process started with `python -I` or via the installed console scripts, so the repo checkout was never importable). KALPANG at commit `de79f039675f5db2c42f3a3e1fe5b15deb41b622`, cloned read-only.

## Departures from the brief, and process notes

1. **KALPANG was retargeted, not reimplemented.** Its binding hard-codes `GITHUB_REPOSITORY_OWNER/NAME` to Gokul's repo and rejects any other target. The run used a copy with those two constants changed to `sahiee-dev/kalpang-fixture` (the change is a two-constant edit, described in `results/kalpang_retarget.md`; the diff itself is not included, see the license section below). The canonical request hashes therefore differ from KALPANG's published ones. The authorize and execute steps ran as separate invocations; the executor, the pinned MCP server image (`v1.12.2@sha256:a44e77b9...`), and the REST observer are KALPANG's own code.
2. **KALPANG's filesystem test suite did not pass in this environment** (`test/effect-boundary.test.js`: 1/5, failing with `Authorized root is outside the private sandbox: /var/folders/...`, likely macOS `/var` symlink handling; cause not confirmed at the time; see the 2026-10-24 re-run below). The GitHub-path suites passed (`github-comment` 9/9, `github-comparison-runner` 4/4). The filesystem scenarios are not used by this experiment.
3. **Credentials.** The token was pasted into the chat twice (the first failed the scope check because the fixture repo did not exist yet and the token's reach could not be confirmed; the second passed: fixture repo and issue readable, the private witness repo returning 404, a write to another repo refused with 403). Because of that the tokens are in the session transcript and should be treated as exposed: **revoke both**. The token was passed only as an inline environment variable on single commands and never written to a file; the harness has no `gh auth token` fallback. A scan of this directory for token patterns found no hits.
4. **`gh` login (the user's broad credential) was used for two things only**, both authorised: creating `sahiee-dev/kalpang-fixture` (private, one issue titled "fixture"), and one read-only existence check of that repo when it returned 404. `sasana-kalpang-witness` was also created with `gh` (private), empty, nothing pushed.
5. **Edit-history purge was done through the web UI** using the logged-in browser session, because GitHub's GraphQL schema has no revision-delete mutation. It is therefore not something the PAT could do, and not reproducible by the scripts here. Its observed effect is recorded in `table.md`.
6. **Artifact naming bug, fixed.** `witness.py` first named verifier/comparator outputs after the file stem; the two originals share `session_sealed.original.jsonl`, so X_in's verify output was overwritten by X_div's and cell E's comparator output overwrote X_div's original. The in-memory rows in `results_raw.json` were never affected. The three outputs were regenerated from the unchanged input files by `witness.py originals` and compared with the first-run rows (all three identical).
7. **Variant 2 has two readings**, so both were run. Primary (`v2_rechain_keep_seal`): recompute the chain through the seal event, keep the original seal's key and signature. Supplementary (`v2b_rechain_seal_untouched`): rechain data events only, leave the seal event byte-for-byte. Both are COMPROMISED, but for different reasons (signature invalid vs prev_hash broken).
8. **A8+E has two rewrites.** The spec says the operator "rewrites the record". The primary row rewrites the classification and also the observation (body hash, length, `updated_at`) to be consistent with the post-edit state, i.e. the strongest operator. The classification-only rewrite is the A8 file reused; the comparator catches it (F1, F2, F5).
9. **Per-event signing is off** (no `session_pubkey`), and no RFC 3161 token is present (`SASANA_TSA_URL` pointed at a dead local port; asserted in the harness). This matches a plain `SqliteLedger` session. Sessions were written through `SqliteLedger` directly; `SESSION_END` goes through `ledger.record("SESSION_END", ...)` because `close_session()` cannot carry a payload.
10. **Archeion** ran as two separate loopback-only processes (key A = legitimate, key B = the attacker's own), each with a throwaway key file in a temp directory and `HOME` redirected. `~/.archeion` was not touched (directory mtime identical before and after: `work/artifacts/archeion_home_before.txt`). The throwaway keys were deleted afterwards; only the public keys are recorded in `results_raw.json`.
11. **Timebox:** well inside ~3 hours; no component was stopped.

## Reported findings (per the spec's pass criteria)

* A record rewritten by an operator with Archeion access gets INTACT / AUTHORITATIVE when verified pinned (cells A8 and A8+E; also X_in). This is the documented limitation, observed.
* The fresh read alone reports a false effect in cell E (IN-BOUNDS; the action was DIVERGENT).
* The comparator is defeated by a consistent full rewrite in A8+E; it is only as independent as the record it reads.
* Unpinned verification of an attacker-resealed log (variant 3) and of a seal-stripped log exit **0** (SELF_SEALED_EVIDENCE and NON_AUTHORITATIVE_EVIDENCE respectively). Neither is AUTHORITATIVE, so the spec's expectation holds, but a caller who only checks the exit code without `--strict`/`--trust-key` would see success.

## Deviations from the spec's expected results

None. Every cell matched its expected status; cells with "exact status unknown" in the spec are recorded in `table.md`.

## License status of KALPANG (checked 2026-10-21, commit `de79f03`)

The KALPANG repository at that commit has no `LICENSE`/`COPYING`/`NOTICE` file, no `license` field in `package.json`, and no license statement in its README. No license is granted by the repository itself. A diff of the retarget would have reproduced context lines from KALPANG's `src/github-comment-binding.js`, so on 2026-10-21 the diff files were deleted from this repository and replaced by a one-sentence instruction (`results/kalpang_retarget.md`): change `GITHUB_REPOSITORY_OWNER` and `GITHUB_REPOSITORY_NAME` in that file (at `de79f03`) to your own fixture repo. No KALPANG source is included in this repository. The repository's history is a single commit, so no earlier commit containing that diff is published.

## Harness edited after the run (2026-10-21)

`work/live_run.mjs` was reworded after the live runs: a few local variables were renamed and one comment added, so that it no longer repeats lines from KALPANG's runner. Behaviour is unchanged (checked afterwards: the authorize step reproduces the real runs' canonical request hashes byte-for-byte, and the execute path runs with the renamed variables). The shipped file is therefore not byte-identical to the one that made the live calls. `work/kalpang_package.json` (a copy of KALPANG's `package.json`) was also removed; use KALPANG's own `package.json` at `de79f03`.

## KALPANG update and suite re-run (2026-10-24)

Gokul pushed `16a6fc2` on 2026-10-23. Diff `de79f03..16a6fc2`: a new `LICENSE` (MIT, Copyright (c) 2026 Gokul Jayaprakash) and one line in `src/sandbox.js` (`SANDBOX_ROOT` now passes through `fs.realpath`). Nothing else changed, so `src/execute-github-comment.js`, `src/github-comment-binding.js` and `src/github-rest-observer.js` are byte-identical to the versions that made the live calls. `sandbox.js` is imported only by the filesystem scenarios (`experiment.js`, `conformance-suite.js`, `reproduce.js`) and `effect-boundary.test.js`, not by the GitHub path.

Re-run at `16a6fc2` (fresh `npm ci`, Node v25.4.0, macOS arm64, same machine as the original run):

| File | Before (`de79f03`, 2026-10-21) | After (`16a6fc2`, 2026-10-24) |
|---|---|---|
| `test/effect-boundary.test.js` | 1/5 pass | **5/5 pass** |
| `test/github-comment.test.js` | 9/9 | 9/9 |
| `test/github-comparison-runner.test.js` | 4/4 | 4/4 |
| `node --test` (all) | not run as a whole | **18/18 pass** |

The failure was therefore environmental, as suspected, and is fixed upstream: the earlier hypothesis (the `/var` -> `/private/var` symlink) matches Gokul's diagnosis. The test run rewrites KALPANG's own `artifacts/*.json` in the scratch clone; those were restored afterwards and nothing from them is used here.

The live runs were **not** repeated: the cells in `table.md` were executed at `de79f03`. Because the GitHub-path files are identical at `16a6fc2`, the run details name both commits instead of relabelling the runs.

License: the "License status" section above is superseded for KALPANG itself: it is MIT-licensed from `16a6fc2`. The earlier decision to ship only a one-sentence retarget instruction is kept (no KALPANG source is redistributed). On 2026-10-24 the repository history was checked: it is one commit (`a55dce2` plus this update), and no KALPANG source or diff is in any commit.
