const fs = require("fs");
const R = "/home/claude/meditech-ai-py/"; const read = (f) => fs.readFileSync(R + f, "utf8");
const block = (js, name) => new Function(js.split("// <i18n>")[1].split("// </i18n>")[0] + `; return ${name};`)();
const appJs = read("static/js/app.js"), accJs = read("static/js/account.js"), pwaJs = read("static/js/pwa.js"), html = read("templates/index.html");
const A = block(appJs, "I18N"), S = block(accJs, "STRINGS"), P = block(pwaJs, "STRINGS");
const en = { ...A.en, ...S.en, ...P.en }, sw = { ...A.sw, ...S.sw, ...P.sw };
let n = 0; const ok = (c, m) => { if (!c) { console.log("FAIL:", m); process.exit(1); } n++; };
const missingSw = Object.keys(en).filter((k) => !(k in sw) && !k.startsWith("clin_")), extraSw = Object.keys(sw).filter((k) => !(k in en));
ok(!missingSw.length && !extraSw.length, "same keys in both languages " + JSON.stringify({ missingSw, extraSw }));
const dup = [...Object.keys(S.en).filter((k) => k in A.en), ...Object.keys(P.en).filter((k) => k in A.en || k in S.en)]; ok(!dup.length, "no key defined in two files: " + dup);
const used = new Set([...html.matchAll(/data-i18n(?:-placeholder)?="([^"]+)"/g)].map((m) => m[1]));
for (const src of [appJs, accJs, pwaJs]) for (const m of src.matchAll(/\bt(?:Or)?\("([^"]+)"\s*[,)]/g)) if (!m[1].endsWith("_")) used.add(m[1]);
for (const s of ["low", "medium", "high"]) { used.add("sev_" + s); used.add("like_" + s); }
for (const k of ["all", "hospital", "clinic", "pharmacy"]) used.add("filter_" + k);
for (const k of ["hospital", "clinic", "pharmacy"]) used.add("kind_" + k);
for (const k of ["new", "reviewed", "all"]) used.add("clin_filter_" + k);
for (let i = 1; i <= 10; i++) { used.add("em" + i + "_t"); used.add("em" + i + "_d"); }
const undef = [...used].filter((k) => !(k in en)); ok(!undef.length, "every key used is defined: " + undef);
for (const k of Object.keys(en)) { if (!(k in sw)) continue;
  ok((en[k].match(/\{\w+\}/g) || []).sort().join() === (sw[k].match(/\{\w+\}/g) || []).sort().join(), "placeholders in " + k); ok(en[k].trim() && sw[k].trim(), "empty " + k); }
const em = []; for (let i = 1; i <= 10; i++) for (const L of [en, sw]) em.push(L["em" + i + "_t"], L["em" + i + "_d"]);
ok(!em.some((x) => /paracetamol|ibuprofen|aspirin|antibiotic|painkiller|\bdose|\b\d+\s?mg\b|tablet|vidonge/i.test(x)), "emergency text names no medicine or dose");
console.log(`translations OK (${Object.keys(en).length} English keys, ${Object.keys(sw).length} Kiswahili keys)`);
