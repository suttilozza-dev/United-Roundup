(function () {
  "use strict";

  // Consent is collected by CookieYes (a Google-certified CMP). This file loads the CookieYes
  // banner, then loads each third-party tool only for the categories the visitor has accepted:
  //   analytics     -> GA4
  //   advertisement -> Google Ads tag, AdSense (assets/ads.js), embedded X posts
  //   functional    -> Kit checkout widget behind the "Support United Roundup" button
  // Nothing from Google or X is requested before the visitor has actively made a choice.
  var COOKIEYES_SRC = "https://cdn-cookieyes.com/client_data/fa25f16a8901fe6d829a765d049bd818/script.js";

  // TODO: replace with the real GA4 Measurement ID once created, e.g. "G-ABC1234XYZ".
  // Left as a placeholder on purpose -- loadGoogleTag() below refuses to configure GA4 while
  // this still looks like a placeholder, so nothing calls out to Google until a real
  // ID is dropped in here.
  var GA_MEASUREMENT_ID = "G-81QGG9136Z";

  // Google Ads tag. Loaded only after consent, together with GA4 (see loadGoogleTag).
  var ADS_TAG_ID = "AW-18489674283";

  // Kit checkout widget. It contacts Kit, Stripe and hCaptcha, so it loads only after consent.
  // Without it the "Support" link (a[data-commerce] in the nav) is a plain link to Kit's page.
  var KIT_COMMERCE_SRC = "https://unitedroundup.kit.com/commerce.js";

  // Links to the Kit newsletter landing page.
  var NEWSLETTER_LINK = 'a[href^="https://unitedroundup.kit.com/df3c9b9f5a"]';

  // Google Ads conversion action "Newsletter click" (a click through to the sign-up page).
  var NEWSLETTER_CONVERSION = "AW-18489674283/PsRJCMSquK0dEKuUyPBE";

  function isConfigured() {
    return typeof GA_MEASUREMENT_ID === "string" && GA_MEASUREMENT_ID.indexOf("XXXX") === -1;
  }

  // What the visitor has accepted. Everything is false until they have actively chosen
  // (CookieYes can pre-accept categories for some regions, which we do not rely on).
  function getChoice() {
    var choice = { analytics: false, advertisement: false, functional: false };
    try {
      var c = typeof window.getCkyConsent === "function" ? window.getCkyConsent() : null;
      if (c && c.isUserActionCompleted && c.categories) {
        choice.analytics = !!c.categories.analytics;
        choice.advertisement = !!c.categories.advertisement;
        choice.functional = !!c.categories.functional;
      }
    } catch (e) {
      /* CookieYes not ready: treat as no consent */
    }
    return choice;
  }

  // One gtag for GA4 and Google Ads. Defining it only queues data locally, it makes no
  // request. The default of "denied" is queued before CookieYes loads.
  function ensureGtag() {
    window.dataLayer = window.dataLayer || [];
    if (typeof window.gtag !== "function") {
      window.gtag = function () {
        window.dataLayer.push(arguments);
      };
    }
    if (!window.__urConsentDefaultSet) {
      window.__urConsentDefaultSet = true;
      window.gtag("consent", "default", {
        ad_storage: "denied",
        ad_user_data: "denied",
        ad_personalization: "denied",
        analytics_storage: "denied",
        wait_for_update: 500,
      });
    }
    return window.gtag;
  }

  // Consent Mode v2 signals, in step with the visitor's choice (also covers withdrawal).
  function updateConsentSignals(choice) {
    var ads = choice.advertisement ? "granted" : "denied";
    ensureGtag()("consent", "update", {
      ad_storage: ads,
      ad_user_data: ads,
      ad_personalization: ads,
      analytics_storage: choice.analytics ? "granted" : "denied",
    });
  }

  // Google tags (GA4 + Google Ads). One gtag.js request, made only once a category that
  // needs it has been accepted. Each tag is configured only for its own category.
  function loadGoogleTag(choice) {
    if (!choice.analytics && !choice.advertisement) return;
    var gtag = ensureGtag();

    if (!window.__urGtagLoaded) {
      window.__urGtagLoaded = true;
      gtag("js", new Date());
      var s = document.createElement("script");
      s.async = true;
      s.src = "https://www.googletagmanager.com/gtag/js?id=" + ADS_TAG_ID;
      document.head.appendChild(s);
    }
    if (choice.analytics && isConfigured() && !window.__urGaConfigured) {
      window.__urGaConfigured = true;
      gtag("config", GA_MEASUREMENT_ID);
    }
    if (choice.advertisement && !window.__urAdsConfigured) {
      window.__urAdsConfigured = true;
      gtag("config", ADS_TAG_ID);
    }
    trackNewsletterClicks();
  }

  // Kit landing page links (the sign-up buttons and the footer link). Delegated, so
  // links added later by the shared nav/footer partials are covered too. Registered
  // only after consent, so nothing is sent without it.
  function trackNewsletterClicks() {
    if (window.__urNewsletterTracked) return;
    window.__urNewsletterTracked = true;
    document.addEventListener("click", function (e) {
      var link = e.target && e.target.closest ? e.target.closest(NEWSLETTER_LINK) : null;
      if (!link || typeof window.gtag !== "function") return;
      window.gtag("event", "newsletter_click");
      // The conversion goes to Google Ads, so it needs the advertisement category as well.
      if (getChoice().advertisement) window.gtag("event", "conversion", { send_to: NEWSLETTER_CONVERSION });
    });
  }

  // Embedded X posts: widgets.js is third-party and sets its own cookies, so it
  // loads only after consent. Without consent the <blockquote> shows as plain text.
  function loadEmbeds() {
    if (window.__urEmbedsLoaded) return;
    if (!document.querySelector(".twitter-tweet")) return;
    window.__urEmbedsLoaded = true;
    // Swaps the "loads once you accept cookies" placeholders for the posts (see .ur-embeds-on in extra.css).
    document.documentElement.classList.add("ur-embeds-on");
    var s = document.createElement("script");
    s.async = true;
    s.charset = "utf-8";
    s.src = "https://platform.x.com/widgets.js";
    document.body.appendChild(s);
  }

  // Google AdSense: the library and the slot markup (assets/ads.js) load only after
  // consent. Without it the .ur-ad placeholders stay hidden.
  function loadAds() {
    if (window.__urAdsLoaded) return;
    if (!document.querySelector(".ur-ad")) return;
    window.__urAdsLoaded = true;
    var s = document.createElement("script");
    s.async = true;
    s.src = "/assets/ads.js";
    document.body.appendChild(s);
  }

  // The nav (with the Support link) arrives after the page loads, so wait for it.
  function loadCommerce() {
    if (window.__urCommerceLoaded) return;
    if (!document.querySelector("a[data-commerce]")) return;
    window.__urCommerceLoaded = true;
    var s = document.createElement("script");
    s.async = true;
    s.defer = true;
    s.src = KIT_COMMERCE_SRC;
    document.head.appendChild(s);
  }

  // Runs on page load and on every change of choice.
  function applyConsent() {
    var choice = getChoice();
    updateConsentSignals(choice);
    loadGoogleTag(choice);
    if (choice.functional) loadCommerce();
    if (choice.advertisement) {
      loadEmbeds();
      loadAds();
    }
  }

  function loadCookieYes() {
    if (document.getElementById("cookieyes")) return;
    var s = document.createElement("script");
    s.id = "cookieyes";
    s.src = COOKIEYES_SRC;
    document.head.appendChild(s);
  }

  function init() {
    ensureGtag(); // queues the "denied" default before CookieYes can queue anything
    document.addEventListener("cookieyes_banner_load", applyConsent);
    document.addEventListener("cookieyes_consent_update", applyConsent);
    document.addEventListener("partials:ready", function () {
      if (getChoice().functional) loadCommerce();
    });
    loadCookieYes();
    // If CookieYes was already there (e.g. loaded earlier in the page), catch up now.
    if (typeof window.getCkyConsent === "function") applyConsent();
  }

  // Exposed so a "Cookie settings" link (in the footer, or the privacy page's own
  // button) can reopen the CookieYes preferences and let a visitor change their mind.
  window.UR_openCookieChoice = function () {
    if (typeof window.revisitCkyConsent === "function") window.revisitCkyConsent();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
