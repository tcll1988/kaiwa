#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初級中国語会話 — 旧ページ → 新ページ 変換ツール

使い方:
    python3 tools/convert.py <旧サイトのフォルダ> <出力フォルダ>

旧サイトのフォルダには 1k/ 2k/ … のような課フォルダと k1.html を置いてください。
第8課〜第14課を追加するときも、同じフォルダに 8k/ … を置いて実行すれば
同じデザインに変換されます。
"""
import html
import os
import re
import shutil
import sys
import unicodedata
from collections import defaultdict

# ---------------------------------------------------------------- 共通ユーティリティ

LESSON_NUM = {
    1: "１", 2: "２", 3: "３", 4: "４", 5: "５", 6: "６", 7: "７",
    8: "８", 9: "９", 10: "１０", 11: "１１", 12: "１２", 13: "１３", 14: "１４",
}


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def tidy(s):
    """全角スペース・改行・連続スペースを整理する（文字そのものは変えない）"""
    s = html.unescape(s)
    s = s.replace("　", " ").replace("&nbsp;", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def esc(s):
    return html.escape(s, quote=False)


def rel(depth):
    """ページの深さから assets/ への相対パスを作る"""
    return "../" * depth


# ---------------------------------------------------------------- ページの骨組み

def shell(title, body, depth, *, mode=True, crumb="", back=None, back_label="戻る",
          lesson_title="", bodyclass=""):
    a = rel(depth)
    head_bar = ""
    if back is not None:
        head_bar = (
            '<header class="topbar">\n'
            f'  <a class="back" href="{back}">← {esc(back_label)}</a>\n'
            f'  <h1 lang="zh-Hans">{esc(lesson_title or title)}</h1>\n'
            + (f'  <span class="crumb">{esc(crumb)}</span>\n' if crumb else "")
            + "</header>\n"
        )
    attrs = ' data-mode="ch"' if mode else ""
    if bodyclass:
        attrs += f' class="{bodyclass}"'
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{a}assets/kaiwa.css">
</head>
<body{attrs}>
{head_bar}{body}
<script src="{a}assets/kaiwa.js"></script>
</body>
</html>
"""


def toolbar(play_all=True):
    btn = ""
    if play_all:
        btn = (
            '  <button type="button" id="playAll" class="btn primary">▶ 全文朗読</button>\n'
            '  <button type="button" id="rateBtn" class="btn" title="再生の速さ">1×</button>\n'
        )
    return (
        '<div class="toolbar">\n'
        '  <div class="seg" role="group" aria-label="表示選択">\n'
        '    <button type="button" data-mode="ch" aria-pressed="true">中国語</button>\n'
        '    <button type="button" data-mode="jp" aria-pressed="false">＋日本語</button>\n'
        '    <button type="button" data-mode="py" aria-pressed="false">＋ピンイン</button>\n'
        '    <button type="button" data-mode="all" aria-pressed="false">全部</button>\n'
        '  </div>\n'
        '  <div class="spacer"></div>\n'
        + btn +
        '</div>\n'
    )


def pager(prev=None, next_=None, back=None, back_label="一覧"):
    parts = ['<nav class="pager">']
    if prev:
        parts.append(f'  <a class="btn" rel="prev" href="{prev}"><span>← 前へ</span></a>')
    else:
        parts.append('  <span class="btn ghost"><span>←</span></span>')
    if back:
        parts.append(f'  <a class="btn" href="{back}"><span>{esc(back_label)}</span></a>')
    if next_:
        parts.append(f'  <a class="btn primary" rel="next" href="{next_}"><span>次へ →</span></a>')
    else:
        parts.append('  <span class="btn ghost"><span>→</span></span>')
    parts.append("</nav>")
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------- 旧 HTML の掃除

FACE_ZH = re.compile(r"sun|hei|song|宋|黑", re.I)
FACE_JA = re.compile(r"mincho|gothic|明朝|ゴシック|ms", re.I)


def font_class(face, size, *, semantic=False):
    """<font face=… size=…> を意味のある class に置きかえる"""
    face = (face or "").lower()
    zh = bool(FACE_ZH.search(face))
    ja = bool(FACE_JA.search(face)) and not zh
    try:
        n = int(str(size).replace("+", "")) + (2 if str(size).startswith("+") else 0)
    except (TypeError, ValueError):
        n = 0
    if semantic:
        if zh and n >= 4:
            return "ex-ch", "zh-Hans"
        if zh and n:
            return "ex-py", None
        if ja and n:
            return "ex-jp", "ja"
    cls = []
    if zh:
        cls.append("zh")
    if n >= 5:
        cls.append("fs-big")
    return " ".join(cls), ("zh-Hans" if zh else None)


def clean_html(frag, *, semantic=False):
    """旧ページの中身から、見た目を直接書いた古い指定を取りのぞく"""
    # <font> → <span class> （face / size の順番はページによってばらばら）
    def repl_font(m):
        attrs = m.group(1)
        face = re.search(r'face\s*=\s*["\']?([^"\'>\s]+)', attrs)
        size = re.search(r'size\s*=\s*["\']?([+\-]?\d+)', attrs)
        cls, lang = font_class(face.group(1) if face else "",
                               size.group(1) if size else "", semantic=semantic)
        bits = []
        if cls:
            bits.append(f'class="{cls}"')
        if lang:
            bits.append(f'lang="{lang}"')
        return "<span " + " ".join(bits) + ">" if bits else "<span>"

    frag = re.sub(r"<font([^>]*)>", repl_font, frag, flags=re.I)
    frag = re.sub(r"</font>", "</span>", frag, flags=re.I)

    # <lable> は HTML にない綴り間違い → <label>
    frag = re.sub(r"<lable\b", "<label", frag, flags=re.I)
    frag = re.sub(r"</lable>", "</label>", frag, flags=re.I)
    frag = re.sub(r'(<label[^>]*?)\s*/>\s*</label>', r"\1></label>", frag, flags=re.I)

    # 定義されていない関数を呼ぶ onchange（コンソールにエラーが出ていた）
    frag = re.sub(r'\s*onchange\s*=\s*"[^"]*setViewItem[^"]*"', "", frag, flags=re.I)

    # 見た目を決めていた古い属性は CSS にまかせる
    frag = re.sub(r'\s(align|bgcolor|border|cellpadding|cellspacing|bordercolor|valign)\s*'
                  r'[=＝]\s*["\']?[^"\'>\s]*["\']?', "", frag, flags=re.I)
    frag = re.sub(r'\s(width|height)\s*=\s*["\']?\d+%?["\']?(?=[\s>])', "",
                  frag, flags=re.I)
    # 入力欄の固定幅・小さすぎる高さは消す（スマホで画面からはみ出す原因）
    frag = re.sub(r'\sstyle\s*=\s*"[^"]*(?:font-size|width|height)[^"]*"', "", frag, flags=re.I)

    # 中身のない飾り行を落とす
    frag = re.sub(r"<tr[^>]*>\s*(?:<td[^>]*>\s*(?:&nbsp;|\s)*</td>\s*)*</tr>", "", frag, flags=re.I)
    frag = re.sub(r"<p>\s*(?:&nbsp;|\s)*</p>", "", frag, flags=re.I)
    frag = re.sub(r"<br\s*/?>\s*(?=</(td|p|div)>)", "", frag, flags=re.I)
    frag = re.sub(r"</?(center|basefont)[^>]*>", "", frag, flags=re.I)
    frag = re.sub(r"</a>(?!\s*<)", "", frag, count=0) if False else frag
    frag = re.sub(r"<a>\s*</a>", "", frag, flags=re.I)
    frag = re.sub(r"\n{3,}", "\n\n", frag)
    frag = balance_spans(frag)
    return frag.strip()


def balance_spans(frag):
    """セルの中で閉じ忘れている <span> を閉じる（元は <font> の閉じ忘れ）"""
    def fix_cell(m):
        inner = m.group(2)
        missing = len(re.findall(r"<span\b", inner)) - len(re.findall(r"</span>", inner))
        return m.group(1) + inner + "</span>" * max(0, missing) + m.group(3)

    return re.sub(r"(<td[^>]*>)(.*?)(</td>)", fix_cell, frag, flags=re.S | re.I)


def fix_images(frag, depth):
    """images/… を共通フォルダ assets/images/… に向け直す"""
    return re.sub(r'(src\s*=\s*["\'])(?:\.\./)*images/',
                  lambda m: m.group(1) + rel(depth) + "assets/images/", frag, flags=re.I)


# ---------------------------------------------------------------- 本文・単語の読み取り

LABEL_RE = re.compile(
    r'<lable\s+id="(?P<id>[^"]+)_(?P<kind>ch|py|jp)"[^>]*>(?P<body>.*?)</lable>',
    re.I | re.S)


def extract_triples(src):
    """中国語・ピンイン・日本語を id でひも付けて取り出す"""
    found = defaultdict(dict)
    order = []
    for m in LABEL_RE.finditer(src):
        key, kind = m.group("id"), m.group("kind").lower()
        if key not in found:
            order.append(key)
        found[key][kind] = tidy(strip_tags(m.group("body")))
    return [(k, found[k]) for k in order]


SPEAKER_RE = re.compile(r"^([A-Z])\s*[:：]\s*")


# ---------------------------------------------------------------- 各ページの変換

def convert_honbun(src, out_path, ctx, depth):
    """会話本文のページ"""
    rows = extract_triples(src)
    lesson, title = ctx["lesson"], ctx["title"]
    part = ctx["part"]

    items = []
    for key, tri in rows:
        ch = tri.get("ch", "")
        spk = ""
        m = SPEAKER_RE.match(ch)
        if m:
            spk, ch = m.group(1), SPEAKER_RE.sub("", ch)
        items.append(
            f'  <li class="line" data-audio="{key}" tabindex="0" role="button" '
            f'aria-label="この文を再生">\n'
            f'    <span class="spk">{esc(spk) or "♪"}</span>\n'
            f'    <p class="l-ch" lang="zh-Hans">{esc(ch)}</p>\n'
            f'    <p class="l-py" data-lang="py">{esc(tri.get("py", ""))}</p>\n'
            f'    <p class="l-jp" data-lang="jp" lang="ja">{esc(tri.get("jp", ""))}</p>\n'
            "  </li>"
        )

    nav = pager(prev=ctx.get("prev"), next_=ctx.get("next"),
                back=f"{rel(depth - 1)}{lesson}.html", back_label="課のメニュー")

    body = (
        '<main class="wrap">\n'
        + toolbar()
        + '<div class="hint">💡 <span>文をタップすると音が出ます。上のボタンで日本語・ピンインの表示や、'
          '読む速さを変えられます。</span></div>\n'
        '<ol class="lines">\n' + "\n".join(items) + "\n</ol>\n"
        + nav + "</main>\n"
    )
    write(out_path, shell(f"{title}｜本文{part}", body, depth,
                          crumb=f"本文 {part}", back=f"{rel(depth - 1)}{lesson}.html",
                          back_label="課のメニュー", lesson_title=title))


def convert_tango(src, out_path, ctx, depth):
    """単語・補充単語のページ"""
    rows = extract_triples(src)
    lesson, title = ctx["lesson"], ctx["title"]
    label = ctx["label"]

    items = []
    for key, tri in rows:
        items.append(
            f'  <li class="word" data-audio="{key}" tabindex="0" role="button" '
            f'aria-label="この単語を再生">\n'
            f'    <span class="w-ch" lang="zh-Hans">{esc(tri.get("ch", ""))}</span>\n'
            f'    <span class="w-py" data-lang="py">{esc(tri.get("py", ""))}</span>\n'
            f'    <span class="w-jp" data-lang="jp" lang="ja">{esc(tri.get("jp", ""))}</span>\n'
            "  </li>"
        )

    nav = pager(prev=ctx.get("prev"), next_=ctx.get("next"),
                back=f"{rel(depth - 1)}{lesson}.html", back_label="課のメニュー")

    extra = ""
    if ctx.get("sibling"):
        extra = (f'<p class="center"><a class="btn" href="{ctx["sibling"][0]}">'
                 f'{esc(ctx["sibling"][1])} →</a></p>\n')

    body = (
        '<main class="wrap">\n'
        + toolbar()
        + '<div class="hint">💡 <span>単語をタップすると音が出ます。'
          'ピンインや意味をかくして、確認テストにも使えます。</span></div>\n'
        '<ul class="words">\n' + "\n".join(items) + "\n</ul>\n"
        + extra + nav + "</main>\n"
    )
    write(out_path, shell(f"{title}｜{label}", body, depth,
                          crumb=label, back=f"{rel(depth - 1)}{lesson}.html",
                          back_label="課のメニュー", lesson_title=title))


def convert_point_index(src, out_path, ctx, depth):
    """文法ポイントの目次"""
    lesson, title = ctx["lesson"], ctx["title"]
    links = re.findall(r'<a href="([^"]+p\.html)"[^>]*>(.*?)</a>', src, re.S)
    items = []
    for i, (href, text) in enumerate(links, 1):
        items.append(f'  <li><a href="{href}"><span class="n">{i}</span>'
                     f'<span lang="zh-Hans">{esc(tidy(strip_tags(text)))}</span>'
                     f'<span class="arrow">›</span></a></li>')
    body = (
        '<main class="wrap narrow">\n'
        '<h2 class="page-title">文法ポイント</h2>\n'
        f'<p class="page-sub">{esc(title)}</p>\n'
        '<ul class="menu">\n' + "\n".join(items) + "\n</ul>\n"
        + pager(back=f"{rel(depth - 1)}{lesson}.html", back_label="課のメニューへ戻る")
        + "</main>\n"
    )
    write(out_path, shell(f"{title}｜文法ポイント", body, depth, mode=False,
                          crumb="文法ポイント", back=f"{rel(depth - 1)}{lesson}.html",
                          back_label="課のメニュー", lesson_title=title))


def convert_point_detail(src, out_path, ctx, depth):
    """文法ポイントの解説ページ"""
    lesson, title = ctx["lesson"], ctx["title"]
    body_src = re.search(r"<body[^>]*>(.*)</body>", src, re.S | re.I)
    frag = body_src.group(1) if body_src else src
    frag = re.sub(r"<style.*?</style>", "", frag, flags=re.S | re.I)
    frag = re.sub(r"<script.*?</script>", "", frag, flags=re.S | re.I)

    # 見出し（最初の目立つ一文）
    head = ""
    m = re.search(r"<p>\s*<font[^>]*>(.*?)</font>", frag, re.S | re.I)
    if m:
        head = tidy(strip_tags(m.group(1)))
        frag = frag[:m.start()] + frag[m.end():]

    # ページ送りのリンクは下で作り直すので、元のものは取りのぞく
    nav_links = re.findall(r'<a href="([^"]+)"[^>]*>\s*(戻る|前へ|次へ)\s*</a>', frag)
    frag = re.sub(r"<tr[^>]*>(?:(?!</tr>).)*?(?:戻る|前へ|次へ)(?:(?!</tr>).)*?</tr>", "",
                  frag, flags=re.S)
    frag = re.sub(r'<p>(?:(?!</p>).)*?<a[^>]*>\s*(?:戻る|前へ|次へ)\s*</a>(?:(?!</p>).)*?</p>', "",
                  frag, flags=re.S)
    frag = re.sub(r'<a href="[^"]*"[^>]*>\s*(?:戻る|前へ|次へ)\s*</a>', "", frag)

    frag = clean_html(frag, semantic=True)
    frag = fix_images(frag, depth)
    # 元のページには閉じられていない <div> が残っていたので、ここで全部外す
    # （中身は表と段落なので div は不要）
    frag = re.sub(r"</?div[^>]*>", "", frag)
    # 見出しを抜き出したあとに残る閉じタグだけの <p> を落とす
    frag = re.sub(r"^\s*</p>", "", frag)
    frag = re.sub(r"(?:<br\s*/?>\s*){2,}", "<br>", frag, flags=re.I)

    prev = next_ = None
    for href, kind in nav_links:
        if kind == "前へ":
            prev = href
        elif kind == "次へ":
            next_ = href

    body = (
        '<main class="wrap narrow">\n'
        + (f'<h2 class="page-title" lang="zh-Hans">{esc(head)}</h2>\n' if head else "")
        + '<div class="card note">\n' + frag + "\n</div>\n"
        + pager(prev=prev, next_=next_, back=f"{ctx['lesson']}-p.html", back_label="ポイント一覧")
        + "</main>\n"
    )
    write(out_path, shell(f"{title}｜{head or '文法ポイント'}", body, depth, mode=False,
                          crumb="文法ポイント", back=f"{ctx['lesson']}-p.html",
                          back_label="ポイント一覧", lesson_title=title))


def convert_lesson_menu(src, out_path, ctx, depth):
    """課のメニュー（本文・単語・文法・宿題）"""
    lesson, title = ctx["lesson"], ctx["title"]
    tiles = [
        ("homework/kaiwa/%s-h-1.html" % lesson, "2.png", "本文", "会話を聞く"),
        ("homework/kaiwa/%s-t1-1.html" % lesson, "3.png", "単語", "新しいことば"),
        ("homework/kaiwa/%s-p.html" % lesson, "4.png", "文法", "ポイント解説"),
        ("homework/kaiwa/%s-l.html" % lesson, "5.png", "宿題", "練習問題"),
    ]
    items = "\n".join(
        f'  <li><a class="tile" href="{href}">'
        f'<img src="{rel(depth)}assets/images/{img}" alt="" loading="lazy">'
        f'<span>{esc(name)}</span><span class="num">{esc(sub)}</span></a></li>'
        for href, img, name, sub in tiles
    )
    body = (
        '<main class="wrap">\n'
        f'<h2 class="page-title" lang="zh-Hans">{esc(title)}</h2>\n'
        '<p class="page-sub">学びたいものをえらんでください</p>\n'
        f'<ul class="grid">\n{items}\n</ul>\n'
        + pager(back=f"{rel(depth)}index.html", back_label="課の一覧へ戻る")
        + "</main>\n"
    )
    write(out_path, shell(title, body, depth, mode=False,
                          back=f"{rel(depth)}index.html", back_label="課の一覧",
                          lesson_title=title))


def convert_homework_index(src, out_path, ctx, depth):
    """宿題の目次"""
    lesson, title = ctx["lesson"], ctx["title"]
    links = re.findall(r'<a href="([^"]+)"[^>]*>\s*<?[^>]*>?\s*(問題\d+)', src, re.S)
    seen, items = set(), []
    for i, (href, text) in enumerate(links, 1):
        if href in seen:
            continue
        seen.add(href)
        total = ctx["counts"].get(re.search(r"-l(\d+)-", href).group(1), "")
        items.append(
            f'  <li><a href="{href}"><span class="n">{i}</span><span>{esc(text)}</span>'
            f'<span class="arrow">{total}問 ›</span></a></li>')
    body = (
        '<main class="wrap narrow">\n'
        f'<p class="hero"><img src="{rel(depth)}assets/images/14.png" alt="加油！" loading="lazy"></p>\n'
        '<h2 class="page-title">練習問題</h2>\n'
        f'<p class="page-sub">{esc(title)}</p>\n'
        '<ul class="menu">\n' + "\n".join(items) + "\n</ul>\n"
        + pager(back=f"{rel(depth - 1)}{lesson}.html", back_label="課のメニューへ戻る")
        + "</main>\n"
    )
    write(out_path, shell(f"{title}｜練習問題", body, depth, mode=False,
                          crumb="練習問題", back=f"{rel(depth - 1)}{lesson}.html",
                          back_label="課のメニュー", lesson_title=title))


def convert_exercise(src, out_path, ctx, depth):
    """練習問題のページ"""
    lesson, title = ctx["lesson"], ctx["title"]
    big, small, total = ctx["big"], ctx["small"], ctx["total"]

    body_src = re.search(r"<body[^>]*>(.*)</body>", src, re.S | re.I)
    frag = body_src.group(1) if body_src else src
    frag = re.sub(r"<style.*?</style>", "", frag, flags=re.S | re.I)
    frag = re.sub(r"<script.*?</script>", "", frag, flags=re.S | re.I)

    # 設問文と、そえられているイラスト
    prompt, img = "", ""
    # 設問文をくるんでいる <div> ごと取りのぞく（閉じタグだけ残らないように）
    m = re.search(r'<div[^>]*>\s*<p>(.*?)</p>.*?</div>', frag, re.S | re.I)
    if m:
        chunk = m.group(1)
        mi = re.search(r'<img[^>]+src="([^"]+)"', chunk, re.I)
        if mi:
            img = mi.group(1)
        prompt = tidy(strip_tags(chunk))
        frag = frag[:m.start()] + frag[m.end():]

    # 音声ボタン（元は doFilePlay() 経由だった）
    audio_name = None
    ma = re.search(r"""setRadioFile\(\s*["']([^"']+)\.mp3["']""", src)
    if ma:
        audio_name = ma.group(1)
    frag = re.sub(r"<tr[^>]*>(?:(?!</tr>).)*?doFilePlay\(\)(?:(?!</tr>).)*?</tr>", "",
                  frag, flags=re.S)

    # 「確認」ボタンと、ページ送りのリンクは作り直す
    nav_links = re.findall(r'<a href="([^"]+)"[^>]*>\s*(戻る|前へ|次へ)\s*</a>', frag)
    frag = re.sub(r"<tr[^>]*>(?:(?!</tr>).)*?(?:doRight\(|戻る|前へ|次へ)(?:(?!</tr>).)*?</tr>", "",
                  frag, flags=re.S)

    # 解答欄の数を数える（1 問に複数の空らんがある形式に対応）
    ids = set(re.findall(r'id="%d_%d_(\d+)"' % (big, small), frag))
    parts = len(ids) if ids else 1

    frag = clean_html(frag)
    frag = fix_images(frag, depth)

    # 答えを表示する場所
    frag = re.sub(r'<label id="(\d+_\d+_R)"[^>]*>\s*</label>',
                  r'<span class="result" id="\1"></span>', frag, flags=re.I)
    # 大きな漢字の見出し（問題文として示される 1〜4 文字）
    frag = re.sub(r'<span class="zh fs-big"[^>]*>\s*([^<]{1,4}?)\s*</span>',
                  r'<span class="cue" lang="zh-Hans">\1</span>', frag)
    frag = mark_inline_inputs(frag)
    # えらぶ前の空白の選択肢に、ことばを入れておく
    frag = re.sub(r'(<option value="0"[^>]*>)\s*(?:&nbsp;|\s)*(</option>)',
                  r"\1選んでください\2", frag, flags=re.I)
    frag = re.sub(r"<table[^>]*>", '<table>', frag, flags=re.I)
    frag = re.sub(r"<table>\s*(?:<tr>\s*(?:<td>\s*</td>\s*)*</tr>\s*)*</table>", "", frag, flags=re.I)
    frag = re.sub(r"<div[^>]*>\s*</div>", "", frag)
    frag = frag.strip()

    prev = next_ = back = None
    for href, kind in nav_links:
        if kind == "前へ":
            prev = href
        elif kind == "次へ":
            next_ = href
        else:
            back = href
    back = back or f"{lesson}-l.html"

    audio_btn = ""
    if audio_name:
        audio_btn = (f'  <button type="button" class="btn primary" data-audio="{audio_name}">'
                     f'▶ 音声を聞く</button>\n')

    pct = int(small / total * 100) if total else 0
    body = (
        '<main class="wrap narrow quiz">\n'
        f'<div class="progress"><span>問題{big}</span>'
        f'<span class="bar"><i style="width:{pct}%"></i></span>'
        f'<span>{small} / {total}</span></div>\n'
        + ('<p class="prompt">'
           + (f'<img src="{rel(depth)}assets/images/{os.path.basename(img)}" alt="" loading="lazy">'
              if img else "")
           + f'<span>{esc(prompt)}</span></p>\n' if prompt else "")
        + ('<p class="center">\n' + audio_btn + "</p>\n" if audio_btn else "")
        + '<div class="card">\n' + frag + "\n</div>\n"
        '<div class="actions">\n'
        f'  <button type="button" class="btn primary" data-check '
        f'onclick="Kaiwa.check({big},{small},{parts})">答え合わせ</button>\n'
        "</div>\n"
        + pager(prev=prev, next_=next_, back=back, back_label="問題一覧")
        + "</main>\n"
    )
    extra = f'<script src="{lesson}-a.js"></script>\n'
    page = shell(f"{title}｜問題{big}-{small}", body, depth, mode=False,
                 crumb=f"問題{big}－{small}", back=back, back_label="問題一覧",
                 lesson_title=title)
    page = page.replace('<script src="', extra + '<script src="', 1)
    write(out_path, page)


def mark_inline_inputs(frag):
    """文の途中にある空らんは小さく、独立した解答らんは横いっぱいに表示する"""
    def fix_cell(m):
        head, inner, tail = m.groups()
        text = tidy(strip_tags(inner))
        if "<input" in inner.lower():
            # 入力欄のほかに文字があるセル＝文中の穴うめ
            if text:
                inner = re.sub(r"<input\b", '<input class="inline"', inner, flags=re.I)
        elif 0 < len(text) <= 10:
            # 「日本語訳文」「①」などの短い見出しは折り返さない
            head = head[:-1] + ' class="nw">'
        return head + inner + tail

    return re.sub(r"(<td[^>]*>)(.*?)(</td>)", fix_cell, frag, flags=re.S | re.I)


def convert_done(src, out_path, ctx, depth):
    """宿題を終えたときのページ"""
    lesson, title = ctx["lesson"], ctx["title"]
    body = (
        '<main class="wrap narrow">\n'
        f'<p class="hero"><img src="{rel(depth)}assets/images/15.png" alt="よくできました" loading="lazy"></p>\n'
        '<h2 class="page-title">おつかれさまでした！</h2>\n'
        '<div class="card center">\n'
        f'  <p>つづけて練習するときは <a href="{lesson}-l.html">問題一覧</a> へ戻ってください。</p>\n'
        '  <p class="muted">宿題を提出するときは、パソコンで下のファイルをダウンロードし、CS から提出してください。</p>\n'
        f'  <p><a class="btn primary" href="../{lesson[:-1]}.xlsx" download>宿題ファイルをひらく</a></p>\n'
        "</div>\n"
        + pager(back=f"{rel(depth - 1)}{lesson}.html", back_label="課のメニューへ戻る")
        + "</main>\n"
    )
    write(out_path, shell(f"{title}｜おつかれさまでした", body, depth, mode=False,
                          back=f"{lesson}-l.html", back_label="問題一覧",
                          lesson_title=title))


# ---------------------------------------------------------------- トップページ

def build_index(out_dir, lessons, max_lesson=14):
    items = []
    for n in range(1, max_lesson + 1):
        key = f"{n}k"
        title = lessons.get(key, {}).get("title", "")
        sub = tidy(re.sub(r"^第[０-９0-9]+課\s*", "", title)) if title else ""
        ready = os.path.exists(os.path.join(out_dir, key, f"{key}.html"))
        label = f'<span>第{LESSON_NUM[n]}課</span>'
        if ready:
            # まだ変換していない課は、フォルダを置いて convert.py を実行すれば自動で有効になります
            items.append(
                f'  <li><a class="tile" href="{key}/{key}.html">{label}'
                + (f'<span class="num" lang="zh-Hans">{esc(sub)}</span>' if sub else
                   '<span class="num">　</span>')
                + "</a></li>")
        else:
            items.append(
                f'  <li><span class="tile disabled" aria-disabled="true">{label}'
                '<span class="num">準備中</span></span></li>')
    body = (
        '<main class="wrap">\n'
        '<div class="hero">\n'
        '  <img src="assets/images/13.png" alt="你好！">\n'
        '  <h1 class="page-title">初級中国語会話</h1>\n'
        '  <p class="page-sub">課をえらんでください</p>\n'
        "</div>\n"
        '<p class="center" style="margin-bottom:18px">'
        '<a class="btn" href="k1-m.html">はじめての方へ（使い方）</a></p>\n'
        '<ul class="grid lessons">\n' + "\n".join(items) + "\n</ul>\n"
        "</main>\n"
    )
    write(os.path.join(out_dir, "index.html"),
          shell("初級中国語会話", body, 0, mode=False))
    # 旧 k1.html のブックマークからも開けるようにしておく
    write(os.path.join(out_dir, "k1.html"),
          '<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">'
          '<meta http-equiv="refresh" content="0; url=index.html">'
          '<title>初級中国語会話</title></head>'
          '<body><p><a href="index.html">初級中国語会話へ</a></p></body></html>\n')


def build_guide(out_dir):
    rows = [
        ("🔊 音を聞く", "文や単語をタップすると、その部分の音声が流れます。"),
        ("🇨🇳 表示をかえる", "「中国語／＋日本語／＋ピンイン／全部」で、見せる内容を切りかえられます。"
                        "えらんだ設定は次のページでもそのまま使えます。"),
        ("▶ 全文朗読", "本文や単語を上から順に続けて読み上げます。もう一度押すと止まります。"),
        ("1× 速さ", "0.75倍 → 1倍 → 1.25倍 と切りかわります。聞きとりにくいときは 0.75倍で。"),
        ("✅ 答え合わせ", "練習問題では、入力して「答え合わせ」を押すと〇か正解が出ます。"
                    "Enter キーでも答え合わせできます。"),
        ("⌨️ キーボード", "問題のページでは ← → キーで前の問題・次の問題へ移動できます。"),
    ]
    cards = "\n".join(
        f'  <li><a class="tile" style="cursor:default" href="#" onclick="return false">'
        f'<span>{esc(t)}</span><span class="num">{esc(d)}</span></a></li>'
        for t, d in rows)
    body = (
        '<main class="wrap narrow">\n'
        '<h2 class="page-title">使い方</h2>\n'
        '<p class="page-sub">スマートフォン・タブレット・パソコンのどれでも使えます</p>\n'
        '<div class="card">\n<ul style="padding-left:1.2em;line-height:2">\n'
        + "\n".join(f"  <li><b>{esc(t)}</b>　{esc(d)}</li>" for t, d in rows)
        + "\n</ul>\n</div>\n"
        '<div class="hint">💡 <span>音が出ないときは、端末のマナーモード・音量をご確認ください。'
        'ページを開いた直後は、一度画面をタップしてからでないと音が出ない機種があります。</span></div>\n'
        + pager(back="index.html", back_label="課の一覧へ戻る")
        + "</main>\n"
    )
    write(os.path.join(out_dir, "k1-m.html"), shell("使い方｜初級中国語会話", body, 0, mode=False))


# ---------------------------------------------------------------- メイン処理

def lesson_title(src_dir, key):
    path = os.path.join(src_dir, key, f"{key}.html")
    if not os.path.exists(path):
        return ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", read(path), re.S | re.I)
    return tidy(strip_tags(m.group(1))) if m else ""


def main(src_dir, out_dir):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(out_dir, exist_ok=True)

    # 共通ファイル（デザインと動き）
    os.makedirs(os.path.join(out_dir, "assets"), exist_ok=True)
    for name in ("kaiwa.css", "kaiwa.js"):
        srcf = os.path.join(here, "assets", name)
        if os.path.exists(srcf):
            shutil.copy2(srcf, os.path.join(out_dir, "assets", name))

    keys = sorted([d for d in os.listdir(src_dir) if re.fullmatch(r"\d+k", d)],
                  key=lambda s: int(s[:-1]))
    lessons = {}
    images_done = False
    report = []

    for key in keys:
        kdir = os.path.join(src_dir, key)
        kaiwa = os.path.join(kdir, "homework", "kaiwa")
        if not os.path.isdir(kaiwa):
            continue
        title = lesson_title(src_dir, key)
        lessons[key] = {"title": title}
        ctx0 = {"lesson": key, "title": title}

        # 画像は 1 か所にまとめる（課ごとに同じものが重複していたため）
        if not images_done and os.path.isdir(os.path.join(kaiwa, "images")):
            img_dst = os.path.join(out_dir, "assets", "images")
            os.makedirs(img_dst, exist_ok=True)
            for f in os.listdir(os.path.join(kaiwa, "images")):
                if f.lower().endswith((".png", ".jpg", ".gif")):
                    shutil.copy2(os.path.join(kaiwa, "images", f), os.path.join(img_dst, f))
            images_done = True

        # 音声と答えファイル・提出用 xlsx はそのまま運ぶ
        dst_kaiwa = os.path.join(out_dir, key, "homework", "kaiwa")
        os.makedirs(dst_kaiwa, exist_ok=True)
        snd_src, snd_dst = os.path.join(kaiwa, "sound"), os.path.join(dst_kaiwa, "sound")
        if os.path.isdir(snd_src):
            shutil.copytree(snd_src, snd_dst, dirs_exist_ok=True)
        for f in os.listdir(kaiwa):
            if f.endswith("-a.js"):
                shutil.copy2(os.path.join(kaiwa, f), os.path.join(dst_kaiwa, f))
        for f in os.listdir(os.path.join(kdir, "homework")):
            if f.endswith((".xlsx", ".xls", ".docx", ".pdf")):
                shutil.copy2(os.path.join(kdir, "homework", f),
                             os.path.join(out_dir, key, "homework", f))

        # ---- 課のメニュー
        convert_lesson_menu(read(os.path.join(kdir, f"{key}.html")),
                            os.path.join(out_dir, key, f"{key}.html"), ctx0, 1)

        files = sorted(os.listdir(kaiwa))
        def numbered(pattern, group):
            got = [f for f in files if re.fullmatch(pattern, f)]
            return sorted(got, key=lambda s: int(re.search(group, s).group(1)))

        hon = numbered(rf"{key}-h-(\d+)\.html", r"h-(\d+)")
        tan = numbered(rf"{key}-t1-\d+\.html", r"t1-(\d+)")
        sup = numbered(rf"{key}-t2-\d+\.html", r"t2-(\d+)")

        # ---- 本文
        for i, f in enumerate(hon):
            ctx = dict(ctx0, part=i + 1,
                       prev=hon[i - 1] if i else None,
                       next=hon[i + 1] if i + 1 < len(hon) else None)
            convert_honbun(read(os.path.join(kaiwa, f)), os.path.join(dst_kaiwa, f), ctx, 3)

        # ---- 単語 / 補充単語
        for group, label, sibling in ((tan, "単語", (sup, "補充単語")),
                                      (sup, "補充単語", (tan, "単語"))):
            for i, f in enumerate(group):
                sib = None
                if i == len(group) - 1 and sibling[0]:
                    sib = (sibling[0][0], sibling[1])
                ctx = dict(ctx0, label=f"{label}{i + 1}" if len(group) > 1 else label,
                           prev=group[i - 1] if i else None,
                           next=group[i + 1] if i + 1 < len(group) else None,
                           sibling=sib)
                convert_tango(read(os.path.join(kaiwa, f)), os.path.join(dst_kaiwa, f), ctx, 3)

        # ---- 文法ポイント
        p_index = f"{key}-p.html"
        if p_index in files:
            convert_point_index(read(os.path.join(kaiwa, p_index)),
                                os.path.join(dst_kaiwa, p_index), ctx0, 3)
        for f in files:
            if re.fullmatch(rf"{key}-\d+p\.html", f):
                convert_point_detail(read(os.path.join(kaiwa, f)),
                                     os.path.join(dst_kaiwa, f), ctx0, 3)

        # ---- 宿題
        counts = defaultdict(int)
        for f in files:
            m = re.fullmatch(rf"{key}-l(\d+)-(\d+)\.html", f)
            if m:
                counts[m.group(1)] = max(counts[m.group(1)], int(m.group(2)))
        if f"{key}-l.html" in files:
            convert_homework_index(read(os.path.join(kaiwa, f"{key}-l.html")),
                                   os.path.join(dst_kaiwa, f"{key}-l.html"),
                                   dict(ctx0, counts=counts), 3)
        if f"{key}-l-o.html" in files:
            convert_done(read(os.path.join(kaiwa, f"{key}-l-o.html")),
                         os.path.join(dst_kaiwa, f"{key}-l-o.html"), ctx0, 3)
        for f in files:
            m = re.fullmatch(rf"{key}-l(\d+)-(\d+)\.html", f)
            if not m:
                continue
            big, small = int(m.group(1)), int(m.group(2))
            ctx = dict(ctx0, big=big, small=small, total=counts[m.group(1)])
            convert_exercise(read(os.path.join(kaiwa, f)),
                             os.path.join(dst_kaiwa, f), ctx, 3)

        report.append(f"{key}: {title}  (本文{len(hon)} 単語{len(tan) + len(sup)} "
                      f"ポイント{sum(1 for f in files if re.fullmatch(rf'{key}-\d+p\.html', f))} "
                      f"問題{sum(counts.values())})")

    build_index(out_dir, lessons)
    build_guide(out_dir)

    print("変換しました:")
    for line in report:
        print("  " + line)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
