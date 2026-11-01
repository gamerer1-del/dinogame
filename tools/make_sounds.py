"""ゲームの効果音をすべてプログラムで合成して assets/sounds/ に書き出す。

外部の素材を使っていないので、ライセンスを気にせず配布できる。
音を変えたいときはこのファイルの数字をいじって、もう一度実行する:

    pip install numpy scipy
    python tools/make_sounds.py
"""
import os
import wave

import numpy as np
from scipy import signal

SR = 22050                      # サンプリング周波数
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "sounds")
rng = np.random.default_rng(7)  # 毎回同じ音になるよう乱数を固定


def t(sec):
    return np.arange(int(SR * sec)) / SR


def noise(sec):
    return rng.uniform(-1, 1, int(SR * sec))


def lowpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def highpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def env(n, attack, decay):
    """attack 秒で立ち上がり、decay の速さで指数的に消える包絡線"""
    tt = np.arange(n) / SR
    a = np.clip(tt / max(attack, 1e-4), 0, 1)
    return a * np.exp(-tt / decay)


def pad(x, sec):
    return np.concatenate([x, np.zeros(int(SR * sec))])


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[: len(p)] += p
    return out


def at(x, sec, total):
    """x を sec 秒の位置に置いた total 秒の配列"""
    out = np.zeros(int(SR * total))
    s = int(SR * sec)
    e = min(len(out), s + len(x))
    out[s:e] += x[: e - s]
    return out


def save(name, x, peak=0.9):
    x = np.asarray(x, dtype=float)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    fade = min(len(x), int(SR * 0.005))
    x[-fade:] *= np.linspace(1, 0, fade)
    data = (x * 32767).astype(np.int16)
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"{name:12s} {len(x) / SR:5.2f}s")


# --- 主人公 -----------------------------------------------------------------

def step():
    """コンクリートの上の足音: 低いトンという音と、靴底のこすれ"""
    n = noise(0.12)
    thump = np.sin(2 * np.pi * 85 * t(0.12)) * env(len(n), 0.002, 0.025)
    scuff = bandpass(n, 400, 3000) * env(len(n), 0.001, 0.02)
    return mix(thump * 1.2, scuff * 0.8)


def step_wet():
    """水たまりの足音: ぴちゃっという跳ね"""
    n = noise(0.35)
    splash = highpass(n, 900) * env(len(n), 0.003, 0.06)
    drops = np.zeros(len(n))
    for k in range(6):
        f = rng.uniform(900, 2200)
        s = rng.uniform(0.04, 0.22)
        drop = np.sin(2 * np.pi * f * t(0.05) * (1 + 2 * t(0.05))) * env(int(SR * 0.05), 0.001, 0.012)
        drops += at(drop, s, 0.35)
    return mix(step() * 0.6, splash, drops * 0.5)


def locker():
    """ロッカーの扉がきしんで閉まる音"""
    dur = 0.7
    tt = t(dur)
    # 摩擦できしむ音: 周波数が細かくふらつくのこぎり波
    f = 320 + 60 * np.sin(2 * np.pi * 3 * tt) + 40 * lowpass(noise(dur), 30) * 20
    phase = 2 * np.pi * np.cumsum(f) / SR
    creak = signal.sawtooth(phase) * (0.5 + 0.5 * np.abs(lowpass(noise(dur), 12) * 30).clip(0, 1))
    creak = bandpass(creak, 300, 2500) * np.clip(tt / 0.05, 0, 1) * np.clip((0.55 - tt) / 0.1, 0, 1)
    clunk = metal_hit([180, 410, 690, 1130], 0.25) * 0.8
    return mix(creak * 0.6, at(clunk, 0.55, dur + 0.25))


def metal_hit(freqs, decay):
    n = int(SR * decay * 4)
    out = np.zeros(n)
    tt = np.arange(n) / SR
    for i, f in enumerate(freqs):
        out += np.sin(2 * np.pi * f * tt) * np.exp(-tt / (decay / (1 + i * 0.4)))
    click = highpass(noise(0.01), 2000)
    return mix(out, click * 0.6)


def can():
    """空き缶が床に当たる音"""
    return mix(metal_hit([1180, 2950, 4130, 5310], 0.12), pad(metal_hit([1350, 3300], 0.06) * 0.5, 0))


def pickup():
    """拾った: 短い電子音2つ"""
    a = np.sin(2 * np.pi * 880 * t(0.09)) * env(int(SR * 0.09), 0.003, 0.05)
    b = np.sin(2 * np.pi * 1320 * t(0.14)) * env(int(SR * 0.14), 0.003, 0.07)
    return mix(a, at(b, 0.08, 0.25))


def door():
    """重い扉がうなりながら上がる音"""
    dur = 1.8
    tt = t(dur)
    grind = lowpass(noise(dur), 260, 3) * 4
    hum = signal.sawtooth(2 * np.pi * (55 + 20 * tt / dur) * tt) * 0.3
    body = (grind + lowpass(hum, 400)) * np.clip(tt / 0.15, 0, 1) * np.clip((1.6 - tt) / 0.2, 0, 1)
    clunk = metal_hit([90, 210, 370], 0.2)
    return mix(body, at(clunk, 1.55, dur + 0.6))


def heartbeat():
    """心臓の音（ドクン、ドクン）"""
    def thump(f, dur, amp):
        tt = t(dur)
        return np.sin(2 * np.pi * f * tt * (1 - 0.3 * tt / dur)) * env(len(tt), 0.006, 0.045) * amp
    return lowpass(mix(thump(55, 0.2, 1.0), at(thump(48, 0.2, 0.7), 0.17, 0.45)), 180)


def caught():
    """捕まった瞬間: 不協和音と衝撃"""
    dur = 1.6
    tt = t(dur)
    chord = sum(signal.sawtooth(2 * np.pi * f * tt) for f in [55, 58.3, 82.4, 116.5])
    chord = lowpass(chord, 900) * np.exp(-tt / 0.7)
    hit = lowpass(noise(dur), 1500) * env(len(tt), 0.002, 0.15) * 3
    return mix(chord, hit, screech() * 0.6)


def elevator():
    """クリア: エレベーターの到着チャイム"""
    def bell(f, dur):
        tt = t(dur)
        return (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-tt / 0.5)
    return mix(bell(659, 1.2), at(bell(523, 1.4), 0.45, 1.9))


# --- 恐竜 ---------------------------------------------------------------------

def dino_step():
    """恐竜の足音: 重い着地と爪が床をかく音"""
    n = noise(0.25)
    thump = np.sin(2 * np.pi * 55 * t(0.25)) * env(len(n), 0.004, 0.05)
    claws = np.zeros(len(n))
    for k in range(3):
        click = highpass(noise(0.015), 2500) * env(int(SR * 0.015), 0.0005, 0.004)
        claws += at(click, 0.02 + k * 0.025 + rng.uniform(0, 0.01), 0.25)
    return mix(lowpass(thump, 300) * 1.4, claws * 0.7)


def growl():
    """低いうなり声: のどを鳴らすようなガラガラした低音"""
    dur = 1.8
    tt = t(dur)
    f0 = 68 + 8 * np.sin(2 * np.pi * 0.7 * tt) + 3 * lowpass(noise(dur), 8) * 20
    voice = signal.sawtooth(2 * np.pi * np.cumsum(f0) / SR)
    rattle = 0.55 + 0.45 * np.sin(2 * np.pi * 22 * tt + 3 * lowpass(noise(dur), 20) * 20)
    breath = bandpass(noise(dur), 150, 900) * 0.6
    shape = np.clip(tt / 0.35, 0, 1) * np.clip((dur - tt) / 0.5, 0, 1)
    x = (voice * rattle + breath) * shape
    x = np.tanh(lowpass(x, 700) * 3)
    return lowpass(x, 900)


def snort():
    """何かに気づいたときの鼻息（フン、フッ）"""
    def puff(dur):
        n = noise(dur)
        return bandpass(n, 250, 1400) * env(len(n), 0.01, dur / 3)
    return mix(puff(0.22), at(puff(0.16) * 0.8, 0.28, 0.5))


def screech():
    """獲物を見つけたときの甲高い叫び声"""
    dur = 1.3
    tt = t(dur)
    sweep = np.interp(tt, [0, 0.15, 0.55, dur], [700, 1650, 1400, 650])
    vib = 1 + 0.04 * np.sin(2 * np.pi * 28 * tt)
    phase = 2 * np.pi * np.cumsum(sweep * vib) / SR
    tone = signal.sawtooth(phase, 0.3) + 0.5 * np.sin(phase * 2.02)
    rasp = bandpass(noise(dur), 1500, 5000) * 0.5
    shape = np.clip(tt / 0.06, 0, 1) * np.clip((dur - tt) / 0.5, 0, 1)
    x = np.tanh((tone + rasp) * shape * 2.5)
    return bandpass(x, 400, 6000)


# --- 環境音 ----------------------------------------------------------------------

def ambience():
    """停電した地下施設: 低い電源のうなり、換気の風、ときどき落ちる水滴（8秒ループ）"""
    dur = 8.0
    tt = t(dur)
    hum = sum(np.sin(2 * np.pi * f * tt) * a for f, a in [(50, 0.5), (100, 0.25), (150, 0.12)])
    hum *= 0.6 + 0.4 * np.sin(2 * np.pi * tt / dur)       # ループ長に合わせてゆっくり揺らす
    wind = lowpass(np.cumsum(noise(dur)) * 0.02, 300)
    wind = wind - lowpass(wind, 2)
    drips = np.zeros(len(tt))
    for s in [0.7, 2.9, 3.4, 5.6, 7.1]:
        f = rng.uniform(1100, 1900)
        d = np.sin(2 * np.pi * f * t(0.12) * (1 + 1.5 * t(0.12))) * env(int(SR * 0.12), 0.001, 0.025)
        drips += at(d, s, dur)
    x = hum * 0.35 + wind * 2.0 + drips * 0.25
    # 継ぎ目が目立たないよう、頭と尻を少し重ねる
    cf = int(SR * 0.3)
    x[:cf] = x[:cf] * np.linspace(0, 1, cf) + x[-cf:] * np.linspace(1, 0, cf)
    return highpass(x[: len(x) - cf], 30)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn, peak in [
        ("step", step, 0.8), ("step_wet", step_wet, 0.85), ("locker", locker, 0.8),
        ("can", can, 0.8), ("pickup", pickup, 0.6), ("door", door, 0.9),
        ("heartbeat", heartbeat, 0.95), ("caught", caught, 0.95), ("elevator", elevator, 0.7),
        ("dino_step", dino_step, 0.9), ("growl", growl, 0.9), ("snort", snort, 0.8),
        ("screech", screech, 0.9), ("ambience", ambience, 0.5),
    ]:
        save(name, fn(), peak)
