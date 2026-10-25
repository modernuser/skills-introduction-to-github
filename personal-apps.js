/* Pure logic for dice.html and calendar.html. No DOM, no network, so the
   pytest suite can run it under node (tests/python/test_personal_pages.py). */
(function (root) {
  "use strict";

  // Monopoly GO reward links are published as mply.io short links.
  // Anything else pasted alongside them (aggregator redirects, look-alike
  // domains) is dropped rather than trusted.
  var DICE_HOSTS = ["mply.io"];

  function extractDiceLinks(text) {
    var found = [];
    var seen = {};
    var re = /https?:\/\/[^\s"'<>()]+/gi;
    var m;
    while ((m = re.exec(String(text || ""))) !== null) {
      var raw = m[0].replace(/[.,;!?]+$/, "");
      var u;
      try { u = new URL(raw); } catch (e) { continue; }
      var host = u.hostname.toLowerCase().replace(/^www\./, "");
      if (DICE_HOSTS.indexOf(host) === -1) continue;
      if (u.pathname.length < 2) continue;          // bare domain, no code
      var clean = "https://" + host + u.pathname + u.search;
      if (seen[clean]) continue;
      seen[clean] = true;
      found.push(clean);
    }
    return found;
  }

  // Adds new URLs to the stored list; existing entries keep their
  // added/claimed state. Returns {links, added}.
  function mergeLinks(existing, urls, now) {
    var links = (existing || []).slice();
    var have = {};
    links.forEach(function (l) { have[l.url] = true; });
    var added = 0;
    urls.forEach(function (url) {
      if (have[url]) return;
      have[url] = true;
      links.push({ url: url, added_at: now, claimed_at: null });
      added++;
    });
    links.sort(function (a, b) { return b.added_at < a.added_at ? -1 : b.added_at > a.added_at ? 1 : 0; });
    return { links: links, added: added };
  }

  // Splits into unclaimed / older-than-cutoff / claimed. The cutoff is the
  // owner's setting, not a published expiry.
  function partitionLinks(links, now, hideAfterDays) {
    var cutoff = new Date(new Date(now).getTime() - hideAfterDays * 864e5).toISOString();
    var out = { open: [], old: [], claimed: [] };
    (links || []).forEach(function (l) {
      if (l.claimed_at) out.claimed.push(l);
      else if (l.added_at < cutoff) out.old.push(l);
      else out.open.push(l);
    });
    return out;
  }

  // Returns a normalized https URL string, or null. Blocks javascript:,
  // data:, and plain http so a pasted value can never become script.
  function safeHttpsUrl(value) {
    var u;
    try { u = new URL(String(value || "").trim()); } catch (e) { return null; }
    return u.protocol === "https:" ? u.href : null;
  }

  var VIEW_MODES = { week: "WEEK", month: "MONTH", agenda: "AGENDA" };

  function buildCalendarEmbedUrl(calendarId, tz, view) {
    var id = String(calendarId || "").trim();
    if (!id || /\s/.test(id)) return null;
    var p = new URLSearchParams({
      src: id,
      ctz: tz || "UTC",
      mode: VIEW_MODES[view] || "WEEK",
      showPrint: "0",
      showTitle: "0"
    });
    return "https://calendar.google.com/calendar/embed?" + p.toString();
  }

  var api = {
    DICE_HOSTS: DICE_HOSTS,
    extractDiceLinks: extractDiceLinks,
    mergeLinks: mergeLinks,
    partitionLinks: partitionLinks,
    safeHttpsUrl: safeHttpsUrl,
    buildCalendarEmbedUrl: buildCalendarEmbedUrl
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.PersonalApps = api;
})(this);
