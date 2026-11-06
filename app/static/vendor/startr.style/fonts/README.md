# Nunito Sans, served at `/fonts/`

The vendored startr.style sheet (`../1.5.0/style.css`) opens with upstream's `@import url('/fonts/Nunito-Sans.css')`. `main.py` mounts this folder at `/fonts`, so the import resolves on the box and no page load reaches startr.style or Google.

- `Nunito-Sans.css` and the ten `.woff2` subsets are byte-for-byte the files Startr/Style serves at `/fonts/`: `src/static/fonts/` at commit `f028648` (2025-03-02) of <https://github.com/Startr/Style>. The sheet's sha256 is pinned in `rootstock/tests/security/test_startr_style_pinned.py`.
- The faces are Google Fonts' Nunito Sans, variable weight 200–1000, normal and italic, in the latin, latin-ext, cyrillic, cyrillic-ext and vietnamese subsets. Copyright 2014 The Nunito Sans Project Authors (<https://github.com/googlefonts/NunitoSans>), licensed under the SIL Open Font License 1.1 (<https://openfontlicense.org>). The OFL permits bundling and redistribution; the fonts are not sold on their own.

To refresh, copy the same files from the Startr/Style checkout and update the pinned sha256 in the test.
