// Google AdSense slots.
//
// This file is NOT in any page's <script> tags. cookie-consent.js injects it only
// after a visitor accepts cookies, so nothing from Google loads before consent.
//
// To add an ad space:
//   1. Create the ad unit in AdSense and add an entry to SLOTS below.
//   2. Drop <div class="ur-ad" data-ur-ad="<name>"></div> where it should appear.
// The "Advertisement" caption, the <ins> block and the push() call are generated
// here. Slots stay hidden (see .ur-ad in extra.css) until consent is given and
// are hidden again if AdSense leaves them unfilled. Add data-no-ads to <body>
// to keep a page ad-free.
(function () {
  "use strict";

  var CLIENT = "ca-pub-6476203131932676";

  // name -> ad unit. Optional keys: format, layout, responsive (default true), style.
  var SLOTS = {
    "top-banner": { slot: "7589982801", format: "auto" },
    "article-banner": { slot: "1982220876", format: "auto" },
    sidebar: { slot: "2743804051", format: "auto" },
    "in-article": {
      slot: "1239150696",
      format: "fluid",
      layout: "in-article",
      responsive: false,
      style: "display:block;text-align:center;",
    },
    footer: { slot: "6468260798", format: "auto" },
  };

  function loadLibrary() {
    if (window.__urAdsLibLoaded) return;
    window.__urAdsLibLoaded = true;
    var s = document.createElement("script");
    s.async = true;
    s.crossOrigin = "anonymous";
    s.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=" + CLIENT;
    document.head.appendChild(s);
  }

  function fillSlot(el) {
    if (el.getAttribute("data-ur-ad-done")) return;
    var cfg = SLOTS[el.getAttribute("data-ur-ad")];
    if (!cfg) return;
    el.setAttribute("data-ur-ad-done", "1");

    var label = document.createElement("small");
    label.className = "ur-ad-label";
    label.textContent = "Advertisement";

    var ins = document.createElement("ins");
    ins.className = "adsbygoogle";
    ins.style.cssText = cfg.style || "display:block";
    ins.setAttribute("data-ad-client", CLIENT);
    ins.setAttribute("data-ad-slot", cfg.slot);
    if (cfg.layout) ins.setAttribute("data-ad-layout", cfg.layout);
    ins.setAttribute("data-ad-format", cfg.format || "auto");
    if (cfg.responsive !== false) ins.setAttribute("data-full-width-responsive", "true");

    el.appendChild(label);
    el.appendChild(ins);

    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      /* ad blocker or library failure - leave the slot empty */
    }
  }

  function render() {
    document.documentElement.classList.add("ur-ads-on");
    var slots = document.querySelectorAll(".ur-ad[data-ur-ad]");
    for (var i = 0; i < slots.length; i++) fillSlot(slots[i]);
  }

  if (document.body.hasAttribute("data-no-ads")) return;

  loadLibrary();
  render();
  // The shared footer (with its slot) arrives after the page loads.
  document.addEventListener("partials:ready", render);
})();
