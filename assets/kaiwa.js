/* ============================================================
   初級中国語会話 — 共通スクリプト
   全ページがこの 1 ファイルを読み込みます。
   ページ側の <script> は不要です。
   ============================================================ */
(function (global) {
  "use strict";

  function el(id) { return document.getElementById(id); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  // localStorage は使えない環境（プライベートモード等）もあるので必ずこれを通す
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) {} },
    keys: function () {
      try { var out = []; for (var i = 0; i < localStorage.length; i++) out.push(localStorage.key(i)); return out; }
      catch (e) { return []; }
    }
  };

  /* ---------- 音声プレーヤー（ページに 1 つだけ） ---------- */
  var audio = new Audio();
  var queue = [];        // 連続再生の待ち行列
  var qIndex = -1;
  var current = null;    // 再生中の要素
  var rate = 1;
  var GAP = 500;         // 全文朗読で、文と文のあいだにあける時間（ミリ秒）
  var gapTimer = null;

  function soundPath(name) { return "sound/" + name + ".mp3"; }

  function mark(node, on) { if (node) node.classList.toggle("playing", !!on); }
  function clearMark() { stopTrack(); mark(current, false); current = null; }

  /* ---------- 読んでいる字に色をつける ---------- */
  // 文の各音節の読みはじめ（秒）は data-t に入っている（変換ツールが録音から求めたもの）。
  // ない場合は、音声の長さを音節の数で等分した目安を使う。
  var track = null;

  function startTrack(node) {
    stopTrack();
    if (!node) return;
    var units = $$(".sy", node);
    if (!units.length) return;
    var t = (node.getAttribute("data-t") || "").split(" ").map(parseFloat)
      .filter(function (x) { return isFinite(x); });
    track = {
      units: units,
      times: t.length === units.length ? t : null,
      end: parseFloat(node.getAttribute("data-end")) || 0,
      last: -2,
      raf: 0
    };
    track.raf = requestAnimationFrame(tick);
  }

  function estimate() {
    var d = audio.duration;
    if (!isFinite(d) || !d) return null;
    var n = track.units.length, lead = Math.min(0.25, d * 0.08), span = d - lead * 2;
    var out = [];
    for (var i = 0; i < n; i++) out.push(lead + span * i / n);
    track.end = d - lead;
    return out;
  }

  function tick() {
    if (!track) return;
    var times = track.times || (track.times = estimate());
    if (times) {
      var ct = audio.currentTime, idx = -1;
      for (var i = 0; i < times.length && times[i] <= ct; i++) idx = i;
      if (track.end && ct >= track.end) idx = times.length;      // 読み終わり
      if (idx !== track.last) {
        track.last = idx;
        track.units.forEach(function (u, k) {
          u.classList.toggle("done", k < idx);
          u.classList.toggle("now", k === idx);
        });
      }
    }
    track.raf = requestAnimationFrame(tick);
  }

  function stopTrack() {
    if (!track) return;
    cancelAnimationFrame(track.raf);
    track.units.forEach(function (u) { u.classList.remove("done", "now"); });
    track = null;
  }

  function toast(msg) {
    var t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    t.setAttribute("role", "status");
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2600);
  }

  // 再生が終わったとき / 失敗したときの処理は 1 か所にまとめる
  audio.addEventListener("ended", function () {
    clearMark();
    if (qIndex >= 0) { qIndex++; gapTimer = setTimeout(step, GAP); }
    else syncPlayAllButton();
  });
  audio.addEventListener("error", function () {
    clearMark();
    if (qIndex >= 0) { qIndex++; step(); }
    else { syncPlayAllButton(); toast("音声が見つかりませんでした"); }
  });

  function playFile(name, node, oneRate) {
    clearMark();
    current = node || document.querySelector('[data-audio="' + name + '"]');
    mark(current, true);
    if (current && current.classList.contains("line") || current && current.classList.contains("word")) {
      var r = current.getBoundingClientRect();
      if (r.top < 120 || r.bottom > global.innerHeight - 20) {
        current.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    }
    audio.pause();
    audio.src = soundPath(name);
    audio.playbackRate = oneRate || rate;
    var p = audio.play();
    if (p && p.catch) p.catch(function () { /* 自動再生がブロックされた場合 */ });
    if (current && current.classList.contains("line")) startTrack(current);
  }

  function step() {
    gapTimer = null;
    if (qIndex < 0 || qIndex >= queue.length) { stop(); return; }
    playFile(queue[qIndex], null);
  }

  function stop() {
    clearTimeout(gapTimer); gapTimer = null;
    audio.pause();
    queue = []; qIndex = -1;
    clearMark();
    syncPlayAllButton();
  }

  /** 1 つの音声を再生する（行や単語をタップしたとき） */
  function play(name, node, oneRate) {
    clearTimeout(gapTimer);
    queue = []; qIndex = -1;
    syncPlayAllButton();
    playFile(name, node, oneRate);
  }

  /** ページ内の音声を上から順に続けて再生する */
  function playAll() {
    var nodes = $$(".line[data-audio], .word[data-audio]");
    if (!nodes.length) return;
    queue = nodes.map(function (n) { return n.getAttribute("data-audio"); });
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
    store.set("kaiwa.rate", String(r));
    var b = el("rateBtn");
    if (b) b.textContent = (r === 1 ? "1" : String(r)) + "×";
  }

  /* ---------- 表示の切り替え（ピンイン・日本語訳） ---------- */
  // 内部では 4 つのモード（ch / py / jp / all）で持つ。CSS はこれを見て表示を切り替える。
  function setMode(mode) {
    document.body.setAttribute("data-mode", mode);
    store.set("kaiwa.mode", mode);
    var py = mode === "py" || mode === "all";
    var jp = mode === "jp" || mode === "all";
    $$("[data-toggle]").forEach(function (b) {
      var on = b.getAttribute("data-toggle") === "py" ? py : jp;
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function toggle(which) {
    var mode = document.body.getAttribute("data-mode") || "ch";
    var py = mode === "py" || mode === "all";
    var jp = mode === "jp" || mode === "all";
    if (which === "py") py = !py; else jp = !jp;
    setMode(py && jp ? "all" : py ? "py" : jp ? "jp" : "ch");
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

  /**
   * ピンイン 1 音節の書き方をそろえる。
   * 答えのファイルでは「la3o」のように、記号がつく母音の直後に数字を書いているが、
   * 学生は「lao3」や「lǎo」と打つことが多い。どれも同じものとして比べる。
   */
  function toneKey(s) {
    s = toneToNumber(String(s).toLowerCase());
    var m = s.match(/^([a-zv]*)([1-5])([a-zv]*)$/);
    return m ? m[1] + m[3] + m[2] : s;
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
    var al = a.toLowerCase(), bl = b.toLowerCase();
    if (al === bl) return true;
    // ピンインは「la3o」「lao3」「lǎo」のどれでも正解にする
    if (toneKey(al) === toneKey(bl)) return true;
    // 空白と、文の途中の句読点（，。！？など）のあるなしは無視する
    var bare = function (x) { return toneToNumber(x).replace(/[\s.,!?;:…·・]/g, ""); };
    return bare(al) === bare(bl);
  }

  // 日本語の漢字（と繁体字）→ 簡体字。
  // 日本語入力で「愛」と打ってしまったときに、×ではなく「おしい」と教えるために使う。
  var JA2ZH = (
    "両两兩两個个麼么習习書书従从從从們们児儿兒儿幾几華华嗎吗圓圆円圆師师張张" +
    "徳德時时様样樣样歓欢歡欢気气氣气沒没熱热愛爱現现電电筆笔節节詞词請请課课" +
    "誰谁謝谢貴贵賀贺車车過过還还這这鉛铅難难飯饭餃饺館馆學学國国來来點点號号" +
    "対对對对東东語语説说說说話话見见聴听聽听読读讀读買买売卖賣卖銭钱錢钱門门" +
    "開开長长間间問问題题漢汉員员飛飞図图圖图楽乐樂乐歳岁歲岁発发發发単单單单" +
    "実实實实鉄铁銀银飲饮頭头顔颜紙纸線线紅红緑绿黒黑帰归歸归雲云誕诞晩晚歩步" +
    "業业動动運运転转轉转試试験验驗验鶏鸡雞鸡魚鱼麺面湯汤歲岁"
  );
  var J2Z = {};
  for (var i = 0; i + 1 < JA2ZH.length; i += 2) J2Z[JA2ZH[i]] = JA2ZH[i + 1];

  function toSimplified(s) {
    return String(s).replace(/[㐀-鿿]/g, function (c) { return J2Z[c] || c; });
  }
  function nonSimplified(s) {
    var seen = {}, out = [];
    String(s).replace(/[㐀-鿿]/g, function (c) {
      if (J2Z[c] && !seen[c]) { seen[c] = 1; out.push(c + "→" + J2Z[c]); }
    });
    return out;
  }

  /** 1 つの解答らんを判定する: "ok" / "almost"（簡体字でない）/ "ng" */
  function judge(value, expected) {
    if (same(value, expected)) return "ok";
    if (nonSimplified(value).length && same(toSimplified(value), expected)) return "almost";
    return "ng";
  }

  /* ---------- 成績の記録（この端末のブラウザの中だけ） ---------- */
  function pageKey() {
    var m = location.pathname.match(/([^\/]+)\.html$/);
    return m ? m[1] : "";
  }
  var scored = false;   // このページを開いてから、最初の答え合わせだけを記録する

  function saveScore(ok) {
    if (scored) return;
    scored = true;
    var k = pageKey();
    if (k) store.set("kaiwa.r." + k, ok ? "1" : "0");
  }
  function getScore(key) { return store.get("kaiwa.r." + key); }   // "1" / "0" / null

  /** 大問ひとつ分の結果を数える */
  function sectionStats(sec, total) {
    var done = 0, ok = 0, firstTodo = null;
    for (var i = 1; i <= total; i++) {
      var r = getScore(sec + "-" + i);
      if (r !== null) done++;
      if (r === "1") ok++;
      else if (firstTodo === null) firstTodo = i;
    }
    return { done: done, ok: ok, total: total, firstTodo: firstTodo };
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
    var status = "ok";
    var hints = [];

    for (var i = 0; i < parts; i++) {
      var node = parts === 1 ? el(base) : el(base + "_" + (i + 1));
      if (!node) { status = "ng"; continue; }
      var j = judge(node.value, expected[i] == null ? "" : expected[i]);
      node.classList.remove("ok", "ng", "almost");
      node.classList.add(j);
      if (j === "almost") hints = hints.concat(nonSimplified(node.value));
      if (j === "ng") status = "ng";
      else if (j === "almost" && status === "ok") status = "almost";
    }

    out.className = "result " + status;
    out.textContent = "";
    if (status === "ok") {
      out.textContent = "〇 正解！";
    } else if (status === "almost") {
      out.appendChild(document.createTextNode("△ おしい！ 簡体字で書きましょう"));
      var s = document.createElement("small");
      s.textContent = hints.join("　");
      out.appendChild(s);
    } else {
      out.appendChild(document.createTextNode("× 正解は"));
      var a = document.createElement("strong");
      a.textContent = expected.join(" / ");
      out.appendChild(a);
    }
    out.setAttribute("role", "status");

    saveScore(status === "ok");
    renderDots();

    // スマホではキーボードを閉じて、結果が見えるようにする
    var coarse = global.matchMedia && global.matchMedia("(pointer: coarse)").matches;
    var act = document.activeElement;
    if (coarse && act && /^(INPUT|SELECT)$/.test(act.tagName)) act.blur();
    out.scrollIntoView({ block: "center", behavior: "smooth" });

    // 正解したら「次へ」を目立たせ、Enter でそのまま進めるようにする
    var next = document.querySelector(".pager a[rel=next]");
    if (next) {
      next.classList.toggle("go", status === "ok");
      if (status === "ok") { try { next.focus({ preventScroll: true }); } catch (e) { next.focus(); } }
    }
    return status === "ok";
  }

  /* ---------- 問題ページ上部の ○×ドット ---------- */
  function renderDots() {
    $$(".dots[data-sec]").forEach(function (box) {
      var sec = box.getAttribute("data-sec");
      var total = +box.getAttribute("data-total");
      var cur = +box.getAttribute("data-cur");
      var st = sectionStats(sec, total);
      box.textContent = "";
      for (var i = 1; i <= total; i++) {
        var a = document.createElement("a");
        var r = getScore(sec + "-" + i);
        a.href = sec + "-" + i + ".html";
        a.textContent = i;
        a.className = (r === "1" ? "ok" : r === "0" ? "ng" : "") + (i === cur ? " cur" : "");
        a.setAttribute("aria-label", "第" + i + "問" + (r === "1" ? "（正解）" : r === "0" ? "（まちがい）" : ""));
        if (i === cur) a.setAttribute("aria-current", "page");
        box.appendChild(a);
      }
      var lab = box.parentNode && box.parentNode.querySelector(".dots-count");
      if (lab) lab.textContent = st.ok + " / " + total + " 正解";
    });
  }

  /* ---------- 問題一覧・おつかれさまページの成績表示 ---------- */
  function renderScores() {
    $$("[data-score-sec]").forEach(function (n) {
      var st = sectionStats(n.getAttribute("data-score-sec"), +n.getAttribute("data-total"));
      n.className = "score" + (st.done === 0 ? "" : st.ok === st.total ? " full" : " part");
      n.textContent = st.done === 0 ? "未" : st.ok + "/" + st.total;
    });

    $$(".summary[data-secs]").forEach(function (box) {
      var rows = box.getAttribute("data-secs").split(",");
      var allOk = 0, allTotal = 0, allDone = 0;
      var list = document.createElement("ul");
      list.className = "menu";
      rows.forEach(function (row, idx) {
        var p = row.split(":"), sec = p[0], total = +p[1];
        var st = sectionStats(sec, total);
        allOk += st.ok; allTotal += total; allDone += st.done;
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = sec + "-" + (st.firstTodo || 1) + ".html";
        a.innerHTML = '<span class="n"></span><span></span><span class="arrow"></span>';
        a.children[0].textContent = idx + 1;
        a.children[1].textContent = "問題" + (idx + 1) + "　" + st.ok + " / " + total;
        a.children[2].textContent = st.ok === total ? "✓" : st.done === 0 ? "はじめる ›" : "やり直す ›";
        if (st.ok === total) a.classList.add("done");
        li.appendChild(a);
        list.appendChild(li);
      });
      box.textContent = "";
      var head = document.createElement("p");
      head.className = "total";
      head.textContent = allDone ? "正解 " + allOk + " / " + allTotal + " 問" : "まだ記録がありません";
      box.appendChild(head);
      box.appendChild(list);
    });
  }

  function resetScores(prefix) {
    if (!global.confirm("この課の記録を消しますか？")) return;
    store.keys().forEach(function (k) {
      if (k && k.indexOf("kaiwa.r." + prefix) === 0) store.del(k);
    });
    renderScores();
    renderDots();
  }

  /* ---------- 起動時のしかけ ---------- */
  function init() {
    // 保存しておいた表示モード・再生速度を復元する
    if (document.querySelector("[data-toggle]")) setMode(store.get("kaiwa.mode") || "ch");
    setRate(parseFloat(store.get("kaiwa.rate")) || 1);

    // 一度閉じたヒントは、次から出さない
    $$(".hint[data-hint]").forEach(function (h) {
      if (store.get("kaiwa.hint." + h.getAttribute("data-hint"))) h.remove();
    });

    // スマホの自動修正・自動大文字で答えが変わらないようにする
    $$('input[type="text"]').forEach(function (i) {
      i.setAttribute("autocapitalize", "off");
      i.setAttribute("autocorrect", "off");
      i.setAttribute("autocomplete", "off");
      i.setAttribute("spellcheck", "false");
      i.setAttribute("enterkeyhint", "done");
    });

    document.addEventListener("click", function (ev) {
      var t = ev.target;
      if (!t.closest) return;

      var hit = t.closest("[data-audio]");
      if (hit) {
        var r1 = parseFloat(hit.getAttribute("data-rate")) || 0;
        play(hit.getAttribute("data-audio"), hit, r1);
        return;
      }
      var tg = t.closest("[data-toggle]");
      if (tg) { toggle(tg.getAttribute("data-toggle")); return; }

      var x = t.closest(".hint .x");
      if (x) {
        var h = x.closest(".hint");
        store.set("kaiwa.hint." + h.getAttribute("data-hint"), "1");
        h.remove();
        return;
      }
      var rs = t.closest("[data-reset]");
      if (rs) { resetScores(rs.getAttribute("data-reset")); return; }

      if (t.id === "playAll") { isPlayingAll() ? stop() : playAll(); return; }
      if (t.id === "rateBtn") {
        var steps = [0.75, 1, 1.25];
        setRate(steps[(steps.indexOf(rate) + 1) % steps.length]);
      }
    });

    document.addEventListener("keydown", function (ev) {
      var t = ev.target;
      // 日本語入力の変換を確定する Enter では、何もしない
      if (ev.isComposing || ev.keyCode === 229) return;

      // 解答欄で Enter を押したら、そのまま答え合わせ
      if (ev.key === "Enter" && t && t.tagName === "INPUT" && t.type === "text") {
        var btn = document.querySelector("[data-check]");
        if (btn) { ev.preventDefault(); btn.click(); }
        return;
      }
      // 文や単語にフォーカスがあるときは Enter / スペースで再生
      if ((ev.key === "Enter" || ev.key === " ") && t && t.matches && t.matches('[data-audio][role="button"]')) {
        ev.preventDefault();
        play(t.getAttribute("data-audio"), t);
        return;
      }
      // ← → キーで前の問題・次の問題へ
      if (t && /^(INPUT|SELECT|TEXTAREA)$/.test(t.tagName)) return;
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      var sel = ev.key === "ArrowRight" ? "[rel=next]" : ev.key === "ArrowLeft" ? "[rel=prev]" : null;
      if (!sel) return;
      var a = document.querySelector(".pager a" + sel);
      if (a) a.click();
    });

    // ページを離れるときは音を止める
    global.addEventListener("pagehide", stop);
    // 「戻る」でページに戻ってきたときも、成績表示を最新にする
    global.addEventListener("pageshow", function () { renderScores(); renderDots(); });

    renderDots();
    renderScores();
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
    check: check, same: same, judge: judge, canon: canon
  };
})(window);
