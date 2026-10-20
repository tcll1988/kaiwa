# -*- coding: utf-8 -*-
"""
ピンインを漢字 1 文字ずつに対応させる。

    align("老师，您好！", "Lǎoshī, nínhǎo！")
    → [("老","Lǎo",False), ("师","shī",True), ("，",None,False),
       ("您","nín",False), ("好","hǎo",True), ("！",None,False)]

    3 つめは「ピンインの単語の最後の音節か」（老师 = Lǎoshī で 1 語）。

ピンインの単語（Lǎoshī など）を正しい音節に区切り、漢字の数と合うものを選ぶ。
句読点の位置も照らし合わせ、少しでも合わなければ None を返す
（そのときは、今までどおりピンインを文の下に 1 行で表示する）。
"""
import re
import unicodedata

# 声調記号 → 記号なしの母音（ü は v として扱う）
_PLAIN = {}
for base, marks in {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò",
                    "u": "ūúǔù", "v": "ǖǘǚǜü"}.items():
    for m in marks:
        _PLAIN[m] = base
        _PLAIN[m.upper()] = base

# 普通話の音節（声調なし）
_SYL = set("""
a ai an ang ao e ei en eng er o ou
yi ya yao ye you yan yang yin ying yong yu yue yuan yun
wu wa wo wai wei wan wang wen weng
ba bo bai bei bao ban ben bang beng bi biao bie bian bin bing bu
pa po pai pei pao pou pan pen pang peng pi piao pie pian pin ping pu
ma mo me mai mei mao mou man men mang meng mi miao mie miu mian min ming mu
fa fo fei fou fan fen fang feng fu
da de dai dei dao dou dan den dang deng dong di dia diao die diu dian ding du duo dui duan dun
ta te tai tao tou tan tang teng tong ti tiao tie tian ting tu tuo tui tuan tun
na ne nai nei nao nou nan nen nang neng nong ni niao nie niu nian nin niang ning nu nuo nuan nv nve
la le lo lai lei lao lou lan lang leng long li lia liao lie liu lian lin liang ling lu luo luan lun lv lve
ga ge gai gei gao gou gan gen gang geng gong gu gua guo guai gui guan gun guang
ka ke kai kei kao kou kan ken kang keng kong ku kua kuo kuai kui kuan kun kuang
ha he hai hei hao hou han hen hang heng hong hu hua huo huai hui huan hun huang
ji jia jiao jie jiu jian jin jiang jing jiong ju jue juan jun
qi qia qiao qie qiu qian qin qiang qing qiong qu que quan qun
xi xia xiao xie xiu xian xin xiang xing xiong xu xue xuan xun
zha zhe zhi zhai zhei zhao zhou zhan zhen zhang zheng zhong zhu zhua zhuo zhuai zhui zhuan zhun zhuang
cha che chi chai chao chou chan chen chang cheng chong chu chua chuo chuai chui chuan chun chuang
sha she shi shai shei shao shou shan shen shang sheng shu shua shuo shuai shui shuan shun shuang
re ri rao rou ran ren rang reng rong ru rua ruo rui ruan run
za ze zi zai zei zao zou zan zen zang zeng zong zu zuo zui zuan zun
ca ce ci cai cao cou can cen cang ceng cong cu cuo cui cuan cun
sa se si sai sao sou san sen sang seng song su suo sui suan sun
""".split())

HANZI = re.compile(r"[㐀-鿿]")
# 文の区切りになる句読点（中国語側・ピンイン側）
ZH_PUNCT = "，。！？、；：,.!?;:"
PY_PUNCT = ",.!?;:，。！？、；："


def _plain(s):
    return "".join(_PLAIN.get(c, c) for c in s).lower()


def _segmentations(word):
    """1 語（記号つきのまま）を音節に区切る方法をすべて返す（長い音節を優先）。
    各音節は (元の綴り, 儿化か) の組。"""
    plain = _plain(word)
    n = len(plain)
    memo = {}

    def go(i):
        if i == n:
            return [[]]
        if i in memo:
            return memo[i]
        out = []
        for j in range(min(n, i + 6), i, -1):
            piece = plain[i:j]
            if piece in _SYL:
                for rest in go(j):
                    out.append([(word[i:j], False)] + rest)
                # 儿化（guǎnr のように音節のあとに r が付く）
                if j < n and plain[j] == "r" and (j + 1 == n or plain[j + 1] not in "aeiouv"):
                    for rest in go(j + 1):
                        out.append([(word[i:j + 1], True)] + rest)
        memo[i] = out[:64]
        return memo[i]

    return go(0)


def _tokens(py):
    """ピンインの行を「単語」と「句読点」に分ける"""
    py = unicodedata.normalize("NFKC", py)          # 全角の Ｄ・！などを半角へ
    py = unicodedata.normalize("NFC", py)
    out = []
    for m in re.finditer(r"[A-Za-zÀ-ɏǍ-ǜü]+(?:'[A-Za-zÀ-ɏǍ-ǜü]+)*|[%s]" % re.escape(PY_PUNCT), py):
        t = m.group(0)
        out.append(("p", t) if t in PY_PUNCT else ("w", t))
    return out


def align(zh, py):
    """[(漢字の並び, ピンイン or None), ...] を返す。対応がとれなければ None。"""
    zh = re.sub(r"\s+", "", unicodedata.normalize("NFC", zh))
    units = []                                       # 漢字 1 つ、または句読点などの文字
    for c in zh:
        units.append(c)
    hanzi_idx = [i for i, c in enumerate(units) if HANZI.match(c)]
    if not hanzi_idx:
        return None

    toks = _tokens(py)
    words = []                                       # 各単語の区切り方の候補
    py_punct_after = []                              # 句読点の直前までの単語数
    for kind, t in toks:
        if kind == "w":
            parts = t.split("'")
            options = [[]]
            for p in parts:
                segs = _segmentations(p)
                if not segs:
                    return None
                options = [o + s for o in options for s in segs][:64]
            words.append(options)
        else:
            py_punct_after.append(len(words))

    # 漢字の数とぴったり合う区切り方を探す（儿化は「漢字＋儿」で 2 文字ぶん）
    target = len(hanzi_idx)
    best = None

    def search(wi, chosen, used):
        nonlocal best
        if best is not None:
            return
        if used > target:
            return
        if wi == len(words):
            if used == target:
                best = list(chosen)
            return
        for opt in words[wi]:
            cost = sum(2 if er else 1 for _, er in opt)
            chosen.append(opt)
            search(wi + 1, chosen, used + cost)
            chosen.pop()
            if best is not None:
                return

    search(0, [], 0)
    if best is None:
        return None

    # 漢字に順番に割りあてる
    syls = [s for opt in best for s in opt]
    word_last = [k == len(opt) - 1 for opt in best for k in range(len(opt))]   # 単語の最後の音節か
    word_end = []                                    # 各単語が終わる漢字の数
    count = 0
    for opt in best:
        count += sum(2 if er else 1 for _, er in opt)
        word_end.append(count)

    result = []
    si = 0
    hz_seen = 0
    i = 0
    hz_before_punct = []
    while i < len(units):
        c = units[i]
        if HANZI.match(c):
            spell, er = syls[si]
            if er:
                if i + 1 >= len(units) or units[i + 1] != "儿":
                    return None
                result.append((c + "儿", spell, word_last[si]))
                i += 2
                hz_seen += 2
            else:
                result.append((c, spell, word_last[si]))
                i += 1
                hz_seen += 1
            si += 1
        else:
            if c in ZH_PUNCT:
                hz_before_punct.append(hz_seen)
            result.append((c, None, False))
            i += 1

    # 文の途中の句読点の位置が、中国語とピンインで食いちがっていないか確かめる
    # （文末の句点のあるなしは問わない）
    py_marks = {word_end[k - 1] for k in py_punct_after if k} - {target}
    zh_marks = set(hz_before_punct) - {0, target}
    if py_marks != zh_marks:
        return None
    return result
