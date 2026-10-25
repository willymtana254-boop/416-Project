(() => {
  // Installable app (Phase 5, bit 5a). Loaded after app.js and account.js.
  if (!window.MT) return;
  const MT = window.MT;
  const { t } = MT;
  const $ = (id) => document.getElementById(id);

  // <i18n>
  const STRINGS = {
    en: {
      update_msg: "A new version is available.", update_btn: "Update",
      install_btn: "Install app",
      install_ios: "To install: tap the Share button, then Add to Home Screen.",
    },
    sw: {
      update_msg: "Toleo jipya linapatikana.", update_btn: "Sasisha",
      install_btn: "Sakinisha programu",
      install_ios: "Ili kusakinisha: gusa kitufe cha Shiriki, kisha Ongeza kwenye Skrini ya Kwanza.",
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

  // ───────────── Start ─────────────
  MT.refresh(); // apply the strings added above to the static markup
  registerWorker();
})();
