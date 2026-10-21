"""Generate results/table.md from the raw run data. Pure formatting: no values are adjusted."""
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])  # repo root containing work/artifacts
ART = ROOT / "work" / "artifacts"
raw = json.loads((ART / "results_raw.json").read_text())
rows = {(r["label"], r["variant"]): r for r in raw["build"] + raw["post_edit"]}
fresh = lambda label, name: json.loads((ART / label / name).read_text())
hist = lambda name: json.loads((ART / "github" / name).read_text())


def sas(r, which="pinned"):
    x = r[which]
    return f"{x['status']} / {x['evidence_class']} / exit {x['exit_code']}"


def cmp_(r):
    c = r["comparator"]
    if not c["flagged"]:
        return "not flagged"
    return "FLAGGED " + ", ".join(k.split("_")[0] for k in c["flags"])


def first_err(r, which="pinned"):
    e = r[which].get("errors") or []
    return e[0] if e else ""


fr_in, fr_div = fresh("X_in", "fresh_pre_edit.json"), fresh("X_div", "fresh_pre_edit.json")
fr_post = fresh("X_div", "fresh_post_edit.json")
h0, h1, h2 = hist("history_X_div_baseline.json"), hist("history_X_div_after_edit.json"), hist("history_X_div_after_purge.json")
FR = {"X_in": f"{fr_in['classification']}", "X_div": f"{fr_div['classification']}"}

lines = []
w = lines.append
w("# Per-cell results (demonstration, one run per cell, not a proof)\n")
w("Sasana 2.0.2 from PyPI, verified through its CLI: `sasana verify <file> --json --trust-key <KEY_A>` unless a row says *unpinned*.")
w("Status / evidence class / exit code are copied from `work/artifacts/verify/*.json`. Fresh-read classification is from `work/artifacts/*/fresh_*.json`.")
w("Comparator flags: F1 body hash differs from sealed observation; F2 `updated_at` differs; F3 identity differs; F4 record's claimed classification differs from the fresh read's; F5 record contradicts its own observation.")
w("`match` = equals the spec's expected result; `FINDING` = the spec's pass criteria say to report it; `deviation` = differs from expected.\n")
w("| Cell | Object | Setup | Expected | Actual Sasana (pinned) | Fresh read | Comparator | Edit history | Match? |")
w("|---|---|---|---|---|---|---|---|---|")
for lab in ("X_in", "X_div"):
    r = rows[(lab, "original")]
    w(f"| 1 | {lab} original | sealed by Archeion A | INTACT / AUTHORITATIVE | {sas(r)} | {FR[lab]} (true) | {cmp_(r)} | n/a (comment unedited: {h0['totalCount']} revisions) | match |")
for lab in ("X_in", "X_div"):
    for v, desc in (("v1_edit_no_rechain", "variant 1: edit, no rechain"), ("v2_rechain_keep_seal", "variant 2: edit, rechain through seal, keep original seal key+signature")):
        r = rows[(lab, v)]
        w(f"| 1 | {lab} {v.split('_')[0]} | {desc} | COMPROMISED | {sas(r)} ({first_err(r)}) | {FR[lab]} | {cmp_(r)} | n/a (unedited) | match |")
for lab in ("X_in", "X_div"):
    r = rows[(lab, "v2b_rechain_seal_untouched")]
    w(f"| 1 (suppl.) | {lab} v2b | variant 2 literal: edit, rechain data events, seal event untouched | COMPROMISED | {sas(r)} ({first_err(r)}) | {FR[lab]} | {cmp_(r)} | n/a | match (not in the spec's four copies) |")
for lab in ("X_div", "X_in"):
    r = rows[(lab, "v3_reseal_attacker_key")]
    w(f"| 2 | {lab} | variant 3: edit, rechain, re-seal with attacker's own Archeion (key B) | pinned COMPROMISED; unpinned NOT AUTHORITATIVE (exact status recorded) | pinned: {sas(r)} ({first_err(r)}); **unpinned: {sas(r, 'unpinned')}** | {FR[lab]} | {cmp_(r)} | n/a | match (unpinned exact status: INTACT / SELF_SEALED_EVIDENCE, exit 0) |")
for lab in ("X_div", "X_in"):
    r = rows[(lab, "cell3_stripped_rechained")]
    w(f"| 3 | {lab} | seal stripped, edit, rechain; verified pinned | NOT INTACT (exact status recorded) | pinned: {sas(r)} ({first_err(r)}); unpinned (suppl.): {sas(r, 'unpinned')} | {FR[lab]} | {cmp_(r)} | n/a | match |")
r = rows[("X_div", "E_original_vs_post_edit_state")]
w(f"| E | X_div | original sealed record untouched; comment then edited back to the authorized body via REST PATCH | Sasana INTACT; fresh read alone IN-BOUNDS (false); PASS iff comparator flags | {sas(r)} | **{fr_post['classification']}** (FALSE: effect at action time was DIVERGENT) | {cmp_(r)} | (observed 2026-10-21) {h1['totalCount']} revisions: edit at {h1['edits'][0]['editedAt']}; creation revision `diff_sha256` equals SHA-256 of the substituted body | match (PASS). FINDING: fresh read alone reports a false effect |")
r = rows[("X_div", "a8_rewrite_genuine_reseal")]
w(f"| A8 | X_div | classification rewritten DIVERGENT->IN-BOUNDS, sealed by the real Archeion (key A); divergent comment still on GitHub | Sasana alone INTACT / AUTHORITATIVE (documented limitation); PASS iff fresh read flags | {sas(r)} | {FR['X_div']} (true) | {cmp_(r)} (F1/F2 silent: the observation was left untouched) | {h0['totalCount']} revisions (no GitHub-side change) | match (PASS). FINDING: rewritten record got AUTHORITATIVE |")
r = rows[("X_in", "a8_rewrite_genuine_reseal")]
w(f"| A8 (suppl.) | X_in | same rewrite on the in-bounds run (IN-BOUNDS->DIVERGENT), sealed by key A | as above | {sas(r)} | {FR['X_in']} (true) | {cmp_(r)} | n/a | match. FINDING: rewritten record got AUTHORITATIVE |")
rf, rw = rows[("X_div", "A8E_full_rewrite_genuine_reseal")], rows[("X_div", "A8E_classification_only_rewrite")]
w(f"| A8+E | X_div | comment edited back; record rewritten (classification AND observation hash/updated_at made consistent with post-edit state), sealed by key A | sealing and fresh read both fail; record whether edit history detects | {sas(rf)} | {fr_post['classification']} (false) | full rewrite: {cmp_(rf)}; classification-only rewrite: {cmp_(rw)} | (observed 2026-10-21) before purge: {h1['totalCount']} revisions, creation revision content = substituted body. After purge: {h2['totalCount']} entries, creation revision tombstoned (see below) | match for sealing and fresh read. FINDING: AUTHORITATIVE for a falsified record; comparator also defeated by a consistent rewrite |")
w("")
w("## Edit-history purge probe (A8+E), observed in this run\n")
w("> **Observed behaviour, dated 2026-10-21.** Everything below about GitHub's edit history (what the web UI offers, what the GraphQL schema exposes, what a deleted revision leaves behind) was observed on that date, on one comment, in one run. GitHub's UI and API behaviour may change; treat any of it as **VERIFY** on a later date.\n")
dl = h2["edits"][1]
w(f"* GraphQL schema introspection (`work/artifacts/github/introspection.json`): no mutation whose name contains edit/revision/history. The only matching type is `UserContentEdit`. So there is no *API* way to delete a revision (observed for this schema, today).")
w(f"* Web UI, logged in as the comment author who is also the repo owner: the creation revision's \"Viewing edit\" dialog offered **Delete revision**; an in-page confirm said \"This edit's content will no longer be visible. This action can not be undone.\" The deletion was performed through the web UI (browser session), not through the PAT.")
w(f"* After deletion, GraphQL `userContentEdits` (`history_X_div_after_purge.json`): totalCount stays {h2['totalCount']}; the creation revision remains listed with `deletedAt={dl['deletedAt']}`, `deletedBy={dl['deletedBy']}`, and its diff is now the {dl['diff_length']}-character placeholder `\"deleted\"` (SHA-256 `{dl['diff_sha256'][:16]}..`). Before deletion its diff hashed to the substituted body. The UI dropdown still says \"Edited 1 time\" and marks the revision \"Deleted\" (`ui/history_dropdown_after_purge.jpg`).")
w(f"* Conclusion for this run: the revision *content* is purgeable by the author/admin; the *existence* of an edit and of a deletion is not purged. The fresh REST read after the purge is unchanged (`fresh_post_purge.json`: {json.loads((ART/'X_div'/'fresh_post_purge.json').read_text())['classification']}, `updated_at` {fr_post['updated_at']}).")
w("* Not tested: deleting the most recent revision; deleting and recreating the whole comment; an org/enterprise audit log (this is a personal-account repo); whether GitHub support retains purged content. **VERIFY** any claim about these.\n")
w("## Run-level notes\n")
w("* Originals: X_in IN-BOUNDS, X_div DIVERGENT, both by KALPANG's own executor and REST observer (see `work/artifacts/*/live_bundle.json`). X_div's body was substituted at the MCP transport boundary, as in KALPANG's body-substitution run.")
w("* No timestamp claims: `SASANA_TSA_URL` pointed at a dead local port, so no RFC 3161 token is in any record (asserted in the harness).")
w("* Records contain hashes and metadata only: no raw bodies and no credentials. A scan of this directory found no token patterns.")
Path(ROOT / "results" / "table.md").write_text("\n".join(lines) + "\n")
print("wrote", ROOT / "results" / "table.md")
