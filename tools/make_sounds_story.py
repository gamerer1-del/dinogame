"""プロローグと扉の効果音を合成して assets/sounds/ に書き出す（numpy だけで動く）。

    python tools/make_sounds_story.py

thunder 雷 / alarm 警報 / bang 扉への体当たり / break 扉が壊れる / slam 扉を閉める
"""
import os
import wave

import numpy as np

SR = 22050
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sounds")
rng = np.random.default_rng(11)


def t(sec):
    return np.arange(int(SR * sec)) / SR


def noise(sec):
    return rng.uniform(-1, 1, int(SR * sec))


def smooth(x, k):
    """移動平均の簡単なローパス。k が大きいほどこもった音になる。"""
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, mode="same")


def env(n, attack, decay):
    tt = np.arange(n) / SR
    return np.clip(tt / max(attack, 1e-4), 0, 1) * np.exp(-tt / decay)


def save(name, x):
    x = x / max(np.abs(x).max(), 1e-6) * 0.9
    data = (x * 32767).astype(np.int16)
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def thunder():
    sec = 5.0
    crack = smooth(noise(sec), 3) * env(int(SR * sec), 0.005, 0.25)
    rumble = smooth(noise(sec), 60) * env(int(SR * sec), 0.08, 1.6) * 6
    roll = smooth(noise(sec), 120) * (0.5 + 0.5 * np.sin(t(sec) * 3.1)) * env(int(SR * sec), 0.4, 2.2) * 8
    return crack + rumble + roll


def alarm():
    sec = 4.0
    tt = t(sec)
    f = 620 + 260 * (np.sin(tt * 2 * np.pi * 0.9) > 0)   # ピーポー
    phase = np.cumsum(2 * np.pi * f / SR)
    x = np.sign(np.sin(phase)) * 0.4 + np.sin(phase * 2) * 0.2
    return smooth(x, 4) * np.clip(tt / 0.05, 0, 1) * np.clip((sec - tt) / 0.3, 0, 1)


def bang():
    sec = 1.2
    n = int(SR * sec)
    hit = smooth(noise(sec), 8) * env(n, 0.002, 0.08)
    body = np.sin(2 * np.pi * 70 * t(sec)) * env(n, 0.002, 0.25) * 0.8
    ring = np.sin(2 * np.pi * 410 * t(sec)) * env(n, 0.002, 0.4) * 0.15
    return hit + body + ring


def break_():
    sec = 2.0
    n = int(SR * sec)
    out = bang()[: n] if len(bang()) >= n else np.pad(bang(), (0, n - len(bang())))
    for i in range(14):
        start = int(SR * (0.1 + rng.uniform(0, 1.2)))
        clank = smooth(noise(0.3), 2) * env(int(SR * 0.3), 0.001, 0.05) * rng.uniform(0.2, 0.6)
        out[start:start + len(clank)] += clank[: n - start]
    crash = np.sin(2 * np.pi * 55 * t(sec)) * env(n, 0.3, 0.4) * 0.6
    return out + np.roll(crash, int(SR * 0.3))


def slam():
    sec = 0.8
    n = int(SR * sec)
    scrape = smooth(noise(sec), 2) * np.clip(t(sec) / 0.35, 0, 1) * (t(sec) < 0.35) * 0.25
    hit = np.roll(bang()[:n] * 0.8, int(SR * 0.35))
    return scrape + hit


if __name__ == "__main__":
    for name, fn in (("thunder", thunder), ("alarm", alarm), ("bang", bang), ("break", break_), ("slam", slam)):
        save(name, fn())
        print("wrote", name)
