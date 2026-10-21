# Witness × adversary matrix (demonstration, one run per cell, not a proof)

**Single-operator caveat.** In these runs one person (Sahir) played every role: the operator, the post-seal GitHub editor, the verifier and the party running each witness. Every "detected" below therefore shows what the witness *can* do when run, not what an independent party *would* do. In particular, **a fresh read survives A8 only if it is run by a party other than the operator.** The operator controls the Archeion record, the GitHub account and the harness here, so nothing in these runs shows that independence exists.

## Adversaries

| ID | Adversary | Runs that play it |
|---|---|---|
| A1 | No-key editor: edits the log file, cannot seal | Cell 1: variants 1, 2 (and 2b) on X_in and X_div |
| A2 | Own-key editor: rewrites and re-seals with a key they generated, or strips the seal | Cell 2 (variant 3, key B), Cell 3 (seal stripped) |
| A3 | Post-seal GitHub editor: leaves the sealed record alone, edits the GitHub comment | Cell E |
| A4 | Operator with Archeion access: rewrites the record and gets a genuine seal | Cell A8 |
| A5 | Operator with Archeion access **and** GitHub admin: also edits the comment back and (in the purge probe) deletes a history revision | Cell A8+E |

## Witnesses

* **Pinned seal**: `sasana verify --trust-key <Archeion public key obtained out of band>`.
* **Unpinned seal**: `sasana verify` with no key (the seal is checked against the key inside the seal itself).
* **Fresh read**: a REST GET of the comment, classified against the canonical expected body, and read against the record's claimed classification (comparator flag F4). "Detected" means the fresh read's verdict contradicts a *false* record while being itself true. Where the fresh read's own verdict is false, the cell says so.
* **Sealed-vs-fresh comparator**: sealed observation (body hash, `updated_at`) against a fresh read. F1/F2/F3 are observation-vs-fresh, F4 is claim-vs-fresh, F5 is the record against itself.
* **GitHub edit history**: GraphQL `userContentEdits` (and the web-UI dropdown) for the comment.

`detected` = the witness raised a flag or non-INTACT/non-AUTHORITATIVE status on the adversary's action. `not detected` = it stayed silent or returned INTACT/AUTHORITATIVE. `not tested` = no run covers it. Paths are under `work/artifacts/`.

## Matrix

| Witness | Who runs this witness | A1 no-key editor | A2 own-key editor | A3 post-seal GitHub editor | A4 operator + Archeion | A5 operator + Archeion + GitHub admin |
|---|---|---|---|---|---|---|
| **Pinned seal** | Anyone holding Archeion's public key from a channel the operator does not control. In these runs: Sahir, with the key fetched from the Archeion he ran. | **detected**: v1 `event_hash mismatch`, v2 `CHAIN_SEAL signature invalid`; COMPROMISED, exit 1 (`verify/X_*.v1_*.pinned.json`, `X_*.v2_*.pinned.json`) | **detected**: v3 `signed by untrusted key`; stripped seal `pinned key provided but session has no CHAIN_SEAL`; both COMPROMISED, exit 1 (`verify/X_*.v3_*.pinned.json`, `X_*.cell3_*.pinned.json`) | **not detected**: record untouched, INTACT / AUTHORITATIVE, exit 0; the record still says DIVERGENT, so no false claim is made, but no alarm is raised either (`verify/X_div.E_original_vs_post_edit_state.pinned.json`) | **not detected**: rewritten record, INTACT / AUTHORITATIVE, exit 0 (`verify/X_div.a8_*.pinned.json`) | **not detected**: INTACT / AUTHORITATIVE, exit 0 (`verify/X_div.a8e_full_*.pinned.json`) |
| **Unpinned seal** | Anyone with the file. No out-of-band material needed. | **detected**: v1, v2, v2b all COMPROMISED, exit 1 (`*.unpinned.json`) | **not detected**: v3 INTACT / SELF_SEALED_EVIDENCE, exit 0; stripped seal INTACT / NON_AUTHORITATIVE_EVIDENCE, exit 0. Not AUTHORITATIVE, but not an error either, and exit 0 (`verify/X_*.v3_*.unpinned.json`, `X_*.cell3_*.unpinned.json`) | **not detected**: INTACT / SELF_SEALED, exit 0 | **not detected**: INTACT / SELF_SEALED, exit 0 | **not detected**: INTACT / SELF_SEALED, exit 0 |
| **Fresh read** (vs the record's claim) | Anyone with read access to the repo. A8 claim: it survives A8 only when run by someone other than the operator (not exercised here). | **detected**: X_div read DIVERGENT contradicts the tampered IN-BOUNDS; X_in read IN-BOUNDS contradicts the tampered DIVERGENT (F4 in `compare/X_*.v1_*.json`, `X_*.v2_*.json`) | **detected**: same contradiction (F4 in `compare/X_*.v3_*.json`, `X_*.cell3_*.json`) | **not detected**: the fresh read alone reports **IN-BOUNDS, which is false** (the action was DIVERGENT); a mismatch with the record exists but the false side is the GitHub state (`X_div/fresh_post_edit.json`) | **detected**: fresh read still DIVERGENT while the record claims IN-BOUNDS (F4 in `compare/X_div.a8_*.json`; `X_div/fresh_pre_edit.json`) | **not detected**: fresh read IN-BOUNDS and the rewritten record also says IN-BOUNDS; they agree (`compare/X_div.a8e_full_*.json`) |
| **Sealed-vs-fresh comparator** | Anyone holding both the sealed record and read access. Its input comes from the sealed record, which A4/A5 control. | **detected**: F4 + F5 (`compare/X_*.v1_*.json`, `v2_*`) | **detected**: F4 + F5 | **detected**: F1 (body hash), F2 (`updated_at`), F4 (`compare/X_div.E_original_vs_post_edit_state.json`) | **detected**: F4 + F5; F1/F2 silent because the observation inside the record was left untouched (`compare/X_div.a8_*.json`) | **not detected** against a full rewrite (observation hash and `updated_at` rewritten to match the post-edit state: no flags, `compare/X_div.a8e_full_*.json`). **detected** against a classification-only rewrite: F1, F2, F5 (`results_raw.json`, row `A8E_classification_only_rewrite`) |
| **GitHub edit history** | Anyone with read access to the repo (GraphQL needs a token with Issues read; the web UI needs repo read). | **not detected**: no GitHub-side change, so the witness has nothing to see (0 revisions, `github/history_X_div_baseline.json`) | **not detected**: same, no GitHub-side change | **detected** (observed 2026-10-21): 2 revisions, edit at 15:54:13Z; the creation revision's diff hashes to the substituted body (`github/history_X_div_after_edit.json`) | **not detected**: no GitHub-side change in A8 (0 revisions at that time) | **detected, with a caveat** (observed 2026-10-21): before the purge, as A3 (edit visible, divergent content recoverable). After the author/admin deleted the creation revision through the web UI, the edit and a `deletedAt`/`deletedBy` marker remain but the content is replaced by `"deleted"` (`github/history_X_div_after_purge.json`, `github/ui/history_dropdown_after_purge.jpg`) |

> **Observed behaviour, dated 2026-10-21.** The GitHub edit-history row (A3 and A5 cells, including what a deleted revision leaves behind) records what the GitHub web UI and GraphQL API did on that date, for one comment, in one run. GitHub's UI and API behaviour may change; treat it as **VERIFY** on a later date.

## What the matrix does *not* cover

* **GitHub audit log**: not tested. This is a personal-account repo, so an org/enterprise audit log was not available to read.
* **Deleting the latest revision, or deleting and recreating the whole comment**: not tested. **VERIFY** before claiming the edit history survives those.
* **Signing-key compromise, deletion/reordering/truncation, authorization correctness, timestamp validity**: out of scope per the spec.
* **A fresh read by an independent party**: not exercised; one person ran everything.
* **Edit history while the comment is unedited in A1/A2/A4**: "not detected" there means "nothing to detect", not "tried and failed".
