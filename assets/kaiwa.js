/* ============================================================
   初級中国語会話 — 共通スクリプト
   全ページがこの 1 ファイルを読み込みます。
   ページ側の <script> は不要です。
   ============================================================ */
(function (global) {
  "use strict";

  /* ---------- 音声プレーヤー（ページに 1 つだけ） ---------- */
  var audio = new Audio();
  var queue = [];        // 連続再生の待ち行列
  var qIndex = -1;
  var current = null;    // 再生中の要素
  var rate = 1;

  function el(id) { return document.getElementById(id); }

  function soundPath(name) { return "sound/" + name + ".mp3"; }

  function mark(node, on) {
    if (!node) return;
    node.classList.toggle("playing", !!on);
  }

  function clearMark() { mark(current, false); current = null; }

  function toast(msg) {
    var t = document.createElement("div");
    t.textContent = msg;
    t.setAttribute("role", "status");
    t.style.cssText =
      "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);" +
      "background:#16303f;color:#fff;padding:10px 18px;border-radius:999px;" +
      "font-size:14px;z-index:999;box-shadow:0 6px 20px rgba(0,0,0,.25)";
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2600);
  }

  // 再生が終わったとき / 失敗したときの処理は 1 か所にまとめる
  audio.addEventListener("ended", function () {
    clearMark();
    if (qIndex >= 0) { qIndex++; step(); }
    else syncPlayAllButton();
  });
  audio.addEventListener("error", function () {
    clearMark();
    if (qIndex >= 0) { qIndex++; step(); }
    else { syncPlayAllButton(); toast("音声が見つかりませんでした"); }
  });

  function playFile(name, node) {
    clearMark();
    current = node || document.querySelector('[data-audio="' + name + '"]');
    mark(current, true);
    if (current && current.scrollIntoView) {
      var r = current.getBoundingClientRect();
      if (r.top < 90 || r.bottom > global.innerHeight - 20) {
        current.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    }
    audio.pause();
    audio.src = soundPath(name);
    audio.playbackRate = rate;
    var p = audio.play();
    if (p && p.catch) p.catch(function () { /* 自動再生がブロックされた場合 */ });
  }

  function step() {
    if (qIndex < 0 || qIndex >= queue.length) { stop(); return; }
    playFile(queue[qIndex], null);
  }

  function stop() {
    audio.pause();
    queue = []; qIndex = -1;
    clearMark();
    syncPlayAllButton();
  }

  /** 1 つの音声を再生する（行や単語をタップしたとき） */
  function play(name, node) {
    queue = []; qIndex = -1;
    syncPlayAllButton();
    playFile(name, node);
  }

  /** ページ内の音声を上から順に続けて再生する */
  function playAll() {
    var nodes = document.querySelectorAll("[data-audio]");
    if (!nodes.length) return;
    queue = Array.prototype.map.call(nodes, function (n) { return n.getAttribute("data-audio"); });
    qIndex = 0;
    syncPlayAllButton();
    step();
  }

  function isPlayingAll() { return qIndex >= 0; }

  function syncPlayAllButton() {
    var b = el("playAll");
    if (!b) return;
    b.textContent = isPlayingAll() ? "■ 停止" : "▶ 全文朗読";
    b.classList.toggle("primary", !isPlayingAll());
  }

  function setRate(r) {
    rate = r;
    audio.playbackRate = r;
    try { localStorage.setItem("kaiwa.rate", String(r)); } catch (e) {}
    var b = el("rateBtn");
    if (b) b.textContent = r.toFixed(2).replace(/0$/, "") + "×";
  }

  /* ---------- 表示選択（中国語 / 日本語 / ピンイン） ---------- */
  function setMode(mode) {
    document.body.setAttribute("data-mode", mode);
    try { localStorage.setItem("kaiwa.mode", mode); } catch (e) {}
    var btns = document.querySelectorAll(".seg [data-mode]");
    Array.prototype.forEach.call(btns, function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-mode") === mode ? "true" : "false");
    });
  }

  /* ---------- 答え合わせ ---------- */

  // 声調記号つきピンイン → 数字つきピンイン（bā → ba1）
  var TONES = {
    "ā":"a1","á":"a2","ǎ":"a3","à":"a4",
    "ē":"e1","é":"e2","ě":"e3","è":"e4",
    "ī":"i1","í":"i2","ǐ":"i3","ì":"i4",
    "ō":"o1","ó":"o2","ǒ":"o3","ò":"o4",
    "ū":"u1","ú":"u2","ǔ":"u3","ù":"u4",
    "ǖ":"v1","ǘ":"v2","ǚ":"v3","ǜ":"v4","ü":"v"
  };

  function toneToNumber(s) {
    // 連続するアルファベットのかたまりごとに、声調記号を数字へ置きかえる
    return s.replace(/[a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]+/g, function (word) {
      var digit = "", out = "";
      for (var i = 0; i < word.length; i++) {
        var c = word[i], t = TONES[c];
        if (t) { out += t[0]; if (t.length > 1) { if (digit) return word; digit = t[1]; } }
        else out += c;
      }
      return out + digit;
    });
  }

  /** 比べる前に表記ゆれをそろえる（全角・空白・句読点のちがいで×にしない） */
  function canon(s) {
    s = String(s == null ? "" : s);
    // 全角英数字・記号 → 半角
    s = s.replace(/[！-～]/g, function (c) {
      return String.fromCharCode(c.charCodeAt(0) - 0xFEE0);
    });
    s = s.replace(/　/g, " ");
    if (s.normalize) s = s.normalize("NFC");
    // 句読点をそろえる
    s = s.replace(/[。．]/g, ".").replace(/[，、]/g, ",")
         .replace(/？/g, "?").replace(/！/g, "!")
         .replace(/[“”「」『』"']/g, "");
    s = s.replace(/\s+/g, " ").trim();
    s = s.replace(/[.,!?;:]+$/, "");   // 文末の句読点は無視する
    return s;
  }

  function same(studentRaw, correctRaw) {
    var a = canon(studentRaw), b = canon(correctRaw);
    if (a === b) return true;
    if (a.toLowerCase() === b.toLowerCase()) return true;
    // ピンインは声調記号でも数字でも正解にする
    var an = toneToNumber(a.toLowerCase()), bn = toneToNumber(b.toLowerCase());
    if (an === bn) return true;
    // 空白のちがいだけは無視する
    return an.replace(/\s/g, "") === bn.replace(/\s/g, "");
  }

  /**
   * 答え合わせ。
   *   big   … 大問番号
   *   small … 小問番号
   *   parts … 解答欄の数（1 なら id="3_1"、2 以上なら id="4_1_1" …）
   * 正解は各課の "<課>-a.js" に入っています。
   */
  function check(big, small, parts) {
    parts = parts || 1;
    var base = big + "_" + small;
    var out = el(base + "_R");
    var correct = (typeof doFindAnswer === "function") ? doFindAnswer(big, small) : "";
    if (!out) return;

    var expected = String(correct).split("@");
    var allOk = true;
    var fields = [];

    for (var i = 0; i < parts; i++) {
      var node = parts === 1 ? el(base) : el(base + "_" + (i + 1));
      if (!node) { allOk = false; continue; }
      fields.push(node);
      var ok = same(node.value, expected[i] == null ? "" : expected[i]);
      node.classList.toggle("ok", ok);
      node.classList.toggle("ng", !ok);
      node.style.borderColor = ok ? "#1b9e5f" : "";
      if (!ok) allOk = false;
    }

    out.className = "result " + (allOk ? "ok" : "ng");
    out.textContent = allOk ? "〇" : expected.join(" / ");

    // 画面を読み上げるソフトにも結果を伝える
    out.setAttribute("role", "status");
    return allOk;
  }

  /* ---------- 起動時のしかけ ---------- */
  function init() {
    // 保存しておいた表示モード・再生速度を復元する
    var mode = "ch", r = 1;
    try {
      mode = localStorage.getItem("kaiwa.mode") || "ch";
      r = parseFloat(localStorage.getItem("kaiwa.rate")) || 1;
    } catch (e) {}
    if (document.querySelector(".seg [data-mode]")) setMode(mode);
    setRate(r);

    // 行・単語をタップしたら、その音声を再生する
    document.addEventListener("click", function (ev) {
      var hit = ev.target.closest ? ev.target.closest("[data-audio]") : null;
      if (hit) { play(hit.getAttribute("data-audio"), hit); return; }

      var seg = ev.target.closest ? ev.target.closest(".seg [data-mode]") : null;
      if (seg) { setMode(seg.getAttribute("data-mode")); return; }

      if (ev.target.id === "playAll") { isPlayingAll() ? stop() : playAll(); return; }
      if (ev.target.id === "rateBtn") {
        var steps = [0.75, 1, 1.25];
        setRate(steps[(steps.indexOf(rate) + 1) % steps.length]);
        return;
      }
    });

    // 解答欄で Enter を押したら、そのまま答え合わせ
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Enter") return;
      var t = ev.target;
      if (!t || t.tagName !== "INPUT" || t.type !== "text") return;
      var box = t.closest(".quiz") || document;
      var btn = box.querySelector("[data-check]");
      if (btn) { ev.preventDefault(); btn.click(); }
    });

    // ← → キーで前の問題・次の問題へ
    document.addEventListener("keydown", function (ev) {
      if (ev.target && /^(INPUT|SELECT|TEXTAREA)$/.test(ev.target.tagName)) return;
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      var sel = ev.key === "ArrowRight" ? "[rel=next]" : ev.key === "ArrowLeft" ? "[rel=prev]" : null;
      if (!sel) return;
      var a = document.querySelector(".pager a" + sel);
      if (a) a.click();
    });

    // ページを離れるときは音を止める
    global.addEventListener("pagehide", stop);

    syncPlayAllButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  global.Kaiwa = {
    play: play, playAll: playAll, stop: stop,
    setMode: setMode, setRate: setRate,
    check: check, same: same, canon: canon
  };
})(window);
