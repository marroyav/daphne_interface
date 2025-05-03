# A minimal, *network-free* test-suite for daphne_app.hardware.daphne

import numpy as np
import pytest
from daphne_app.hardware.daphne import timeout_handler, _remove_control_chars, Daphne

# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------
@timeout_handler
def _slow_fn(t=0.2):
    import time
    time.sleep(t)
    return "ok"

def _make_sine(n=1024):
    t = np.arange(n)
    return np.sin(2 * np.pi * 5 * t / n) * 1000  # 5-bin sine


# ---------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------
def test_remove_ctrl():
    assert _remove_control_chars("ab\x01c\x7Fd") == "abcd"

def test_timeout():
    with pytest.raises(TimeoutError):
        _slow_fn(2)      # 2 s  »  decorator aborts after 1 s

def test_fft_helpers():
    sig = _make_sine()
    x, y = Daphne.compute_fft(sig, dt=1.0, plot=False)
    assert x.size == y.size
    assert (y < 0).all()          # magnitudes in dBFS are negative

def test_mean_fft():
    waves = [_make_sine() for _ in range(4)]
    freq, mag, rms = Daphne.compute_mean_fft(waves, dt=1.0)
    assert freq.size == mag.size
    assert rms > 0
