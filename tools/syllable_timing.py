# -*- coding: utf-8 -*-
"""
音声ファイルから「何秒目にどの音節を読んでいるか」を見つける。

    times(mp3, n_syllables, clause_breaks)
    → ([0.31, 0.52, 0.80, ...], 2.95)      # 各音節の読みはじめ（秒）, 読み終わり（秒）

clause_breaks は、文の途中の句読点の前にある音節の数（例：老师，您好 → [2]）。
録音の中の「間（ま）」を句読点に合わせ、その区間の中で音の強弱の谷を探して音節を区切る。

ffmpeg と numpy が必要。どちらかがなければ None を返し、
ページ側（kaiwa.js）が音声の長さから目安で表示する。
"""
import shutil
import subprocess

try:
    import numpy as np
except ImportError:            # numpy がない環境では使わない
    np = None

RATE = 16000
HOP = 0.01                     # 10 ミリ秒ごとに音の大きさを測る


def available():
    return np is not None and shutil.which("ffmpeg") is not None


def _envelope(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
        stdout=subprocess.PIPE, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    hop, win = int(RATE * HOP), int(RATE * 0.025)
    if len(x) < win:
        return None
    n = 1 + (len(x) - win) // hop
    frames = np.lib.stride_tricks.as_strided(x, shape=(n, win), strides=(x.strides[0] * hop, x.strides[0]))
    rms = np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    # 少しなめらかにする（50 ミリ秒）
    k = np.ones(5) / 5
    return np.convolve(db, k, mode="same")


def _runs(mask):
    """True が続く区間を [(はじめ, おわり), ...] で返す（おわりは含まない）"""
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def times(path, n, clause_breaks=()):
    if n <= 0 or not available():
        return None
    try:
        env = _envelope(path)
    except Exception:
        return None
    if env is None:
        return None

    floor, peak = np.percentile(env, 10), np.percentile(env, 99)
    thr = max(floor + 10, peak - 35)
    speech = env > thr

    # 短すぎる途切れ（60ms 未満）はつなげ、短すぎる雑音（40ms 未満）は消す
    for a, b in _runs(~speech):
        if b - a < 6 and a > 0 and b < len(speech):
            speech[a:b] = True
    for a, b in _runs(speech):
        if b - a < 4:
            speech[a:b] = False

    regions = _runs(speech)
    if not regions:
        return None
    s0, s1 = regions[0][0], regions[-1][1]

    # 文中の「間」（150ms 以上の無音）
    pauses = [(a, b) for a, b in _runs(~speech[s0:s1]) if b - a >= 15]
    pauses = [(a + s0, b + s0) for a, b in pauses]

    # 「間」と句読点を対応させる。
    # 句読点があっても間をあけずに読むことも、句読点がなくても息つぎすることもあるので、
    # 「声が出ていた時間」で測った位置がいちばん近いもの同士だけを組にする。
    breaks = [c for c in clause_breaks if 0 < c < n]
    voiced_total = int(speech[s0:s1].sum()) or 1
    per_syl = voiced_total / n                                   # 1 音節あたりの声の長さ
    p_pos = [int(speech[s0:a].sum()) / per_syl for a, _ in pauses]   # 間の位置（音節いくつ目か）
    P, K, SKIP = len(pauses), len(breaks), 1.0
    cost = [[0.0] * (K + 1) for _ in range(P + 1)]
    move = [[None] * (K + 1) for _ in range(P + 1)]
    for i in range(1, P + 1):
        cost[i][0], move[i][0] = cost[i - 1][0] + SKIP, "p"
    for j in range(1, K + 1):
        cost[0][j], move[0][j] = cost[0][j - 1] + SKIP, "b"
    for i in range(1, P + 1):
        for j in range(1, K + 1):
            options = [(cost[i - 1][j] + SKIP, "p"), (cost[i][j - 1] + SKIP, "b"),
                       (cost[i - 1][j - 1] + abs(p_pos[i - 1] - breaks[j - 1]), "m")]
            cost[i][j], move[i][j] = min(options)
    pairs = []
    i, j = P, K
    while i > 0 or j > 0:
        mv = move[i][j]
        if mv == "m":
            pairs.append((pauses[i - 1], breaks[j - 1]))
            i, j = i - 1, j - 1
        elif mv == "p":
            i -= 1
        else:
            j -= 1
    pairs.reverse()

    # 句読点のない所での息つぎも、音節の切れ目にはちがいない。
    # その前に音節がいくつあるかは「声が出ていた時間」から見積もる（句読点と組になった間は確定）。
    fixed = {pa: brk for pa, brk in pairs}
    cuts = []                                     # [(間, その前の音節数)]
    prev = 0
    for idx, pa in enumerate(pauses):
        if pa in fixed:
            cnt = fixed[pa]
        else:
            nxt = next((fixed[q] for q in pauses[idx + 1:] if q in fixed), n)
            cnt = int(round(p_pos[idx]))
            if not prev < cnt < nxt:
                continue                          # 入る場所がなければ、区切りには使わない
        if cnt <= prev:
            continue
        cuts.append((pa, cnt))
        prev = cnt

    # 「間」で区切り、それぞれの区間に音節を割りふる
    segs, prev_end, prev_cnt = [], s0, 0
    for (pa, pb), cnt in cuts:
        segs.append((prev_end, pa, cnt - prev_cnt))
        prev_end, prev_cnt = pb, cnt
    segs.append((prev_end, s1, n - prev_cnt))

    starts = []
    for a, b, cnt in segs:
        if cnt <= 0:
            continue
        # 区間の中の「声が出ている時間」だけを等分し、その近くの音の谷に合わせる
        voiced = np.flatnonzero(speech[a:b]) + a
        if len(voiced) < cnt:
            voiced = np.arange(a, b)
        step = len(voiced) / cnt
        prev = a
        for j in range(cnt):
            if j == 0:
                t = voiced[0]
            else:
                guess = voiced[min(len(voiced) - 1, int(round(j * step)))]
                w = max(3, int(step * 0.3))
                lo, hi = max(prev + 5, guess - w), min(b - 1, guess + w)
                t = lo + int(np.argmin(env[lo:hi + 1])) if hi > lo else guess
            starts.append(int(t))
            prev = int(t)

    return [round(f * HOP, 2) for f in starts], round(s1 * HOP, 2)
