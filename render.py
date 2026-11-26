#!/usr/bin/env python3
"""Generate index.html from the crossnode-bench v1.4.0 result files.

Nothing on the page is typed by hand: every number is recomputed here from
``evidence.jsonl.gz`` (one JSON record per trial) and cross-checked against the
shipped ``report.json`` / ``false_success.jsonl``.  The result files themselves
are pinned by sha256 in ``PINNED`` below, so a swapped or edited artifact fails
the build instead of silently changing the page.

Usage:
    python3 render.py                     # write index.html
    python3 render.py --check             # compare against committed index.html
    python3 render.py --artifacts DIR     # read result files from DIR
    python3 render.py --print-values      # dump the value table only

DIR may be the release folder (contains ``honest/`` and ``liar/``), the
``results/`` parent, or a crossnode-bench checkout root.  Stdlib only.
"""

import argparse
import difflib
import gzip
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

ARTIFACT_SET = "crossnode-bench v1.4.0 :: results/vultr-fleet-2026-11-09-200"
UPSTREAM = "https://github.com/gamai-io/crossnode-bench/tree/v1.4.0/results/vultr-fleet-2026-11-09-200"

# sha256 of the input files as published. A mismatch is a hard failure: the
# page must not be regenerated from different bytes without a deliberate edit
# to this table (see README, "Refreshing the page").
PINNED = {
    "honest/evidence.jsonl.gz": "960b661424b2c2a147ad2179d15aeab357a34ce6e45b3e8564066fe824e87049",
    "liar/evidence.jsonl.gz": "372851594aae1ee554a46b817a0c466fad3edda4f3e9a0ecff2df9a081789674",
    "honest/report.json": "48b1bfdb7fa1fca1991a934810851e13f8867a26807b3d657d2b63b36ceaae4e",
    "liar/report.json": "aee9107cb21da4576935113048ef3c466adfe173bfefe59b59150fbe2ad3a1eb",
    "honest/false_success.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "liar/false_success.jsonl": "e47f0c21b46a46f9e8bdcec1ed1d2c5d224c46967aa301d0c2d9b1e65710eda3",
}

# Where the four result folders may live under --artifacts.
SEARCH_ROOTS = (
    "",
    "results/vultr-fleet-2026-11-09-200",
    "vultr-fleet-2026-11-09-200",
    "artifacts",
    "artifacts/vultr-fleet-2026-11-09-200",
)

REQUIRED_ROW_KEYS = ("run", "node", "task", "kind", "ms", "passed", "false_success")


class Fail(Exception):
    """Artifact or consistency problem: exit 1."""


# --------------------------------------------------------------------------
# loading + hashing
# --------------------------------------------------------------------------

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def locate(root, rel):
    for base in SEARCH_ROOTS:
        path = os.path.normpath(os.path.join(root, base, rel))
        if os.path.isfile(path):
            return path
    raise Fail(
        "missing artifact %r under %s (looked in: %s)"
        % (rel, root, ", ".join(repr(b or ".") for b in SEARCH_ROOTS))
    )


def read_artifact(root, rel):
    path = locate(root, rel)
    with open(path, "rb") as fh:
        data = fh.read()
    digest = sha256_bytes(data)
    expected = PINNED[rel]
    if digest != expected:
        raise Fail(
            "sha256 mismatch for %s\n  expected %s (pinned)\n  actual   %s\n"
            "  refusing to render: the artifact bytes are not the released ones"
            % (path, expected, digest)
        )
    return data, digest


def load_evidence(data, label):
    rows = []
    try:
        text = gzip.decompress(data).decode("utf-8")
    except OSError as exc:
        raise Fail("%s: not a gzip stream (%s)" % (label, exc))
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise Fail("%s:%d: invalid JSON (%s)" % (label, lineno, exc))
        missing = [k for k in REQUIRED_ROW_KEYS if k not in row]
        if missing:
            raise Fail("%s:%d: record lacks %s" % (label, lineno, ", ".join(missing)))
        if not isinstance(row["passed"], bool) or not isinstance(row["false_success"], bool):
            raise Fail("%s:%d: passed/false_success are not booleans" % (label, lineno))
        if not isinstance(row["ms"], (int, float)) or row["ms"] < 0:
            raise Fail("%s:%d: bad latency %r" % (label, lineno, row["ms"]))
        if row["false_success"] and row["passed"]:
            # A false success is a claim the gate rejected; it can never pass.
            raise Fail("%s:%d: record is both false_success and passed" % (label, lineno))
        rows.append(row)
    if not rows:
        raise Fail("%s: no records" % label)
    return rows


# --------------------------------------------------------------------------
# recomputation
# --------------------------------------------------------------------------

def percentile(values, pct):
    """Nearest-rank percentile on the raw per-trial latencies."""
    ordered = sorted(values)
    rank = max(1, int(math.ceil(pct / 100.0 * len(ordered))))
    return float(ordered[rank - 1])


def stats(rows, label):
    records = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    false_success = sum(1 for r in rows if r["false_success"])
    nodes = sorted({r["node"] for r in rows})
    vultr = [n for n in nodes if n.startswith("vultr-") and not n.endswith("-liar")]
    fs_rows = [r for r in rows if r["false_success"]]
    latencies = [float(r["ms"]) for r in rows]
    out = {
        "records": records,
        "passed": passed,
        "false_success": false_success,
        "pass_pct": passed / records * 100.0,
        "false_success_pct": false_success / records * 100.0,
        "tasks": len({r["task"] for r in rows}),
        "runs": len({r["run"] for r in rows}),
        "nodes": len(nodes),
        "vultr_nodes": len(vultr),
        "vultr_node_names": vultr,
        "node_names": nodes,
        "p50": round(percentile(latencies, 50), 1),
        "p95": round(percentile(latencies, 95), 1),
        "fs_nodes": sorted({r["node"] for r in fs_rows}),
        "fs_tasks": sorted({r["task"] for r in fs_rows}),
        "probe_nodes": sorted({r["node"] for r in rows if r["kind"] == "probe"}),
        "probes": sum(1 for r in rows if r["kind"] == "probe"),
        "kinds": sorted({r["kind"] for r in rows}),
    }
    if passed > records:
        raise Fail("%s: passed (%d) > records (%d)" % (label, passed, records))
    return out


def check_report(payload, computed, label):
    """The shipped summary must agree with the recomputation; if it does not,
    the artifact set is inconsistent and we stop instead of picking a winner."""
    try:
        report = json.loads(payload.decode("utf-8"))
    except ValueError as exc:
        raise Fail("%s: invalid JSON (%s)" % (label, exc))

    exact = {
        "records": computed["records"],
        "passed": computed["passed"],
        "false_success": computed["false_success"],
        "tasks": computed["tasks"],
        "runs": computed["runs"],
    }
    for key, value in exact.items():
        if report.get(key) != value:
            raise Fail(
                "%s: %s says %r but evidence.jsonl.gz yields %r"
                % (label, key, report.get(key), value)
            )
    approx = (
        ("pass_rate", computed["pass_pct"] / 100.0, 0.0005),
        ("false_success_rate", computed["false_success_pct"] / 100.0, 0.0005),
        ("latency_ms.p50", computed["p50"], 0.05),
        ("latency_ms.p95", computed["p95"], 0.05),
    )
    for key, value, tol in approx:
        if key.startswith("latency_ms."):
            got = (report.get("latency_ms") or {}).get(key.split(".", 1)[1])
        else:
            got = report.get(key)
        if got is None:
            raise Fail("%s: %s is missing from report.json" % (label, key))
        if abs(float(got) - float(value)) > tol:
            raise Fail(
                "%s: %s says %r but evidence.jsonl.gz yields %r"
                % (label, key, got, value)
            )
    return report


def check_false_success_file(payload, computed, label):
    lines = [ln for ln in payload.decode("utf-8").splitlines() if ln.strip()]
    if len(lines) != computed["false_success"]:
        raise Fail(
            "%s: %d lines but %d false-success records in evidence.jsonl.gz"
            % (label, len(lines), computed["false_success"])
        )
    nodes = sorted({json.loads(ln)["node"] for ln in lines})
    if nodes != computed["fs_nodes"]:
        raise Fail(
            "%s: nodes %s disagree with evidence.jsonl.gz %s"
            % (label, nodes, computed["fs_nodes"])
        )


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def build_values(root):
    hashes = {}
    evidence = {}
    reports = {}

    for run in ("honest", "liar"):
        gz, gz_sha = read_artifact(root, "%s/evidence.jsonl.gz" % run)
        hashes["%s/evidence.jsonl.gz" % run] = gz_sha
        evidence[run] = load_evidence(gz, "%s/evidence.jsonl.gz" % run)

        rj, rj_sha = read_artifact(root, "%s/report.json" % run)
        hashes["%s/report.json" % run] = rj_sha
        reports[run] = check_report(rj, stats(evidence[run], run), "%s/report.json" % run)

        fs, fs_sha = read_artifact(root, "%s/false_success.jsonl" % run)
        hashes["%s/false_success.jsonl" % run] = fs_sha
        check_false_success_file(fs, stats(evidence[run], run), "%s/false_success.jsonl" % run)

    honest = stats(evidence["honest"], "honest")
    liar = stats(evidence["liar"], "liar")

    # Nodes do not all run the same task set (probes only exist on nodes that
    # expose a probe adapter), so the per-record count is checked per node.
    for label in ("honest", "liar"):
        for node in sorted({r["node"] for r in evidence[label]}):
            rows = [r for r in evidence[label] if r["node"] == node]
            runs = len({r["run"] for r in rows})
            tasks = len({r["task"] for r in rows})
            if len(rows) != runs * tasks:
                raise Fail(
                    "%s/%s: %d records != %d runs x %d tasks"
                    % (label, node, len(rows), runs, tasks)
                )
    for label, st in (("honest", honest), ("liar", liar)):
        run_counts = {len({r["run"] for r in evidence[label] if r["node"] == n})
                      for n in {r["node"] for r in evidence[label]}}
        if run_counts != {st["runs"]}:
            raise Fail(
                "%s: nodes disagree on the number of runs (%s)"
                % (label, sorted(run_counts))
            )

    v = {
        "artifact_set": ARTIFACT_SET,
        "upstream": UPSTREAM,

        "honest_records": "{:,}".format(honest["records"]),
        "honest_passed": "{:,}".format(honest["passed"]),
        "honest_false_success": "{:,}".format(honest["false_success"]),
        "honest_tasks": "{:,}".format(honest["tasks"]),
        "honest_runs": "{:,}".format(honest["runs"]),
        "honest_vultr_nodes": "{:,}".format(honest["vultr_nodes"]),
        "honest_node_names": ", ".join(honest["vultr_node_names"]),
        "honest_probe_nodes": ", ".join(honest["probe_nodes"]),
        "honest_probes": "{:,}".format(honest["probes"]),
        "honest_vultr_kinds": "/".join(
            sorted({r["kind"] for r in evidence["honest"] if r["node"].startswith("vultr-")})
        ),
        "honest_p50": "%.1f" % honest["p50"],
        "honest_p95": "%.1f" % honest["p95"],
        "honest_sha256": hashes["honest/evidence.jsonl.gz"],
        "honest_ts": reports["honest"].get("ts", ""),

        "liar_records": "{:,}".format(liar["records"]),
        "liar_passed": "{:,}".format(liar["passed"]),
        "liar_false_success": "{:,}".format(liar["false_success"]),
        "liar_pass_pct": "%.2f" % liar["pass_pct"],
        "liar_fs_pct": "%.2f" % liar["false_success_pct"],
        "liar_fs_nodes": ", ".join(liar["fs_nodes"]),
        "liar_fs_tasks": ", ".join(liar["fs_tasks"]),
        "liar_p50": "%.1f" % liar["p50"],
        "liar_p95": "%.1f" % liar["p95"],
        "liar_sha256": hashes["liar/evidence.jsonl.gz"],
        "liar_ts": reports["liar"].get("ts", ""),
        "liar_nodes": "{:,}".format(liar["nodes"]),
    }
    return v, hashes, honest, liar


def render(template, values):
    html = template
    for key, value in values.items():
        token = "{{%s}}" % key
        html = html.replace(token, value)
    leftover = html.count("{{")
    if leftover:
        raise Fail("template has %d unsubstituted placeholder(s)" % leftover)
    return html


def print_tables(values, hashes, honest, liar):
    rows = [
        ("honest records", values["honest_records"], "honest/evidence.jsonl.gz#records"),
        ("honest passed", values["honest_passed"], "honest/evidence.jsonl.gz#passed"),
        ("honest false_success", values["honest_false_success"], "honest/evidence.jsonl.gz#false_success"),
        ("honest tasks", values["honest_tasks"], "honest/evidence.jsonl.gz#task"),
        ("honest runs", values["honest_runs"], "honest/evidence.jsonl.gz#run"),
        ("honest vultr nodes", values["honest_vultr_nodes"], "honest/evidence.jsonl.gz#node"),
        ("honest probe nodes", values["honest_probe_nodes"], "honest/evidence.jsonl.gz#kind=probe"),
        ("honest p50 ms", values["honest_p50"], "honest/evidence.jsonl.gz#ms"),
        ("honest p95 ms", values["honest_p95"], "honest/evidence.jsonl.gz#ms"),
        ("liar records", values["liar_records"], "liar/evidence.jsonl.gz#records"),
        ("liar passed", values["liar_passed"], "liar/evidence.jsonl.gz#passed"),
        ("liar pass %", values["liar_pass_pct"], "liar/evidence.jsonl.gz#passed/records"),
        ("liar false_success", values["liar_false_success"], "liar/evidence.jsonl.gz#false_success"),
        ("liar false_success %", values["liar_fs_pct"], "liar/evidence.jsonl.gz#false_success/records"),
        ("liar false_success nodes", values["liar_fs_nodes"], "liar/evidence.jsonl.gz#false_success,node"),
        ("liar false_success tasks", values["liar_fs_tasks"], "liar/evidence.jsonl.gz#false_success,task"),
        ("liar p50 ms", values["liar_p50"], "liar/evidence.jsonl.gz#ms"),
        ("liar p95 ms", values["liar_p95"], "liar/evidence.jsonl.gz#ms"),
    ]
    width = max(len(r[0]) for r in rows)
    src = max(len(r[2]) for r in rows)
    print("recomputed from artifacts (%s)" % ARTIFACT_SET)
    print("%-*s  %-10s  %-*s" % (width, "value", "", src, "source"))
    for name, value, source in rows:
        print("%-*s  %-10s  %-*s" % (width, name, value, src, source))
    print()
    print("input sha256 (pinned, verified)")
    for rel in PINNED:
        print("  %-28s %s  ok" % (rel, hashes[rel]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifacts", default=os.path.join(HERE, "artifacts"),
                    help="directory holding the crossnode-bench result files")
    ap.add_argument("--template", default=os.path.join(HERE, "page.template.html"))
    ap.add_argument("--out", default=os.path.join(HERE, "index.html"))
    ap.add_argument("--check", action="store_true",
                    help="do not write; fail if the committed page differs")
    ap.add_argument("--print-values", action="store_true",
                    help="print the recomputed table and exit")
    args = ap.parse_args(argv)

    try:
        with open(args.template, encoding="utf-8") as fh:
            template = fh.read()
        values, hashes, honest, liar = build_values(args.artifacts)
        html = render(template, values)
    except Fail as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        return 1

    print_tables(values, hashes, honest, liar)

    if args.print_values:
        return 0

    if args.check:
        try:
            with open(args.out, encoding="utf-8") as fh:
                current = fh.read()
        except FileNotFoundError:
            print("FAIL: %s does not exist; run `make build`" % args.out, file=sys.stderr)
            return 1
        if current == html:
            print("\ncheck: %s matches the artifacts" % os.path.basename(args.out))
            return 0
        diff = difflib.unified_diff(
            current.splitlines(True), html.splitlines(True),
            fromfile="committed/%s" % os.path.basename(args.out),
            tofile="generated/%s" % os.path.basename(args.out),
        )
        sys.stderr.writelines(diff)
        print(
            "\nFAIL: %s is stale or hand-edited; run `make build` and commit the result"
            % os.path.basename(args.out),
            file=sys.stderr,
        )
        return 1

    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        fh.write(html)
    print("\nwrote %s (%d bytes)" % (args.out, len(html.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
