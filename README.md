# gamAI Evidence Dashboard

Static, dependency-free dashboard that publishes the **measured** evidence behind the gamAI agent trust layer. Every number is reproducible from the linked repositories.

`index.html` is **generated**, not authored: `render.py` recomputes each figure from the crossnode-bench v1.4.0 result files and refuses to build if those files are not the released bytes. There are no hand-typed numbers on the page.

- **Live:** https://demo.gamai.io
- GitHub Pages: https://gamai-io.github.io/demo/

## What it shows

All figures below are from **crossnode-bench v1.4.0**, which ships the record files and hashes.

| Run | Setup | Result |
|---|---|---|
| Honest fleet | 16 tasks x 200 rounds, 8 Vultr `vc2-1c-1gb` + Contabo | 25,600/25,600 pass (100%), **0** false successes (P1/P2 probes require an adapter and ran on the local node only) |
| Controlled liar | same fleet + one `MockLiar` wrapper on `vultr-lax` | 28,800 records, 28,400/28,800 pass (98.61%), **400 false successes (1.39%) — all 400 on the lying node** |

The second run is a *detection* test: the benchmark counted the liar's claims as false
successes, it did not pass them. Artifact: `liar/evidence.jsonl.gz`
sha256 `372851594aae1ee554a46b817a0c466fad3edda4f3e9a0ecff2df9a081789674`.

**Correction 2026-11-23.** The page used to show "25,600 trials (LUMI-C) / pass 93.75% /
6.25% flagged", which merged an honest-fleet total with a separate 25,600-trial Slurm run
(200 runs x 16 tasks x 8 nodes). That Slurm run is reported in `evidence-gate-runtime`
but its dataset is **not public yet**, so it is no longer shown as evidence here.

## Reproduce

```bash
pip install gamai-trust
gamai-trust demo        # proofgate + agent-immunity + crossnode, one JSON

# shipped run (crossnode-bench v1.4.0): honest fleet 25,600/25,600, 0 false successes
# controlled liar variant: 28,800 records, 400 false successes, all on the MockLiar node
# reproduce: see crossnode-bench README + repro.sh (that repo ships the records)
```

## Repos

| Repo | What it proves |
|---|---|
| [gamai-trust](https://github.com/gamai-io/gamai-trust) | verify claims, remember refusals, score false success |
| [sigil](https://github.com/gamai-io/sigil) | proof-carrying execution profile (SIGIL/1) |
| [crossnode-bench](https://github.com/gamai-io/crossnode-bench) | agent honesty across heterogeneous nodes |
| [gamai-guard](https://github.com/gamai-io/gamai-guard) | multilingual prompt-injection guard (29/30 blocked, 0/10 FP — not machine-checked here) |

## Refreshing the page

`index.html` is output. Do not edit it by hand — `make verify` fails if the committed
file differs from what the artifacts produce.

```bash
make build     # fetch crossnode-bench v1.4.0 result files into ./artifacts/, regenerate index.html
make verify    # regenerate into memory; exit 1 if index.html is stale or hand-edited
```

How it works:

- `render.py` reads `artifacts/honest/` and `artifacts/liar/` — `evidence.jsonl.gz`
  (one JSON record per trial), `report.json` and `false_success.jsonl` — and recomputes
  every figure on the page from the per-trial records: counts, pass rate, false-success
  count/share/node/tasks, p50/p95 latency (nearest-rank) and node inventory.
- Every number is printed to stdout as a table with its `file#field` source. Each figure
  in the HTML carries the same `data-source` attribute.
- `PINNED` in `render.py` holds the sha256 of all six input files. A missing file or a
  hash mismatch aborts the build; so does any disagreement between `evidence.jsonl.gz`
  and the shipped `report.json` / `false_success.jsonl`.
- The page is rendered from `page.template.html`; the template holds the layout and the
  `data-source` markers, never a figure.
- `.github/workflows/verify.yml` runs `render.py --check` against a checkout of
  crossnode-bench `v1.4.0` on every push.

Pointing at an existing checkout instead of downloading:

```bash
python3 render.py --artifacts /path/to/crossnode-bench/results/vultr-fleet-2026-11-09-200
```

**Deliberate refresh.** When crossnode-bench publishes a new artifact set: update
`ARTIFACT_SET`/`UPSTREAM`, replace the six entries in `PINNED` with the new sha256s,
adjust the paths if the results folder moved, then `make build`, inspect the printed
value table and the diff, and commit `index.html` together with `render.py`. Changing a
number without changing an artifact hash is not possible, which is the point.

**Not machine-checked.** The "Validated on EuroHPC LUMI" badge and the numbers for the
other repos (e.g. gamai-guard's 29/30) are not derived from these artifacts; the page
does not claim them as generated, and the guard figures are labelled as unchecked in
this README.

## Honest limits

v0.x. The trust layer **reports** state; it does not make an agent honest. Every repo ships `repro.sh` — verify it yourself. We publish evidence, not slogans.

## License

Apache-2.0. See `LICENSE`.
