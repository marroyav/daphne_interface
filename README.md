
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

<!-- ──────────────────────────────────────────────────────────────────────── -->
# Working with DAPHNE spy-buffer data

These short recipes show how to **capture raw wave-forms**, **save them to
disk**, and **plot / store mean-FFT spectra** for any DAPHNE endpoint.

---

## 1 · Quick one-liner from the CLI

Capture **10** wave-forms × **4000** samples from the channels listed in
`details.json`, trigger the spy-buffer in *aligned* mode, build an
interactive Plotly viewer **and** keep a compressed copy of the raw data.

```bash
daphne capture plotly \
       --details details.json      \
       --samples 4000              \
       --n-wf 10                   \
       --trigger aligned           \
       --html waveforms.html       \
       --save-wf waveforms.npz
```

## 2 · Programmatic capture inside Python


```python

import numpy as np
from daphne_app.hardware.daphne import Daphne

ip_suffix = 7                                  # board 10.73.137.107
dev = Daphne(f"10.73.137.{100 + ip_suffix}")

wave = dev.read_waveform(afe=0, ch=0,
                         samples=4000,
                         self_trigger=True)

np.savez_compressed("AFE0_CH0.npz", wave=wave)
dev.close()
print("✅  Wave-form saved to AFE0_CH0.npz")

````

*Trigger modes*:  
*software* ⇒ write 0x2000 once per read.  
*aligned*  ⇒ write 0x2020 & 0x2021 for centred buffer.

---

## Contributing

Run tests with `pytest`.  Pre‑commit hooks via `pre-commit install`.

---

© 2025 DUNE collaboration – MIT licence.

