# my_channels.py  –  global CH numbers, or per-AFE if you prefer
channels_to_acquire = {
    0: [0, 7],             # AFE 0  → CH 0 and CH 7
    1: [0, 7],             # AFE 1  → CH 8 and CH 15
    2: [0, 7],             # …
    3: [0, 7],
    4: list(range(8)),     # all 8 channels on AFE 4
}
