/*!
 * DropaCode — Insights section
 * Paste-once embed. Layout lives here; the writing lives in insights.json.
 *
 * Deliberately a different shape from the Technology & Trends card grid:
 * Three columns, one tight paragraph each, rule above rather than a boxed card -
 * enough separation from the Technology & Trends grid to not read as a repeat.
 */
(function () {
  "use strict";

  var CONFIG = {
    accent: "#4F46E5",
    feed: "insights.json",
    theme: "auto",
    mountId: "dropacode-insights-section"
  };

  var scriptEl = document.currentScript;

  function getMount() {
    var el = document.getElementById(CONFIG.mountId);
    if (el) return el;
    el = document.createElement("div");
    el.id = CONFIG.mountId;
    if (scriptEl && scriptEl.parentNode) scriptEl.parentNode.insertBefore(el, scriptEl);
    else document.body.appendChild(el);
    return el;
  }

  /* ------------------------------------------------- host style sniffing */

  function luminance(rgb) {
    var m = /rgba?\((\d+)[,\s]+(\d+)[,\s]+(\d+)/.exec(rgb || "");
    if (!m) return null;
    return (0.2126 * +m[1] + 0.7152 * +m[2] + 0.0722 * +m[3]) / 255;
  }

  function detectTheme(host) {
    var declared = host.getAttribute("data-theme");
    if (declared === "light" || declared === "dark") return declared;
    var node = host;
    while (node && node !== document.documentElement) {
      var bg = getComputedStyle(node).backgroundColor;
      if (bg && bg !== "transparent" && !/rgba\(0,\s*0,\s*0,\s*0\)/.test(bg)) {
        var l = luminance(bg);
        if (l !== null) return l < 0.5 ? "dark" : "light";
      }
      node = node.parentElement;
    }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function hostFont(host) {
    var f = getComputedStyle(host).fontFamily;
    return f || "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
  }

  /* -------------------------------------------------------------- styles */

  var PALETTE = {
    light: { text: "#0E1726", muted: "#4A5568", faint: "#8B93A5", line: "#E3E8F0", rule: "#EDF1F7" },
    dark:  { text: "#F2F5FA", muted: "#AEB8C7", faint: "#7C8698", line: "#28313F", rule: "#1E2733" }
  };

  function styles(theme, font) {
    var c = PALETTE[theme];
    var a = CONFIG.accent;
    return [
      ":host{all:initial;display:block;}",
      "*,*::before,*::after{box-sizing:border-box;}",
      ".wrap{font-family:" + font + ";color:" + c.text + ";max-width:1160px;margin:0 auto;",
      "padding:64px 24px;line-height:1.6;-webkit-font-smoothing:antialiased;}",
      ".eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;font-weight:700;",
      "color:" + a + ";margin:0 0 12px;}",
      ".head{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:12px;}",
      "h2.title{font-size:clamp(26px,3.2vw,38px);line-height:1.18;font-weight:700;margin:0;letter-spacing:-.02em;}",
      ".stamp{font-size:13px;color:" + c.faint + ";white-space:nowrap;}",
      ".standfirst{font-size:16.5px;color:" + c.muted + ";margin:14px 0 0;max-width:68ch;}",
      ".grid{display:grid;gap:22px;margin-top:34px;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));",
      "align-items:stretch;}",
      "article{display:flex;flex-direction:column;border-top:3px solid " + a + ";",
      "padding:20px 0 0;min-width:0;}",
      ".meta{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;}",
      ".tag{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:" + a + ";",
      "background:" + a + "14;border:1px solid " + a + "2e;border-radius:999px;padding:4px 10px;}",
      ".when{font-size:12.5px;color:" + c.faint + ";}",
      "h3{font-size:19px;line-height:1.3;font-weight:700;margin:0 0 12px;letter-spacing:-.01em;}",
      "p.body{font-size:15px;color:" + c.muted + ";margin:0 0 18px;}",
      "a.src{margin-top:auto;padding-top:14px;border-top:1px solid " + c.rule + ";",
      "font-size:13px;font-weight:600;color:" + a + ";text-decoration:none;",
      "display:inline-flex;align-items:center;gap:6px;}",
      "a.src:hover{text-decoration:underline;}",
      "a.src:focus-visible{outline:2px solid " + a + ";outline-offset:3px;border-radius:4px;}",
      "a.src svg{width:11px;height:11px;flex:none;}",
      "@media (max-width:640px){.wrap{padding:44px 18px;}.grid{gap:28px;}}"
    ].join("");
  }

  /* ------------------------------------------------------------- render */

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function safeUrl(u) { return /^https?:\/\//i.test(u || "") ? u : "#"; }

  function fmtDate(iso) {
    var d = new Date(iso);
    return isNaN(d) ? "" : d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  }

  var ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 17L17 7M9 7h8v8"/></svg>';

  function render(host, data) {
    var theme = detectTheme(host);
    host.__dacTheme = theme;
    var root = host.shadowRoot || host.attachShadow({ mode: "open" });

    var entries = (data.items || []).map(function (it) {
      return '<article>' +
        '<div class="meta">' +
        (it.tag ? '<span class="tag">' + esc(it.tag) + "</span>" : "") +
        (it.date ? '<span class="when">' + esc(fmtDate(it.date)) + "</span>" : "") +
        "</div>" +
        "<h3>" + esc(it.title) + "</h3>" +
        (it.body || []).map(function (p) { return '<p class="body">' + esc(p) + "</p>"; }).join("") +
        (it.url ? '<a class="src" href="' + esc(safeUrl(it.url)) + '" target="_blank" rel="noopener noreferrer">' +
          esc(it.source || "Source") + ARROW + "</a>" : "") +
        "</article>";
    }).join("");

    root.innerHTML =
      "<style>" + styles(theme, hostFont(host)) + "</style>" +
      '<section class="wrap" aria-labelledby="dac-ins-h">' +
      '<p class="eyebrow">' + esc(data.eyebrow || "Insights") + "</p>" +
      '<div class="head"><h2 class="title" id="dac-ins-h">' + esc(data.heading || "Insights") + "</h2>" +
      (data.updated ? '<span class="stamp">Updated ' + esc(fmtDate(data.updated)) + "</span>" : "") +
      "</div>" +
      (data.standfirst ? '<p class="standfirst">' + esc(data.standfirst) + "</p>" : "") +
      '<div class="grid">' + entries + "</div></section>";
  }

  /* ---------------------------------------------------------------- boot */

  function feedUrl() {
    var base = (scriptEl && scriptEl.src) || document.baseURI;
    var url;
    try { url = new URL(CONFIG.feed, base).href; } catch (e) { url = CONFIG.feed; }
    return url + (url.indexOf("?") > -1 ? "&" : "?") + "t=" + Math.floor(Date.now() / 60000);
  }

  function boot() {
    var host = getMount();
    fetch(feedUrl(), { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error("feed " + r.status); return r.json(); })
      .then(function (data) {
        if (!data || !data.items || !data.items.length) throw new Error("empty feed");
        render(host, data);
        var recheck = function () { if (detectTheme(host) !== host.__dacTheme) render(host, data); };
        setTimeout(recheck, 500);
        window.addEventListener("load", function () { setTimeout(recheck, 300); });
      })
      .catch(function (err) {
        host.style.display = "none";
        if (window.console) console.warn("[DropaCode insights]", err.message);
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
