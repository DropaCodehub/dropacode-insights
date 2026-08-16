/*!
 * DropaCode — Technology & Trends section
 * Paste-once embed. Rendering logic lives here; weekly content lives in content.json.
 *
 * Customisation: edit CONFIG below, commit, done. No change needed on the Readdy side.
 */
(function () {
  "use strict";

  var CONFIG = {
    // Brand accent used for the eyebrow, links and card hairlines.
    accent: "#4F46E5",
    // Where the weekly content lives, relative to this script's own URL.
    feed: "content.json",
    // "auto" reads the host page background and picks light/dark to match.
    // Force with data-theme="light" | "dark" on the mount element.
    theme: "auto",
    heading: "Technology & Trends",
    eyebrow: "Weekly briefing",
    mountId: "dropacode-insights"
  };

  var scriptEl = document.currentScript;

  /* ------------------------------------------------------------------ mount */

  function getMount() {
    var el = document.getElementById(CONFIG.mountId);
    if (el) return el;
    // No mount div on the page: create one where the script tag sits.
    el = document.createElement("div");
    el.id = CONFIG.mountId;
    if (scriptEl && scriptEl.parentNode) {
      scriptEl.parentNode.insertBefore(el, scriptEl);
    } else {
      document.body.appendChild(el);
    }
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
    if (CONFIG.theme === "light" || CONFIG.theme === "dark") return CONFIG.theme;
    var node = host;
    while (node && node !== document.documentElement) {
      var bg = getComputedStyle(node).backgroundColor;
      if (bg && bg !== "transparent" && !/rgba\(0,\s*0,\s*0,\s*0\)/.test(bg)) {
        var l = luminance(bg);
        if (l !== null) return l < 0.5 ? "dark" : "light";
      }
      node = node.parentElement;
    }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function hostFont(host) {
    var f = getComputedStyle(host).fontFamily;
    return f && f !== "" ? f : "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
  }

  /* -------------------------------------------------------------- styling */

  var PALETTE = {
    light: {
      text: "#0E1726", muted: "#5A6478", faint: "#8B93A5",
      surface: "#FFFFFF", inset: "#F6F8FB", line: "#E3E8F0", leadBg: "#F6F8FB"
    },
    dark: {
      text: "#F2F5FA", muted: "#A6B0C2", faint: "#7C8698",
      surface: "#141A24", inset: "#1A222E", line: "#28313F", leadBg: "#1A222E"
    }
  };

  function styles(theme, font) {
    var c = PALETTE[theme];
    return [
      ":host{all:initial;display:block;}",
      "*,*::before,*::after{box-sizing:border-box;}",
      ".wrap{font-family:" + font + ";color:" + c.text + ";",
      "max-width:1160px;margin:0 auto;padding:64px 24px;line-height:1.6;",
      "-webkit-font-smoothing:antialiased;}",
      ".eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:12px;",
      "letter-spacing:.14em;text-transform:uppercase;font-weight:700;color:" + CONFIG.accent + ";margin:0 0 12px;}",
      ".eyebrow .dot{width:6px;height:6px;border-radius:50%;background:" + CONFIG.accent + ";",
      "box-shadow:0 0 0 0 " + CONFIG.accent + "66;animation:pulse 2.6s ease-out infinite;}",
      "@keyframes pulse{0%{box-shadow:0 0 0 0 " + CONFIG.accent + "66}70%{box-shadow:0 0 0 7px " + CONFIG.accent + "00}100%{box-shadow:0 0 0 0 " + CONFIG.accent + "00}}",
      "@media (prefers-reduced-motion:reduce){.eyebrow .dot{animation:none}}",
      ".head{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:28px;}",
      "h2.title{font-size:clamp(26px,3.2vw,38px);line-height:1.2;font-weight:700;margin:0;letter-spacing:-.02em;}",
      ".stamp{font-size:13px;color:" + c.faint + ";white-space:nowrap;}",
      ".lead{background:" + c.leadBg + ";border:1px solid " + c.line + ";border-left:3px solid " + CONFIG.accent + ";",
      "border-radius:14px;padding:26px 28px;margin:0 0 28px;}",
      ".lead h3{font-size:19px;font-weight:700;margin:0 0 10px;letter-spacing:-.01em;}",
      ".lead p{margin:0 0 12px;font-size:15.5px;color:" + c.muted + ";}",
      ".lead p:last-child{margin-bottom:0;}",
      ".grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(258px,1fr));}",
      ".card{background:" + c.surface + ";border:1px solid " + c.line + ";border-radius:14px;padding:22px;",
      "display:flex;flex-direction:column;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;}",
      ".card:hover{transform:translateY(-2px);border-color:" + CONFIG.accent + "55;box-shadow:0 8px 26px " + (theme === "dark" ? "rgba(0,0,0,.38)" : "rgba(16,24,40,.07)") + ";}",
      "@media (prefers-reduced-motion:reduce){.card,.card:hover{transition:none;transform:none}}",
      ".tag{align-self:flex-start;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;",
      "color:" + CONFIG.accent + ";background:" + CONFIG.accent + "14;border:1px solid " + CONFIG.accent + "2e;",
      "border-radius:999px;padding:4px 10px;margin-bottom:14px;}",
      ".card h3{font-size:16.5px;line-height:1.35;font-weight:700;margin:0 0 10px;letter-spacing:-.01em;}",
      ".card p{font-size:14.5px;color:" + c.muted + ";margin:0 0 16px;}",
      ".meta{margin-top:auto;display:flex;align-items:center;justify-content:space-between;gap:10px;",
      "padding-top:14px;border-top:1px solid " + c.line + ";font-size:12.5px;color:" + c.faint + ";}",
      "a.src{color:" + CONFIG.accent + ";text-decoration:none;font-weight:600;display:inline-flex;align-items:center;gap:5px;}",
      "a.src:hover{text-decoration:underline;}",
      "a.src:focus-visible,.card:focus-within{outline:2px solid " + CONFIG.accent + ";outline-offset:3px;border-radius:4px;}",
      "a.src svg{width:11px;height:11px;flex:none;}",
      "@media (max-width:640px){.wrap{padding:44px 18px;}.lead{padding:20px;}}"
    ].join("");
  }

  /* ------------------------------------------------------------- rendering */

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function safeUrl(u) {
    return /^https?:\/\//i.test(u || "") ? u : "#";
  }

  function fmtDate(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return "";
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  }

  var ARROW =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M7 17L17 7M9 7h8v8"/></svg>';

  function render(host, data) {
    var theme = detectTheme(host);
    host.__dacTheme = theme;
    var font = hostFont(host);
    var root = host.shadowRoot || host.attachShadow({ mode: "open" });

    var cards = (data.items || [])
      .map(function (it) {
        return (
          '<article class="card">' +
          (it.tag ? '<span class="tag">' + esc(it.tag) + "</span>" : "") +
          "<h3>" + esc(it.headline) + "</h3>" +
          "<p>" + esc(it.summary) + "</p>" +
          '<div class="meta"><span>' + esc(it.source || "") + "</span>" +
          '<a class="src" href="' + esc(safeUrl(it.url)) + '" target="_blank" rel="noopener noreferrer">' +
          "Read" + ARROW + "</a></div></article>"
        );
      })
      .join("");

    var lead = data.lead
      ? '<div class="lead"><h3>' + esc(data.lead.title) + "</h3>" +
        (data.lead.body || []).map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("") +
        "</div>"
      : "";

    root.innerHTML =
      "<style>" + styles(theme, font) + "</style>" +
      '<section class="wrap" aria-labelledby="dac-h">' +
      '<p class="eyebrow"><span class="dot"></span>' + esc(data.eyebrow || CONFIG.eyebrow) + "</p>" +
      '<div class="head"><h2 class="title" id="dac-h">' + esc(data.heading || CONFIG.heading) + "</h2>" +
      (data.updated ? '<span class="stamp">Updated ' + esc(fmtDate(data.updated)) + "</span>" : "") +
      "</div>" + lead +
      '<div class="grid">' + cards + "</div></section>";
  }

  /* ---------------------------------------------------------------- boot */

  function feedUrl() {
    var base = (scriptEl && scriptEl.src) || "";
    var url;
    try {
      url = new URL(CONFIG.feed, base || document.baseURI).href;
    } catch (e) {
      url = CONFIG.feed;
    }
    // Minute-granularity cache-bust so a Monday update goes live immediately.
    return url + (url.indexOf("?") > -1 ? "&" : "?") + "t=" + Math.floor(Date.now() / 60000);
  }

  function boot() {
    var host = getMount();
    fetch(feedUrl(), { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error("feed " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.items || !data.items.length) throw new Error("empty feed");
        render(host, data);
        // Host backgrounds can still be settling (web fonts, CSS transitions,
        // lazy theme classes). Re-check once things have quiesced and repaint
        // only if the detected theme actually changed.
        var recheck = function () {
          if (detectTheme(host) !== host.__dacTheme) render(host, data);
        };
        setTimeout(recheck, 500);
        window.addEventListener("load", function () { setTimeout(recheck, 300); });
      })
      .catch(function (err) {
        // Fail quiet: collapse the section rather than show a broken block.
        host.style.display = "none";
        if (window.console) console.warn("[DropaCode insights]", err.message);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
