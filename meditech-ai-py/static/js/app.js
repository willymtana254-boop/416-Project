// ==========================================================================
// PART 1: CHAT, RESULTS AND FACILITIES
// Page text in English and Kiswahili, the conversation, the result card, nearby facilities.
// Exposes window.MT for the two parts below.
// ==========================================================================
(() => {
  // <i18n>
  const I18N = {
    en: {
      pill: "Agentic triage",
      hero: "Describe your symptoms — MediTECH AI may ask a few follow-up questions before giving a triage assessment, the way an intake nurse would.",
      phFirst: "e.g. I have a throbbing headache behind my eyes, slight fever, and nausea. It started this morning…",
      phAnswer: "Your answer…",
      tag_headache: "Headache", tag_fever: "Fever", tag_fatigue: "Fatigue", tag_nausea: "Nausea",
      tag_cough: "Cough", tag_chest: "Chest pain", tag_breath: "Shortness of breath",
      tag_dizzy: "Dizziness", tag_rash: "Rash", tag_joint: "Joint pain",
      area_none: "— Primary affected area (optional) —",
      area_head: "Head & Neck", area_chest: "Chest & Heart", area_abdomen: "Abdomen & Digestive",
      area_back: "Back & Spine", area_arms: "Arms & Hands", area_legs: "Legs & Feet", area_skin: "Skin",
      area_eyes: "Eyes", area_ent: "Ears, Nose & Throat", area_urinary: "Urinary & Reproductive",
      area_general: "General / Whole Body",
      region_none: "— Where are you? (optional) —",
      region_coast: "Coast (Mombasa, Kilifi, Kwale, Lamu, Tana River, Taita-Taveta)",
      region_lake: "Lake Victoria / Western (Kisumu, Siaya, Homa Bay, Migori, Busia, Kakamega, Bungoma)",
      region_rift: "Rift Valley (Nakuru, Uasin Gishu, Kericho, Nandi, Trans Nzoia, Baringo, Narok, Kajiado)",
      region_central: "Nairobi & Central (Nairobi, Kiambu, Nyeri, Murang'a, Kirinyaga, Embu, Meru)",
      region_north: "Northern & Eastern dry areas (Turkana, Marsabit, Garissa, Wajir, Mandera, Isiolo, Kitui)",
      photo: "Photo of a visible symptom (optional)",
      start: "🔬 Start assessment", send: "Send answer", thinking: "Thinking…",
      errEmpty: "Please describe your symptoms or attach an image.",
      errGeneric: "Something went wrong.",
      sentImage: "(sent an image)",
      sev_low: "Low severity", sev_medium: "Medium severity", sev_high: "High severity",
      like_high: "high", like_medium: "medium", like_low: "low",
      redFlags: "Red flags identified:",
      secConditions: "Possible conditions", secActions: "Recommended actions",
      sources: "Informed by reference notes on:",
      disclaimer: "⚠️ This is informational only and is not a medical diagnosis. Always consult a qualified healthcare professional for advice, diagnosis, or treatment.",
      newAssessment: "↺ New assessment",
      emergBanner: "🚨 High severity. Call 999 or 112, or go to the nearest hospital now.",
      emergBtn: "Find nearest hospital",
      facTitle: "📍 Find the nearest health facility",
      facSub: "Hospitals, clinics and pharmacies near you",
      facBtn: "🗺️ Use my location", facRefresh: "🔄 Refresh",
      facFoot: "Your location is sent to this app's server only to search OpenStreetMap and isn't saved by this app. Map data © OpenStreetMap contributors. Listings may be incomplete or out of date. In an emergency call 999 or 112.",
      facLoading: "Finding facilities near you…",
      facDenied: "Location access was blocked. Allow location in your browser and try again.",
      facNoGeo: "Your browser doesn't support location.",
      facError: "Could not load facilities. Please try again.",
      facNone: "No facilities found nearby in the map data. The data may be incomplete: ask locally, or call 999 or 112 in an emergency.",
      facCount: "{n} shown · searched within {r} km",
      filter_all: "All", filter_hospital: "Hospitals", filter_clinic: "Clinics", filter_pharmacy: "Pharmacies",
      kind_hospital: "Hospital", kind_clinic: "Clinic / health centre", kind_pharmacy: "Pharmacy",
      facEmergency: "Emergency services", facUnnamed: "Unnamed",
      facDirections: "Directions", facCall: "Call",
    },
    sw: {
      pill: "Tathmini ya awali",
      hero: "Eleza dalili zako — MediTECH AI inaweza kukuuliza maswali machache kabla ya kutoa tathmini, kama muuguzi wa mapokezi.",
      phFirst: "k.m. Nina maumivu makali ya kichwa nyuma ya macho, homa kidogo na kichefuchefu. Yalianza asubuhi ya leo…",
      phAnswer: "Jibu lako…",
      tag_headache: "Maumivu ya kichwa", tag_fever: "Homa", tag_fatigue: "Uchovu", tag_nausea: "Kichefuchefu",
      tag_cough: "Kikohozi", tag_chest: "Maumivu ya kifua", tag_breath: "Kukosa pumzi",
      tag_dizzy: "Kizunguzungu", tag_rash: "Vipele", tag_joint: "Maumivu ya viungo",
      area_none: "— Sehemu kuu iliyoathirika (si lazima) —",
      area_head: "Kichwa na shingo", area_chest: "Kifua na moyo", area_abdomen: "Tumbo na mmeng'enyo",
      area_back: "Mgongo", area_arms: "Mikono", area_legs: "Miguu", area_skin: "Ngozi",
      area_eyes: "Macho", area_ent: "Masikio, pua na koo", area_urinary: "Mkojo na uzazi",
      area_general: "Mwili mzima",
      region_none: "— Uko wapi? (si lazima) —",
      region_coast: "Pwani (Mombasa, Kilifi, Kwale, Lamu, Tana River, Taita-Taveta)",
      region_lake: "Ziwa Victoria / Magharibi (Kisumu, Siaya, Homa Bay, Migori, Busia, Kakamega, Bungoma)",
      region_rift: "Bonde la Ufa (Nakuru, Uasin Gishu, Kericho, Nandi, Trans Nzoia, Baringo, Narok, Kajiado)",
      region_central: "Nairobi na Kati (Nairobi, Kiambu, Nyeri, Murang'a, Kirinyaga, Embu, Meru)",
      region_north: "Kaskazini na Mashariki kavu (Turkana, Marsabit, Garissa, Wajir, Mandera, Isiolo, Kitui)",
      photo: "Picha ya dalili inayoonekana (si lazima)",
      start: "🔬 Anza tathmini", send: "Tuma jibu", thinking: "Inafikiria…",
      errEmpty: "Tafadhali eleza dalili zako au ambatisha picha.",
      errGeneric: "Kuna hitilafu imetokea.",
      sentImage: "(nimetuma picha)",
      sev_low: "Hatari ndogo", sev_medium: "Hatari ya wastani", sev_high: "Hatari kubwa",
      like_high: "juu", like_medium: "wastani", like_low: "chini",
      redFlags: "Dalili hatari zilizobainika:",
      secConditions: "Hali zinazowezekana", secActions: "Hatua zinazopendekezwa",
      sources: "Imetegemea maelezo ya rejea kuhusu:",
      disclaimer: "⚠️ Hii ni taarifa ya jumla tu na si utambuzi wa kitabibu. Daima wasiliana na mtaalamu wa afya aliyehitimu kwa ushauri, utambuzi au matibabu.",
      newAssessment: "↺ Tathmini mpya",
      emergBanner: "🚨 Hatari kubwa. Piga 999 au 112, au nenda hospitali iliyo karibu sasa.",
      emergBtn: "Tafuta hospitali iliyo karibu",
      facTitle: "📍 Tafuta kituo cha afya kilicho karibu",
      facSub: "Hospitali, zahanati na maduka ya dawa karibu nawe",
      facBtn: "🗺️ Tumia mahali nilipo", facRefresh: "🔄 Onyesha upya",
      facFoot: "Mahali ulipo hutumwa kwa seva ya programu hii ili kutafuta kwenye OpenStreetMap tu na hakihifadhiwi na programu hii. Data ya ramani © wachangiaji wa OpenStreetMap. Orodha inaweza kuwa pungufu au isiyosasishwa. Wakati wa dharura piga 999 au 112.",
      facLoading: "Inatafuta vituo vilivyo karibu nawe…",
      facDenied: "Ruhusa ya mahali imezuiwa. Ruhusu mahali kwenye kivinjari chako kisha ujaribu tena.",
      facNoGeo: "Kivinjari chako hakiwezi kutambua mahali.",
      facError: "Imeshindwa kupakia vituo. Tafadhali jaribu tena.",
      facNone: "Hakuna vituo vilivyopatikana karibu kwenye data ya ramani. Data inaweza kuwa pungufu: uliza watu wa eneo hilo, au piga 999 au 112 wakati wa dharura.",
      facCount: "{n} vimeonyeshwa · utafutaji ndani ya km {r}",
      filter_all: "Vyote", filter_hospital: "Hospitali", filter_clinic: "Zahanati na kliniki", filter_pharmacy: "Maduka ya dawa",
      kind_hospital: "Hospitali", kind_clinic: "Zahanati / kituo cha afya", kind_pharmacy: "Duka la dawa",
      facEmergency: "Huduma za dharura", facUnnamed: "Bila jina",
      facDirections: "Maelekezo", facCall: "Piga simu",
    },
  };
  // </i18n>

  // ── Small helpers ──
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable: fine */ } },
    del(k) { try { localStorage.removeItem(k); } catch { /* storage unavailable: fine */ } },
  };
  let lang = store.get("meditech_lang") === "sw" ? "sw" : "en";
  const t = (key) => (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
  // t() returns the key itself when a translation is missing; tOr() lets callers
  // fall back to the raw value instead (e.g. an unexpected likelihood from the model).
  const tOr = (key, fallback) => ((I18N[lang] && I18N[lang][key]) || I18N.en[key] || fallback);
  const fmt = (s, vars) => s.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : ""));
  const esc = (s) =>
    String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  // A fetch() that never reached the server (no connection, DNS failure...) rejects with a TypeError.
  // Compared by name so it also works across browser frames. the accounts part (below) marks its own with code "offline".
  const isNetworkError = (e) => !!e && (e.name === "TypeError" || e.code === "offline" || e.network === true);

  const FAC_KEY = "meditech_fac_cache";
  const rad = (d) => (d * Math.PI) / 180;
  function haversineKm(lat1, lon1, lat2, lon2) {
    const dp = rad(lat2 - lat1), dl = rad(lon2 - lon1);
    const a = Math.sin(dp / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dl / 2) ** 2;
    return 2 * 6371 * Math.asin(Math.sqrt(a));
  }
  function fmtDate(iso) {
    try {
      const d = new Date(iso);
      return isNaN(d) ? String(iso || "") : d.toLocaleString(lang === "sw" ? "sw-KE" : "en-GB", { dateStyle: "medium", timeStyle: "short" });
    } catch { return String(iso || ""); }
  }

  // Extension points for the accounts part (part 2) (sign-in, saved history, clinician view).
  const hooks = { lang: [], assessment: [], afterRender: [], reset: [] };

  // ── State ──
  let history = [];          // Gemini-format conversation, resent every turn
  let imageB64 = null;       // {mimeType, data} | null
  let isFirstTurn = true;
  let loading = false;
  let lastAssessment = null; // {turn, sources}, kept so a language switch can re-render it
  const fac = { items: [], radiusKm: 0, filter: "all", status: "idle", errorMsg: "", cachedAt: null, cachedNow: false };

  // ── DOM refs ──
  const $ = (id) => document.getElementById(id);
  const chatLog = $("chatLog"), textInput = $("textInput"), firstTurnExtras = $("firstTurnExtras");
  const bodyArea = $("bodyArea"), regionSelect = $("regionSelect"), imgFile = $("imgFile");
  const goBtn = $("goBtn"), inputCard = $("inputCard"), errBox = $("errBox"), resultsCard = $("resultsCard");
  const langSelect = $("langSelect");
  const locBtn = $("locBtn"), facFilters = $("facFilters"), facStatus = $("facStatus"), facList = $("facList");
  const facCard = $("facCard"), facNote = $("facNote"), facForget = $("facForget");

  // ── Language ──
  function applyI18n() {
    document.documentElement.lang = lang;
    langSelect.value = lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    textInput.placeholder = isFirstTurn ? t("phFirst") : t("phAnswer");
    refreshButton();
    if (lastAssessment) renderAssessment(lastAssessment.turn, lastAssessment.sources);
    renderFacilities();
    hooks.lang.forEach((fn) => fn());
  }

  langSelect.addEventListener("change", () => {
    lang = langSelect.value === "sw" ? "sw" : "en";
    store.set("meditech_lang", lang);
    applyI18n();
  });

  // Remember the region between visits (a convenience, not sensitive).
  const savedRegion = store.get("meditech_region");
  if (savedRegion && [...regionSelect.options].some((o) => o.value === savedRegion)) {
    regionSelect.value = savedRegion;
  }
  regionSelect.addEventListener("change", () => store.set("meditech_region", regionSelect.value));

  // ── Quick tags: insert the tag in the language currently shown ──
  document.querySelectorAll(".qtag[data-i18n]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tag = btn.textContent;
      textInput.value = textInput.value.trim() ? `${textInput.value.trim()}, ${tag}` : tag;
      textInput.focus();
    });
  });

  // ── Image upload ──
  imgFile.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      imageB64 = { mimeType: file.type, data: ev.target.result.split(",")[1] };
    };
    reader.readAsDataURL(file);
  });

  // ── Send ──
  goBtn.addEventListener("click", send);

  function refreshButton() {
    goBtn.disabled = loading;
    goBtn.textContent = loading ? t("thinking") : isFirstTurn ? t("start") : t("send");
  }

  async function send() {
    const text = textInput.value.trim();
    if (!text && !imageB64) {
      showErr(t("errEmpty"));
      return;
    }
    hideErr();
    loading = true;
    refreshButton();

    const pending = addBubble("user", text || t("sentImage"));
    let accepted = false; // true once the server has answered, so we only undo a bubble that never got through

    const payload = {
      history,
      message: text,
      image: imageB64 || undefined,
      bodyArea: isFirstTurn ? bodyArea.value || undefined : undefined,
      language: lang,
      region: regionSelect.value || undefined,
    };

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);

      history = data.history;
      accepted = true;
      isFirstTurn = false;
      firstTurnExtras.style.display = "none";
      textInput.value = "";
      textInput.rows = 3;
      imageB64 = null;
      imgFile.value = "";

      if (data.turn.kind === "question") {
        addBubble("model", data.turn.question, data.turn.reason);
      } else {
        lastAssessment = { turn: data.turn, sources: data.sources };
        hooks.assessment.forEach((fn) => fn(data));
        if (data.turn.severity === "high") fac.filter = "hospital";
        renderAssessment(data.turn, data.sources);
        renderFacilities();
        inputCard.style.display = "none";
      }
    } catch (e) {
      if (!accepted && pending) pending.remove(); // the text stays in the box so the patient can simply try again
      showErr(isNetworkError(e) ? t("errOffline") : e.message || t("errGeneric"));
    } finally {
      loading = false;
      applyI18n();
    }
  }

  // ── Chat + assessment rendering ──
  function addBubble(from, text, reason) {
    const div = document.createElement("div");
    div.className = `bubble ${from}`;
    div.textContent = text;
    if (reason) {
      const r = document.createElement("span");
      r.className = "reason";
      r.textContent = reason;
      div.appendChild(r);
    }
    chatLog.appendChild(div);
    div.scrollIntoView({ behavior: "smooth", block: "end" });
    return div;
  }

  function renderAssessment(d, sources) {
    const sev = ["low", "medium", "high"].includes(d.severity) ? d.severity : "medium";
    const likeCls = { high: "lh", medium: "lm", low: "ll" };
    const actIco = { urgent: "🚨", soon: "📅", self: "🏠" };

    const emergencyHtml =
      sev === "high"
        ? `<div class="emerg-banner"><span>${esc(t("emergBanner"))}</span>
             <button class="loc-btn" id="emergBtn" type="button">${esc(t("emergBtn"))}</button></div>`
        : "";

    const redFlagsHtml =
      d.redFlags && d.redFlags.length
        ? `<div class="redflags">⚠️ ${esc(t("redFlags"))}<ul>${d.redFlags
            .map((f) => `<li>${esc(f)}</li>`).join("")}</ul></div>`
        : "";

    const condsHtml = (d.conditions || [])
      .map((c, i) => `
      <div class="cond">
        <div class="cond-n">${i + 1}</div>
        <div>
          <div class="cond-name">${esc(c.name)}</div>
          <div class="cond-desc">${esc(c.description)}</div>
        </div>
        <div class="cond-like ${likeCls[c.likelihood] || "lm"}">${esc(tOr("like_" + c.likelihood, c.likelihood))}</div>
      </div>`).join("");

    const actsHtml = (d.actions || [])
      .map((a) => `<div class="act a-${["urgent", "soon", "self"].includes(a.type) ? a.type : "self"}">${actIco[a.type] || "•"} ${esc(a.text)}</div>`)
      .join("");

    const sourcesHtml =
      sources && sources.length
        ? `<div class="sources">📖 ${esc(t("sources"))} ${sources.map((s) => esc(s)).join(", ")}</div>`
        : "";

    resultsCard.innerHTML = `
      <span class="badge b-${sev}">${esc(t("sev_" + sev))}</span>
      ${emergencyHtml}
      ${redFlagsHtml}
      <div class="sec">${esc(t("secConditions"))}</div>
      ${condsHtml}
      <div class="sec">${esc(t("secActions"))}</div>
      ${actsHtml}
      ${sourcesHtml}
      <div id="saveNote"></div>
      <div class="disc">${esc(t("disclaimer"))}</div>
      <button class="new-btn" id="newBtn" type="button">${esc(t("newAssessment"))}</button>
    `;
    resultsCard.style.display = "block";
    $("newBtn").addEventListener("click", resetAll);
    const eb = $("emergBtn");
    if (eb) {
      eb.addEventListener("click", () => {
        fac.filter = "hospital";
        facCard.scrollIntoView({ behavior: "smooth", block: "start" });
        findFacilities();
      });
    }
    hooks.afterRender.forEach((fn) => fn());
  }

  function resetAll() {
    history = [];
    imageB64 = null;
    isFirstTurn = true;
    lastAssessment = null;
    hooks.reset.forEach((fn) => fn());
    fac.filter = "all";
    chatLog.innerHTML = "";
    resultsCard.style.display = "none";
    resultsCard.innerHTML = "";
    inputCard.style.display = "block";
    firstTurnExtras.style.display = "block";
    textInput.value = "";
    textInput.rows = 5;
    bodyArea.value = "";
    imgFile.value = "";
    hideErr();
    applyI18n();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function showErr(msg) {
    errBox.textContent = `⚠️ ${msg}`;
    errBox.style.display = "block";
  }
  function hideErr() {
    errBox.style.display = "none";
  }

  // ── Nearest facilities ──
  locBtn.addEventListener("click", findFacilities);
  facForget.addEventListener("click", () => {
    forgetFacilities();
    if (window.MT && MT.flash) MT.flash(t("fac_forgotten"));
  });

  facFilters.addEventListener("click", (e) => {
    const b = e.target.closest("[data-filter]");
    if (!b) return;
    fac.filter = b.dataset.filter;
    renderFacilities();
  });

  // The last successful search is kept on this device (facility names, places and phone numbers: no
  // account data, and not the patient's own position) so the list still opens when the connection or
  // the map service is down. GPS works offline, so distances are recalculated from where the patient is now.
  function saveFacCache(data) {
    store.set(FAC_KEY, JSON.stringify({
      savedAt: new Date().toISOString(), radiusKm: data.radiusKm, items: (data.facilities || []).slice(0, 40),
    }));
  }
  function loadFacCache() {
    try {
      const c = JSON.parse(store.get(FAC_KEY));
      return c && Array.isArray(c.items) && c.items.length ? c : null;
    } catch { return null; }
  }
  function useFacCache(cache, pos) {
    let items = cache.items;
    if (pos) {
      items = items
        .map((f) => (typeof f.lat === "number" && typeof f.lon === "number"
          ? { ...f, distanceKm: Math.round(haversineKm(pos.coords.latitude, pos.coords.longitude, f.lat, f.lon) * 10) / 10 }
          : f))
        .sort((a, b) => a.distanceKm - b.distanceKm);
    }
    fac.items = items;
    fac.radiusKm = cache.radiusKm;
    fac.cachedAt = cache.savedAt;
    fac.cachedNow = !!pos;
    fac.status = "done";
  }
  function forgetFacilities() {
    store.del(FAC_KEY);
    if (fac.cachedAt) { fac.items = []; fac.status = "idle"; fac.cachedAt = null; }
    renderFacilities();
  }

  function findFacilities() {
    if (!navigator.geolocation) {
      fac.status = "error";
      fac.errorMsg = t("facNoGeo");
      renderFacilities();
      return;
    }
    fac.status = "loading";
    fac.cachedAt = null;
    renderFacilities();

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const res = await fetch("/api/facilities", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
          });
          const data = await res.json();
          if (!res.ok) { const err = new Error(data.error || t("facError")); err.status = res.status; throw err; }
          fac.items = data.facilities || [];
          fac.radiusKm = data.radiusKm;
          fac.cachedAt = null;
          fac.status = "done";
          if (fac.items.length) saveFacCache(data); // never overwrite a good saved list with an empty result
        } catch (e) {
          // No connection, or the map service is failing (a 5xx): the saved list is better than an error.
          const unavailable = isNetworkError(e) || (e && e.status >= 500);
          const cache = unavailable ? loadFacCache() : null;
          if (cache) {
            useFacCache(cache, pos);
          } else {
            fac.status = "error";
            fac.errorMsg = isNetworkError(e) ? t("facNoCache") : e.message || t("facError");
          }
        }
        renderFacilities();
      },
      () => {
        // No location. If we are also offline, the saved list (old distances) is better than nothing.
        const cache = navigator.onLine === false ? loadFacCache() : null;
        if (cache) useFacCache(cache, null);
        else fac.status = "denied";
        renderFacilities();
      },
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 }
    );
  }

  // Only ever link to the map URL pattern the server builds.
  const safeMapUrl = (u) =>
    typeof u === "string" && u.startsWith("https://www.google.com/maps/dir/?api=1&destination=") ? u : "";

  function renderFacilities() {
    locBtn.disabled = fac.status === "loading";
    locBtn.textContent = fac.status === "done" ? t("facRefresh") : t("facBtn");

    facNote.style.display = "none";
    if (fac.status === "done" && fac.cachedAt) {
      facNote.textContent = fmt(t(fac.cachedNow ? "facCachedNow" : "facCachedOld"), { date: fmtDate(fac.cachedAt) });
      facNote.style.display = "block";
    }
    facForget.style.display = loadFacCache() ? "" : "none";

    facStatus.className = "fac-status";
    if (fac.status === "loading") facStatus.textContent = t("facLoading");
    else if (fac.status === "denied") { facStatus.textContent = t("facDenied"); facStatus.classList.add("bad"); }
    else if (fac.status === "error") { facStatus.textContent = fac.errorMsg || t("facError"); facStatus.classList.add("bad"); }
    else facStatus.textContent = "";

    if (fac.status !== "done") {
      facFilters.style.display = "none";
      facList.innerHTML = "";
      return;
    }

    if (!fac.items.length) {
      facFilters.style.display = "none";
      facStatus.textContent = t("facNone");
      facList.innerHTML = "";
      return;
    }

    facFilters.style.display = "flex";
    facFilters.innerHTML = ["all", "hospital", "clinic", "pharmacy"]
      .map((k) => `<button type="button" class="qtag${fac.filter === k ? " on" : ""}" data-filter="${k}">${esc(t("filter_" + k))}</button>`)
      .join("");

    const shown = fac.items.filter((f) => fac.filter === "all" || f.kind === fac.filter).slice(0, 10);
    facStatus.textContent = fmt(t("facCount"), { n: shown.length, r: fac.radiusKm });

    facList.innerHTML = shown.map((f) => {
      const url = safeMapUrl(f.directionsUrl);
      const phone = String(f.phone || "").replace(/[^\d+]/g, "");
      const meta = [t("kind_" + f.kind), `${Number(f.distanceKm).toFixed(1)} km`];
      if (f.emergency) meta.push(t("facEmergency"));
      return `
        <div class="fac-item">
          <div>
            <div class="fac-name">${esc(f.name || t("facUnnamed"))}</div>
            <div class="fac-meta">${meta.map(esc).join(" · ")}</div>
            ${f.openingHours ? `<div class="fac-hours">${esc(f.openingHours)}</div>` : ""}
          </div>
          <div class="fac-actions">
            ${url ? `<a class="fac-link primary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(t("facDirections"))}</a>` : ""}
            ${phone ? `<a class="fac-link" href="tel:${esc(phone)}">${esc(t("facCall"))}</a>` : ""}
          </div>
        </div>`;
    }).join("");
  }

  // ── Public surface for parts 2 and 3 ──
  window.MT = {
    t, esc, fmt, store, isNetworkError, FAC_KEY, fmtDate, forgetFacilities,
    getLang: () => lang,
    reload: () => window.location.reload(),
    hooks,
    refresh: applyI18n,
    rerender: () => { if (lastAssessment) renderAssessment(lastAssessment.turn, lastAssessment.sources); },
    addStrings(strings) {
      for (const L of ["en", "sw"]) Object.assign(I18N[L], (strings && strings[L]) || {});
    },
  };

  // ── Start ──
  applyI18n();
})();

// ==========================================================================
// PART 2: ACCOUNTS, HISTORY AND THE CLINICIAN QUEUE
// Sign-in, saved results, sharing, and the clinician view.
// ==========================================================================
(() => {
  // Accounts, saved history and the clinician queue (Phase 4).
  // Uses window.MT from part 1 (translation helper and extension hooks).
  if (!window.MT) return;
  const MT = window.MT;
  const { t, esc, fmt, hooks } = MT;
  const $ = (id) => document.getElementById(id);

  // <i18n>
  // Patient-facing strings exist in English and Kiswahili. Strings starting
  // with clin_ are for clinicians and fall back to English.
  const STRINGS = {
    en: {
      acct_signin: "Sign in", acct_signout: "Sign out", acct_history: "My history",
      acct_clinician: "Clinician queue", back: "← Back",
      auth_tab_signin: "Sign in", auth_tab_register: "Create account",
      auth_title_signin: "Sign in to your account", auth_title_register: "Create an account",
      auth_name: "Your name", auth_email: "Email", auth_password: "Password",
      auth_password_hint: "At least 8 characters.",
      auth_submit_signin: "Sign in", auth_submit_register: "Create account",
      auth_working: "Please wait…",
      auth_privacy: "An account is optional: you can use MediTECH AI without one. With an account you can keep a history of your assessments and, only if you choose, share one with a clinician. Your assessments are stored on this app's server. Photos are never stored.",
      err_invalid_email: "Please enter a valid email address.",
      err_weak_password: "Choose a password of at least 8 characters that is not easy to guess.",
      err_name_required: "Please enter your name.",
      err_email_taken: "An account with this email already exists. Try signing in.",
      err_bad_credentials: "Incorrect email or password.",
      err_rate_limited: "Too many attempts. Please wait a few minutes and try again.",
      err_not_logged_in: "Please sign in first.",
      err_not_found: "That record was not found.",
      err_too_large: "That photo is too large. Please use a smaller image.",
      save_saved: "✓ Saved to your history",
      save_deleted: "Assessment deleted.",
      save_failed: "Could not save this assessment to your history.",
      save_guest: "Sign in to save this assessment and track your history over time.",
      save_share: "Share with a clinician", save_unshare: "Stop sharing",
      save_shared_note: "Shared: clinicians can see your name and this assessment.",
      save_delete: "Delete",
      trend_notice: "You have had {n} assessments rated medium or high severity in the last {d} days. Consider booking a check-up with a clinician.",
      hist_title: "My assessments", hist_empty: "No saved assessments yet.",
      hist_loading: "Loading…", hist_failed: "Could not load your history.", hist_more: "Load more",
      hist_shared: "Shared", hist_reviewed: "Reviewed", hist_note: "Clinician's note",
      hist_conversation: "Conversation",
      hist_confirm_delete: "Delete this assessment? This cannot be undone.",
      acct_delete_title: "Delete my account",
      acct_delete_help: "This permanently deletes your account and every saved assessment. Enter your password to confirm.",
      acct_delete_btn: "Delete account and all data",
      acct_delete_confirm: "Permanently delete your account and all your data?",
      acct_deleted: "Your account and data were deleted.",
      clin_title: "Shared assessments",
      clin_sub: "Only assessments that patients chose to share appear here.",
      clin_filter_new: "Awaiting review", clin_filter_reviewed: "Reviewed", clin_filter_all: "All",
      clin_empty: "Nothing here.", clin_failed: "Could not load the queue.",
      clin_note_label: "Note to the patient (they will see this)",
      clin_mark: "Mark as reviewed", clin_saved: "Review saved.",
    },
    sw: {
      acct_signin: "Ingia", acct_signout: "Toka", acct_history: "Historia yangu",
      acct_clinician: "Foleni ya wataalamu", back: "← Rudi",
      auth_tab_signin: "Ingia", auth_tab_register: "Fungua akaunti",
      auth_title_signin: "Ingia kwenye akaunti yako", auth_title_register: "Fungua akaunti",
      auth_name: "Jina lako", auth_email: "Barua pepe", auth_password: "Nenosiri",
      auth_password_hint: "Angalau herufi 8.",
      auth_submit_signin: "Ingia", auth_submit_register: "Fungua akaunti",
      auth_working: "Tafadhali subiri…",
      auth_privacy: "Akaunti si lazima: unaweza kutumia MediTECH AI bila akaunti. Ukiwa na akaunti unaweza kuhifadhi historia ya tathmini zako na, ukitaka tu, kushiriki moja na mtaalamu wa afya. Tathmini zako huhifadhiwa kwenye seva ya programu hii. Picha hazihifadhiwi kamwe.",
      err_invalid_email: "Tafadhali weka barua pepe halali.",
      err_weak_password: "Chagua nenosiri lenye angalau herufi 8 ambalo si rahisi kubashiri.",
      err_name_required: "Tafadhali weka jina lako.",
      err_email_taken: "Akaunti yenye barua pepe hii tayari ipo. Jaribu kuingia.",
      err_bad_credentials: "Barua pepe au nenosiri si sahihi.",
      err_rate_limited: "Majaribio mengi mno. Tafadhali subiri dakika chache kisha ujaribu tena.",
      err_not_logged_in: "Tafadhali ingia kwanza.",
      err_not_found: "Rekodi hiyo haikupatikana.",
      err_too_large: "Picha hiyo ni kubwa mno. Tafadhali tumia picha ndogo zaidi.",
      save_saved: "✓ Imehifadhiwa kwenye historia yako",
      save_deleted: "Tathmini imefutwa.",
      save_failed: "Imeshindwa kuhifadhi tathmini hii kwenye historia yako.",
      save_guest: "Ingia ili kuhifadhi tathmini hii na kufuatilia historia yako kadri muda unavyopita.",
      save_share: "Shiriki na mtaalamu wa afya", save_unshare: "Acha kushiriki",
      save_shared_note: "Imeshirikiwa: wataalamu wa afya wanaweza kuona jina lako na tathmini hii.",
      save_delete: "Futa",
      trend_notice: "Umekuwa na tathmini {n} zenye hatari ya wastani au kubwa katika siku {d} zilizopita. Fikiria kupanga uchunguzi na mtaalamu wa afya.",
      hist_title: "Tathmini zangu", hist_empty: "Hakuna tathmini zilizohifadhiwa bado.",
      hist_loading: "Inapakia…", hist_failed: "Imeshindwa kupakia historia yako.", hist_more: "Pakia zaidi",
      hist_shared: "Imeshirikiwa", hist_reviewed: "Imekaguliwa", hist_note: "Maelezo ya mtaalamu",
      hist_conversation: "Mazungumzo",
      hist_confirm_delete: "Futa tathmini hii? Hii haiwezi kurudishwa.",
      acct_delete_title: "Futa akaunti yangu",
      acct_delete_help: "Hii itafuta kabisa akaunti yako na tathmini zote zilizohifadhiwa. Weka nenosiri lako kuthibitisha.",
      acct_delete_btn: "Futa akaunti na data yote",
      acct_delete_confirm: "Futa kabisa akaunti yako na data yako yote?",
      acct_deleted: "Akaunti yako na data yako zimefutwa.",
    },
  };
  // </i18n>
  MT.addStrings(STRINGS);

  // ── State ──
  let me = null;             // {id, name, email, role} | null
  let view = "home";
  let authMode = "signin";
  let saveInfo = null;       // save state of the assessment currently on screen
  let flashTimer = null;
  const hist = { items: [], total: 0, trend: null, open: new Set(), details: {}, loading: false, error: false, offline: false, needsOnline: false, savedAt: null };
  const clin = { status: "new", items: [], total: 0, open: null, detail: null, loading: false, error: false, offline: false };

  const sevOf = (s) => (["low", "medium", "high"].includes(s) ? s : "medium");

  function fmtDate(iso) {
    try {
      const d = new Date(iso);
      if (isNaN(d)) return String(iso || "");
      return d.toLocaleString(MT.getLang() === "sw" ? "sw-KE" : "en-GB", { dateStyle: "medium", timeStyle: "short" });
    } catch { return String(iso || ""); }
  }

  function flash(msg) {
    const box = $("flash");
    box.textContent = msg;
    box.style.display = "block";
    clearTimeout(flashTimer);
    flashTimer = setTimeout(() => { box.style.display = "none"; }, 6000);
  }

  async function api(method, url, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(url, opts);
    } catch (e) {
      // The request never reached the server: no connection, or it dropped.
      const err = new Error("offline");
      err.code = "offline";
      err.network = true;
      throw err;
    }
    let data = {};
    try { data = await res.json(); } catch { /* non-JSON error page */ }
    if (!res.ok) {
      const err = new Error(data.error || `Request failed (${res.status})`);
      err.code = data.code;
      err.status = res.status;
      throw err;
    }
    return data;
  }

  // Server error codes are translated here; the server's English text is the fallback.
  function errMsg(e) {
    const key = "err_" + (e && e.code ? e.code : "");
    const tr = t(key);
    return tr !== key ? tr : (e && e.message) || t("errGeneric");
  }

  // ── Views ──
  function showView(name) {
    if ((name === "history" || name === "clinician") && !me) name = "auth";
    if (name === "clinician" && me && me.role !== "clinician") name = "home";
    view = name;
    [["homeView", "home"], ["authCard", "auth"], ["historyCard", "history"], ["clinCard", "clinician"], ["emergencyCard", "emergency"]]
      .forEach(([id, v]) => { $(id).style.display = v === name ? "block" : "none"; });
    if (name === "auth") renderAuth();
    if (name === "history") loadHistory(true);
    if (name === "clinician") loadClinician(true);
    window.scrollTo({ top: 0 });
  }

  MT.showView = showView;
  MT.flash = flash;

  async function wipeAll() { if (MT.offline) await MT.offline.wipeAll(); }

  function renderAccountBar() {
    const bar = $("accountBar");
    if (!me) {
      bar.innerHTML = `<button class="hdr-btn" type="button" data-nav="auth">${esc(t("acct_signin"))}</button>`;
      return;
    }
    bar.innerHTML =
      `<span class="hdr-name">${esc(me.name)}</span>` +
      (me.offlineSession ? `<span class="hdr-offline">${esc(t("off_offline_user"))}</span>` : "") +
      `<button class="hdr-btn" type="button" data-nav="history">${esc(t("acct_history"))}</button>` +
      (me.role === "clinician" && !me.offlineSession
        ? `<button class="hdr-btn" type="button" data-nav="clinician">${esc(t("acct_clinician"))}</button>` : "") +
      `<button class="hdr-btn" type="button" data-nav="signout">${esc(t("acct_signout"))}</button>`;
  }

  $("accountBar").addEventListener("click", (e) => {
    const b = e.target.closest("[data-nav]");
    if (!b) return;
    if (b.dataset.nav === "signout") signOut();
    else showView(b.dataset.nav);
  });
  const goHome = () => showView("home");
  $("homeLink").addEventListener("click", goHome);
  $("homeLink").addEventListener("keydown", (e) => { if (e.key === "Enter") goHome(); });
  ["authBack", "histBack", "clinBack"].forEach((id) => $(id).addEventListener("click", goHome));

  async function signOut() {
    try {
      await api("POST", "/api/auth/logout", {});
    } catch (err) {
      if (err.network) { flash(t("off_signout_needs_online")); return; } // still signed in on the server: do not pretend otherwise
      /* any other error: sign out on this device anyway */
    }
    await wipeAll();
    forgetUser();
    showView("home");
  }

  function forgetUser() {
    me = null;
    saveInfo = null;
    hist.items = []; hist.details = {}; hist.open = new Set(); hist.total = 0; hist.trend = null; hist.offline = false; hist.needsOnline = false;
    clin.items = []; clin.open = null; clin.detail = null; clin.total = 0;
    renderAccountBar();
    MT.rerender();
  }

  // ── Sign in / register ──
  function renderAuth() {
    const reg = authMode === "register";
    $("authTitle").textContent = t(reg ? "auth_title_register" : "auth_title_signin");
    $("authNameRow").style.display = reg ? "block" : "none";
    $("authPwHint").style.display = reg ? "block" : "none";
    $("authSubmit").textContent = t(reg ? "auth_submit_register" : "auth_submit_signin");
    $("authPassword").autocomplete = reg ? "new-password" : "current-password";
    document.querySelectorAll("[data-auth-tab]").forEach((b) => b.classList.toggle("on", b.dataset.authTab === authMode));
  }

  document.querySelectorAll("[data-auth-tab]").forEach((b) => {
    b.addEventListener("click", () => {
      authMode = b.dataset.authTab;
      $("authErr").style.display = "none";
      renderAuth();
    });
  });

  $("authForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const reg = authMode === "register";
    const body = { email: $("authEmail").value.trim(), password: $("authPassword").value };
    if (reg) body.name = $("authName").value.trim();
    $("authErr").style.display = "none";
    $("authSubmit").disabled = true;
    $("authSubmit").textContent = t("auth_working");
    try {
      const data = await api("POST", reg ? "/api/auth/register" : "/api/auth/login", body);
      me = data.user;
      if (MT.offline) MT.offline.rememberUser(me); // so the app can reopen offline as this user
      $("authPassword").value = "";
      renderAccountBar();
      await claimPending();
      showView("home");
    } catch (err) {
      $("authErr").textContent = `⚠️ ${errMsg(err)}`;
      $("authErr").style.display = "block";
    } finally {
      $("authSubmit").disabled = false;
      renderAuth();
    }
  });

  // A guest who finishes an assessment and then signs in keeps the result.
  async function claimPending() {
    if (!saveInfo || !saveInfo.claim || saveInfo.saved) return;
    try {
      const d = await api("POST", "/api/history/claim", { token: saveInfo.claim });
      saveInfo = { ...saveInfo, saved: true, id: d.assessmentId, trend: d.trend, claim: null, failed: false };
    } catch {
      saveInfo = { ...saveInfo, claim: null, failed: true };
    }
    MT.rerender();
  }

  // ── The note under a finished assessment ──
  hooks.assessment.push((data) => {
    saveInfo = {
      saved: !!data.saved,
      id: data.assessmentId || null,
      shared: false,
      trend: data.trend || null,
      claim: data.claimToken || null,
      failed: data.saved === false,
    };
  });
  hooks.reset.push(() => { saveInfo = null; });
  hooks.afterRender.push(renderSaveNote);

  function renderSaveNote() {
    const box = $("saveNote");
    if (!box) return;
    if (!saveInfo) { box.innerHTML = ""; return; }
    let h = "";
    const tr = saveInfo.trend;
    if (tr && tr.notice) h += trendHtml(tr);
    if (saveInfo.saved) {
      h += `<div class="save-note"><div class="save-row"><span>${esc(t("save_saved"))}</span>
        <button type="button" class="qtag" data-save="share">${esc(t(saveInfo.shared ? "save_unshare" : "save_share"))}</button>
        <button type="button" class="qtag" data-save="delete">${esc(t("save_delete"))}</button></div>
        ${saveInfo.shared ? `<div class="fac-foot">${esc(t("save_shared_note"))}</div>` : ""}</div>`;
    } else if (saveInfo.failed) {
      h += `<div class="save-note bad">${esc(t("save_failed"))}</div>`;
    } else if (!me && saveInfo.claim) {
      h += `<div class="save-note"><span>${esc(t("save_guest"))}</span>
        <button type="button" class="qtag" data-save="signin">${esc(t("acct_signin"))}</button></div>`;
    }
    box.innerHTML = h;
  }

  const trendHtml = (tr) =>
    `<div class="trend-note">📈 ${esc(fmt(t("trend_notice"), { n: tr.count, d: tr.days }))}</div>`;

  $("resultsCard").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-save]");
    if (!b || !saveInfo) return;
    const act = b.dataset.save;
    try {
      if (act === "signin") {
        authMode = "signin";
        showView("auth");
      } else if (act === "share" && saveInfo.id) {
        const d = await api("POST", `/api/history/${saveInfo.id}/share`, { shared: !saveInfo.shared });
        saveInfo.shared = d.shared;
        renderSaveNote();
      } else if (act === "delete" && saveInfo.id) {
        if (!window.confirm(t("hist_confirm_delete"))) return;
        await api("DELETE", `/api/history/${saveInfo.id}`);
        hist.items = hist.items.filter((i) => i.id !== saveInfo.id);
        saveInfo = { ...saveInfo, saved: false, id: null, trend: null, failed: false };
        renderSaveNote();
        flash(t("save_deleted"));
      }
    } catch (err) {
      flash(errMsg(err));
    }
  });

  // ── Shared rendering of one saved assessment ──
  function detailHtml(d) {
    if (!d) return `<div class="fac-status">${esc(t("hist_loading"))}</div>`;
    const likeCls = { high: "lh", medium: "lm", low: "ll" };
    const actIco = { urgent: "🚨", soon: "📅", self: "🏠" };
    const like = (l) => { const x = t("like_" + l); return x.startsWith("like_") ? l : x; };
    const flags = (d.redFlags || []).length
      ? `<div class="redflags">⚠️ ${esc(t("redFlags"))}<ul>${d.redFlags.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></div>` : "";
    const conds = (d.conditions || []).map((c, i) => `
      <div class="cond"><div class="cond-n">${i + 1}</div>
        <div><div class="cond-name">${esc(c.name)}</div><div class="cond-desc">${esc(c.description)}</div></div>
        <div class="cond-like ${likeCls[c.likelihood] || "lm"}">${esc(like(c.likelihood))}</div></div>`).join("");
    const acts = (d.actions || []).map((a) =>
      `<div class="act a-${["urgent", "soon", "self"].includes(a.type) ? a.type : "self"}">${actIco[a.type] || "•"} ${esc(a.text)}</div>`).join("");
    const convo = (d.transcript || []).map((m) =>
      `<div class="bubble ${m.from === "user" ? "user" : "model"} small">${esc(m.text)}</div>`).join("");
    const note = d.clinicianNote
      ? `<div class="clin-note"><b>${esc(t("hist_note"))}</b><div>${esc(d.clinicianNote)}</div></div>` : "";
    return `${flags}
      <div class="sec">${esc(t("secConditions"))}</div>${conds}
      <div class="sec">${esc(t("secActions"))}</div>${acts}
      ${note}
      <div class="sec">${esc(t("hist_conversation"))}</div><div class="chat-log">${convo}</div>`;
  }

  // ── History ──
  // Optional, per device: keep a copy of the signed-in patient's history so it can be read offline.
  const optedIn = () => !!(MT.offline && me && MT.offline.enabledFor(me.id));
  const canSaveCopy = () => optedIn() && !me.offlineSession && !hist.offline;
  let prefetchRun = 0;

  async function saveOfflineCopy() {
    if (!canSaveCopy()) return;
    try { await MT.offline.save(me.id, { items: hist.items, total: hist.total, trend: hist.trend, details: hist.details }); }
    catch { /* storage full or unavailable: the copy is a convenience */ }
  }

  async function prefetchDetails() {
    if (!canSaveCopy()) return;
    const run = ++prefetchRun;
    for (const it of hist.items.slice(0, 20)) {
      if (run !== prefetchRun || !canSaveCopy()) return; // superseded, or the option was turned off meanwhile
      if (hist.details[it.id]) continue;
      try { hist.details[it.id] = await api("GET", `/api/history/${it.id}`); }
      catch (err) { if (err.network) break; }
    }
    if (run === prefetchRun) await saveOfflineCopy();
  }

  async function loadHistoryOffline() {
    const rec = optedIn() ? await MT.offline.load(me.id) : null;
    if (!rec) { hist.needsOnline = true; return; }
    hist.items = rec.items || [];
    hist.total = hist.items.length;
    hist.trend = rec.trend || null;
    hist.details = rec.details || {};
    hist.offline = true;
    hist.savedAt = rec.savedAt;
  }

  async function loadHistory(reset) {
    if (!me) return;
    if (reset) { hist.items = []; hist.open = new Set(); hist.details = {}; hist.total = 0; hist.trend = null; hist.offline = false; hist.savedAt = null; }
    hist.loading = true; hist.error = false; hist.needsOnline = false;
    renderHistory();
    try {
      const d = await api("GET", `/api/history?limit=20&offset=${hist.items.length}`);
      hist.items = hist.items.concat(d.items);
      hist.total = d.total;
      hist.trend = d.trend;
      hist.offline = false;
      await saveOfflineCopy();   // does nothing unless the patient turned the option on
      prefetchDetails();
    } catch (err) {
      if (err.network) await loadHistoryOffline(); else hist.error = true;
    }
    hist.loading = false;
    renderHistory();
  }

  $("offlineToggle").addEventListener("change", async (e) => {
    if (!MT.offline || !me) return;
    if (e.target.checked) {
      if (me.offlineSession) { e.target.checked = false; flash(t("err_offline")); return; } // needs the server to fetch the history
      MT.offline.enable(me.id);
      await saveOfflineCopy();
      prefetchDetails();
    } else {
      prefetchRun++;               // stop any copy still being made
      await MT.offline.disable();  // deletes what is stored on this device
    }
    renderHistory();
  });

  function histItemHtml(it) {
    const sev = sevOf(it.severity);
    const chips = [it.shared ? t("hist_shared") : "", it.reviewStatus === "reviewed" && it.shared ? t("hist_reviewed") : ""]
      .filter(Boolean).map((c) => `<span class="chip">${esc(c)}</span>`).join("");
    let detail = "";
    if (hist.open.has(it.id)) {
      const d = hist.details[it.id];
      detail = `<div class="hist-detail">${detailHtml(d)}${d ? `
        <div class="save-row">
          <button type="button" class="qtag" data-act="share" data-id="${it.id}">${esc(t(it.shared ? "save_unshare" : "save_share"))}</button>
          <button type="button" class="qtag" data-act="delete" data-id="${it.id}">${esc(t("save_delete"))}</button>
        </div>${it.shared ? `<div class="fac-foot">${esc(t("save_shared_note"))}</div>` : ""}` : ""}</div>`;
    }
    return `<div class="hist-item" data-id="${it.id}">
      <div class="hist-row" data-toggle="${it.id}" role="button" tabindex="0">
        <span class="badge b-${sev}">${esc(t("sev_" + sev))}</span>
        <span class="hist-date">${esc(fmtDate(it.createdAt))}</span>${chips}
      </div>
      <div class="hist-summary">${esc(it.summary)}</div>
      ${it.topConditions && it.topConditions.length ? `<div class="hist-conds">${esc(it.topConditions.join(" · "))}</div>` : ""}
      ${detail}
    </div>`;
  }

  function renderHistory() {
    $("histStatus").textContent = hist.loading ? t("hist_loading")
      : hist.needsOnline ? t("off_history_needs_online")
      : hist.error ? t("hist_failed")
      : !hist.items.length ? t("hist_empty") : "";
    const banner = $("histOffline");
    banner.style.display = hist.offline ? "block" : "none";
    if (hist.offline) banner.textContent = fmt(t("off_banner"), { date: MT.fmtDate(hist.savedAt) });
    $("offlineOpt").style.display = MT.offline && MT.offline.supported() && me ? "flex" : "none";
    $("offlineToggle").checked = optedIn();
    $("histTrend").innerHTML = hist.trend && hist.trend.notice ? trendHtml(hist.trend) : "";
    $("histList").innerHTML = hist.items.map(histItemHtml).join("");
    $("histMore").style.display = !hist.offline && hist.items.length < hist.total ? "flex" : "none";
  }

  $("histMore").addEventListener("click", () => loadHistory(false));

  async function toggleHistory(id) {
    if (hist.open.has(id)) { hist.open.delete(id); renderHistory(); return; }
    hist.open.add(id);
    renderHistory();
    if (!hist.details[id]) {
      try { hist.details[id] = await api("GET", `/api/history/${id}`); }
      catch (err) { hist.open.delete(id); flash(errMsg(err)); }
      renderHistory();
    }
  }

  $("histList").addEventListener("click", async (e) => {
    const act = e.target.closest("[data-act]");
    if (act) {
      const id = Number(act.dataset.id);
      const item = hist.items.find((i) => i.id === id);
      if (!item) return;
      try {
        if (act.dataset.act === "share") {
          const d = await api("POST", `/api/history/${id}/share`, { shared: !item.shared });
          item.shared = d.shared;
          if (saveInfo && saveInfo.id === id) saveInfo.shared = d.shared;
        } else if (act.dataset.act === "delete") {
          if (!window.confirm(t("hist_confirm_delete"))) return;
          await api("DELETE", `/api/history/${id}`);
          hist.items = hist.items.filter((i) => i.id !== id);
          hist.total = Math.max(0, hist.total - 1);
          delete hist.details[id];
          hist.open.delete(id);
          if (saveInfo && saveInfo.id === id) { saveInfo = { ...saveInfo, saved: false, id: null, trend: null }; MT.rerender(); }
        }
      } catch (err) { flash(errMsg(err)); }
      renderHistory();
      saveOfflineCopy();   // keep the stored copy in step with shares and deletions made online
      return;
    }
    const row = e.target.closest("[data-toggle]");
    if (row) toggleHistory(Number(row.dataset.toggle));
  });
  $("histList").addEventListener("keydown", (e) => {
    const row = e.target.closest("[data-toggle]");
    if (row && e.key === "Enter") toggleHistory(Number(row.dataset.toggle));
  });

  $("delBtn").addEventListener("click", async () => {
    const pw = $("delPassword").value;
    if (!pw) return;
    if (!window.confirm(t("acct_delete_confirm"))) return;
    try {
      await api("POST", "/api/account/delete", { password: pw });
      $("delPassword").value = "";
      await wipeAll();
      forgetUser();
      showView("home");
      flash(t("acct_deleted"));
    } catch (err) { flash(errMsg(err)); }
  });

  // ── Clinician queue ──
  async function loadClinician(reset) {
    if (!me || me.role !== "clinician") return;
    if (reset) { clin.items = []; clin.total = 0; clin.open = null; clin.detail = null; }
    clin.loading = true; clin.error = false;
    renderClinician();
    try {
      const d = await api("GET", `/api/clinician/queue?status=${encodeURIComponent(clin.status)}&limit=30&offset=${clin.items.length}`);
      clin.items = clin.items.concat(d.items);
      clin.total = d.total;
    } catch (err) { clin.error = true; clin.offline = !!(err && err.network); }
    clin.loading = false;
    renderClinician();
  }

  function clinItemHtml(it) {
    const sev = sevOf(it.severity);
    const open = clin.open === it.id;
    let detail = "";
    if (open) {
      const d = clin.detail && clin.detail.id === it.id ? clin.detail : null;
      detail = `<div class="hist-detail">${detailHtml(d)}${d ? `
        <label class="file-label" for="clinNote">${esc(t("clin_note_label"))}</label>
        <textarea id="clinNote" rows="3" maxlength="1000">${esc(d.clinicianNote || "")}</textarea>
        <button class="go-btn" type="button" data-clin="review" data-id="${it.id}">${esc(t("clin_mark"))}</button>` : ""}</div>`;
    }
    return `<div class="hist-item" data-id="${it.id}">
      <div class="hist-row" data-toggle="${it.id}" role="button" tabindex="0">
        <span class="badge b-${sev}">${esc(t("sev_" + sev))}</span>
        <strong>${esc(it.patientName || "")}</strong>
        <span class="hist-date">${esc(fmtDate(it.createdAt))}</span>
        ${it.reviewStatus === "reviewed" ? `<span class="chip">${esc(t("hist_reviewed"))}</span>` : ""}
      </div>
      <div class="hist-summary">${esc(it.summary)}</div>
      ${it.topConditions && it.topConditions.length ? `<div class="hist-conds">${esc(it.topConditions.join(" · "))}</div>` : ""}
      ${detail}
    </div>`;
  }

  function renderClinician() {
    $("clinFilters").innerHTML = ["new", "reviewed", "all"]
      .map((k) => `<button type="button" class="qtag${clin.status === k ? " on" : ""}" data-clin-filter="${k}">${esc(t("clin_filter_" + k))}</button>`)
      .join("");
    $("clinStatus").textContent = clin.loading ? t("hist_loading")
      : clin.error ? t(clin.offline ? "err_offline" : "clin_failed")
      : !clin.items.length ? t("clin_empty") : "";
    $("clinList").innerHTML = clin.items.map(clinItemHtml).join("");
    $("clinMore").style.display = clin.items.length < clin.total ? "flex" : "none";
  }

  $("clinMore").addEventListener("click", () => loadClinician(false));
  $("clinFilters").addEventListener("click", (e) => {
    const b = e.target.closest("[data-clin-filter]");
    if (!b) return;
    clin.status = b.dataset.clinFilter;
    loadClinician(true);
  });

  async function toggleClinician(id) {
    if (clin.open === id) { clin.open = null; clin.detail = null; renderClinician(); return; }
    clin.open = id; clin.detail = null;
    renderClinician();
    try {
      const d = await api("GET", `/api/clinician/assessments/${id}`);
      if (clin.open === id) clin.detail = d;
    } catch (err) { clin.open = null; flash(errMsg(err)); }
    renderClinician();
  }

  $("clinList").addEventListener("click", async (e) => {
    const review = e.target.closest("[data-clin='review']");
    if (review) {
      const id = Number(review.dataset.id);
      try {
        await api("POST", `/api/clinician/assessments/${id}/review`, { note: $("clinNote").value });
        flash(t("clin_saved"));
        if (clin.status === "new") {
          clin.items = clin.items.filter((i) => i.id !== id);
          clin.total = Math.max(0, clin.total - 1);
          clin.open = null; clin.detail = null;
        } else {
          const it = clin.items.find((i) => i.id === id);
          if (it) it.reviewStatus = "reviewed";
        }
      } catch (err) { flash(errMsg(err)); }
      renderClinician();
      return;
    }
    const row = e.target.closest("[data-toggle]");
    if (row) toggleClinician(Number(row.dataset.toggle));
  });
  $("clinList").addEventListener("keydown", (e) => {
    const row = e.target.closest("[data-toggle]");
    if (row && e.key === "Enter") toggleClinician(Number(row.dataset.toggle));
  });

  // ── Language changes: redraw whatever is on screen ──
  hooks.lang.push(() => {
    renderAccountBar();
    renderAuth();
    if (view === "history") renderHistory();
    if (view === "clinician") renderClinician();
  });

  $("emergNav").addEventListener("click", () => showView("emergency"));
  $("emergBack").addEventListener("click", goHome);

  // ── Start ──
  MT.refresh(); // apply the strings added above to the static markup
  // The "Emergency signs" home-screen shortcut opens /?view=emergency
  if (new URLSearchParams(window.location.search).get("view") === "emergency") showView("emergency");
  api("GET", "/api/auth/me")
    .then((d) => {
      me = d.user;
      if (MT.offline) {
        if (me) MT.offline.rememberUser(me);
        else MT.offline.wipeAccountData(); // the server says nobody is signed in: drop any account data kept here
      }
    })
    .catch((err) => {
      // Offline: carry on read-only as the last signed-in user, or as a guest.
      const last = err.network && MT.offline ? MT.offline.lastUser() : null;
      me = last ? { ...last, offlineSession: true } : null;
    })
    .finally(() => { renderAccountBar(); });
})();

// ==========================================================================
// PART 3: INSTALLABLE APP AND OFFLINE USE
// Install button, offline banner, service worker, emergency-signs card.
// ==========================================================================
(() => {
  // Installable app and offline use (Phase 5). Uses window.MT from part 1.
  if (!window.MT) return;
  const MT = window.MT;
  const { t, esc } = MT;
  const $ = (id) => document.getElementById(id);

  // <i18n>
  // The emergency-signs text is general safety information, not a diagnosis. A clinician should review
  // it, and the Kiswahili, before real use.
  const STRINGS = {
    en: {
      update_msg: "A new version is available.", update_btn: "Update",
      install_btn: "Install app",
      install_ios: "To install: tap the Share button, then Add to Home Screen.",
      net_offline: "You are offline. Assessments and sign-in need the internet. Emergency signs still work.",
      net_online: "Back online.",
      errOffline: "You are offline, so MediTECH AI cannot assess symptoms right now. Your message is kept. If this could be an emergency, call 999 or 112 or go to the nearest health facility now. Emergency signs are available offline.",
      err_offline: "You are offline. Please try again when you are connected.",
      acct_emergency: "Emergency signs",
      em_title: "When to get emergency help now",
      em_intro: "If you or someone with you has any of these signs, call 999 or 112, or go to the nearest hospital now. Do not wait to see if it improves.",
      em_call_999: "Call 999", em_call_112: "Call 112",
      em_note: "Tell them exactly where you are, and stay with the person until help arrives. This list is general information and does not replace medical care. MediTECH AI is not an emergency service. This page works without internet.",
      em1_t: "Stroke",
      em1_d: "Face drooping on one side, weakness or numbness in an arm or leg, slurred or confused speech, sudden loss of vision, or a sudden severe headache.",
      em2_t: "Heart attack",
      em2_d: "Pressure, tightness or squeezing pain in the chest that lasts more than a few minutes or comes and goes, spreading to the arm, jaw, neck or back, with sweating, nausea or breathlessness.",
      em3_t: "Trouble breathing",
      em3_d: "Cannot catch breath at rest, cannot speak in full sentences, blue or grey lips, or struggling for air.",
      em4_t: "Severe allergic reaction",
      em4_d: "Swelling of the face, lips or throat, difficulty breathing or dizziness soon after a sting, food or medicine.",
      em5_t: "Meningitis or sepsis",
      em5_d: "Fever with a stiff neck, severe headache, confusion or unusual sleepiness, or a rash that does not fade when a clear glass is pressed on it. Also cold, blotchy skin with a very fast heartbeat and confusion.",
      em6_t: "Heavy bleeding",
      em6_d: "Bleeding that does not stop after firm pressure, or bleeding with faintness.",
      em7_t: "Collapse or fits",
      em7_d: "Someone who has collapsed, does not respond when spoken to or shaken gently, or has a fit that does not stop or keeps returning.",
      em8_t: "Babies and young children",
      em8_d: "Not feeding or drinking, very sleepy, floppy or hard to wake, a bulging soft spot on the head, fits, fast or difficult breathing, or no urine for 12 hours, especially with fever.",
      em9_t: "Severe belly pain",
      em9_d: "Pain that keeps getting worse, a hard or rigid belly, pain that is much worse with movement or coughing, or pain with repeated vomiting.",
      em10_t: "Pregnancy",
      em10_d: "Heavy bleeding, severe headache with blurred vision, fits, severe belly pain, fever, or the baby moving much less than usual.",
      facCachedNow: "Showing the list saved on {date} because the live search is not available. Distances are measured from your current position. It may be out of date.",
      facCachedOld: "Showing the list saved on {date} because the live search is not available. Distances were measured from where you searched, and the list may be out of date.",
      facNoCache: "You are offline and no facility list is saved on this device yet. Search once while online to save one.",
      fac_forget: "Remove the saved list from this device",
      fac_forgotten: "The saved facility list was removed from this device.",
      off_toggle: "Keep a copy of my history on this device for offline reading",
      off_help: "Anyone who can open this app on this device while you are signed in could read the copy. It is removed when you turn this off, sign out or delete your account.",
      off_banner: "You are reading the copy saved on {date}. It may be out of date.",
      off_history_needs_online: "Your history is not saved on this device. Connect to the internet to see it.",
      off_signout_needs_online: "You need to be online to sign out. To remove the offline copy now, turn off the option to keep a copy of your history on this device.",
      off_offline_user: "(offline)",
    },
    sw: {
      update_msg: "Toleo jipya linapatikana.", update_btn: "Sasisha",
      install_btn: "Sakinisha programu",
      install_ios: "Ili kusakinisha: gusa kitufe cha Shiriki, kisha Ongeza kwenye Skrini ya Kwanza.",
      net_offline: "Huna mtandao. Tathmini na kuingia vinahitaji intaneti. Dalili za dharura bado zinafanya kazi.",
      net_online: "Mtandao umerudi.",
      errOffline: "Huna mtandao, kwa hiyo MediTECH AI haiwezi kutathmini dalili sasa hivi. Ujumbe wako umehifadhiwa. Ikiwa hii inaweza kuwa dharura, piga 999 au 112 au nenda kituo cha afya kilicho karibu sasa. Dalili za dharura zinapatikana bila mtandao.",
      err_offline: "Huna mtandao. Tafadhali jaribu tena ukiwa na mtandao.",
      acct_emergency: "Dalili za dharura",
      em_title: "Wakati wa kupata msaada wa dharura sasa",
      em_intro: "Ikiwa wewe au mtu aliye nawe ana dalili yoyote kati ya hizi, piga 999 au 112, au nenda hospitali iliyo karibu sasa. Usisubiri kuona kama itapungua.",
      em_call_999: "Piga 999", em_call_112: "Piga 112",
      em_note: "Waambie mahali ulipo hasa, na ubaki na mgonjwa hadi msaada ufike. Orodha hii ni taarifa ya jumla na haichukui nafasi ya huduma ya matibabu. MediTECH AI si huduma ya dharura. Ukurasa huu unafanya kazi bila intaneti.",
      em1_t: "Kiharusi",
      em1_d: "Uso kupinda upande mmoja, udhaifu au ganzi kwenye mkono au mguu, kuongea kwa kukwama au kuchanganyikiwa, kupoteza uwezo wa kuona ghafla, au maumivu makali ya kichwa ya ghafla.",
      em2_t: "Shambulio la moyo",
      em2_d: "Shinikizo, kubana au maumivu ya kukamua kifuani yanayodumu zaidi ya dakika chache au yanayokuja na kwenda, yakisambaa hadi mkono, taya, shingo au mgongo, pamoja na jasho, kichefuchefu au kukosa pumzi.",
      em3_t: "Shida ya kupumua",
      em3_d: "Kushindwa kupata pumzi ukiwa umepumzika, kushindwa kuongea sentensi kamili, midomo ya samawati au kijivu, au kuhangaika kupata hewa.",
      em4_t: "Mzio mkali",
      em4_d: "Uvimbe wa uso, midomo au koo, shida ya kupumua au kizunguzungu muda mfupi baada ya kuumwa na mdudu, kula chakula au kutumia dawa.",
      em5_t: "Uti wa mgongo wa ubongo (meninjaitis) au sepsis",
      em5_d: "Homa pamoja na shingo ngumu, maumivu makali ya kichwa, kuchanganyikiwa au usingizi usio wa kawaida, au vipele visivyofifia unapobonyeza kioo safi juu yake. Pia ngozi baridi yenye madoa na mapigo ya moyo ya haraka sana na kuchanganyikiwa.",
      em6_t: "Kutoka damu nyingi",
      em6_d: "Damu inayotoka na haikomi baada ya kubonyeza kwa nguvu, au kutoka damu pamoja na kuhisi kuzimia.",
      em7_t: "Kuanguka au kifafa",
      em7_d: "Mtu ambaye ameanguka, hajibu akiitwa au kutikiswa taratibu, au ana kifafa kisichokoma au kinachorudi mara kwa mara.",
      em8_t: "Watoto wachanga na wadogo",
      em8_d: "Hanyonyi au hanywi, usingizi mwingi, mwili legevu au vigumu kuamka, utosi unaovimba, kifafa, kupumua haraka au kwa shida, au kutokojoa kwa saa 12, hasa pamoja na homa.",
      em9_t: "Maumivu makali ya tumbo",
      em9_d: "Maumivu yanayozidi kuongezeka, tumbo gumu au lililokaza, maumivu yanayozidi sana unaposogea au kukohoa, au maumivu pamoja na kutapika mara kwa mara.",
      em10_t: "Ujauzito",
      em10_d: "Kutoka damu nyingi, maumivu makali ya kichwa pamoja na kutoona vizuri, kifafa, maumivu makali ya tumbo, homa, au mtoto kucheza kidogo sana kuliko kawaida.",
      facCachedNow: "Inaonyesha orodha iliyohifadhiwa tarehe {date} kwa sababu utafutaji wa moja kwa moja haupatikani. Umbali umepimwa kutoka mahali ulipo sasa. Inaweza kuwa imepitwa na wakati.",
      facCachedOld: "Inaonyesha orodha iliyohifadhiwa tarehe {date} kwa sababu utafutaji wa moja kwa moja haupatikani. Umbali ulipimwa kutoka ulipotafutia, na orodha inaweza kuwa imepitwa na wakati.",
      facNoCache: "Huna mtandao na hakuna orodha ya vituo iliyohifadhiwa kwenye kifaa hiki bado. Tafuta mara moja ukiwa na mtandao ili kuhifadhi moja.",
      fac_forget: "Ondoa orodha iliyohifadhiwa kwenye kifaa hiki",
      fac_forgotten: "Orodha ya vituo iliyohifadhiwa imeondolewa kwenye kifaa hiki.",
      off_toggle: "Hifadhi nakala ya historia yangu kwenye kifaa hiki ili niisome bila mtandao",
      off_help: "Mtu yeyote anayeweza kufungua programu hii kwenye kifaa hiki ukiwa umeingia anaweza kusoma nakala hiyo. Huondolewa ukizima hii, ukitoka au ukifuta akaunti yako.",
      off_banner: "Unasoma nakala iliyohifadhiwa tarehe {date}. Inaweza kuwa imepitwa na wakati.",
      off_history_needs_online: "Historia yako haijahifadhiwa kwenye kifaa hiki. Unganisha intaneti ili kuiona.",
      off_signout_needs_online: "Unahitaji mtandao ili kutoka. Ili kuondoa nakala ya nje ya mtandao sasa, zima chaguo la kuhifadhi nakala ya historia yako kwenye kifaa hiki.",
      off_offline_user: "(bila mtandao)",
    },
  };
  // </i18n>
  MT.addStrings(STRINGS);
  if (!MT.reload) MT.reload = () => window.location.reload();

  let flashTimer = null;
  function flash(msg) {
    const box = $("flash");
    if (!box) return;
    box.textContent = msg;
    box.style.display = "block";
    clearTimeout(flashTimer);
    flashTimer = setTimeout(() => { box.style.display = "none"; }, 6000);
  }

  // ───────────── On-device store for the opt-in offline history ─────────────
  // Nothing here is used unless the patient ticks "Keep a copy of my history on this device". The copy lives
  // in this browser's IndexedDB, is removed when the option is turned off, when the patient signs out or
  // deletes the account, and whenever the server says nobody is signed in. Only the signed-in user's own
  // assessments are stored: never a password, and not the email address.
  const ls = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* unavailable */ } },
    del(k) { try { localStorage.removeItem(k); } catch { /* unavailable */ } },
  };
  const OPT_KEY = "meditech_offline_user";    // which user turned the option on, on this device
  const LAST_USER_KEY = "meditech_last_user"; // {id, name, role} so the app can open offline
  const DB_NAME = "meditech-offline", STORE = "history";

  function openDb() {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB) { reject(new Error("IndexedDB is not available")); return; }
      let req;
      try { req = window.indexedDB.open(DB_NAME, 1); } catch (e) { reject(e); return; }
      req.onupgradeneeded = () => {
        if (!req.result.objectStoreNames.contains(STORE)) req.result.createObjectStore(STORE, { keyPath: "userId" });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function run(mode, fn) {
    const db = await openDb();
    try {
      return await new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const request = fn(tx.objectStore(STORE));
        tx.oncomplete = () => resolve(request ? request.result : undefined);
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error);
      });
    } finally {
      db.close();
    }
  }

  MT.offline = {
    supported: () => !!window.indexedDB,
    enabledFor: (userId) => ls.get(OPT_KEY) === String(userId),
    enable: (userId) => ls.set(OPT_KEY, String(userId)),
    async disable() {
      ls.del(OPT_KEY);
      try { await run("readwrite", (s) => s.clear()); } catch { /* nothing stored */ }
    },
    async save(userId, data) {
      await run("readwrite", (s) => s.put({ userId, savedAt: new Date().toISOString(), ...data }));
    },
    async load(userId) {
      try { return (await run("readonly", (s) => s.get(userId))) || null; } catch { return null; }
    },
    rememberUser(u) { ls.set(LAST_USER_KEY, JSON.stringify({ id: u.id, name: u.name, role: u.role })); },
    lastUser() {
      try { const u = JSON.parse(ls.get(LAST_USER_KEY)); return u && u.id ? u : null; } catch { return null; }
    },
    // The server says nobody is signed in: remove everything tied to an account.
    async wipeAccountData() {
      ls.del(OPT_KEY); ls.del(LAST_USER_KEY);
      try { await run("readwrite", (s) => s.clear()); } catch { /* nothing stored */ }
    },
    // Explicit sign-out or account deletion: also forget the saved facility list.
    async wipeAll() {
      if (MT.forgetFacilities) MT.forgetFacilities(); else ls.del(MT.FAC_KEY);
      await this.wipeAccountData();
    },
  };

  // ───────────── Online / offline banner ─────────────
  // navigator.onLine is only a hint (it can be wrong), so nothing is blocked because of it: a send is
  // always attempted, and only a real network failure produces the offline message.
  let offlineNow = false, wasOffline = false, backTimer = null;

  function showNet(offline) {
    const b = $("netBanner");
    clearTimeout(backTimer);
    offlineNow = offline;
    document.body.classList.toggle("offline", offline);
    if (offline) {
      b.className = "net-banner";
      b.textContent = t("net_offline");
      b.style.display = "block";
    } else if (wasOffline) {
      b.className = "net-banner ok";
      b.textContent = t("net_online");
      b.style.display = "block";
      backTimer = setTimeout(() => { b.style.display = "none"; }, 3000);
    } else {
      b.style.display = "none";
    }
    wasOffline = offline;
  }
  window.addEventListener("offline", () => showNet(true));
  window.addEventListener("online", () => showNet(false));
  if (navigator.onLine === false) showNet(true);

  // ───────────── Service worker and updates ─────────────
  let waitingWorker = null, userAskedUpdate = false;

  function registerWorker() {
    if (!("serviceWorker" in navigator)) return;
    const local = ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname);
    if (!window.isSecureContext && !local) return; // browsers only allow service workers on https or localhost

    // The first install also fires "controllerchange" (the new worker takes over a page it did not control
    // before). Only reload when the patient clicked "Update".
    let reloading = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (!userAskedUpdate || reloading) return;
      reloading = true;
      MT.reload();
    });

    navigator.serviceWorker.register("/sw.js", { scope: "/" }).then((reg) => {
      const offerUpdate = (worker) => { waitingWorker = worker; $("updateBanner").style.display = "flex"; };
      if (reg.waiting && navigator.serviceWorker.controller) offerUpdate(reg.waiting);
      reg.addEventListener("updatefound", () => {
        const worker = reg.installing;
        if (!worker) return;
        worker.addEventListener("statechange", () => {
          if (worker.state === "installed" && navigator.serviceWorker.controller) offerUpdate(worker);
        });
      });
      const check = () => { try { Promise.resolve(reg.update()).catch(() => {}); } catch { /* ignore */ } };
      document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") check(); });
      setInterval(check, 60 * 60 * 1000);
    }).catch(() => { /* no service worker: the app still works online */ });
  }

  $("updateBtn").addEventListener("click", () => {
    userAskedUpdate = true;
    if (waitingWorker) waitingWorker.postMessage({ type: "SKIP_WAITING" });
  });

  // ───────────── Install button ─────────────
  let installEvent = null;
  const installBtn = $("installBtn");
  const standalone = () =>
    window.navigator.standalone === true || (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches);
  const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();          // keep the browser's own mini-bar away; we show our button instead
    installEvent = e;
    installBtn.style.display = "";
  });
  window.addEventListener("appinstalled", () => {
    installEvent = null;
    installBtn.style.display = "none";
  });
  installBtn.addEventListener("click", async () => {
    if (installEvent) {
      const ev = installEvent;
      installEvent = null;
      installBtn.style.display = "none";
      try { ev.prompt(); await ev.userChoice; } catch { /* dismissed */ }
    } else {
      flash(t("install_ios")); // iPhone and iPad have no install prompt
    }
  });
  if (isIOS() && !standalone()) installBtn.style.display = "";

  // ───────────── Emergency signs (part of the shell, so it works offline) ─────────────
  const EM_ITEMS = 10;
  function renderEmergency() {
    let html = "";
    for (let i = 1; i <= EM_ITEMS; i++) {
      html += `<div class="emerg-item"><b>${esc(t("em" + i + "_t"))}</b><span>${esc(t("em" + i + "_d"))}</span></div>`;
    }
    $("emergList").innerHTML = html;
  }

  MT.hooks.lang.push(() => {
    renderEmergency();
    if (offlineNow) $("netBanner").textContent = t("net_offline");
    else if (wasOffline && $("netBanner").style.display !== "none") $("netBanner").textContent = t("net_online");
  });

  // ───────────── Start ─────────────
  MT.refresh(); // apply the strings added above to the static markup
  renderEmergency();
  registerWorker();
})();
