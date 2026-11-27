# Giriama (nyf) and Kalenjin (kln)

`nyf.json` and `kln.json` hold the glossary and example replies that are added to the
model prompt for that language (read by `language_resources()` in `ai.py`).

1. With a native speaker, fill the `glossary` values. Leave a value empty if unsure.
2. Add real examples under `examples` (`patient` message and a good `assistant` reply).
3. Interface text: add translations to the `nyf` and `kln` blocks in `static/js/app.js`
   (same keys as `en` and `sw`). Missing keys show in Kiswahili, then English.
4. Set `KALENJIN_VARIETY` in `ai.py` once the variety is chosen (for example "Kipsigis").
5. Have a native-speaking clinician review outputs before removing the "beta" label.
