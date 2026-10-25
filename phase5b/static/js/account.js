(() => {
  // Accounts, saved history and the clinician queue (Phase 4). Loaded after
  // app.js, which exposes window.MT (translation helper and extension hooks).
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
  const hist = { items: [], total: 0, trend: null, open: new Set(), details: {}, loading: false, error: false };
  const clin = { status: "new", items: [], total: 0, open: null, detail: null, loading: false, error: false };

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

  function renderAccountBar() {
    const bar = $("accountBar");
    if (!me) {
      bar.innerHTML = `<button class="hdr-btn" type="button" data-nav="auth">${esc(t("acct_signin"))}</button>`;
      return;
    }
    bar.innerHTML =
      `<span class="hdr-name">${esc(me.name)}</span>` +
      `<button class="hdr-btn" type="button" data-nav="history">${esc(t("acct_history"))}</button>` +
      (me.role === "clinician"
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
    try { await api("POST", "/api/auth/logout", {}); } catch { /* signing out locally anyway */ }
    forgetUser();
    showView("home");
  }

  function forgetUser() {
    me = null;
    saveInfo = null;
    hist.items = []; hist.details = {}; hist.open = new Set(); hist.total = 0; hist.trend = null;
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
  async function loadHistory(reset) {
    if (!me) return;
    if (reset) { hist.items = []; hist.open = new Set(); hist.details = {}; hist.total = 0; hist.trend = null; }
    hist.loading = true; hist.error = false;
    renderHistory();
    try {
      const d = await api("GET", `/api/history?limit=20&offset=${hist.items.length}`);
      hist.items = hist.items.concat(d.items);
      hist.total = d.total;
      hist.trend = d.trend;
    } catch { hist.error = true; }
    hist.loading = false;
    renderHistory();
  }

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
      : hist.error ? t("hist_failed")
      : !hist.items.length ? t("hist_empty") : "";
    $("histTrend").innerHTML = hist.trend && hist.trend.notice ? trendHtml(hist.trend) : "";
    $("histList").innerHTML = hist.items.map(histItemHtml).join("");
    $("histMore").style.display = hist.items.length < hist.total ? "flex" : "none";
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
    } catch { clin.error = true; }
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
      : clin.error ? t("clin_failed")
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
    .then((d) => { me = d.user; })
    .catch(() => { me = null; })
    .finally(() => { renderAccountBar(); });
})();
