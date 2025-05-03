
# DAPHNE Interface CLI

A friendly command‑line wrapper (based on **Typer**) to configure,
calibrate and debug DAPHNE front‑end boards from NP/LAr test‑stands.

```
$ daphne --help
Usage: daphne [OPTIONS] COMMAND [ARGS]...
```

---

## Installation

```bash
git clone <your fork>
cd daphne_interface
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

---

## Shell completion

```bash
# Bash
eval "$(daphne --install-completion bash)"
# Z‑sh
eval "$(daphne --install-completion zsh)"
# Fish
eval "$(daphne --install-completion fish)"
```

---

## Command cheat‑sheet

| Area                  | Skeleton                              | Note |
|-----------------------|---------------------------------------|------|
| Configure            | `daphne configure json FILE`          | apply full JSON config |
| Spy buffer capture   | `daphne capture plotly [opts]`        | interactive Plotly HTML |
| Offset calibration   | `daphne calibrate offsets [opts]`     | adaptive self‑centring |
| Read‑backs           | `daphne check bias|trim|self-trigger` | inspect registers |
| Low‑level helpers    | `daphne set bias|trim …`              | scripting use |

---

### Offset‑DAC example

```bash
daphne calibrate offsets --details details.json \
                         --target 4000 --band 2 \
                         --samples 4000 --n-wf 20 \
                         --step-init 50 --max-iters 20 \
                         --save-json best_offsets.json
```

Key points: dynamic step (min 1), median baseline on first 128 samples,
safe DAC window 1500‑3000, log+PNG artefacts.

---

### Spy‑buffer example

```bash
daphne capture plotly --details details.json \
                      --samples 4000 --n-wf 10 \
                      --trigger aligned --html wf.html
```

*Trigger modes*:  
*software* ⇒ write 0x2000 once per read.  
*aligned*  ⇒ write 0x2020 & 0x2021 for centred buffer.

---

## Contributing

Run tests with `pytest`.  Pre‑commit hooks via `pre-commit install`.

---

© 2025 DUNE collaboration – MIT licence.

