# og-card — the try.sage.is share image

`card.html` renders `app/static/assets/images/og-image.jpg`, the Open Graph and Twitter
card for the try.sage welcome page. It is a build-time source, not a served page.

## Why an HTML source instead of a static file

The card has to look like the page it previews. `card.html` lifts the look from
`sage_is_ai/pages/templates/try-sage.html` directly: the first slideshow image as
backdrop, the same two-layer dim (`linear-gradient(0deg, #000 20%, transparent)` over a
55% flat black, blurred), the same circular mark, the same serif heading. When the
welcome page changes, this file is the one place to change with it.

It deliberately does **not** load `startr.style`. This renders once, offline, and a card
that silently loses its layout because a CDN was unreachable would ship without anyone
noticing.

## Rebuild

```sh
cd tools/og-card
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --hide-scrollbars --allow-file-access-from-files \
  --force-device-scale-factor=1 --window-size=1200,630 \
  --screenshot=/tmp/og-card.png "file://$PWD/card.html"
magick /tmp/og-card.png -quality 86 -strip ../../app/static/assets/images/og-image.jpg
```

1200×630 is the Open Graph large-card size and the dimensions
`try_sage_panel.py` declares in `og:image:width` / `og:image:height`. Changing the
window size means changing those too, and `try-sage-welcome.cy.ts` asserts they match.

JPEG, not PNG or WebP, for two reasons. The same card as PNG measures 271 kB against
55 kB. And the static mount serves `.webp` as `text/plain` — harmless for the
slideshow, fatal for a crawler fetching `og:image`.

## Status

The current image is a **rough card**, not final art: the mark is `favicon.png` scaled up
and the type is Georgia. Real art replaces the image without touching the tags, since
`social_image` in `try_sage_panel.py` is the only reference.
