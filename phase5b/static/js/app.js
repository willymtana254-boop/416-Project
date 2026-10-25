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
  // Compared by name so it also works across browser frames. account.js marks its own with code "offline".
  const isNetworkError = (e) => !!e && (e.name === "TypeError" || e.code === "offline" || e.network === true);

  // Extension points for account.js (sign-in, saved history, clinician view).
  const hooks = { lang: [], assessment: [], afterRender: [], reset: [] };

  // ── State ──
  let history = [];          // Gemini-format conversation, resent every turn
  let imageB64 = null;       // {mimeType, data} | null
  let isFirstTurn = true;
  let loading = false;
  let lastAssessment = null; // {turn, sources}, kept so a language switch can re-render it
  const fac = { items: [], radiusKm: 0, filter: "all", status: "idle", errorMsg: "" };

  // ── DOM refs ──
  const $ = (id) => document.getElementById(id);
  const chatLog = $("chatLog"), textInput = $("textInput"), firstTurnExtras = $("firstTurnExtras");
  const bodyArea = $("bodyArea"), regionSelect = $("regionSelect"), imgFile = $("imgFile");
  const goBtn = $("goBtn"), inputCard = $("inputCard"), errBox = $("errBox"), resultsCard = $("resultsCard");
  const langSelect = $("langSelect");
  const locBtn = $("locBtn"), facFilters = $("facFilters"), facStatus = $("facStatus"), facList = $("facList");
  const facCard = $("facCard");

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

  facFilters.addEventListener("click", (e) => {
    const b = e.target.closest("[data-filter]");
    if (!b) return;
    fac.filter = b.dataset.filter;
    renderFacilities();
  });

  function findFacilities() {
    if (!navigator.geolocation) {
      fac.status = "error";
      fac.errorMsg = t("facNoGeo");
      renderFacilities();
      return;
    }
    fac.status = "loading";
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
          if (!res.ok) throw new Error(data.error || t("facError"));
          fac.items = data.facilities || [];
          fac.radiusKm = data.radiusKm;
          fac.status = "done";
        } catch (e) {
          fac.status = "error";
          fac.errorMsg = e.message || t("facError");
        }
        renderFacilities();
      },
      () => {
        fac.status = "denied";
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

  // ── Public surface for account.js ──
  window.MT = {
    t, esc, fmt, isNetworkError,
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
