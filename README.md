# gamAI Evidence Dashboard

Static, dependency-free dashboard that publishes the **measured** evidence behind the gamAI agent trust layer. Every number is reproducible from the linked repositories.

- **Live:** https://demo.gamai.io
- GitHub Pages: https://gamai-io.github.io/demo/

## What it shows

All figures below are from **crossnode-bench v1.4.0**, which ships the record files and hashes.

| Run | Setup | Result |
|---|---|---|
| Honest fleet | 16 tasks x 200 rounds, 8 Vultr `vc2-1c-1gb` + Contabo | 25,600/25,600 pass (100%), **0** false successes |
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
| [gamai-guard](https://github.com/gamai-io/gamai-guard) | multilingual prompt-injection guard (29/30 blocked, 0/10 FP) |

## Honest limits

v0.x. The trust layer **reports** state; it does not make an agent honest. Every repo ships `repro.sh` — verify it yourself. We publish evidence, not slogans.

## License

Apache-2.0. See `LICENSE`.
