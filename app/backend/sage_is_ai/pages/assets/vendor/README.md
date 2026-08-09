# Vendored third-party assets

Files here are shipped byte-for-byte as their publisher released them. Nothing
in this directory is edited — not for lint, not for spelling, not for style. A
minifier's variable names read as typos forever, and "fixing" one would corrupt
the dependency, which is why `.pre-commit-config.yaml` excludes `/vendor/` and
`*.min.js` from codespell.

They are vendored rather than loaded from a CDN because the no-build end state
serves every shared asset as a local static file: no third-party request on the
page, nothing to 5xx, and an air-gapped deployment works the same as a
connected one.

## htmx.min.js

| | |
| --- | --- |
| version | 2.0.4 |
| source | `https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js` |
| sha256 | `e209dda5c8235479f3166defc7750e1dbcd5a5c1808b7792fc2e6733768fb447` |
| verified | 2026-07-27 |

Provenance is an unbroken chain to the registry's own record, not one download
trusted on sight:

1. npm registry metadata for `htmx.org@2.0.4` declares the package tarball's
   integrity as
   `sha512-HLxMCdfXDOJirs3vBZl/ZLoY+c7PfM4Ahr2Ad4YXh6d22T5ltbTXFFkpx9Tgb2vvmWFMbIc3LqN2ToNkZJvyYQ==`.
2. The downloaded tarball hashes to exactly that.
3. `package/dist/htmx.min.js` inside that tarball has the sha256 above.
4. The file in this directory is byte-identical to it.

Independently, unpkg and jsdelivr both serve the same bytes.

A note for whoever upgrades this, because it is an easy mistake and it was
nearly written into this file: npm's `dist.integrity` is a digest of the
TARBALL, not of any file inside it. Comparing it against a file's own hash
proves nothing and will not match. Check the tarball, then check what you
extracted from it.

To upgrade: repeat the four steps above for the new version, record the new
sha256 here, and re-run `make e2e`. htmx freezes its API by policy, so an
upgrade should be a byte swap — if it is not, that is the news.
