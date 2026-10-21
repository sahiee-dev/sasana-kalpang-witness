# Sasana × KALPANG witness experiment — spec

## Source: Gokul Jayaprakash, email 2026-10-21 05:05 ET (verbatim)

Everything runs against 2.0.2, one run per cell, labelled a demonstration, with no timestamp claims.

**Common setup.** Two real executions on your fixture repo: X_in (in-bounds) and X_div (divergent). Each is sealed with Archeion. Verification uses `--trust-key` unless stated. Four phases go in the payloads of the standard event types. The effect classification always comes from a fresh REST read compared with the canonical expected request, never from the log alone.

| Cell | Setup | Expected result |
|---|---|---|
| 1 | A–D unchanged: originals plus variant 1 (edit, no rechain) and variant 2 (rechain, keep seal) | Originals INTACT / AUTHORITATIVE. All four tampered copies COMPROMISED. |
| 2 | Variant 3: rechain and re-seal with an attacker key, verified pinned and unpinned | Pinned: COMPROMISED. Unpinned: must NOT return AUTHORITATIVE. Exact status is unknown, so record it. |
| 3 | Seal stripped, rechained, verified pinned | Must NOT return INTACT. Record the exact status. |
| E | After sealing X_div, edit the comment back to the authorized body | Sasana: INTACT (the record is faithful to what was observed). Fresh read alone: IN-BOUNDS (false). Pass only if the comparison of the sealed observation against the fresh read flags the mismatch, using `updated_at` and edit history where available. |
| A8 | Operator rewrites X_div's reconciliation to IN-BOUNDS and gets a genuine Archeion seal | Sasana alone: INTACT / AUTHORITATIVE (the documented limitation). Pass if the fresh read, with the divergent comment still present, flags the mismatch. |
| A8+E (optional) | Both: the operator edits the comment back, rewrites the record and re-seals | Sealing and fresh read both fail. Only GitHub-side edit history or an audit log can detect it. Record whether it does. |

Tamper target (from Gokul's original 2026-10-10 spec): the reconciliation classification. For X_div, DIVERGENT → IN-BOUNDS; for X_in, IN-BOUNDS → DIVERGENT. Variant 1 = edit the field without updating the hash chain. Variant 2 = edit the field and recompute the chain, keeping the original seal.

**The question this answers.** Which combination of witnesses (pinned seal, fresh read, sealed-versus-fresh comparison, GitHub edit history) survives which adversary (no-key editor, own-key editor, post-seal GitHub editor, operator with Archeion access). Present it as a witness-by-adversary table, filled in from the runs, marked as a demonstration, not a proof.

**Pass criteria.** Every cell matches its expected status, or the deviation is recorded exactly. Any case where a tampered or rewritten record gets AUTHORITATIVE is reported as a finding. Any case where the fresh read alone reports a false effect is also reported.

**Not tested.** Deletion, reordering and truncation, signing-key compromise, authorization correctness, and timestamp authority validity.

## Additions agreed by Sahir (2026-10-21)

1. Witness independence: one person plays every role in these runs. The witness matrix gets a "who runs this witness" column, and the A8 claim is scoped to: a fresh read survives A8 only if run by a party other than the operator.
2. Edit-history purge: in A8+E, test whether the comment author or repo admin can delete a revision from the comment's edit history. Record whether it's purgeable and what remains. Don't assume edit history is available.
3. Cell E comparator: compare the sealed observation (body hash plus updated_at at sealing time) against the fresh read; it's built as part of the harness.
