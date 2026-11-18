/* =====================================================================
   DARKITH Forge — integrated client-coupling update watcher.

   ONE source of truth for "is my installed copy stale against the live
   remote circuit tree?". Three consumers read this file:
     1. the fused webapp (`darkith forge.html`) — injected at build time
     2. the host APK surface (app/src/main/assets/homekeeper.html)
     3. tools/updater_test.mjs — drives decide()/parse()/cmp() with real
        inputs so the alerting logic cannot silently rot.

   It is DUAL-TRACK and never lies:
     * REMOTE track — compares the installed versionCode against the live
       VERSION.json manifest. Offline is a first-class state ("unknown"),
       not a failure: a phone in aeroplane mode still shows its own version.
     * LOCAL track — the T-1 stale self-report: the copy you are running is
       compared against the newest version stamped in the tree at build
       time. This is what answers "am I running last session's wrap-up?".

   Design laws (fracture closures):
     * offline -> "unknown", never a false "up to date";
     * the alert fires ONCE per new version, never on every poll;
     * the dialog is the app's own UI.dialog when present, else a native
       alert — so it works on every host, including a bare browser tab;
     * no network call is ever made unless check()/watch() asks for it.
   ===================================================================== */
(function (global) {
  "use strict";

  /* The build replaces this object literal with the repo's VERSION.json at
     the moment of fusion, so the page carries its OWN version, offline. */
  var LOCAL = {"versionCode":3,"versionName":"1.2.0-omega","surfaceVersion":"v5.3.1"};

  var DEFAULT_MANIFEST_URL =
    "https://raw.githubusercontent.com/Deobfugazi/darkith-forge/main/VERSION.json";
  var DEFAULT_ONESHOT_URL =
    "https://github.com/Deobfugazi/darkith-forge/releases/latest/download/darkith-one-shot.sh";

  /* ---------- version algebra (pure; the harness exercises these) ---------- */

  /* versionCode is authoritative. If a manifest lacks it, derive a code from
     a dotted name: 1.2.0 -> 10200 (major*10000 + minor*100 + patch). */
  function codeOf(man) {
    if (!man) return null;
    if (typeof man.versionCode === "number" && isFinite(man.versionCode)) return man.versionCode;
    if (typeof man.versionCode === "string" && /^\d+$/.test(man.versionCode)) return parseInt(man.versionCode, 10);
    var name = String(man.versionName || man.surfaceVersion || "");
    var m = name.match(/(\d+)\.(\d+)(?:\.(\d+))?/);
    if (!m) return null;
    return parseInt(m[1], 10) * 10000 + parseInt(m[2], 10) * 100 + parseInt(m[3] || "0", 10);
  }

  function cmp(a, b) {
    var ca = codeOf(a), cb = codeOf(b);
    if (ca === null || cb === null) return null;
    if (ca < cb) return -1;
    if (ca > cb) return 1;
    return 0;
  }

  /* The whole decision, as a pure function of two manifests + reachability.
     Returns { state, title, message, local, remote, actionable }. */
  function decide(local, remote, reachable) {
    var L = local || LOCAL;
    var lcode = codeOf(L);
    var lname = String(L.versionName || L.surfaceVersion || "?");
    if (reachable === false || !remote) {
      return {
        state: "unknown", actionable: false,
        title: "Update check — offline",
        message: "Installed: " + lname + " (code " + lcode + ").\n" +
                 "The live remote could not be reached, so a newer sovereign " +
                 "upliftment can neither be confirmed nor denied.\n" +
                 "Run a one-shot build when online to compare.",
        local: L, remote: null
      };
    }
    var r = cmp(L, remote);
    if (r === null) {
      return {
        state: "unknown", actionable: false,
        title: "Update check — indeterminate",
        message: "Installed: " + lname + ". The remote manifest carries no " +
                 "comparable version. Nothing is claimed either way.",
        local: L, remote: remote
      };
    }
    if (r < 0) {
      var rname = String(remote.versionName || remote.surfaceVersion || "?");
      return {
        state: "update", actionable: true,
        title: "Sovereign upliftment available",
        message: "Installed: " + lname + " (code " + lcode + ")\n" +
                 "Remote:    " + rname + " (code " + codeOf(remote) + ")\n\n" +
                 "A newer build is live on the remote circuit tree" +
                 (remote.notes ? ":\n\n" + remote.notes : ".") + "\n\n" +
                 "Update with the one-shot:\n" + (remote.oneshot_url || DEFAULT_ONESHOT_URL),
        local: L, remote: remote
      };
    }
    return {
      state: "current", actionable: false,
      title: "Up to date",
      message: "Installed: " + lname + " (code " + lcode + ").\n" +
               "This is the newest sovereign upliftment on the remote.",
      local: L, remote: remote
    };
  }

  /* ---------- I/O (only reached when a check is actually asked for) ---------- */

  function fetchManifest(url, timeoutMs) {
    var g = global;
    if (typeof g.fetch !== "function") return Promise.resolve({ ok: false, reason: "no-fetch" });
    var ctrl = (typeof g.AbortController === "function") ? new g.AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, timeoutMs || 8000) : null;
    var opts = { cache: "no-store" };
    if (ctrl) opts.signal = ctrl.signal;
    return g.fetch(url, opts).then(function (res) {
      if (timer) clearTimeout(timer);
      if (!res || !res.ok) return { ok: false, reason: "http-" + (res && res.status) };
      return res.json().then(function (j) { return { ok: true, manifest: j }; });
    }).catch(function (e) {
      if (timer) clearTimeout(timer);
      return { ok: false, reason: "error:" + (e && e.name ? e.name : e) };
    });
  }

  /* The installed APK's real version, read from the package manager through
     the bridge — never guessed. Falls back to the page's own LOCAL stamp. */
  function probeLocal() {
    var b = global.darkith || global.HomekeeperBridge || null;
    try {
      if (b && typeof b.apkVersion === "function") {
        var s = String(b.apkVersion());            // "bridge=hk-bridge-52 pkg=1.2.0-omega (3)"
        var m = s.match(/pkg=([^\s(]+)\s*\((\d+)\)/);
        if (m) return { versionName: m[1], versionCode: parseInt(m[2], 10), source: "apk" };
      }
    } catch (e) { /* bridge absent or threw: fall through to the stamp */ }
    var L = { versionName: LOCAL.versionName, versionCode: LOCAL.versionCode, surfaceVersion: LOCAL.surfaceVersion, source: "embedded" };
    return L;
  }

  /* ---------- presentation (host-agnostic) ---------- */

  function present(title, message) {
    var g = global;
    try {
      if (g.UI && typeof g.UI.dialog === "function") {
        return g.UI.dialog({ title: title, msg: message, cancel: false, ok: "OK" });
      }
    } catch (e) { /* fall through */ }
    try { if (typeof g.alert === "function") { g.alert(title + "\n\n" + message); return; } } catch (e2) {}
    try { if (typeof g.console !== "undefined" && g.console.log) g.console.log("[" + title + "]\n" + message); } catch (e3) {}
  }

  /* ---------- the watcher ---------- */

  var lastAlertedCode = null;   /* the alert fires once per new remote code */
  var lastDecision = null;

  function check(opts) {
    opts = opts || {};
    var url = opts.url || DEFAULT_MANIFEST_URL;
    var local = probeLocal();
    return fetchManifest(url, opts.timeoutMs).then(function (r) {
      var d = decide(local, r.ok ? r.manifest : null, r.ok);
      lastDecision = d;
      if (d.state === "update" && opts.alert !== false) {
        var rcode = codeOf(r.manifest);
        if (lastAlertedCode !== rcode) { lastAlertedCode = rcode; present(d.title, d.message); }
      }
      if (d.state === "unknown" && opts.alert === "always") present(d.title, d.message);
      render(d);
      return d;
    });
  }

  function watch(intervalMs) {
    check({ alert: true });
    var id = setInterval(function () { check({ alert: true }); }, intervalMs || 6 * 3600 * 1000);
    return id;
  }

  /* ---------- footer mount ---------- */

  var el = null;
  function label(d) {
    if (!d) return "Ω checking…";
    var v = (d.local && d.local.versionName) || LOCAL.versionName;
    if (d.state === "update") return "Ω upliftment " + (d.remote && d.remote.versionName) + " available";
    if (d.state === "unknown") return "Ω v" + v + " · offline";
    return "Ω v" + v + " · current";
  }
  function render(d) {
    if (!el) return;
    el.textContent = label(d);
    el.setAttribute("data-state", d ? d.state : "checking");
    el.style.color = d && d.state === "update" ? "#ffcf5c" : (d && d.state === "unknown" ? "#c9a24a" : "#9adf9a");
  }
  function mount(container) {
    var g = global;
    if (!g.document) return null;
    if (el && el.parentNode) return el;
    el = g.document.getElementById("dku-watch");
    if (!el) {
      el = g.document.createElement("span");
      el.id = "dku-watch";
      el.title = "DARKITH update watcher — tap to check";
      el.style.cssText =
        "position:fixed;left:6px;bottom:6px;z-index:2147483647;font:11px/1.2 ui-monospace,monospace;" +
        "color:#9adf9a;background:rgba(5,5,5,.82);border:1px solid rgba(232,194,104,.35);" +
        "border-radius:6px;padding:3px 7px;cursor:pointer;user-select:none";
      el.addEventListener("click", function () { check({ alert: "always" }); });
      (container || g.document.body).appendChild(el);
    }
    render(lastDecision);
    return el;
  }

  global.__dkUpdate = {
    version: "1.0.0",
    LOCAL: LOCAL,
    manifestUrl: DEFAULT_MANIFEST_URL,
    oneshotUrl: DEFAULT_ONESHOT_URL,
    codeOf: codeOf,
    cmp: cmp,
    decide: decide,
    probeLocal: probeLocal,
    fetchManifest: fetchManifest,
    check: check,
    watch: watch,
    mount: mount,
    present: present,
    lastDecision: function () { return lastDecision; },
    _setEl: function (node) { el = node; }   /* test seam */
  };

  /* Auto-mount when a DOM is present; the app calls mount() explicitly if it
     wants the pill inside a specific container. */
  if (global.document) {
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", function () { mount(); });
    } else {
      mount();
    }
  }
})(typeof window !== "undefined" ? window : globalThis);
