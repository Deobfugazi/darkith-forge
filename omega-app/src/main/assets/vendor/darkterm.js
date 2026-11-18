"use strict";
/* =====================================================================
   DarkTerm — a real POSIX-style shell engine for the Darkith Inscriber.
   Offline. No dependencies. Runs in the browser and in Node (headless).

   Supports: words + quoting (', ", \), expansions ($VAR, ${VAR:-d}, $((..)),
   $(..), `..`), field splitting, globbing, pipelines, redirection
   (<, >, >>, 2>, 2>>, &>, <<, <<<), sequences (; & && ||), control flow
   (if/elif/else, while, until, for..in, case, break, continue, return),
   functions, arithmetic, and a coreutils set over a virtual filesystem.

   Exposed as window.DarkTerm / module export for differential testing.
   ===================================================================== */
(function (root) {
  "use strict";

  var VERSION = "1.0.0";

  /* ================= VFS ================= */
  function VFS() { this.root = { t: "d", c: {}, m: 493, ts: 0 }; }   // 0755
  VFS.prototype.norm = function (cwd, p) {
    p = (p == null ? "" : String(p));
    if (p === "") return cwd;
    var abs = (p.charAt(0) === "/") ? p : cwd + "/" + p;
    var parts = abs.split("/"), out = [];
    for (var i = 0; i < parts.length; i++) {
      var s = parts[i];
      if (s === "" || s === ".") continue;
      if (s === "..") { out.pop(); continue; }
      out.push(s);
    }
    return "/" + out.join("/");
  };
  VFS.prototype.get = function (abs) {
    if (abs === "/") return this.root;
    var parts = abs.split("/").slice(1), n = this.root;
    for (var i = 0; i < parts.length; i++) {
      if (n.t !== "d") return null;
      n = n.c[parts[i]];
      if (!n) return null;
    }
    return n;
  };
  VFS.prototype.split = function (abs) {
    var parts = abs.split("/"); var base = parts.pop(); var dir = parts.join("/") || "/";
    return { dir: dir, base: base };
  };
  VFS.prototype.mkdirp = function (abs, mode) {
    var parts = abs.split("/").slice(1), n = this.root;
    for (var i = 0; i < parts.length; i++) {
      if (!n.c[parts[i]]) n.c[parts[i]] = { t: "d", c: {}, m: mode == null ? 493 : mode, ts: 0 };
      n = n.c[parts[i]];
      if (n.t !== "d") return false;
    }
    return true;
  };
  VFS.prototype.writeFile = function (abs, data, mode) {
    var p = this.split(abs), parent = this.get(p.dir);
    if (!parent || parent.t !== "d") return false;
    parent.c[p.base] = { t: "f", d: String(data), m: mode == null ? 420 : mode, ts: 0 };
    return true;
  };
  VFS.prototype.readFile = function (abs) {
    var n = this.get(abs); if (!n) return null;
    if (n.t === "d") return { dir: true };
    return { dir: false, data: n.d };
  };
  VFS.prototype.list = function (abs) {
    var n = this.get(abs); if (!n || n.t !== "d") return null;
    return Object.keys(n.c).sort();
  };
  VFS.prototype.unlink = function (abs) {
    var p = this.split(abs), parent = this.get(p.dir);
    if (parent && parent.t === "d" && parent.c[p.base]) { delete parent.c[p.base]; return true; }
    return false;
  };

  /* ================= small utils ================= */
  var isNum = function (s) { return s !== "" && !isNaN(Number(s)); };
  function uniq(a) { var o = {}, r = []; a.forEach(function (x) { if (!o[x]) { o[x] = 1; r.push(x); } }); return r; }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function oct(n) { return (n & 511).toString(8); }
  function pad(s, w, c, left) { s = String(s); c = c || " "; while (s.length < w) { s = left ? c + s : s + c; } return s; }
  function err(code, msg) { var e = new Error(msg || ""); e._code = code; return e; }

  /* signals */
  function ExitSignal(code) { this.code = code; }
  function ReturnSignal(code) { this.code = code; }
  function BreakSignal(n) { this.n = n; }
  function ContinueSignal(n) { this.n = n; }

  /* ================= lexer ================= */
  function tokenize(src) {
    var toks = [], i = 0, n = src.length;
    function isMeta(c) { return "|&;()<>".indexOf(c) >= 0; }
    function isBlank(c) { return c === " " || c === "\t"; }
    while (i < n) {
      var c = src[i];
      if (c === "\\" && src[i + 1] === "\n") { i += 2; continue; }        // line continuation
      if (isBlank(c)) { i++; continue; }
      if (c === "\n") { toks.push({ t: "nl" }); i++; continue; }
      if (c === "#") { while (i < n && src[i] !== "\n") i++; continue; }
      // operators
      if (c === ";" || c === "&" || c === "|" || c === "<" || c === ">" || c === "(" || c === ")") {
        var two = src.substr(i, 2), three = src.substr(i, 3);
        if (three === "&&") { }
        if (two === "&&" || two === "||" || two === ";;" || two === ">>" || two === "<<" || two === "&>") {
          if (two === "<<") {
            if (src[i + 2] === "<") { toks.push({ t: "op", v: "<<<" }); i += 3; continue; }
            if (src[i + 2] === "-") { toks.push({ t: "op", v: "<<-" }); i += 3; continue; }
          }
          toks.push({ t: "op", v: two }); i += 2; continue;
        }
        toks.push({ t: "op", v: c }); i++; continue;
      }
      // redirection with fd prefix: 2>, 2>>, &>
      if (/[0-9]/.test(c)) {
        var j = i; while (j < n && /[0-9]/.test(src[j])) j++;
        if (src[j] === ">" || src[j] === "<") {
          var fd = src.slice(i, j), rest = src.substr(j, 2);
          if (rest === ">>") { toks.push({ t: "op", v: "fdredir", fd: fd, r: ">>" }); i = j + 2; continue; }
          toks.push({ t: "op", v: "fdredir", fd: fd, r: src[j] }); i = j + 1; continue;
        }
      }
      // word
      var w = "", depthP = 0;
      while (i < n) {
        var ch = src[i];
        if (ch === "\\") { w += src[i] + (src[i + 1] || ""); i += 2; continue; }
        if (ch === "'") { w += ch; i++; while (i < n && src[i] !== "'") { w += src[i]; i++; } w += "'"; i++; continue; }
        if (ch === '"') { w += ch; i++; while (i < n && src[i] !== '"') { if (src[i] === "\\") { w += src[i] + (src[i + 1] || ""); i += 2; } else { w += src[i]; i++; } } w += '"'; i++; continue; }
        if (ch === "$" && src[i + 1] === "(") {
          // $( ... ) or $(( ... ))
          var dbl = src[i + 2] === "(";
          var open = dbl ? "((" : "(", close = dbl ? "))" : ")", k = i + (dbl ? 3 : 2), d = 1;
          w += src.substr(i, dbl ? 3 : 2); i += (dbl ? 3 : 2);
          while (i < n) {
            if (dbl) { if (src.substr(i, 2) === "))" && d === 1) { w += "))"; i += 2; d = 0; break; }
              if (src[i] === "(") d++; else if (src[i] === ")") d--; }
            else { if (src[i] === "(") d++; else if (src[i] === ")") { d--; if (d === 0) { w += ")"; i++; break; } } }
            w += src[i]; i++;
          }
          continue;
        }
        if (ch === "`") { w += ch; i++; while (i < n && src[i] !== "`") { w += src[i]; i++; } w += "`"; i++; continue; }
        if (ch === "{" || ch === "}") { w += ch; i++; continue; }
        if (isBlank(ch) || ch === "\n" || ch === ";" || ch === "&" || ch === "|" || ch === "<" || ch === ">") break;
        if (ch === "(" || ch === ")") break;
        w += ch; i++;
      }
      toks.push({ t: "word", v: w });
    }
    toks.push({ t: "eof" });
    return toks;
  }

  /* ================= parser ================= */
  function Parser(toks) { this.t = toks; this.i = 0; }
  Parser.prototype.peek = function (k) { return this.t[this.i + (k || 0)]; };
  Parser.prototype.next = function () { return this.t[this.i++]; };
  Parser.prototype.atOp = function (v) { var x = this.peek(); return x && x.t === "op" && x.v === v; };
  Parser.prototype.atWord = function (v) { var x = this.peek(); return x && x.t === "word" && x.v === v; };
  Parser.prototype.skipNL = function () { while (this.peek().t === "nl" || this.atOp(";")) this.next(); };
  Parser.prototype.skipNLOnly = function () { while (this.peek().t === "nl") this.next(); };

  var RESERVED = { "if": 1, "then": 1, "elif": 1, "else": 1, "fi": 1, "for": 1, "in": 1, "do": 1, "done": 1,
    "while": 1, "until": 1, "case": 1, "esac": 1, "function": 1, "{": 1, "}": 1, "!": 1 };

  Parser.prototype.parse = function () { var list = this.parseList(["eof"]); return list; };

  Parser.prototype.parseList = function (stop) {
    var items = [];
    this.skipNL();
    while (!this.atStop(stop)) {
      var andor = this.parseAndOr(stop);
      if (!andor) break;
      var sep = ";";
      if (this.peek().t === "nl") { sep = ";"; }
      else if (this.atOp("&")) { sep = "&"; this.next(); }
      else if (this.atOp(";")) { this.next(); }
      else if (this.atOp("&&") || this.atOp("||")) { /* handled in andor */ }
      items.push({ andor: andor, sep: sep });
      this.skipNL();
    }
    return { type: "list", items: items };
  };
  Parser.prototype.atStop = function (stop) {
    var x = this.peek();
    if (x.t === "eof") return true;
    if (x.t === "op" && (stop.indexOf(x.v) >= 0)) return true;
    if (x.t === "word" && stop.indexOf(x.v) >= 0) return true;
    return false;
  };
  Parser.prototype.parseAndOr = function (stop) {
    var first = this.parsePipeline(stop);
    if (!first) return null;
    var ops = [], pipes = [first];
    while (this.atOp("&&") || this.atOp("||")) { ops.push(this.next().v); pipes.push(this.parsePipeline(stop)); }
    return { type: "andor", pipes: pipes, ops: ops };
  };
  Parser.prototype.parsePipeline = function (stop) {
    var bang = false;
    if (this.atWord("!")) { bang = true; this.next(); }
    var cmds = [], redirs = [];
    var c0 = this.parseCommand(stop); if (!c0) return null;
    cmds.push(c0);
    while (this.atOp("|")) { this.next(); this.skipNLOnly(); cmds.push(this.parseCommand(stop)); }
    return { type: "pipe", cmds: cmds, bang: bang };
  };
  Parser.prototype.parseCommand = function (stop) {
    var x = this.peek();
    if (x.t === "word") {
      switch (x.v) {
        case "if": return this.parseIf();
        case "while": return this.parseWhile(false);
        case "until": return this.parseWhile(true);
        case "for": return this.parseFor();
        case "case": return this.parseCase();
        case "function": return this.parseFunction();
        case "{": return this.parseBrace();
        case "(": return this.parseSubshell();
      }
    }
    if (x.t === "op" && x.v === "(") return this.parseSubshell();
    // name() { ... }  function definition without the `function` keyword
    if (x.t === "word" && this.peek(1) && this.peek(1).t === "op" && this.peek(1).v === "(" &&
        this.peek(2) && this.peek(2).t === "op" && this.peek(2).v === ")") {
      var fname = this.next().v; this.next(); this.next(); this.skipNLOnly();
      var fbody = this.parseCommand(null);
      return { type: "func", name: fname, body: fbody };
    }
    return this.parseSimple(stop);
  };
  Parser.prototype.parseIf = function () {
    this.next(); // if
    var cond = this.parseList(["then"]); this.expectWord("then");
    var body = this.parseList(["elif", "else", "fi"]);
    var elifs = [], els = null;
    while (this.atWord("elif")) { this.next(); var c = this.parseList(["then"]); this.expectWord("then"); var b = this.parseList(["elif", "else", "fi"]); elifs.push({ c: c, b: b }); }
    if (this.atWord("else")) { this.next(); els = this.parseList(["fi"]); }
    this.expectWord("fi");
    return { type: "if", cond: cond, body: body, elifs: elifs, els: els };
  };
  Parser.prototype.parseWhile = function (until) {
    this.next(); var cond = this.parseList(["do"]); this.expectWord("do");
    var body = this.parseList(["done"]); this.expectWord("done");
    return { type: "while", until: until, cond: cond, body: body };
  };
  Parser.prototype.parseFor = function () {
    this.next(); var name = this.next().v;
    var words = null;
    if (this.atWord("in")) { this.next(); words = []; while (this.peek().t === "word" && !this.atOp(";") && this.peek().t !== "nl" && !this.atWord("do")) words.push(this.next().v); }
    if (this.atOp(";")) this.next();
    this.skipNLOnly();
    this.expectWord("do");
    var body = this.parseList(["done"]); this.expectWord("done");
    return { type: "for", name: name, words: words, body: body };
  };
  Parser.prototype.parseCase = function () {
    this.next(); var word = this.next().v;
    this.skipNLOnly();
    this.expectWord("in");
    var arms = [];
    this.skipNL();
    while (!this.atWord("esac") && this.peek().t !== "eof") {
      // pattern(s) )
      var pats = [];
      while (this.peek().t === "word") { var p = this.next().v; if (p === "esac") { this.i--; break; } pats.push(p); if (this.atOp("|")) this.next(); else break; }
      if (this.atOp(")")) this.next();
      var body = this.parseList(["esac"]);
      if (this.atOp(";;")) this.next();
      this.skipNL();
      arms.push({ pats: pats, body: body });
    }
    this.expectWord("esac");
    return { type: "case", word: word, arms: arms };
  };
  Parser.prototype.parseFunction = function () {
    this.next(); var name = this.next().v;
    if (this.atOp("(")) { this.next(); if (this.atOp(")")) this.next(); }
    this.skipNLOnly();
    var body = this.parseCommand(null);
    return { type: "func", name: name, body: body };
  };
  Parser.prototype.parseBrace = function () {
    this.next(); var list = this.parseList(["}"]); this.expectWord("}");
    return { type: "group", body: list };
  };
  Parser.prototype.parseSubshell = function () {
    if (this.atOp("(")) this.next();
    var list = this.parseList([")"]); if (this.atOp(")")) this.next();
    return { type: "subshell", body: list };
  };
  Parser.prototype.expectWord = function (w) { var x = this.peek(); if (x.t === "word" && x.v === w) { this.next(); return; } throw new Error("syntax error: expected `" + w + "`"); };

  Parser.prototype.parseSimple = function () {
    var assigns = [], words = [], redirs = [];
    while (true) {
      var x = this.peek();
      if (x.t === "op" && (x.v === "<" || x.v === ">" || x.v === ">>" || x.v === "<<" || x.v === "<<-" || x.v === "<<<" || x.v === "&>" || x.v === "fdredir")) {
        redirs.push(this.parseRedir()); continue;
      }
      if (x.t === "word") {
        // assignment only if it looks like name=... and no words yet
        if (words.length === 0 && /^[A-Za-z_][A-Za-z0-9_]*=/.test(x.v)) {
          var eq = x.v.indexOf("=");
          assigns.push({ name: x.v.slice(0, eq), val: x.v.slice(eq + 1) });
          this.next(); continue;
        }
        if (RESERVED[x.v] && words.length === 0) break;
        words.push(this.next().v); continue;
      }
      break;
    }
    if (!words.length && !assigns.length && !redirs.length) return null;
    return { type: "simple", assigns: assigns, words: words, redirs: redirs };
  };
  Parser.prototype.parseRedir = function () {
    var x = this.next();
    if (x.t === "op" && x.v === "fdredir") { return { fd: parseInt(x.fd, 10), op: x.r, target: this.redirectTarget() }; }
    var op = x.v, fd = null;
    if (op === "&>") { return { fd: 1, op: "&>", target: this.redirectTarget() }; }
    if (op === "<<" || op === "<<-") { return { fd: 0, op: "heredoc", strip: op === "<<-", target: this.redirectTarget(true) }; }
    return { fd: op === "<" || op === "<<<" ? 0 : 1, op: op, target: this.redirectTarget() };
  };
  Parser.prototype.redirectTarget = function (raw) {
    var x = this.peek();
    if (x.t === "word") { this.next(); return x.v; }
    return "";
  };

  /* ================= expansion ================= */
  function expandWord(shell, raw, opts) {
    // returns array of fields (after expansions, splitting, globbing)
    opts = opts || {};
    var pieces = [];   // {s, splittable}
    var hadExpansion = false, hadGlobChar = false, quotedAny = false;
    var i = 0, n = raw.length;
    function push(s, splittable) { if (s !== "") pieces.push({ s: s, splittable: !!splittable }); }

    while (i < n) {
      var c = raw[i];
      if (c === "\\") { var nx = raw[i + 1] || ""; push(nx, false); quotedAny = true; i += 2; continue; }
      if (c === "'") {
        quotedAny = true; i++; var s = "";
        while (i < n && raw[i] !== "'") { s += raw[i]; i++; }
        i++; push(s, false); continue;
      }
      if (c === '"') {
        quotedAny = true; i++;
        while (i < n && raw[i] !== '"') {
          if (raw[i] === "\\") { var nx2 = raw[i + 1]; if (nx2 === '"' || nx2 === "\\" || nx2 === "$" || nx2 === "`") { push(nx2, false); i += 2; } else { push("\\", false); i++; } continue; }
          if (raw[i] === "$") { var r = readDollar(shell, raw, i); push(r.text, false); hadExpansion = true; i = r.i; continue; }
          if (raw[i] === "`") { var r2 = readBacktick(shell, raw, i); push(r2.text, false); hadExpansion = true; i = r2.i; continue; }
          push(raw[i], false); i++;
        }
        i++; continue;
      }
      if (c === "$") { var r3 = readDollar(shell, raw, i); push(r3.text, !r3.quoted); hadExpansion = true; i = r3.i; continue; }
      if (c === "`") { var r4 = readBacktick(shell, raw, i); push(r4.text, true); hadExpansion = true; i = r4.i; continue; }
      if (c === "*" || c === "?" || c === "[") hadGlobChar = true;
      push(c, false); i++;
    }

    // field splitting on splittable whitespace/IFS
    var ifs = shell.getVar("IFS"); if (ifs == null) ifs = " \t\n";
    var fields = [], cur = "", curSplittable = false;
    if (ifs !== "") {
      for (var p = 0; p < pieces.length; p++) {
        var pc = pieces[p];
        if (!pc.splittable) { cur += pc.s; continue; }
        for (var k = 0; k < pc.s.length; k++) {
          var ch = pc.s[k];
          if (ifs.indexOf(ch) >= 0) {
            if (cur !== "" || curSplittable) { fields.push(cur); cur = ""; curSplittable = false; }
            else { /* leading separator: drop */ }
          } else { cur += ch; curSplittable = true; }
        }
      }
    } else {
      cur = pieces.map(function (x) { return x.s; }).join("");
    }
    if (cur !== "" || fields.length === 0) fields.push(cur);
    // if everything was empty and there were no pieces, produce empty field only when quoted
    if (pieces.length === 0) fields = quotedAny ? [""] : [];

    // globbing
    var out = [];
    for (var f = 0; f < fields.length; f++) {
      var fld = fields[f];
      if (!quotedAny && hadGlobChar && /[*?\[]/.test(fld)) {
        var g = glob(shell, fld);
        if (g.length) { out = out.concat(g); continue; }
      }
      out.push(fld);
    }
    return out;
  }

  function readDollar(shell, s, i) {
    // s[i] === '$'
    var j = i + 1;
    if (s[j] === "{") {
      var k = j + 1, d = 1, inner = "";
      while (k < s.length && d > 0) { if (s[k] === "{") d++; else if (s[k] === "}") { d--; if (d === 0) break; } inner += s[k]; k++; }
      return { text: expandBraced(shell, inner), i: k + 1 };
    }
    if (s[j] === "(" && s[j + 1] === "(") {
      var k2 = j + 2, d2 = 1, ex = "";
      while (k2 < s.length) { if (s[k2] === "(") d2++; else if (s[k2] === ")") { d2--; if (d2 === 0) break; } ex += s[k2]; k2++; }
      return { text: String(arith(shell, ex)), i: k2 + 2 };
    }
    if (s[j] === "(") {
      var k3 = j + 1, d3 = 1, cmd = "";
      while (k3 < s.length) { if (s[k3] === "(") d3++; else if (s[k3] === ")") { d3--; if (d3 === 0) break; } cmd += s[k3]; k3++; }
      var out = shell.capture(cmd);
      return { text: out.replace(/\n+$/, ""), i: k3 + 1 };
    }
    var m = /^([A-Za-z_][A-Za-z0-9_]*|\?|#|\$|!|\*|@|-|[0-9]+)/.exec(s.slice(j));
    if (!m) return { text: "$", i: j };
    return { text: shell.getVar(m[1]), i: j + m[1].length };
  }

  function readBacktick(shell, s, i) {
    var j = i + 1, cmd = "";
    while (j < s.length && s[j] !== "`") { if (s[j] === "\\") { cmd += s[j + 1] || ""; j += 2; } else { cmd += s[j]; j++; } }
    var out = shell.capture(cmd);
    return { text: out.replace(/\n+$/, ""), i: j + 1 };
  }

  function expandBraced(shell, inner) {
    if (inner === "") return "";
    // ${#var}
    if (inner.charAt(0) === "#") return String(shell.getVar(inner.slice(1)).length);
    var m = /^([A-Za-z_][A-Za-z0-9_]*|[0-9]+|[-?!#$*@])(:?[-=+?])(.*)$/.exec(inner);
    if (m) {
      var name = m[1], op = m[2], arg = m[3];
      var val = shell.getVar(name), unset = (val === "");
      if (op.charAt(0) === ":") {
        if (unset) { if (op === ":-") return expandStr(shell, arg); if (op === ":=") { shell.setVar(name, expandStr(shell, arg)); return expandStr(shell, arg); } if (op === ":?") throw new Error(arg || (name + ": parameter null or not set")); if (op === ":+") return ""; }
        if (op === ":+") return expandStr(shell, arg);
        return val;
      } else {
        var has = shell.hasVar(name);
        if (!has) { if (op === "-") return expandStr(shell, arg); if (op === "=") { shell.setVar(name, expandStr(shell, arg)); return expandStr(shell, arg); } if (op === "?") throw new Error(arg || (name + ": parameter not set")); if (op === "+") return ""; }
        if (op === "+") return expandStr(shell, arg);
        return val;
      }
    }
    return shell.getVar(inner);
  }
  function expandStr(shell, s) { return expandWord(shell, s, {}).join(" "); }

  /* ================= arithmetic ================= */
  function arith(shell, expr) {
    // bash expands command substitutions and $vars inside $((...))
    var s = String(expr)
      .replace(/\$\(\(/g, "$((")
      .replace(/\$\(([^()]*(?:\([^()]*\)[^()]*)*)\)/g, function (_, cmd) { return shell.capture(cmd); })
      .replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g, function (_, n) { var v = shell.getVar(n); return v === "" ? "0" : v; })
      .replace(/\$([A-Za-z_][A-Za-z0-9_]*)/g, function (_, n) { var v = shell.getVar(n); return v === "" ? "0" : v; });
    var i = 0;
    function ws() { while (i < s.length && /\s/.test(s[i])) i++; }
    function peek() { ws(); return s[i]; }
    function parseExpr() { return parseAssign(); }
    function parseAssign() {
      var save = i;
      ws(); var m = /^[A-Za-z_][A-Za-z0-9_]*/.exec(s.slice(i));
      if (m) { var after = i + m[0].length; while (after < s.length && /\s/.test(s[after])) after++;
        if (s[after] === "=" && s[after + 1] !== "=") { i = after + 1; var v = parseAssign(); shell.setVar(m[0], String(v)); return v; } }
      i = save; return parseTernary();
    }
    function parseTernary() { var c = parseOr(); if (peek() === "?") { i++; var a = parseAssign(); if (peek() === ":") i++; var b = parseAssign(); return c ? a : b; } return c; }
    function parseOr() { var l = parseAnd(); while (true) { ws(); if (s.substr(i, 2) === "||") { i += 2; var r = parseAnd(); l = (l || r) ? 1 : 0; } else return l; } }
    function parseAnd() { var l = parseBitOr(); while (true) { ws(); if (s.substr(i, 2) === "&&") { i += 2; var r = parseBitOr(); l = (l && r) ? 1 : 0; } else return l; } }
    function parseBitOr() { var l = parseBitXor(); while (true) { ws(); if (s[i] === "|" && s[i + 1] !== "|") { i++; l = l | parseBitXor(); } else return l; } }
    function parseBitXor() { var l = parseBitAnd(); while (true) { ws(); if (s[i] === "^") { i++; l = l ^ parseBitAnd(); } else return l; } }
    function parseBitAnd() { var l = parseEq(); while (true) { ws(); if (s[i] === "&" && s[i + 1] !== "&") { i++; l = l & parseEq(); } else return l; } }
    function parseEq() { var l = parseRel(); while (true) { ws(); if (s.substr(i, 2) === "==") { i += 2; l = (l == parseRel()) ? 1 : 0; } else if (s.substr(i, 2) === "!=") { i += 2; l = (l != parseRel()) ? 1 : 0; } else return l; } }
    function parseRel() { var l = parseShift(); while (true) { ws(); if (s.substr(i, 2) === "<=") { i += 2; l = (l <= parseShift()) ? 1 : 0; } else if (s.substr(i, 2) === ">=") { i += 2; l = (l >= parseShift()) ? 1 : 0; } else if (s[i] === "<") { i++; l = (l < parseShift()) ? 1 : 0; } else if (s[i] === ">") { i++; l = (l > parseShift()) ? 1 : 0; } else return l; } }
    function parseShift() { var l = parseAdd(); while (true) { ws(); if (s.substr(i, 2) === "<<") { i += 2; l = l << parseAdd(); } else if (s.substr(i, 2) === ">>") { i += 2; l = l >> parseAdd(); } else return l; } }
    function parseAdd() { var l = parseMul(); while (true) { ws(); if (s[i] === "+") { i++; l = l + parseMul(); } else if (s[i] === "-") { i++; l = l - parseMul(); } else return l; } }
    function parseMul() { var l = parseUnary(); while (true) { ws(); if (s[i] === "*" && s[i + 1] !== "*") { i++; l = l * parseUnary(); } else if (s[i] === "/") { i++; var d = parseUnary(); l = d === 0 ? 0 : Math.trunc(l / d); } else if (s[i] === "%") { i++; var d2 = parseUnary(); l = d2 === 0 ? 0 : (l % d2); } else return l; } }
    function parseUnary() {
      ws();
      if (s[i] === "+") { i++; return +parseUnary(); }
      if (s[i] === "-") { i++; return -parseUnary(); }
      if (s[i] === "!") { i++; return parseUnary() ? 0 : 1; }
      if (s[i] === "~") { i++; return ~parseUnary(); }
      if (s.substr(i, 2) === "++") { i += 2; var nm = /^[A-Za-z_][A-Za-z0-9_]*/.exec(s.slice(i))[0]; i += nm.length; var nv = +shell.getVar(nm) + 1; shell.setVar(nm, String(nv)); return nv; }
      if (s.substr(i, 2) === "--") { i += 2; var nm2 = /^[A-Za-z_][A-Za-z0-9_]*/.exec(s.slice(i))[0]; i += nm2.length; var nv2 = +shell.getVar(nm2) - 1; shell.setVar(nm2, String(nv2)); return nv2; }
      return parsePower();
    }
    function parsePower() { var b = parsePrimary(); ws(); if (s.substr(i, 2) === "**") { i += 2; return Math.pow(b, parseUnary()); } return b; }
    function parsePrimary() {
      ws();
      if (s[i] === "(") { i++; var v = parseExpr(); ws(); if (s[i] === ")") i++; return v; }
      var num = /^(0[xX][0-9a-fA-F]+|[0-9]+)/.exec(s.slice(i));
      if (num) { i += num[0].length; return parseInt(num[0], num[0].toLowerCase().indexOf("0x") === 0 ? 16 : 10); }
      var id = /^[A-Za-z_][A-Za-z0-9_]*/.exec(s.slice(i));
      if (id) {
        i += id[0].length;
        if (s.substr(i, 2) === "++") { i += 2; var o1 = parseInt(shell.getVar(id[0]), 10) || 0; shell.setVar(id[0], String(o1 + 1)); return o1; }
        if (s.substr(i, 2) === "--") { i += 2; var o2 = parseInt(shell.getVar(id[0]), 10) || 0; shell.setVar(id[0], String(o2 - 1)); return o2; }
        var val = shell.getVar(id[0]); return val === "" ? 0 : (parseInt(val, 10) || 0);
      }
      return 0;
    }
    return parseExpr();
  }

  /* ================= glob ================= */
  function globMatch(pat, name) {
    // fnmatch-style: * ? [set]
    var pi = 0, ni = 0, star = -1, mark = 0;
    while (ni < name.length) {
      if (pi < pat.length && (pat[pi] === "?" || pat[pi] === name[ni])) { pi++; ni++; }
      else if (pi < pat.length && pat[pi] === "[") {
        var cls = "", k = pi + 1, neg = false;
        if (pat[k] === "!" || pat[k] === "^") { neg = true; k++; }
        while (k < pat.length && pat[k] !== "]") { cls += pat[k]; k++; }
        var ok = false, c = name[ni];
        for (var z = 0; z < cls.length; z++) {
          if (cls[z + 1] === "-" && cls[z + 2] && cls[z + 2] !== "]") { if (c >= cls[z] && c <= cls[z + 2]) ok = true; z += 2; }
          else if (cls[z] === c) ok = true;
        }
        if (ok !== neg) { pi = k + 1; ni++; } else if (star >= 0) { pi = star + 1; ni = ++mark; } else return false;
      }
      else if (pi < pat.length && pat[pi] === "*") { star = pi; mark = ni; pi++; }
      else if (star >= 0) { pi = star + 1; ni = ++mark; }
      else return false;
    }
    while (pi < pat.length && pat[pi] === "*") pi++;
    return pi === pat.length;
  }
  function glob(shell, pattern) {
    var segs = pattern.split("/"), absolute = pattern.charAt(0) === "/";
    var bases = absolute ? ["/"] : [shell.cwd];
    var results = [];
    function walk(base, idx) {
      if (idx >= segs.length) return;
      var seg = segs[idx], last = idx === segs.length - 1;
      var dirAbs = shell.fs.norm("/", base);
      var node = shell.fs.get(dirAbs);
      if (!node || node.t !== "d") return;
      var names = Object.keys(node.c);
      if (seg === "" && idx === 0 && absolute) { walk("/", idx + 1); return; }
      if (!/[*?\[]/.test(seg)) {
        var child = node.c[seg];
        if (!child) return;
        var childAbs = shell.fs.norm(dirAbs, seg);
        if (last) results.push(childAbs); else if (child.t === "d") walk(childAbs, idx + 1);
        return;
      }
      names.forEach(function (nm) {
        if (seg.charAt(0) !== "." && nm.charAt(0) === ".") return;
        if (globMatch(seg, nm)) {
          var a = shell.fs.norm(dirAbs, nm);
          if (last) results.push(a); else if (node.c[nm].t === "d") walk(a, idx + 1);
        }
      });
    }
    if (absolute) walk("/", 1); else walk(shell.cwd, 0);
    return uniq(results).sort();
  }

  /* ================= stdin cursor (fd 0) ================= */
  function mkstdin(str) { return { data: String(str == null ? "" : str), pos: 0 }; }
  function stdinAll(io) { return io && io.stdin ? io.stdin.data.slice(io.stdin.pos) : ""; }

  /* ================= builtins & coreutils ================= */
  // Every command: function(shell, args, io) -> {out, err, code}
  // io = { stdin: string }

  var CMDS = {};

  CMDS["true"] = function () { return { code: 0 }; };
  CMDS[":"] = function () { return { code: 0 }; };
  CMDS["false"] = function () { return { code: 1 }; };
  CMDS["echo"] = function (sh, args) {
    var nl = true, esc = false, a = args.slice(), out = [];
    if (a[0] === "-n") { nl = false; a.shift(); }
    if (a[0] === "-e") { esc = true; a.shift(); }
    if (a[0] === "-ne" || a[0] === "-en") { nl = false; esc = true; a.shift(); }
    for (var i = 0; i < a.length; i++) {
      var s = a[i];
      if (esc) s = s.replace(/\\n/g, "\n").replace(/\\t/g, "\t").replace(/\\\\/g, "\\").replace(/\\c[\s\S]*/, "");
      out.push(s);
    }
    return { out: out.join(" ") + (nl ? "\n" : ""), code: 0 };
  };
  CMDS["printf"] = function (sh, args) {
    if (!args.length) return { out: "", code: 0 };
    var fmt = args[0], rest = args.slice(1), ai = 0, out = "";
    if (!/%/.test(fmt)) return { out: fmt.replace(/\\n/g, "\n").replace(/\\t/g, "\t"), code: 0 };
    function once() { return onePass(); }
    // bash reuses the format until all args are consumed
    do { out += onePass(); } while (ai < rest.length);
    return { out: out, code: 0 };
    function onePass() {
    var out = "", i = 0;
    while (i < fmt.length) {
      var c = fmt[i];
      if (c === "\\") {
        var nx = fmt[i + 1];
        var map = { n: "\n", t: "\t", r: "\r", "\\": "\\", "0": "\0", a: "\x07", b: "\b", f: "\f", v: "\v" };
        if (nx === "x") { var h = /^[0-9a-fA-F]{1,2}/.exec(fmt.slice(i + 2)); if (h) { out += String.fromCharCode(parseInt(h[0], 16)); i += 2 + h[0].length; continue; } }
        if (nx === "0") { var o = /^[0-7]{1,3}/.exec(fmt.slice(i + 2)); if (o) { out += String.fromCharCode(parseInt(o[0], 8)); i += 2 + o[0].length; continue; } }
        if (map[nx] != null) { out += map[nx]; i += 2; continue; }
        out += nx; i += 2; continue;
      }
      if (c === "%") {
        if (fmt[i + 1] === "%") { out += "%"; i += 2; continue; }
        var spec = /^%([-+ 0#]*)(\d+)?(?:\.(\d+))?([diouxXfeEgGcsbq])/.exec(fmt.slice(i));
        if (!spec) { out += "%"; i++; continue; }
        var flags = spec[1] || "", width = spec[2] ? parseInt(spec[2], 10) : 0, prec = spec[3] != null ? parseInt(spec[3], 10) : null, conv = spec[4];
        var arg = rest[ai++]; if (arg === undefined) arg = "";
        var val;
        if (conv === "d" || conv === "i") val = String(parseInt(arg, 10) || 0);
        else if (conv === "u") val = String(Math.abs(parseInt(arg, 10) || 0));
        else if (conv === "o") val = (parseInt(arg, 10) || 0).toString(8);
        else if (conv === "x") val = (parseInt(arg, 10) || 0).toString(16);
        else if (conv === "X") val = (parseInt(arg, 10) || 0).toString(16).toUpperCase();
        else if (conv === "f" || conv === "F") val = (parseFloat(arg) || 0).toFixed(prec == null ? 6 : prec);
        else if (conv === "e" || conv === "E") val = (parseFloat(arg) || 0).toExponential(prec == null ? 6 : prec);
        else if (conv === "g" || conv === "G") val = String(parseFloat(arg) || 0);
        else if (conv === "c") val = String(arg).charAt(0) || "";
        else if (conv === "b") val = String(arg).replace(/\\n/g, "\n").replace(/\\t/g, "\t").replace(/\\\\/g, "\\");
        else if (conv === "q") val = "'" + String(arg).replace(/'/g, "'\\''") + "'";
        else { val = String(arg); if (prec != null) val = val.slice(0, prec); }
        if (width > val.length) {
          var padch = (flags.indexOf("0") >= 0 && "diouxXfeEgG".indexOf(conv) >= 0) ? "0" : " ";
          val = flags.indexOf("-") >= 0 ? pad(val, width, " ") : pad(val, width, padch, true);
        }
        out += val; i += spec[0].length; continue;
      }
      out += c; i++;
    }
    return out;
    }
  };
  CMDS["pwd"] = function (sh) { return { out: sh.cwd + "\n", code: 0 }; };
  CMDS["cd"] = function (sh, args) {
    var t = args[0] || sh.getVar("HOME") || "/";
    if (t === "-") t = sh.getVar("OLDPWD") || "/";
    var abs = sh.fs.norm(sh.cwd, t);
    var n = sh.fs.get(abs);
    if (!n) return { err: "cd: " + t + ": No such file or directory\n", code: 1 };
    if (n.t !== "d") return { err: "cd: " + t + ": Not a directory\n", code: 1 };
    sh.setVar("OLDPWD", sh.cwd); sh.cwd = abs; return { code: 0 };
  };
  CMDS["export"] = function (sh, args) {
    if (!args.length) { var o = ""; sh.exportsList().forEach(function (k) { o += "export " + k + "=" + JSON.stringify(sh.getVar(k)) + "\n"; }); return { out: o, code: 0 }; }
    args.forEach(function (a) { var eq = a.indexOf("="); if (eq >= 0) { sh.setVar(a.slice(0, eq), a.slice(eq + 1)); sh.export(a.slice(0, eq)); } else sh.export(a); });
    return { code: 0 };
  };
  CMDS["unset"] = function (sh, args) { args.forEach(function (a) { sh.unset(a); }); return { code: 0 }; };
  CMDS["set"] = function (sh, args) {
    if (args.length && args[0] === "-e") { sh.errexit = true; return { code: 0 }; }
    if (args.length && (args[0] === "+e")) { sh.errexit = false; return { code: 0 }; }
    if (args.length && args[0].charAt(0) === "-") return { code: 0 };
    if (args.length) { sh.positional = args.slice(); return { code: 0 }; }
    var o = ""; Object.keys(sh.vars).sort().forEach(function (k) { o += k + "=" + JSON.stringify(sh.vars[k]) + "\n"; });
    return { out: o, code: 0 };
  };
  CMDS["env"] = function (sh) { var o = ""; sh.exportsList().sort().forEach(function (k) { o += k + "=" + sh.getVar(k) + "\n"; }); return { out: o, code: 0 }; };
  CMDS["read"] = function (sh, args, io) {
    var cur = io.stdin || mkstdin("");
    var rest = cur.data.slice(cur.pos);
    if (rest === "") return { code: 1 };
    var nl = rest.indexOf("\n");
    var line = nl < 0 ? rest : rest.slice(0, nl);
    cur.pos += (nl < 0 ? rest.length : nl + 1);
    var names = args.length ? args : ["REPLY"];
    if (names.length === 1) sh.setVar(names[0], line);
    else { var parts = line.trim().split(/\s+/); names.forEach(function (nm, i) { sh.setVar(nm, parts[i] || ""); }); }
    return { code: 0 };
  };
  CMDS["exit"] = function (sh, args) { throw new ExitSignal(args.length ? (parseInt(args[0], 10) || 0) : sh.lastCode); };
  CMDS["return"] = function (sh, args) { throw new ReturnSignal(args.length ? (parseInt(args[0], 10) || 0) : sh.lastCode); };
  CMDS["break"] = function (sh, args) { throw new BreakSignal(args.length ? parseInt(args[0], 10) : 1); };
  CMDS["continue"] = function (sh, args) { throw new ContinueSignal(args.length ? parseInt(args[0], 10) : 1); };
  CMDS["shift"] = function (sh, args) { var n = args.length ? parseInt(args[0], 10) : 1; sh.positional = sh.positional.slice(n); return { code: 0 }; };
  CMDS["type"] = function (sh, args) {
    var o = "";
    args.forEach(function (a) { o += a + " is " + (sh.funcs[a] ? "a function" : (CMDS[a] ? "a shell builtin" : "not found")) + "\n"; });
    return { out: o, code: args.every(function (a) { return CMDS[a] || sh.funcs[a]; }) ? 0 : 1 };
  };
  CMDS["which"] = CMDS["type"];
  CMDS["eval"] = function (sh, args) { var c = sh.runString(args.join(" ")); return { code: c }; };
  CMDS["source"] = function (sh, args) { return sh.sourceFile(args[0]); };
  CMDS["."] = CMDS["source"];
  CMDS["alias"] = function (sh, args) {
    if (!args.length) { var o = ""; Object.keys(sh.aliases).forEach(function (k) { o += "alias " + k + "='" + sh.aliases[k] + "'\n"; }); return { out: o, code: 0 }; }
    args.forEach(function (a) { var eq = a.indexOf("="); if (eq >= 0) sh.aliases[a.slice(0, eq)] = a.slice(eq + 1).replace(/^'(.*)'$/, "$1"); });
    return { code: 0 };
  };
  CMDS["unalias"] = function (sh, args) { args.forEach(function (a) { delete sh.aliases[a]; }); return { code: 0 }; };
  CMDS["sleep"] = function (sh, args) { return { code: 0, _sleep: parseFloat(args[0] || "0") }; };
  CMDS["clear"] = function () { return { out: "\x1b[2J\x1b[H", code: 0 }; };
  CMDS["history"] = function (sh) { var o = ""; sh.history.forEach(function (h, i) { o += pad(i + 1, 5, " ", true) + "  " + h + "\n"; }); return { out: o, code: 0 }; };

  /* test / [ */
  function doTest(sh, a) {
    var i = 0;
    function primary() {
      var t = a[i];
      if (t === "!") { i++; return !primary(); }
      if (t === "(") { i++; var v = or(); if (a[i] === ")") i++; return v; }
      if (t === "-z") { i++; return (a[i++] || "") === ""; }
      if (t === "-n") { i++; return (a[i++] || "") !== ""; }
      if (t === "-e") { i++; return !!sh.fs.get(sh.fs.norm(sh.cwd, a[i++])); }
      if (t === "-f") { i++; var n = sh.fs.get(sh.fs.norm(sh.cwd, a[i++])); return !!n && n.t === "f"; }
      if (t === "-d") { i++; var d = sh.fs.get(sh.fs.norm(sh.cwd, a[i++])); return !!d && d.t === "d"; }
      if (t === "-s") { i++; var s = sh.fs.get(sh.fs.norm(sh.cwd, a[i++])); return !!s && s.t === "f" && s.d.length > 0; }
      if (t === "-r" || t === "-w" || t === "-x") { i++; return !!sh.fs.get(sh.fs.norm(sh.cwd, a[i++])); }
      var lhs = a[i++];
      var op = a[i];
      if (op === "=" || op === "==") { i++; return lhs === a[i++]; }
      if (op === "!=") { i++; return lhs !== a[i++]; }
      if (op === "-eq") { i++; return parseInt(lhs, 10) === parseInt(a[i++], 10); }
      if (op === "-ne") { i++; return parseInt(lhs, 10) !== parseInt(a[i++], 10); }
      if (op === "-lt") { i++; return parseInt(lhs, 10) < parseInt(a[i++], 10); }
      if (op === "-le") { i++; return parseInt(lhs, 10) <= parseInt(a[i++], 10); }
      if (op === "-gt") { i++; return parseInt(lhs, 10) > parseInt(a[i++], 10); }
      if (op === "-ge") { i++; return parseInt(lhs, 10) >= parseInt(a[i++], 10); }
      return lhs !== "";
    }
    function and() { var l = primary(); while (a[i] === "-a") { i++; var r = primary(); l = l && r; } return l; }
    function or() { var l = and(); while (a[i] === "-o") { i++; var r = and(); l = l || r; } return l; }
    return or();
  }
  CMDS["test"] = function (sh, args) { return { code: doTest(sh, args) ? 0 : 1 }; };
  CMDS["["] = function (sh, args) { var a = args.slice(); if (a[a.length - 1] === "]") a.pop(); return { code: doTest(sh, a) ? 0 : 1 }; };

  /* ---- file commands ---- */
  CMDS["ls"] = function (sh, args) {
    var long = false, all = false, one = false, paths = [];
    args.forEach(function (a) {
      if (a === "-l") long = true; else if (a === "-a" || a === "-la" || a === "-al") { all = true; if (a.indexOf("l") >= 0) long = true; }
      else if (a === "-1") one = true; else if (a.charAt(0) === "-" && a.length > 1) { if (a.indexOf("a") >= 0) all = true; if (a.indexOf("l") >= 0) long = true; if (a.indexOf("1") >= 0) one = true; }
      else paths.push(a);
    });
    if (!paths.length) paths = ["."];
    var out = "", code = 0, multi = paths.length > 1;
    paths.forEach(function (p, idx) {
      var abs = sh.fs.norm(sh.cwd, p), node = sh.fs.get(abs);
      if (!node) { out += "ls: cannot access '" + p + "': No such file or directory\n"; code = 2; return; }
      if (multi) out += (idx ? "\n" : "") + p + ":\n";
      if (node.t === "f") { out += p.split("/").pop() + "\n"; return; }
      var names = Object.keys(node.c).sort();
      if (!all) names = names.filter(function (n) { return n.charAt(0) !== "."; });
      if (long) {
        names.forEach(function (nm) {
          var c = node.c[nm], kind = c.t === "d" ? "d" : "-", size = c.t === "d" ? 4096 : c.d.length;
          out += kind + oct(c.m || 420) + " 1 user user " + pad(size, 6, " ", true) + " Jan  1 00:00 " + nm + "\n";
        });
      } else { out += names.join("\n") + (names.length ? "\n" : ""); }
    });
    return { out: out, code: code };
  };
  CMDS["cat"] = function (sh, args, io) {
    var a = args.filter(function (x) { return x.charAt(0) !== "-" || x === "-"; });
    if (!a.length) return { out: stdinAll(io), code: 0 };
    var out = "", code = 0;
    a.forEach(function (p) {
      if (p === "-") { out += stdinAll(io); return; }
      var abs = sh.fs.norm(sh.cwd, p), n = sh.fs.get(abs);
      if (!n) { out += "cat: " + p + ": No such file or directory\n"; code = 1; }
      else if (n.t === "d") { out += "cat: " + p + ": Is a directory\n"; code = 1; }
      else out += n.d;
    });
    return { out: out, code: code };
  };
  CMDS["head"] = function (sh, args, io) {
    var n = 10, files = [];
    for (var i = 0; i < args.length; i++) { if (args[i] === "-n") { n = parseInt(args[++i], 10); } else if (/^-\d+$/.test(args[i])) { n = parseInt(args[i].slice(1), 10); } else if (args[i].charAt(0) !== "-") files.push(args[i]); }
    var data = files.length ? files.map(function (f) { var x = sh.fs.get(sh.fs.norm(sh.cwd, f)); return x && x.t === "f" ? x.d : ""; }).join("") : (stdinAll(io));
    var lines = data.split("\n"); var keep = lines.slice(0, n).join("\n"); if (data.slice(-1) === "\n" && n <= lines.length - 1) keep += "\n";
    return { out: keep, code: 0 };
  };
  CMDS["tail"] = function (sh, args, io) {
    var n = 10, fromStart = false, files = [];
    for (var i = 0; i < args.length; i++) {
      if (args[i] === "-n") { var v = args[++i]; if (v.charAt(0) === "+") { fromStart = true; n = parseInt(v.slice(1), 10); } else n = parseInt(v, 10); }
      else if (/^-\d+$/.test(args[i])) n = parseInt(args[i].slice(1), 10);
      else if (args[i].charAt(0) !== "-") files.push(args[i]);
    }
    var data = files.length ? files.map(function (f) { var x = sh.fs.get(sh.fs.norm(sh.cwd, f)); return x && x.t === "f" ? x.d : ""; }).join("") : (stdinAll(io));
    var lines = data.split("\n"); if (data.slice(-1) === "\n") lines.pop();
    var out = fromStart ? lines.slice(n - 1) : lines.slice(-n);
    return { out: out.join("\n") + (out.length ? "\n" : ""), code: 0 };
  };
  CMDS["wc"] = function (sh, args, io) {
    var l = false, w = false, c = false, files = [];
    args.forEach(function (a) { if (a === "-l") l = true; else if (a === "-w") w = true; else if (a === "-c") c = true; else if (a === "-lwc" || a === "-clw") { l = w = c = true; } else if (a.charAt(0) !== "-") files.push(a); });
    if (!l && !w && !c) l = w = c = true;
    var data = files.length ? files.map(function (f) { var x = sh.fs.get(sh.fs.norm(sh.cwd, f)); return x && x.t === "f" ? x.d : ""; }).join("") : (stdinAll(io));
    var lines = (data === "" ? 0 : data.split("\n").length - (data.slice(-1) === "\n" ? 1 : 0));
    var words = data.split(/\s+/).filter(function (x) { return x !== ""; }).length;
    var parts = []; if (l) parts.push(lines); if (w) parts.push(words); if (c) parts.push(data.length);
    return { out: parts.join(" ") + (files.length ? " " + files[0] : "") + "\n", code: 0 };
  };
  CMDS["mkdir"] = function (sh, args) {
    var p = false, mode = 493, dirs = [];
    args.forEach(function (a) { if (a === "-p") p = true; else if (a === "-m") { } else if (a.charAt(0) !== "-") dirs.push(a); });
    var code = 0, out = "";
    dirs.forEach(function (d) {
      var abs = sh.fs.norm(sh.cwd, d);
      if (sh.fs.get(abs)) { if (!p) { out += "mkdir: cannot create directory '" + d + "': File exists\n"; code = 1; } return; }
      if (!sh.fs.mkdirp(abs, mode) && !p) { out += "mkdir: cannot create directory '" + d + "'\n"; code = 1; }
    });
    return { out: out, code: code };
  };
  CMDS["rmdir"] = function (sh, args) {
    var code = 0, out = "";
    args.filter(function (a) { return a.charAt(0) !== "-"; }).forEach(function (d) {
      var abs = sh.fs.norm(sh.cwd, d), n = sh.fs.get(abs);
      if (!n) { out += "rmdir: failed to remove '" + d + "': No such file or directory\n"; code = 1; return; }
      if (n.t !== "d") { out += "rmdir: failed to remove '" + d + "': Not a directory\n"; code = 1; return; }
      if (Object.keys(n.c).length) { out += "rmdir: failed to remove '" + d + "': Directory not empty\n"; code = 1; return; }
      sh.fs.unlink(abs);
    });
    return { out: out, code: code };
  };
  CMDS["rm"] = function (sh, args) {
    var rec = false, force = false, paths = [];
    args.forEach(function (a) { if (a === "-r" || a === "-rf" || a === "-fr") rec = true; if (a === "-f" || a === "-rf" || a === "-fr") force = true; if (a.charAt(0) !== "-") paths.push(a); });
    var code = 0, out = "";
    function del(abs, name) {
      var n = sh.fs.get(abs);
      if (!n) { if (!force) { out += "rm: cannot remove '" + name + "': No such file or directory\n"; code = 1; } return; }
      if (n.t === "d" && !rec) { out += "rm: cannot remove '" + name + "': Is a directory\n"; code = 1; return; }
      sh.fs.unlink(abs);
    }
    paths.forEach(function (p) { del(sh.fs.norm(sh.cwd, p), p); });
    return { out: out, code: code };
  };
  CMDS["touch"] = function (sh, args) {
    args.filter(function (a) { return a.charAt(0) !== "-"; }).forEach(function (p) { var abs = sh.fs.norm(sh.cwd, p); if (!sh.fs.get(abs)) sh.fs.writeFile(abs, ""); });
    return { code: 0 };
  };
  CMDS["cp"] = function (sh, args) {
    var rec = false, paths = [];
    args.forEach(function (a) { if (a === "-r" || a === "-R") rec = true; else if (a.charAt(0) !== "-") paths.push(a); });
    if (paths.length < 2) return { err: "cp: missing destination\n", code: 1 };
    var dst = paths.pop(), dstAbs = sh.fs.norm(sh.cwd, dst), dstNode = sh.fs.get(dstAbs);
    var code = 0, out = "";
    paths.forEach(function (src) {
      var srcAbs = sh.fs.norm(sh.cwd, src), n = sh.fs.get(srcAbs);
      if (!n) { out += "cp: cannot stat '" + src + "': No such file or directory\n"; code = 1; return; }
      if (n.t === "d" && !rec) { out += "cp: -r not specified; omitting directory '" + src + "'\n"; code = 1; return; }
      if (dstNode && dstNode.t === "d") sh.fs.writeFile(sh.fs.norm(dstAbs, src.split("/").pop()), n.t === "f" ? n.d : "", n.m);
      else sh.fs.writeFile(dstAbs, n.t === "f" ? n.d : "", n.m);
    });
    return { out: out, code: code };
  };
  CMDS["mv"] = function (sh, args) {
    var paths = args.filter(function (a) { return a.charAt(0) !== "-"; });
    if (paths.length < 2) return { err: "mv: missing destination\n", code: 1 };
    var dst = paths.pop(), dstAbs = sh.fs.norm(sh.cwd, dst), dstNode = sh.fs.get(dstAbs);
    var code = 0, out = "";
    paths.forEach(function (src) {
      var srcAbs = sh.fs.norm(sh.cwd, src), n = sh.fs.get(srcAbs);
      if (!n) { out += "mv: cannot stat '" + src + "': No such file or directory\n"; code = 1; return; }
      if (dstNode && dstNode.t === "d") sh.fs.writeFile(sh.fs.norm(dstAbs, src.split("/").pop()), n.t === "f" ? n.d : "", n.m);
      else sh.fs.writeFile(dstAbs, n.t === "f" ? n.d : "", n.m);
      sh.fs.unlink(srcAbs);
    });
    return { out: out, code: code };
  };
  CMDS["basename"] = function (sh, args) { var p = (args[0] || "").replace(/\/+$/, ""); var b = p.split("/").pop() || "/"; if (args[1] && b.slice(-args[1].length) === args[1]) b = b.slice(0, -args[1].length); return { out: b + "\n", code: 0 }; };
  CMDS["dirname"] = function (sh, args) { var p = (args[0] || "").replace(/\/+$/, ""); var parts = p.split("/"); parts.pop(); var d = parts.join("/") || (p.charAt(0) === "/" ? "/" : "."); if (d === "") d = "/"; return { out: d + "\n", code: 0 }; };
  CMDS["stat"] = function (sh, args) {
    var p = args.filter(function (a) { return a.charAt(0) !== "-"; })[0];
    var abs = sh.fs.norm(sh.cwd, p), n = sh.fs.get(abs);
    if (!n) return { err: "stat: cannot statx '" + p + "': No such file or directory\n", code: 1 };
    return { out: "  File: " + p + "\n  Size: " + (n.t === "d" ? 4096 : n.d.length) + "\tType: " + (n.t === "d" ? "directory" : "regular file") + "\n", code: 0 };
  };
  CMDS["du"] = function (sh, args) {
    var p = args.filter(function (a) { return a.charAt(0) !== "-"; })[0] || ".";
    var abs = sh.fs.norm(sh.cwd, p), n = sh.fs.get(abs);
    if (!n) return { err: "du: cannot access '" + p + "'\n", code: 1 };
    function size(node) { if (node.t === "f") return node.d.length; var s = 0; Object.keys(node.c).forEach(function (k) { s += size(node.c[k]); }); return s; }
    return { out: Math.ceil(size(n) / 1024) + "\t" + p + "\n", code: 0 };
  };
  CMDS["tree"] = function (sh, args) {
    var p = args.filter(function (a) { return a.charAt(0) !== "-"; })[0] || ".";
    var abs = sh.fs.norm(sh.cwd, p), n = sh.fs.get(abs);
    if (!n) return { err: p + " [error opening dir]\n", code: 1 };
    var out = p + "\n", nd = 0, nf = 0;
    function walk(node, prefix) {
      var names = Object.keys(node.c).sort();
      names.forEach(function (nm, i) {
        var last = i === names.length - 1, c = node.c[nm];
        out += prefix + (last ? "└── " : "├── ") + nm + "\n";
        if (c.t === "d") { nd++; walk(c, prefix + (last ? "    " : "│   ")); } else nf++;
      });
    }
    walk(n, "");
    out += "\n" + nd + " directories, " + nf + " files\n";
    return { out: out, code: 0 };
  };
  CMDS["find"] = function (sh, args) {
    var root = ".", name = null, type = null, maxd = 1e9, i = 0;
    if (args[0] && args[0].charAt(0) !== "-") { root = args[0]; i = 1; }
    for (; i < args.length; i++) {
      if (args[i] === "-name") name = args[++i];
      else if (args[i] === "-type") type = args[++i];
      else if (args[i] === "-maxdepth") maxd = parseInt(args[++i], 10);
    }
    var abs = sh.fs.norm(sh.cwd, root), out = "";
    function walk(a, d, rel) {
      var n = sh.fs.get(a); if (!n) return;
      var nm = a.split("/").pop() || "/";
      var okType = !type || (type === "d" ? n.t === "d" : n.t === "f");
      var okName = !name || globMatch(name, nm);
      if (okType && okName && d >= 0) out += (rel || a) + "\n";
      if (n.t === "d" && d < maxd) Object.keys(n.c).sort().forEach(function (k) { walk(sh.fs.norm(a, k), d + 1, (rel || root) + "/" + k); });
    }
    walk(abs, 0, root === "." ? "." : root);
    return { out: out, code: 0 };
  };

  /* ---- text commands ---- */
  CMDS["grep"] = function (sh, args, io) {
    var i = 0, ic = false, inv = false, num = false, cnt = false, quiet = false, list = false, word = false, only = false, extended = false, fixed = false, pats = [], files = [];
    for (; i < args.length; i++) {
      var a = args[i];
      if (a === "-e") { pats.push(args[++i]); continue; }
      if (a === "-f") { var fn = sh.fs.get(sh.fs.norm(sh.cwd, args[++i])); if (fn) pats.push(fn.d.replace(/\n$/, "")); continue; }
      if (a.charAt(0) === "-" && a.length > 1 && !/^-$/.test(a)) {
        for (var k = 1; k < a.length; k++) { var ch = a[k];
          if (ch === "i") ic = true; else if (ch === "v") inv = true; else if (ch === "n") num = true; else if (ch === "c") cnt = true;
          else if (ch === "q") quiet = true; else if (ch === "l") list = true; else if (ch === "w") word = true; else if (ch === "o") only = true;
          else if (ch === "E") extended = true; else if (ch === "F") fixed = true; }
        continue;
      }
      if (pats.length === 0 && !files.length) { pats.push(a); continue; }
      files.push(a);
    }
    if (!pats.length) return { err: "grep: no pattern\n", code: 2 };
    var src = files.length ? files.map(function (f) { var x = sh.fs.get(sh.fs.norm(sh.cwd, f)); return x && x.t === "f" ? x.d : ""; }).join("") : (stdinAll(io));
    var flags = (ic ? "i" : "");
    var res = "", matches = 0, lines = src.split("\n"); if (src.slice(-1) === "\n") lines.pop();
    lines.forEach(function (ln, idx) {
      var hit = pats.some(function (p) {
        var re;
        try { re = fixed ? new RegExp(escRe(p), flags) : new RegExp(extended ? p : breToJs(p), flags); } catch (e) { re = new RegExp(escRe(p), flags); }
        if (word) { var m = ln.match(re); return m && new RegExp("\\b" + escRe(m[0]) + "\\b", flags).test(ln) && re.test(ln); }
        return re.test(ln);
      });
      if (hit !== inv) {
        matches++;
        if (quiet) return;
        if (list) { if (files.length) res += files[0] + "\n"; return; }
        var prefix = (num ? (idx + 1) + ":" : "") + (files.length > 1 && !list ? "" : "");
        if (only) { var re2; try { re2 = new RegExp(fixed ? escRe(pats[0]) : (extended ? pats[0] : breToJs(pats[0])), flags + "g"); } catch (e) { re2 = new RegExp(escRe(pats[0]), flags + "g"); } var mm = ln.match(re2); if (mm) mm.forEach(function (x) { res += prefix + x + "\n"; }); }
        else res += prefix + ln + "\n";
      }
    });
    if (quiet) return { code: matches ? 0 : 1 };
    if (cnt) res = matches + "\n";
    return { out: res, code: matches ? 0 : 1 };
  };
  function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
  function breToJs(p) { return p.replace(/\\\(/g, "(").replace(/\\\)/g, ")").replace(/\\\|/g, "|").replace(/\\\+/g, "+").replace(/\\\?/g, "?"); }

  CMDS["sort"] = function (sh, args, io) {
    var numeric = false, rev = false, uniqF = false, key = null, sep = null;
    for (var i = 0; i < args.length; i++) {
      var a = args[i];
      if (a === "-n") numeric = true; else if (a === "-r") rev = true; else if (a === "-u") uniqF = true;
      else if (a === "-k") key = parseInt(args[++i], 10); else if (a === "-t") sep = args[++i];
      else if (a.charAt(0) === "-") { if (a.indexOf("n") >= 0) numeric = true; if (a.indexOf("r") >= 0) rev = true; if (a.indexOf("u") >= 0) uniqF = true; }
    }
    var data = stdinAll(io);
    var lines = data.split("\n"); if (data.slice(-1) === "\n") lines.pop();
    function keyOf(l) { if (key == null) return l; var parts = sep ? l.split(sep) : l.trim().split(/\s+/); return parts[key - 1] || ""; }
    lines.sort(function (a, b) { var ka = keyOf(a), kb = keyOf(b); var r = numeric ? (parseFloat(ka) - parseFloat(kb)) : (ka < kb ? -1 : ka > kb ? 1 : 0); return rev ? -r : r; });
    if (uniqF) { var seen = {}, o = []; lines.forEach(function (l) { var k = keyOf(l); if (!seen[k]) { seen[k] = 1; o.push(l); } }); lines = o; }
    return { out: lines.join("\n") + (lines.length ? "\n" : ""), code: 0 };
  };
  CMDS["uniq"] = function (sh, args, io) {
    var count = false, dup = false, onlyDup = false, uniqOnly = false;
    args.forEach(function (a) { if (a === "-c") count = true; else if (a === "-d") dup = true; else if (a === "-D") onlyDup = true; else if (a === "-u") uniqOnly = true; });
    var data = stdinAll(io), lines = data.split("\n"); if (data.slice(-1) === "\n") lines.pop();
    var out = "", i = 0;
    while (i < lines.length) {
      var j = i; while (j + 1 < lines.length && lines[j + 1] === lines[i]) j++;
      var n = j - i + 1, val = lines[i];
      var emit = true;
      if (dup && n < 2) emit = false; if (uniqOnly && n > 1) emit = false; if (onlyDup && n < 2) emit = false;
      if (emit) out += (count ? pad(n, 7, " ", true) + " " : "") + val + "\n";
      i = j + 1;
    }
    return { out: out, code: 0 };
  };
  CMDS["cut"] = function (sh, args, io) {
    var delim = "\t", fields = null, chars = null;
    for (var i = 0; i < args.length; i++) {
      var a = args[i];
      if (a === "-d") delim = args[++i];
      else if (a === "-f") fields = args[++i];
      else if (a === "-c") chars = args[++i];
      else if (a.slice(0, 2) === "-d") delim = a.slice(2);
      else if (a.slice(0, 2) === "-f") fields = a.slice(2);
      else if (a.slice(0, 2) === "-c") chars = a.slice(2);
    }
    var data = stdinAll(io), lines = data.split("\n"); if (data.slice(-1) === "\n") lines.pop();
    function range(spec, len) { var out = []; spec.split(",").forEach(function (r) { var m = /^(\d+)-(\d+)$/.exec(r); if (m) { for (var x = +m[1]; x <= +m[2]; x++) out.push(x); } else if (/^\d+$/.test(r)) out.push(+r); }); return out; }
    var out = lines.map(function (l) {
      if (chars) { var idx = range(chars); return idx.map(function (k) { return l[k - 1] || ""; }).join(""); }
      var parts = delim === "\t" && l.indexOf("\t") < 0 ? l.split(/\s+/) : l.split(delim);
      var fi = range(fields || "1");
      return fi.map(function (k) { return parts[k - 1] == null ? "" : parts[k - 1]; }).join(delim);
    });
    return { out: out.join("\n") + (out.length ? "\n" : ""), code: 0 };
  };
  CMDS["tr"] = function (sh, args, io) {
    var del = false, sq = false, sets = [];
    args.forEach(function (a) { if (a === "-d") del = true; else if (a === "-s") sq = true; else if (a === "-") sets.push(a); else if (a.charAt(0) !== "-") sets.push(a); });
    function expandSet(s) { var out = "", i = 0; s = s.replace(/\\n/g, "\n").replace(/\\t/g, "\t"); while (i < s.length) { if (s[i + 1] === "-" && s[i + 2]) { for (var c = s.charCodeAt(i); c <= s.charCodeAt(i + 2); c++) out += String.fromCharCode(c); i += 3; } else { out += s[i]; i++; } } return out; }
    var data = stdinAll(io);
    var from = expandSet(sets[0] || ""), to = expandSet(sets[1] || "");
    var res = "";
    for (var k = 0; k < data.length; k++) {
      var ch = data[k], idx = from.indexOf(ch);
      if (del) { if (idx < 0) res += ch; continue; }
      if (idx >= 0) ch = to ? (to[idx] != null ? to[idx] : to[to.length - 1]) : ch;
      if (sq && res.slice(-1) === ch && (from.indexOf(ch) >= 0 || to.indexOf(ch) >= 0)) continue;
      res += ch;
    }
    return { out: res, code: 0 };
  };
  CMDS["sed"] = function (sh, args, io) {
    var quiet = false, scripts = [], files = [];
    for (var i = 0; i < args.length; i++) {
      if (args[i] === "-n") quiet = true;
      else if (args[i] === "-e") scripts.push(args[++i]);
      else if (args[i] === "-E" || args[i] === "-r") { }
      else if (args[i].charAt(0) === "-" && args[i].length > 1 && !/^-$/.test(args[i])) { if (args[i].indexOf("n") >= 0) quiet = true; }
      else if (!scripts.length && files.length === 0) scripts.push(args[i]);
      else files.push(args[i]);
    }
    if (!scripts.length) return { code: 0 };
    var data = stdinAll(io), lines = data.split("\n"); if (data.slice(-1) === "\n") lines.pop();
    var out = [];
    lines.forEach(function (ln, idx) {
      var lnNo = idx + 1, cur = ln, print = !quiet, deleted = false;
      scripts.forEach(function (scr) {
        scr.split(";").forEach(function (cmd) {
          cmd = cmd.trim(); if (!cmd) return;
          var addr = null, rest = cmd;
          var am = /^(\d+|\$)(,(\d+|\$))?/.exec(cmd);
          if (am) { addr = am[0]; rest = cmd.slice(am[0].length); }
          function inRange() {
            if (!addr) return true;
            var parts = addr.split(",");
            function val(x) { return x === "$" ? lines.length : parseInt(x, 10); }
            if (parts.length === 1) return lnNo === val(parts[0]);
            return lnNo >= val(parts[0]) && lnNo <= val(parts[1]);
          }
          if (rest === "p") { if (inRange()) out.push(cur); return; }
          if (rest === "d") { if (inRange()) deleted = true; return; }
          if (rest.charAt(0) === "s") {
            var sm = /^s(.)(.*?)\1(.*?)\1([gi]*)$/.exec(rest);
            if (sm && inRange()) {
              var pat = sm[2], rep = sm[3], fl = sm[4];
              try {
                var re = new RegExp(pat, fl.indexOf("g") >= 0 ? "g" : "");
                rep = rep.replace(/\\([0-9])/g, "$$$1").replace(/&/g, "$&");
                cur = cur.replace(re, rep);
              } catch (e) { }
            }
          }
        });
      });
      if (!deleted) { if (print) out.push(cur); }
      else if (quiet) { }
    });
    return { out: out.join("\n") + (out.length ? "\n" : ""), code: 0 };
  };
  CMDS["awk"] = function (sh, args, io) {
    // minimal: awk '{print $N}' / '{print}' / -F, patterns; enough for pipelines
    var fs = /\s+/, prog = null, files = [], i = 0;
    for (; i < args.length; i++) { if (args[i] === "-F") fs = args[++i]; else if (!prog) prog = args[i]; else files.push(args[i]); }
    if (!prog) return { err: "awk: no program\n", code: 2 };
    var data = files.length ? files.map(function (f) { var x = sh.fs.get(sh.fs.norm(sh.cwd, f)); return x && x.t === "f" ? x.d : ""; }).join("") : (stdinAll(io));
    var lines = data.split("\n"); if (data.slice(-1) === "\n") lines.pop();
    var out = "";
    var body = prog.replace(/^\{/, "").replace(/\}$/, "");
    var parts = body.split(";");
    lines.forEach(function (ln, idx) {
      var f = fs === /\s+/ ? ln.split(/\s+/) : ln.split(fs);
      parts.forEach(function (st) {
        st = st.trim(); if (!st) return;
        var pm = /^print\s*(.*)$/.exec(st);
        if (pm) {
          var ex = pm[1];
          if (ex === "") out += ln + "\n";
          else {
            var pieces = ex.split(/"([^"]*)"/), acc = "";
            for (var q = 0; q < pieces.length; q++) {
              if (q % 2 === 1) { acc += pieces[q]; }
              else { acc += pieces[q].replace(/\$(\d+)/g, function (_, d) { return f[+d - 1] == null ? "" : f[+d - 1]; }).replace(/\s*,\s*/g, " "); }
            }
            out += acc + "\n";
          }
        }
      });
    });
    return { out: out, code: 0 };
  };
  CMDS["seq"] = function (sh, args) {
    var a = args.filter(function (x) { return x.charAt(0) !== "-" || /^-\d/.test(x); });
    var first = 1, step = 1, last;
    if (a.length === 1) last = parseFloat(a[0]);
    else if (a.length === 2) { first = parseFloat(a[0]); last = parseFloat(a[1]); }
    else { first = parseFloat(a[0]); step = parseFloat(a[1]); last = parseFloat(a[2]); }
    var out = "";
    if (step === 0) return { err: "seq: step cannot be zero\n", code: 1 };
    for (var v = first; step > 0 ? v <= last : v >= last; v += step) out += (Number.isInteger(v) ? v : v) + "\n";
    return { out: out, code: 0 };
  };
  CMDS["expr"] = function (sh, args) {
    if (args.length === 1) return { out: args[0] + "\n", code: 0 };
    if (args[1] === ":") { var re = new RegExp("^" + args[2]); var m = args[0].match(re); return { out: (m ? m[0] : "") + "\n", code: m ? 0 : 1 }; }
    try { var v = arith(sh, args.join(" ")); return { out: String(v) + "\n", code: v ? 0 : 1 }; } catch (e) { return { err: "expr: syntax error\n", code: 2 }; }
  };
  CMDS["date"] = function (sh, args) {
    var fmt = "+%a %b %e %H:%M:%S %Z %Y", i = 0;
    if (args[0] && args[0].charAt(0) === "+") fmt = args[0];
    var d = new Date(sh.now || Date.now());
    var map = { Y: d.getFullYear(), m: pad(d.getMonth() + 1, 2, "0", true), d: pad(d.getDate(), 2, "0", true),
      H: pad(d.getHours(), 2, "0", true), M: pad(d.getMinutes(), 2, "0", true), S: pad(d.getSeconds(), 2, "0", true),
      s: Math.floor(d.getTime() / 1000), F: d.getFullYear() + "-" + pad(d.getMonth() + 1, 2, "0", true) + "-" + pad(d.getDate(), 2, "0", true) };
    var out = fmt.replace(/^\+/, "").replace(/%([YmdHMsF])/g, function (_, c) { return map[c]; });
    return { out: out + "\n", code: 0 };
  };
  CMDS["rev"] = function (sh, args, io) {
    var data = stdinAll(io), lines = data.split("\n"); if (data.slice(-1) === "\n") lines.pop();
    return { out: lines.map(function (l) { return l.split("").reverse().join(""); }).join("\n") + (lines.length ? "\n" : ""), code: 0 };
  };
  CMDS["tac"] = function (sh, args, io) {
    var data = stdinAll(io), lines = data.split("\n"); if (data.slice(-1) === "\n") lines.pop();
    return { out: lines.reverse().join("\n") + (lines.length ? "\n" : ""), code: 0 };
  };
  CMDS["nl"] = function (sh, args, io) {
    var data = stdinAll(io), lines = data.split("\n"); if (data.slice(-1) === "\n") lines.pop();
    return { out: lines.map(function (l, i) { return pad(i + 1, 6, " ", true) + "\t" + l; }).join("\n") + (lines.length ? "\n" : ""), code: 0 };
  };
  CMDS["less"] = function (sh, args, io) { return CMDS["cat"](sh, args, io); };
  CMDS["more"] = CMDS["less"];
  CMDS["help"] = function (sh) {
    var names = Object.keys(CMDS).sort().join("  ");
    return { out: "DarkTerm " + VERSION + " — builtins & commands:\n\n" + names + "\n\nshell: quoting, $VAR ${VAR:-x} $((arith)) $(cmd), pipes |, redirects < > >> 2> &>, ; && || &, if/for/while/until/case, functions, globs.\n", code: 0 };
  };

  /* ================= Shell ================= */
  function Shell(opts) {
    opts = opts || {};
    this.fs = opts.fs || new VFS();
    this.cwd = opts.cwd || "/home/inscriber";
    this.vars = { PATH: "/bin:/usr/bin", HOME: this.cwd, PWD: this.cwd, IFS: " \t\n", "?": "0", "$": "0", "#": "0" };
    this._exports = { PATH: 1, HOME: 1, PWD: 1 };
    this.positional = [];
    this.funcs = {};
    this.aliases = {};
    this.lastCode = 0;
    this.errexit = false;
    this.history = [];
    this.now = opts.now || 0;
    this.loopDepth = 0;
    this.funcDepth = 0;
    this._lineNo = 0;
  }
  Shell.prototype.getVar = function (name) {
    if (name === "?") return String(this.lastCode);
    if (name === "$") return "1";
    if (name === "#") return String(this.positional.length);
    if (/^[0-9]+$/.test(name)) return this.positional[parseInt(name, 10) - 1] || "";
    if (name === "*" || name === "@") return this.positional.join(" ");
    if (Object.prototype.hasOwnProperty.call(this.vars, name)) return this.vars[name];
    return "";
  };
  Shell.prototype.hasVar = function (name) { return Object.prototype.hasOwnProperty.call(this.vars, name); };
  Shell.prototype.setVar = function (name, val) { this.vars[name] = String(val); };
  Shell.prototype.unset = function (name) { delete this.vars[name]; delete this._exports[name]; };
  Shell.prototype.export = function (name) { this._exports[name] = 1; };
  Shell.prototype.exportsList = function () { return Object.keys(this._exports); };

  Shell.prototype.capture = function (cmd) {
    var sub = this.fork();
    var r = sub.runString(String(cmd));
    return sub._stdout != null ? sub._stdout : "";
  };
  Shell.prototype.fork = function () {
    var s = new Shell({ fs: this.fs, cwd: this.cwd, now: this.now });
    s.vars = JSON.parse(JSON.stringify(this.vars));
    s._exports = JSON.parse(JSON.stringify(this._exports));
    s.positional = this.positional.slice();
    s.funcs = this.funcs; s.aliases = this.aliases; s.lastCode = this.lastCode;
    s._dtctx = this._dtctx; s.onCommand = this.onCommand;
    s._out = ""; s._err = "";
    return s;
  };

  Shell.prototype.runString = function (src) {
    var ast;
    try { ast = new Parser(tokenize(String(src))).parse(); }
    catch (e) { this._stdout = ""; this._stderr = "syntax error: " + (e.message || e) + "\n"; return 2; }
    this._out = ""; this._err = "";
    var code;
    try { code = this.execList(ast); }
    catch (e) {
      if (e instanceof ExitSignal) { code = e.code; }
      else if (e instanceof ReturnSignal) { code = e.code; }
      else { this._err += "error: " + (e && e.message ? e.message : String(e)) + "\n"; code = 1; }
    }
    this.lastCode = code;
    this._stdout = this._out; this._stderr = this._err;
    return code;
  };
  Shell.prototype.sourceFile = function (path) {
    var n = this.fs.get(this.fs.norm(this.cwd, path));
    if (!n || n.t !== "f") return { err: "source: " + path + ": No such file\n", code: 1 };
    return { out: this.capture(n.d), code: 0 };
  };

  /* --- execution --- */
  Shell.prototype.execList = function (list, io) {
    var code = this.lastCode;
    for (var i = 0; i < list.items.length; i++) {
      var it = list.items[i];
      code = this.execAndOr(it.andor, io);
      if (this.errexit && code !== 0) throw new ExitSignal(code);
    }
    return code;
  };
  Shell.prototype.execAndOr = function (ao, io) {
    var code = 0;
    for (var i = 0; i < ao.pipes.length; i++) {
      if (i > 0) { var op = ao.ops[i - 1]; if (op === "&&" && code !== 0) continue; if (op === "||" && code === 0) continue; }
      code = this.execPipe(ao.pipes[i], io);
    }
    return code;
  };
  Shell.prototype.execPipe = function (pipe, io) {
    var input = (io && io.stdin) ? io.stdin : mkstdin("");
    var code = 0, last = pipe.cmds.length - 1;
    for (var i = 0; i <= last; i++) {
      if (i < last) {
        var sub = this.fork(); sub._out = ""; sub._err = "";
        var rc = sub.execCommand(pipe.cmds[i], { stdin: input });
        input = mkstdin(sub._out + (rc.out || ""));
        if (sub._err) this._err += sub._err;
        code = rc.code == null ? 0 : rc.code;
      } else {
        var r = this.execCommand(pipe.cmds[i], { stdin: input });
        this._out += r.out || "";
        if (r.err) this._err += r.err;
        code = r.code == null ? 0 : r.code;
      }
    }
    if (pipe.bang) code = code === 0 ? 1 : 0;
    return code;
  };
  Shell.prototype.execCommand = function (node, io) {
    io = io || { stdin: mkstdin("") };
    if (!node) return { out: "", err: "", code: 0 };

    if (node.type === "list") { return { out: "", code: this.execList(node, io) }; }
    if (node.type === "andor") { return { out: "", code: this.execAndOr(node, io) }; }
    if (node.type === "pipe") { return { out: "", code: this.execPipe(node, io) }; }
    if (node.type === "group") { return { out: "", code: this.execList(node.body, io) }; }
    if (node.type === "subshell") { var sub = this.fork(); return { out: "", code: sub.execList(node.body, io) }; }
    if (node.type === "func") { this.funcs[node.name] = node.body; return { out: "", code: 0 }; }

    if (node.type === "if") {
      if (this.execList(node.cond, io) === 0) return { out: "", code: this.execList(node.body, io) };
      for (var e = 0; e < node.elifs.length; e++) if (this.execList(node.elifs[e].c, io) === 0) return { out: "", code: this.execList(node.elifs[e].b, io) };
      if (node.els) return { out: "", code: this.execList(node.els, io) };
      return { out: "", code: 0 };
    }
    if (node.type === "while") {
      var code = 0, guard = 0;
      this.loopDepth++;
      try {
        while (guard++ < 100000) {
          var c = this.execList(node.cond, io);
          var ok = node.until ? (c !== 0) : (c === 0);
          if (!ok) break;
          try { code = this.execList(node.body, io); }
          catch (e2) { if (e2 instanceof BreakSignal) { if (e2.n > 1) { e2.n--; throw e2; } break; } if (e2 instanceof ContinueSignal) { if (e2.n > 1) { e2.n--; throw e2; } continue; } throw e2; }
        }
      } finally { this.loopDepth--; }
      return { out: "", code: code };
    }
    if (node.type === "for") {
      var items = node.words ? this.expandWords(node.words) : this.positional.slice();
      var c2 = 0; this.loopDepth++;
      try {
        for (var w = 0; w < items.length; w++) {
          this.setVar(node.name, items[w]);
          try { c2 = this.execList(node.body, io); }
          catch (e3) { if (e3 instanceof BreakSignal) { if (e3.n > 1) { e3.n--; throw e3; } break; } if (e3 instanceof ContinueSignal) { if (e3.n > 1) { e3.n--; throw e3; } continue; } throw e3; }
        }
      } finally { this.loopDepth--; }
      return { out: "", code: c2 };
    }
    if (node.type === "case") {
      var val = this.expandWords([node.word])[0] || "";
      for (var a = 0; a < node.arms.length; a++) {
        var arm = node.arms[a];
        var matched = arm.pats.some(function (p) { return globMatch(p.replace(/"/g, ""), val); });
        if (matched) return { out: "", code: this.execList(arm.body, io) };
      }
      return { out: "", code: 0 };
    }

    if (node.type === "simple") return this.execSimple(node, io);
    return { out: "", err: "", code: 0 };
  };

  function braceExpand(w) {
    // find first top-level { , ... } with a comma or range; expand recursively
    var depth = 0, start = -1, i;
    for (i = 0; i < w.length; i++) {
      var c = w[i];
      if (c === "\\") { i++; continue; }
      if (c === "'" || c === '"') { var q = c; i++; while (i < w.length && w[i] !== q) { if (w[i] === "\\") i++; i++; } continue; }
      if (c === "{") { if (depth === 0) start = i; depth++; }
      else if (c === "}") { depth--; if (depth === 0 && start >= 0) {
        var inner = w.slice(start + 1, i);
        var rm = /^(-?\d+)\.\.(-?\d+)(?:\.\.(-?\d+))?$/.exec(inner);
        if (rm) {
          var a0 = parseInt(rm[1], 10), a1 = parseInt(rm[2], 10), st = rm[3] ? Math.abs(parseInt(rm[3], 10)) : 1;
          if (a1 < a0) st = -st;
          var rr = [];
          for (var v = a0; st > 0 ? v <= a1 : v >= a1; v += st) rr.push(w.slice(0, start) + v + w.slice(i + 1));
          return rr;
        }
        var alts = splitTop(inner, ",");
        if (alts.length > 1) {
          var res = [];
          alts.forEach(function (a) { braceExpand(w.slice(0, start) + a + w.slice(i + 1)).forEach(function (x) { res.push(x); }); });
          return res;
        }
        start = -1;
      } }
    }
    return [w];
  }
  function splitTop(s, sep) {
    var out = [], depth = 0, cur = "";
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (c === "{") depth++;
      else if (c === "}") depth--;
      if (c === sep && depth === 0) { out.push(cur); cur = ""; }
      else cur += c;
    }
    out.push(cur);
    return out;
  }

  Shell.prototype.expandWords = function (words) {
    var out = [], self = this;
    words.forEach(function (w) {
      braceExpand(w).forEach(function (bw) { out = out.concat(expandWord(self, bw, {})); });
    });
    return out;
  };

  Shell.prototype.execSimple = function (node, io) {
    var self = this;
    // redirections
    var stdin = (io && io.stdin) ? io.stdin : mkstdin(""), outFile = null, outAppend = false, errFile = null, errAppend = false, bothFile = null, bothAppend = false;
    var heredoc = null;
    for (var r = 0; r < node.redirs.length; r++) {
      var rd = node.redirs[r];
      var tgt = this.expandWords([rd.target])[0] || "";
      if (rd.op === "heredoc") heredoc = rd.target;
      else if (rd.op === "<" || rd.op === "<<<") stdin = mkstdin(rd.op === "<<<" ? (this.expandWords([rd.target])[0] || "") + "\n" : this.readIn(tgt));
      else if (rd.fd === 2 && rd.op === ">") { errFile = this.fs.norm(this.cwd, tgt); errAppend = false; }
      else if (rd.fd === 2 && rd.op === ">>") { errFile = this.fs.norm(this.cwd, tgt); errAppend = true; }
      else if (rd.op === "&>") { bothFile = this.fs.norm(this.cwd, tgt); }
      else if (rd.op === ">") { outFile = this.fs.norm(this.cwd, tgt); outAppend = false; }
      else if (rd.op === ">>") { outFile = this.fs.norm(this.cwd, tgt); outAppend = true; }
    }
    if (heredoc != null) { stdin = mkstdin(""); }

    // assignments
    var assigns = node.assigns;
    var words = node.words.slice();

    // alias expansion on first word
    if (words.length && this.aliases[words[0]]) {
      var al = this.aliases[words[0]].split(/\s+/);
      words = al.concat(words.slice(1));
    }

    // function / builtin with no command name
    if (!words.length) {
      assigns.forEach(function (a) { self.setVar(a.name, self.expandWords([a.val]).join(" ") || expandWord(self, a.val, {}).join(" ")); });
      return { out: "", err: "", code: 0 };
    }

    // expand args
    var argv = this.expandWords(words);
    var cmd = argv.shift();

    // if command name is a var assignment-only line, handled above
    if (!cmd) return { out: "", err: "", code: 0 };

    if (this.onCommand) { try { this.onCommand(cmd, argv.slice()); } catch (e) { /* observer must never break a command */ } }

    var res;
    if (this.funcs[cmd]) {
      var saved = { positional: this.positional, vars: null };
      var sub = this.fork();
      sub.positional = argv.slice();
      this.funcDepth++;
      try { var rc = sub.execCommand(this.funcs[cmd], { stdin: stdin }); res = { out: sub._out, err: sub._err, code: rc.code }; }
      catch (e) { if (e instanceof ReturnSignal) res = { out: sub._out, err: sub._err, code: e.code }; else throw e; }
      finally { this.funcDepth--; }
      res = { out: res.out || "", err: res.err || "", code: res.code };
    } else if (CMDS[cmd]) {
      // temporary env for assignments preceding command
      var tmpVars = {};
      assigns.forEach(function (a) { tmpVars[a.name] = self.expandWords([a.val]).join(" "); });
      var savedVars = {};
      Object.keys(tmpVars).forEach(function (k) { savedVars[k] = self.vars[k]; self.vars[k] = tmpVars[k]; });
      try { res = CMDS[cmd](this, argv, { stdin: stdin }) || { code: 0 }; }
      finally { Object.keys(tmpVars).forEach(function (k) { if (savedVars[k] === undefined) delete self.vars[k]; else self.vars[k] = savedVars[k]; }); }
    } else {
      res = { err: cmd + ": command not found\n", code: 127 };
    }

    res = res || { code: 0 };
    var out = res.out || "", errOut = res.err || "";

    // apply redirections
    if (bothFile) { this.writeOut(bothFile, out + errOut, false); out = ""; errOut = ""; }
    if (outFile) { this.writeOut(outFile, out, outAppend); out = ""; }
    if (errFile) { this.writeOut(errFile, errOut, errAppend); errOut = ""; }

    return { out: out, err: errOut, code: res.code == null ? 0 : res.code };
  };

  Shell.prototype.writeOut = function (abs, data, append) {
    if (append) { var n = this.fs.get(abs); this.fs.writeFile(abs, (n && n.t === "f" ? n.d : "") + data); }
    else this.fs.writeFile(abs, data);
  };
  Shell.prototype.readIn = function (abs) { var n = this.fs.get(abs); return n && n.t === "f" ? n.d : ""; };

  /* ================= session facade ================= */
  function createSession(opts) {
    opts = opts || {};
    var sh = new Shell(opts);
    seedFS(sh, opts);
    return {
      shell: sh,
      fs: sh.fs,
      get cwd() { return sh.cwd; },
      set now(v) { sh.now = v; },
      exec: function (line) {
        sh._out = ""; sh._err = "";
        var code = sh.runString(line);
        return { out: sh._stdout || "", err: sh._stderr || "", code: code, cwd: sh.cwd };
      },
      getVar: function (k) { return sh.getVar(k); },
      setVar: function (k, v) { sh.setVar(k, v); },
      history: function () { return sh.history.slice(); }
    };
  }

  function seedFS(sh, opts) {
    var fs = sh.fs;
    if (opts.empty) return;
    ["/bin", "/usr/bin", "/home/inscriber", "/tmp", "/sdcard", "/sdcard/Darkith"].forEach(function (d) { fs.mkdirp(d); });
    fs.writeFile("/home/inscriber/README.txt",
      "Darkith Inscriber — a real shell in a single HTML file.\n" +
      "Try: ls, echo hi, for i in 1 2 3; do echo $i; done, ls | sort | head\n");
    fs.writeFile("/home/inscriber/notes.txt",
      "alpha\nbeta\ngamma\nalpha\nbeta\n");
    fs.writeFile("/home/inscriber/numbers.txt", "5\n3\n9\n1\n7\n");
    fs.writeFile("/home/inscriber/script.sh",
      "#!/bin/sh\nfor f in *.txt; do\n  echo \"== $f ==\"\n  wc -l \"$f\"\ndone\n");
  }

  var API = { version: VERSION, Shell: Shell, VFS: VFS, createSession: createSession, tokenize: tokenize, Parser: Parser, arith: arith, globMatch: globMatch,
    CMDS: CMDS, registerCommand: function (name, fn) { CMDS[name] = fn; } };
  if (typeof window !== "undefined") window.DarkTerm = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof window !== "undefined" ? window : this);
