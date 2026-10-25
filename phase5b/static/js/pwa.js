(() => {
  // Installable app and offline use (Phase 5). Loaded after app.js and account.js.
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
