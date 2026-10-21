"""Sasana x KALPANG witness harness (demonstration, one run per cell, not a proof).

Run with the venv interpreter in isolated mode so only the PyPI wheel is imported:
    venv/bin/python -I work/witness.py build        # originals, seals, cells 1/2/3/A8 variants
    venv/bin/python -I work/witness.py post_edit    # after the GitHub-side edit: cell E and A8+E

Everything here talks to Sasana 2.0.2 only through its CLI (`sasana seal`, `sasana verify`) and the
public ledger API. Records carry hashes only: no raw comment bodies, no credentials.
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

os.environ["SASANA_TSA_URL"] = "http://127.0.0.1:9/"  # dead port: no RFC 3161 token, no timestamp claim

import sasana  # noqa: E402
from sasana.sqlite_ledger import SqliteLedger  # noqa: E402
from sasana.verifier import compute_event_hash  # noqa: E402

HERE = Path(__file__).resolve().parent
SCRATCH = HERE.parent
VENV_BIN = SCRATCH / "venv" / "bin"
assert str(SCRATCH / "venv") in sasana.__file__, f"not the PyPI wheel: {sasana.__file__}"
assert sasana.__version__ == "2.0.2", sasana.__version__
ART = HERE / "artifacts"
SERVER_A, SERVER_B = "http://127.0.0.1:18747", "http://127.0.0.1:18748"  # A = legitimate, B = attacker's own


def pubkey(server):
    with urllib.request.urlopen(server + "/pubkey", timeout=10) as r:
        return json.load(r)["pubkey"]


try:
    KEY_A, KEY_B = pubkey(SERVER_A), pubkey(SERVER_B)
except OSError:  # servers stopped: only the `originals` mode may run, using the keys recorded at build time
    _k = json.loads((ART / "results_raw.json").read_text())["keys"]
    KEY_A, KEY_B = _k["archeion_A_legit_pubkey"], _k["archeion_B_attacker_pubkey"]
assert KEY_A != KEY_B


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True, cwd="/tmp", env={"PATH": os.environ["PATH"], "HOME": "/tmp"})
    return p.returncode, p.stdout, p.stderr


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_jsonl(path, events):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(e) + "\n" for e in events))


def seal(src, dst, server):
    rc, out, err = sh([str(VENV_BIN / "sasana"), "seal", str(src), "--server", server, "--out", str(dst)])
    assert rc == 0, (rc, out, err)


def verify(path, key):
    """Run `sasana verify --json [--trust-key KEY]`; returns {exit_code, result}."""
    args = [str(VENV_BIN / "sasana"), "verify", str(path), "--json"] + (["--trust-key", key] if key else [])
    rc, out, err = sh(args)
    return {"cli": " ".join(["sasana", "verify", Path(path).name, "--json"] + (["--trust-key", "<KEY_A>"] if key else [])),
            "exit_code": rc, "result": json.loads(out) if out.strip() else None, "stderr": err.strip() or None}


# ---------------------------------------------------------------- session construction (4 phases)
def build_unsealed(label, bundle, out_path):
    obs = bundle["observation"]
    sid = f"witness-{label.lower().replace('_', '-')}-run1"
    db_dir = HERE / "ledger_tmp"
    db_dir.mkdir(exist_ok=True)
    classification = bundle["kalpang_report"]["comparison_result"]
    with SqliteLedger(db_path=db_dir / f"{sid}.db") as led:
        # 1 authorization -> SESSION_START
        led.open_session(session_id=sid, agent_id="sasana-kalpang-witness-harness", metadata={
            "phase": "authorization", "decision": bundle["authorization"]["decision"],
            "canonical_request_sha256": bundle["authorization"]["canonical_request_sha256"],
            "authorized_body_sha256": bundle["authorized_body_sha256"], "target": bundle["target"],
            "mcp_server_image": bundle["mcp_server"]["image"], "mcp_toolset": bundle["mcp_server"]["toolset"],
            "authorizer": "kalpang github-comment-binding (unsigned authorization.json)"})
        assert "rfc3161_token" not in json.loads(led._conn.execute("select payload_json from events where seq=1").fetchone()[0])
        # 2 execution -> TOOL_CALL
        led.record("TOOL_CALL", {"phase": "execution", "tool": "add_issue_comment", "target": bundle["target"],
                                 "canonical_request_sha256": bundle["authorization"]["canonical_request_sha256"],
                                 "transport_body_sha256": bundle["mcp"]["transport_body_sha256"],
                                 "mcp_call_status": bundle["kalpang_report"]["mcp_call_status"], "mcp_is_error": bundle["mcp"]["is_error"]})
        # 3 observation -> TOOL_RESULT
        led.record("TOOL_RESULT", {"phase": "observation", "observer": "github rest list+detail (kalpang github-rest-observer)",
                                   "comment_id": obs["comment_id"], "issue_url": obs["issue_url"], "body_sha256": obs["body_sha256"],
                                   "body_length": obs["body_length"], "created_at": obs["created_at"], "updated_at": obs["updated_at"]})
        # 4 reconciliation -> SESSION_END (record() accepts SESSION_END; close_session() cannot carry a payload)
        led.record("SESSION_END", {"status": "success", "phase": "reconciliation", "classification": classification,
                                   "authorized_body_sha256": bundle["authorized_body_sha256"], "observed_body_sha256": obs["body_sha256"],
                                   "canonical_request_sha256": bundle["authorization"]["canonical_request_sha256"], "comment_id": obs["comment_id"]})
        led.export_jsonl(out_path)
    for f in db_dir.glob(f"{sid}.db*"):
        f.unlink()


# ---------------------------------------------------------------- tampering
def strip_seal(events):
    return [e for e in events if e["event_type"] != "CHAIN_SEAL"]


def rechain(events, start_idx):
    """Recompute prev_hash/event_hash for events[start_idx:]; signature fields are left as they are."""
    for i in range(start_idx, len(events)):
        events[i]["prev_hash"] = events[i - 1]["event_hash"]
        events[i]["event_hash"] = compute_event_hash(events[i], "jcs-rfc8785")
    return events


def flip(label):
    return "IN-BOUNDS" if label == "DIVERGENT" else "DIVERGENT"


def idx(events, etype):
    return next(i for i, e in enumerate(events) if e["event_type"] == etype)


def edit_classification(events):
    e = events[idx(events, "SESSION_END")]
    e["payload"]["classification"] = flip(e["payload"]["classification"])
    return idx(events, "SESSION_END")


def variants_for(label, sealed_path, unsealed_path):
    """Write the tampered copies for cells 1, 2, 3 and A8; returns {name: (path, description)}."""
    out_dir = ART / "tampered"
    sealed, unsealed = read_jsonl(sealed_path), read_jsonl(unsealed_path)
    made = {}

    def put(name, events, desc):
        p = out_dir / f"{label}.{name}.jsonl"
        write_jsonl(p, events)
        made[name] = (p, desc)

    # variant 1: edit the field, no rechain, original seal untouched
    ev = copy.deepcopy(sealed)
    edit_classification(ev)
    put("v1_edit_no_rechain", ev, "edit reconciliation classification; hashes and seal untouched")
    # variant 2: edit + recompute chain through the seal event, keep the original seal's key and signature
    ev = copy.deepcopy(sealed)
    i = edit_classification(ev)
    rechain(ev[:-1], i)
    seal_ev = ev[-1]
    seal_ev["prev_hash"] = ev[-2]["event_hash"]
    seal_ev["payload"]["session_hash"] = ev[-2]["event_hash"]
    seal_ev["event_hash"] = compute_event_hash(seal_ev, "jcs-rfc8785")  # original signature kept, now over a stale hash
    put("v2_rechain_keep_seal", ev, "edit + rechain through the seal event (prev_hash, session_hash, event_hash); original seal key and signature kept")
    # variant 2 (literal): edit + rechain the data events only; seal event byte-for-byte untouched
    ev = copy.deepcopy(sealed)
    i = edit_classification(ev)
    rechain(ev[:-1], i)
    put("v2b_rechain_seal_untouched", ev, "supplementary: edit + rechain data events only; seal event left byte-for-byte as sealed")
    # variant 3: strip, edit, rechain, re-seal with the attacker's own Archeion (key B)
    ev = strip_seal(copy.deepcopy(sealed))
    i = edit_classification(ev)
    rechain(ev, i)
    tmp = out_dir / f"{label}.cell3_stripped_rechained.jsonl"
    write_jsonl(tmp, ev)
    made["cell3_stripped_rechained"] = (tmp, "seal stripped, classification edited, chain recomputed, no seal")
    v3 = out_dir / f"{label}.v3_reseal_attacker_key.jsonl"
    seal(tmp, v3, SERVER_B)
    made["v3_reseal_attacker_key"] = (v3, "edited + rechained, sealed by the attacker's own Archeion (key B)")
    # A8: operator with Archeion access: genuine seal by key A over a rewritten reconciliation
    ev = copy.deepcopy(unsealed)
    i = edit_classification(ev)
    rechain(ev, i)
    tmp = out_dir / f"{label}.a8_rewritten_unsealed.jsonl"
    write_jsonl(tmp, ev)
    a8 = out_dir / f"{label}.a8_rewrite_genuine_reseal.jsonl"
    seal(tmp, a8, SERVER_A)
    tmp.unlink()
    made["a8_rewrite_genuine_reseal"] = (a8, "reconciliation classification rewritten, then sealed by the real Archeion (key A)")
    return made


# ---------------------------------------------------------------- comparator
def comparator(log_path, fresh_path):
    """Sealed observation (body hash, updated_at at sealing time) vs a fresh REST read.

    F1..F3 compare the sealed TOOL_RESULT with the fresh read. F4 compares the record's claimed
    classification with the fresh read's classification. F5 checks the record against itself.
    """
    ev = read_jsonl(log_path)
    fresh = json.loads(Path(fresh_path).read_text())
    start = next(e for e in ev if e["event_type"] == "SESSION_START")["payload"]
    obs = next(e for e in ev if e["event_type"] == "TOOL_RESULT")["payload"]
    claimed = next(e for e in ev if e["event_type"] == "SESSION_END")["payload"]["classification"]
    authorized = start["authorized_body_sha256"]
    flags = {}
    if fresh.get("http") != 200:
        flags["FRESH_READ_UNAVAILABLE"] = f"HTTP {fresh.get('http')}"
    else:
        if obs["body_sha256"] != fresh["body_sha256"]:
            flags["F1_body_hash_changed"] = f"sealed {obs['body_sha256'][:12]}.. vs fresh {fresh['body_sha256'][:12]}.."
        if obs["updated_at"] != fresh["updated_at"]:
            flags["F2_updated_at_changed"] = f"sealed {obs['updated_at']} vs fresh {fresh['updated_at']}"
        if obs["created_at"] != fresh["created_at"] or obs["comment_id"] != fresh["comment_id"]:
            flags["F3_identity_changed"] = "created_at or comment_id differs"
        if claimed != fresh["classification"]:
            flags["F4_claim_vs_fresh_classification"] = f"record claims {claimed}; fresh read classifies {fresh['classification']}"
    own = "IN-BOUNDS" if obs["body_sha256"] == authorized else "DIVERGENT"
    if own != claimed:
        flags["F5_record_internally_inconsistent"] = f"observation hash implies {own}; record claims {claimed}"
    return {"log": Path(log_path).name, "fresh_read": Path(fresh_path).name, "record_claims": claimed,
            "fresh_classification": fresh.get("classification"), "flagged": bool(flags), "flags": flags}


def run_checks(label, name, path, fresh_path, results, stem=None):
    pinned, unpinned = verify(path, KEY_A), verify(path, None)
    vdir = ART / "verify"
    vdir.mkdir(parents=True, exist_ok=True)
    stem = stem or Path(path).stem
    (vdir / f"{stem}.pinned.json").write_text(json.dumps(pinned, indent=2) + "\n")
    (vdir / f"{stem}.unpinned.json").write_text(json.dumps(unpinned, indent=2) + "\n")
    cmp_ = comparator(path, fresh_path)
    cdir = ART / "compare"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / f"{stem}.json").write_text(json.dumps(cmp_, indent=2) + "\n")
    row = {"label": label, "variant": name, "file": Path(path).name,
           "pinned": {"status": pinned["result"]["status"], "evidence_class": pinned["result"]["evidence_class"], "exit_code": pinned["exit_code"], "errors": pinned["result"].get("errors")},
           "unpinned": {"status": unpinned["result"]["status"], "evidence_class": unpinned["result"]["evidence_class"], "exit_code": unpinned["exit_code"], "errors": unpinned["result"].get("errors")},
           "comparator": cmp_}
    results.append(row)
    return row


def main():
    mode = sys.argv[1]
    results_path = ART / "results_raw.json"
    results = json.loads(results_path.read_text()) if results_path.exists() else {"build": [], "post_edit": []}
    if mode == "build":
        results["build"] = []
        results["keys"] = {"archeion_A_legit_pubkey": KEY_A, "archeion_B_attacker_pubkey": KEY_B}
        results["sasana_version"] = sasana.__version__
        for label in ("X_in", "X_div"):
            d = ART / label
            bundle = json.loads((d / "live_bundle.json").read_text())
            unsealed, sealed = d / "session_unsealed.jsonl", d / "session_sealed.original.jsonl"
            build_unsealed(label, bundle, unsealed)
            seal(unsealed, sealed, SERVER_A)
            fresh = d / "fresh_pre_edit.json" if (d / "fresh_pre_edit.json").exists() else d / "fresh_post_seal.json"
            run_checks(label, "original", sealed, fresh, results["build"], stem=f"{label}.original")
            for name, (p, _) in variants_for(label, sealed, unsealed).items():
                run_checks(label, name, p, fresh, results["build"])
    elif mode == "post_edit":
        results["post_edit"] = []
        d = ART / "X_div"
        fresh = d / "fresh_post_edit.json"
        sealed, unsealed = d / "session_sealed.original.jsonl", d / "session_unsealed.jsonl"
        # cell E: the sealed original, unchanged, against the post-edit GitHub state
        run_checks("X_div", "E_original_vs_post_edit_state", sealed, fresh, results["post_edit"], stem="X_div.E_original_vs_post_edit_state")
        post = json.loads(fresh.read_text())
        authorized_len = None
        # A8+E full rewrite: operator edits the comment back, rewrites classification AND the observation to match, re-seals
        ev = copy.deepcopy(read_jsonl(unsealed))
        i = idx(ev, "TOOL_RESULT")
        ev[i]["payload"]["body_sha256"] = post["body_sha256"]
        ev[i]["payload"]["body_length"] = post["body_length"]
        ev[i]["payload"]["updated_at"] = post["updated_at"]
        j = edit_classification(ev)
        ev[j]["payload"]["observed_body_sha256"] = post["body_sha256"]
        rechain(ev, i)
        tmp = ART / "tampered" / "X_div.a8e_full_rewrite_unsealed.jsonl"
        write_jsonl(tmp, ev)
        full = ART / "tampered" / "X_div.a8e_full_rewrite_genuine_reseal.jsonl"
        seal(tmp, full, SERVER_A)
        tmp.unlink()
        run_checks("X_div", "A8E_full_rewrite_genuine_reseal", full, fresh, results["post_edit"])
        # A8+E weak rewrite (classification only) = the A8 record, against the post-edit state
        run_checks("X_div", "A8E_classification_only_rewrite", ART / "tampered" / "X_div.a8_rewrite_genuine_reseal.jsonl", fresh, results["post_edit"])
    elif mode == "originals":
        # Regenerate the three on-disk artifacts that the first run overwrote (shared basename), from the same unchanged files.
        redo = []
        for label, fresh in (("X_in", ART / "X_in" / "fresh_pre_edit.json"), ("X_div", ART / "X_div" / "fresh_pre_edit.json")):
            run_checks(label, "original", ART / label / "session_sealed.original.jsonl", fresh, redo, stem=f"{label}.original")
        run_checks("X_div", "E_original_vs_post_edit_state", ART / "X_div" / "session_sealed.original.jsonl", ART / "X_div" / "fresh_post_edit.json", redo, stem="X_div.E_original_vs_post_edit_state")
        old = {(r["label"], r["variant"]): r for r in results["build"] + results["post_edit"]}
        for r in redo:
            o = old[(r["label"], r["variant"])]
            same = (r["pinned"], r["unpinned"], r["comparator"]["flags"]) == (o["pinned"], o["unpinned"], o["comparator"]["flags"])
            print(f"{r['label']} {r['variant']}: rerun identical to first run = {same}")
        return
    else:
        raise SystemExit("mode: build | post_edit | originals")
    results_path.write_text(json.dumps(results, indent=2) + "\n")
    for r in results[mode]:
        print(f"{r['label']:6} {r['variant']:36} pinned={r['pinned']['status']}/{r['pinned']['evidence_class']} exit={r['pinned']['exit_code']} | unpinned={r['unpinned']['status']}/{r['unpinned']['evidence_class']} exit={r['unpinned']['exit_code']} | cmp_flagged={r['comparator']['flagged']} {sorted(r['comparator']['flags'])}")


main()
