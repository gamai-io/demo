# gamAI Evidence Dashboard

Static, dependency-free dashboard that publishes the **measured** evidence behind the gamAI agent trust layer. Every number is reproducible from the linked repositories.

- **Live:** https://demo.gamai.io
- GitHub Pages: https://gamai-io.github.io/demo/

## What it shows

- **25,600** cross-node claim-vs-truth trials (EuroHPC LUMI-C, 8 nodes, CPU only)
- **0** false-success on read / action / cross
- **6.25%** dishonest claims flagged (1,600), verified per probe
- **2.4 ms** median probe latency (p95 10.8 ms)

## Reproduce

```bash
pip install gamai-trust
gamai-trust demo        # proofgate + agent-immunity + crossnode, one JSON

# 25,600-trial run (LUMI-C, ~0 GPU-h):
sbatch --partition=standard --nodes=8 --export=ALL,RUNS=200 sbatch-f2-crossnode.sh
# 25,600 trials | pass 93.75% | false-success 6.25% | 0 on read/action/cross
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
